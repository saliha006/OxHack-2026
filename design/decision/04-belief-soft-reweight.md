# Belief: soft reweight

> **DRAFT, not team-agreed.** Back to: [decision-layer.md](../decision-layer.md#7-feature-checklist). Status: ⬜ not started.

**Job:** Bayes-update candidate weights from indirect evidence.

| | |
|---|---|
| **Input** | Candidates + this turn's events (speed order, damage dealt/taken) |
| **Output** | Reweighted candidates |
| **Build stage** | Stage 4 (after the hard filter) |
| **Owner** | {{owner, not decided}} |

## Interface
🟠 Not decided. Goes in `contracts/` once agreed.

## Decisions (Derrick, 2026-10-24)
1. **Evidence in v1:** speed order, damage they took, damage they dealt.
2. **Hard zero:** a candidate that can't explain the evidence is removed (weight 0), not down-weighted.
   ⚠️ A modelling slip (unseen speed boost, missed crit, rounding) can remove the true set; 03's rebuild is the safety net.

## Open decisions
- 🟠 How to handle speed ties, Scarf, priority and Trick Room in the speed check

## Done when
- [ ] A speed-order observation shifts weight toward consistent sets
- [ ] {{measurable check, not decided}}
