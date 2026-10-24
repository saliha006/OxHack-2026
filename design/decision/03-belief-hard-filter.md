# Belief: hard filter

> **DRAFT, not team-agreed.** Back to: [decision-layer.md](../decision-layer.md#7-feature-checklist). Status: ⬜ not started.

**Job:** Drop candidate sets that contradict what's been revealed.

| | |
|---|---|
| **Input** | Candidates + revealed info (moves, item, ability, Tera, implied items) |
| **Output** | Filtered, renormalised candidates |
| **Build stage** | Stage 4 |
| **Owner** | {{owner, not decided}} |

## Interface
🟠 Not decided. Goes in `contracts/` once agreed.

## Open decisions
- 🟠 Which implied-item rules are in v1 (Choice lock, Boots on hazards, no Leftovers heal, …)?
- 🟠 What happens if every candidate is filtered out?

## Done when
- [ ] A revealed move removes every set without it
- [ ] An all-filtered species falls back to {{fallback, not decided}}
