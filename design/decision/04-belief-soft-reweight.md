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

## Open decisions
- 🟠 Which evidence is in v1: speed order, damage ranges, behaviour hints?
- 🟠 How to handle speed ties, Scarf, priority and Trick Room in the speed check

## Done when
- [ ] A speed-order observation shifts weight toward consistent sets
- [ ] {{measurable check, not decided}}
