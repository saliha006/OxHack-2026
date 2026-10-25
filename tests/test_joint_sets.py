import json
import math
from pathlib import Path

from contracts.set_candidates import CandidateSet, Species, Spread, Usage
from data.pipeline import joint_sets

GAMBIT = "dark|supremeoverlord|blackglasses|adamant|0,252,4,0,0,252|ironhead|kowtowcleave|suckerpunch|swordsdance"
USAGE_SET = {"weight": 1.0, "moves": ["suckerpunch", "swordsdance", "ironhead", "lowkick"], "item": "leftovers",
             "ability": "supremeoverlord", "tera_type": "bug", "spread": {"nature": "adamant", "evs": [248, 252, 8, 0, 0, 0]}}
USAGE = {"moves": {"suckerpunch": 1.0}, "items": {"leftovers": 1.0}, "abilities": {"supremeoverlord": 1.0},
         "tera_types": {"bug": 1.0}, "spreads": [[{"nature": "adamant", "evs": [248, 252, 8, 0, 0, 0]}, 1.0]]}


def keys(typed_dict):
    return set(typed_dict.__required_keys__)


def test_observed_sets_parse_with_count_weights_and_drop_sets_missing_tera_or_a_full_spread():
    sets = joint_sets.observed_sets({GAMBIT: 3, "dark|supremeoverlord|leftovers|adamant|0,252|suckerpunch": 5,
                                     "|supremeoverlord|leftovers|adamant|0,252,4,0,0,252|suckerpunch": 5,
                                     "fairy|supremeoverlord||jolly|0,252,4,0,0,252|suckerpunch": 1})
    assert [(s["item"], s["tera_type"], round(s["weight"], 2)) for s in sets] == [("blackglasses", "dark", 0.75), ("", "fairy", 0.25)]
    assert sets[0]["spread"] == {"nature": "adamant", "evs": [0, 252, 4, 0, 0, 252]}


def test_blend_gives_observed_sets_three_quarters_merges_the_same_set_and_renormalises():
    same_as_usage = {**USAGE_SET, "moves": list(reversed(USAGE_SET["moves"]))}
    blended = joint_sets.blend([USAGE_SET], [{**joint_sets.observed_sets({GAMBIT: 1})[0], "weight": 0.5},
                                             {**same_as_usage, "weight": 0.5}])
    assert [round(s["weight"], 3) for s in blended] == [0.625, 0.375]
    assert (blended[0]["item"], blended[1]["item"]) == ("leftovers", "blackglasses")


def test_blend_keeps_at_most_thirty_sets():
    many = [{**USAGE_SET, "tera_type": f"t{i}", "weight": 1 / 40} for i in range(40)]
    blended = joint_sets.blend([], many)
    assert len(blended) == 30 and math.isclose(sum(s["weight"] for s in blended), 1.0)


def test_build_blends_known_species_and_adds_observed_only_ones_with_usage_in_contract_shape():
    candidates = {"source": {"format": "gen9ou"}, "species": {"kingambit": {"sets": [USAGE_SET], "usage": USAGE},
                                                              "untouched": {"sets": [USAGE_SET], "usage": USAGE}}}
    built = joint_sets.build(candidates, {"kingambit": {GAMBIT: 2}, "archaludon": {GAMBIT.replace("dark", "fairy"): 4}})
    assert built["species"]["untouched"] == candidates["species"]["untouched"]
    assert built["species"]["kingambit"]["sets"][0]["item"] == "blackglasses"
    new = built["species"]["archaludon"]
    assert set(new) == keys(Species) and set(new["usage"]) == keys(Usage)
    assert new["usage"]["tera_types"] == {"fairy": 1.0} and new["usage"]["moves"]["kowtowcleave"] == 1.0
    for candidate in new["sets"]:
        assert set(candidate) == keys(CandidateSet) and set(candidate["spread"]) == keys(Spread)


def test_main_writes_the_blended_file(tmp_path):
    (tmp_path / "c.json").write_text(json.dumps({"source": {}, "species": {"kingambit": {"sets": [USAGE_SET], "usage": USAGE}}}))
    (tmp_path / "f.json").write_text(json.dumps({"kingambit": {GAMBIT: 1}}))
    joint_sets.main(["--candidates", str(tmp_path / "c.json"), "--full-sets", str(tmp_path / "f.json"), "--out", str(tmp_path / "o.json")])
    assert len(json.loads((tmp_path / "o.json").read_text())["species"]["kingambit"]["sets"]) == 2


def test_the_committed_joint_file_keeps_the_contract_for_every_species():
    data = json.loads((Path(__file__).parent.parent / "data" / "set_candidates_joint.json").read_text(encoding="utf-8"))
    for species in data["species"].values():
        assert set(species) == keys(Species) and set(species["usage"]) == keys(Usage)
        assert math.isclose(sum(s["weight"] for s in species["sets"]), 1.0) and 1 <= len(species["sets"]) <= 30
