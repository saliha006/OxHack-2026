import math

import pytest
from poke_engine import Move, Pokemon, Side, State

from decision.actions import Action
from decision.simulate import simulate
from decision.value import value


def mon(hp=100):
    return Pokemon(id="kingambit", level=100, types=("dark", "steel"), hp=hp, maxhp=100, moves=[Move(id="ironhead")])


def team(*hps):
    return Side(pokemon=[mon(hp) for hp in hps])


def state(ours, theirs):
    return State(side_one=team(*ours), side_two=team(*theirs))


FULL = (100,) * 6


def test_two_full_teams_are_even():
    assert value(state(FULL, FULL)) == 0.5


def test_a_ko_counts_its_hp_and_its_life():
    # Losing a full-HP Pokémon costs 2 of the side's 12 points: (2/12) / 2 above even.
    assert math.isclose(value(state(FULL, (0, 100, 100, 100, 100, 100))), 0.5 + 1 / 12)


def test_chip_damage_counts_only_its_hp():
    assert math.isclose(value(state(FULL, (50, 100, 100, 100, 100, 100))), 0.5 + 0.5 / 24)


def test_value_is_symmetric():
    ours, theirs = (100, 40, 0, 100, 70, 10), (90, 0, 0, 100, 100, 25)
    assert math.isclose(value(state(ours, theirs)), 1 - value(state(theirs, ours)))


@pytest.mark.parametrize("ours, theirs, expected", [
    ((10, 0, 0, 0, 0, 0), (0,) * 6, 1.0),
    ((0,) * 6, (10, 0, 0, 0, 0, 0), 0.0),
    ((0,) * 6, (0,) * 6, 0.5),
])
def test_a_side_with_nothing_left_is_a_flat_result(ours, theirs, expected):
    assert value(state(ours, theirs)) == expected


def test_value_stays_between_zero_and_one():
    assert 0 < value(state((1, 0, 0, 0, 0, 0), FULL)) < 0.5 < value(state(FULL, (1, 0, 0, 0, 0, 0))) < 1


def test_fainted_slot_from_the_engine_counts_as_dead():
    # our_side() uses create_fainted() for fainted slots; poke-engine also pads every Side to 6 with them.
    ours = Side(pokemon=[mon() for _ in range(5)] + [Pokemon.create_fainted()])
    assert math.isclose(value(State(side_one=ours, side_two=team(*FULL))), 0.5 - 1 / 12)


def test_scores_a_simulated_turn():
    start = state((100,), (100,))
    outcomes = simulate(start, Action("move", 1), Action("move", 1))
    # Both Kingambit hit each other with the same move, so the expected value stays near even.
    expected = sum(p * value(s) for p, s in outcomes)
    assert 0.4 < expected < 0.6
