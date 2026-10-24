from poke_engine import Side, State


def value(state: State) -> float:
    """How good the state is for us (side_one), from 0 (lost) through 0.5 (even) to 1 (won).

    Stage-3 heuristic: each Pokémon is worth 1 for being alive plus its HP fraction, averaged over the side.
    It shares the 0-1 scale with the trained win-probability model meant to replace it.
    """
    ours, theirs = _alive(state.side_one), _alive(state.side_two)
    if not ours or not theirs:
        # Both sides empty at once (Explosion, Destiny Bond) scores as a draw.
        return 0.5 if ours == theirs else float(bool(ours))
    return 0.5 + (_score(state.side_one) - _score(state.side_two)) / 2


def _alive(side: Side) -> int:
    return sum(mon.hp > 0 for mon in side.pokemon)


def _score(side: Side) -> float:
    return sum((mon.hp > 0) + mon.hp / mon.maxhp for mon in side.pokemon) / (2 * len(side.pokemon))
