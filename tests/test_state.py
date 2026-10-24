import json
from pathlib import Path

import pytest
from poke_engine import Move, Pokemon, Side, State

from decision.actions import Action
from decision.simulate import simulate
from decision.state import our_side

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def request_():
    return json.loads((FIXTURES / "move_request.json").read_text())


def test_team_is_built_in_request_order(request_):
    side = our_side(request_)
    assert [p.id for p in side.pokemon] == [
        "kingambit", "greattusk", "gholdengo", "dragapult", "corviknight", "ironvaliant",
    ]
    assert side.active_index == "0"


def test_active_pokemon_carries_the_request_details(request_):
    kingambit = our_side(request_).pokemon[0]
    assert kingambit.types == ("dark", "steel")
    assert kingambit.weight_kg == 120
    assert (kingambit.hp, kingambit.maxhp) == (300, 400)
    assert (kingambit.attack, kingambit.defense, kingambit.special_attack,
            kingambit.special_defense, kingambit.speed) == (300, 250, 150, 220, 200)
    assert kingambit.item == "leftovers"
    assert kingambit.ability == "supremeoverlord"
    assert kingambit.tera_type == "dark"
    assert not kingambit.terastallized
    assert [(m.id, m.pp) for m in kingambit.moves] == [
        ("swordsdance", 16), ("kowtowcleave", 16), ("suckerpunch", 16), ("ironhead", 16),
    ]


def test_active_index_follows_the_active_flag(request_):
    team = request_["side"]["pokemon"]
    team[0]["active"], team[2]["active"] = False, True
    assert our_side(request_).active_index == "2"


@pytest.mark.parametrize("code, status", [
    ("brn", "burn"), ("par", "paralyze"), ("slp", "sleep"), ("frz", "freeze"), ("psn", "poison"), ("tox", "toxic"),
])
def test_status_is_read_from_condition(request_, code, status):
    request_["side"]["pokemon"][1]["condition"] = f"200/380 {code}"
    tusk = our_side(request_).pokemon[1]
    assert (tusk.hp, tusk.status) == (200, status)


def test_fainted_pokemon_keeps_its_slot_with_zero_hp(request_):
    request_["side"]["pokemon"][3]["condition"] = "0 fnt"
    side = our_side(request_)
    assert len(side.pokemon) == 6
    assert side.pokemon[3].hp == 0


def test_level_comes_from_details(request_):
    request_["side"]["pokemon"][1]["details"] = "Great Tusk, L84"
    request_["side"]["pokemon"][2]["details"] = "Gholdengo"
    side = our_side(request_)
    assert (side.pokemon[1].level, side.pokemon[2].level) == (84, 100)


def test_forme_is_looked_up_by_its_own_species(request_):
    request_["side"]["pokemon"][1]["details"] = "Samurott-Hisui, L100, F"
    samurott = our_side(request_).pokemon[1]
    assert samurott.id == "samurotthisui"
    assert samurott.types == ("water", "dark")


def test_terastallized_pokemon_is_marked(request_):
    request_["side"]["pokemon"][0]["terastallized"] = "Dark"
    request_["side"]["pokemon"][0]["details"] = "Kingambit, L100, F, tera:Dark"
    kingambit = our_side(request_).pokemon[0]
    assert kingambit.terastallized
    assert kingambit.id == "kingambit"


def test_locked_active_has_only_the_requested_move(request_):
    # Move slots index active[0].moves, so a locked request's single move must be the engine's move 1 too.
    request_["active"][0] = {"moves": [{"move": "Sucker Punch", "id": "suckerpunch", "pp": 5, "maxpp": 8,
                                        "target": "normal", "disabled": False}], "trapped": True}
    assert [(m.id, m.pp) for m in our_side(request_).pokemon[0].moves] == [("suckerpunch", 5)]


def test_benched_moves_come_from_the_team_list(request_):
    tusk = our_side(request_).pokemon[1]
    assert [m.id for m in tusk.moves] == ["headlongrush", "icespinner", "rapidspin", "knockoff"]


def test_side_from_a_request_can_be_simulated(request_):
    gholdengo = Pokemon(id="gholdengo", level=100, types=("steel", "ghost"), hp=314, maxhp=314,
        special_attack=365, speed=303, moves=[Move(id="makeitrain")])
    state = State(side_one=our_side(request_), side_two=Side(pokemon=[gholdengo]))
    outcomes = simulate(state, Action("move", 4), Action("move", 1))
    # Iron Head (slot 4) is Steel into Steel/Ghost: resisted, but it lands.
    assert all(s.side_two.pokemon[0].hp < 314 for _, s in outcomes)
