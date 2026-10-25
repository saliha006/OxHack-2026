import json
import logging
import statistics
import time
from collections import Counter
from collections.abc import Callable
from pathlib import Path

from poke_env.player import Player
from poke_env.player.battle_order import SingleBattleOrder

from bot.parser import Parser
from decision.actions import our_actions


log = logging.getLogger("bot")
decision_logger = logging.getLogger("decision")


class _ErrorCounter(logging.Handler):
    """Agent.choose never raises; an ERROR on the decision logger is the only sign it fell back."""

    def __init__(self):
        super().__init__(logging.ERROR)
        self.count = 0

    def emit(self, record):
        self.count += 1


def _label(request: dict, choice: str | None) -> str | None:
    """A choice in words, from the request it answers: "move 2 terastallize" -> "Iron Head + Tera"."""
    kind, _, rest = (choice or "").partition(" ")
    try:
        if kind == "move":
            move = request["active"][0]["moves"][int(rest.split()[0]) - 1]
            name = move.get("move") or move["id"]
            return f"{name} + Tera" if "terastallize" in rest else name
        team = request["side"]["pokemon"]
        if kind == "switch":
            return "switch to " + team[int(rest) - 1]["details"].split(",")[0]
        if kind == "team":
            return "lead with " + team[int(rest[0]) - 1]["details"].split(",")[0]
    except (KeyError, IndexError, ValueError):
        pass  # a choice the request can't name (e.g. "default") stays as Showdown spells it
    return None


def _first_legal(request: dict) -> str:
    try:
        return our_actions(request)[0].to_choice()
    except Exception:
        log.exception("no legal option in the request; sending 'default'")
        return "default"


class BattleSession:
    """One battle: every protocol line goes to the parser and the raw log, every request to the agent."""

    def __init__(self, tag: str, agent, runs_dir: Path, clock: Callable[[], float] = time.perf_counter,
                 on_decision: Callable[[str, dict], None] | None = None):
        self.tag = tag
        self.agent = agent
        self.clock = clock
        self.on_decision = on_decision
        # Our side is only known once poke-env has seen the |player| lines, so early lines wait here.
        self.backlog: list[str] = []
        self.parser: Parser | None = None
        # Line-buffered, so a killed run keeps every line so far and the demo can stream the trace live.
        self.raw = open(runs_dir / f"{tag}.log", "w", encoding="utf-8", buffering=1)
        self.trace = open(runs_dir / f"{tag}.jsonl", "w", encoding="utf-8", buffering=1)
        self.decision_file = logging.FileHandler(runs_dir / f"{tag}.decision.log", encoding="utf-8", delay=True)
        self.errors = _ErrorCounter()
        self.answered: tuple[object, int] | None = None  # (rqid, retries) of the last request we answered
        self.decisions = 0
        self.fallbacks = 0
        self.think_ms: list[float] = []
        self.rejected_choices = 0
        self.fallback_reasons: Counter[str] = Counter()
        self.world_counts: Counter[str] = Counter()
        self.search_ms: list[float] = []
        self.pending_decision: dict | None = None

    def feed(self, line: str) -> None:
        self.raw.write(line + "\n")
        if self.parser is None:
            self.backlog.append(line)
        else:
            self.parser.feed(line)

    def decide(self, request: dict, us: str) -> str | None:
        if request.get("wait"):
            return None  # do not consume pending events or reuse the preceding decision's trace
        if self.parser is None:
            self.parser = Parser(us)
            for line in self.backlog:
                self.parser.feed(line)
            self.backlog = []
        rqid = request.get("rqid")
        if self.answered is not None and rqid is not None and self.answered[0] == rqid:
            return self._retry(request, rqid)

        self.parser.observe_request(request)
        state = self.parser.snapshot()
        self._observe_reply(state)
        before = self.errors.count
        decision_logger.addHandler(self.errors)
        decision_logger.addHandler(self.decision_file)
        start = self.clock()
        try:
            choice = self.agent.choose(request, state)
        finally:
            elapsed = (self.clock() - start) * 1000
            decision_logger.removeHandler(self.errors)
            decision_logger.removeHandler(self.decision_file)
        agent_trace = getattr(self.agent, "last_trace", None) or {}
        reason = agent_trace.get("fallback_reason")
        fell_back = self.errors.count > before or bool(reason)
        self.decisions += 1
        self.fallbacks += fell_back
        self.think_ms.append(elapsed)
        if fell_back:
            self.fallback_reasons[str(reason or "decision_error")] += 1
        for key in ("requested_worlds", "completed_worlds", "failed_worlds", "usable_worlds"):
            self.world_counts[key] += agent_trace.get(key, 0)
        self.search_ms.append(float(agent_trace.get("search_ms", 0)))
        self.answered = (rqid, 0)
        line = {"turn": state["turn"], "kind": _kind(request), "choice": choice, "label": _label(request, choice),
                "think_ms": round(elapsed, 1), "fallback": fell_back, "state": state, "request": request}
        line.update(agent_trace)
        line["decision_id"] = f"{self.tag}:{self.decisions}"
        # Append the reply as its own linked record once observed. Raw visit shares stay in this decision's trace.
        self.pending_decision = line
        self.trace.write(json.dumps(line) + "\n")
        if self.on_decision:
            self.on_decision(self.tag, line)
        return choice

    def _observe_reply(self, state: dict) -> None:
        if self.pending_decision is None:
            return
        them = "p2" if state["us"] == "p1" else "p1"
        observed, followups = [], []
        prior_events = []
        for event in state["last_turn"]:
            if event["side"] == them and event["type"] in ("move", "switch"):
                action = {"kind": event["type"], "move": event.get("move"), "slot": event["pokemon"]}
                # A replacement after fainting (or a switch forced by our move) is not the reply searched at root.
                fainted = any(e["side"] == them and e["type"] == "damage" and e.get("hp_percent") == 0
                              for e in prior_events)
                forced = event["type"] == "switch" and any(e["side"] != them and e["type"] == "move"
                                                           for e in prior_events)
                if not observed and not fainted and not forced and self.pending_decision["kind"] != "team":
                    if any(e["side"] == them and (e.get("source") or "").startswith("tera:") for e in prior_events):
                        action["tera"] = True
                    observed.append(action)
                else:
                    followups.append(action)
            prior_events.append(event)
        reply = {"kind": "observation", "decision_id": self.pending_decision["decision_id"],
                 "decision_turn": self.pending_decision["turn"], "observed_turn": state["turn"],
                 "opponent_actions": observed or None, "opponent_action_status": "observed" if observed else "unknown"}
        if followups:
            reply["followup_actions"] = followups
        self.trace.write(json.dumps(reply) + "\n")
        self.pending_decision = None

    def _retry(self, request: dict, rqid) -> str:
        """Showdown rejected our answer to this request: try the first legal option, then let Showdown pick."""
        retries = self.answered[1] + 1
        self.answered = (rqid, retries)
        self.fallbacks += 1
        self.rejected_choices += 1
        self.fallback_reasons["rejected_choice"] += 1
        invalidate = getattr(self.agent, "invalidate_choice", None)
        invalidation_error = None
        if invalidate:
            invalidation_error = invalidate()
        choice = _first_legal(request) if retries == 1 else "default"
        log.warning("%s: choice rejected (retry %d), sending %s", self.tag, retries, choice)
        self.trace.write(json.dumps({"kind": "retry", "choice": choice, "fallback": True,
                                    "decision_id": self.pending_decision["decision_id"] if self.pending_decision else None,
                                    **({"invalidation_error": invalidation_error} if invalidation_error else {})}) + "\n")
        return choice

    def close(self, won: bool | None, turns: int) -> dict:
        side = self.parser.state["us"] if self.parser else None
        if self.parser:
            self._observe_reply(self.parser.snapshot())
        summary = {"tag": self.tag, "side": side, "won": won, "turns": turns, "decisions": self.decisions,
                   "fallbacks": self.fallbacks, "rejected_choices": self.rejected_choices,
                   "fallback_reasons": dict(self.fallback_reasons), **dict(self.world_counts),
                   "decision_ms": self.think_ms, "actual_search_ms": self.search_ms,
                   **_percentiles(self.think_ms)}
        self.trace.write(json.dumps({"kind": "end", **summary}) + "\n")
        for f in (self.raw, self.trace):
            f.close()
        self.decision_file.close()
        close_agent = getattr(self.agent, "close", None)
        if close_agent:
            close_agent()
        return summary


def _kind(request: dict) -> str:
    if request.get("teamPreview"):
        return "team"
    return "switch" if request.get("forceSwitch") else "move"


def _percentiles(ms: list[float]) -> dict:
    if len(ms) < 2:
        p50 = p95 = p99 = round(ms[0], 1) if ms else None
    else:
        cuts = statistics.quantiles(ms, n=100, method="inclusive")
        p50, p95, p99 = round(cuts[49], 1), round(cuts[94], 1), round(cuts[98], 1)
    return {"think_p50_ms": p50, "think_p95_ms": p95, "think_p99_ms": p99}


class AgentPlayer(Player):
    """A poke-env player whose every choice comes from the decision layer, fed by our own parser."""

    def __init__(self, make_agent: Callable[[], object], runs_dir: str | Path = "runs",
                 on_decision: Callable[[str, dict], None] | None = None, **kwargs):
        super().__init__(**kwargs)
        self.make_agent = make_agent
        self.on_decision = on_decision
        self.runs_dir = Path(runs_dir)
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.sessions: dict[str, BattleSession] = {}
        self.summaries: list[dict] = []
        self.finished_tags: set[str] = set()

    async def _handle_battle_message(self, split_messages: list[list[str]]):
        tag = split_messages[0][0].lstrip(">")
        if tag in self.finished_tags:
            # Showdown can send a final request/deinit after the finish callback.
            # Reopening a session here would truncate the completed battle's files.
            return
        if tag.startswith("battle-"):
            if tag not in self.sessions:
                self.sessions[tag] = BattleSession(tag, self.make_agent(), self.runs_dir, on_decision=self.on_decision)
            session = self.sessions[tag]
            # Our parser sees the whole message before poke-env answers the request inside it.
            for parts in split_messages[1:]:
                if len(parts) > 1:
                    session.feed("|".join(parts))
        try:
            await super()._handle_battle_message(split_messages)
        except Exception:
            # An error here would otherwise leave the request unanswered and the battle stalled (poke-env #973).
            log.exception("poke-env failed on a message in %s", tag)
            if any(len(parts) > 1 and parts[1] == "request" for parts in split_messages[1:]):
                await self.ps_client.send_message("/choose default", tag)

    def choose_move(self, battle) -> SingleBattleOrder:
        # poke-env never asks on a wait request, the only one the agent answers with None.
        choice = self.sessions[battle.battle_tag].decide(battle.last_request, battle.player_role)
        return SingleBattleOrder(f"/choose {choice}")

    def teampreview(self, battle) -> str:
        choice = self.sessions[battle.battle_tag].decide(battle.last_request, battle.player_role)
        return f"/choose {choice}"

    def _battle_finished_callback(self, battle):
        self.finished_tags.add(battle.battle_tag)
        self.summaries.append(self.sessions.pop(battle.battle_tag).close(battle.won, battle.turn))
