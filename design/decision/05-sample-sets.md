# Sample opponent sets

> **DRAFT, not team-agreed.** Back to: [decision-layer.md](../decision-layer.md#7-feature-checklist). Status: ✅ built on `derrick` (on hand-made priors), not merged.

**Job:** Pick the top k sets per opponent Pokémon to simulate against.

| | |
|---|---|
| **Input** | Belief weights |
| **Output** | `[set, p][]` per opponent Pokémon |
| **Build stage** | Stage 4 (what stage 3 uses instead: {{not decided}}) |
| **Owner** | {{owner, not decided}} |

## Interface
🟠 Not decided. Goes in `contracts/` once agreed.

## Decisions (Derrick, 2026-10-24)
1. **k = 5** for the opponent's active Pokémon; weights renormalised to sum to 1.
2. **Top-k**, not a random draw: deterministic.
3. **Vary the active only:** each benched Pokémon uses its single most likely set. 5 states per turn.

**Interface:** `Belief.scenarios(k=5) -> [(p, [set per slot ×6])]`: one scenario per top set of the active
Pokémon, bench at its best guess. Feeds `build_state` and the selector's `set_probs` directly.

Code: `decision/belief.py` · tests `tests/test_belief.py`.

## Open decisions

## Done when
- [ ] Returns at most k sets with probabilities that sum to 1
