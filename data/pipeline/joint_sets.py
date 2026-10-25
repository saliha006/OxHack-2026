"""Blend observed complete sets into the usage candidates, written as a second set-candidates file.

Foul Play's gen9ou `pokemon_full_sets.json` (from data.foulplay.cc) counts whole sets seen on the ladder:
"tera|ability|item|nature|hp,atk,def,spa,spd,spe|move|...". Usage marginals pick each field independently, so they
also build sets nobody brings; observed sets keep moves, item, Tera and spread together.

    uv run python -m data.pipeline.joint_sets
"""
import argparse
import json
from collections import Counter
from pathlib import Path

SOURCE = Path("foul-play/fp/data/pkmn_sets_cache/gen9ou/pokemon_full_sets.json")
# Foul Play's own split between its observed sets and usage sets. Weights inside each stay count-based: equal
# weights per template over-concentrated the first coherent mixture (docs/coherent-sets-v2-results on Kenar-coherent-v2).
OBSERVED_SHARE = 0.75
MAX_SETS = 30


def observed_sets(counts: dict[str, int]) -> list[dict]:
    """Parsed sets with count-share weights; a set missing its Tera type or a full spread can't be built, so it's dropped."""
    sets = []
    for key, count in counts.items():
        tera, ability, item, nature, evs, *moves = key.split("|")
        spread = evs.split(",")
        if tera and moves and len(spread) == 6:
            sets.append({"weight": count, "moves": moves, "item": item, "ability": ability, "tera_type": tera,
                         "spread": {"nature": nature, "evs": [int(x) for x in spread]}})
    total = sum(s["weight"] for s in sets)
    return [{**s, "weight": s["weight"] / total} for s in sets]


def _identity(s: dict) -> tuple:
    return (frozenset(s["moves"]), s["item"], s["ability"], s["tera_type"], s["spread"]["nature"], tuple(s["spread"]["evs"]))


def blend(usage_sets: list[dict], observed: list[dict]) -> list[dict]:
    merged = {}
    for share, sets in ((OBSERVED_SHARE, observed), (1 - OBSERVED_SHARE, usage_sets)):
        for s in sets:
            key = _identity(s)
            if key in merged:
                merged[key]["weight"] += share * s["weight"]
            else:
                merged[key] = {**s, "weight": share * s["weight"]}
    best = sorted(merged.values(), key=lambda s: -s["weight"])[:MAX_SETS]
    total = sum(s["weight"] for s in best)
    return [{**s, "weight": s["weight"] / total} for s in best]


def usage_from(sets: list[dict]) -> dict:
    """Usage shares for a species only the observed sets know, so belief can still rebuild when nothing fits."""
    def shares(field):
        tally = Counter()
        for s in sets:
            tally[field(s)] += s["weight"]
        return dict(tally)
    moves = Counter()
    for s in sets:
        for move in s["moves"]:
            moves[move] += s["weight"]
    spreads = Counter()
    for s in sets:
        spreads[(s["spread"]["nature"], tuple(s["spread"]["evs"]))] += s["weight"]
    return {"moves": dict(moves), "items": shares(lambda s: s["item"]), "abilities": shares(lambda s: s["ability"]),
            "tera_types": shares(lambda s: s["tera_type"]),
            "spreads": [({"nature": n, "evs": list(evs)}, w) for (n, evs), w in spreads.most_common()]}


def build(candidates: dict, full_sets: dict[str, dict[str, int]]) -> dict:
    species = {}
    for name, entry in candidates["species"].items():
        observed = observed_sets(full_sets.get(name, {}))
        species[name] = {**entry, "sets": blend(entry["sets"], observed)} if observed else entry
    for name in full_sets.keys() - candidates["species"].keys():
        observed = observed_sets(full_sets[name])
        if observed:
            best = sorted(observed, key=lambda s: -s["weight"])[:MAX_SETS]
            total = sum(s["weight"] for s in best)
            species[name] = {"sets": [{**s, "weight": s["weight"] / total} for s in best], "usage": usage_from(observed)}
    return {"source": candidates["source"], "species": species}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--candidates", type=Path, default=Path("data/set_candidates.json"))
    parser.add_argument("--full-sets", type=Path, default=SOURCE)
    parser.add_argument("--out", type=Path, default=Path("data/set_candidates_joint.json"))
    args = parser.parse_args(argv)
    candidates = json.loads(args.candidates.read_text(encoding="utf-8"))
    full_sets = json.loads(args.full_sets.read_text(encoding="utf-8"))
    args.out.write_text(json.dumps(build(candidates, full_sets)), encoding="utf-8")


if __name__ == "__main__":
    main()
