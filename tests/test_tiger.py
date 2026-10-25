import sys
from types import SimpleNamespace

import pytest

from backtest import tiger

ROWS = [
    ('{"battle_id": "gen9ou-1", "turn": 1, "p2_active": "flabébé", "state": {"us": "p1"}}',),
    ('{"battle_id": "gen9ou-1", "turn": 2, "p2_active": "flabébé", "state": {"us": "p1"}}',),
]


def lines(path):
    return path.read_text(encoding="utf-8").splitlines()


def test_dump_writes_each_row_verbatim_on_its_own_line(tmp_path):
    path = tmp_path / "tiger" / "turns.jsonl"
    assert tiger.dump(ROWS, path) == 2
    assert lines(path) == [row for (row,) in ROWS]


def test_turns_reads_the_dump_back_in_order(tmp_path):
    path = tmp_path / "turns.jsonl"
    tiger.dump(ROWS, path)
    read = list(tiger.turns(path))
    assert [(t["battle_id"], t["turn"]) for t in read] == [("gen9ou-1", 1), ("gen9ou-1", 2)]
    assert read[0]["p2_active"] == "flabébé"


def test_a_dropped_stream_keeps_the_last_full_dump(tmp_path):
    path = tmp_path / "turns.jsonl"
    tiger.dump(ROWS, path)

    def dropped():
        yield ROWS[0]
        raise ConnectionError("Tiger went away")

    with pytest.raises(ConnectionError):
        tiger.dump(dropped(), path)
    assert lines(path) == [row for (row,) in ROWS]


class FakeCursor:
    def __init__(self, rows):
        self.rows, self.queries = rows, []

    def execute(self, query):
        self.queries.append(query)

    def __iter__(self):
        return iter(self.rows)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeConnection:
    def __init__(self, cursor):
        self.named_cursor, self.cursor_names = cursor, []

    def cursor(self, name):
        self.cursor_names.append(name)
        return self.named_cursor

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_main_streams_the_ordered_table_through_a_server_side_cursor(tmp_path, monkeypatch, capsys):
    cursor = FakeCursor(ROWS)
    connection = FakeConnection(cursor)
    urls = []
    monkeypatch.setitem(sys.modules, "psycopg", SimpleNamespace(connect=lambda url: urls.append(url) or connection))
    monkeypatch.setenv("TIMESCALE_SERVICE_URL", "postgres://reader@tiger/oxhack")
    monkeypatch.chdir(tmp_path)

    assert tiger.main() == 0
    assert urls == ["postgres://reader@tiger/oxhack"]
    assert connection.cursor_names == ["turns"]
    assert cursor.queries == [tiger.QUERY]
    assert lines(tmp_path / tiger.DUMP) == [row for (row,) in ROWS]
    assert "2 turns" in capsys.readouterr().out
