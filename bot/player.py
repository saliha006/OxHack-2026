import json
import logging
import statistics
import time
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


def _first_legal(request: dict) -> str:
    try:
        return our_actions(request)[0].to_choice()
    except Exception:
        log.exception("no legal option in the request; sending 'default'")
        return "default"


class BattleSession:
    """One battle: every protocol line goes to the parser and the raw log, every request to the agent."""

    def __init__(self, tag: str, agent, runs_dir: Path, clock: Callable[[], float] = time.perf_counter):
        self.tag = tag
        self.agent = agent
        self.clock = clock
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

    def feed(self, line: str) -> None:
        self.raw.write(line + "\n")
        if self.parser is None:
            self.backlog.append(line)
        else:
            self.parser.feed(line)

    def decide(self, request: dict, us: str) -> str | None:
        if self.parser is None:
            self.parser = Parser(us)
            for line in self.backlog:
                self.parser.feed(line)
            self.backlog = []
        rqid = request.get("rqid")
        if self.answered is not None and rqid is not None and self.answered[0] == rqid:
            return self._retry(request, rqid)

        state = self.parser.snapshot()
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
        fell_back = self.errors.count > before
        self.decisions += 1
        self.fallbacks += fell_back
        self.think_ms.append(elapsed)
        self.answered = (rqid, 0)
        line = {"turn": state["turn"], "kind": _kind(request), "choice": choice, "think_ms": round(elapsed, 1),
                "fallback": fell_back, "state": state}
        line.update(getattr(self.agent, "last_trace", None) or {})
        self.trace.write(json.dumps(line) + "\n")
        return choice

    def _retry(self, request: dict, rqid) -> str:
        """Showdown rejected our answer to this request: try the first legal option, then let Showdown pick."""
        retries = self.answered[1] + 1
        self.answered = (rqid, retries)
        self.fallbacks += 1
        choice = _first_legal(request) if retries == 1 else "default"
        log.warning("%s: choice rejected (retry %d), sending %s", self.tag, retries, choice)
        self.trace.write(json.dumps({"kind": "retry", "choice": choice, "fallback": True}) + "\n")
        return choice

    def close(self, won: bool | None, turns: int) -> dict:
        side = self.parser.state["us"] if self.parser else None
        summary = {"tag": self.tag, "side": side, "won": won, "turns": turns, "decisions": self.decisions,
                   "fallbacks": self.fallbacks, **_percentiles(self.think_ms)}
        self.trace.write(json.dumps({"kind": "end", **summary}) + "\n")
        for f in (self.raw, self.trace):
            f.close()
        self.decision_file.close()
        return summary


def _kind(request: dict) -> str:
    if request.get("teamPreview"):
        return "team"
    return "switch" if request.get("forceSwitch") else "move"


def _percentiles(ms: list[float]) -> dict:
    if len(ms) < 2:
        p50 = p99 = round(ms[0], 1) if ms else None
    else:
        cuts = statistics.quantiles(ms, n=100, method="inclusive")
        p50, p99 = round(cuts[49], 1), round(cuts[98], 1)
    return {"think_p50_ms": p50, "think_p99_ms": p99}


class AgentPlayer(Player):
    """A poke-env player whose every choice comes from the decision layer, fed by our own parser."""

    def __init__(self, make_agent: Callable[[], object], runs_dir: str | Path = "runs", **kwargs):
        super().__init__(**kwargs)
        self.make_agent = make_agent
        self.runs_dir = Path(runs_dir)
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.sessions: dict[str, BattleSession] = {}
        self.summaries: list[dict] = []

    async def _handle_battle_message(self, split_messages: list[list[str]]):
        tag = split_messages[0][0].lstrip(">")
        if tag.startswith("battle-"):
            if tag not in self.sessions:
                self.sessions[tag] = BattleSession(tag, self.make_agent(), self.runs_dir)
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
        self.summaries.append(self.sessions.pop(battle.battle_tag).close(battle.won, battle.turn))
