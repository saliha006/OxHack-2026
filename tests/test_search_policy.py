import copy

import pytest

from decision.actions import Action, our_actions
from decision.search_policy import map_choice, pool_results
from tests.turn2 import REQUEST


def world(visits, *, weight=1, index=0, error=None):
    return {"index": index, "weight": weight, "error": error,
            "our_visits": [{"choice": m, "visits": n} for m, n in visits.items()],
            "opponent_visits": [{"choice": "shadowball", "visits": 10}]}


def test_sampled_occurrences_are_equal_weight_even_with_different_visits_and_priors():
    worlds = [world({"swordsdance": 90, "ironhead": 10}, weight=0.9),
              world({"swordsdance": 1, "ironhead": 9}, weight=0.1)]
    result = pool_results(worlds, REQUEST)
    assert result["search_support"] == pytest.approx({"move 1": 0.5, "move 4": 0.5})
    assert result["action"] == Action("move", 1)
    assert result["opponent_support"] == {"shadowball": 1}
    weighted = pool_results(worlds, REQUEST, mode="enumerated")
    assert weighted["search_support"] == pytest.approx({"move 1": 0.82, "move 4": 0.18})


def test_reordered_switch_maps_to_request_slot_not_preview_order():
    request = copy.deepcopy(REQUEST)
    request["side"]["pokemon"][1], request["side"]["pokemon"][4] = (
        request["side"]["pokemon"][4], request["side"]["pokemon"][1])
    species = request["side"]["pokemon"][1]["details"].split(",")[0]
    from decision.state import to_id
    assert map_choice("switch " + to_id(species), request) == Action("switch", 2)


def test_tera_and_disabled_options_are_filtered_then_renormalised():
    request = copy.deepcopy(REQUEST)
    request["active"][0]["moves"][0]["disabled"] = True
    request["active"][0].pop("canTerastallize", None)
    result = pool_results([world({"swordsdance": 40, "ironhead-tera": 40, "ironhead": 20})], request)
    assert result["search_support"] == {"move 4": 1}
    assert len(result["mapping_failures"]) == 2


def test_partial_failures_zero_visits_and_unknown_choices_do_not_erase_good_world():
    result = pool_results([world({}, error={"type": "PanicException"}), world({"ironhead": 0}),
                           world({"rejectedoption": 50}), world({"ironhead": 3})], REQUEST)
    assert result["usable_worlds"] == 1
    assert result["action"] == Action("move", 4)
    assert len(result["unusable_worlds"]) == 3


def test_struggle_maps_to_the_single_request_slot():
    request = copy.deepcopy(REQUEST)
    request["active"][0]["moves"] = [{"id": "struggle", "pp": 1}]
    result = pool_results([world({"struggle": 12})], request)
    assert result["action"] == Action("move", 1)
    assert result["action"] in our_actions(request)


def test_negative_nan_and_infinite_visits_are_not_support():
    result = pool_results([world({"ironhead": float("nan"), "swordsdance": -1,
                                 "kowtowcleave": float("inf")})], REQUEST)
    assert result["action"] is None
    assert result["unusable_worlds"][0]["reason"] == "zero_visits"


def test_all_filtered_returns_explicit_empty_support():
    result = pool_results([world({"No Move": 10})], REQUEST)
    assert result["action"] is None
    assert result["search_support"] == {}
    assert result["unusable_worlds"][0]["reason"] == "no_supported_legal_action"


def test_ambiguous_switch_is_rejected():
    request = copy.deepcopy(REQUEST)
    request["side"]["pokemon"][1]["details"] = request["side"]["pokemon"][0]["details"]
    assert map_choice("switch kingambit", request) is None
