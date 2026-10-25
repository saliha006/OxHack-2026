"""Copies Nate's Tiger `turns` table to one local JSONL file: a full read takes ~20 s from disk against ~5 min over the network."""
import json
import os
from collections.abc import Iterable, Iterator
from pathlib import Path

DUMP = Path("runs/tiger/turns.jsonl")
# Postgres renders row_to_json, so each saved line is the row exactly as Tiger holds it. The order keeps a game's
# turns together and in play order; Tiger merges its monthly chunks along the primary key, so there's no full sort.
QUERY = "SELECT row_to_json(t)::text FROM turns t ORDER BY battle_id, turn"


def dump(rows: Iterable[tuple[str]], path: Path = DUMP) -> int:
    """Writes one row per line; the file only appears once every row is in, so a dropped connection leaves no half dump."""
    part = path.with_name(path.name + ".part")
    part.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with open(part, "w", encoding="utf-8") as out:
        for (line,) in rows:
            out.write(line + "\n")
            count += 1
    part.replace(path)
    return count


def turns(path: Path = DUMP) -> Iterator[dict]:
    with open(path, encoding="utf-8") as dumped:
        for line in dumped:
            yield json.loads(line)


def main() -> int:
    import psycopg  # here, not at the top, so the decision tests run without the data group

    # A named cursor streams from the server in batches; a plain one would pull all ~3 GB into memory first.
    with psycopg.connect(os.environ["TIMESCALE_SERVICE_URL"]) as conn, conn.cursor(name="turns") as cur:
        cur.itersize = 5000
        cur.execute(QUERY)
        count = dump(cur)
    print(f"{count} turns -> {DUMP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
