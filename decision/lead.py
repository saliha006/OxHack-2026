import json
import math
from pathlib import Path

from contracts.battle_state import BattleState
from decision.actions import Action
from decision.state import DEX, to_id

# Showdown's typechart (play.pokemonshowdown.com/data/typechart.js), snapshot of 2026-10-24, trimmed to
# defending type -> attacking type -> Showdown's damageTaken code.
TYPECHART = json.loads((Path(__file__).parent / "data" / "typechart.json").read_text())
MULTIPLIER = {0: 1.0, 1: 2.0, 2: 0.5, 3: 0.0}
# An immunity counts as a double resist, so one immune foe can't swamp the average with -inf.
FLOOR = 0.25


def pick_lead(request: dict, battle: BattleState) -> Action:
    """Feature 11: the lead with the best average type matchup against the opponent's six (ties keep team order).

    Types only, both ways (STAB attack types, no sets or speed): at preview we know their species and nothing else.
    """
    them = "p2" if battle["us"] == "p1" else "p1"
    foes = [_types(mon["species"]) for mon in battle["sides"][them]["pokemon"]]
    ours = [_types(mon["details"].split(", ")[0]) for mon in request["side"]["pokemon"]]
    scores = [sum(_edge(mine, foe) for foe in foes) for mine in ours]
    return Action("lead", scores.index(max(scores)) + 1)


def _types(species: str) -> list[str]:
    return [t.lower() for t in DEX[to_id(species)]["types"]]


def _edge(mine: list[str], foe: list[str]) -> float:
    """How much better our best STAB hits them than their best STAB hits us, in doublings."""
    return math.log2(_best_hit(mine, foe)) - math.log2(_best_hit(foe, mine))


def _best_hit(attacker: list[str], defender: list[str]) -> float:
    return max(max(FLOOR, math.prod(MULTIPLIER[TYPECHART[d][a]] for d in defender)) for a in attacker)
