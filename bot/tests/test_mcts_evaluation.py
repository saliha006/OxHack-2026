import copy
import json
import random
from types import SimpleNamespace

import pytest

from bot import eval as harness
from bot.player import BattleSession
from bot.tests.test_eval import InlinePool, TEAM, fakes
from bot.tests.test_player import TO_TURN_2, StubAgent, request, trace_lines
from tests.test_belief import PRIORS


def test_observed_opponent_reply_links_to_the_preceding_decision(tmp_path):
    session = BattleSession("battle-gen9ou-1", StubAgent(), tmp_path)
    for line in TO_TURN_2:
        session.feed(line)
    session.decide(request("move_request"), "p1")
    session.feed("|move|p2a: Gholdengo|Make It Rain|p1a: Kingambit")
    session.feed("|turn|3")
    session.decide({**request("move_request"), "rqid": 99}, "p1")
    lines = trace_lines(tmp_path)
    observation = lines[1]
    assert observation["kind"] == "observation"
    assert observation["decision_id"] == lines[0]["decision_id"]
    assert observation["opponent_action_status"] == "observed"
    assert observation["opponent_actions"] == [{"kind": "move", "move": "makeitrain", "slot": 2}]
    assert lines[2]["decision_id"] != lines[0]["decision_id"]
    session.close(None, 3)


def test_unobserved_reply_is_unknown_and_the_agent_closes_at_battle_end(tmp_path):
    closed = []
    agent = StubAgent()
    agent.close = lambda: closed.append(True)
    session = BattleSession("battle-gen9ou-1", agent, tmp_path)
    session.decide(request("move_request"), "p1")
    session.close(True, 1)
    observation = trace_lines(tmp_path)[1]
    assert observation["opponent_action_status"] == "unknown"
    assert observation["opponent_actions"] is None
    assert closed == [True]


def test_wait_requests_do_not_replay_stale_trace_or_consume_pending_events(tmp_path):
    agent = StubAgent(trace={"backend": "mcts", "requested_worlds": 8})
    session = BattleSession("battle-gen9ou-1", agent, tmp_path)
    for line in TO_TURN_2:
        session.feed(line)
    session.decide(request("move_request"), "p1")
    session.feed("|move|p2a: Gholdengo|Make It Rain|p1a: Kingambit")
    assert session.decide({"wait": True}, "p1") is None
    assert session.decisions == 1 and len(agent.states) == 1 and len(trace_lines(tmp_path)) == 1
    assert session.parser.state["last_turn"][0]["move"] == "makeitrain"
    assert trace_lines(tmp_path)[0]["request"] == request("move_request")
    session.close(None, 2)


def test_agent_players_use_distinct_trace_directories_in_a_shared_battle(tmp_path):
    a = harness.make_player("full", False, PRIORS, 3, str(tmp_path), TEAM, random.Random(1))
    b = harness.make_player("mcts1", False, PRIORS, 3, str(tmp_path), TEAM, random.Random(2))
    assert a.runs_dir != b.runs_dir
    assert a.runs_dir.parent == b.runs_dir.parent == tmp_path / "players"
    assert a.runs_dir.name == a.username and b.runs_dir.name == b.username


def test_repeated_run_seed_does_not_reconnect_to_an_old_showdown_account(tmp_path):
    a = harness.make_player("mcts1", False, PRIORS, 3, str(tmp_path), TEAM, random.Random(1))
    b = harness.make_player("mcts1", False, PRIORS, 3, str(tmp_path), TEAM, random.Random(1))
    assert a.username != b.username


def test_matched_mcts_comparison_has_no_artificial_response_jitter(tmp_path, fakes):
    players = {}
    harness.play_game("mcts-current", 0, players, ["TEAM"], PRIORS, 3, str(tmp_path), random.Random(1), 2026)
    assert all(not hasattr(p, "jitter_rng") for p in players.values())


def test_forced_replacement_after_faint_is_unknown_root_reply(tmp_path):
    session = BattleSession("battle-gen9ou-1", StubAgent(), tmp_path)
    for line in TO_TURN_2:
        session.feed(line)
    session.decide(request("move_request"), "p1")
    session.feed("|move|p1a: Kingambit|Kowtow Cleave|p2a: Gholdengo")
    session.feed("|-damage|p2a: Gholdengo|0 fnt")
    session.feed("|faint|p2a: Gholdengo")
    session.feed("|switch|p2a: Samurott|Samurott-Hisui, F|100/100")
    session.close(True, 2)
    observation = trace_lines(tmp_path)[1]
    assert observation["opponent_action_status"] == "unknown" and observation["opponent_actions"] is None
    assert observation["followup_actions"] == [{"kind": "switch", "move": None, "slot": 1}]


def test_pivot_keeps_the_move_as_root_reply_and_records_followup_switch(tmp_path):
    session = BattleSession("battle-gen9ou-1", StubAgent(), tmp_path)
    for line in TO_TURN_2:
        session.feed(line)
    session.decide(request("move_request"), "p1")
    session.feed("|move|p2a: Gholdengo|Volt Switch|p1a: Kingambit")
    session.feed("|switch|p2a: Samurott|Samurott-Hisui, F|100/100")
    session.close(False, 2)
    observation = trace_lines(tmp_path)[1]
    assert observation["opponent_actions"] == [{"kind": "move", "move": "voltswitch", "slot": 2}]
    assert observation["followup_actions"][0]["kind"] == "switch"


def test_rejected_choice_invalidates_belief_replay(tmp_path):
    invalidated = []
    agent = StubAgent()
    agent.invalidate_choice = lambda: invalidated.append(True)
    session = BattleSession("battle-gen9ou-1", agent, tmp_path)
    session.decide(request("move_request"), "p1")
    session.decide(request("move_request"), "p1")
    assert invalidated == [True]
    session.close(False, 2)


def test_structured_fallbacks_and_world_counts_reach_the_summary(tmp_path):
    agent = StubAgent(trace={"backend": "mcts", "fallback_reason": "worker_timeout", "search_ms": 123,
                             "requested_worlds": 8, "completed_worlds": 2, "failed_worlds": 1, "usable_worlds": 1})
    session = BattleSession("battle-gen9ou-1", agent, tmp_path, clock=iter([0.0, 0.4]).__next__)
    session.decide(request("move_request"), "p1")
    summary = session.close(False, 1)
    assert summary["fallbacks"] == 1
    assert summary["fallback_reasons"] == {"worker_timeout": 1}
    assert summary["completed_worlds"] == 2 and summary["failed_worlds"] == 1
    assert summary["think_p95_ms"] == 400
    assert summary["actual_search_ms"] == [123]


def test_mcts_arms_distinguish_equal_total_from_equal_per_world_compute():
    options = harness.MCTS_ARM_OPTIONS
    assert options["mcts1long"]["search_ms"] == options["mcts8"]["mcts_worlds"] * options["mcts8"]["search_ms"]
    assert options["mcts1"]["search_ms"] == options["mcts8"]["search_ms"]
    assert harness.MCTS_PAIRINGS["mcts-worlds-equal-total"][:2] == ("mcts1long", "mcts8")
    assert options["mcts8active"]["sampling"] == "active"
    assert options["mcts8frozen"]["frozen_beliefs"] is True


def test_mcts_team_pairs_match_across_comparisons_and_swap_sides(tmp_path, fakes):
    # Reuse the harness's fake players while verifying its actual side and team scheduling.
    for pairing in ("mcts-current", "mcts-bench"):
        players = {}
        a = harness.play_game(pairing, 0, players, ["T0", "T1"], PRIORS, 3.0, str(tmp_path),
                              random.Random(7), 123)
        b = harness.play_game(pairing, 1, players, ["T0", "T1"], PRIORS, 3.0, str(tmp_path),
                              random.Random(7), 123)
        assert a["team"] == b["team"] == harness.team_index(123, "mcts-current", 0, 2)
        assert {a["side"], b["side"]} == {"p1", "p2"}
        assert a["compute"]["a"]["engine_threads"] == 1


def test_manifest_records_team_and_prior_hashes_compute_and_heldout_role():
    a = harness.evaluation_manifest(["Team A", "Team B"], PRIORS, 3.0, 7, 2, "held-out")
    b = harness.evaluation_manifest(["Team A", "Team B"], copy.deepcopy(PRIORS), 3.0, 7, 2, "held-out")
    assert a == b and a["team_role"] == "held-out"
    assert a["concurrent_games"] == 2 and a["engine_version"] == "0.0.48"
    assert a["team_hashes"][0] != a["team_hashes"][1]
    assert a["arms"]["mcts8"]["mcts_worlds"] == 8


def test_action_agreement_measures_actions_and_keeps_traces_without_comparing_visits():
    choices = iter(["move 1", "move 1", "switch 2"])
    closed = []
    def make_agent():
        return SimpleNamespace(choose=lambda *_: next(choices), close=lambda: closed.append(True),
                               last_trace={"completed_worlds": 1})
    measured = harness.action_agreement(make_agent, {}, {}, 3)
    assert measured["choices"] == {"move 1": 2, "switch 2": 1}
    assert measured["pairwise_action_agreement"] == pytest.approx(1 / 3)
    assert len(measured["traces"]) == 3 and len(closed) == 3


def test_report_pools_actual_decision_latencies_instead_of_averaging_percentiles():
    from bot.tests.test_eval import result
    rows = [result("mcts-current", 0), result("mcts-current", 1)]
    rows[0].update(decision_ms=[10, 20], actual_search_ms=[5, 10], completed_worlds=2, failed_worlds=0)
    rows[1].update(decision_ms=[30, 100], actual_search_ms=[20, 50], completed_worlds=2, failed_worlds=1,
                   fallback_reasons={"worker_timeout": 1})
    report = harness.report(rows)["mcts-current"]
    assert report["think_p50_ms"] == 25
    assert report["think_p95_ms"] == 89.5
    assert report["actual_search_ms"] == 85
    assert report["completed_worlds"] == 4 and report["failed_worlds"] == 1
    assert report["fallback_reasons"] == {"worker_timeout": 1}


def test_saved_config_is_runnable_explicit_options_win_and_incompatible_resume_fails(tmp_path, monkeypatch):
    jobs = []
    monkeypatch.setattr(harness, "ProcessPoolExecutor", InlinePool)
    monkeypatch.setattr(harness, "play_shard", lambda *args: jobs.append(args))
    teams = tmp_path / "team.txt"
    priors = tmp_path / "priors.json"
    config = tmp_path / "config.json"
    teams.write_text(TEAM, encoding="utf-8")
    priors.write_text(json.dumps(PRIORS), encoding="utf-8")
    config.write_text(json.dumps({"pairings": ["mcts-current"], "games": 6, "budget": 2.0,
                                  "teams": str(teams), "priors": str(priors), "shards": 1}), encoding="utf-8")
    args = ["--runs", str(tmp_path / "results"), "run", "--config", str(config), "--games", "2"]
    assert harness.main(args) == 0
    assert len(jobs) == 1 and len(jobs[0][0]) == 2 and jobs[0][3] == 2.0
    with pytest.raises(SystemExit) as error:
        harness.main([*args, "--budget", "3"])
    assert error.value.code == 2


def test_priors_derived_from_evaluation_teams_cannot_be_declared_heldout(tmp_path):
    with pytest.raises(SystemExit) as error:
        harness.main(["--runs", str(tmp_path), "run", "--pairings", "mcts-current", "--games", "2",
                      "--teams", "bot/teams/standin-gen9ou.txt", "--priors-from-teams", "--team-role", "held-out"])
    assert error.value.code == 2


def test_the_deeper_arm_spends_the_same_search_time_as_mcts8_and_the_new_pairings_play_the_search_bot():
    deeper, current = harness.arm_config("mcts4x300", 3.0), harness.arm_config("mcts8", 3.0)
    assert (deeper["mcts_worlds"], deeper["search_ms"]) == (4, 300)
    assert deeper["mcts_worlds"] * deeper["search_ms"] == current["mcts_worlds"] * current["search_ms"]
    for name in ("mcts-headline", "mcts-foulplay-high", "mcts-deeper-foulplay-high", "mcts-deeper"):
        assert harness.arm_config(harness.PAIRINGS[name][0], 3.0)["backend"] == "mcts"
    assert harness.PAIRINGS["mcts-foulplay-high"][1] == "fphigh"
