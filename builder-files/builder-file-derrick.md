# Derrick: Decision layer (state intake, belief over opponent sets, simulate, value, selector, fallback)
**GitHub:** `RandomGeeb` · **Branch:** `derrick` · **Tool:** Claude Code · **Brief last updated:** 2026-10-24 21:10 UTC by saliha
**Spec:** the PRD (`OxHack-2026-PRD.md`) and `design-decision/*.md`. A bare § means the PRD; CLAUDE.md and this brief's own sections are always named.

## 0. How the agent reads this brief (every task)
1. `CLAUDE.md` is already loaded (don't re-read it); read this brief once. Follow both.
2. **Work `▶ Current tasks` top to bottom.** The order is the pass 9 build plan: two research agents plus an adversarial critic, using peer-reviewed papers, official docs and source, practitioner consensus, the current code and the PRD. **Decision-layer design choices are Derrick's:** every "Recommended" line below is research-backed advice he can accept, change or replace.
3. **Want a different route, more features or another decision in your area? Go ahead.** Your Claude always asks first: "Have you told the team? Who agreed?" (CLAUDE.md §2c). Changes to another builder's path or a shared contract wait for that owner's yes.
4. Before starting, read `progress.md`'s 📌 Open board (CLAUDE.md §2b). Rows To @derrick come first: tell the user, then resolve or schedule them.
5. Ship each task with the CLAUDE.md §7 sequence, then log it (CLAUDE.md §2b). Use the `debug` skill on every issue.
6. Times are **UTC** (UK clocks go back at 02:00 BST on Sunday). The research doc is saliha's and local only: ask her for a pass instead of searching for it.

**Task tags:** `[⚠ touches @name: what]` = changes someone else's area or a shared contract; get that owner's yes before merging (§2c). `[⏸ waits on @name: what]` = blocked until they deliver (a 📨 row on the Open board). `[🟠 your call]` = a design decision for the user (CLAUDE.md §1).

---

## 1. Ownership
**Owns:**
- `decision/`, `tests/`, `pyproject.toml`, `uv.lock`: the Python decision layer (poke-engine based)
- `design-decision/decision-layer.md`, `design-decision/decision/*.md`: its design (12 feature docs)
- `contracts/battle-state.md`, `contracts/battle_state.py`, `contracts/examples/`: the `BattleState` contract (as author; the bot layer fills it)

**Does NOT touch:**
| Area / path | Owner | Why it's theirs |
|---|---|---|
| `bot/` (Showdown connection, log parser, eval harness) | @saliha | bot layer |
| `data/` (set candidates, team pool, training sets) | @nate | data layer |
| PRD, CLAUDE.md, skills | @saliha (doc owner) | plan changes need the team (§2c) |

**Shared** (flag in `progress.md` ⚠️ Conflicts): `contracts/*`, `fixtures/*`.

## 2. Contract & Guardrails
**Scope contract.** Derrick builds the layer that turns a `BattleState` + the raw `|request|` into the best `Choice`, with every model (belief, opponent policy, value) swappable without touching the loop (`design-decision/decision-layer.md`).
- Run · Test: `uv run pytest --cov=decision` (numbers: `progress.md` → 📊 Latest).

**Out of scope:** the Showdown connection, log parsing and eval harness (bot layer); building set candidates and training data (data layer); voice; an own Rust hot path.

**Guardrails:**
- ⛔ **Off-plan → CLAUDE.md §2c.**
- Any change to `BattleState` field meaning is a ⚠️ row To @saliha (she writes the parser).
- **Key research finding [P9 D2]:** poke-engine's built-in `monte_carlo_tree_search` and `iterative_deepening_expectiminimax` hard-wire its Rust evaluation, so a learned value can't plug in without a Rust fork, and the expectiminimax matrix (NaN where pruned, pure maximin inside) can't feed the LP. The learned-value and LP story lives in our Python loop. The README's "Gen 4–8 only" line is stale.
- Never commit secrets.

---

## 3. ▶ Current tasks (2026-10-24 21:10 UTC, pass 9 build plan), in order
*Status: ⬜ not started · 🟡 in progress · ⏸ blocked · ✅ done · Hours = focused work. Total ≈ 13 h, the heaviest load: tasks marked "proposed hand-over" can move to nate or saliha if you say yes.*

1. ⬜ **Turn-time profile** (0.5 h; old task 7): p50 / p99 of one `choose` on real states. It sets the eval think budget (1.0 s proposed) and whether the MCTS arm (task 10) is worth building.
   - *Done when:* the numbers are in `progress.md` → 📊 Latest.
2. ✅ **Belief floor** (0.5 h) `[🟠 your call]` — done: floor 0.03 on the replay, reveals stay hard with the floor as the empty fallback (`progress.md` ff18c93)
   - **Recommended [P9 D1]:** in `_explains_turn`, drop a set that can't explain a turn to a small floor `eps` (0.02–0.05) instead of zero, so a rounding miss or an unlisted set doesn't wipe out the belief. **Alternative:** keep the hard zero (simpler, but fragile).
   - *Done when:* a test shows a contradicted set keeps weight `eps` and recovers when later turns fit it.
3. ⬜ **`build_state` on a parser-made `BattleState`** (old task 3; now unblocked: `from bot.parser import Parser, states_from_log` is on `main`).
   - *Done when:* `build_state` runs on parser output from a real game, with no hand-made fixture.
4. ⬜ **Expose the decision trace** `[⚠ touches @saliha: trace fields]` (old task 6): after `choose()`, `agent.last_trace` holds the top 3 options with scores, the chosen line's win probability, and the top sets per opponent Pokémon.
   - *Done when:* saliha's bot writes it every turn, at under 5% extra think time.
5. ⬜ **Belief on real priors** (old task 4) `[⏸ waits on @nate: set candidates]`: load `data/set_candidates.json` (per `contracts/set-candidates.md`) instead of the hand-made priors.
   - *Done when:* a full game runs on the real set file.
6. ⬜ **Batch the leaves** (1.5 h): refactor `Agent._evaluate` to collect every leaf state and score them in one call, plus a featurizer parity test (training features from `states_from_log` equal live features). The heuristic stays the default.
   - *Done when:* same choices as before on the test states, and the parity test passes.
7. ⬜ **Calibrated win-probability model** (4 h, timeboxed; old task 8) `[needs scikit-learn in pyproject.toml: add it when you begin]` `[🟠 your call: whether and how]` `[⏸ waits on @nate: 20k-game extract by 01:00 UTC]`
   - **Recommended [P9 D3 + critique]:** ship it as a standalone prediction product, not gated on any A/B. Baselines first (constant, HP heuristic; rating-only offline only, because the local server has no ratings). Then logistic regression, then `HistGradientBoostingClassifier` with monotone constraints if time allows. Use public-info features only. Pick Platt or isotonic calibration by validation log loss. Split by battle, time and player; test on games after 2026-05-19; bootstrap intervals by battle.
   - **Alternative:** a small neural net (slower to train and calibrate, no gain shown at this data size).
   - Model frozen by 06:00 UTC; shipping logistic only is a pass.
   - *Done when:* log loss, Brier and a reliability diagram beat the HP heuristic on the test split, and the agent can switch to the model with a flag.
8. ⬜ **Score the belief** (1.5 h) *(proposed hand-over to @nate)*: next-reveal log loss vs the prior and vs hard-filter-only, on held-out reveal events and on our eval games where the true opponent set is known. Not on pool teams: they come from the same usage stats, so the test would be circular [P9 critique].
   - *Done when:* the numbers, with intervals, are in `progress.md`.
9. ⬜ *(stretch)* **Maximin LP behind a flag, default off** (2 h; old task 9) `[🟠 your call]` `[needs scipy, which comes with scikit-learn]`
   - **Recommended [P9 D4 + critique]:** `scipy.optimize.linprog` (HiGHS) after iterated dominance deletion. Against fixed poke-env baselines it can't beat argmax-EV, so report offline exploitability. Run an A/B only against an adaptive opponent, and only if time remains.
10. ⬜ *(stretch, only if the one-ply agent is under ~85% vs SimpleHeuristics after saliha's smoke eval)* **poke-engine MCTS arm** (2.5 h): one MCTS per sampled state, summing visit shares (the Foul Play wiring), behind a flag. Self-play decides; keep it out of the headline.
11. ⬜ *(stretch)* **Scenario diversity** (1.5 h) [P9 D1]: the set-candidates contract multiplies independent marginals, so the top 5 scenarios are near-clones of the modal set; sample for diversity instead.

*Coach review moved to saliha's brief as a proposed hand-over (her task 9): needs your yes.*

**Seams** (same note in the other two briefs): the bot calls `agent.choose(request, battle_state)` in-process, one `Agent` per battle, blocking inside a shard process. Training states come from saliha's `states_from_log`, so features match the live bot (task 6's parity test). Nate's set file feeds task 5; his pairs feed task 7.

## 6a. Reference
- Research doc passes 1 (maths), 7 (design decisions) and 9 (`research_notes/pass9-decision-prediction.md`, `pass9-critique.md`); `design-decision/DESIGN.md` is the map.

## 4. Done log (newest first)
- ✅ **Feature 11, special requests** (decided by derrick 2026-10-24): type-matchup lead at preview (C), forced switch scored by the main loop (A). `decision/lead.py`, 144 tests, 100% coverage on `derrick` @ `a50936e`. `progress.md` 2026-10-24 19:26.
- ✅ **Merge `derrick` into `main`**: one clean commit `5e203fc` with the code and contracts only; 140 tests pass on `main`. Agreed by saliha, nate.
- ✅ **Task 1, core decision loop on dumb models** (`our_actions`, `opp_actions`, `simulate`, `value`, `build_state`, selector): 96 tests, 100% coverage; progress entry 2026-10-24 17:51.

## 5. Working-style notes for the agent
- Verbosity Level 0: options + a recommendation, no teaching notes. Flag scope creep at once.
- Hackathon pace: the smallest thing that passes its *Done when*; cut order is PRD §19.

## 6. Open blanks (fill when the chat or repo answers them, CLAUDE.md 🔁)
- Whether the HP/alive heuristic gets replaced by the learned model: Derrick's call (task 7).
- Yes/no on the proposed hand-overs (task 8 to nate, coach to saliha).
- Dependencies (notice, 2026-10-24): saliha adds `poke-env==0.16.1` to `pyproject.toml` for the bot; tasks 7 and 9 need `scikit-learn` (add it when you begin); nate's charts add `matplotlib`.
- Windows: `decision/state.py:9` and `decision/opponent.py:11` read JSON without `encoding="utf-8"`, so the suite only passes on Windows with `PYTHONUTF8=1`. A one-line fix each when you next touch them.

---
── Archived (superseded 2026-10-24 21:10 UTC by the pass 9 build plan — do NOT action) ──
- Old task 5 (pick the upgrade path) → split into tasks 7 (value model) and 9 (LP) above.
- Old tasks 6–9 (trace, profile, win probability, LP) → renumbered 4, 1, 7, 9 with the pass 9 designs.
- Old task 4 (belief layer) → the logic is built (🟡); real priors are task 5, scoring is task 8.
