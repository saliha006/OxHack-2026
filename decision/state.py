import json
import re
from pathlib import Path

from poke_engine import Move, Pokemon, Side

# Showdown's pokedex.json (play.pokemonshowdown.com/data), snapshot of 2026-10-24. The request never sends types or
# weight, and poke-engine would otherwise treat every Pokémon as a 0 kg Normal type.
DEX = json.loads((Path(__file__).parent / "data" / "pokedex.json").read_text(encoding="utf-8"))

STATUS = {"brn": "burn", "par": "paralyze", "slp": "sleep", "frz": "freeze", "psn": "poison", "tox": "toxic"}


def to_id(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def our_side(request: dict, observed_side: dict | None = None) -> Side:
    """Our poke-engine Side, in the request's team order so Action slots index it directly.

    Boosts, volatiles and side conditions aren't in the request; they stay at defaults until BattleState supplies them.
    """
    team = request["side"]["pokemon"]
    active_index = next(i for i, mon in enumerate(team) if mon["active"])
    active_moves = None
    if "active" in request:
        # Move slots count from active[0].moves, which is a single move when locked or Struggling.
        active_moves = [Move(id=m["id"], pp=m.get("pp", 1), disabled=bool(m.get("disabled")))
                        for m in request["active"][0]["moves"]]
    observed_team = (observed_side or {}).get("pokemon", [])
    observed = {mon["species"]: mon for mon in observed_team}
    identities = {mon["request_ident"]: mon for mon in observed_team if mon.get("request_ident")}
    pokemon = [_pokemon(mon, active_moves if i == active_index else None,
                        identities.get(mon.get("ident"), observed.get(to_id(mon["details"].split(",")[0]), {})))
               for i, mon in enumerate(team)]
    return Side(pokemon=pokemon, active_index=str(active_index))


def _pokemon(mon: dict, moves: list[Move] | None, observed: dict | None = None) -> Pokemon:
    observed = observed or {}
    species, *rest = mon["details"].split(", ")
    level = next((int(part[1:]) for part in rest if re.fullmatch(r"L\d+", part)), 100)
    hp, _, status = mon["condition"].partition(" ")
    if status == "fnt":
        # Preserve identity and transformed state even after fainting: the engine determines spent Tera by
        # looking for a terastallized Pokémon anywhere on the team, including fainted slots.
        current, maxhp = 0, int(mon.get("maxhp", observed.get("exact_maxhp", 100)))
    else:
        current, maxhp = map(int, hp.split("/"))
    entry = DEX[to_id(species)]
    stats = mon["stats"]
    return Pokemon(
        id=to_id(species),
        level=level,
        types=tuple(t.lower() for t in entry["types"]) + ("typeless",) * (2 - len(entry["types"])),
        base_types=tuple(t.lower() for t in entry["types"]) + ("typeless",) * (2 - len(entry["types"])),
        hp=current,
        maxhp=maxhp,
        ability=mon["ability"] or "none",
        base_ability=mon.get("baseAbility", mon["ability"]) or "none",
        item=mon["item"] or "none",
        attack=stats["atk"],
        defense=stats["def"],
        special_attack=stats["spa"],
        special_defense=stats["spd"],
        speed=stats["spe"],
        status=STATUS.get(status, "none"),
        sleep_turns=observed.get("sleep_turns", observed.get("status_turns", 0)) if status == "slp" else 0,
        rest_turns=observed.get("rest_turns", 0) if status == "slp" else 0,
        weight_kg=entry["weightkg"],
        # Tera is irreversible; a fainted request slot can clear its flag.
        # A confirmed public transformed identity still spends the resource.
        terastallized=bool(mon["terastallized"]) or bool(observed.get("terastallized")),
        tera_type=mon["teraType"].lower(),
        # The current active request is exact. Other slots retain last-seen PP
        # by move identity; only never-seen moves use the native default of 16.
        moves=moves or [Move(id=m, pp=observed.get("move_pp", {}).get(m, {}).get("pp", 16)) for m in mon["moves"]],
    )
