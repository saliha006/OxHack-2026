import copy
import logging
import math
import time
from collections.abc import Callable

from contracts.battle_state import BattleState
from contracts.set_candidates import SetCandidates
from decision.actions import Action, our_actions
from decision.adapter import build_state
from decision.belief import Belief
from decision.lead import pick_lead
from decision.opponent import opp_actions, uniform_policy
from decision.selector import expected_value, select
from decision.simulate import simulate
from decision.value import value


log = logging.getLogger("decision")


class Agent:
    """One battle's decision maker: a Showdown request plus a BattleState in, a choice string out."""

    def __init__(self, priors: SetCandidates, k: int = 5, budget: float = 3.0,
                 clock: Callable[[], float] = time.monotonic, *, backend: str = "mcts",
                 mcts_worlds: int = 8, search_ms: int = 150, engine_threads: int = 1,
                 sampling: str = "team", frozen_beliefs: bool = False, seed: int = 2026):
        if backend not in {"one_ply", "mcts"}:
            raise ValueError("backend must be one_ply or mcts")
        if sampling not in {"team", "active"}:
            raise ValueError("sampling must be team or active")
        if min(mcts_worlds, search_ms, engine_threads) < 1 or budget <= 0:
            raise ValueError("worlds, search time, threads and budget must be positive")
        self.priors = priors
        self.k = k
        self.budget = budget
        self.clock = clock
        self.deadline = math.inf  # set per decision by choose()
        self.belief: Belief | None = None
        self.backend = backend
        self.config = {"mcts_worlds": mcts_worlds, "search_ms": search_ms, "engine_threads": engine_threads,
                       "sampling": sampling, "frozen_beliefs": frozen_beliefs, "seed": seed,
                       "budget_seconds": budget, "return_reserve_seconds": min(0.3, budget * 0.1),
                       "randomisation": False, "learned_reranker": False}
        self.worker = None
        self.last_trace: dict | None = None

    def choose(self, request: dict, battle: BattleState) -> str | None:
        """Never raises and always answers: a decision layer error must not stall the battle (feature 12)."""
        if request.get("wait"):
            return None
        started = time.monotonic()
        self.deadline = self.clock() + self.budget
        self.last_trace = {"backend": self.backend, "config": self.config.copy(), "turn": battle.get("turn"),
                           "requested_worlds": 0, "scheduled_worlds": 0, "completed_worlds": 0,
                           "failed_worlds": 0, "interrupted_worlds": 0, "usable_worlds": 0,
                           "sampled_worlds": [], "worlds": [], "failures": [], "mapping_failures": [],
                           "fallback_reason": None, "state_preparation_ms": 0.0, "search_ms": 0.0,
                           "search_support": {}, "opponent_support": {}}
        try:
            if self.backend == "mcts":
                choice = self._choose_mcts(request, battle, started)
            else:
                choice = self._choose(request, battle)
            self.last_trace["chosen_action"] = choice
            return choice
        except BaseException as exc:
            log.exception("decision failed on turn %s; sending the first legal option", battle.get("turn"))
            self.last_trace["fallback_reason"] = "decision_error"
            self.last_trace["failures"].append({"stage": "decision", "type": type(exc).__name__, "message": str(exc)})
            if self.belief is not None:
                # This turn's choice wasn't planned, so belief mustn't replay it next turn.
                self.belief.last_request = self.belief.last_choice = None
            try:
                choice = our_actions(request)[0].to_choice()
            except Exception:
                log.exception("couldn't list legal options either; sending 'default'")
                choice = "default"
            self.last_trace["chosen_action"] = choice
            return choice
        finally:
            self.last_trace["total_ms"] = (time.monotonic() - started) * 1000

    def _choose_mcts(self, request: dict, battle: BattleState, started: float) -> str:
        from decision.search import SearchWorker
        from decision.search_policy import pool_results

        # Preview remains the established lead policy, with no search or native preparation.
        if request.get("teamPreview"):
            return pick_lead(request, battle).to_choice()
        legal = our_actions(request)
        if not legal:
            self.last_trace["fallback_reason"] = "no_legal_actions"
            return "default"
        fallback = legal[0]
        self.last_trace["requested_worlds"] = self.config["mcts_worlds"]
        if self.worker is None:
            self.worker = SearchWorker(self.priors)
        cutoff = started + self.budget - self.config["return_reserve_seconds"]
        worker_started = time.monotonic()
        previous_generation = self.worker.generation
        active_world = None
        prepared = False
        for message in self.worker.stream(request, battle, self.config, cutoff):
            kind = message["kind"]
            if kind == "prepared":
                prepared = True
                self.last_trace.update({k: v for k, v in message.items() if k != "kind"})
            elif kind == "world_started":
                active_world = message["index"]
                self.last_trace["scheduled_worlds"] += 1
            elif kind == "world":
                result = message["result"]
                active_world = None
                self.last_trace["worlds"].append(result)
                self.last_trace["completed_worlds"] += 1
                self.last_trace["failed_worlds"] += bool(result.get("error"))
                self.last_trace["search_ms"] += result.get("elapsed_ms", 0)
                self.last_trace["state_preparation_ms"] += result.get("preparation_ms", 0)
            elif kind == "failure":
                self.last_trace["failures"].append(message["error"])
                if active_world is not None:
                    # The child announced this world before entering native work. Its crash/timeout is a failed
                    # attempt, not a completed result; earlier streamed worlds still participate in pooling.
                    self.last_trace["worlds"].append({"index": active_world, "our_visits": [],
                                                      "opponent_visits": [], "error": message["error"],
                                                      "interrupted": True})
                    self.last_trace["failed_worlds"] += 1
                    self.last_trace["interrupted_worlds"] += 1
                    active_world = None
            elif kind == "done":
                self.last_trace["scheduled_worlds"] = message.get("scheduled_worlds", 0)
        self.last_trace["worker_wall_ms"] = (time.monotonic() - worker_started) * 1000
        self.last_trace["worker_generation"] = self.worker.generation
        self.last_trace["belief_history_reset"] = (previous_generation > 0 and
                                                    self.worker.generation > previous_generation)
        self.last_trace["belief_history_was_reset"] = self.worker.generation > 1
        pooled = pool_results(self.last_trace["worlds"], request)
        action = pooled.pop("action")
        self.last_trace.update(pooled)
        if action is None:
            action = fallback
            self.last_trace["fallback_reason"] = ("worker_failure" if self.last_trace["failures"]
                                                   else "no_supported_legal_action")
        bookkeeping_deadline = min(started + self.budget, time.monotonic() + 0.05)
        bookkeeping_started = time.monotonic()
        bookkeeping_error = self.worker.chose(request, action, deadline=bookkeeping_deadline) if prepared else None
        self.last_trace["bookkeeping_ms"] = (time.monotonic() - bookkeeping_started) * 1000
        self.last_trace["replay_not_recorded"] = bool(bookkeeping_error) or not prepared
        if not prepared:
            self.last_trace["replay_not_recorded_reason"] = "preparation_failed"
        if bookkeeping_error:
            self.last_trace["bookkeeping_error"] = bookkeeping_error
            self.last_trace["worker_restart_required"] = self.worker.process is None
            log.warning("chosen action retained; replay bookkeeping failed: %s", bookkeeping_error)
        return action.to_choice()

    def close(self) -> None:
        """Release the per-battle native worker, including after a cancelled game."""
        if self.worker is not None:
            self.worker.close()
            self.worker = None

    def invalidate_choice(self) -> dict | None:
        """A server rejection means the originally planned move is not replay evidence."""
        if self.belief is not None:
            self.belief.last_request = self.belief.last_choice = None
        if self.worker is not None:
            error = self.worker.invalidate_choice(deadline=time.monotonic() + 0.05)
            if error and self.last_trace is not None:
                self.last_trace["invalidation_error"] = error
                self.last_trace["replay_not_recorded"] = True
                self.last_trace["worker_restart_required"] = self.worker.process is None
            return error
        return None

    def _choose(self, request: dict, battle: BattleState) -> str:
        previous_recoveries = len(self.belief.recovery_events) if self.belief is not None else 0
        if self.belief is None:
            self.belief = Belief(self.priors, battle)
        self.belief.update(battle)
        if self.last_trace is not None:
            self.last_trace["recovery_events"] = self.belief.recovery_events[previous_recoveries:]
            self.last_trace["belief_candidates"] = self.belief.candidate_records()
        if request.get("teamPreview"):
            return pick_lead(request, battle).to_choice()
        if request.get("forceSwitch"):
            action = self._best_switch_in(request, battle)
        else:
            action, _ = self._evaluate(request, battle)
        self.belief.chose(request, action)
        return action.to_choice()

    def _evaluate(self, request: dict, battle: BattleState) -> tuple[Action, float]:
        """The best action for a move request and its expected value, over belief's scenarios and their replies."""
        ours = our_actions(request)
        scores = {a: {} for a in ours}
        set_probs, opp_probs = {}, {}
        for i, (p, sets) in enumerate(self.belief.scenarios(self.k)):
            # Scenarios come most likely first, so stopping early keeps the ones that matter most.
            if set_probs and self.clock() > self.deadline:
                break
            state = build_state(request, battle, sets)
            theirs = opp_actions(state, battle)
            set_probs[i], opp_probs[i] = p, uniform_policy(theirs)
            for a in ours:
                # Each (our action, their action) pair is scored as the probability-weighted value of its outcomes.
                scores[a][i] = {b: sum(q * value(s) for q, s in simulate(state, a, b)) for b in theirs}
        done = sum(set_probs.values())
        set_probs = {i: p / done for i, p in set_probs.items()}
        best = select(scores, set_probs, opp_probs)
        return best, expected_value(scores[best], set_probs, opp_probs)

    def _best_switch_in(self, request: dict, battle: BattleState) -> Action:
        """Feature 11 stand-in: send whichever Pokémon gives the best next turn, judged by the move-turn evaluation."""
        options = our_actions(request)
        evs = [self._evaluate(_as_move_request(request, option.slot), battle)[1] for option in options]
        return options[evs.index(max(evs))]


def _as_move_request(request: dict, slot: int) -> dict:
    """The move request we'd get next turn with `slot` sent in: full PP assumed, since only the active's PP is sent."""
    hypothetical = copy.deepcopy(request)
    del hypothetical["forceSwitch"]
    team = hypothetical["side"]["pokemon"]
    for n, mon in enumerate(team, 1):
        mon["active"] = n == slot
    hypothetical["active"] = [{"moves": [{"id": m, "pp": 16, "disabled": False} for m in team[slot - 1]["moves"]]}]
    return hypothetical
