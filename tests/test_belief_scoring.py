import copy

from evaluation.belief_reliability import score_transitions, summarize
from tests.test_belief import PRIORS
from tests.turn2 import EXAMPLE, REQUEST


def test_target_revelation_is_scored_before_updating_any_ablation():
    first = copy.deepcopy(EXAMPLE)
    first["sides"]["p2"]["pokemon"][2]["revealed_moves"] = ["makeitrain"]
    second = copy.deepcopy(first)
    second["turn"] += 1
    # None of these candidates has this newly revealed move. Updating before
    # scoring would rebuild every posterior to include it, hiding support failure.
    second["sides"]["p2"]["pokemon"][2]["revealed_moves"].append("thunderwave")
    decisions = [{"state": state, "request": REQUEST, "choice": "default"} for state in (first, second)]
    rows, _ = score_transitions(decisions, PRIORS, battle_id="fixture", role="a")
    target = next(row for row in rows if row["revealed"] == "thunderwave")
    assert all(all("thunderwave" not in candidate["moves"] for candidate in values)
               for values in target["predictions"].values())
    result = summarize([target])["subsets"]["scoring"]
    assert set(result["zero_support_revelations"].values()) == {1}


def test_unobserved_final_transition_has_no_invented_labels():
    rows, _ = score_transitions([{"state": copy.deepcopy(EXAMPLE), "request": REQUEST, "choice": "default"}],
                                PRIORS, battle_id="fixture", role="a")
    assert rows == []
