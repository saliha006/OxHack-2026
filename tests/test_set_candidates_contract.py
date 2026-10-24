import json
import math
from pathlib import Path

from contracts.set_candidates import CandidateSet, SetCandidates, Source, Species, Spread, Usage

EXAMPLE = Path(__file__).parent.parent / "contracts" / "examples" / "set_candidates_example.json"


def keys(typed_dict):
    return set(typed_dict.__annotations__)


def test_example_has_exactly_the_contract_keys():
    data = json.loads(EXAMPLE.read_text())
    assert set(data) == keys(SetCandidates)
    assert set(data["source"]) == keys(Source)
    for species in data["species"].values():
        assert set(species) == keys(Species)
        assert set(species["usage"]) == keys(Usage)
        for candidate in species["sets"]:
            assert set(candidate) == keys(CandidateSet)
            assert set(candidate["spread"]) == keys(Spread)
            assert len(candidate["spread"]["evs"]) == 6


def test_weights_sum_to_one_per_species():
    data = json.loads(EXAMPLE.read_text())
    for species in data["species"].values():
        assert math.isclose(sum(s["weight"] for s in species["sets"]), 1.0)
