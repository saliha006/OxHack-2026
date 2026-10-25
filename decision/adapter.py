from poke_engine import Move, Pokemon, Side, SideConditions, State

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


def build_state(request: dict, battle: BattleState, sets: list[PokemonSet]) -> State:
    """The poke-engine State for one turn: us as side_one, with one guessed set per opponent slot.

    Our team comes from the request, which Showdown reorders on every switch (that order is what Action slots
    index). The opponent's team keeps BattleState's team-preview order, which `sets` must follow.
    """
    us = battle["us"]
    ours = our_side(request)
    seen = battle["sides"]["p2" if us == "p1" else "p1"]
    return _state(battle, _side(battle["sides"][us], ours.pokemon, int(ours.active_index)), _guessed_side(seen, sets))


def build_public_state(battle: BattleState, our_sets: list[PokemonSet], their_sets: list[PokemonSet]) -> State:
    """The poke-engine State for a replay turn, which has no request: both sides as a spectator sees them.

    Our side is guessed the same way as theirs, so both teams keep team-preview order and Action slots index it.
    """
    us = battle["sides"][battle["us"]]
    them = battle["sides"]["p2" if battle["us"] == "p1" else "p1"]
    return _state(battle, _guessed_side(us, our_sets), _guessed_side(them, their_sets))


def _state(battle: BattleState, side_one: Side, side_two: Side) -> State:
    field = battle["field"]
    return State(
        side_one=side_one,
        side_two=side_two,
        weather=WEATHER.get(field["weather"], "none"),
        weather_turns_remaining=_left(WEATHER_TURNS, field["weather_turns"]) if field["weather"] else 0,
        terrain=field["terrain"] or "none",
        terrain_turns_remaining=_left(TERRAIN_TURNS, field["terrain_turns"]) if field["terrain"] else 0,
        trick_room="trickroom" in field["effects"],
        trick_room_turns_remaining=(
            _left(TRICK_ROOM_TURNS, field["effects"]["trickroom"]) if "trickroom" in field["effects"] else 0
        ),
    )


def _side(seen: SideState, pokemon: list[Pokemon], active: int) -> Side:
    boosts = seen["boosts"]
    hazards = seen["hazards"]
    timed = {SIDE_EFFECT_FIELD[name]: _left(SIDE_EFFECT_TURNS[name], turns)
             for name, turns in seen["side_effects"].items() if name in SIDE_EFFECT_FIELD}
    active_mon = pokemon[active]
    move_ids = [move.id for move in active_mon.moves]
    last = seen["last_move"]
    volatiles = set(seen["volatiles"])
    if last not in move_ids:
        # poke-engine panics on Encore without a last move in the list; that only happens while Struggling,
        # when Encore has nothing left to restrict.
        volatiles.discard("encore")
    return Side(
        pokemon=pokemon,
        active_index=str(active),
        attack_boost=boosts["atk"],
        defense_boost=boosts["def"],
        special_attack_boost=boosts["spa"],
        special_defense_boost=boosts["spd"],
        speed_boost=boosts["spe"],
        accuracy_boost=boosts["accuracy"],
        evasion_boost=boosts["evasion"],
        # poke-engine reads lowercase Showdown IDs and ignores names it doesn't model.
        volatile_statuses=volatiles,
        last_used_move=f"move:{move_ids.index(last)}" if last in move_ids else "move:none",
        # A Substitute starts at a quarter of max HP; hits on it aren't in BattleState, so it's taken as unbroken.
        substitute_health=active_mon.maxhp // 4 if "substitute" in seen["volatiles"] else 0,
        side_conditions=SideConditions(
            stealth_rock=hazards["stealthrock"],
            spikes=hazards["spikes"],
            toxic_spikes=hazards["toxicspikes"],
            sticky_web=hazards["stickyweb"],
            toxic_count=seen["pokemon"][seen["active"]]["status_turns"] if active_mon.status == "toxic" else 0,
            **timed,
        ),
    )


def _guessed_side(seen: SideState, sets: list[PokemonSet]) -> Side:
    team = [_guessed(mon, guess, seen if n == seen["active"] else None)
            for n, (mon, guess) in enumerate(zip(seen["pokemon"], sets, strict=True))]
    return _side(seen, team, seen["active"])


def _guessed(mon: PokemonState, guess: PokemonSet, active_side: SideState | None) -> Pokemon:
    if mon["hp_percent"] == 0:
        return Pokemon.create_fainted()
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
        hp=round(mon["hp_percent"] / 100 * maxhp),
        maxhp=maxhp,
        ability=mon["ability"] or guess.ability,
        item=item,
        attack=atk,
        defense=dfn,
        special_attack=spa,
        special_defense=spd,
        speed=spe,
        status=STATUS.get(mon["status"], "none"),
        sleep_turns=mon["status_turns"] if mon["status"] == "slp" else 0,
        weight_kg=DEX[species]["weightkg"],
        terastallized=mon["terastallized"],
        tera_type=mon["tera_type"] or guess.tera_type,
        moves=[Move(id=m) for m in moves],
    )


def _known_or(revealed: str | None, guessed: str) -> str:
    # None = not revealed yet; "" = revealed as having none (knocked off, consumed).
    if revealed is None:
        return guessed
    return revealed or "none"


def _left(total: int, elapsed: int) -> int:
    return max(total - elapsed, 0)
