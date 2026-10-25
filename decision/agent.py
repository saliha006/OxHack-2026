import copy
import logging
import math
import time
from collections.abc import Callable
from functools import partial

from poke_engine import State

from contracts.battle_state import BattleState
from contracts.set_candidates import SetCandidates
from decision.actions import Action, our_actions
from decision.adapter import build_public_state, build_state
from decision.belief import Belief
from decision.lead import pick_lead
from decision.opponent import opp_actions, public_actions, uniform_policy
from decision.selector import expected_value, select
from decision.sets import PokemonSet
from decision.simulate import simulate
from decision.value import value


log = logging.getLogger("decision")


class Agent:
    """One battle's decision maker: a Showdown request plus a BattleState in, a choice string out."""

    def __init__(self, priors: SetCandidates, k: int = 5, budget: float = 3.0,
                 clock: Callable[[], float] = time.monotonic):
        self.priors = priors
        self.k = k
        self.budget = budget
        self.clock = clock
        self.deadline = math.inf  # set per decision by choose()
        self.belief: Belief | None = None

    def choose(self, request: dict, battle: BattleState) -> str | None:
        """Never raises and always answers: a decision layer error must not stall the battle (feature 12)."""
        if request.get("wait"):
            return None
        self.deadline = self.clock() + self.budget
        try:
            return self._choose(request, battle)
        except Exception:
            log.exception("decision failed on turn %s; sending the first legal option", battle.get("turn"))
            if self.belief is not None:
                # This turn's choice wasn't planned, so belief mustn't replay it next turn.
                self.belief.last_request = self.belief.last_choice = None
            try:
                return our_actions(request)[0].to_choice()
            except Exception:
                log.exception("couldn't list legal options either; sending 'default'")
                return "default"

    def _choose(self, request: dict, battle: BattleState) -> str:
        if self.belief is None:
            self.belief = Belief(self.priors, battle)
        self.belief.update(battle)
        if request.get("teamPreview"):
            return pick_lead(request, battle).to_choice()
        if request.get("forceSwitch"):
            action = self._best_switch_in(request, battle)
        else:
            action, _ = self._evaluate(request, battle)
        self.belief.chose(request, action)
        return action.to_choice()

    def choose_public(self, battle: BattleState, our_sets: list[PokemonSet]) -> Action:
        """A move turn of a replay, which has no request: our side is guessed like theirs, from `sets_from_game`.

        The action's slots index team-preview order, not Showdown's. Unlike choose(), errors propagate, so a backtest
        records them instead of scoring a fallback as a decision.
        """
        self.deadline = self.clock() + self.budget
        if self.belief is None:
            self.belief = Belief(self.priors, battle)
        # belief.chose is never called: its turn replay rebuilds our side from the request, so on a replay belief
        # runs on reveals alone.
        self.belief.update(battle)
        build = partial(build_public_state, battle, our_sets)
        # Our options don't depend on their sets, so any guess at theirs will do to list them.
        _, best_guess = self.belief.scenarios(1)[0]
        action, _ = self._best(public_actions(build(best_guess), battle, battle["us"]), build, battle)
        return action

    def _evaluate(self, request: dict, battle: BattleState) -> tuple[Action, float]:
        """The best action for a move request and its expected value, over belief's scenarios and their replies."""
        return self._best(our_actions(request), partial(build_state, request, battle), battle)

    def _best(self, ours: list[Action], build: Callable[[list[PokemonSet]], State],
              battle: BattleState) -> tuple[Action, float]:
        scores = {a: {} for a in ours}
        set_probs, opp_probs = {}, {}
        for i, (p, sets) in enumerate(self.belief.scenarios(self.k)):
            # Scenarios come most likely first, so stopping early keeps the ones that matter most.
            if set_probs and self.clock() > self.deadline:
                break
            state = build(sets)
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
