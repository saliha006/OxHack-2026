# Sample opponent sets

> **DRAFT, not team-agreed.** Back to: [decision-layer.md](../decision-layer.md#7-feature-checklist). Status: ⬜ not started.

**Job:** Pick the top k sets per opponent Pokémon to simulate against.

| | |
|---|---|
| **Input** | Belief weights |
| **Output** | `[set, p][]` per opponent Pokémon |
| **Build stage** | Stage 4 (what stage 3 uses instead: {{not decided}}) |
| **Owner** | {{owner, not decided}} |

## Interface
🟠 Not decided. Goes in `contracts/` once agreed.

## Open decisions
- 🟠 k per Pokémon (3–5 proposed), or set by the turn budget?
- 🟠 Top-k vs random sampling; how the "other" bucket is represented

## Done when
- [ ] Returns at most k sets with probabilities that sum to 1
