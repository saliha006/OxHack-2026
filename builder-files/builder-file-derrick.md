# Derrick: Decision layer (state intake, belief over opponent sets, simulate, value, selector, fallback)
**GitHub:** `RandomGeeb` · **Branch:** `derrick` · **Tool:** Claude Code · **Brief last updated:** 2026-10-24 by saliha
**Spec:** the PRD (`OxHack-2026-PRD.md`) and `design/*.md`. A bare § means the PRD; CLAUDE.md and this brief's own sections are always named.

## 0. How the agent reads this brief (every task)
1. `CLAUDE.md` is already loaded (don't re-read it); read this brief once. Follow both.
2. **Only action `▶ Current tasks`**, top to bottom.
3. Before starting, read `progress.md`'s 📌 Open board (CLAUDE.md §2b). Rows To @derrick come first: tell the user, then resolve or schedule them.
4. Ship each task with the CLAUDE.md §7 sequence, then log it (CLAUDE.md §2b). Use the `debug` skill on every issue.
5. Token budget (CLAUDE.md): Grep `OxHack-2026-research.md` by pass number, never read it whole; read only the `design/` doc for your layer.

**Task tags:** `[⚠ touches @name: what]` = changes someone else's area or a shared contract; get that owner's yes before merging (§2c). `[⏸ waits on @name: what]` = blocked until they deliver (a 📨 row on the Open board).

---

## 1. Ownership
**Owns:**
- `decision/`, `tests/`, `pyproject.toml`, `uv.lock`: the Python decision layer (poke-engine based)
- `design/decision-layer.md`, `design/decision/*.md`: its design (12 feature docs)
- `contracts/battle-state.md`, `contracts/battle_state.py`, `contracts/examples/`: the `BattleState` contract (as author; the bot layer fills it)

**Does NOT touch:**
| Area / path | Owner | Why it's theirs |
|---|---|---|
| `bot/` (Showdown connection, log parser) | @saliha | bot layer |
| `data/` (ingestion, set candidates, training sets) | @nate | data layer |
| PRD, CLAUDE.md, skills | @saliha (doc owner) | plan changes need the team (§2c) |

**Shared** (flag in `progress.md` ⚠️ Conflicts): `contracts/*`, `fixtures/*`.

## 2. Contract & Guardrails
**Scope contract.** Derrick builds the layer that turns a `BattleState` + the raw `|request|` into the best `Choice`, with every model (belief, opponent policy, value) swappable without touching the loop (`design/decision-layer.md`).
- Feature docs 01-12 under `design/decision/`: state intake, set priors, belief (hard filter, soft reweight), set sampling, our/opp actions, simulate, value, selector, special requests, budget fallback.
- Run · Test: `uv run pytest --cov=decision` (96 tests, 100% coverage so far).

**Out of scope:** the Showdown connection and log parsing (bot layer); building set candidates and training data (data layer); voice and coaching text.

**Guardrails:**
- ⛔ **Off-plan → CLAUDE.md §2c.** Ask *"Has the whole team agreed? Who?"* first.
- Any change to `BattleState` field meaning is a ⚠️ row To @saliha (she writes the parser).
- Research-backed upgrades, in order (research doc, pass 1): calibrated gradient-boosted value model replacing the HP heuristic; per-turn maximin LP instead of argmax-EV; Bayesian belief + quantal-response opponent (largest, cut first). Each is a 🟠 decision for the user.
- Never commit secrets.

---

## 3. ▶ Current tasks (2026-10-24), in order
*Status: ⬜ not started · 🟡 in progress · ⏸ blocked · ✅ done*

**Added 2026-10-24 19:45 by saliha (demo plan; pending the team's yes)**
6. ⬜ **Expose a decision trace** `[⚠ touches @saliha: trace fields]`: after `choose()`, make available the top 3 options with scores, the chosen line's value / win-probability estimate, and the top sets per opponent Pokémon (e.g. `agent.last_trace`).
   - *Done when:* saliha's bot writes it every turn (her task 5), at under 5% extra think time.
7. ⬜ **Turn-time profile** (PRD recommends enumerating everything first; Derrick's call): read p50 / p99 from saliha's eval runs; turn on the Tera / status-move pruning only if p99 > 2.5 s.
   - *Done when:* the numbers are in `progress.md` → 📊 Latest.
8. ⬜ **Calibrated win probability** `[🟠 Derrick's call: whether and how; ⏸ waits on @nate: (state, winner) pairs]`: the "prediction" half of the HRT pitch.
   - *Done when:* log loss, Brier score and a reliability check beat the HP heuristic on the test split, and the bot can switch to it with a flag.
9. ⬜ **Maximin LP behind a flag** (PRD lists it as the next selector upgrade; Derrick's call, incl. the solver dependency).
   - *Done when:* an A/B over 100+ games in saliha's harness, with intervals, says keep or drop.

**Seams** (same note in the other two briefs): the bot calls `agent.choose(request, battle_state)` in-process, one `Agent` per battle. Training states come from saliha's parser, so features match the live bot.

1. ✅ **Core decision loop on dumb models** (`our_actions`, `opp_actions`, `simulate`, `value`, `build_state`, selector): 96 tests, 100% coverage on branch `derrick`; progress entry 2026-10-24 17:51.
3. ⏸ **Opponent side from real parsed logs** `[⏸ waits on @saliha: the parser filling BattleState, incl. the last_move reset on switch]`
   - *Done when:* `build_state` runs on a parser-produced `BattleState` from a real game, no hand-made fixture.
4. ⬜ **Belief layer (hard filter, soft reweight, sampling)** `[⏸ waits on @nate: set candidates + priors per species]`
   - *Done when:* next-reveal log loss beats the uniform-prior baseline on held-out games.
5. ⬜ **Pick and build the upgrade path** (calibrated value model, maximin LP): a 🟠 handoff to the user first.
   - *Done when:* the user picked, and exploitability / log loss is reported against the current baseline.
   - *Note 2026-10-24 (saliha):* split by the 2026-10-24 decisions into tasks 8 (value model) and 9 (maximin LP) above.

## 6a. Reference
- Research doc passes 1 (maths) and 7 (Showdown protocol + poke-engine); `design/DESIGN.md` is the map.

## 4. Done log (newest first)
- ✅ **Feature 11, special requests** (decided by derrick 2026-10-24): type-matchup lead at preview (C), forced switch scored by the main loop (A). `decision/lead.py`, 144 tests, 100% coverage on `derrick` @ `a50936e`. Full-game *Done when* waits on @saliha's parser (task 3). `progress.md` 2026-10-24 19:26.
- ✅ **Merge `derrick` into `main`**: one clean commit `5e203fc` with the code and contracts only (no shared docs in main's history); 140 tests pass on `main`. Agreed by saliha, nate. `progress.md` 2026-10-24 entries' Where lines updated.

## 5. Working-style notes for the agent
- Verbosity Level 0: options + a recommendation, no teaching notes. Flag scope creep at once.
- Hackathon pace (25 h): the smallest thing that passes its *Done when*; the cut order is in the research doc's READ THIS FIRST.

## 6. Open blanks (fill when the chat or repo answers them, CLAUDE.md 🔁)
- Whether the HP/alive heuristic gets replaced by a learned value model: Derrick's call (task 8).
- Decision-layer design choices are Derrick's; the 2026-10-24 PRD decisions on selector, pruning, lead and forced switch are recommendations he can override.

---
── Archived (superseded <date> — do NOT action) ──
(none)
