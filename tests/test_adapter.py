import copy

import pytest

from decision.actions import Action
from decision.adapter import build_state
from decision.sets import stats
from decision.simulate import simulate
from tests.turn2 import EXAMPLE, REQUEST, SETS, guess


@pytest.fixture
def battle():
    return copy.deepcopy(EXAMPLE)


def theirs(state):
    return state.side_two


def test_our_side_comes_from_the_request(battle):
    state = build_state(REQUEST, battle, SETS)
    assert state.side_one.pokemon[0].id == "kingambit"
    assert (state.side_one.pokemon[0].hp, state.side_one.pokemon[0].maxhp) == (300, 400)


def test_opponent_team_is_in_preview_order_with_the_active_slot(battle):
    side = theirs(build_state(REQUEST, battle, SETS))
    assert [p.id for p in side.pokemon] == ["dragonite", "samurotthisui", "gholdengo", "pecharunt", "walkingwake", "tinglu"]
    assert side.active_index == "2"


def test_opponent_stats_come_from_the_set(battle):
    gholdengo = theirs(build_state(REQUEST, battle, SETS)).pokemon[2]
    maxhp, atk, dfn, spa, spd, spe = stats("gholdengo", 100, SETS[2])
    assert (gholdengo.maxhp, gholdengo.attack, gholdengo.special_attack, gholdengo.speed) == (maxhp, atk, spa, spe)
    assert gholdengo.types == ("steel", "ghost")


def test_revealed_moves_come_first(battle):
    gholdengo = theirs(build_state(REQUEST, battle, SETS)).pokemon[2]
    assert [m.id for m in gholdengo.moves] == ["makeitrain", "shadowball", "nastyplot", "recover"]


def test_revealed_tera_overrides_the_set(battle):
    gholdengo = theirs(build_state(REQUEST, battle, SETS)).pokemon[2]
    assert (gholdengo.tera_type, gholdengo.terastallized) == ("steel", True)


def test_revealed_item_and_ability_override_the_set(battle):
    dragonite = battle["sides"]["p2"]["pokemon"][0]
    dragonite["item"], dragonite["ability"] = "", "innerfocus"
    mon = theirs(build_state(REQUEST, battle, SETS)).pokemon[0]
    assert (mon.item, mon.ability) == ("none", "innerfocus")


def test_unrevealed_details_come_from_the_set(battle):
    mon = theirs(build_state(REQUEST, battle, SETS)).pokemon[1]
    assert (mon.item, mon.ability, mon.tera_type) == ("focussash", "sharpness", "normal")


def test_opponent_hp_is_percent_of_max_hp(battle):
    battle["sides"]["p2"]["pokemon"][2]["hp_percent"] = 60
    gholdengo = theirs(build_state(REQUEST, battle, SETS)).pokemon[2]
    assert gholdengo.hp == round(0.6 * gholdengo.maxhp)


def test_fainted_opponent_keeps_its_slot(battle):
    battle["sides"]["p2"]["pokemon"][1]["hp_percent"] = 0
    side = theirs(build_state(REQUEST, battle, SETS))
    assert side.pokemon[1].hp == 0
    assert side.pokemon[2].id == "gholdengo"


def test_status_and_its_counters(battle):
    battle["sides"]["p2"]["pokemon"][2].update(status="tox", status_turns=3)
    battle["sides"]["p2"]["pokemon"][4].update(status="slp", status_turns=1)
    side = theirs(build_state(REQUEST, battle, SETS))
    assert side.pokemon[2].status == "toxic"
    assert side.side_conditions.toxic_count == 3
    assert (side.pokemon[4].status, side.pokemon[4].sleep_turns) == ("sleep", 1)


def test_boosts_volatiles_and_substitute(battle):
    battle["sides"]["p2"]["volatiles"] = ["substitute", "taunt"]
    side = theirs(build_state(REQUEST, battle, SETS))
    assert side.special_attack_boost == -1
    assert side.volatile_statuses == {"substitute", "taunt"}
    # A fresh Substitute has a quarter of max HP; damage to it isn't in BattleState, so it's assumed full.
    assert side.substitute_health == side.pokemon[2].maxhp // 4


def test_hazards_and_timed_side_effects(battle):
    battle["sides"]["p1"]["hazards"].update(stealthrock=1, spikes=2)
    battle["sides"]["p1"]["side_effects"] = {"reflect": 2, "tailwind": 1}
    ours = build_state(REQUEST, battle, SETS).side_one.side_conditions
    assert (ours.stealth_rock, ours.spikes, ours.toxic_spikes) == (1, 2, 0)
    # Elapsed turns become turns left, assuming default lengths (Reflect 5, Tailwind 4).
    assert (ours.reflect, ours.tailwind) == (3, 3)


def test_field(battle):
    battle["field"] = {"weather": "sunnyday", "weather_turns": 2, "terrain": "electricterrain",
                       "terrain_turns": 1, "effects": {"trickroom": 3}}
    state = build_state(REQUEST, battle, SETS)
    assert (state.weather, state.weather_turns_remaining) == ("sun", 3)
    assert (state.terrain, state.terrain_turns_remaining) == ("electricterrain", 4)
    assert (state.trick_room, state.trick_room_turns_remaining) == (True, 2)


def test_we_can_be_p2(battle):
    battle["us"] = "p2"
    state = build_state(REQUEST, battle, [guess("tackle")] * 6)
    assert state.side_one.pokemon[0].id == "kingambit"   # still the request's team
    assert state.side_two.pokemon[0].id == "meowscarada"  # p1 is now the opponent
    assert state.side_two.active_index == "5"


def test_built_state_can_be_simulated(battle):
    state = build_state(REQUEST, battle, SETS)
    # Iron Head (our slot 4) against Gholdengo's Make It Rain (its slot 1, revealed first).
    outcomes = simulate(state, Action("move", 4), Action("move", 1))
    assert all(s.side_two.pokemon[2].hp < state.side_two.pokemon[2].hp for _, s in outcomes)


def test_a_missing_set_is_an_error(battle):
    with pytest.raises(ValueError):
        build_state(REQUEST, battle, SETS[:5])
