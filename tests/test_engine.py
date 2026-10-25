import copy
import json

from backtest import engine
from decision.agent import Agent
from tests.test_belief import OUR_PRIORS
from tests.turn2 import EXAMPLE


def row(battle_id, turn, split="test", logged="move:kowtowcleave", tera=False, state=EXAMPLE):
    return {"battle_id": battle_id, "turn": turn, "split": split, "p1_action": logged, "p1_tera_now": tera,
            "state": copy.deepcopy(state)}


def write_dump(path, rows):
    # Postgres's row_to_json writes no spaces, with battle_id first.
    path.write_text("".join(json.dumps(r, separators=(",", ":")) + "\n" for r in rows), encoding="utf-8")
    return path


def two_turns(battle_id, split="test", state=EXAMPLE):
    return [row(battle_id, 1, split, state=state), row(battle_id, 2, split, state=state)]


def test_battle_id_is_read_off_the_start_of_the_line():
    assert engine.battle_id(json.dumps({"battle_id": "gen9ou-1", "turn": 1}, separators=(",", ":"))) == "gen9ou-1"


def test_sample_is_seeded_and_keeps_to_one_split(tmp_path):
    dump = write_dump(tmp_path / "turns.jsonl", two_turns("a") + two_turns("b") + two_turns("c") + two_turns("d", "train"))
    picked = engine.sample(dump, "test", 2, seed=1)
    assert picked == engine.sample(dump, "test", 2, seed=1)
    assert len(picked) == 2 and set(picked) <= {"a", "b", "c"}
    assert sorted(engine.sample(dump, "all", 10, seed=1)) == ["a", "b", "c", "d"]


def test_load_gives_each_game_its_rows_in_play_order(tmp_path):
    dump = write_dump(tmp_path / "turns.jsonl", two_turns("a") + two_turns("c"))
    games = engine.load(dump, ["c", "a"])
    assert [[(r["battle_id"], r["turn"]) for r in game] for game in games] == [[("c", 1), ("c", 2)], [("a", 1), ("a", 2)]]


def test_missing_species_names_pokemon_the_set_file_lacks():
    priors = {"species": {k: v for k, v in OUR_PRIORS["species"].items() if k != "tinglu"}}
    assert engine.missing_species([row("g", 1)], priors) == {"tinglu"}
    assert engine.missing_species([row("g", 1)], OUR_PRIORS) == set()


def test_play_records_each_choice_in_the_replay_s_own_words():
    [turn] = engine.play([row("g", 2)], OUR_PRIORS, budget=3.0)
    assert turn["logged"] == "move:kowtowcleave"
    assert turn["chose"].startswith(("move:", "switch:")) and turn["seconds"] > 0


def test_a_strat_error_is_recorded_and_the_game_goes_on(monkeypatch):
    original, calls = Agent.choose_public, []

    def fails_once(self, battle, our_sets):
        calls.append(battle["turn"])
        if len(calls) == 1:
            raise RuntimeError("engine panicked")
        return original(self, battle, our_sets)

    monkeypatch.setattr(Agent, "choose_public", fails_once)
    first, second = engine.play([row("g", 2), row("g", 3)], OUR_PRIORS, budget=3.0)
    assert first["error"] == "RuntimeError: engine panicked" and "chose" not in first
    assert "chose" in second


def turn(logged, chose=None, seconds=0.1, logged_tera=False, chose_tera=False, error=None):
    if error:
        return {"logged": logged, "error": error}
    return {"logged": logged, "chose": chose, "seconds": seconds, "logged_tera": logged_tera, "chose_tera": chose_tera}


def test_summary_counts_same_choices_skips_and_errors():
    first = [turn("move:a", "move:a", 0.1), turn("move:b", "move:c", 0.2), turn("fainted", "move:a", 0.3),
             turn("move:a", error="KeyError: 'x'")]
    second = [turn("switch:x", "switch:x", 0.4, logged_tera=True)]
    report = engine.summary([first, second], [{"roaringmoon"}, {"roaringmoon", "swanna"}], sampled=4)
    assert report["games"] == {"sampled": 4, "played": 2, "skipped_missing_species": 2}
    assert report["missing_species"] == {"roaringmoon": 2, "swanna": 1}
    assert report["turns"] == {"total": 5, "scorable": 3, "errors": 1}
    same = report["same_as_p1"]
    assert same["rate"] == 2 / 3 and same["with_tera_too"] == 1 / 3
    # Resampling two games (1 of 2 and 1 of 1 same) can only give 1/2, 2/3 or 1.
    assert same["interval_95"] == (0.5, 1.0)
    assert report["think_seconds"] == {"p50": 0.25, "p99": 0.4, "max": 0.4}
    assert report["error_kinds"] == {"KeyError": 1}


def test_summary_with_nothing_played_has_no_rates():
    report = engine.summary([], [{"swanna"}], sampled=1)
    assert report["same_as_p1"] == {"rate": None, "interval_95": None, "with_tera_too": None}
    assert report["think_seconds"] is None


def test_main_skips_games_without_sets_and_writes_turns_and_summary(tmp_path, capsys):
    unlisted = copy.deepcopy(EXAMPLE)
    unlisted["sides"]["p2"]["pokemon"][5]["species"] = "swanna"
    dump = write_dump(tmp_path / "turns.jsonl", two_turns("listed") + two_turns("unlisted", state=unlisted))
    priors = tmp_path / "priors.json"
    priors.write_text(json.dumps(OUR_PRIORS), encoding="utf-8")
    out = tmp_path / "backtest"

    assert engine.main(["--dump", str(dump), "--priors", str(priors), "--out", str(out), "--games", "5"]) == 0
    [turns] = out.glob("*-test-5g-seed2026.jsonl")
    [summary] = out.glob("*.summary.json")
    assert len(turns.read_text(encoding="utf-8").splitlines()) == 2
    assert json.loads(summary.read_text(encoding="utf-8"))["games"] == {"sampled": 2, "played": 1, "skipped_missing_species": 1}
    assert "skipped, no sets for swanna" in capsys.readouterr().out
