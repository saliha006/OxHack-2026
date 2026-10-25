> **Historical feature design.** For implemented branch-specific behavior and current evidence, read [CURRENT-STATUS.md](../../CURRENT-STATUS.md) and [DATA-CONTEXT.md](../../DATA-CONTEXT.md) first.

# Simulate one turn

> **DRAFT, not team-agreed.** Back to: [decision-layer.md](../decision-layer.md#7-feature-checklist). Status: ✅ built on `derrick`, not merged.

**Job:** Given state, our action, their action and their set, produce the next state.

| | |
|---|---|
| **Input** | State + our action + their action + sampled set |
| **Output** | Next state (or a distribution over outcomes) |
| **Build stage** | Stage 2 |
| **Owner** | {{owner, not decided}} |

## Interface
🟠 Not decided. Goes in `contracts/` once agreed.

## Decisions (Derrick, 2026-10-24)
1. **Engine:** [`poke-engine`](https://github.com/pmariglia/poke-engine) (Rust + Python bindings), built with
   `poke-engine/terastallization` (gen9). Only its one-turn outcomes are used; our loop and selector make the decision,
   not its MCTS / expectiminimax. Test results: research doc R2 (matches the real game's turn 1; 0.038 ms per call).

2. **Returns** every outcome: `list[(probability, next State)]`. The input state is not changed.
3. **Working state:** poke-engine's `State` is the decision layer's state. Feature 01 converts `BattleState` → `State`
   once per turn, **building each side in the request's order** (Action slots index it directly). We are side_one.
4. **Input:** `simulate(state, ours: Action, theirs: Action)`. This sets 07's output type to `Action` as well.

Code: `decision/simulate.py` · tests `tests/test_simulate.py`.

## Open decisions
- 🟠 Q5 + turn budget: how many calls can we afford?

## Done when
- [x] Matches a real turn from the sample log (turn 1: Kingambit at 66%)
- [x] Time per call measured: 0.038 ms (research doc R2)
