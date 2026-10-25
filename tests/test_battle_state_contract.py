import json
from pathlib import Path

from contracts.battle_state import BattleState, Event, Field, PokemonState, SideState

EXAMPLE = Path(__file__).parent.parent / "contracts" / "examples" / "battle_state_turn2.json"


def keys(typed_dict):
    return set(typed_dict.__required_keys__)


def test_example_has_exactly_the_contract_keys():
    state = json.loads(EXAMPLE.read_text())
    assert set(state) == keys(BattleState)
    assert set(state["field"]) == keys(Field)
    for side in state["sides"].values():
        assert set(side) == keys(SideState)
        assert len(side["pokemon"]) == 6
        for mon in side["pokemon"]:
            assert set(mon) == keys(PokemonState)
    for event in state["last_turn"]:
        assert set(event) == keys(Event)


def test_example_matches_the_sample_log_after_turn_one():
    # design/bot-layer.md §1b: Kingambit took Make It Rain to 60%, Leftovers to 66%; Gholdengo Tera'd Steel.
    state = json.loads(EXAMPLE.read_text())
    ours, theirs = state["sides"]["p1"], state["sides"]["p2"]
    assert ours["pokemon"][ours["active"]]["hp_percent"] == 66
    gholdengo = theirs["pokemon"][theirs["active"]]
    assert gholdengo["revealed_moves"] == ["makeitrain"]
    assert gholdengo["terastallized"] and theirs["tera_used"]
    assert theirs["boosts"]["spa"] == -1
    assert [e["type"] for e in state["last_turn"]] == ["switch", "reveal", "move", "damage", "heal"]
