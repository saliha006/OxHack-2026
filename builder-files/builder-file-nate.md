> **Current-status correction — 25 October 2026.** Data ingestion, real marginal priors, Tiger tables and turns contract are built. Removing the 1825 cutoff remains a proposed separate rebuild, not the committed default. Earlier build tasks below are historical; current sources/splits are in DATA-CONTEXT. See [current branch status](../CURRENT-STATUS.md) and [data/training context](../DATA-CONTEXT.md).

# Nate: Data layer (set candidates + priors, team pool, training sets, charts, data card)
**GitHub:** `aldrichbanas07` · **Branch:** any branch with `nate` in its name (now `nate-data`: renamed from `Data-stuff-(Nate)` on 2026-10-25 01:20 UTC by saliha, same commits. One-time fix in your clone: `git fetch --prune && git branch -m "Data-stuff-(Nate)" nate-data && git branch -u origin/nate-data`. Never push to the old name; that would recreate it) · **Tool:** Claude Code · **Brief last updated:** 2026-10-24 21:10 UTC by saliha
**Spec:** the PRD (`OxHack-2026-PRD.md`) and `design-decision/*.md`. A bare § means the PRD; CLAUDE.md and this brief's own sections are always named.

## 0. How the agent reads this brief (every task)
1. `CLAUDE.md` is already loaded (don't re-read it); read this brief once. Follow both.
2. **Work `▶ Current tasks` top to bottom.** The order is the pass 9 build plan: two research agents plus an adversarial critic, using peer-reviewed papers, official docs and source, practitioner consensus, the current code and the PRD. Each task names the recommended design and the main alternative; data-layer choices are Nate's to accept or change.
3. **Want a different route, more features or another decision in your area? Go ahead.** Your Claude always asks first: "Have you told the team? Who agreed?" (CLAUDE.md §2c). Changes to another builder's path or a shared contract wait for that owner's yes.
4. Before starting, read `progress.md`'s 📌 Open board (CLAUDE.md §2b). Rows To @nate come first: tell the user, then resolve or schedule them.
5. Ship each task with the CLAUDE.md §7 sequence, then log it (CLAUDE.md §2b). Use the `debug` skill on every issue.
6. Times are **UTC** (UK clocks go back at 02:00 BST on Sunday). The research doc is saliha's and local only: ask her for a pass instead of searching for it.

**Task tags:** `[⚠ touches @name: what]` = changes someone else's area or a shared contract; get that owner's yes before merging (§2c). `[⏸ waits on @name: what]` = blocked until they deliver (a 📨 row on the Open board). `[🟠 your call]` = a design decision for the user (CLAUDE.md §1).

---

## 1. Ownership
**Owns:**
- `data/`: set candidates, team pool, training extract, charts, data card {{exact paths: confirm}}
- `design-decision/data-layer.md`: its design (DRAFT, not team-agreed)

**Does NOT touch:**
| Area / path | Owner | Why it's theirs |
|---|---|---|
| `decision/`, `tests/`, `contracts/battle_state.py` | @derrick | decision layer |
| `bot/` | @saliha | bot layer |
| PRD, CLAUDE.md, skills | @saliha (doc owner) | plan changes need the team (§2c) |

**Shared** (flag in `progress.md` ⚠️ Conflicts): `contracts/*`, `fixtures/*`.

## 2. Contract & Guardrails
**Scope contract.** Nate builds what the other two layers consume offline: **set candidates + priors per species**, the **team pool**, and the **training pairs**, plus the charts and data card that prove them.
- Per-player Elo comes from the log's `|player|` line, NOT the dataset `rating` column. Elo is offline-only (the local server has none), so it's for baselines and filtering, never a serving feature.

**Out of scope:** the decision loop, the Showdown bot, coaching text, voice; ClickHouse; scraping Showdown's API (the test set comes from HolidayOugi).

**Guardrails:**
- ⛔ **Off-plan → CLAUDE.md §2c.**
- Split every evaluation by battle id, time and player. The test set is games after 2026-05-19.
- Public-only features parsed from raw logs: Metamon's parsed replays back-fill hidden info from the end of the battle (look-ahead).
- Never commit secrets or data files.

---

## 3. ▶ Current tasks (2026-10-24 21:10 UTC, pass 9 build plan), in order
*Status: ⬜ not started · 🟡 in progress · ⏸ blocked · ✅ done · Hours = focused work*

1. ⬜ **Set candidates + priors per species** (old task 3; **first: no priors, no agent**) `[⚠ touches @derrick: the format he consumes]`
   - Build `data/set_candidates.json` from Smogon chaos stats `gen9ou-1825`, 2026-09, in the shape of `contracts/set-candidates.md` (drafted by Derrick; `tests/test_set_candidates_contract.py` checks a file against it).
   - *Done when:* the file passes the contract test and is on `main` by 01:00 UTC.
2. ⬜ **Ladder snapshot: one `curl`** (0.1 h; old task 1). **Recommended [P9 B6]:** cut the scheduler. Save `pokemonshowdown.com/ladder/gen9ou.json` once with a timestamp, then move on (Elo-from-decisions is parked).
3. ⬜ **Team pool + our team** (1.5 h; old task 6) `[🟠 your call]`
   - **Recommended [P9 B2 + critique]:** sample 60 seeded teams from `jakegrigsby/metamon-teams` `hl_05_26/gen9ou` with `random.Random(seed)`. Validate each with Showdown's `validate-team`, then drop any that Derrick's adapter / poke-engine can't represent (log which). Write a manifest. Our fixed team is one of the `competitive/gen9ou` expert sample teams, picked with saliha and derrick after ~20 games.
   - **Rejected:** poke-env's `generate_team` / `SmogonStatsTeambuilder`, which don't enforce legality. Showdown's `generate-team gen9ou` throws locally.
   - *Done when:* every kept team validates and runs through `build_state`, and the seed reproduces the pool.
4. ⬜ **Training extract: (state, winner) pairs** (3 h; old tasks 2 + 4) `[⏸ waits on @saliha: states_from_log is on main]` `[🟠 your call: storage]`
   - **Recommended [P9 B4 + critique]:** Metamon raw replays, 5–8 shards, for train and validation; HolidayOugi part 13 for the test set (games after 2026-05-19). Cap at about 100k games. Store as plain Parquet + DuckDB. Build per-turn states with saliha's `states_from_log` (one parser, so features match the live bot). Split by battle, time and player, with a leakage check (no battle, player or team in two splits). Plot a learning curve to show the size is enough.
   - **Rejected:** ClickHouse (a server to run, overkill at this size); 300k games (no time); scraping the replay API.
   - Bot filtering (old task 5): a simple, stated rule is enough (e.g. drop accounts with a bot-like name or games under N turns); write the rule on the data card.
   - **First 20k-game extract to derrick by 01:00 UTC**; full extract by 04:00 UTC.
   - *Done when:* train/val/test Parquet files exist with the leakage check passing.
5. ⬜ **Eval and demo charts** (old task 7), from saliha's `runs/*.jsonl` and `runs/eval-*.jsonl`: win-rate bars with 95% intervals per leg; one game's per-turn win-probability curve; the reliability diagram for derrick's model. Pre-rendered PNGs with matplotlib `[needs matplotlib in pyproject.toml: add it when you begin, with a ⚠️ row to @derrick]`.
   - *Done when:* one command regenerates all three, and they run on the smoke-eval results tonight.
6. ⬜ **Data card** (old task 8): datasets, sizes, date ranges, splits, licence notes, bot-filter rule, eval think budget.
   - *Done when:* every number traces to a query or a file.
7. ⬜ *(proposed hand-over from @derrick, needs his yes)* **Score the belief + the model's evaluation figures** (1.5 h): next-reveal log loss of derrick's belief vs the prior on held-out reveals and our eval games (not on pool teams: circular), plus the log loss / Brier / reliability figures for his model.

**Seams** (same note in the other two briefs): saliha's `states_from_log` is the one way logs become `BattleState`s, so training features match the live bot. Derrick consumes the set file (task 1) and the pairs (task 4); saliha's eval consumes the team pool (task 3).

## 6a. Reference
- Research doc passes 2, 3 and 9 (`research_notes/pass9-bot-data-eval.md`, `pass9-critique.md`); `design-decision/data-layer.md`; `contracts/set-candidates.md`.

## 4. Done log (newest first)
- (empty)

## 5. Working-style notes for the agent
- Verbosity Level 0: options + a recommendation, no teaching notes. Flag scope creep at once.
- Hackathon pace: the smallest thing that passes its *Done when*; cut order is PRD §19.

## 6. Open blanks (fill when the chat or repo answers them, CLAUDE.md 🔁)
- Exact `data/` paths.
- 🟠 storage (Parquet + DuckDB recommended), bot-filter rule.

---
── Archived (superseded 2026-10-24 21:10 UTC by the pass 9 build plan — do NOT action) ──
- Old task 1 (ladder snapshotter, scheduled) → one `curl` (task 2); Elo-from-decisions is parked.
- Old task 2 (ingest gen9ou replays, HolidayOugi main) → task 4 (Metamon raw shards for train/val, HolidayOugi part 13 for test, ~100k games).
- Old tasks 3, 6, 7, 8 → tasks 1, 3, 5, 6. Old task 5 (bot filtering) → folded into task 4. Old task 4 (training sets) → task 4.
