import copy
import math

import pytest

from decision.actions import Action
from decision.adapter import build_public_state, build_state
from decision.opponent import opp_actions, public_actions, uniform_policy
from decision.simulate import simulate
from tests.turn2 import EXAMPLE, OUR_SETS, REQUEST, SETS

# Bob's living bench, in preview order (slot 3 is the active Gholdengo).
BENCH = [Action("switch", n) for n in (1, 2, 4, 5, 6)]


@pytest.fixture
def battle():
    return copy.deepcopy(EXAMPLE)


def actions(battle, sets=SETS):
    return opp_actions(build_state(REQUEST, battle, sets), battle)


def unlock(battle):
    # Revealed as holding nothing, so the guessed Choice Scarf doesn't apply.
    battle["sides"]["p2"]["pokemon"][2]["item"] = ""


def test_choice_locked_into_its_last_move(battle):
    # Turn 2 of the sample: Scarf Gholdengo used Make It Rain, so it's locked into slot 1 or switches.
    assert actions(battle) == [Action("move", 1)] + BENCH


def test_no_lock_without_a_choice_item(battle):
    unlock(battle)
    assert actions(battle) == [Action("move", n) for n in (1, 2, 3, 4)] + BENCH


def test_no_lock_before_it_has_moved(battle):
    battle["sides"]["p2"]["last_move"] = None
    assert actions(battle) == [Action("move", n) for n in (1, 2, 3, 4)] + BENCH


def test_tera_copies_while_their_tera_is_unused(battle):
    unlock(battle)
    battle["sides"]["p2"]["tera_used"] = False
    battle["sides"]["p2"]["pokemon"][2].update(terastallized=False)
    moves = [Action("move", n) for n in (1, 2, 3, 4)]
    assert actions(battle) == moves + [Action("move", n, tera=True) for n in (1, 2, 3, 4)] + BENCH


def test_taunt_removes_status_moves(battle):
    unlock(battle)
    battle["sides"]["p2"]["volatiles"] = ["taunt"]
    # Gholdengo's moves: Make It Rain, Shadow Ball, Nasty Plot (status), Recover (status).
    assert actions(battle) == [Action("move", 1), Action("move", 2)] + BENCH


def test_encore_keeps_only_the_last_move(battle):
    unlock(battle)
    battle["sides"]["p2"]["volatiles"] = ["encore"]
    battle["sides"]["p2"]["last_move"] = "shadowball"
    assert actions(battle) == [Action("move", 2)] + BENCH


def struggling(battle):
    # Encored into Nasty Plot while Taunted: no move is usable, so the game makes it Struggle.
    unlock(battle)
    battle["sides"]["p2"]["volatiles"] = ["encore", "taunt"]
    battle["sides"]["p2"]["last_move"] = "nastyplot"
    return battle


def test_no_usable_move_means_struggle(battle):
    state = build_state(REQUEST, struggling(battle), SETS)
    assert [m.id for m in state.side_two.pokemon[2].moves] == ["struggle"]
    assert opp_actions(state, battle) == [Action("move", 1)] + BENCH


def test_choice_locked_into_a_status_move_while_taunted_struggles(battle):
    battle["sides"]["p2"]["volatiles"] = ["taunt"]
    battle["sides"]["p2"]["last_move"] = "nastyplot"
    state = build_state(REQUEST, battle, SETS)
    assert [m.id for m in state.side_two.pokemon[2].moves] == ["struggle"]


def test_struggle_can_be_simulated(battle):
    request = copy.deepcopy(REQUEST)
    request["side"]["pokemon"][0]["item"] = ""  # no Leftovers, so the hit shows in our HP
    state = build_state(request, struggling(battle), SETS)
    outcomes = simulate(state, Action("move", 1), Action("move", 1))
    # poke-engine's gen9 Struggle is a 50 BP Normal move with no recoil (the real one is typeless, with 1/4 recoil).
    assert all(s.side_one.pokemon[0].hp < state.side_one.pokemon[0].hp for _, s in outcomes)


def test_benched_pokemon_keep_their_moves_while_the_active_struggles(battle):
    state = build_state(REQUEST, struggling(battle), SETS)
    assert len(state.side_two.pokemon[0].moves) == 4


def test_fainted_bench_is_not_a_switch_target(battle):
    battle["sides"]["p2"]["pokemon"][0]["hp_percent"] = 0
    assert actions(battle) == [Action("move", 1)] + BENCH[1:]


def test_uniform_policy_gives_each_move_and_switch_an_equal_share():
    policy = uniform_policy([Action("move", 1)] + BENCH)
    assert all(math.isclose(p, 1 / 6) for p in policy.values())


def test_tera_copy_splits_its_move_share():
    tera = [Action("move", 1), Action("move", 2), Action("move", 1, tera=True), Action("switch", 4)]
    policy = uniform_policy(tera)
    assert math.isclose(policy[Action("move", 1)], 1 / 6)
    assert math.isclose(policy[Action("move", 1, tera=True)], 1 / 6)
    assert math.isclose(policy[Action("move", 2)], 1 / 3)
    assert math.isclose(policy[Action("switch", 4)], 1 / 3)
    assert math.isclose(sum(policy.values()), 1.0)


def test_every_listed_action_can_be_simulated(battle):
    unlock(battle)
    battle["sides"]["p2"]["tera_used"] = False
    battle["sides"]["p2"]["pokemon"][2].update(terastallized=False)
    state = build_state(REQUEST, battle, SETS)
    for theirs in opp_actions(state, battle):
        assert simulate(state, Action("move", 4), theirs)


def test_encored_state_can_be_simulated(battle):
    # Regression: poke-engine panics on Encore unless the side's last used move is set.
    unlock(battle)
    battle["sides"]["p2"]["volatiles"] = ["encore"]
    battle["sides"]["p2"]["last_move"] = "shadowball"
    state = build_state(REQUEST, battle, SETS)
    assert state.side_two.last_used_move == "move:1"
    assert simulate(state, Action("move", 4), Action("move", 2))


def test_public_actions_list_our_side_from_the_battle_state(battle):
    state = build_public_state(battle, OUR_SETS, SETS)
    moves = [Action("move", n) for n in range(1, 5)]
    tera = [Action("move", n, tera=True) for n in range(1, 5)]
    assert public_actions(state, battle, "p1") == moves + tera + [Action("switch", n) for n in range(1, 6)]
