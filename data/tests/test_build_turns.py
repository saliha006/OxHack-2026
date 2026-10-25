import json
from datetime import datetime, timezone
from pathlib import Path

from data.pipeline.build_turns import snapshots, turn_rows

FIXTURE = Path(__file__).parents[2] / "bot" / "tests" / "fixtures" / "gen9ou-2703852247.log"
STARTED = datetime(2026, 10, 1, tzinfo=timezone.utc)


def fixture_rows():
    return turn_rows("gen9ou-2703852247", FIXTURE.read_text(encoding="utf-8"), STARTED, "p1", "test")


def test_one_row_per_turn_in_order():
    rows = fixture_rows()
    turns = FIXTURE.read_text(encoding="utf-8").count("\n|turn|")
    assert [r["turn"] for r in rows] == list(range(1, turns + 1))
    assert {r["winner"] for r in rows} == {"p1"} and {r["split"] for r in rows} == {"test"}


def test_first_turn_starts_with_both_leads_out_and_full_teams():
    first = fixture_rows()[0]
    assert (first["p1_elo"], first["p2_elo"]) == (1654, 1625)
    assert first["p1_active"] and first["p2_active"]
    assert first["p1_alive"] == first["p2_alive"] == 6 and first["p1_hp_total"] == first["p2_hp_total"] == 6.0


def test_each_pokemon_keeps_its_slot_and_the_slots_add_up_to_the_totals():
    rows = fixture_rows()
    for side in ("p1", "p2"):
        assert len({tuple(r[f"{side}_mon{k}_species"] for k in range(1, 7)) for r in rows}) <= 2  # a hidden forme may resolve once
        for r in rows:
            hps = [r[f"{side}_mon{k}_hp"] for k in range(1, 7)]
            assert sum(hps) / 100 == r[f"{side}_hp_total"] and sum(hp > 0 for hp in hps) == r[f"{side}_alive"]


def test_actions_are_labelled_and_the_state_round_trips():
    rows = fixture_rows()
    actions = [r[f"{s}_action"] for r in rows for s in ("p1", "p2") if r[f"{s}_action"]]
    assert actions and all(a.split(":")[0] in ("move", "switch", "cant", "fainted") for a in actions)
    assert all(json.loads(r["state"])["turn"] == r["turn"] for r in rows)


def test_faints_add_up_to_what_the_log_ends_with():
    rows = fixture_rows()
    _, final, _ = snapshots(FIXTURE.read_text(encoding="utf-8"))
    for side in ("p1", "p2"):
        final_alive = sum(mon["hp_percent"] > 0 for mon in final["sides"][side]["pokemon"])
        assert sum(r[f"{side}_fainted_now"] for r in rows) == rows[0][f"{side}_alive"] - final_alive


def test_a_pokemon_knocked_out_before_moving_has_no_chosen_action():
    log = "\n".join([
        "|t:|100", "|player|p1|A|1|1500", "|player|p2|B|2|1500", "|poke|p1|Kingambit|", "|poke|p2|Great Tusk|",
        "|teampreview", "|start", "|switch|p1a: Kingambit|Kingambit|100/100",
        "|switch|p2a: Great Tusk|Great Tusk|100/100", "|t:|110", "|turn|1",
        "|move|p2a: Great Tusk|Headlong Rush|p1a: Kingambit", "|-damage|p1a: Kingambit|0 fnt",
        "|faint|p1a: Kingambit", "|t:|125", "|win|B"])
    [row] = turn_rows("x", log, STARTED, "p2", "train")
    assert row["p2_action"] == "move:headlongrush" and row["p1_action"] == "fainted"
    assert row["first_mover"] == "p2" and row["p1_fainted_now"] == 1 and row["seconds_taken"] == 15
