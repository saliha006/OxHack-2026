import math

import pytest
from poke_engine import Move, Pokemon, Side, State

from decision.actions import Action
from decision.simulate import simulate


def turn_one():
    """Turn 1 of replay gen9ou-2703852247 (design/bot-layer.md §1b), with common spreads assumed."""
    meowscarada = Pokemon(id="meowscarada", level=100, types=("grass", "dark"), hp=294, maxhp=294,
        ability="protean", item="choiceband", attack=319, defense=176, special_attack=146,
        special_defense=176, speed=377, tera_type="grass",
        moves=[Move(id=m) for m in ("flowertrick", "knockoff", "uturn", "tripleaxel")])
    kingambit = Pokemon(id="kingambit", level=100, types=("dark", "steel"), hp=404, maxhp=404,
        ability="supremeoverlord", item="leftovers", attack=405, defense=276, special_attack=140,
        special_defense=207, speed=137, tera_type="dark",
        moves=[Move(id=m) for m in ("swordsdance", "kowtowcleave", "suckerpunch", "ironhead")])
    gholdengo = Pokemon(id="gholdengo", level=100, types=("steel", "ghost"), hp=314, maxhp=314,
        ability="goodasgold", item="choicescarf", attack=140, defense=226, special_attack=365,
        special_defense=209, speed=303, tera_type="steel",
        moves=[Move(id=m) for m in ("makeitrain", "shadowball", "trick", "focusblast")])
    return State(side_one=Side(pokemon=[meowscarada, kingambit]), side_two=Side(pokemon=[gholdengo]))


def showdown_percent(mon):
    # Showdown rounds HP up when it reports a percentage.
    return math.ceil(100 * mon.hp / mon.maxhp)


def test_turn_one_matches_the_real_game():
    outcomes = simulate(turn_one(), Action("switch", 2), Action("move", 1, tera=True))
    probability, state = max(outcomes, key=lambda o: o[0])
    kingambit = state.side_one.pokemon[1]
    # The log shows Kingambit at 66/100 after Make It Rain and Leftovers.
    assert showdown_percent(kingambit) == 66
    assert state.side_one.active_index == "1"
    assert state.side_two.pokemon[0].terastallized


def test_outcome_probabilities_sum_to_one():
    outcomes = simulate(turn_one(), Action("switch", 2), Action("move", 1, tera=True))
    assert len(outcomes) > 1  # the crit branch
    assert all(0 < p <= 1 for p, _ in outcomes)
    # poke-engine reports percentages as 32-bit floats, so the sum is only exact to about 1e-7.
    assert math.isclose(sum(p for p, _ in outcomes), 1.0, rel_tol=1e-6)


def test_input_state_is_not_changed():
    state = turn_one()
    simulate(state, Action("move", 2), Action("move", 1))
    assert state.side_two.pokemon[0].hp == 314
    assert not state.side_two.pokemon[0].terastallized


@pytest.mark.parametrize("slot, spa_boost", [(1, -1), (2, 0)])
def test_move_slot_picks_that_move(slot, spa_boost):
    # Slot 1 is Make It Rain, which always drops Gholdengo's SpA; slot 2 is Shadow Ball, which doesn't.
    outcomes = simulate(turn_one(), Action("switch", 2), Action("move", slot))
    assert all(state.side_two.special_attack_boost == spa_boost for _, state in outcomes)


def test_lead_is_not_a_turn_action():
    with pytest.raises(ValueError):
        simulate(turn_one(), Action("lead", 1), Action("move", 1))
