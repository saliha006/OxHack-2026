"""Loads cleaned battles from data/clean/battles/ into Tiger: one row per game in `battles`, its log in `battle_logs`.

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


def load(conn: psycopg.Connection, path: Path, table: str) -> int:
    """Copies one cleaned file into a table, skipping ids already there; returns the rows added."""
    columns = TABLES[table][0]
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
    parser.add_argument("files", nargs="*", type=Path, help="cleaned parquet files (default: all of data/clean/battles)")
    parser.add_argument("--table", choices=TABLES, default="battles")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    with psycopg.connect(os.environ["TIMESCALE_SERVICE_URL"]) as conn:
        conn.execute(TABLES[args.table][1])
        conn.commit()
        for path in args.files or sorted(CLEAN.glob("*.parquet")):
            start = time.monotonic()
            added = load(conn, path, args.table)
            print(f"{path.name}: {added} rows added to {args.table} in {time.monotonic() - start:.0f}s", flush=True)


if __name__ == "__main__":
    main()
