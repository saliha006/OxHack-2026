# Turn budget + fallback

> **DRAFT, not team-agreed.** Back to: [decision-layer.md](../decision-layer.md#7-feature-checklist). Status: ⬜ not started.

**Job:** Keep each decision inside the time limit and always send something.

| | |
|---|---|
| **Input** | Clock + partial results |
| **Output** | A `Choice`, always |
| **Build stage** | Stage 3 |
| **Owner** | {{owner, not decided}} |

## Interface
🟠 Not decided. Goes in `contracts/` once agreed.

## Open decisions
- 🟠 Q5: local only, or a timed ladder game? Per-turn limit?
- 🟠 Q6: on timeout or error, send the first legal move, the best so far, or something else?

## Done when
- [ ] No game is lost on time
- [ ] An exception inside the loop still sends a legal choice
