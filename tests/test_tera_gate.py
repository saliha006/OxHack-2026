import copy

import pytest

from decision.actions import Action
from decision.agent import Agent
from decision.search_policy import gate_tera, pool_results
from tests.test_belief import PRIORS
from tests.turn2 import EXAMPLE, REQUEST

TERA_IRON_HEAD = Action("move", 4, tera=True)


def world(visits, error=None):
    return {"error": error, "our_visits": [{"choice": m, "visits": n} for m, n in visits.items()], "opponent_visits": []}


# Iron Head + Tera is every world's runner-up, so it tops the pooled average without topping any world.
RUNNER_UP = [world({"swordsdance": 50, "ironhead-tera": 45, "ironhead": 5}),
             world({"ironhead": 52, "ironhead-tera": 45, "swordsdance": 3})]


def gate(worlds, min_wins):
    pooled = pool_results(worlds, REQUEST)
    return pooled["action"], gate_tera(pooled["action"], pooled["search_support"], REQUEST, worlds, min_wins)


def test_a_tera_that_tops_no_world_falls_back_to_the_best_supported_plain_choice():
    pooled_pick, (action, record) = gate(RUNNER_UP, 1)
    assert pooled_pick == TERA_IRON_HEAD
    assert action == Action("move", 4) and record == {"top_in_worlds": 0, "min_wins": 1, "blocked": True}


def test_a_tera_that_tops_enough_worlds_is_kept_and_errored_worlds_do_not_count():
    worlds = [world({"ironhead-tera": 60, "ironhead": 40})] * 2 + [world({}, error={"stage": "native_search"})]
    _, (action, record) = gate(worlds, 2)
    assert action == TERA_IRON_HEAD and record["top_in_worlds"] == 2 and not record["blocked"]
    _, (action, record) = gate(worlds, 3)
    assert action == Action("move", 4) and record["blocked"]


def test_plain_choices_pass_untouched_and_a_tera_with_no_supported_alternative_stands():
    _, (action, record) = gate([world({"swordsdance": 9, "ironhead": 1})], 3)
    assert action == Action("move", 1) and not record["blocked"]
    alone = [world({"ironhead-tera": 10})]
    assert gate_tera(TERA_IRON_HEAD, {"move 4 terastallize": 1.0}, REQUEST, alone, 2)[0] == TERA_IRON_HEAD


def test_the_gate_is_off_by_default_and_only_takes_a_world_count_for_mcts():
    assert Agent(PRIORS).config["tera_min_wins"] == 0
    for bad in (-1, True, 1.5):
        with pytest.raises(ValueError, match="tera_min_wins"):
            Agent(PRIORS, tera_min_wins=bad)
    with pytest.raises(ValueError, match="tera_min_wins"):
        Agent(PRIORS, backend="one_ply", tera_min_wins=2)


def test_the_agent_plays_and_records_the_gated_choice(monkeypatch):
    import decision.search

    class FinishedWorker:
        generation = 0

        def __init__(self, priors):
            self.recorded = []

        def stream(self, request, battle, config, deadline):
            self.generation = 1
            yield {"kind": "prepared", "state_preparation_ms": 0}
            for index, w in enumerate(RUNNER_UP):
                yield {"kind": "world_started", "index": index}
                yield {"kind": "world", "result": {"index": index, **w, "total_visits": 100}}
            yield {"kind": "done", "scheduled_worlds": len(RUNNER_UP)}

        def chose(self, request, action, *, deadline):
            self.recorded.append(action)

    monkeypatch.setattr(decision.search, "SearchWorker", FinishedWorker)
    agent = Agent(PRIORS, mcts_worlds=2, search_ms=300, tera_min_wins=1)
    assert agent.choose(REQUEST, copy.deepcopy(EXAMPLE)) == "move 4"
    assert agent.worker.recorded == [Action("move", 4)]
    assert agent.last_trace["tera_gate"]["blocked"] is True
