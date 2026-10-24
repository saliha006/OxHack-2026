# Special requests

> Back to: [decision-layer.md](../decision-layer.md#7-feature-checklist). Status: 🟡 built on `derrick`, not merged; *Done when* waits on the parser.

**Job:** Handle team preview (lead choice) and forced switches.

| | |
|---|---|
| **Input** | Team preview / forced-switch request |
| **Output** | `team …` or `switch N` |
| **Build stage** | Stage 3 |
| **Owner** | @derrick |

## Interface
Internal to the decision layer: `Agent.choose` answers a preview request with `team …` and a forced switch with `switch N`. No contract change.

## Team preview: type-matchup lead (Derrick, 2026-10-24, decision C)
- Each of our six is scored against the opponent's six by species types only (at preview that's all we know about them):
  log₂ of our best STAB multiplier on them minus log₂ of theirs on us, summed over their six. Highest leads; ties keep team order.
- An immunity counts as ×0.25, so one immune foe can't send the score to −∞.
- The back five keep the team's own order.
- ⚠️ Ignores sets, coverage moves and speed. Revisit if leads lose turn 1 often in real games.

Code: `decision/lead.py` (`pick_lead`), type chart snapshot `decision/data/typechart.json`.

## Forced switch: reuse the main loop (Derrick, 2026-10-24, decision A)
- For each switch-in, the move-turn evaluation runs as if it were in (full PP assumed), and the best one goes in.
- ⚠️ Judged by the current models: under the uniform opponent a damaged Pokémon that can Roost, or a fragile
  hard-hitter, can outscore a healthy one. Fixed by task 5's value model, not by extra rules.

Code: `decision/agent.py` (`_best_switch_in`).

## Decisions
- ✅ Q3 lead: type-matchup rule (C) over fixed order (A, ignores the opponent) and simulating 36 lead pairs (B, weak priors at preview, budget). Revisit if a full game plays end to end and leads look bad.
- ✅ Forced switch: reuse the main loop (A) over a separate HP×type rule (B, a second scoring path) and A with a filter (C, thresholds to tune). Revisit if the value model upgrade is cut.

## Done when
- [ ] Plays a full game without a timeout at preview or after a faint
