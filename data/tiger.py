"""Offline, read-only Tiger access; never import this module from the battle agent.

The streamed row_to_json/atomic export follows Derrick's backtest/tiger.py
pattern on origin/derrick, with explicit credentials, TLS and read-only sessions.
"""
import argparse
import hashlib
import json
import os
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV = ROOT / ".env.kenar-tiger"
DEFAULT_DUMP = ROOT / "runs/tiger/turns.jsonl"


class SetupError(ValueError):
    """Controlled local messages; database/library ValueErrors may contain secrets."""


QUERY = "SELECT row_to_json(t)::text FROM public.turns t ORDER BY battle_id, turn, started_at"
COUNTS = """SELECT split,count(*) AS turns,count(DISTINCT (battle_id,started_at)) AS battles,
 min(started_at) AS first_battle,max(started_at) AS last_battle,
 count(*) FILTER(WHERE winner IS NULL OR winner NOT IN ('p1','p2')) AS invalid_outcomes,
 count(*) FILTER(WHERE state IS NULL) AS missing_states
 FROM public.turns GROUP BY split ORDER BY split"""
METADATA = """SELECT t.battle_id,t.started_at,t.split,t.winner,b.p1,b.p2,b.p1_team,b.p2_team
 FROM (SELECT DISTINCT battle_id,started_at,split,winner FROM public.turns) t
 JOIN public.battles b ON b.id=t.battle_id AND b.started_at=t.started_at
 ORDER BY t.battle_id,t.started_at"""


def _json(value):
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    raise TypeError(type(value).__name__)


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_name(path.name + ".part")
    part.write_text(json.dumps(data, indent=2, default=_json) + "\n", encoding="utf-8")
    part.replace(path)


@contextmanager
def connect(env_file: Path = DEFAULT_ENV, timeout_ms: int = 120000):
    import psycopg
    from dotenv import dotenv_values

    # Parse as data, never source an env file as shell code. Values never enter command arguments/logs.
    values = dotenv_values(env_file, interpolate=False) if env_file.exists() else {}
    url = values.get("TIMESCALE_SERVICE_URL") or os.environ.get("TIMESCALE_SERVICE_URL")
    if not url:
        raise SetupError("TIMESCALE_SERVICE_URL missing; supply the private env file")
    with psycopg.connect(url, connect_timeout=15, sslmode="require",
                         options=f"-c default_transaction_read_only=on -c statement_timeout={int(timeout_ms)} -c TimeZone=UTC",
                         application_name="oxhack-offline-reader") as conn:
        conn.read_only = True
        conn.isolation_level = psycopg.IsolationLevel.REPEATABLE_READ
        yield conn


def table_rows(conn, query: str) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(query)
        names = [column.name for column in cur.description]
        return [dict(zip(names, row)) for row in cur]


def inspect(conn) -> dict:
    permission = table_rows(conn, """SELECT current_setting('transaction_read_only') AS transaction_read_only,
     has_table_privilege(current_user,'public.turns','SELECT') AS select_turns,
     has_table_privilege(current_user,'public.turns','INSERT') AS insert_turns,
     has_table_privilege(current_user,'public.turns','UPDATE') AS update_turns,
     has_table_privilege(current_user,'public.turns','DELETE') AS delete_turns""")[0]
    columns = table_rows(conn, """SELECT table_name,column_name,data_type FROM information_schema.columns
     WHERE table_schema='public' AND table_name IN ('turns','battles','battle_logs')
     ORDER BY table_name,ordinal_position""")
    return {"checked_at": datetime.now(timezone.utc).isoformat(), "source": "Tiger public tables",
            "permissions": permission, "tls_in_use": bool(conn.pgconn.ssl_in_use),
            "split_counts": table_rows(conn, COUNTS), "columns": columns,
            "team_identity": "battles.p1_team/p2_team are species rosters, not complete hidden sets",
            "credential_values_included": False}


def dump(rows, path: Path, *, expected_rows: int | None = None, progress=None) -> dict:
    """Preserve every database column, bounded memory and no final file until complete."""
    if path.exists():
        raise FileExistsError("output already exists; reuse it or choose a new path")
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_name(path.name + ".part")
    count, digest = 0, hashlib.sha256()
    try:
        with part.open("wb") as stream:
            for (line,) in rows:
                payload = line.encode("utf-8") + b"\n"
                stream.write(payload)
                digest.update(payload)
                count += 1
                if progress and count % 25000 == 0:
                    progress(count)
        if expected_rows is not None and count != expected_rows:
            raise SetupError("export row count differs from its consistent-snapshot count")
        part.replace(path)
    except BaseException:
        part.unlink(missing_ok=True)
        raise
    return {"rows": count, "sha256": digest.hexdigest(), "bytes": path.stat().st_size}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV)
    sub = parser.add_subparsers(dest="command", required=True)
    checking = sub.add_parser("check")
    checking.add_argument("--output", type=Path, default=ROOT / "runs/tiger/readiness.json")
    exporting = sub.add_parser("export")
    exporting.add_argument("--output", type=Path, default=DEFAULT_DUMP)
    exporting.add_argument("--batch-size", type=int, default=512)
    args = parser.parse_args(argv)
    if args.command == "export" and args.batch_size < 1:
        parser.error("batch size must be positive")
    try:
        with connect(args.env_file, timeout_ms=900000 if args.command == "export" else 120000) as conn:
            if args.command == "check":
                report = inspect(conn)
                write_json(args.output, report)
                print(json.dumps({"permissions": report["permissions"], "tls_in_use": report["tls_in_use"],
                                  "split_counts": report["split_counts"], "report": str(args.output)}, default=_json))
            else:
                if args.output.exists():
                    raise FileExistsError("output already exists; reuse it or choose a new path")
                counts = table_rows(conn, COUNTS)
                metadata = table_rows(conn, METADATA)
                if len(metadata) != sum(r["battles"] for r in counts):
                    raise SetupError("battle metadata join did not cover every sampled game")
                started = time.monotonic()
                with conn.cursor(name="oxhack_turn_export") as cur:
                    cur.itersize = args.batch_size
                    cur.execute(QUERY)
                    result = dump(cur, args.output, expected_rows=sum(r["turns"] for r in counts),
                                  progress=lambda n: print(f"Exported {n:,} rows in {time.monotonic()-started:.0f}s", flush=True))
                write_json(args.output.with_suffix(".battles.json"), metadata)
                report = {"source": "Tiger public.turns", "query": QUERY, "metadata_query": METADATA,
                          "exported_at": datetime.now(timezone.utc).isoformat(), "read_only": True,
                          "split_counts": counts, "battle_metadata_rows": len(metadata),
                          "team_identity": "preview_roster_proxy", "source_label": "public_ladder",
                          "human_status": "unverified", "elapsed_seconds": time.monotonic()-started, **result}
                write_json(args.output.with_suffix(".manifest.json"), report)
                print(json.dumps(report, default=_json), flush=True)
    except (SetupError, FileExistsError) as exc:
        print(f"Setup/export stopped: {exc}")
        return 1
    except Exception as exc:
        # Database errors can quote DSNs or connection fields. Report only class/state, never their raw message.
        print(json.dumps({"error_type": type(exc).__name__, "sqlstate": getattr(exc, "sqlstate", None),
                          "message": "Read-only Tiger operation failed; credential values suppressed"}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
