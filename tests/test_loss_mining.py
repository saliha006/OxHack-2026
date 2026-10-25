import copy

from analysis.mine_losses import signatures
from tests.turn2 import EXAMPLE, REQUEST


def row(move="spikes", executed=True, cap=3):
    state = copy.deepcopy(EXAMPLE)
    state["sides"]["p2"]["hazards"]["spikes"] = cap
    request = copy.deepcopy(REQUEST)
    request["active"][0]["moves"][0]["id"] = move
    before = {"state": state, "request": request, "choice": "move 1", "decision_id": "fixture:1"}
    after = copy.deepcopy(before)
    after["state"]["last_turn"] = ([{"type": "move", "side": "p1", "pokemon": 5, "move": move}]
                                  if executed else [])
    return [before, after]


def test_hazard_signature_needs_executed_move_and_public_cap():
    assert signatures(row())["counts"] == {"hazard_at_cap": 1}
    assert signatures(row(executed=False))["counts"] == {}
    assert signatures(row(cap=2))["counts"] == {}


def test_final_transition_is_unknown_and_not_a_negative():
    assert signatures(row()[:1])["opportunities"] == {}


def test_boosted_foe_exposure_requires_boost():
    assert signatures(row())["opportunities"].get("boosted_foe_faint", 0) == 0
    rows = row()
    rows[0]["state"]["sides"]["p2"]["boosts"]["spa"] = 2
    result = signatures(rows)
    assert result["opportunities"]["boosted_foe_faint"] == 1
    assert result["counts"].get("boosted_foe_faint", 0) == 0


def test_forced_replacement_does_not_count_the_same_faint_again():
    rows = row()
    rows[0]["state"]["sides"]["p2"]["boosts"]["spa"] = 2
    rows[0]["state"]["sides"]["p1"]["pokemon"][5]["hp_percent"] = 0
    assert signatures(rows)["opportunities"] == {}
    rows = row()
    rows[0]["request"]["forceSwitch"] = [True]
    assert signatures(rows)["opportunities"] == {}
