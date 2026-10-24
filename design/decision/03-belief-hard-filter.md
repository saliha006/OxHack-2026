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

## Decisions (Derrick, 2026-10-24)
1. **Removes** candidates that contradict revealed moves, item, ability or Tera type.
2. **Implied-item rules in v1:** two different moves without switching ⇒ not a Choice item; damaged at end of turn
   with no Leftovers heal ⇒ not Leftovers; switched into hazards with no hazard damage ⇒ Heavy-Duty Boots (or Magic
   Guard); used a status move ⇒ not Assault Vest.
3. **All ruled out ⇒ rebuild** from the trimmed counts (02), keeping only options consistent with everything revealed,
   using the same set builder.

## Open decisions

## Done when
- [ ] A revealed move removes every set without it
- [ ] An all-filtered species falls back to {{fallback, not decided}}
