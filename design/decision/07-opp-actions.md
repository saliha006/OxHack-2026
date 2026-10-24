# Opponent actions + policy

> **DRAFT, not team-agreed.** Back to: [decision-layer.md](../decision-layer.md#7-feature-checklist). Status: ✅ built on `derrick` against the `BattleState` contract; not merged. Trained policy: stage 5.

**Job:** List the opponent's likely legal actions and give each a probability.

| | |
|---|---|
| **Input** | State + belief (their moves, Tera used?, trapped?) |
| **Output** | `[action, p][]` |
| **Build stage** | Stage 3 uniform → Stage 5 trained |
| **Owner** | {{owner, not decided}} |

## Interface
🟠 Not decided. Goes in `contracts/` once agreed.

## Decisions (Derrick, 2026-10-24)
1. **Input:** `BattleState` (`contracts/battle-state.md`, drafted by Derrick). Still blocked until a parser produces it.
2. **Unrevealed moves:** taken from feature 05's sampled sets, so this feature is built after 02–05.
3. **What they can do in v1:** moves, **Tera moves** (while their Tera is unused), and **switches** to any living
   benched Pokémon. We can't see whether they're trapped, so switches are always allowed.

4. **Policy (stage 3):** uniform over moves and switches; a move's Tera copy splits that move's share.
5. **Limits in v1:** Choice lock and Encore (only the last move), Taunt (no status moves, from a snapshot of
   Showdown's `moves.json`). Trapping can't be seen, so switches are always offered.
6. **Interface:** `opp_actions(state, battle) -> list[Action]` + `uniform_policy(actions) -> {Action: p}`. The trained
   policy replaces only the second.

**Rules:** their moves come from the built state (revealed first, then the guessed set), so unrevealed moves come
from the set as decided. **Struggle (Derrick, 2026-10-24):** if the limits leave no move (e.g. Encored into a status move while Taunted),
`build_state` gives the active Pokémon Struggle as its only move, so `opp_actions` returns `move 1` = Struggle plus
switches. The check is one shared helper, `usable_moves()`. ⚠️ poke-engine's gen9 Struggle is a 50 BP **Normal** move
with **no recoil**; the real one is typeless (hits Ghosts) with ¼ max-HP recoil. Engine gap, not ours (research doc R2).

Code: `decision/opponent.py` · tests `tests/test_opponent.py`.

## Open decisions
- 🟠 Stage 5: training data and model for the learned policy

## Done when
- [ ] Probabilities sum to 1
- [ ] The uniform policy and the trained policy are swappable behind the same interface
