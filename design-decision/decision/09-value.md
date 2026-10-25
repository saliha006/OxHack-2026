> **Historical feature design.** For implemented branch-specific behavior and current evidence, read [CURRENT-STATUS.md](../../CURRENT-STATUS.md) and [DATA-CONTEXT.md](../../DATA-CONTEXT.md) first.

# Value function

> **DRAFT, not team-agreed.** Back to: [decision-layer.md](../decision-layer.md#7-feature-checklist). Status: ✅ heuristic built on `derrick`, not merged. Trained model: stage 5.

**Job:** Score a state from our side.

| | |
|---|---|
| **Input** | State |
| **Output** | A number (higher = better for us) |
| **Build stage** | Stage 3 heuristic → Stage 5 trained |
| **Owner** | {{owner, not decided}} |

## Interface
🟠 Not decided. Goes in `contracts/` once agreed.

## Decisions (Derrick, 2026-10-24)
1. **Terms:** HP + Pokémon alive only (no status, boosts or hazards), so the trained model has a clear baseline to beat.
2. **Scale:** 0 (lost) · 0.5 (even) · 1 (won), the same as the trained win-probability model.
3. **Weights:** equal. Each Pokémon = 1 (alive) + HP fraction; side score = sum / (2 · slots);
   `value = 0.5 + (ours − theirs) / 2`. A KO of a full-HP Pokémon = +1/12; 50% chip = +1/48.
4. **Rating prior:** left out for now. `value(state)` reads only the state; revisit when the data layer has ratings.

**Rules:** no Pokémon left on one side → flat 1 or 0; on both sides at once → 0.5. poke-engine pads every `Side` to
6 slots with fainted placeholders, so a slot count is always 6.

Code: `decision/value.py` · tests `tests/test_value.py`.

## Open decisions
- 🟠 Stage 5: training data, features and model type for the learned win probability

## Done when
- [x] A won position scores higher than a lost one
- [ ] Heuristic and trained value are swappable
