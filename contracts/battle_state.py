"""BattleState: what the bot layer hands the decision layer each turn, as JSON. Spec: contracts/battle-state.md."""
from typing import Literal, NotRequired, TypedDict

SideId = Literal["p1", "p2"]


class PokemonState(TypedDict):
    species: str              # Showdown ID of the forme, e.g. "samurotthisui"; base ID while the forme is hidden
    forme_known: bool         # False while team preview showed "Species-*"
    level: int
    hp_percent: int           # 0-100 as Showdown reports it; 0 = fainted
    status: Literal["", "brn", "par", "slp", "frz", "psn", "tox"]
    status_turns: int         # end-of-turns since the status started (sleep and toxic counters)
    revealed_moves: list[str] # Showdown IDs, in the order first seen
    item: str | None          # None = not revealed; "" = known to have none (knocked off, consumed); else its ID
    ability: str | None       # None = not revealed
    tera_type: str | None     # None = not revealed
    terastallized: bool
    sleep_turns: NotRequired[int]  # observed failed sleep actions, rather than elapsed end-of-turns
    rest_turns: NotRequired[int]  # engine convention: 3 initially, decrements on sleeping action attempts


class SideState(TypedDict):
    player: str
    rating: int | None        # start Elo from |player|, None if unrated
    pokemon: list[PokemonState]  # team preview order
    active: int | None        # index into pokemon; None before leads are sent
    tera_used: bool           # any Pokémon on this side has Terastallized this game
    boosts: dict[Literal["atk", "def", "spa", "spd", "spe", "accuracy", "evasion"], int]  # active Pokémon, -6..6
    volatiles: list[str]      # active Pokémon's -start effects, e.g. "substitute", "taunt", "encore", "confusion"
    last_move: str | None     # the active Pokémon's last move ID (Choice lock, Encore); reset to None when this side switches
    hazards: dict[Literal["stealthrock", "spikes", "toxicspikes", "stickyweb"], int]  # layers, 0 if absent
    side_effects: dict[str, int]  # timed side conditions in play -> turns elapsed, e.g. {"reflect": 2, "tailwind": 1}
    volatile_turns: NotRequired[dict[str, int]]  # optional extension: elapsed upkeeps since each -start
    wish: NotRequired[dict[str, int]]  # {turns: elapsed upkeeps, source: preview slot, hp?: exact heal amount}
    future_sight: NotRequired[dict[str, int]]  # {turns: elapsed upkeeps, source: attacker preview slot}
    substitute_hp: NotRequired[int]  # exact remaining HP only if known; otherwise adapter explicitly estimates


class Field(TypedDict):
    weather: str              # "" or e.g. "sunnyday", "raindance", "sandstorm", "snow"
    weather_turns: int
    terrain: str              # "" or e.g. "electricterrain"
    terrain_turns: int
    effects: dict[str, int]   # other field effects -> turns elapsed, e.g. {"trickroom": 1}


class Event(TypedDict):
    # One line of last turn's log that belief needs, in log order. Unused keys are None.
    type: Literal["move", "switch", "damage", "heal", "miss", "cant", "reveal"]
    side: SideId
    pokemon: int              # index into that side's pokemon
    move: str | None          # move: the move used; cant: the move it couldn't use
    target: SideId | None     # move: the side targeted
    hp_percent: int | None    # damage / heal: HP after
    source: str | None        # damage / heal / reveal: e.g. "move", "item:leftovers", "ability:intimidate", "stealthrock"
    crit: bool                # damage from a move: the hit was a critical
    effectiveness: Literal["super", "resisted", "immune", "neutral"] | None  # damage from a move
    reason: str | None        # cant: e.g. "par", "flinch", "slp"


class BattleState(TypedDict):
    us: SideId
    turn: int                 # the turn about to be chosen; 0 at team preview
    sides: dict[SideId, SideState]
    field: Field
    last_turn: list[Event]    # everything since the previous request; empty at team preview
