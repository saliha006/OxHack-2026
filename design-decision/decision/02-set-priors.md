> **Historical feature design.** For implemented branch-specific behavior and current evidence, read [CURRENT-STATUS.md](../../CURRENT-STATUS.md) and [DATA-CONTEXT.md](../../DATA-CONTEXT.md) first.

# Set priors (load)

> **DRAFT, not team-agreed.** Back to: [decision-layer.md](../decision-layer.md#7-feature-checklist). Status: ⬜ not started.

**Job:** Load the per-species candidate sets and their prior weights produced offline by the data layer.

| | |
|---|---|
| **Input** | Data layer artifact ([data-layer.md §5a](../data-layer.md#5a-set-candidates--priors-per-species)) |
| **Output** | Weighted candidate sets per opponent species, plus an "other" bucket |
| **Build stage** | Stage 4 |
| **Owner** | {{owner, not decided}} |

## Interface
🟠 Not decided. Goes in `contracts/` once agreed.

## Decisions (Derrick, 2026-10-24)
1. **Source:** Smogon chaos stats, **1825** band, month **2026-09** (574,541 battles, 243 species). Moves, item, ability,
   Tera and spread are combined into full sets, weighted by the product of their frequencies. Consistency rules: Choice
   item or Assault Vest ⇒ no status moves; legal moves only. Choices are treated as independent.
2. **Storage:** a script reads the chaos file once and commits **(a) the built sets** (30 per species, weights
   renormalised) and **(b) a trimmed copy of the counts** (top options per species), for 03's fallback. Runtime loads
   both, with no network.
3. **No teammate correlations** in v1: chaos teammate data is per species, not per set.
4. **30 candidates per species, no "other" bucket.**
5. **Belief memory (Derrick, 2026-10-24):** belief is the decision layer's one memory. Each opponent Pokémon's set weights live for the whole battle and are updated with every turn's `last_turn` events. The engine `State` is still rebuilt each turn.

## Open decisions
- 🟠 What to do for a species with no candidates

## Done when
- [ ] All 6 opponent species from team preview get candidates
- [ ] Weights per species sum to 1
