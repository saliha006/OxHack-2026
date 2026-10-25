"""Cleans raw replay parquet files into data/clean/battles/, one output file per input file, logs kept."""
import argparse
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "holidayougi"
OUT = ROOT / "data" / "clean" / "battles"

# Games uploaded from this date on are the test split (Metamon's cutoff; brief guardrail). Earlier ones are training.
TEST_FROM = "2026-05-19"
# The data freeze: the project started 2026-10-24 12:00 BST. Nothing after it is kept.
FREEZE = "2026-10-24 11:00:00+00"

# One row per replay. Elo is each player's pre-game rating from their |player| line, not the dataset's `rating`
# column (that is the lower player's post-game rating). Showdown floors Elo at 1000, so 1000 means "1000 or less".
# Teams are the six species each side shows at team preview, sorted, spelled as the preview shows them: some formes are
# hidden there ("Zamazenta-*", "Greninja-*"). Leads are the species each side sends out first.
CLEAN_SQL = f"""
WITH raw AS (
    SELECT *, substr(log, 1, CASE WHEN instr(log, '|turn|1') > 0 THEN instr(log, '|turn|1') ELSE length(log) END)
        AS preview
    FROM read_parquet('{{path}}')
    WHERE formatid = 'gen9ou'
), parsed AS (
    SELECT
        id,
        '{{source}}' AS source,
        to_timestamp(coalesce(try_cast(regexp_extract(log, '\\|t:\\|([0-9]+)', 1) AS BIGINT), uploadtime)) AS started_at,
        to_timestamp(uploadtime) AS uploaded_at,
        regexp_extract(log, '\\|player\\|p1\\|([^|\\n]*)', 1) AS p1,
        regexp_extract(log, '\\|player\\|p2\\|([^|\\n]*)', 1) AS p2,
        try_cast(regexp_extract(log, '\\|player\\|p1\\|[^|\\n]*\\|[^|\\n]*\\|([0-9]+)', 1) AS INTEGER) AS p1_elo,
        try_cast(regexp_extract(log, '\\|player\\|p2\\|[^|\\n]*\\|[^|\\n]*\\|([0-9]+)', 1) AS INTEGER) AS p2_elo,
        list_sort(regexp_extract_all(preview, '\\|poke\\|p1\\|([^,|\\n]+)', 1)) AS p1_team,
        list_sort(regexp_extract_all(preview, '\\|poke\\|p2\\|([^,|\\n]+)', 1)) AS p2_team,
        nullif(regexp_extract(preview, '\\|switch\\|p1a: [^|\\n]*\\|([^,|\\n]+)', 1), '') AS p1_lead,
        nullif(regexp_extract(preview, '\\|switch\\|p2a: [^|\\n]*\\|([^,|\\n]+)', 1), '') AS p2_lead,
        regexp_extract(log, '\\n\\|win\\|([^\\n]*)', 1) AS winner_name,
        regexp_matches(log, '\\n\\|tie(\\n|$)') AS tie,
        list_max(list_transform(regexp_extract_all(log, '\\|turn\\|([0-9]+)', 1), lambda x: x::INTEGER)) AS turns,
        log LIKE '%|rated|%' AS rated,
        views,
        rating AS dataset_rating,
        log
    FROM raw
    QUALIFY row_number() OVER (PARTITION BY id ORDER BY uploadtime DESC) = 1
)
SELECT
    id, source, started_at, uploaded_at, p1, p2, p1_elo, p2_elo, p1_team, p2_team, p1_lead, p2_lead,
    CASE WHEN tie THEN 'tie' WHEN winner_name = p1 THEN 'p1' WHEN winner_name = p2 THEN 'p2' END AS winner,
    coalesce(turns, 0) AS turns, rated, views, dataset_rating,
    CASE WHEN id LIKE 'smogtours-%' THEN 'eval' WHEN started_at >= TIMESTAMPTZ '{TEST_FROM}' THEN 'test' ELSE 'train' END
        AS split,
    log
FROM parsed
WHERE started_at < TIMESTAMPTZ '{FREEZE}'
"""


def clean(con: duckdb.DuckDBPyConnection, path: Path, source: str):
    """The cleaned rows of one raw parquet file, as a DuckDB relation."""
    return con.sql(CLEAN_SQL.format(path=path.as_posix(), source=source))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", type=Path, help="raw parquet files (default: every file in data/raw/holidayougi)")
    parser.add_argument("--source", default="holidayougi")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute("SET memory_limit = '6GB'")
    con.execute("SET TimeZone = 'UTC'")
    for path in args.files or sorted(RAW.glob("*.parquet")):
        out = OUT / path.name
        clean(con, path, args.source).write_parquet(out.as_posix(), compression="zstd")
        # Read the whole result: an execute() result left half-read blocks the next file's write.
        [(rows, no_elo, no_winner)] = con.sql(
            f"SELECT count(*), count(*) FILTER (WHERE p1_elo IS NULL OR p2_elo IS NULL), count(*) FILTER (WHERE winner IS NULL)"
            f" FROM '{out.as_posix()}'").fetchall()
        print(f"{out.name}: {rows} battles, {no_elo} missing an Elo, {no_winner} with no winner")


if __name__ == "__main__":
    main()
