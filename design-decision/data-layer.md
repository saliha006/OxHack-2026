# Data layer

> **Implementation audit: 25 October 2026.** Read [CURRENT-STATUS.md](../CURRENT-STATUS.md) for branch heads,
> local-only work and the evidence hierarchy. Back to the map: [DESIGN.md](DESIGN.md).

**Job:** build the offline set priors and public replay states consumed by decision and evaluation code. The shipped
pipeline uses local Parquet/DuckDB and Tiger/Postgres. Earlier ClickHouse, API-scraping and joint-set proposals are
superseded by the implementation described below; future work is labelled separately.

## 1. What exists, and where

| Area | Verified implementation |
|---|---|
| `main` at `bbb95d6` | `data/pipeline/{build_set_candidates,clean_battles,build_turns,load_tiger}.py`, their tests, committed `data/set_candidates.json`, `contracts/turns.md` |
| `nate-data` at `e6700d3` | Same data source and turns contract as audited `main`; later `main` changes are progress-log updates |
| `Data-stuff-(Nate)` at `6c5bf4b` | Historical name still present remotely; same data pipeline, predates the turns contract and later progress updates |
| `derrick` at `9f86111` | Adds Tiger-to-local JSONL export and replay action-agreement CLI; see [Backtesting](backtesting.md) |
| `Kenar-coherent-sets` | Adds a separate opt-in coherent-prior pipeline and evidence; see [CURRENT-STATUS.md](../CURRENT-STATUS.md) |
| Local `Kenar-mcts` work | Prediction/Tiger integration and evaluation experiments must be distinguished from pushed branch contents; see [CURRENT-STATUS.md](../CURRENT-STATUS.md) |

Source pins: [main data tree](https://github.com/saliha006/OxHack-2026/tree/bbb95d60fb57a01497aae370d8ca922c275bb79d/data),
[turns contract](https://github.com/saliha006/OxHack-2026/blob/bbb95d60fb57a01497aae370d8ca922c275bb79d/contracts/turns.md),
[Derrick's export](https://github.com/saliha006/OxHack-2026/blob/9f86111365ecefb510408dcfdf03aea925def085/backtest/tiger.py).

## 2. Replay cleaning and storage

`clean_battles.py` reads raw HolidayOugi replay Parquet by default, filters `formatid = 'gen9ou'`, parses each raw log,
and writes cleaned Parquet with Zstd compression. It keeps the newest upload per replay ID **within each input
file**; do not assume this alone proves global cross-file deduplication. Tiger primary keys prevent duplicate keys
on reload through `ON CONFLICT DO NOTHING`.

- Start Elo comes from each player's `|player|` line. The dataset's `rating` column is retained locally as
  `dataset_rating`, not substituted for either player's pre-game Elo.
- Teams are sorted preview species strings; leads are the first sent-out species. Preview can conceal a forme.
- Split: `smogtours-*` IDs are `eval`; other games from **2026-05-19** are `test`, earlier games are `train`.
- Freeze: games starting at or after **2026-10-24 11:00 UTC** (12:00 BST) are excluded.
- This is a replay ingestion pipeline. A deployed replay scraper, ladder scheduler and separate `players` table
  were not found in these audited branch trees.

`load_tiger.py` stores monthly hypertables in Tiger:

| Table | Key | Contents |
|---|---|---|
| `battles` | `(id, started_at)` | Players, pre-game Elos, teams/leads, result, length, format-source metadata |
| `battle_logs` | `(id, started_at)` | Full raw battle log, intentionally uncompressed |
| `turns` | `(battle_id, turn, started_at)` | Typed per-turn columns plus public `BattleState` in JSONB |

Local Parquet retains views, dataset rating and split; `battles` does not upload those three fields. `turns` retains
its split. Join tables on **both ID and `started_at`** so Tiger can prune monthly chunks. The turns DDL is generated
from the Parquet schema; a new column requires coordinating the existing database schema, not merely rerunning a
`CREATE TABLE IF NOT EXISTS`.

Sources: [cleaning](https://github.com/saliha006/OxHack-2026/blob/bbb95d60fb57a01497aae370d8ca922c275bb79d/data/pipeline/clean_battles.py),
[loading and DDL](https://github.com/saliha006/OxHack-2026/blob/bbb95d60fb57a01497aae370d8ca922c275bb79d/data/pipeline/load_tiger.py).

## 3. Public per-turn training extract

`build_turns.py` uses `bot.parser.Parser`, the live bot's parser, snapshotting at each `|turn|`. Each row holds the
state **before the turn**, the first logged action per side during the turn, and the eventual winner. `state.us`
is `p1`; requests and private exact sets are absent. A forced replacement after a faint has no separate turn row.

Defaults: **20,000 games**, seed **2026**, 75% train / 25% test. Eligibility requires rated games, both pre-game
Elos known, at least six turns and a winner. Train sampling starts **2025-01-01**. This is not a high-Elo-only sample
and does not implement a reliable bot-account filter.

Columns include active species/HP/status, alive and HP totals, active boosts, Tera availability, hazards/screens,
all twelve preview slots' species/HP/status, field, actions, Tera/faint indicators, first mover, crit, timing, split,
winner and full state. Slots follow each game's preview order; a slot number is not a stable feature between games.

The contract records **489,840 turns** from 20,000 games: train **361,437 turns / 15,000 games**, test **128,403 /
5,000**. These are repository-recorded build figures, not a fresh database count in this documentation refresh.
It also records `battles` and `battle_logs` at **2,506,142 games** each and raw logs at **9.2 GB**.

### Split and leakage limits

- No game appears in both recorded splits, but there is **no validation split yet** in this extract. Carve one off
  chronologically for tuning rather than choosing settings on test.
- **43%** of test games share a player with train and **38%** share an exact team. The recorded unseen subset has
  **1,909 games** sharing neither. Report full-test and unseen-subset metrics separately.
- The raw parser path is public and chronological, unlike a parsed dataset that backfills hidden sets. Parser
  coverage is still finite: malformed old HP strings can lose a fact, and rebuilt current-parser state can differ
  from a historically stored Tiger snapshot after parser fixes.
- Winner is a label, not a serving feature. `seconds_taken` includes both players' thinking and turn playback.
- The `eval` split rule exists in cleaned data, but the default turns builder samples only `train` and `test`.
  Do not describe its 20k extract as a tournament evaluation set.

Sources: [turn extraction](https://github.com/saliha006/OxHack-2026/blob/bbb95d60fb57a01497aae370d8ca922c275bb79d/data/pipeline/build_turns.py),
[contract, baselines and leakage query](https://github.com/saliha006/OxHack-2026/blob/bbb95d60fb57a01497aae370d8ca922c275bb79d/contracts/turns.md).

## 4. Current marginal set priors

`data/set_candidates.json` is already built and committed on `main`; it is not waiting for a format agreement.
The current file uses Smogon chaos **gen9ou, September 2026, cutoff 1825**. The recorded output is **243 species +
78 forme aliases**. The builder composes candidate sets from marginal frequencies rather than observed joint sets.

- Up to **30 candidates/species**, with weights normalized after selection. Item-stratified allocation preserves
  item mass rather than allowing the most common item's combinations to crowd out every alternative.
- Candidate pools: top **8 moves**, **4 items**, **2 abilities**, **3 Tera types**, **3 spreads**. Four-move
  combinations use inclusion/exclusion probabilities; remaining categories use products of shares.
- Usage fallback retains top **10 moves** and top **5** other categories/spreads. There is no explicit "other"
  candidate or team/player-conditioned weighting in this v1 file.
- **Assault Vest excludes status moves; Choice items do not.** Choice Scarf + Trick is valid. The older
  `contracts/set-candidates.md` sentence banning status moves on Choice items is stale relative to builder source.
- Emitted moves must exist in the committed move snapshot. This check is not a complete competitive-team validator.
- Formes can borrow a known parent's priors through `battleOnly`, `changesFrom` and guarded `baseSpecies` lookup;
  type differences stop ordinary regional formes from borrowing unsuitable base priors.

Source: [marginal-prior builder](https://github.com/saliha006/OxHack-2026/blob/bbb95d60fb57a01497aae370d8ca922c275bb79d/data/pipeline/build_set_candidates.py).

### Pending cutoff change and separate coherent priors

`main`'s latest progress entry proposes rebuilding from the same month's **cutoff 0** file. It records a local
200-game replay comparison: 1825 priors covered **125 games**, cutoff 0 covered **195**; action agreement was
**29.9%** versus **31.5%**. This proposal still waits on Nate's agreement/rebuild; the committed file and builder
default remain 1825. This is action agreement, not a win-rate improvement.

The coherent-prior work on `Kenar-coherent-sets` is a separate opt-in source and does not silently replace this
marginal file. Its completed comparison and promotion decision are in [CURRENT-STATUS.md](../CURRENT-STATUS.md).
Team-conditioned fallback by matching opponent teammates remains a proposal in the legacy data plan.

Source: [recorded cutoff experiment and pending decision](https://github.com/saliha006/OxHack-2026/blob/bbb95d60fb57a01497aae370d8ca922c275bb79d/progress.md).

## 5. Evaluation, access and setup

Recorded Tiger test baselines are constant 0.5 (**log loss 0.6931, Brier 0.25**) and the alive/HP heuristic
(**0.6407, 0.2246**). Recorded opponent switch rate is **19.2% of acted turns**. These are baselines/data statistics,
not evidence a learned value or opponent model has shipped on `main`.

Derrick's `backtest/` branch code reads a local Tiger dump, reconstructs a request-free decision, and measures
agreement against logged p1 choices while retaining the replay's fixed states. It is a **CLI without a dashboard**;
it does not establish counterfactual wins after alternative actions. See [Backtesting](backtesting.md).

Tiger access uses a local read-only `TIMESCALE_SERVICE_URL`; credentials stay outside git. No Tiger query belongs
inside `Agent.choose`: offline outputs are loaded before play. The branch's `backtest.tiger` CLI expects this
variable in the process environment; it does not itself call `load_dotenv`.

Main's `pyproject.toml` declares poke-engine/poke-env and pytest dev tools. The data pipeline additionally imports
**DuckDB, PyArrow, Psycopg and python-dotenv**, which are not all declared there. A fresh main checkout's plain
`uv sync` is therefore not a complete data setup. Inspect the chosen branch's dependency file before running it;
newer Kenar work has separate setup documentation. Rust is required to build the gen9/Tera poke-engine dependency.

Source: [main dependency declaration](https://github.com/saliha006/OxHack-2026/blob/bbb95d60fb57a01497aae370d8ca922c275bb79d/pyproject.toml).

## 6. Work still requiring evidence or a decision

- Rebuild/publish cutoff 0 priors if agreed, updating the source contract alongside the artifact.
- Establish validation and unseen-player/team reporting for learned models; retain chronological reveal scoring.
- Document an actual bot-filter rule and dataset licence/provenance in a data card.
- Verify completion of the legacy ladder snapshot, independently validated team pool and presentation charts;
  those deliverables were not found in the audited main/data branch trees.
- Keep coherent templates, marginal priors, public replay data and local Tiger experiments separately labelled.
