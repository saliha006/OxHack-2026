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

## Stand-ins until this feature is built (Derrick, 2026-10-24)
- **Team preview:** the team goes in as built (`team 123456`).
- **Forced switch:** for each switch-in, the move-turn evaluation runs as if it were in (full PP assumed), and the best
  one goes in. ⚠️ Judged by the current models: under the uniform opponent a damaged Pokémon that can Roost, or a
  fragile hard-hitter, can outscore a healthy one.

Code: `decision/agent.py` (`_best_switch_in`).

## Open decisions
- 🟠 Q3: fixed lead order first, or decided from the start?
- 🟠 Forced switch: reuse the main loop with the opponent not acting, or a separate rule?

## Done when
- [ ] Plays a full game without a timeout at preview or after a faint
