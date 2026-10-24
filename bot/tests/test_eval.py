import copy
import json
from concurrent.futures import Future
from pathlib import Path

import pytest

from bot import eval as harness
from bot.eval import AblatedAgent, FlatBelief, FrozenBelief
from decision.agent import Agent
from tests.test_belief import PRIORS
from tests.turn2 import EXAMPLE, REQUEST

TEAM = (Path(__file__).parent.parent / "teams" / "standin-gen9ou.txt").read_text(encoding="utf-8")


def weights(belief, slot):
    return [round(w, 6) for _, w in belief.candidates[slot]]


def test_frozen_belief_keeps_the_prior_after_a_reveal_but_still_tracks_the_active_slot():
    battle = copy.deepcopy(EXAMPLE)
    belief = FrozenBelief(PRIORS, battle)
    battle["sides"]["p2"]["pokemon"][2]["item"] = "leftovers"
    belief.update(battle)
    assert weights(belief, 2) == [0.5, 0.3, 0.2]
    assert belief.previous is battle["sides"]["p2"]


def test_flat_belief_weighs_every_known_set_equally_for_the_whole_battle():
    battle = copy.deepcopy(EXAMPLE)
    belief = FlatBelief(PRIORS, battle)
    assert weights(belief, 0) == [0.5, 0.5] and weights(belief, 2) == [round(1 / 3, 6)] * 3
    belief.update(battle)
    assert weights(belief, 2) == [round(1 / 3, 6)] * 3


def test_an_ablated_agent_decides_with_its_own_belief():
    agent = AblatedAgent(PRIORS, FrozenBelief, budget=1.0)
    assert agent.choose(REQUEST, copy.deepcopy(EXAMPLE)).startswith(("move", "switch"))
    assert type(agent.belief) is FrozenBelief


def test_an_ablated_agent_still_answers_when_its_belief_cannot_be_built():
    agent = AblatedAgent({"source": PRIORS["source"], "species": {}}, FrozenBelief)
    assert agent.choose(REQUEST, copy.deepcopy(EXAMPLE)) == "move 1"
    assert agent.belief is None


def test_an_ablated_agent_builds_nothing_on_a_wait_request():
    agent = AblatedAgent(PRIORS, FlatBelief)
    assert agent.choose({"wait": True}, copy.deepcopy(EXAMPLE)) is None
    assert agent.belief is None


def test_each_arm_builds_the_agent_it_names():
    full, prior, flat, k1 = (harness.ARMS[a](PRIORS, 1.0) for a in ("full", "prior", "flat", "k1"))
    assert type(full) is Agent and (full.k, full.budget) == (5, 1.0)
    assert (prior.belief_cls, flat.belief_cls) == (FrozenBelief, FlatBelief)
    assert k1.k == 1


def result(match, game, winner="ours", team=0, fallbacks=0, decisions=40, p99=300.0):
    return {"match": match, "game": game, "team": team, "winner": winner, "tag": "t", "side": "p1", "won": True,
            "turns": 30, "decisions": decisions, "fallbacks": fallbacks, "think_p50_ms": 60.0, "think_p99_ms": p99}


def write(runs, name, rows):
    (runs / name).write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def test_finished_games_are_read_from_every_shard_and_machine(tmp_path):
    write(tmp_path, "eval-headline-a-0.jsonl", [result("headline", 0), result("headline", 2)])
    write(tmp_path, "eval-headline-b-1.jsonl", [result("headline", 1)])
    write(tmp_path, "eval-usage-a-0.jsonl", [result("usage", 5)])
    assert harness.done_games(tmp_path, "headline") == {0, 1, 2}


def test_remaining_games_are_dealt_across_shards_and_empty_shards_dropped():
    assert harness.shard_games(7, 3, {1, 4}) == [[0, 5], [2, 6], [3]]
    assert harness.shard_games(3, 2, {0, 1, 2}) == []


def test_wilson_interval():
    assert harness.wilson(0, 0) == (0.0, 1.0)
    lo, hi = harness.wilson(50, 100)
    assert (round(lo, 3), round(hi, 3)) == (0.404, 0.596)


def test_team_bootstrap_resamples_whole_teams():
    rows = [result("h", g, team=0) for g in range(5)]
    assert harness.team_bootstrap(rows) == (1.0, 1.0)
    rows += [result("h", g, "theirs", team=1) for g in range(5, 10)]
    lo, hi = harness.team_bootstrap(rows)
    assert lo == 0.0 and hi == 1.0


def test_report_merges_shards_counts_ties_as_half_and_skips_unplayed_matches(tmp_path):
    write(tmp_path, "eval-headline-a-0.jsonl", [result("headline", 0), result("headline", 1, "tie", team=1)])
    write(tmp_path, "eval-headline-a-1.jsonl", [result("headline", 2, "theirs", fallbacks=4, p99=900.0)])
    table = harness.report(tmp_path)
    assert list(table) == ["headline"]
    h = table["headline"]
    assert (h["games"], h["planned"], h["teams"]) == (3, 300, 2)
    assert h["win_rate"] == pytest.approx(0.5)
    assert h["fallback_rate"] == pytest.approx(4 / 120)
    assert h["worst_game_p99_ms"] == 900.0


def test_teams_load_from_a_file_or_a_folder(tmp_path):
    (tmp_path / "a.txt").write_text("A", encoding="utf-8")
    (tmp_path / "b.txt").write_text("B", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    assert harness.load_teams(tmp_path) == ["A", "B"]
    assert harness.load_teams(tmp_path / "a.txt") == ["A"]


class FakePlayer:
    def __init__(self, make_agent=None, runs_dir=None, **kwargs):
        self.name = kwargs["account_configuration"].username
        self.summaries, self.teams = [], []
        self.agent = make_agent() if make_agent else None

    def update_team(self, team):
        self.teams.append(team)

    async def battle_against(self, other, n_battles):
        ours = self if self.name.endswith(" a") else other
        ours.summaries.append({"tag": "t", "side": "p1" if ours is self else "p2", "won": len(ours.summaries) % 2 == 0,
                               "turns": 30, "decisions": 31, "fallbacks": 0, "think_p50_ms": 50.0, "think_p99_ms": 200.0})


@pytest.fixture
def fake_players(monkeypatch):
    monkeypatch.setattr(harness, "AgentPlayer", FakePlayer)
    monkeypatch.setattr(harness, "BASELINES", {name: FakePlayer for name in harness.BASELINES})


def test_a_shard_rotates_teams_alternates_sides_and_appends_one_line_per_game(tmp_path, fake_players):
    harness.play_shard("headline", [0, 1, 2], ["T0", "T1"], PRIORS, 1.0, str(tmp_path), "m", 0)
    rows = [json.loads(line) for line in (tmp_path / "eval-headline-m-0.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [(r["game"], r["team"], r["side"], r["winner"]) for r in rows] == [
        (0, 0, "p1", "ours"), (1, 1, "p2", "theirs"), (2, 0, "p1", "ours")]


def test_an_agent_vs_agent_shard_gives_both_sides_their_own_arm(tmp_path, fake_players, monkeypatch):
    built = []
    original = FakePlayer.__init__

    def recording_init(self, make_agent=None, runs_dir=None, **kwargs):
        original(self, make_agent, runs_dir, **kwargs)
        built.append(self.agent)

    monkeypatch.setattr(FakePlayer, "__init__", recording_init)
    harness.play_shard("usage", [0], ["T0"], PRIORS, 1.0, str(tmp_path), "m", 0)
    assert [a.belief_cls for a in built] == [FrozenBelief, FlatBelief]


class InlinePool:
    def __init__(self, max_workers):
        self.max_workers = max_workers

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def submit(self, fn, *args):
        future = Future()
        future.set_result(fn(*args))
        return future


def test_run_submits_one_job_per_shard_with_unfinished_games_only(tmp_path, monkeypatch):
    jobs = []
    monkeypatch.setattr(harness, "ProcessPoolExecutor", InlinePool)
    monkeypatch.setattr(harness, "play_shard", lambda *args: jobs.append(args))
    write(tmp_path, "eval-random-x-0.jsonl", [result("random", 0)])
    team = tmp_path / "team.txt"
    team.write_text(TEAM, encoding="utf-8")
    code = harness.main(["--runs", str(tmp_path), "run", "--matches", "random", "--games", "5", "--shards", "2",
                         "--teams", str(team), "--priors-from-team", "--machine", "m"])
    assert code == 0
    assert [(j[0], j[1], j[7]) for j in jobs] == [("random", [1, 3], 0), ("random", [2, 4], 1)]
    assert "zapdos" in jobs[0][3]["species"] and jobs[0][4] == 1.0


def test_run_reads_priors_from_a_file(tmp_path, monkeypatch):
    jobs = []
    monkeypatch.setattr(harness, "ProcessPoolExecutor", InlinePool)
    monkeypatch.setattr(harness, "play_shard", lambda *args: jobs.append(args))
    priors = tmp_path / "priors.json"
    priors.write_text(json.dumps(PRIORS), encoding="utf-8")
    harness.main(["--runs", str(tmp_path), "run", "--matches", "random", "--games", "1", "--shards", "1",
                  "--priors", str(priors)])
    assert jobs[0][3] == PRIORS


def test_report_command_prints_and_saves_the_table(tmp_path, capsys):
    write(tmp_path, "eval-random-a-0.jsonl", [result("random", 0), result("random", 1, "theirs")])
    assert harness.main(["--runs", str(tmp_path), "report"]) == 0
    assert "random        full vs random: 50.0% over 2/30 games" in capsys.readouterr().out
    assert json.loads((tmp_path / "eval-summary.json").read_text(encoding="utf-8"))["random"]["games"] == 2
