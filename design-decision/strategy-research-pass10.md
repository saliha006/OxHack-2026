# Decision layer: research-backed plan (pass 10, 2026-10-25 ~00:50 UTC)

**For @derrick. Every line here is a recommendation; decision-layer choices are yours (CLAUDE.md §2).**
Four specialist research agents (search, belief, opponent model + value, speed) and a fifth that cross-checked them,
using peer-reviewed papers, official source (poke-engine, Showdown, Foul Play), community threads, measurements on
our own code, and the PRD. Full notes and source ledgers: saliha's research doc, pass 10 (local; ask her for any part).

## The big picture
Each turn is a table: our move × their move × which hidden set they run, with dice inside each cell. We never solve
that table whole; each piece of the agent shrinks or prices one axis:

| Axis | What handles it | Status |
|---|---|---|
| Dice (damage rolls, crits, accuracy) | poke-engine returns the few outcomes per cell (~1.5); exact weighted average | built, cheap |
| Hidden set | belief: a weighted list (≤30 sets); simulate a few representative sets, weight answers by belief mass, **before** choosing (so no strategy-fusion error at one ply) | built; two crash bugs |
| Their move | opponent model: a probability per reply. Uniform today puts ~56% of the mass on switching (5 of 9 options early on) | built (uniform) |
| The future (depth) | the leaf value must price what happens next. HP+alive can't see boosts, hazards or status, which is why Swords Dance is strictly dominated at one ply on our test position and the top three moves score 0.503 / 0.501 / 0.497 (a coin flip) | **the real weakness** |
| Time | cells × scenarios × ~1.1–1.6 ms of Python per cell (measured) | fine at k=5 |

So the agent is a **one-ply expected-value agent with a learned leaf**, not an equilibrium solver; say it that way.

## What's wrong today, in order
1. **Two crash bugs in `belief.py`** made 12.7% of turns fall back to "first legal move" in the smoke run (one-value `calculate_damage` return for fixed-damage moves like Ruination; `max()` on an empty slot in `scenarios()`). Plus the Keldeo-Resolute forme mismatch. Fixing these beats any model upgrade.
2. **The HP value can't see the future**, so near-ties between attacks are decided by noise and setup moves never win.

## Core plan (~4.5 h incl. slack)
| # | Step | Owner | Hours | Proof |
|---|---|---|---|---|
| 1 | **Instrumentation:** per turn, timings (build / cells / select), scenarios, cells, per-scenario argmax, top-1 vs top-2 gap, the matrix, the observed opponent reply. Feeds the trace (your task 4) and gates steps 7–8 | derrick (trace fields: ⚠️ saliha) | 0.25 | log lines on ≥100 real turns |
| 2 | **Belief crash fixes + floor:** one-value damage return = max = crit; empty-slot guard; battle-only formes to base species; hard zero → floor eps≈0.03 that recovers; repair a revealed move missing from a set | derrick | 1.25 | unit tests; 10-game smoke fallback 12.7% → <1% |
| 3 | **Featurizer** `decision/features.py`: the same columns from a poke-engine `State` and from a `BattleState` (replays), reading each side once | derrick | 1.5 | dual-path parity test |
| 4 | **Train + calibrate logistic** (HGB only if it beats logistic and time remains): battle/time/player split, Platt or isotonic by validation log loss, bootstrap by battle; baselines constant and HP. *Proposed hand-over to nate* | nate (alt: saliha) | 1.5–2, in parallel | log loss, Brier, reliability beat HP and constant after 2026-05-19 |
| 5 | **`LearnedValue` behind a flag**, batched (one `predict_proba` per scenario), falls back to the HP value on any error | derrick | 1.0 | same choices with the flag off; missing model file falls back |

Needs: nate's 20k-game extract and the team's yes on scikit-learn. **If the extract isn't on disk by ~02:00 UTC:** ship the HP value for the demo, show the model as an offline prediction result when it lands, and do step 6 instead.

## Stretch, in order (each behind a flag, default off)
| # | Step | Hours | Note |
|---|---|---|---|
| 6 | Opponent model: measured switch share first, then quantal response `(1-ε)·softmax(λ·u_opp) + ε·uniform`, cap 0.7 per reply; λ=0 is exactly today | 1.25–1.5 | zero think time; switch-rate count from replays: nate, 0.3 h |
| 7 | Margin in `select` against the optimiser's curse | 0.5 | only if step 1 shows most turns aren't near-ties |
| 8 | Scenario cells (one representative per speed/item/Tera/attack group, keep k ≤ 8) | 1.25–1.5 | only if per-scenario argmax disagrees on >~10% of turns |
| 9 | Process pool for the live demo (one task per scenario, ~3× lower wall clock on 4 workers; poke-engine holds the GIL, so processes not threads) + one shared deadline for forced-switch evaluation (today up to 5 × 3 s) | 1.5 + 0.3 | `workers=0` in the eval: processes cut latency, not total CPU |
| 10 | Depth-2 refine on the top ~6 rows × 4 columns, same EV operator at children, setup/Protect/recovery/best-switch rows always kept | 3.5–4.5 | +0.4–0.9 s; post-hackathon realistically |
| 11 | Maximin LP flag (root only) | 2 | report offline exploitability |

## Don't
- Don't prune candidates by one-ply dominance or poke-engine's `id` eval: both drop setup moves (verified on our test position).
- Don't build the instruction-list HP shortcut: it can't feed a learned value, which needs the real next state.
- Don't write a Python DUCT/CFR/MCTS: ~1 ms per cell in Python vs ~10⁵ iterations/s in Rust.

## Cut order and never-cut
**Cut first → last:** engine-MCTS arm · depth-2 · LP beyond offline exploitability · pool · scenario cells · margin · HGB (ship logistic) · opponent model.
**Never cut:** belief fixes + floor · the trace · a calibrated, held-out, baselined logistic (even if its wiring slips) · the HP fallback and `choose` never raising.

## What judges see
- **Prediction:** belief gain over the prior and over hard-filter-only (nats per reveal, with intervals); win-probability log loss, Brier and reliability vs constant and HP baselines.
- **Decision:** head-to-head vs SimpleHeuristics (300 games, Wilson + team bootstrap); ablations reported either way (HP vs learned value; uniform vs quantal); p50/p99 think time. Our 300-game A/B can't see differences under ~10 points, so claim no win-rate gain for refinements.
- **Honest limits:** one-ply EV agent with a learned leaf, not a Nash solver; "value before depth" rests on cost, not on Pokémon evidence (Foul Play, the strongest bot, searches deep with a hand-written eval); the learned value is trained on human continuations.

## Measure before trusting any estimate
All timings came from one fixture position under CPU load from a running eval. Re-measure on ≥100 real positions: p50/p99 per stage, per-scenario argmax disagreement, top-1/top-2 gap, featurizer cost per leaf, real opponent switch rate, fallback rate after the fixes, and the set-candidates diversity once `data/set_candidates.json` exists.
