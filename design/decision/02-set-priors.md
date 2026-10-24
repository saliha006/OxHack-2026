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

## Open decisions
- 🟠 Q9: load once at startup, query live, or a mix?
- 🟠 Artifact format (owned by the data layer)
- 🟠 What to do for a species with no candidates

## Done when
- [ ] All 6 opponent species from team preview get candidates
- [ ] Weights per species sum to 1
