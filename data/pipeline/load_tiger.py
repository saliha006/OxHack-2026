"""Loads cleaned data into Tiger: one row per game in `battles`, its log in `battle_logs`, one row per turn in `turns`.

battle_logs stays uncompressed: storage is cheap on the credits, and reading one log is ~0.02 ms on the server against
~12 ms compressed.

Views, dataset rating and split stay in the local parquet only. Split is derivable from started_at and id
(see clean_battles.py).
"""
import argparse
import os
import time
from pathlib import Path

import duckdb
import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
CLEAN = ROOT / "data" / "clean" / "battles"

# Both are hypertables chunked by month on the time the game started; a primary key has to include that time column.
# The logs get their own table so queries over `battles` never read 9 KB of text per row.
TABLES = {
    "battles": (
        ["id", "source", "started_at", "uploaded_at", "p1", "p2", "p1_elo", "p2_elo", "p1_team", "p2_team", "p1_lead",
         "p2_lead", "winner", "turns", "rated"],
        """
        CREATE TABLE IF NOT EXISTS battles (
            id             text        NOT NULL,
            source         text        NOT NULL,
            started_at     timestamptz NOT NULL,
            uploaded_at    timestamptz NOT NULL,
            p1             text,
            p2             text,
            p1_elo         integer,
            p2_elo         integer,
            p1_team        text[],
            p2_team        text[],
            p1_lead        text,
            p2_lead        text,
            winner         text,
            turns          integer     NOT NULL,
            rated          boolean     NOT NULL,
            PRIMARY KEY (id, started_at)
        );
        SELECT create_hypertable('battles', by_range('started_at', INTERVAL '1 month'), if_not_exists => true);
        -- So "games where a side includes these Pokémon" (p1_team @> ARRAY[...]) doesn't scan every row.
        CREATE INDEX IF NOT EXISTS battles_p1_team ON battles USING gin (p1_team);
        CREATE INDEX IF NOT EXISTS battles_p2_team ON battles USING gin (p2_team);
        """),
    "battle_logs": (
        ["id", "started_at", "log"],
        """
        CREATE TABLE IF NOT EXISTS battle_logs (
            id         text        NOT NULL,
            started_at timestamptz NOT NULL,
            log        text        NOT NULL,
            PRIMARY KEY (id, started_at)
        );
        SELECT create_hypertable('battle_logs', by_range('started_at', INTERVAL '1 month'), if_not_exists => true);
        """),
}
# Rows per COPY batch; a log row is ~9 KB, so this keeps memory to tens of MB.
BATCH = 2_000

PG_TYPES = {"VARCHAR": "text", "BIGINT": "bigint", "INTEGER": "integer", "DOUBLE": "double precision",
            "BOOLEAN": "boolean", "TIMESTAMP WITH TIME ZONE": "timestamptz"}


def turns_table(path: Path) -> tuple[list[str], str]:
    """The turns table's columns and DDL, read off a file from build_turns.py (its ~70 columns change as it grows).

    `state` is jsonb so SQL can reach into it (state->'sides'->'p2'->'boosts'). Chunked by the game's start time, so
    a game's turns share a chunk.
    """
    described = duckdb.sql(f"DESCRIBE SELECT * FROM read_parquet('{path.as_posix()}')").fetchall()
    columns = [name for name, *_ in described]
    definitions = ",\n".join(
        f"{name} {'jsonb' if name == 'state' else PG_TYPES.get(kind, 'text')}"
        f"{' NOT NULL' if name in ('battle_id', 'turn', 'started_at') else ''}" for name, kind, *_ in described)
    return columns, f"""
        CREATE TABLE IF NOT EXISTS turns ({definitions}, PRIMARY KEY (battle_id, turn, started_at));
        SELECT create_hypertable('turns', by_range('started_at', INTERVAL '1 month'), if_not_exists => true);
        """


def load(conn: psycopg.Connection, path: Path, table: str, columns: list[str]) -> int:
    """Copies one cleaned file into a table, skipping rows already there; returns the rows added."""
    duck = duckdb.connect()
    duck.execute("SET TimeZone = 'UTC'")
    rows = duck.execute(f"SELECT {', '.join(columns)} FROM read_parquet('{path.as_posix()}')")
    with conn.cursor() as cur:
        # Copy into a scratch table first, so a re-run can skip what's already loaded instead of failing on the key.
        cur.execute(f"CREATE TEMP TABLE staging (LIKE {table}) ON COMMIT DROP")
        with cur.copy(f"COPY staging ({', '.join(columns)}) FROM STDIN") as copy:
            while batch := rows.fetchmany(BATCH):
                for row in batch:
                    copy.write_row(row)
        cur.execute(f"INSERT INTO {table} SELECT * FROM staging ON CONFLICT DO NOTHING")
        added = cur.rowcount
    conn.commit()
    return added


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", type=Path,
                        help="parquet files (default: all of data/clean/battles; required for turns)")
    parser.add_argument("--table", choices=[*TABLES, "turns"], default="battles")
    args = parser.parse_args()
    if args.table == "turns" and not args.files:
        parser.error("--table turns needs the turns file(s) to load")
    files = args.files or sorted(CLEAN.glob("*.parquet"))
    columns, ddl = turns_table(files[0]) if args.table == "turns" else TABLES[args.table]
    load_dotenv(ROOT / ".env")
    with psycopg.connect(os.environ["TIMESCALE_SERVICE_URL"]) as conn:
        conn.execute(ddl)
        conn.commit()
        for path in files:
            start = time.monotonic()
            added = load(conn, path, args.table, columns)
            print(f"{path.name}: {added} rows added to {args.table} in {time.monotonic() - start:.0f}s", flush=True)


if __name__ == "__main__":
    main()
