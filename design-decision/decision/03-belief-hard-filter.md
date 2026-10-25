> **Historical feature design.** For implemented branch-specific behavior and current evidence, read [CURRENT-STATUS.md](../../CURRENT-STATUS.md) and [DATA-CONTEXT.md](../../DATA-CONTEXT.md) first.

# Belief: hard filter

> **DRAFT, not team-agreed.** Back to: [decision-layer.md](../decision-layer.md#7-feature-checklist). Status: ✅ built on `derrick` (on hand-made priors), not merged.

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

**Rules (one right answer):** a known-none item (`""`) doesn't filter, since it may have been knocked off. Taking
Stealth Rock damage on switch-in rules out Boots (the converse of the Boots rule). An item named in an event's
`[from] item:` tag counts as revealed. The Leftovers rule is skipped on a turn with a faint, since the replacement may
have arrived after the end of turn. **Rebuild size:** revealed moves topped up with the most-used moves × top 3 items
× top 2 Tera types × top 3 spreads (≤18 sets), Choice / Assault Vest dropped when a status move is in.

Code: `decision/belief.py` (`Belief.update`) · tests `tests/test_belief.py`.

## Open decisions

## Done when
- [ ] A revealed move removes every set without it
- [ ] An all-filtered species falls back to {{fallback, not decided}}
