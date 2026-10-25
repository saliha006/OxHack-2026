from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from data.pipeline.build_turns import turn_rows
from data.pipeline.load_tiger import turns_table

FIXTURE = Path(__file__).parents[2] / "bot" / "tests" / "fixtures" / "gen9ou-2703852247.log"


def test_turns_table_matches_the_built_file(tmp_path):
    rows = turn_rows("g", FIXTURE.read_text(encoding="utf-8"), datetime(2026, 10, 1, tzinfo=timezone.utc), "p1", "test")
    path = tmp_path / "turns.parquet"
    pq.write_table(pa.Table.from_pylist(rows), path)
    columns, ddl = turns_table(path)
    assert columns == list(rows[0])
    assert "state jsonb" in ddl and "battle_id text NOT NULL" in ddl and "started_at timestamptz NOT NULL" in ddl
    assert "p1_hp_total double precision" in ddl and "p1_tera_used boolean" in ddl and "seconds_taken bigint" in ddl
    assert "PRIMARY KEY (battle_id, turn, started_at)" in ddl
