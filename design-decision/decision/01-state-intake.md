> **Historical feature design.** For implemented branch-specific behavior and current evidence, read [CURRENT-STATUS.md](../../CURRENT-STATUS.md) and [DATA-CONTEXT.md](../../DATA-CONTEXT.md) first.

# State intake

> **DRAFT, not team-agreed.** Back to: [decision-layer.md](../decision-layer.md#7-feature-checklist). Status: ✅ built on `derrick` against the `BattleState` contract (tested on its example); not merged. Waiting on a real parser.

**Job:** Take the bot layer's `BattleState` (plus this turn's events, if Q7 says so) and check it has everything the later steps need.

| | |
|---|---|
| **Input** | `BattleState` from the bot layer |
| **Output** | A validated state the rest of the loop reads |
| **Build stage** | Stage 3 |
| **Owner** | {{owner, not decided}} |

## Interface
🟠 Not decided. Goes in `contracts/` once agreed.

## Decisions (Derrick, 2026-10-24)
1. **Output:** poke-engine's `State` (see 08). We are `side_one`.
2. **Built now:** `our_side(request) -> Side`, from the request alone, in the request's team order.
3. **Species data:** a committed snapshot of Showdown's `pokedex.json` (types, weight), at `decision/data/pokedex.json`.
4. **`BattleState` is defined by Derrick** (changed from "the bot layer defines it"), as JSON: `contracts/battle-state.md`. Q7: snapshot + last turn's events. The parser is proposed for saliha (bot layer).
5. **Q8, memory:** none. The state is rebuilt every turn from the request + `BattleState`.

**Rules:** the active Pokémon's moves come from `active[0].moves` (one move when locked or Struggling), so move slots
match `our_actions`. Benched PP isn't sent, so full PP is assumed. Fainted Pokémon keep their slot via
`Pokemon.create_fainted()`. Not from the request: boosts, volatiles, hazards, weather, terrain, the opponent side.

**Adapter (Derrick, 2026-10-24):** `build_state(request, battle_state, sets) -> State`.
- `sets`: one `PokemonSet` per opponent slot (team-preview order), from 05 later. A set holds moves, item, ability,
  Tera type, **nature + EVs** (stats computed with pokedex base stats, `decision/sets.py`).
- **Revealed info wins** over the set: revealed moves fill the first slots, then the set's others.
- **Opponent HP** = `hp_percent × max HP`, rounded.
- Our team always comes from the request (Showdown reorders it on every switch); only side-wide fields (boosts,
  volatiles, hazards, screens) come from `BattleState`.
- Each side's `last_used_move` is set from `BattleState.last_move` (poke-engine panics on Encore without it).
  Encore is dropped while Struggling, where it can't restrict anything.
- Elapsed turns → turns left at default lengths (weather/terrain/Trick Room/screens 5, Tailwind 4). Substitute is
  assumed unbroken (¼ max HP).

Code: `decision/state.py`, `decision/adapter.py`, `decision/sets.py` · tests `test_state.py`, `test_adapter.py`, `test_sets.py`.

## Open decisions
- 🟠 What happens if a field is missing or the state looks inconsistent?

## Done when
- [ ] Every request kind (preview / move / forced switch / wait) is recognised
- [ ] Replaying the sample log ([bot-layer.md §1b](../bot-layer.md#1b-sample-log-real-gen9ou-game)) gives no errors
