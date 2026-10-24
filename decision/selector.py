import math
from collections.abc import Hashable, Mapping

from decision.actions import Action

# scores[our action][opponent set][opponent action] = value of the resulting state.
# The opponent's options depend on its set (Choice lock, Taunt, Struggle), so their odds are given per set.
Table = Mapping[Hashable, Mapping[Hashable, float]]
Scores = Mapping[Action, Table]
OppProbs = Mapping[Hashable, Mapping[Hashable, float]]


def select(scores: Scores, set_probs: Mapping[Hashable, float], opp_probs: OppProbs) -> Action:
    """Highest expected value; ties go to the better worst case, then to the first action in `scores` order."""
    if not scores:
        raise ValueError("no actions to choose from")
    ev = {a: expected_value(table, set_probs, opp_probs) for a, table in scores.items()}
    worst = {a: _worst(table, set_probs, opp_probs) for a, table in scores.items()}

    best_ev = max(ev.values())
    tied = [a for a in scores if _tied(ev[a], best_ev)]
    best_worst = max(worst[a] for a in tied)
    return next(a for a in tied if _tied(worst[a], best_worst))


def expected_value(table: Table, set_probs: Mapping[Hashable, float], opp_probs: OppProbs) -> float:
    """Σ p(set) · Σ p(their action | set) · value."""
    return sum(set_probs[s] * opp_probs[s][b] * value for s, by_action in table.items() for b, value in by_action.items())


def _worst(table: Table, set_probs, opp_probs) -> float:
    # Only outcomes that can happen: a zero-probability reply shouldn't scare us off an action.
    return min(
        value
        for s, by_action in table.items()
        for b, value in by_action.items()
        if set_probs[s] > 0 and opp_probs[s][b] > 0
    )


def _tied(x: float, y: float) -> bool:
    # poke-engine's probabilities are 32-bit floats (~7 digits), so equal EVs can differ around 1e-8.
    # The absolute part covers scores near zero, where no relative tolerance can call them equal.
    return math.isclose(x, y, rel_tol=1e-6, abs_tol=1e-6)
