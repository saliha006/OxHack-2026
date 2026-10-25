"""SetCandidates: the data layer's per-species set file that the decision layer's belief loads. Spec: contracts/set-candidates.md."""
from typing import NotRequired, TypedDict


class Spread(TypedDict):
    nature: str               # Showdown ID, e.g. "timid"
    evs: list[int]            # [hp, atk, def, spa, spd, spe]


class CandidateSet(TypedDict):
    weight: float             # prior probability within its species; a species' weights sum to 1
    moves: list[str]          # 1-4 Showdown move IDs
    item: str                 # Showdown item ID; "" = no item
    ability: str
    tera_type: str            # lowercase type, e.g. "steel"
    spread: Spread
    ivs: NotRequired[list[int]]  # optional [hp, atk, def, spa, spd, spe]; old usage files default to 31


class Usage(TypedDict):
    # Trimmed chaos counts as shares, for rebuilding sets when no candidate fits what's been revealed.
    moves: dict[str, float]       # share of sets that run the move (sums to about 4)
    items: dict[str, float]       # each category below sums to about 1
    abilities: dict[str, float]
    tera_types: dict[str, float]
    spreads: list[tuple[Spread, float]]


class Species(TypedDict):
    sets: list[CandidateSet]  # at most 30, highest weight first
    usage: Usage


class Source(TypedDict):
    format: str               # "gen9ou"
    month: str                # chaos month, "2026-09"
    cutoff: int               # rating band, 1825
    battles: int              # "number of battles" in the chaos file's info block


class SetCandidates(TypedDict):
    source: Source
    species: dict[str, Species]  # keyed by Showdown species ID, formes separate ("samurotthisui")
