import pytest

from decision.actions import Action
from decision.selector import expected_value, select

A, B, C = Action("move", 1), Action("move", 2), Action("switch", 3)


def uniform(sets, *actions):
    """The same opponent odds under every set."""
    return {s: {b: 1 / len(actions) for b in actions} for s in sets}


def test_picks_highest_expected_value():
    scores = {
        A: {"s1": {"attack": 0.2, "switch": 0.6}, "s2": {"attack": 0.4, "switch": 0.6}},
        B: {"s1": {"attack": 0.5, "switch": 0.5}, "s2": {"attack": 0.5, "switch": 0.5}},
    }
    opp = {s: {"attack": 0.25, "switch": 0.75} for s in ("s1", "s2")}
    # A: 0.25*(0.5*0.2+0.5*0.4) + 0.75*0.6 = 0.525 > B: 0.5
    assert select(scores, {"s1": 0.5, "s2": 0.5}, opp) == A


def test_set_probabilities_weight_the_score():
    scores = {A: {"s1": {"x": 1.0}, "s2": {"x": 0.0}}, B: {"s1": {"x": 0.0}, "s2": {"x": 1.0}}}
    opp = uniform(("s1", "s2"), "x")
    assert select(scores, {"s1": 0.9, "s2": 0.1}, opp) == A
    assert select(scores, {"s1": 0.1, "s2": 0.9}, opp) == B


def test_opponent_odds_can_differ_per_set():
    # Under s1 they're locked into "x"; under s2 they only ever pick "y".
    scores = {A: {"s1": {"x": 1.0}, "s2": {"x": 1.0, "y": 0.0}},
              B: {"s1": {"x": 0.0}, "s2": {"x": 0.0, "y": 1.0}}}
    opp = {"s1": {"x": 1.0}, "s2": {"x": 0.0, "y": 1.0}}
    assert expected_value(scores[A], {"s1": 0.3, "s2": 0.7}, opp) == pytest.approx(0.3)
    assert select(scores, {"s1": 0.3, "s2": 0.7}, opp) == B


def test_equal_ev_breaks_toward_better_worst_case():
    scores = {A: {"s": {"x": 0.0, "y": 1.0}}, B: {"s": {"x": 0.5, "y": 0.5}}}
    assert select(scores, {"s": 1.0}, uniform(("s",), "x", "y")) == B


def test_worst_case_spans_sets_and_opponent_actions():
    scores = {A: {"s1": {"x": 0.5}, "s2": {"x": 0.5}}, B: {"s1": {"x": 1.0}, "s2": {"x": 0.0}}}
    assert select(scores, {"s1": 0.5, "s2": 0.5}, uniform(("s1", "s2"), "x")) == A


def test_impossible_outcomes_do_not_count_as_worst_case():
    scores = {A: {"s": {"x": 0.5, "never": -1.0}}, B: {"s": {"x": 0.5, "never": 0.5}}}
    # "never" has probability 0, so A's -1.0 can't happen; A wins on order.
    assert select(scores, {"s": 1.0}, {"s": {"x": 1.0, "never": 0.0}}) == A


def test_full_tie_goes_to_first_action_in_order():
    scores = {C: {"s": {"x": 0.5}}, A: {"s": {"x": 0.5}}, B: {"s": {"x": 0.5}}}
    assert select(scores, {"s": 1.0}, uniform(("s",), "x")) == C


def test_float_rounding_does_not_break_a_tie():
    scores = {A: {"s": {"x": 0.1 + 0.2}}, B: {"s": {"x": 0.3}}}
    assert select(scores, {"s": 1.0}, uniform(("s",), "x")) == A


def test_engine_precision_noise_still_counts_as_a_tie():
    # poke-engine probabilities are 32-bit, so equal EVs can differ around 1e-8.
    scores = {A: {"s1": {"x": 1.00000006}, "s2": {"x": 0.0}},  # EV 0.50000003, worst 0.0
              B: {"s1": {"x": 0.5}, "s2": {"x": 0.5}}}          # EV 0.5, worst 0.5
    assert select(scores, {"s1": 0.5, "s2": 0.5}, uniform(("s1", "s2"), "x")) == B


def test_ties_near_zero_use_an_absolute_tolerance():
    scores = {A: {"s1": {"x": 1.00000002}, "s2": {"x": -1.0}},  # EV 1e-8, worst -1.0
              B: {"s1": {"x": 0.0}, "s2": {"x": 0.0}}}          # EV 0.0, worst 0.0
    # No relative tolerance can call 1e-8 and 0 equal; an absolute one can, so B wins on its better worst case.
    assert select(scores, {"s1": 0.5, "s2": 0.5}, uniform(("s1", "s2"), "x")) == B


def test_empty_table_is_an_error():
    with pytest.raises(ValueError):
        select({}, {"s": 1.0}, {"s": {"x": 1.0}})
