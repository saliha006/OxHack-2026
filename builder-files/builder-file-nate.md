# Nate: Data layer (ingestion, ratings, set candidates + priors, training sets)
**GitHub:** `aldrichbanas07` · **Branch:** `{{nate's branch}}` · **Tool:** Claude Code · **Brief last updated:** 2026-10-24 by saliha
**Spec:** the PRD (`OxHack-2026-PRD.md`) and `design-decision/*.md`. A bare § means the PRD; CLAUDE.md and this brief's own sections are always named.

## 0. How the agent reads this brief (every task)
1. `CLAUDE.md` is already loaded (don't re-read it); read this brief once. Follow both.
2. **Only action `▶ Current tasks`**, top to bottom.
3. Before starting, read `progress.md`'s 📌 Open board (CLAUDE.md §2b). Rows To @nate come first: tell the user, then resolve or schedule them.
4. Ship each task with the CLAUDE.md §7 sequence, then log it (CLAUDE.md §2b). Use the `debug` skill on every issue.
5. Token budget (CLAUDE.md): read only the `design-decision/` doc for your layer. The research doc is saliha's and local only: ask her for a pass instead of searching for it.

**Task tags:** `[⚠ touches @name: what]` = changes someone else's area or a shared contract; get that owner's yes before merging (§2c). `[⏸ waits on @name: what]` = blocked until they deliver (a 📨 row on the Open board).

---

## 1. Ownership
**Owns:**
- `data/`: ingestion, storage, ladder snapshotter, offline outputs {{exact paths: not decided}}
- `design-decision/data-layer.md`: its design (DRAFT, not team-agreed)

**Does NOT touch:**
| Area / path | Owner | Why it's theirs |
|---|---|---|
| `decision/`, `tests/`, `contracts/battle_state.py` | @derrick | decision layer |
| `bot/` | @saliha | bot layer |
| PRD, CLAUDE.md, skills | @saliha (doc owner) | plan changes need the team (§2c) |

**Shared** (flag in `progress.md` ⚠️ Conflicts): `contracts/*`, `fixtures/*`.

## 2. Contract & Guardrails
**Scope contract.** Nate builds what the decision layer consumes offline: **set candidates + priors per species** and **training sets** (`design-decision/data-layer.md` §5), from replays and ratings.
- Research verdict (research doc, pass 2): main data = `HolidayOugi/pokemon-showdown-replays` (gen9ou ≈ 2.5M replays, raw usernames, no licence stated); Metamon raw (pseudonymised) as cross-check. Metamon's 28.5 GB parsed set is not needed.
- Per-player Elo comes from the log's `|player|` line, NOT the dataset `rating` column (that is the lower player's post-game rating). Elo is floored at 1000 (left-censored).

**Out of scope:** the decision loop, the Showdown bot, coaching text, voice.

**Guardrails:**
- ⛔ **Off-plan → CLAUDE.md §2c.** Ask *"Has the whole team agreed? Who?"* first.
- Split every evaluation by battle id, time and player. The test set is Showdown API games after 2026-05-19; Smogtours is a separate eval split (research doc, pass 3).
- Use public-only features parsed from raw logs: Metamon's parsed replays back-fill hidden info from the end of the battle (look-ahead).
- Rate-limit and cache every Showdown request. Showdown's terms say nothing about crawling (neither permission nor ban found), so stay polite.
- Storage is a 🟠 decision (ClickHouse vs lighter). Filtering to gen9ou columns should keep it well under 30 GB. Never commit secrets or data files.

---

## 3. ▶ Current tasks (2026-10-24), in order
*Status: ⬜ not started · 🟡 in progress · ⏸ blocked · ✅ done*

**Added 2026-10-24 19:45 by saliha (demo plan; pending the team's yes)**
6. ⬜ **Team pool** (`data/teams/`, packed format): ~60 seeded gen9ou teams from poke-env's `generate_team("gen9ou", ..., rng=Random(seed))` or `SmogonStatsTeambuilder.from_format("gen9ou", month="2026-09", cutoff=1825)`, validated against the local server (`/vtm gen9ou` or Showdown's `TeamValidator`); drop failures (a test run passed 39 of 40). One becomes our fixed team (saliha and derrick pick); the rest are the evaluation opponents.
   - *Done when:* every kept team validates, and the seed reproduces the pool.
7. ⬜ **Eval and demo charts**, from saliha's `runs/*.jsonl` and `runs/eval-*.json`: win-rate bars with 95% intervals per baseline; one game's per-turn win-probability curve; a reliability diagram for the win-probability model.
   - *Done when:* one command regenerates all three charts, and they go into the demo.
8. ⬜ **Data card**: one table for the demo and Devpost (datasets, sizes, date ranges, splits, licence notes).
   - *Done when:* every number in it traces to a query or a file.

**Seams** (same note in the other two briefs): saliha's parser (her task 3) is the one way logs become `BattleState`s, so training features match the live bot. Derrick consumes the set file and the (state, winner) pairs.

1. ⬜ **Start the ladder snapshotter now** (top 500 from `pokemonshowdown.com/ladder/gen9ou.json`, scheduled, timestamped): it can't be backfilled.
   - *Done when:* snapshots accumulate with a timestamp per row and one run's output exists.
2. ⬜ **Ingest gen9ou replays** (HolidayOugi main, Metamon raw cross-check; dedupe on replay id; Elo from `|player|` lines) `[🟠 storage decision first]`
   - *Done when:* a gen9ou table keyed on replay id with both players' start Elo, queryable.
3. ⬜ **Set candidates + priors per species** (top 20-50 per species plus an "other" bucket; design §5a) `[⚠ touches @derrick: the output format he consumes]`
   - *Done when:* one format is agreed with Derrick, and a held-out game's revealed sets are covered at a stated rate.
   - *Note 2026-10-24 (saliha):* the format is now drafted as `contracts/set-candidates.md` / `set_candidates.py` on `main`; `tests/test_set_candidates_contract.py` checks a file against it.
4. ⬜ **Training sets + splits** (opponent-policy pairs from high-Elo replays, (state, winner) pairs, split by battle/time/player, Smogtours eval split) `[🟠 Elo cut-off, bot filtering]`
   - *Done when:* train/val/test files exist with a leakage check (no battle, player or team in two splits).
   - *Note 2026-10-24 (saliha):* build the per-turn states with saliha's parser (her task 3), not a second parser `[⏸ waits on @saliha]`. Derrick's calibrated win-probability model trains on these pairs.
5. ⬜ **Bot filtering rule** (🟠 decision): how bot accounts are detected and dropped.

## 6a. Reference
- Research doc passes 1-3; `design-decision/data-layer.md`; replay API `search.json?format=gen9ou&before=<uploadtime>`; no endpoint gives ladder ranks 501-1000.

## 4. Done log (newest first)
- (empty)

## 5. Working-style notes for the agent
- Verbosity Level 0: options + a recommendation, no teaching notes. Flag scope creep at once.
- Hackathon pace (25 h): the smallest thing that passes its *Done when*; the cut order is in the research doc's READ THIS FIRST.

## 6. Open blanks (fill when the chat or repo answers them, CLAUDE.md 🔁)
- Nate's branch name and exact owned paths.
- 🟠 storage, Elo cut-off, bot detection (`design-decision/data-layer.md` §6).

---
── Archived (superseded <date> — do NOT action) ──
(none)
