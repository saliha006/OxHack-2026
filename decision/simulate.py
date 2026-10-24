from poke_engine import Side, State, generate_instructions

from decision.actions import Action


def simulate(state: State, ours: Action, theirs: Action) -> list[tuple[float, State]]:
    """Every outcome of one turn as (probability, next state). Our side is side_one; the input state is not changed."""
    outcomes = generate_instructions(state, engine_move(state.side_one, ours), engine_move(state.side_two, theirs))
    return [(o.percentage / 100, state.apply_instructions(o)) for o in outcomes]


def engine_move(side: Side, action: Action) -> str:
    """An Action as the string poke-engine expects for that side."""
    # Slots index the engine's lists directly, so feature 01 must build each side in the request's order.
    if action.kind == "move":
        move = side.pokemon[int(side.active_index)].moves[action.slot - 1].id
        return f"{move}-tera" if action.tera else move
    if action.kind == "switch":
        return side.pokemon[action.slot - 1].id
    raise ValueError(f"{action.kind} is chosen at team preview, not simulated")
