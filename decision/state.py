import json
import re
from pathlib import Path

from poke_engine import Move, Pokemon, Side

# Showdown's pokedex.json (play.pokemonshowdown.com/data), snapshot of 2026-10-24. The request never sends types or
# weight, and poke-engine would otherwise treat every Pokémon as a 0 kg Normal type.
DEX = json.loads((Path(__file__).parent / "data" / "pokedex.json").read_text())

STATUS = {"brn": "burn", "par": "paralyze", "slp": "sleep", "frz": "freeze", "psn": "poison", "tox": "toxic"}


def to_id(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def our_side(request: dict) -> Side:
    """Our poke-engine Side, in the request's team order so Action slots index it directly.

    Boosts, volatiles and side conditions aren't in the request; they stay at defaults until BattleState supplies them.
    """
    team = request["side"]["pokemon"]
    active_index = next(i for i, mon in enumerate(team) if mon["active"])
    active_moves = None
    if "active" in request:
        # Move slots count from active[0].moves, which is a single move when locked or Struggling.
        active_moves = [Move(id=m["id"], pp=m.get("pp", 1)) for m in request["active"][0]["moves"]]
    pokemon = [_pokemon(mon, active_moves if i == active_index else None) for i, mon in enumerate(team)]
    return Side(pokemon=pokemon, active_index=str(active_index))


def _pokemon(mon: dict, moves: list[Move] | None) -> Pokemon:
    if mon["condition"].endswith("fnt"):
        return Pokemon.create_fainted()
    species, *rest = mon["details"].split(", ")
    level = next((int(part[1:]) for part in rest if re.fullmatch(r"L\d+", part)), 100)
    hp, _, status = mon["condition"].partition(" ")
    current, maxhp = map(int, hp.split("/"))
    entry = DEX[to_id(species)]
    stats = mon["stats"]
    return Pokemon(
        id=to_id(species),
        level=level,
        types=tuple(t.lower() for t in entry["types"]) + ("typeless",) * (2 - len(entry["types"])),
        hp=current,
        maxhp=maxhp,
        ability=mon["ability"] or "none",
        item=mon["item"] or "none",
        attack=stats["atk"],
        defense=stats["def"],
        special_attack=stats["spa"],
        special_defense=stats["spd"],
        speed=stats["spe"],
        status=STATUS.get(status, "none"),
        weight_kg=entry["weightkg"],
        terastallized=bool(mon["terastallized"]),
        tera_type=mon["teraType"].lower(),
        # Benched PP isn't in the request; the engine's default (full) is assumed.
        moves=moves or [Move(id=m) for m in mon["moves"]],
    )
