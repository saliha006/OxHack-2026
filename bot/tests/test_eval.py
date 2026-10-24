import asyncio
import copy
import json
import math
import random
from concurrent.futures import Future
from pathlib import Path
from types import SimpleNamespace

import pytest
from poke_env.player import RandomPlayer

from bot import eval as harness
from bot.eval import AblatedAgent, FlatBelief, FrozenBelief
from bot.player import AgentPlayer
from decision.agent import Agent
from tests.test_belief import PRIORS
from tests.turn2 import EXAMPLE, REQUEST

TEAM = (Path(__file__).parent.parent / "teams" / "standin-gen9ou.txt").read_text(encoding="utf-8").strip()


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


def test_players_get_random_names_and_only_the_opponent_side_is_jittered(tmp_path):
    rng = random.Random(1)
    ours = harness.make_player("full", False, PRIORS, 1.0, str(tmp_path), TEAM, rng)
    theirs = harness.make_player("random", True, PRIORS, 1.0, str(tmp_path), TEAM, rng)
    assert type(ours) is AgentPlayer
    assert isinstance(theirs, RandomPlayer) and isinstance(theirs, harness.Jitter)
    assert ours.username != theirs.username and ours.username.startswith("ox") and len(ours.username) == 10
    assert not hasattr(ours, "jitter_rng")


def test_jitter_waits_a_capped_random_time_before_the_real_move(monkeypatch):
    waits = []

    async def fake_sleep(seconds):
        waits.append(seconds)

    class Base:
        def choose_move(self, battle):
            return f"move for {battle}"

    class Jittered(harness.Jitter, Base):
        pass

    # Only the harness's view of asyncio: patching the real module would also catch the event loop's own sleeps.
    monkeypatch.setattr(harness, "asyncio", SimpleNamespace(sleep=fake_sleep))
    player = Jittered()
    player.jitter_rng = random.Random(0)
    moves = [asyncio.run(player.choose_move(n)) for n in range(2000)]
    assert moves[0] == "move for 0"
    assert 0 < min(waits) and max(waits) == 3.0  # about 0.7% of draws pass 3 s and are capped
    assert 0.2 < sorted(waits)[1000] < 0.3  # median near 0.25 s


def result(pairing, game, winner="a", team=0, fallbacks=0, decisions=40, p99=300.0, a="full", b="random"):
    return {"pairing": pairing, "game": game, "a": a, "b": b, "team": team, "side": "p1", "winner": winner,
            "turns": 30, "battle": "battle-gen9ou-1", "decisions": decisions, "fallbacks": fallbacks,
            "think_p50_ms": 60.0, "think_p99_ms": p99}


def write(runs, name, rows):
    (runs / "eval").mkdir(exist_ok=True)
    (runs / "eval" / name).write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def test_finished_games_are_read_from_every_shard_and_machine(tmp_path):
    write(tmp_path, "a-0.jsonl", [result("headline", 0), result("random", 2)])
    write(tmp_path, "b-1.jsonl", [result("headline", 1)])
    assert harness.done_games(tmp_path) == {("headline", 0), ("headline", 1), ("random", 2)}


def test_the_schedule_shuffles_every_pairing_together_and_skips_finished_games():
    shards = harness.schedule({"headline": 6, "random": 4}, 3, {("headline", 0)}, seed=7)
    games = [g for shard in shards for g in shard]
    assert sorted(games) == sorted([("headline", g) for g in range(1, 6)] + [("random", g) for g in range(4)])
    assert len(shards) == 3 and {len(s) for s in shards} == {3}
    assert games != sorted(games)
    assert harness.schedule({"headline": 6, "random": 4}, 3, {("headline", 0)}, seed=7) == shards
    assert harness.schedule({"random": 1}, 2, {("random", 0)}, seed=7) == []


def test_each_game_draws_the_same_team_and_side_every_time():
    first = harness.game_rng(1, "headline", 4)
    again = harness.game_rng(1, "headline", 4)
    assert [first.random() for _ in range(3)] == [again.random() for _ in range(3)]
    assert harness.game_rng(1, "headline", 5).random() != harness.game_rng(1, "headline", 4).random()


def test_wilson_interval():
    assert harness.wilson(0, 0) == (0.0, 1.0)
    lo, hi = harness.wilson(50, 100)
    assert (round(lo, 3), round(hi, 3)) == (0.404, 0.596)


def test_team_bootstrap_resamples_whole_teams():
    rows = [result("h", g, team=0) for g in range(5)]
    assert harness.team_bootstrap(rows) == (1.0, 1.0)
    rows += [result("h", g, "b", team=1) for g in range(5, 10)]
    assert harness.team_bootstrap(rows) == (0.0, 1.0)


def test_report_merges_rows_counts_ties_as_half_and_skips_unplayed_pairings():
    rows = [result("headline", 0), result("headline", 1, "tie", team=1),
            result("headline", 2, "b", fallbacks=4, p99=900.0)]
    table = harness.report(rows)
    assert list(table) == ["headline"]
    h = table["headline"]
    assert (h["games"], h["planned"], h["teams"]) == (3, 300, 2)
    assert h["win_rate"] == pytest.approx(0.5)
    assert h["fallback_rate"] == pytest.approx(4 / 120)
    assert h["worst_game_p99_ms"] == 900.0


def test_report_handles_pairings_with_no_agent_on_side_a():
    rows = [{k: v for k, v in result("random", 0).items() if k not in ("decisions", "fallbacks", "think_p50_ms", "think_p99_ms")}]
    r = harness.report(rows)["random"]
    assert r["fallback_rate"] is None and r["worst_game_p99_ms"] is None


def test_teams_load_from_a_file_or_a_folder_without_trailing_blank_lines(tmp_path):
    (tmp_path / "a.txt").write_text("A\n\n\n", encoding="utf-8")
    (tmp_path / "b.txt").write_text("B", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    assert harness.load_teams(tmp_path) == ["A", "B"]
    assert harness.load_teams(tmp_path / "a.txt") == ["A"]


class FakeBaseline:
    def __init__(self, name):
        self.name, self.teams, self.battles = name, [], {}

    def update_team(self, team):
        self.teams.append(team)

    async def battle_against(self, other, n_battles):
        a, b = (self, other) if self.side == "a" else (other, self)
        n = len(a.battles)
        won = None if n == 2 else n % 2 == 0
        a.battles[n] = SimpleNamespace(won=won, turn=20 + n, player_role="p1" if a is self else "p2",
                                       battle_tag=f"battle-gen9ou-{n}")
        if isinstance(a, FakeAgentPlayer):
            a.summaries.append({"decisions": 21, "fallbacks": n, "think_p50_ms": 50.0, "think_p99_ms": 200.0})


class FakeAgentPlayer(FakeBaseline):
    def __init__(self, name):
        super().__init__(name)
        self.summaries = []


@pytest.fixture
def fakes(monkeypatch):
    made = []

    def make_player(name, jittered, priors, budget, runs, team, rng):
        player = (FakeAgentPlayer if name in harness.ARMS else FakeBaseline)(name)
        player.side = "b" if jittered else "a"
        made.append(player)
        return player

    monkeypatch.setattr(harness, "make_player", make_player)
    monkeypatch.setattr(harness, "AgentPlayer", FakeAgentPlayer)
    return made


def shard_rows(tmp_path):
    return [json.loads(line) for line in (tmp_path / "eval" / "m-0.jsonl").read_text(encoding="utf-8").splitlines()]


def test_a_shard_reuses_players_varies_teams_and_appends_one_line_per_game(tmp_path, fakes):
    games = [("headline", 0), ("random", 0), ("headline", 1)]
    harness.play_shard(games, ["T0", "T1", "T2"], PRIORS, 1.0, str(tmp_path), "m", 0, seed=3)
    rows = shard_rows(tmp_path)
    assert [(r["pairing"], r["game"]) for r in rows] == games
    assert [(p.name, p.side) for p in fakes] == [("full", "a"), ("simpleheuristics", "b"), ("random", "b")]
    assert [r["winner"] for r in rows] == ["a", "b", "tie"]
    assert [r["team"] for r in rows] == [harness.game_rng(3, p, g).randrange(3) for p, g in games]
    assert rows[1]["fallbacks"] == 1 and rows[0]["battle"] == "battle-gen9ou-0"
    assert fakes[0].teams == [f"T{r['team']}" for r in rows]


def test_a_shard_with_a_baseline_on_side_a_records_no_agent_numbers(tmp_path, fakes, monkeypatch):
    monkeypatch.setitem(harness.PAIRINGS, "bots", ("random", "maxbasepower", 1))
    harness.play_shard([("bots", 0)], ["T0"], PRIORS, 1.0, str(tmp_path), "m", 0, seed=3)
    assert "decisions" not in shard_rows(tmp_path)[0]


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


def test_run_submits_one_shuffled_job_per_shard_with_unfinished_games_only(tmp_path, monkeypatch):
    jobs = []
    monkeypatch.setattr(harness, "ProcessPoolExecutor", InlinePool)
    monkeypatch.setattr(harness, "play_shard", lambda *args: jobs.append(args))
    write(tmp_path, "x-0.jsonl", [result("random", 0)])
    (tmp_path / "teams").mkdir()
    (tmp_path / "teams" / "t.txt").write_text(TEAM + "\n\n", encoding="utf-8")
    code = harness.main(["--runs", str(tmp_path), "run", "--pairings", "random", "--games", "5", "--shards", "2",
                         "--teams", str(tmp_path / "teams"), "--priors-from-teams", "--machine", "m", "--seed", "9"])
    assert code == 0
    assert [(j[4], j[5], j[6]) for j in jobs] == [(str(tmp_path), "m", 0), (str(tmp_path), "m", 1)]
    assert sorted(g for j in jobs for g in j[0]) == [("random", g) for g in range(1, 5)]
    assert jobs[0][1] == [TEAM] and "zapdos" in jobs[0][2]["species"] and jobs[0][7] == 9


def test_run_reads_priors_from_a_file(tmp_path, monkeypatch):
    jobs = []
    monkeypatch.setattr(harness, "ProcessPoolExecutor", InlinePool)
    monkeypatch.setattr(harness, "play_shard", lambda *args: jobs.append(args))
    priors = tmp_path / "priors.json"
    priors.write_text(json.dumps(PRIORS), encoding="utf-8")
    harness.main(["--runs", str(tmp_path), "run", "--pairings", "random", "--games", "1", "--shards", "1",
                  "--teams", "bot/teams/standin-gen9ou.txt", "--priors", str(priors)])
    assert jobs[0][2] == PRIORS


def test_report_command_prints_and_saves_the_table(tmp_path, capsys):
    write(tmp_path, "a-0.jsonl", [result("random", 0), result("random", 1, "b")])
    assert harness.main(["--runs", str(tmp_path), "report"]) == 0
    assert "random                full vs random: 50.0% over 2/30 games" in capsys.readouterr().out
    assert json.loads((tmp_path / "eval-summary.json").read_text(encoding="utf-8"))["pairings"]["random"]["games"] == 2


def test_an_epsilon_mix_plays_random_moves_at_its_rate_and_its_own_otherwise():
    class Own:
        def choose_move(self, battle):
            return "own"

        def choose_random_move(self, battle):
            return "random"

    mixed = harness._mixed(Own, 0.31)()
    mixed.move_rng = random.Random(4)
    picks = [mixed.choose_move(None) for _ in range(4000)]
    assert type(mixed).__name__ == "OwnEps31"
    assert 0.28 < picks.count("random") / 4000 < 0.34


def test_mixed_levels_are_built_for_the_ladder_and_seeded_by_make_player(tmp_path):
    assert [harness.BASELINES[n].eps for n in ("sh83", "sh58", "sh31", "sh12", "mb46")] == [0.83, 0.58, 0.31, 0.12, 0.46]
    player = harness.make_player("sh31", True, PRIORS, 1.0, str(tmp_path), TEAM, random.Random(2))
    assert isinstance(player, harness.EpsilonMix) and isinstance(player, harness.Jitter)
    assert isinstance(player.move_rng, random.Random)


def test_ladder_pairings_cover_the_agent_and_every_neighbour_without_repeating_core_pairs():
    core = {"headline": ("full", "b", 300), "rev": ("c", "b", 10)}
    extra = harness.ladder_pairings(core, ["a", "b", "c", "full"], vs_agent=40, neighbours=30)
    assert extra == {"full~a": ("full", "a", 40), "full~c": ("full", "c", 40), "a~b": ("a", "b", 30)}


def test_the_real_ladder_has_every_level_and_its_neighbours():
    pairs = {frozenset((a, b)) for a, b, _ in harness.PAIRINGS.values()}
    assert all(frozenset(("full", level)) in pairs for level in harness.LADDER[:-1])
    assert all(frozenset(p) in pairs for p in zip(harness.LADDER, harness.LADDER[1:]))
    assert all(name in harness.ARMS or name in harness.BASELINES for name in harness.LADDER)


def games(a, b, a_wins, b_wins, ties=0):
    return ([result("p", 0, "a", a=a, b=b)] * a_wins + [result("p", 0, "b", a=a, b=b)] * b_wins
            + [result("p", 0, "tie", a=a, b=b)] * ties)


def test_ratings_put_the_anchor_at_1000_and_a_three_to_one_edge_near_plus_191():
    table = harness.ratings(games("strong", "random", 750, 250), draws=50)
    assert table["random"]["elo"] == pytest.approx(1000)
    assert table["strong"]["elo"] == pytest.approx(1000 + 400 * math.log10(3), abs=2)
    lo, hi = table["strong"]["elo_95"]
    assert lo < table["strong"]["elo"] < hi


def test_ratings_chain_through_neighbours_and_stay_finite_for_an_unbeaten_player():
    rows = games("mid", "random", 30, 10) + games("top", "mid", 20, 0)
    table = harness.ratings(rows, draws=20)
    assert table["random"]["elo"] < table["mid"]["elo"] < table["top"]["elo"] < math.inf


def test_neighbours_list_the_levels_around_the_agent_with_its_record():
    table = {n: {"elo": e, "elo_95": (e - 50, e + 50)} for n, e in
             [("random", 1000), ("sh83", 1100), ("full", 1300), ("sh12", 1350), ("fp", 1500)]}
    rows = games("full", "sh12", 3, 1) + games("sh12", "full", 0, 2, ties=2)
    near = harness.neighbours(table, rows, reach=2)
    assert [(n["step"], n["level"], n["gap"]) for n in near] == [(-2, "random", -300), (-1, "sh83", -200),
                                                                 (1, "sh12", 50), (2, "fp", 200)]
    sh12 = near[2]
    assert sh12["games"] == 8 and sh12["agent_win_rate"] == pytest.approx(6 / 8)
    assert near[3]["agent_win_rate"] is None and near[3]["games"] == 0


def test_report_command_prints_ratings_and_the_agents_neighbours(tmp_path, capsys):
    write(tmp_path, "a-0.jsonl", games("full", "random", 6, 2) + games("full", "sh12", 3, 3))
    harness.main(["--runs", str(tmp_path), "report"])
    out = capsys.readouterr().out
    assert "elo random" in out and "elo full" in out and "agent wins" in out
    summary = json.loads((tmp_path / "eval-summary.json").read_text(encoding="utf-8"))
    assert set(summary) == {"pairings", "ratings", "neighbours", "void_games"} and summary["ratings"]["random"]["elo"] == 1000


class FakeProcess:
    def __init__(self, args, cwd, stdout, stderr):
        self.args, self.cwd, self.stdout, self.exit_code, self.terminated = args, cwd, stdout, None, False

    def poll(self):
        return self.exit_code

    def terminate(self):
        self.terminated = True


@pytest.fixture
def popen(monkeypatch):
    started = []

    def fake_popen(args, cwd, stdout, stderr):
        started.append(FakeProcess(args, cwd, stdout, stderr))
        return started[-1]

    monkeypatch.setattr(harness.subprocess, "Popen", fake_popen)
    return started


def test_foul_play_starts_accepting_challenges_with_its_team_list_in_game_order(tmp_path, popen):
    paths = [tmp_path / "team_3.txt", tmp_path / "team_1.txt", tmp_path / "team_3.txt"]
    fp = harness.FoulPlay(212, paths, tmp_path, "oxabc")
    args = popen[0].args
    assert args[args.index("--bot-mode") + 1] == "accept_challenge"
    assert args[args.index("--search-time-ms") + 1] == "212" and args[args.index("--run-count") + 1] == "3"
    assert args[args.index("--ps-username") + 1] == "oxabc" and popen[0].cwd == harness.FOUL_PLAY
    team_list = Path(args[args.index("--team-list") + 1]).read_text(encoding="utf-8").splitlines()
    assert team_list == [str(p.resolve()) for p in paths]
    fp.close()
    assert popen[0].terminated and fp.output.closed


def test_foul_play_is_ready_once_it_waits_for_the_next_challenge(tmp_path, popen, monkeypatch):
    fp = harness.FoulPlay(100, [tmp_path / "t.txt"], tmp_path, "oxabc")
    fp.output.write("INFO Waiting for a gen9ou challenge\n")
    fp.output.flush()
    fp.wait_ready(timeout=5)
    assert fp.games == 1
    naps = []
    monkeypatch.setattr(harness.time, "sleep", lambda s: (naps.append(s), fp.output.write("Waiting for a\n"), fp.output.flush()))
    fp.wait_ready(timeout=5)
    assert fp.games == 2 and naps == [0.5]
    fp.close()


def test_foul_play_that_exits_or_stalls_raises_instead_of_hanging_the_shard(tmp_path, popen, monkeypatch):
    fp = harness.FoulPlay(100, [tmp_path / "t.txt"], tmp_path, "oxabc")
    popen[0].exit_code = 1
    with pytest.raises(RuntimeError, match="oxabc"):
        fp.wait_ready(timeout=5)
    popen[0].exit_code = None
    monkeypatch.setattr(harness.time, "sleep", lambda s: None)
    with pytest.raises(RuntimeError):
        fp.wait_ready(timeout=0)
    fp.close()


def test_a_shard_starts_one_foul_play_per_level_it_meets_with_teams_in_its_game_order(tmp_path, monkeypatch):
    made = []
    monkeypatch.setattr(harness, "FoulPlay", lambda ms, paths, folder, name: made.append((ms, paths, name)) or name)
    games = [("full~fpmid", 3), ("headline", 0), ("prior~fpmid", 1), ("full~fphigh", 0)]
    players = harness.start_foul_play(games, ["T0", "T1", "T2"], tmp_path, random.Random(5), seed=8)
    assert set(players) == {("b", "fpmid"), ("b", "fphigh")}
    ms, paths, name = made[0]
    assert 150 <= ms <= 260 and name.startswith("ox")
    expected = [harness.game_rng(8, p, g).randrange(3) for p, g in [("full~fpmid", 3), ("prior~fpmid", 1)]]
    assert [int(p.stem.split("_")[1]) for p in paths] == expected
    assert (tmp_path / "teams" / "team_2.txt").read_text(encoding="utf-8") == "T2"
    assert 450 <= made[1][0] <= 700


class FakeFoulPlay:
    def __init__(self):
        self.username, self.ready, self.closed = "oxfp", 0, False

    def wait_ready(self):
        self.ready += 1

    def close(self):
        self.closed = True


def test_a_game_against_foul_play_waits_for_it_then_challenges_it(tmp_path, monkeypatch):
    monkeypatch.setattr(harness, "FoulPlay", FakeFoulPlay)
    monkeypatch.setattr(harness, "AgentPlayer", FakeAgentPlayer)
    ours, fp = FakeAgentPlayer("full"), FakeFoulPlay()
    challenged = []

    async def send_challenges(username, n):
        challenged.append((username, n))
        ours.battles[0] = SimpleNamespace(won=False, turn=40, player_role="p1", battle_tag="battle-gen9ou-9")
        ours.summaries.append({"decisions": 41, "fallbacks": 0, "think_p50_ms": 50.0, "think_p99_ms": 300.0})

    ours.send_challenges = send_challenges
    players = {("a", "full"): ours, ("b", "fplow"): fp}
    line = harness.play_game("full~fplow", 2, players, ["T0", "T1"], PRIORS, 1.0, str(tmp_path), random.Random(1), 4)
    assert challenged == [("oxfp", 1)] and fp.ready == 1
    assert (line["winner"], line["side"], line["turns"], line["b"]) == ("b", "p1", 40, "fplow")
    assert ours.teams == [f"T{harness.game_rng(4, 'full~fplow', 2).randrange(2)}"]


def test_a_game_that_ends_at_team_preview_is_void(tmp_path, fakes, monkeypatch):
    async def instant_forfeit(self, other, n_battles):
        a = self if self.side == "a" else other
        a.battles[0] = SimpleNamespace(won=True, turn=0, player_role="p1", battle_tag="battle-gen9ou-0")
        a.summaries.append({"decisions": 1, "fallbacks": 0, "think_p50_ms": 5.0, "think_p99_ms": 5.0})

    monkeypatch.setattr(FakeBaseline, "battle_against", instant_forfeit)
    harness.play_shard([("headline", 0)], ["T0"], PRIORS, 1.0, str(tmp_path), "m", 0, seed=3)
    assert shard_rows(tmp_path)[0]["winner"] == "void"


def test_void_games_are_left_out_of_the_score_but_counted_in_the_report(tmp_path, capsys):
    write(tmp_path, "a-0.jsonl", [result("random", 0), result("random", 1, "void"), result("random", 2, "b")])
    assert [r["game"] for r in harness.scored(harness.read_results(tmp_path))] == [0, 2]
    harness.main(["--runs", str(tmp_path), "report"])
    assert "void games (a side dropped out at team preview, not scored): 1" in capsys.readouterr().out
    assert json.loads((tmp_path / "eval-summary.json").read_text(encoding="utf-8"))["pairings"]["random"]["games"] == 2


def test_a_shard_closes_its_foul_play_processes_even_when_a_game_fails(tmp_path, monkeypatch):
    fp = FakeFoulPlay()
    monkeypatch.setattr(harness, "FoulPlay", FakeFoulPlay)
    monkeypatch.setattr(harness, "start_foul_play", lambda *args: {("b", "fplow"): fp, ("a", "x"): object()})

    def broken(*args):
        raise RuntimeError("server went away")

    monkeypatch.setattr(harness, "play_game", broken)
    with pytest.raises(RuntimeError):
        harness.play_shard([("full~fplow", 0)], ["T0"], PRIORS, 1.0, str(tmp_path), "m", 0, seed=1)
    assert fp.closed
