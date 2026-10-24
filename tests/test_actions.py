import json
from pathlib import Path

import pytest

from decision.actions import Action, our_actions

FIXTURES = Path(__file__).parent / "fixtures"


def load(name):
    return json.loads((FIXTURES / f"{name}.json").read_text())


@pytest.fixture
def move_request():
    request = load("move_request")
    del request["active"][0]["canTerastallize"]
    return request


def moves(actions):
    return [a for a in actions if a.kind == "move"]


def switches(actions):
    return [a for a in actions if a.kind == "switch"]


def test_move_request_offers_every_move_and_every_benched_switch(move_request):
    actions = our_actions(move_request)
    assert moves(actions) == [Action("move", n) for n in (1, 2, 3, 4)]
    assert switches(actions) == [Action("switch", n) for n in (2, 3, 4, 5, 6)]


def test_disabled_move_is_left_out(move_request):
    move_request["active"][0]["moves"][1]["disabled"] = True
    assert [a.slot for a in moves(our_actions(move_request))] == [1, 3, 4]


def test_disabled_can_be_a_reason_string(move_request):
    # Showdown sometimes puts the disabling effect's name in `disabled` instead of `true`.
    move_request["active"][0]["moves"][0]["disabled"] = "Taunt"
    assert [a.slot for a in moves(our_actions(move_request))] == [2, 3, 4]


def test_can_terastallize_adds_a_tera_copy_of_each_usable_move():
    request = load("move_request")
    request["active"][0]["moves"][3]["disabled"] = True
    tera = [a for a in moves(our_actions(request)) if a.tera]
    assert tera == [Action("move", n, tera=True) for n in (1, 2, 3)]


@pytest.mark.parametrize("flag", ["trapped", "maybeTrapped"])
def test_trapped_or_maybe_trapped_offers_no_switches(move_request, flag):
    move_request["active"][0][flag] = True
    assert switches(our_actions(move_request)) == []


def test_fainted_team_members_are_not_switch_targets(move_request):
    move_request["side"]["pokemon"][2]["condition"] = "0 fnt"
    assert [a.slot for a in switches(our_actions(move_request))] == [2, 4, 5, 6]


def test_locked_move_is_the_only_move(move_request):
    # Outrage lock / Struggle: Showdown sends just the one move, and trapped.
    move_request["active"][0] = {
        "moves": [{"move": "Struggle", "id": "struggle", "target": "randomNormal", "disabled": False}],
        "trapped": True,
    }
    assert our_actions(move_request) == [Action("move", 1)]


def test_forced_switch_offers_only_living_benched_pokemon():
    assert our_actions(load("force_switch_request")) == [Action("switch", n) for n in (2, 3, 5, 6)]


def test_wait_request_offers_nothing():
    assert our_actions(load("wait_request")) == []


def test_team_preview_offers_each_pokemon_as_lead():
    assert our_actions(load("team_preview_request")) == [Action("lead", n) for n in range(1, 7)]


@pytest.mark.parametrize(
    "action, choice",
    [
        (Action("move", 2), "move 2"),
        (Action("move", 2, tera=True), "move 2 terastallize"),
        (Action("switch", 4), "switch 4"),
        (Action("lead", 1), "team 123456"),
        (Action("lead", 3), "team 312456"),
        (Action("lead", 6), "team 612345"),
    ],
)
def test_to_choice(action, choice):
    assert action.to_choice() == choice
