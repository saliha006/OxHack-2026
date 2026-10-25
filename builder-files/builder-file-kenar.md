> **Status, 2026-10-25 ~10:00 UTC.** Your MCTS is the decision layer on `main` (PR #1, 07:01) and the demo bot's default: 8 worlds × 150 ms, 1 engine thread, `reliable` belief. Coherent priors stay opt-in. How the system works today: PRD v4 (§7, §10); evidence pins: `CURRENT-STATUS.md`.

# Kenar: Search + prediction (MCTS decision layer, belief and set-prior experiments, offline prediction and diagnostics)
**GitHub:** `kxnar` · **Branches:** `Kenar-mcts`, `Kenar-coherent-sets` (also on GitHub: `Kenar-coherent-v2`, `Kenar-merge-ready`, `Kenar-foulplay-eval`) · **Tool:** {{tool}} · **Brief created:** 2026-10-25 ~10:00 UTC by saliha
**Spec:** the PRD (`OxHack-2026-PRD.md`) and `design-decision/*.md`. A bare § means the PRD; CLAUDE.md and this brief's own sections are always named.

## 0. How the agent reads this brief (every task)
1. `CLAUDE.md` is already loaded (don't re-read it); read this brief once. Follow both.
2. **Work `▶ Current tasks` top to bottom.** Search and prediction design choices in your paths are yours to propose; anything that changes `decision/` behaviour is agreed with @derrick until the ownership split is settled (§1).
3. **Want a different route, more features or another decision in your area? Go ahead.** Your Claude always asks first: "Have you told the team? Who agreed?" (CLAUDE.md §2c). Changes to another builder's path or a shared contract wait for that owner's yes.
4. Before starting, read `progress.md`'s 📌 Open board (CLAUDE.md §2b). Rows To @kenar come first: tell the user, then resolve or schedule them.
5. Ship each task with the CLAUDE.md §7 sequence, then log it (CLAUDE.md §2b). Use the `debug` skill on every issue.
6. Times are **UTC**. The research doc is saliha's and local only: ask her for a pass instead of searching for it.

**Task tags:** `[⚠ touches @name: what]` = changes someone else's area or a shared contract; get that owner's yes before merging (§2c). `[⏸ waits on @name: what]` = blocked until they deliver (a 📨 row on the Open board). `[🟠 your call]` = a design decision for the user (CLAUDE.md §1).

---

## 1. Ownership
**Authored on `main`** (PR #1 and later; confirm the split with the team):
- `decision/search.py` (search worker + native MCTS), `decision/root_mixing.py`, `decision/lead_model.py`, and most of the MCTS changes in `decision/agent.py`, `belief.py`, `adapter.py` and `search_policy.py`
- `prediction/` (offline win-probability model, belief and action scoring)
- `evaluation/` (MCTS studies, team reservations, diagnostics) and `analysis/` (loss mining, openings, no-progress audit)
- `docs/` (MCTS provenance), `data/curated-v1/`, `data/pipeline/import_curated_sets.py`, `data/pipeline/reveal_evidence.py`

**Shared, ownership TBC** (PRD §0 Pending): `decision/` with @derrick (the 👥 Team table still lists him); the curated-set files sit in @nate's `data/`.

**Does NOT touch:**
| Area / path | Owner | Why it's theirs |
|---|---|---|
| `bot/` (connection, parser, demo, eval harness) | @saliha | bot layer |
| `data/pipeline/` (except your two scripts), `data/set_candidates.json`, Tiger tables | @nate | data layer |
| `pyproject.toml`, `uv.lock` | @derrick | dependencies come with a ⚠️ row to him |
| PRD, CLAUDE.md, skills | @saliha (doc owner) | plan changes need the team (§2c) |

**Shared** (flag in `progress.md` ⚠️ Conflicts): `contracts/*`.

## 2. Contract & Guardrails
**Scope contract.** Kenar builds the search that turns `BattleState` + the raw request into a choice through `agent.choose(request, battle_state)` inside the 3 s budget, plus the offline studies that say whether a change helps.
- The demo and the trace read `agent.last_trace` (worlds, own and opponent support, sampled worlds, fallback reason, timings): renaming or removing those fields is a ⚠️ row To @saliha.
- Run · Test: `uv run pytest --cov=decision` (the `tests/` suite); prediction needs the `prediction` dependency group. Numbers: `progress.md` → 📊 Latest.

**Out of scope:** the Showdown connection, parser and eval harness (bot layer); building the default priors and Tiger tables (data layer); public ladder play.

**Guardrails:**
- ⛔ **Off-plan → CLAUDE.md §2c.**
- Visit shares are not calibrated win probabilities; never present them as such (PRD §2).
- `prediction/` stays out of search until a model beats the HP heuristic on held-out games (it doesn't yet: 0.6600 vs 0.6348).
- Tiger downloading and training stay paused unless the team agrees otherwise (`CURRENT-STATUS.md`).
- A new default (flag on by default, new priors) needs a head-to-head win over `mcts8` with a Wilson lower bound above 50% (PRD §0).
- Never commit secrets or data files.

---

## 3. ▶ Current tasks (2026-10-25 ~10:00 UTC)
*Demo freeze 10:30 UTC (no code after it), submission 12:00 UTC. Status: ⬜ not started · 🟡 in progress · ⏸ blocked · ✅ done*

1. 🟡 **Eval slice:** started the fphard pairings (seed 101, 2 shards) at 08:20, then moved to `mcts-headline` (`mcts8` vs SimpleHeuristics, seed 101) around 09:00, after backing up to `runs/backup-0900/`. Stop at 09:45 and send every `runs/eval/kenar-*.jsonl` to saliha.
   - *Done when:* saliha has the files and the game count.
2. ⬜ **Answer the ⚠️ row on the Open board:** saliha's opt-in Tera gate in your `decision/agent.py` + `search_policy.py` (`tera_min_wins`, default 0 = off). Keep it or ask for it to be reverted.
3. ⬜ **Agree the `decision/` ownership split with @derrick**, then tell saliha so the 👥 Team table and both briefs match.
4. ⬜ **After the demo:** `Kenar-coherent-v2` (conservative coherent priors, panels unfinished) stays off `main` until then; what happens to it next is your call with the team.

## 6a. Reference
- PRD §7.1–7.3, §7.5, §17; `design-decision/decision-layer.md`, `predictions.md`, `coherent-sets.md`; `CURRENT-STATUS.md` (MCTS measurements and their limits).

## 4. Done log (newest first)
- ✅ **MCTS decision layer merged to `main` as the default** (PR #1, 2026-10-25 07:01): 8 whole-team worlds × 150 ms native MCTS in a supervised worker, `reliable` belief, `one_ply` kept as a comparator. *(Logged by saliha from `progress.md` 📊 Latest.)*
- ✅ **Coherent priors, published opt-in** (`Kenar-coherent-sets`): 556 variants mixed 50/50 with usage candidates; complete screening 25W–35L (Wilson 30.1–54.3%), so it stays opt-in. *(From `CURRENT-STATUS.md`.)*
- ✅ **Prediction public study** (`prediction/`): calibrated logistic model, log loss 0.6600 vs the HP heuristic's 0.6348 on the test split; belief next-reveal loss favours the prior. *(From `CURRENT-STATUS.md`.)*
- ✅ **MCTS pilot reliability:** 1,288 calls, 7,863/7,863 usable worlds, no fallback or decision over 3 s. *(From `CURRENT-STATUS.md`.)*

## 5. Working-style notes for the agent
- Verbosity Level 0: options + a recommendation, no teaching notes. Flag scope creep at once.
- Hackathon pace: the smallest thing that passes its *Done when*; cut order is PRD §19.

## 6. Open blanks (fill when the chat or repo answers them, CLAUDE.md 🔁)
- Tool ({{tool}}).
- The `decision/` ownership split with @derrick.
- Which of your remote branches stay live after the demo, and which are archives.

---
