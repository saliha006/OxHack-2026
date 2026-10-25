> Source snapshot: main at bbb95d60fb57a01497aae370d8ca922c275bb79d. See ../DATA-CONTEXT.md for branch-specific corrections.

# Turns table

> **v1**, built by the data layer (@nate), 2026-10-25. For the decision layer (@derrick): training data for the
> win-probability model, the opponent model and belief scoring. Change requests go to @nate on the Open board.

**What it is:** one row per turn of a replay: the battle state at the start of the turn, what each side did that
turn, and how the game ended. It lives in Tiger as `turns`: **489,840 rows from 20,000 gen9ou games**.

- **Built by:** `data/pipeline/build_turns.py`, from the cleaned replays in `data/clean/battles/`.
- **Loaded by:** `data/pipeline/load_tiger.py --table turns <file>`.
- **Checked by:** `data/tests/test_build_turns.py`.

## Access
Your **read-only login** (the `derrick-tiger.env` file nate sent you, saved as `.env`, which is git-ignored) is the whole
API: `TIMESCALE_SERVICE_URL` works with any Postgres client or library. It can read every table and can't write.

Stream it in Python; psycopg returns `state` as a dict:
```python
import os, psycopg
from dotenv import load_dotenv

load_dotenv()
with psycopg.connect(os.environ["TIMESCALE_SERVICE_URL"]) as conn, conn.cursor(name="turns") as cur:
    cur.itersize = 5000  # server-side cursor: streams in batches
    cur.execute("SELECT battle_id, split, winner, state FROM turns")
    for battle_id, split, winner, state in cur:
        ...
```
Measured: 100k rows with `state` in ~65 s, so the whole table in ~5 min. Load it once per training run.
`uv run --with "psycopg[binary]" --with python-dotenv ...` keeps `pyproject.toml` unchanged.

**Joining to the other tables:** `battles` (one row per game, all 2,506,142 games: players, pre-game Elo, winner,
turns, rated, teams, leads) and `battle_logs` (the raw log) are hypertables chunked by month. Always join on both
columns, `t.battle_id = b.id AND t.started_at = b.started_at`. Joining on the id alone makes Tiger search every
monthly chunk: 133 s against 13 s, measured.

## Which games, and the splits
- **Sample:** rated games, both Elos known, 6+ turns, a winner (no ties), seed 2026.
- **`train`:** 15,000 games (361,437 turns) from 2025-01-01 to 2026-05-18.
- **`test`:** 5,000 games (128,403 turns) from 2026-05-19 to 2026-10-05, the latest date in the replay dataset.
- **Freeze:** the data stops at 2026-10-24 12:00 BST.
- **No validation split yet.** For choosing a calibration method, carve one off by date, e.g. train games with
  `started_at >= '2026-03-01'`, so it's time-ordered like `test`.
- **Leakage:** no game is in both splits. 43% of test games share a player with train, and 38% share an exact team.
  **1,909 test games share neither.** Report both the full test split and this unseen subset (query below).

## How the decision layer uses it
| Part | Used for |
|---|---|
| `state` + `winner` | **Win-probability model (task 7):** `x = featurize(state)`, `y = winner == state["us"]` |
| `p1_action` / `p2_action` + `state` | **Opponent model (pass 10 step 6):** players switched on **19.2%** of the turns they acted |
| `state` across a game's turns | **Belief scoring (task 8):** moves, items, abilities and Tera revealed turn by turn |
| The other columns | Baselines, analysis and demo charts, without parsing JSON |

## What it guarantees
- **Same states as the live bot:** `state` is saliha's `Parser` snapshotted at each `|turn|`. It's identical to
  `states_from_log` on all 34 turns of `bot/tests/fixtures/gen9ou-2703852247.log` (checked).
- **Public information only:** it's a spectator's view, with no look-ahead.
- **`us` is `"p1"` in every row.** The view is symmetric, so setting `state["us"] = "p2"` with `y = winner == "p2"` is
  a valid second sample from the same row.
- **Replays have no Showdown `request`,** so features must come from the `BattleState` alone (the dual-path
  featurizer).
- **One row per `|turn|`.** A forced switch after a faint has no row of its own: the replacement is the next row's
  active.

## Columns (99)
| Group | Columns |
|---|---|
| Which turn | `battle_id`, `turn` (the turn about to be chosen; 1 = first move), `started_at` (game start), `turn_started_at`, `seconds_taken`, `split`, `winner` (`p1`/`p2`), `p1_elo`, `p2_elo` |
| Each side at the start of the turn (`p1_…`, `p2_…`) | `active`, `active_hp`, `active_status`, `alive`, `hp_total`, `statused`, `atk`/`def`/`spa`/`spd`/`spe` (active's boosts, -6..6), `tera_used`, `stealthrock`, `spikes`, `toxicspikes`, `stickyweb`, `reflect`, `lightscreen`, `auroraveil`, `tailwind`, `substitute` |
| Every Pokémon (`p1_mon1…6_…`, `p2_mon1…6_…`) | `species`, `hp`, `status` |
| Field | `weather`, `terrain`, `trickroom` |
| What happened this turn | `p1_action`, `p2_action`, `p1_tera_now`, `p2_tera_now`, `p1_fainted_now`, `p2_fainted_now`, `first_mover`, `crit` |
| Full state | `state` (jsonb): the `BattleState` per `contracts/battle-state.md` |

**Conventions**
- **IDs:** Pokémon and moves are Showdown IDs, as in `BattleState`.
- **HP:** `hp` and `active_hp` are percentages, 0-100, with 0 meaning fainted. `hp_total` adds up the six HP
  fractions, so it runs 0-6. A Pokémon not yet seen counts as full.
- **Slots:** `monK` follows team preview order, which holds for the whole game, so `p1_mon3` is the same Pokémon every
  turn. That order is arbitrary between games, so don't use a slot as a feature.
- **Hazards and screens** are counted on the side they're on: hazards hurt that side's switch-ins, and screens
  protect that side.
- **Actions:** `pX_action` is that side's first `move:<id>`, `switch:<species>` or `cant:<reason>` line of the turn.
  `fainted` means its active was knocked out before acting, so its choice was never shown. `NULL` means no action was
  logged, for example a forfeit turn.
- **Time:** `seconds_taken` is wall-clock time to the next turn: both players thinking plus the turn playing out.

## Baselines to beat (test split, computed in Tiger)
| Model | Log loss | Brier |
|---|---|---|
| Constant 0.5 | 0.6931 | 0.25 |
| HP heuristic (`decision/value.py`): `0.5 + ((p1_alive + p1_hp_total) - (p2_alive + p2_hp_total)) / 24` | **0.6407** | **0.2246** |

```sql
SELECT split, count(*) AS turns,
       avg(-(CASE WHEN winner = 'p1' THEN ln(v) ELSE ln(1 - v) END)) AS hp_log_loss,
       avg(power((winner = 'p1')::int - v, 2)) AS hp_brier
FROM (SELECT split, winner,
             greatest(0.001, least(0.999, 0.5 + ((p1_alive + p1_hp_total) - (p2_alive + p2_hp_total)) / 24.0)) AS v
      FROM turns) x
GROUP BY split;
```

**Unseen test games** (no player or team also in train; 1,909 games, ~13 s):
```sql
WITH g AS (
    SELECT t.battle_id, t.split, b.p1, b.p2, b.p1_team, b.p2_team
    FROM (SELECT DISTINCT battle_id, started_at, split FROM turns) t
    JOIN battles b ON b.id = t.battle_id AND b.started_at = t.started_at
), train_players AS (
    SELECT p1 AS player FROM g WHERE split = 'train' UNION SELECT p2 FROM g WHERE split = 'train'
), train_teams AS (
    SELECT p1_team AS team FROM g WHERE split = 'train' UNION SELECT p2_team FROM g WHERE split = 'train'
)
SELECT battle_id FROM g
WHERE split = 'test'
  AND p1 NOT IN (SELECT player FROM train_players) AND p2 NOT IN (SELECT player FROM train_players)
  AND p1_team NOT IN (SELECT team FROM train_teams) AND p2_team NOT IN (SELECT team FROM train_teams);
```

## Rules
- **No Tiger queries inside `Agent.choose`.** Train offline and ship the model as a file the bot loads at startup.
  From a laptop, one round trip to Tiger can take hundreds of milliseconds on a busy network, and the turn budget is
  3 s.
- **The login is read-only.** For a new column, more games or another sample, ask nate. 100k games is about an
  11-minute build plus about 20 minutes of upload.

## Still open
- **The validation split:** derrick's choice (suggestion above).
- **Bot filtering:** no rule yet beyond rated games with 6+ turns.
- **Old logs:** the parser skips the odd malformed line (e.g. HP written `20/100y`), which costs one fact in that turn.
