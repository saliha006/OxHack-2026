"""Loads cleaned battles from data/clean/battles/ into Tiger, without the logs (those stay in local parquet)."""
import argparse
import os
import time
from pathlib import Path

import duckdb
import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
CLEAN = ROOT / "data" / "clean" / "battles"

COLUMNS = ["id", "source", "started_at", "uploaded_at", "p1", "p2", "p1_elo", "p2_elo", "winner", "turns", "rated",
           "views", "dataset_rating", "split"]

# A hypertable chunked by month on the time the game started; the primary key has to include that time column.
SCHEMA = """
CREATE TABLE IF NOT EXISTS battles (
    id             text        NOT NULL,
    source         text        NOT NULL,
    started_at     timestamptz NOT NULL,
    uploaded_at    timestamptz NOT NULL,
    p1             text,
    p2             text,
    p1_elo         integer,
    p2_elo         integer,
    winner         text,
    turns          integer     NOT NULL,
    rated          boolean     NOT NULL,
    views          bigint,
    dataset_rating double precision,
    split          text        NOT NULL,
    PRIMARY KEY (id, started_at)
);
SELECT create_hypertable('battles', by_range('started_at', INTERVAL '1 month'), if_not_exists => true);
"""


def load(conn: psycopg.Connection, path: Path) -> int:
    """Copies one cleaned file into battles, skipping ids already there; returns the rows added."""
    duck = duckdb.connect()
    duck.execute("SET TimeZone = 'UTC'")
    rows = duck.execute(f"SELECT {', '.join(COLUMNS)} FROM read_parquet('{path.as_posix()}')")
    with conn.cursor() as cur:
        # Copy into a scratch table first, so a re-run can skip what's already loaded instead of failing on the key.
        cur.execute("CREATE TEMP TABLE staging (LIKE battles) ON COMMIT DROP")
        with cur.copy(f"COPY staging ({', '.join(COLUMNS)}) FROM STDIN") as copy:
            while batch := rows.fetchmany(10_000):
                for row in batch:
                    copy.write_row(row)
        cur.execute("INSERT INTO battles SELECT * FROM staging ON CONFLICT DO NOTHING")
        added = cur.rowcount
    conn.commit()
    return added


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", type=Path, help="cleaned parquet files (default: all of data/clean/battles)")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    with psycopg.connect(os.environ["TIMESCALE_SERVICE_URL"]) as conn:
        conn.execute(SCHEMA)
        conn.commit()
        for path in args.files or sorted(CLEAN.glob("*.parquet")):
            start = time.monotonic()
            added = load(conn, path)
            print(f"{path.name}: {added} battles added in {time.monotonic() - start:.0f}s")


if __name__ == "__main__":
    main()
