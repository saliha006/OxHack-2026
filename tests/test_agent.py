import copy
import json
from pathlib import Path

from decision.actions import our_actions
from decision.agent import Agent, _as_move_request
from decision.belief import Belief
from tests.test_belief import PRIORS
from tests.turn2 import EXAMPLE, REQUEST

FIXTURES = Path(__file__).parent / "fixtures"


def load(name):
    return json.loads((FIXTURES / f"{name}.json").read_text())


def test_wait_sends_nothing():
    assert Agent(PRIORS).choose(load("wait_request"), copy.deepcopy(EXAMPLE)) is None


def test_team_preview_keeps_the_team_order():
    assert Agent(PRIORS).choose(load("team_preview_request"), copy.deepcopy(EXAMPLE)) == "team 123456"


def test_move_request_gives_a_legal_choice_and_records_it():
    agent = Agent(PRIORS)
    choice = agent.choose(REQUEST, copy.deepcopy(EXAMPLE))
    assert choice in {a.to_choice() for a in our_actions(REQUEST)}
    assert agent.belief.last_choice.to_choice() == choice


def test_finishes_off_a_nearly_fainted_opponent():
    battle = copy.deepcopy(EXAMPLE)
    battle["sides"]["p2"]["pokemon"][2]["hp_percent"] = 3
    choice = Agent(PRIORS).choose(REQUEST, battle)
    # Any attack KOs; Swords Dance (move 1) or a switch would leave it alive.
    assert choice.startswith("move") and not choice.startswith("move 1")


def test_the_same_turn_gives_the_same_choice():
    assert Agent(PRIORS).choose(REQUEST, copy.deepcopy(EXAMPLE)) == Agent(PRIORS).choose(REQUEST, copy.deepcopy(EXAMPLE))


def test_forced_switch_sends_the_pokemon_with_the_best_next_turn():
    # Judged by the models we have, not by intuition: under the uniform opponent policy a damaged Pokémon that can
    # Roost may score above a healthy one, since the opponent is expected to attack less than half the time.
    request = load("force_switch_request")
    battle = copy.deepcopy(EXAMPLE)
    agent = Agent(PRIORS)
    agent.belief = Belief(PRIORS, battle)
    agent.belief.update(battle)
    evs = {a.slot: agent._evaluate(_as_move_request(request, a.slot), battle)[1] for a in our_actions(request)}
    best = max(evs, key=evs.get)
    assert Agent(PRIORS).choose(request, copy.deepcopy(EXAMPLE)) == f"switch {best}"


def test_forced_switch_request_becomes_a_move_request_for_the_switch_in():
    hypothetical = _as_move_request(load("force_switch_request"), 5)
    assert "forceSwitch" not in hypothetical
    assert [m["active"] for m in hypothetical["side"]["pokemon"]] == [False, False, False, False, True, False]
    assert [m["id"] for m in hypothetical["active"][0]["moves"]] == ["bravebird", "defog", "roost", "uturn"]


def test_belief_carries_over_between_turns():
    agent = Agent(PRIORS)
    battle = copy.deepcopy(EXAMPLE)
    agent.choose(REQUEST, battle)
    first = agent.belief
    agent.choose(REQUEST, copy.deepcopy(battle))
    assert agent.belief is first


class FakeClock:
    """Time that jumps forward by `step` seconds every time it's read."""

    def __init__(self, step):
        self.now, self.step = 0.0, step

    def __call__(self):
        self.now += self.step
        return self.now


def test_out_of_time_uses_the_scenarios_already_finished():
    # Every clock read costs 10 s, so the 3 s budget is gone after the first (most likely) scenario.
    rushed = Agent(PRIORS, budget=3.0, clock=FakeClock(10.0)).choose(REQUEST, copy.deepcopy(EXAMPLE))
    top_scenario_only = Agent(PRIORS, k=1).choose(REQUEST, copy.deepcopy(EXAMPLE))
    assert rushed == top_scenario_only


def test_plenty_of_time_uses_every_scenario():
    relaxed = Agent(PRIORS, budget=3.0, clock=FakeClock(0.0)).choose(REQUEST, copy.deepcopy(EXAMPLE))
    assert relaxed == Agent(PRIORS).choose(REQUEST, copy.deepcopy(EXAMPLE))


def test_an_error_sends_the_first_legal_option_and_logs_it(monkeypatch, caplog):
    def broken(*args):
        raise RuntimeError("engine fell over")

    monkeypatch.setattr("decision.agent.build_state", broken)
    with caplog.at_level("ERROR", logger="decision"):
        choice = Agent(PRIORS).choose(REQUEST, copy.deepcopy(EXAMPLE))
    assert choice == our_actions(REQUEST)[0].to_choice()
    assert "engine fell over" in caplog.text
    assert "turn 2" in caplog.text


def test_if_even_the_legal_options_fail_it_sends_default(monkeypatch):
    def broken(*args):
        raise RuntimeError("bad request")

    monkeypatch.setattr("decision.agent.our_actions", broken)
    assert Agent(PRIORS).choose(REQUEST, copy.deepcopy(EXAMPLE)) == "default"


def test_after_an_error_the_next_turn_is_not_replayed(monkeypatch):
    agent = Agent(PRIORS)
    monkeypatch.setattr("decision.agent.build_state", lambda *a: (_ for _ in ()).throw(RuntimeError("x")))
    agent.choose(REQUEST, copy.deepcopy(EXAMPLE))
    # The failed turn's choice wasn't recorded, so belief won't replay a turn it never planned.
    assert agent.belief.last_choice is None
