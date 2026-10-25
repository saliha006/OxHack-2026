> **Historical feature design.** For implemented branch-specific behavior and current evidence, read [CURRENT-STATUS.md](../../CURRENT-STATUS.md) and [DATA-CONTEXT.md](../../DATA-CONTEXT.md) first.

# Turn budget + fallback

> **DRAFT, not team-agreed.** Back to: [decision-layer.md](../decision-layer.md#7-feature-checklist). Status: ✅ built on `derrick`, not merged.

**Job:** Keep each decision inside the time limit and always send something.

| | |
|---|---|
| **Input** | Clock + partial results |
| **Output** | A `Choice`, always |
| **Build stage** | Stage 3 |
| **Owner** | {{owner, not decided}} |

## Interface
🟠 Not decided. Goes in `contracts/` once agreed.

## Decisions (Derrick, 2026-10-24)
1. **Budget:** 3 seconds per decision (`Agent(budget=3.0)`).
2. **Out of time:** best so far. Scenarios run most likely first; once the deadline passes no new scenario starts, and
   the finished ones are renormalised. The first scenario always completes. A forced switch shares one deadline.
3. **On error:** log it (logger `decision`, with the turn) and send the first legal option from `our_actions`.
   If that fails too, send Showdown's `default`. Belief forgets the failed turn's choice so it isn't replayed.

Code: `decision/agent.py` (`choose`) · tests `tests/test_agent.py`.

## Open decisions

## Done when
- [ ] No game is lost on time
- [ ] An exception inside the loop still sends a legal choice
