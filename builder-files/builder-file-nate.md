# Nate: Data layer (ingestion, ratings, set candidates + priors, training sets)
**GitHub:** `aldrichbanas07` · **Branch:** `{{nate's branch}}` · **Tool:** Claude Code · **Brief last updated:** 2026-10-24 by saliha
**Spec:** the PRD (`OxHack-2026-PRD.md`) and `design/*.md`. A bare § means the PRD; CLAUDE.md and this brief's own sections are always named.

## 0. How the agent reads this brief (every task)
1. `CLAUDE.md` is already loaded (don't re-read it); read this brief once. Follow both.
2. **Only action `▶ Current tasks`**, top to bottom.
3. Before starting, read `progress.md`'s 📌 Open board (CLAUDE.md §2b). Rows To @nate come first: tell the user, then resolve or schedule them.
4. Ship each task with the CLAUDE.md §7 sequence, then log it (CLAUDE.md §2b). Use the `debug` skill on every issue.
5. Token budget (CLAUDE.md): Grep `OxHack-2026-research.md` by pass number, never read it whole; read only the `design/` doc for your layer.

**Task tags:** `[⚠ touches @name: what]` = changes someone else's area or a shared contract; get that owner's yes before merging (§2c). `[⏸ waits on @name: what]` = blocked until they deliver (a 📨 row on the Open board).

---

## 1. Ownership
**Owns:**
- `data/`: ingestion, storage, ladder snapshotter, offline outputs {{exact paths: not decided}}
- `design/data-layer.md`: its design (DRAFT, not team-agreed)

**Does NOT touch:**
| Area / path | Owner | Why it's theirs |
|---|---|---|
| `decision/`, `tests/`, `contracts/battle_state.py` | @derrick | decision layer |
| `bot/` | @saliha | bot layer |
| PRD, CLAUDE.md, skills | @saliha (doc owner) | plan changes need the team (§2c) |

**Shared** (flag in `progress.md` ⚠️ Conflicts): `contracts/*`, `fixtures/*`.

## 2. Contract & Guardrails
**Scope contract.** Nate builds what the decision layer consumes offline: **set candidates + priors per species** and **training sets** (`design/data-layer.md` §5), from replays and ratings.
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

1. ⬜ **Start the ladder snapshotter now** (top 500 from `pokemonshowdown.com/ladder/gen9ou.json`, scheduled, timestamped): it can't be backfilled.
   - *Done when:* snapshots accumulate with a timestamp per row and one run's output exists.
2. ⬜ **Ingest gen9ou replays** (HolidayOugi main, Metamon raw cross-check; dedupe on replay id; Elo from `|player|` lines) `[🟠 storage decision first]`
   - *Done when:* a gen9ou table keyed on replay id with both players' start Elo, queryable.
3. ⬜ **Set candidates + priors per species** (top 20-50 per species plus an "other" bucket; design §5a) `[⚠ touches @derrick: the output format he consumes]`
   - *Done when:* one format is agreed with Derrick, and a held-out game's revealed sets are covered at a stated rate.
4. ⬜ **Training sets + splits** (opponent-policy pairs from high-Elo replays, (state, winner) pairs, split by battle/time/player, Smogtours eval split) `[🟠 Elo cut-off, bot filtering]`
   - *Done when:* train/val/test files exist with a leakage check (no battle, player or team in two splits).
5. ⬜ **Bot filtering rule** (🟠 decision): how bot accounts are detected and dropped.

## 6a. Reference
- Research doc passes 1-3; `design/data-layer.md`; replay API `search.json?format=gen9ou&before=<uploadtime>`; no endpoint gives ladder ranks 501-1000.

## 4. Done log (newest first)
- (empty)

## 5. Working-style notes for the agent
- Verbosity Level 0: options + a recommendation, no teaching notes. Flag scope creep at once.
- Hackathon pace (25 h): the smallest thing that passes its *Done when*; the cut order is in the research doc's READ THIS FIRST.

## 6. Open blanks (fill when the chat or repo answers them, CLAUDE.md 🔁)
- Nate's branch name and exact owned paths.
- 🟠 storage, Elo cut-off, bot detection (`design/data-layer.md` §6).

---
── Archived (superseded <date> — do NOT action) ──
(none)
