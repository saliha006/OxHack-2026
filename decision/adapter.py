from poke_engine import Move, Pokemon, Side, SideConditions, State, VolatileStatusDurations

from contracts.battle_state import BattleState, PokemonState, SideState
from decision.opponent import usable_moves
from decision.sets import PokemonSet, stats
from decision.state import DEX, STATUS, our_side

# gen9ou weathers only; the primal ones (desolateland, primordialsea) come from Pokémon banned in OU.
WEATHER = {"sunnyday": "sun", "raindance": "rain", "sandstorm": "sand", "snow": "snow"}

# Default lengths, used to turn BattleState's elapsed turns into poke-engine's turns left. Light Clay, Damp Rock and
# the like never show in the log, so extended durations are missed.
WEATHER_TURNS = TERRAIN_TURNS = TRICK_ROOM_TURNS = 5
SIDE_EFFECT_TURNS = {"reflect": 5, "lightscreen": 5, "auroraveil": 5, "safeguard": 5, "mist": 5, "tailwind": 4}
SIDE_EFFECT_FIELD = {"reflect": "reflect", "lightscreen": "light_screen", "auroraveil": "aurora_veil",
                     "safeguard": "safeguard", "mist": "mist", "tailwind": "tailwind"}
# The binding's .pyi calls all of these "turns remaining", but the Rust implementation uses elapsed counters
# for Encore/Taunt/lockedmove/Yawn and a countdown for Slow Start. Confusion's counter is unused by stock gen9.
VOLATILE_TURNS = {"encore": 2, "lockedmove": 2, "slowstart": 6, "taunt": 2, "yawn": 1}


def build_state(request: dict, battle: BattleState, sets: list[PokemonSet]) -> State:
    """The poke-engine State for one turn: us as side_one, with one guessed set per opponent slot.

    Our team comes from the request, which Showdown reorders on every switch (that order is what Action slots
    index). The opponent's team keeps BattleState's team-preview order, which `sets` must follow.
    """
    us = battle["us"]
    them = "p2" if us == "p1" else "p1"
    field = battle["field"]
    ours = our_side(request, battle["sides"][us])
    seen = battle["sides"][them]
    theirs = [_opponent(mon, guess, seen if n == seen["active"] else None)
              for n, (mon, guess) in enumerate(zip(seen["pokemon"], sets, strict=True))]
    return State(
        side_one=_side(battle["sides"][us], ours.pokemon, int(ours.active_index),
                       check_resource=False,  # our request supplies the exact transformed slots
                       force_switch=any(request.get("forceSwitch", [])),
                       force_trapped=bool(request.get("active", [{}])[0].get("trapped") or
                                          request.get("active", [{}])[0].get("maybeTrapped"))),
        side_two=_side(seen, theirs, seen["active"]),
        weather=WEATHER.get(field["weather"], "none"),
        weather_turns_remaining=_active_left(WEATHER_TURNS, field["weather_turns"]) if field["weather"] else 0,
        terrain=field["terrain"] or "none",
        terrain_turns_remaining=_active_left(TERRAIN_TURNS, field["terrain_turns"]) if field["terrain"] else 0,
        trick_room="trickroom" in field["effects"],
        trick_room_turns_remaining=(
            _active_left(TRICK_ROOM_TURNS, field["effects"]["trickroom"]) if "trickroom" in field["effects"] else 0
        ),
    )


def _side(seen: SideState, pokemon: list[Pokemon], active: int, *,
          force_switch: bool = False, force_trapped: bool = False, check_resource: bool = True) -> Side:
    boosts = seen["boosts"]
    hazards = seen["hazards"]
    timed = {SIDE_EFFECT_FIELD[name]: _active_left(SIDE_EFFECT_TURNS[name], turns)
             for name, turns in seen["side_effects"].items() if name in SIDE_EFFECT_FIELD}
    active_mon = pokemon[active]
    if check_resource and seen["tera_used"] and not any(mon.terastallized for mon in pokemon):
        raise ValueError("spent Tera has no transformed team slot; cannot safely build native resource state")
    move_ids = [move.id for move in active_mon.moves]
    last = seen["last_move"]
    volatiles = set(seen["volatiles"])
    if last not in move_ids:
        # poke-engine panics on Encore without a last move in the list; that only happens while Struggling,
        # when Encore has nothing left to restrict.
        volatiles.discard("encore")
    durations = {name: (max(1, total - seen.get("volatile_turns", {}).get(name, 0)) if name == "slowstart"
                       else min(total, seen.get("volatile_turns", {}).get(name, 0)))
                 for name, total in VOLATILE_TURNS.items() if name in volatiles}
    # Delayed effects store the source in preview order. Resolve it against the actual engine team order,
    # since our request can reorder the team after a switch.
    def source_slot(effect):
        preview_slot = effect.get("source", seen["active"])
        species = seen["pokemon"][preview_slot]["species"]
        return next((n for n, mon in enumerate(pokemon) if mon.id == species), active)
    wish = seen.get("wish", {})
    future = seen.get("future_sight", {})
    return Side(
        pokemon=pokemon,
        active_index=str(active),
        force_switch=force_switch,
        force_trapped=force_trapped,
        attack_boost=boosts["atk"],
        defense_boost=boosts["def"],
        special_attack_boost=boosts["spa"],
        special_defense_boost=boosts["spd"],
        speed_boost=boosts["spe"],
        accuracy_boost=boosts["accuracy"],
        evasion_boost=boosts["evasion"],
        # poke-engine reads lowercase Showdown IDs and ignores names it doesn't model.
        volatile_statuses=volatiles,
        volatile_status_durations=VolatileStatusDurations(**durations),
        last_used_move=f"move:{move_ids.index(last)}" if last in move_ids else "move:none",
        # A Substitute starts at a quarter of max HP; hits on it aren't in BattleState, so it's taken as unbroken.
        substitute_health=(seen.get("substitute_hp", active_mon.maxhp // 4)
                           if "substitute" in seen["volatiles"] else 0),
        wish=(_left(2, wish["turns"]), wish.get("hp", pokemon[source_slot(wish)].maxhp // 2))
             if wish else (0, 0),
        future_sight=(_left(3, future["turns"]), str(source_slot(future))) if future else (0, "0"),
        side_conditions=SideConditions(
            stealth_rock=hazards["stealthrock"],
            spikes=hazards["spikes"],
            toxic_spikes=hazards["toxicspikes"],
            sticky_web=hazards["stickyweb"],
            toxic_count=seen["pokemon"][seen["active"]]["status_turns"] if active_mon.status == "toxic" else 0,
            protect=min(6, max(0, seen.get("protect_streak", 0))),
            **timed,
        ),
    )


def _opponent(mon: PokemonState, guess: PokemonSet, active_side: SideState | None) -> Pokemon:
    species, level = mon["species"], mon["level"]
    maxhp, atk, dfn, spa, spd, spe = stats(species, level, guess)
    types = [t.lower() for t in DEX[species]["types"]]
    # Observed facts beat the guess: revealed moves fill the first slots, then the set's other moves.
    moves = (mon["revealed_moves"] + [m for m in guess.moves if m not in mon["revealed_moves"]])[:4]
    item = _known_or(mon["item"], guess.item)
    # poke-engine only runs Struggle from the move list, which can't be edited once built, so it goes in here.
    if active_side is not None and not usable_moves(moves, item, active_side):
        moves = ["struggle"]
    return Pokemon(
        id=species,
        level=level,
        types=tuple(types) + ("typeless",) * (2 - len(types)),
        base_types=tuple(types) + ("typeless",) * (2 - len(types)),
        hp=round(mon["hp_percent"] / 100 * maxhp),
        maxhp=maxhp,
        ability=mon["ability"] or guess.ability,
        base_ability=mon["ability"] or guess.ability,
        item=item,
        attack=atk,
        defense=dfn,
        special_attack=spa,
        special_defense=spd,
        speed=spe,
        status=STATUS.get(mon["status"], "none"),
        sleep_turns=mon.get("sleep_turns", mon["status_turns"]) if mon["status"] == "slp" else 0,
        rest_turns=mon.get("rest_turns", 0) if mon["status"] == "slp" else 0,
        weight_kg=DEX[species]["weightkg"],
        terastallized=mon["terastallized"],
        tera_type=mon["tera_type"] or guess.tera_type,
        moves=[Move(id=m, disabled=(active_side is not None and
                                   n not in usable_moves(moves, item, active_side)))
               for n, m in enumerate(moves, 1)],
    )


def _known_or(revealed: str | None, guessed: str) -> str:
    # None = not revealed yet; "" = revealed as having none (knocked off, consumed).
    if revealed is None:
        return guessed
    return revealed or "none"


def _left(total: int, elapsed: int) -> int:
    return max(total - elapsed, 0)


def _active_left(total: int, elapsed: int) -> int:
    # A currently observed effect cannot already be absent. Its unknown expiry
    # is still an estimate; recheck on the next protocol snapshot.
    return max(total - elapsed, 1)


def adapter_diagnostics(request: dict, battle: BattleState) -> list[dict]:
    """Explicit estimates in the native state; these are observations about conversion, not engine errors."""
    estimates = [{"field": "opponent_pp", "certainty": "estimated",
                  "reason": "not observed; engine defaults to 16 per move"},
                 {"field": "our_bench_pp", "reason": "per-move provenance below; unseen moves still default to 16"}]
    observed = battle["sides"][battle["us"]]["pokemon"]
    for slot in request.get("side", {}).get("pokemon", []):
        species = ''.join(char.lower() for char in slot["details"].split(',')[0] if char.isalnum())
        mon = next((mon for mon in observed if mon.get("request_ident") == slot.get("ident") or
                    mon["species"] == species), {})
        current = {move['id']: move for move in request.get('active', [{}])[0].get('moves', [])
                   if 'pp' in move} if slot.get('active') else {}
        for move in slot.get('moves', []):
            cached = mon.get('move_pp', {}).get(move)
            certainty = ('exact' if move in current else
                         'estimated' if cached is None or cached.get('certainty') == 'estimated' else 'remembered')
            estimates.append({'field': 'move_pp', 'side': battle['us'], 'species': species, 'move': move,
                              'certainty': certainty,
                              'reason': 'current request' if move in current else
                                        cached.get('source', 'last request') if cached else 'native default 16; never observed'})
    if any(request.get('forceSwitch', [])) and any(mon.get('active') and not mon.get('condition', '').endswith('fnt')
                                                  for mon in request.get('side', {}).get('pokemon', [])):
        estimates.append({'field': 'continuation_request', 'certainty': 'estimated',
                          'reason': 'living pivot/replacement; any unobserved queued opponent move remains unknown; native saved move omitted'})
    for side_id, side in battle["sides"].items():
        for effect in side["side_effects"]:
            if effect in SIDE_EFFECT_TURNS:
                estimates.append({"side": side_id, "field": effect, "reason": "default duration; extender may be hidden"})
            else:
                estimates.append({"side": side_id, "field": effect, "reason": "unsupported side effect omitted"})
        for effect in side["volatiles"]:
            if effect in VOLATILE_TURNS:
                estimates.append({"side": side_id, "field": effect,
                                  "reason": "observed upkeeps approximate native action counters; clamped to valid range"})
            elif effect == "confusion":
                estimates.append({"side": side_id, "field": effect, "reason": "stock engine does not expire confusion"})
        if "substitute" in side["volatiles"] and "substitute_hp" not in side:
            estimates.append({"side": side_id, "field": "substitute_hp", "reason": "quarter max HP; damage hidden"})
        if side.get("wish") and "hp" not in side["wish"]:
            estimates.append({"side": side_id, "field": "wish_hp", "reason": "half source max HP; opponent spread sampled"})
        if side["tera_used"] and not any(mon["terastallized"] for mon in side["pokemon"]):
            estimates.append({"side": side_id, "field": "tera_used", "reason": "inconsistent observation: transformed slot unknown"})
        if any(mon["status"] == "slp" and "sleep_turns" not in mon for mon in side["pokemon"]):
            estimates.append({"side": side_id, "field": "sleep_turns", "reason": "elapsed upkeep count; sleep attempts/Rest uncertain"})
    for field in ("weather", "terrain"):
        if battle["field"][field]:
            estimates.append({"field": field, "reason": "default duration; extender may be hidden"})
    return estimates
