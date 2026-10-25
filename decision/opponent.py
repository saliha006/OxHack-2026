import json
from collections import Counter
from pathlib import Path

from poke_engine import State

from contracts.battle_state import BattleState, SideId, SideState
from decision.actions import Action

# Showdown's moves.json (play.pokemonshowdown.com/data), snapshot of 2026-10-24; only `category` is read, for Taunt.
MOVES = json.loads((Path(__file__).parent / "data" / "moves.json").read_text(encoding="utf-8"))

CHOICE_ITEMS = {"choiceband", "choicespecs", "choicescarf"}


def opp_actions(state: State, battle: BattleState) -> list[Action]:
    """The opponent's options this turn, in the built state's slot order (side_two).

    Their moves are the ones build_state filled in: revealed first, then the guessed set's.
    """
    return public_actions(state, battle, "p2" if battle["us"] == "p1" else "p1")


def public_actions(state: State, battle: BattleState, player: SideId) -> list[Action]:
    """A side's options as a spectator sees them, in the built state's slot order: for either side of a replay."""
    side = state.side_one if player == battle["us"] else state.side_two
    seen = battle["sides"][player]
    active = int(side.active_index)
    mon = side.pokemon[active]
    moves = usable_moves([move.id for move in mon.moves], mon.item, seen)

    actions = [Action("move", n) for n in moves]
    if not seen["tera_used"]:
        actions += [Action("move", n, tera=True) for n in moves]
    # A spectator can't tell who is trapped, so every living benched Pokémon is a switch option.
    actions += [Action("switch", n) for n, p in enumerate(side.pokemon, 1) if n - 1 != active and p.hp > 0]
    return actions


def usable_moves(move_ids: list[str], item: str, seen: SideState) -> list[int]:
    """1-based slots of the active Pokémon's moves it can pick; empty means it has to Struggle."""
    moves = list(range(1, len(move_ids) + 1))
    last = seen["last_move"]
    # Both a Choice item and Encore hold them to their last move until they switch out.
    if last in move_ids and ("encore" in seen["volatiles"] or item in CHOICE_ITEMS):
        moves = [move_ids.index(last) + 1]
    if "taunt" in seen["volatiles"]:
        moves = [n for n in moves if MOVES[move_ids[n - 1]]["category"] != "Status"]
    return moves


def uniform_policy(actions: list[Action]) -> dict[Action, float]:
    """Equal odds for each move and each switch; a move's Tera copy splits that move's share."""
    choices = Counter((a.kind, a.slot) for a in actions)
    return {a: 1 / (len(choices) * choices[(a.kind, a.slot)]) for a in actions}
