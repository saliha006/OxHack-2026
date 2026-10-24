# Special requests

> **DRAFT, not team-agreed.** Back to: [decision-layer.md](../decision-layer.md#7-feature-checklist). Status: ⬜ not started.

**Job:** Handle team preview (lead choice) and forced switches.

| | |
|---|---|
| **Input** | Team preview / forced-switch request |
| **Output** | `team …` or `switch N` |
| **Build stage** | Stage 3 |
| **Owner** | {{owner, not decided}} |

## Interface
🟠 Not decided. Goes in `contracts/` once agreed.

## Open decisions
- 🟠 Q3: fixed lead order first, or decided from the start?
- 🟠 Forced switch: reuse the main loop with the opponent not acting, or a separate rule?

## Done when
- [ ] Plays a full game without a timeout at preview or after a faint
