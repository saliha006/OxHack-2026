import json
import math

import pytest

from contracts.set_candidates import CandidateSet, SetCandidates, Species, Spread, Usage
from data.pipeline.build_set_candidates import (
    CHAOS, MAX_SETS, MOVES, build, forme_aliases, item_slots, parse_spread, to_id)

# A cut-down chaos entry: six moves (one status), a Choice item, Assault Vest, an empty move slot and "nothing" as an item.
CHAOS_SAMPLE = {
    "info": {"metagame": "gen9ou", "cutoff": 1825, "number of battles": 1000},
    "data": {"Samurott-Hisui": {
        "Abilities": {"sharpness": 90.0, "shelltoshell": 10.0},
        "Items": {"choiceband": 45.0, "focussash": 35.0, "assaultvest": 10.0, "nothing": 10.0},
        "Moves": {"ceaselessedge": 95.0, "razorshell": 90.0, "suckerpunch": 80.0, "aquajet": 60.0,
                  "swordsdance": 45.0, "knockoff": 25.0, "": 5.0},
        "Tera Types": {"dark": 70.0, "ghost": 30.0},
        "Spreads": {"Jolly:0/252/0/0/4/252": 80.0, "Adamant:252/252/0/0/4/0": 20.0},
    }},
}


def keys(typed_dict):
    return set(typed_dict.__annotations__)


def assert_contract_shape(data):
    assert set(data) == keys(SetCandidates)
    for species in data["species"].values():
        assert set(species) == keys(Species)
        assert set(species["usage"]) == keys(Usage)
        assert 1 <= len(species["sets"]) <= MAX_SETS
        assert math.isclose(sum(s["weight"] for s in species["sets"]), 1.0)
        weights = [s["weight"] for s in species["sets"]]
        assert weights == sorted(weights, reverse=True)
        for candidate in species["sets"]:
            assert set(candidate) == keys(CandidateSet)
            assert set(candidate["spread"]) == keys(Spread)
            assert len(candidate["spread"]["evs"]) == 6
            assert 1 <= len(candidate["moves"]) <= 4
            assert all(m in MOVES for m in candidate["moves"])


def test_ids_and_spreads_use_showdown_spellings():
    assert to_id("Samurott-Hisui") == "samurotthisui"
    assert to_id("Kommo-o") == "kommoo"
    assert parse_spread("Timid:0/0/0/252/4/252") == {"nature": "timid", "evs": [0, 0, 0, 252, 4, 252]}


def test_sample_matches_the_contract():
    result = build(CHAOS_SAMPLE, "2026-09")
    assert_contract_shape(result)
    assert result["source"] == {"format": "gen9ou", "month": "2026-09", "cutoff": 1825, "battles": 1000}
    assert list(result["species"]) == ["samurotthisui"]


def is_status(move):
    return MOVES[move]["category"] == "Status"


def test_assault_vest_never_carries_status_moves():
    chaos = json.loads(json.dumps(CHAOS_SAMPLE))
    chaos["data"]["Samurott-Hisui"]["Items"] = {"assaultvest": 100.0}
    sets = build(chaos, "2026-09")["species"]["samurotthisui"]["sets"]
    assert sets
    assert not any(is_status(m) for s in sets for m in s["moves"])


def test_choice_items_may_carry_status_moves():
    # Choice Scarf + Transform is Ditto's standard set; a Choice item only locks the move.
    chaos = {"info": CHAOS_SAMPLE["info"], "data": {"Ditto": {
        "Abilities": {"imposter": 100.0}, "Items": {"choicescarf": 97.0, "nothing": 3.0},
        "Moves": {"transform": 100.0, "": 300.0}, "Tera Types": {"normal": 100.0},
        "Spreads": {"Relaxed:248/0/252/0/8/0": 100.0}}}}
    sets = build(chaos, "2026-09")["species"]["ditto"]["sets"]
    assert sets[0]["item"] == "choicescarf" and sets[0]["moves"] == ["transform"]
    assert math.isclose(sum(s["weight"] for s in sets if s["item"] == "choicescarf"), 0.97)


def test_empty_slots_and_no_item_are_spelled_as_the_contract_says():
    species = build(CHAOS_SAMPLE, "2026-09")["species"]["samurotthisui"]
    assert "" not in species["usage"]["moves"]
    assert "" in species["usage"]["items"] and "nothing" not in species["usage"]["items"]
    assert math.isclose(species["usage"]["moves"]["ceaselessedge"], 0.95)


def test_most_likely_set_comes_first():
    best = build(CHAOS_SAMPLE, "2026-09")["species"]["samurotthisui"]["sets"][0]
    assert best["ability"] == "sharpness" and best["tera_type"] == "dark"
    assert best["spread"] == {"nature": "jolly", "evs": [0, 252, 0, 0, 4, 252]}


def test_slots_follow_item_shares():
    assert item_slots([0.5, 0.3, 0.2]) == [15, 9, 6]
    assert sum(item_slots([0.97, 0.02, 0.01])) == MAX_SETS
    assert min(item_slots([0.97, 0.02, 0.01])) >= 1


def test_each_item_keeps_its_usage_share():
    species = build(CHAOS_SAMPLE, "2026-09")["species"]["samurotthisui"]
    shares = {"choiceband": 0.45, "focussash": 0.35, "assaultvest": 0.10, "": 0.10}
    for item, share in shares.items():
        assert math.isclose(sum(s["weight"] for s in species["sets"] if s["item"] == item), share)


def test_battle_formes_borrow_their_base_species_sets():
    aliases = forme_aliases({"keldeo", "zamazenta", "maushold", "greninja", "ogerponwellspring", "slowking"})
    assert aliases["keldeoresolute"] == "keldeo"
    assert aliases["zamazentacrowned"] == "zamazenta"
    assert aliases["mausholdfour"] == "maushold"
    assert aliases["greninjaash"] == "greninja"  # via Greninja-Bond
    assert aliases["ogerponwellspringtera"] == "ogerponwellspring"


def test_regional_formes_never_borrow_another_pokemons_sets():
    assert "slowkinggalar" not in forme_aliases({"slowking"})


def test_unknown_move_fails_loudly():
    bad = json.loads(json.dumps(CHAOS_SAMPLE))
    bad["data"]["Samurott-Hisui"]["Moves"]["notamove"] = 1.0
    with pytest.raises(ValueError, match="notamove"):
        build(bad, "2026-09")


@pytest.mark.skipif(not CHAOS.exists(), reason="the chaos file is downloaded locally, not committed")
def test_real_chaos_file_covers_every_species():
    chaos = json.loads(CHAOS.read_text(encoding="utf-8"))
    result = build(chaos, "2026-09")
    assert_contract_shape(result)
    assert {to_id(name) for name in chaos["data"]} <= set(result["species"])
    assert result["species"]["keldeoresolute"] == result["species"]["keldeo"]
