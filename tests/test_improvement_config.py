import copy

from decision.agent import Agent
from tests.test_agent import load
from tests.test_belief import PRIORS
from tests.turn2 import EXAMPLE


def test_historical_leads_remain_default_and_deliberate_fixed_lead_is_legal():
    request = load("team_preview_request")
    assert Agent(PRIORS).config["lead_policy"] == "types"
    agent = Agent(PRIORS, fixed_lead=3)
    assert agent.choose(request, copy.deepcopy(EXAMPLE)) == "team 312456"
    assert agent.last_trace["lead"] == {"policy": "fixed", "chosen_slot": 3}


def test_experimental_lead_is_explicit_and_traced_without_native_work():
    request = load("team_preview_request")
    agent = Agent(PRIORS, lead_policy="moves_stats")
    choice = agent.choose(request, copy.deepcopy(EXAMPLE))
    assert choice.startswith("team ")
    assert agent.last_trace["lead"]["policy"] == "moves_stats_v1"
    assert agent.last_trace["lead"]["historical_choice"] == "team 123456"
    assert agent.last_trace["requested_worlds"] == 0
    assert agent.worker is None
