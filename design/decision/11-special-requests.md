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

## Decided (2026-10-24)
- ✅ Lead: fixed hand-picked order for v1 (`team 123456`-style). A type-matchup lead score is a later upgrade if time
  remains. Why: no source measures a lead effect in singles OU. Revisit if test games keep losing from the lead.
- ✅ Forced switch: reuse the main loop with the opponent's only option `None` (poke-engine and Showdown both model it
  that way). Double faint is a normal switch-vs-switch matrix. Keep the stand-in's next-turn evaluation as the score
  while the value is the HP heuristic, then score by post-switch value once the trained model lands. No "switch eats a
  hit" penalty here.

## Done when
- [ ] Plays a full game without a timeout at preview or after a faint
