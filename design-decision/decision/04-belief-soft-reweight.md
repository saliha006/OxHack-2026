# Belief: soft reweight

> **DRAFT, not team-agreed.** Back to: [decision-layer.md](../decision-layer.md#7-feature-checklist). Status: ✅ built on `derrick` (on hand-made priors), not merged.

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

3. **Method: replay the turn in poke-engine per candidate** (Derrick, 2026-10-24), not hand-written rules. Belief
   remembers our last choice (`Belief.chose(request, action)`) and last turn's `BattleState`, rebuilds the starting
   state with the candidate in the opponent's active slot, and drops it if the engine can't produce:
   - **the move order:** each side's move is first run alone to get its signature (its first instruction), then the
     full turn's outcomes are checked for that order. Speed ties give both orders; an outcome where a side the log
     shows acting never acts (flinch) doesn't match;
   - **the damage they took and dealt:** within `calculate_damage`'s range (85–100% of max roll; the crit roll if the
     event says crit), ±1 point for Showdown's rounding; a KO only needs enough damage.
4. **No evidence from:** a switch on either side, a turn where only one side acted, signatures the engine can't tell
   apart, immune hits, a hit that lands after the target pivoted out, and **multi-hit moves** (until the contract
   carries `hit_count`, parked by Derrick).

Code: `decision/belief.py` (`_explains_turn`) · tests `tests/test_reweight.py`.

## Open decisions
- 🟠 How to handle speed ties, Scarf, priority and Trick Room in the speed check

## Done when
- [ ] A speed-order observation shifts weight toward consistent sets
- [ ] {{measurable check, not decided}}
