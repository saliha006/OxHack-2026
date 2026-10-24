# Data layer

> **DRAFT, not team-agreed.** Back to the map: [DESIGN.md](DESIGN.md).

**Job:** collect past battles and player ratings, store them, and turn them into the two things the decision layer
needs offline: **set candidates + priors** and **training sets** for the learned models.

---

## 1. Sources

| Source | Use | Notes |
|---|---|---|
| `jakegrigsby/metamon-raw-replays` (Hugging Face) | Bulk historical battles | ~2.68M rows, v6 cutoff 2026-05-19; usernames pseudonymised; thin 2021–2024 coverage |
| Showdown replay API (`replay.pokemonshowdown.com`) | Games after the archive cutoff | `search.json?format=gen9ou&before=<uploadtime>`, `/<id>.json`, `/<id>.log`; public uploads only |
| Ladder API (`pokemonshowdown.com/ladder/gen9ou.json`, `/users/<id>.json`) | Player skill snapshots | Top 500 only (cut-off ~1636 Elo on 2026-10-24); snapshot on a schedule |
| Smogtours replays (`smogtours-gen9ou-*`) | High-skill eval split | Links scraped from Smogon tournament threads; mostly unrated |
| Smogon chaos JSON (`smogon.com/stats/<YYYY-MM>/chaos/gen9ou-1825.json`) | Set priors | Marginal frequencies of moves / items / abilities / Tera / spreads, plus teammates |

Evidence grades for each source go in the research doc (CLAUDE.md §10), not here.

## 2. Ratings

- Start Elo per player: the `|player|p1|<name>|<avatar>|<elo>` log line.
- Post-game change: the `|raw|` lines.
- The ladder snapshots only cover the top 500, so ratings below ~1636 come from logs alone.

## 3. Ingestion

- **Rate-limit and cache every Showdown request.** {{limit and cache location: not decided}}
- Dedupe on replay id (the archive and the live API overlap after the cutoff).
- **Filter bots out of training data.** {{how bots are detected: not decided}}

## 4. Storage (ClickHouse, proposed)

| Table | Key | Holds |
|---|---|---|
| `battles` | replay id | Format, upload time, players, ratings, raw log, {{…}} |
| `players` | {{user id + snapshot time?}} | Ladder snapshots |

🟠 Schema, retention and whether raw logs are stored in full are all still decisions.

## 5. Offline outputs (what the decision layer consumes)

### 5a. Set candidates + priors (per species)
Candidates, best source first:
1. Metamon `replay_stats` joint sets.
2. Smogon analysis sample sets.
3. Sets composed from chaos marginals, with consistency rules (Choice item / Assault Vest ⇒ no status moves; legal
   moves only).

Keep the **top 20–50** per species. Prior weights come from the rating band (the 1825 file), teammate correlations, and
player history when the sample is large enough. Add a small **"other" bucket** built from marginals for off-meta sets.

### 5b. Training sets
- **Opponent policy:** (state, action actually taken) pairs from high-Elo replays. {{Elo threshold: not decided}}
- **Value model:** (state, eventual winner) pairs.
- **Eval split:** Smogtours games, kept out of training.

## 6. Open decisions
- 🟠 ClickHouse vs something lighter for a 25-hour build (it's a new service to run).
- 🟠 Output format for set candidates (JSON per species? one file?) and how often it's rebuilt.
- 🟠 The Elo cut-off for "high-Elo" training data.
- 🟠 How bots are detected and filtered.
