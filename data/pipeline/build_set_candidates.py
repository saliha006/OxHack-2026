"""Builds data/set_candidates.json (contracts/set-candidates.md) from one Smogon chaos file."""
import argparse
import json
import re
from itertools import combinations, product
from math import prod
from pathlib import Path

from contracts.set_candidates import CandidateSet, SetCandidates, Species, Spread, Usage

ROOT = Path(__file__).resolve().parents[2]
CHAOS = ROOT / "data" / "raw" / "chaos" / "2026-09-gen9ou-1825.json"
OUT = ROOT / "data" / "set_candidates.json"

# The decision layer's snapshot of Showdown's moves.json: it looks up every move we emit, so sets only use moves it knows.
MOVES = json.loads((ROOT / "decision" / "data" / "moves.json").read_text(encoding="utf-8"))

MAX_SETS = 30
# How deep each category goes when sets are combined: the top moves (4 per set), items, abilities, Tera types, spreads.
POOL_MOVES, POOL_ITEMS, POOL_ABILITIES, POOL_TERAS, POOL_SPREADS = 8, 4, 2, 3, 3
# How much of each category the usage block keeps for belief's rebuild fallback.
USAGE_MOVES, USAGE_OTHER = 10, 5


def to_id(name: str) -> str:
    """Showdown's toID: "Samurott-Hisui" -> "samurotthisui"."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def parse_spread(spread: str) -> Spread:
    """Chaos spreads are "Nature:hp/atk/def/spa/spd/spe"."""
    nature, evs = spread.split(":")
    return Spread(nature=to_id(nature), evs=[int(ev) for ev in evs.split("/")])


def top(shares: dict[str, float], n: int) -> list[tuple[str, float]]:
    return sorted(shares.items(), key=lambda kv: -kv[1])[:n]


def move_sets(moves: dict[str, float]) -> list[tuple[tuple[str, ...], float]]:
    """Every 4 of the top moves, each move in or out independently with its share as the chance it's in."""
    pool = top(moves, POOL_MOVES)
    if len(pool) <= 4:
        return [(tuple(m for m, _ in pool), 1.0)]
    return [(tuple(m for m, _ in pool if m in chosen),
             prod(min(p, 1.0) if m in chosen else 1.0 - min(p, 1.0) for m, p in pool))
            for chosen in map(set, combinations([m for m, _ in pool], 4))]


def item_slots(shares: list[float]) -> list[int]:
    """Splits the MAX_SETS slots between items by share (largest remainder), at least one each."""
    quotas = [MAX_SETS * s / sum(shares) for s in shares]
    slots = [max(1, int(q)) for q in quotas]
    # The one-each floor can overshoot; take the excess back from the biggest items.
    while sum(slots) > MAX_SETS:
        slots[slots.index(max(slots))] -= 1
    by_remainder = sorted(range(len(shares)), key=lambda i: -(quotas[i] - int(quotas[i])))
    for i in by_remainder[:max(0, MAX_SETS - sum(slots))]:
        slots[i] += 1
    return slots


def species_entry(name: str, counts: dict) -> Species:
    total = sum(counts["Abilities"].values())  # the species' weighted battle count; every category is a share of it
    share = lambda category: {k: v / total for k, v in counts[category].items()}
    # "" is an empty move slot; it isn't a move the decision layer can look up.
    moves = {m: s for m, s in share("Moves").items() if m}
    unknown = set(moves) - set(MOVES)
    if unknown:
        raise ValueError(f"{name}: moves missing from decision/data/moves.json: {sorted(unknown)}")
    # Chaos spells "no item" as "nothing"; the contract spells it "".
    items = {("" if i == "nothing" else i): s for i, s in share("Items").items()}
    abilities, teras = share("Abilities"), share("Tera Types")
    spreads = [(parse_spread(sp), s) for sp, s in top(share("Spreads"), max(POOL_SPREADS, USAGE_OTHER))]

    combos = move_sets(moves)
    by_item = {}
    for item, pi in top(items, POOL_ITEMS):
        # Assault Vest blocks status moves. Choice items don't (Choice Scarf + Trick is a staple); they only lock the move.
        allowed = [(ms, pm) for ms, pm in combos
                   if item != "assaultvest" or all(MOVES[m]["category"] != "Status" for m in ms)]
        allowed_weight = sum(pm for _, pm in allowed)
        if allowed_weight:
            candidates = [(pm / allowed_weight * pa * pt * ps, ms, item, ability, tera, spread)
                          for (ms, pm), (ability, pa), (tera, pt), (spread, ps) in product(
                              allowed, top(abilities, POOL_ABILITIES), top(teras, POOL_TERAS), spreads[:POOL_SPREADS])]
            by_item[item] = (pi, sorted(candidates, key=lambda s: -s[0]))
    if not by_item:
        raise ValueError(f"{name}: every combined set broke a consistency rule")

    sets = []
    for item, (pi, candidates), slots in zip(by_item, by_item.values(), item_slots([pi for pi, _ in by_item.values()])):
        # Each item keeps its usage share however few of its sets fit, so the cut to 30 can't crowd out a common item.
        kept = candidates[:slots]
        kept_weight = sum(w for w, *_ in kept)
        sets += [(pi * w / kept_weight, *rest) for w, *rest in kept]
    sets.sort(key=lambda s: -s[0])
    weight = sum(s[0] for s in sets)

    rounded = lambda pairs: {k: round(v, 4) for k, v in pairs}
    return Species(
        sets=[CandidateSet(weight=w / weight, moves=list(ms), item=item, ability=ability, tera_type=tera, spread=spread)
              for w, ms, item, ability, tera, spread in sets],
        usage=Usage(moves=rounded(top(moves, USAGE_MOVES)), items=rounded(top(items, USAGE_OTHER)),
                    abilities=rounded(top(abilities, USAGE_OTHER)), tera_types=rounded(top(teras, USAGE_OTHER)),
                    spreads=[(sp, round(s, 4)) for sp, s in spreads[:USAGE_OTHER]]))


def build(chaos: dict, month: str) -> SetCandidates:
    info = chaos["info"]
    return SetCandidates(
        source={"format": info["metagame"], "month": month, "cutoff": info["cutoff"],
                "battles": info["number of battles"]},
        species={to_id(name): species_entry(name, counts) for name, counts in chaos["data"].items()})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chaos", type=Path, default=CHAOS)
    parser.add_argument("--month", default="2026-09")
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    result = build(json.loads(args.chaos.read_text(encoding="utf-8")), args.month)
    args.out.write_text(json.dumps(result, indent=1), encoding="utf-8")
    sets = sum(len(s["sets"]) for s in result["species"].values())
    print(f"{args.out}: {len(result['species'])} species, {sets} sets")


if __name__ == "__main__":
    main()
