import asyncio
import json
import logging
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from poke_env import AccountConfiguration
from poke_env.player import Player

from bot.parser import Parser
from bot.player import AgentPlayer, BattleSession

ROOT = Path(__file__).parent.parent.parent
REPLAY = (Path(__file__).parent / "fixtures" / "gen9ou-2703852247.log").read_text(encoding="utf-8").splitlines()
TO_TURN_2 = REPLAY[: REPLAY.index("|turn|2") + 1]


def request(name: str) -> dict:
    return json.loads((ROOT / "tests" / "fixtures" / f"{name}.json").read_text(encoding="utf-8"))


class StubAgent:
    def __init__(self, choice="move 1", fail=False, trace=None):
        self.choice, self.fail, self.states = choice, fail, []
        if trace is not None:
            self.last_trace = trace

    def choose(self, request, battle):
        self.states.append(battle)
        if self.fail:
            logging.getLogger("decision").error("decision failed")
        return self.choice


def session(tmp_path, agent=None, ticks=None):
    clock = iter(ticks).__next__ if ticks else None
    kwargs = {"clock": clock} if clock else {}
    return BattleSession("battle-gen9ou-1", agent or StubAgent(), tmp_path, **kwargs)


def trace_lines(tmp_path):
    return [json.loads(line) for line in (tmp_path / "battle-gen9ou-1.jsonl").read_text(encoding="utf-8").splitlines()]


def test_lines_before_the_first_request_reach_the_parser_once_our_side_is_known(tmp_path):
    agent = StubAgent()
    s = session(tmp_path, agent)
    for line in TO_TURN_2:
        s.feed(line)
    s.decide(request("move_request"), "p2")
    expected = Parser("p2")
    for line in TO_TURN_2:
        expected.feed(line)
    assert agent.states == [expected.snapshot()]


def test_lines_after_the_first_request_go_straight_to_the_parser(tmp_path):
    agent = StubAgent()
    s = session(tmp_path, agent)
    s.decide(request("team_preview_request"), "p1")
    for line in TO_TURN_2:
        s.feed(line)
    s.decide({**request("move_request"), "rqid": 4}, "p1")
    assert agent.states[1]["turn"] == 2


def test_every_line_lands_in_the_raw_log(tmp_path):
    s = session(tmp_path)
    for line in TO_TURN_2:
        s.feed(line)
    s.close(None, 2)
    assert (tmp_path / "battle-gen9ou-1.log").read_text(encoding="utf-8").splitlines() == TO_TURN_2


def test_a_decision_writes_a_trace_line_that_reloads_into_the_same_state(tmp_path):
    agent = StubAgent(choice="switch 3")
    s = session(tmp_path, agent, ticks=[10.0, 10.25])
    for line in TO_TURN_2:
        s.feed(line)
    assert s.decide(request("move_request"), "p1") == "switch 3"
    line = trace_lines(tmp_path)[0]
    assert line["state"] == agent.states[0]
    assert (line["turn"], line["kind"], line["choice"], line["think_ms"], line["fallback"]) == (2, "move", "switch 3", 250.0, False)


def test_the_agents_own_trace_fields_are_merged_into_the_line(tmp_path):
    s = session(tmp_path, StubAgent(trace={"top": [["move 1", 0.6]], "win_probability": 0.6}))
    s.decide(request("move_request"), "p1")
    line = trace_lines(tmp_path)[0]
    assert line["top"] == [["move 1", 0.6]] and line["win_probability"] == 0.6


@pytest.mark.parametrize("name, kind", [("team_preview_request", "team"), ("force_switch_request", "switch"),
                                        ("move_request", "move")])
def test_the_trace_names_the_request_kind(tmp_path, name, kind):
    s = session(tmp_path)
    s.decide(request(name), "p1")
    assert trace_lines(tmp_path)[0]["kind"] == kind


def test_an_error_on_the_decision_logger_counts_as_a_fallback_and_lands_in_the_battle_log(tmp_path):
    s = session(tmp_path, StubAgent(fail=True))
    s.decide(request("move_request"), "p1")
    summary = s.close(False, 1)
    assert (summary["decisions"], summary["fallbacks"]) == (1, 1)
    assert trace_lines(tmp_path)[0]["fallback"] is True
    assert "decision failed" in (tmp_path / "battle-gen9ou-1.decision.log").read_text(encoding="utf-8")
    assert s.errors not in logging.getLogger("decision").handlers


def test_a_rejected_choice_retries_with_the_first_legal_option_then_default(tmp_path):
    agent = StubAgent(choice="move 4")
    s = session(tmp_path, agent)
    req = request("move_request")
    assert s.decide(req, "p1") == "move 4"
    assert s.decide(req, "p1") == "move 1"
    assert s.decide(req, "p1") == "default"
    assert len(agent.states) == 1
    assert (s.decisions, s.fallbacks) == (1, 2)
    assert [line["kind"] for line in trace_lines(tmp_path)] == ["move", "retry", "retry"]


def test_a_new_request_is_decided_afresh(tmp_path):
    agent = StubAgent()
    s = session(tmp_path, agent)
    s.decide(request("move_request"), "p1")
    s.decide({**request("move_request"), "rqid": 99}, "p1")
    assert len(agent.states) == 2 and s.fallbacks == 0


def test_a_retry_with_no_legal_option_sends_default(tmp_path):
    s = session(tmp_path)
    s.decide({"rqid": 7, "side": {}}, "p1")
    assert s.decide({"rqid": 7, "side": {}}, "p1") == "default"


@pytest.mark.parametrize("ms, p50, p99", [([], None, None), ([12.34], 12.3, 12.3), ([10.0, 20.0, 30.0], 20.0, 29.8)])
def test_the_summary_reports_think_time_percentiles(tmp_path, ms, p50, p99):
    s = session(tmp_path)
    s.think_ms = ms
    summary = s.close(True, 30)
    assert (summary["think_p50_ms"], summary["think_p99_ms"]) == (p50, p99)
    assert trace_lines(tmp_path)[-1] == {"kind": "end", **summary}


def player(tmp_path, agent=None):
    p = AgentPlayer(make_agent=lambda: agent or StubAgent(), runs_dir=tmp_path,
                    account_configuration=AccountConfiguration("tester", None), battle_format="gen9ou",
                    start_listening=False)
    p.ps_client.send_message = AsyncMock()
    return p


def test_late_battle_message_does_not_reopen_or_truncate_finished_artifacts(tmp_path, monkeypatch):
    p = player(tmp_path)
    tag = "battle-gen9ou-1"
    s = BattleSession(tag, StubAgent(), tmp_path)
    p.sessions[tag] = s
    s.feed("|turn|12")
    p._battle_finished_callback(battle(request("move_request")))
    trace = (tmp_path / f"{tag}.jsonl").read_bytes()
    raw = (tmp_path / f"{tag}.log").read_bytes()
    upstream = AsyncMock()
    monkeypatch.setattr(Player, "_handle_battle_message", upstream)
    asyncio.run(p._handle_battle_message([[f">{tag}"], ["", "request", ""]]))
    assert tag not in p.sessions
    assert len(p.summaries) == 1
    assert (tmp_path / f"{tag}.jsonl").read_bytes() == trace
    assert (tmp_path / f"{tag}.log").read_bytes() == raw
    assert not upstream.called


def battle(req, tag="battle-gen9ou-1"):
    return SimpleNamespace(battle_tag=tag, last_request=req, player_role="p1", won=True, turn=12)


def test_the_parser_sees_a_message_before_poke_env_handles_it(tmp_path, monkeypatch):
    async def scenario():
        seen = []
        p = player(tmp_path)

        async def poke_env_handler(self, split_messages):
            seen.append(list(self.sessions["battle-gen9ou-1"].backlog))

        monkeypatch.setattr(Player, "_handle_battle_message", poke_env_handler)
        await p._handle_battle_message([[">battle-gen9ou-1"], ["", "player", "p1", "tester", ""], [""], ["", "turn", "1"]])
        assert seen == [["|player|p1|tester|", "|turn|1"]]

    asyncio.run(scenario())


def test_a_poke_env_failure_on_a_request_still_answers_it(tmp_path, monkeypatch):
    async def scenario():
        p = player(tmp_path)

        async def broken(self, split_messages):
            raise RuntimeError("poke-env bug")

        monkeypatch.setattr(Player, "_handle_battle_message", broken)
        await p._handle_battle_message([[">battle-gen9ou-1"], ["", "turn", "1"]])
        p.ps_client.send_message.assert_not_awaited()
        await p._handle_battle_message([[">battle-gen9ou-1"], ["", "request", "{}"]])
        p.ps_client.send_message.assert_awaited_once_with("/choose default", "battle-gen9ou-1")

    asyncio.run(scenario())


def test_non_battle_rooms_open_no_session(tmp_path, monkeypatch):
    async def scenario():
        p = player(tmp_path)
        monkeypatch.setattr(Player, "_handle_battle_message", AsyncMock())
        await p._handle_battle_message([[">game-bestof3-gen9ou-1"], ["", "init", "game"]])
        assert p.sessions == {}

    asyncio.run(scenario())


def test_moves_and_team_preview_are_sent_as_choose_commands(tmp_path, monkeypatch):
    async def scenario():
        monkeypatch.setattr(Player, "_handle_battle_message", AsyncMock())
        p = player(tmp_path, StubAgent(choice="team 213456"))
        await p._handle_battle_message([[">battle-gen9ou-1"], ["", "init", "battle"]])
        assert p.teampreview(battle(request("team_preview_request"))) == "/choose team 213456"
        p.sessions["battle-gen9ou-1"].agent.choice = "move 2 terastallize"
        assert p.choose_move(battle(request("move_request"))).message == "/choose move 2 terastallize"

    asyncio.run(scenario())


def test_a_finished_battle_closes_its_session_and_keeps_the_summary(tmp_path, monkeypatch):
    async def scenario():
        monkeypatch.setattr(Player, "_handle_battle_message", AsyncMock())
        p = player(tmp_path)
        await p._handle_battle_message([[">battle-gen9ou-1"], ["", "init", "battle"]])
        p.choose_move(battle(request("move_request")))
        p._battle_finished_callback(battle(None))
        assert p.sessions == {}
        assert p.summaries[0]["tag"] == "battle-gen9ou-1" and p.summaries[0]["won"] is True and p.summaries[0]["turns"] == 12

    asyncio.run(scenario())


@pytest.mark.parametrize("choice, words", [
    ("move 2", "Kowtow Cleave"), ("move 1 terastallize", "Swords Dance + Tera"), ("switch 3", "switch to Gholdengo"),
    ("team 213456", "lead with Great Tusk"), ("default", None), ("move 9", None), (None, None)])
def test_a_choice_is_labelled_in_words_from_its_request(choice, words):
    from bot.player import label
    assert label(request("move_request"), choice) == words


def test_each_decision_is_handed_to_the_callback_with_its_battle_tag(tmp_path):
    seen = []
    s = BattleSession("battle-gen9ou-1", StubAgent(choice="move 2"), tmp_path, on_decision=lambda tag, line: seen.append((tag, line)))
    s.decide(request("move_request"), "p1")
    assert seen[0][0] == "battle-gen9ou-1" and seen[0][1]["label"] == "Kowtow Cleave"
    assert seen[0][1] == trace_lines(tmp_path)[0]
