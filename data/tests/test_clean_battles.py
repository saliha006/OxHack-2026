import duckdb
import pytest

from data.pipeline.clean_battles import clean

LOG = """|t:|1701538642
|gametype|singles
|player|p1|Vale_2C|boarder|1131
|player|p2|2Starlightz|102|1042
|gen|9
|tier|[Gen 9] OU
|rated|
|poke|p1|Kingambit, L50, F|
|poke|p1|Zamazenta-*|
|poke|p2|Great Tusk|
|poke|p2|Dragapult, M|
|start
|switch|p1a: Gambit|Kingambit, F|100/100
|switch|p2a: Great Tusk|Great Tusk|100/100
|turn|1
|turn|2
|turn|8
|win|2Starlightz
|raw|Vale_2C's rating: 1131 &rarr; <strong>1100</strong><br />(-31 for losing)"""


def row(id="gen9ou-1", log=LOG, uploadtime=1701538800, formatid="gen9ou", rating=1084.0):
    return {"id": id, "format": "[Gen 9] OU", "players": ["a", "b"], "log": log, "uploadtime": uploadtime,
            "views": 3, "formatid": formatid, "rating": rating}


@pytest.fixture
def run(tmp_path):
    def run(*rows):
        con = duckdb.connect()
        con.execute("SET TimeZone = 'UTC'")
        path = tmp_path / "raw.parquet"
        con.sql("SELECT * FROM (SELECT unnest($rows, recursive := true))", params={"rows": list(rows)}).write_parquet(
            path.as_posix())
        cleaned = clean(con, path, "test")
        return {r[0]: dict(zip(cleaned.columns, r)) for r in cleaned.fetchall()}
    return run


def test_players_elo_winner_and_turns_come_from_the_log(run):
    battle = run(row())["gen9ou-1"]
    assert (battle["p1"], battle["p2"], battle["p1_elo"], battle["p2_elo"]) == ("Vale_2C", "2Starlightz", 1131, 1042)
    assert battle["winner"] == "p2" and battle["turns"] == 8 and battle["rated"]
    assert battle["dataset_rating"] == 1084.0 and battle["source"] == "test"
    assert str(battle["started_at"]).startswith("2023-12-02 17:37:22")


def test_teams_are_sorted_preview_species_and_leads_ignore_nicknames(run):
    battle = run(row())["gen9ou-1"]
    assert battle["p1_team"] == ["Kingambit", "Zamazenta-*"] and battle["p2_team"] == ["Dragapult", "Great Tusk"]
    assert battle["p1_lead"] == "Kingambit" and battle["p2_lead"] == "Great Tusk"


def test_ties_and_missing_elo(run):
    log = LOG.replace("|win|2Starlightz", "|tie").replace("|boarder|1131", "|boarder|")
    battle = run(row(log=log))["gen9ou-1"]
    assert battle["winner"] == "tie"
    assert battle["p1_elo"] is None and battle["p2_elo"] == 1042


def test_splits_by_time_and_smogtours(run):
    late = LOG.replace("|t:|1701538642", "|t:|1780000000")  # 2026-05-28
    battles = run(row(id="gen9ou-1"), row(id="gen9ou-2", log=late), row(id="smogtours-gen9ou-3"))
    assert [battles[i]["split"] for i in ("gen9ou-1", "gen9ou-2", "smogtours-gen9ou-3")] == ["train", "test", "eval"]


def test_drops_other_formats_duplicates_and_games_after_the_freeze(run):
    after = LOG.replace("|t:|1701538642", "|t:|1793000000")  # 2026-10-26
    battles = run(row(id="gen9ou-1"), row(id="gen9ou-1", uploadtime=1701539999), row(id="gen9uu-2", formatid="gen9uu"),
                  row(id="gen9ou-3", log=after))
    assert list(battles) == ["gen9ou-1"]
