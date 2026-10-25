import copy
import pytest

from decision.agent import Agent
from decision.actions import Action
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


def test_optional_mixing_keeps_preview_deterministic_and_sampling_seed_separate():
    agent = Agent(PRIORS, mix_root=True, seed=101, mix_seed=202)
    before = agent.mix_rng.getstate()
    assert agent.choose(load("team_preview_request"), copy.deepcopy(EXAMPLE)) == "team 123456"
    assert agent.mix_rng.getstate() == before
    assert agent.config["seed"] == 101 and agent.config["mix_seed"] == 202
    assert agent.config["randomisation"] is True
    assert agent.worker is None


def test_mixing_is_off_by_default_and_is_explicitly_mcts_only():
    assert Agent(PRIORS).mix_rng is None
    assert Agent(PRIORS).config["randomisation"] is False
    with pytest.raises(ValueError, match="MCTS-only"):
        Agent(PRIORS, backend="one_ply", mix_root=True)


def test_worker_replay_records_the_final_mixed_choice(monkeypatch):
    from tests.turn2 import REQUEST
    import decision.search

    class FinishedWorker:
        generation = 0

        def __init__(self, priors):
            self.recorded = []

        def stream(self, request, battle, config, deadline):
            self.generation = 1
            yield {"kind": "prepared", "state_preparation_ms": 0}
            for index in range(4):
                yield {"kind": "world_started", "index": index}
                yield {"kind": "world", "result": {
                    "index": index, "our_visits": [
                        {"choice": request["active"][0]["moves"][0]["id"], "visits": 5100},
                        {"choice": request["active"][0]["moves"][1]["id"], "visits": 4900}],
                    "opponent_visits": [], "total_visits": 10000}}
            yield {"kind": "done", "scheduled_worlds": 4}

        def chose(self, request, action, *, deadline):
            self.recorded.append(action)

    monkeypatch.setattr(decision.search, "SearchWorker", FinishedWorker)
    agent = Agent(PRIORS, mcts_worlds=4, search_ms=300, mix_root=True, mix_seed=2)
    assert agent.choose(REQUEST, copy.deepcopy(EXAMPLE)) == "move 2"
    assert agent.worker.recorded == [Action("move", 2)]
    assert agent.last_trace["root_mixing"]["original_choice"] == "move 1"
