import json
from types import SimpleNamespace

import pytest

from bot import demo


def side(species="kingambit", hp=80, status="", active=0, fainted=0):
    team = [{"species": species, "hp_percent": hp, "status": status}] + [{"species": "x", "hp_percent": 100, "status": ""}] * 5
    for i in range(1, fainted + 1):
        team[i] = {"species": "x", "hp_percent": 0, "status": ""}
    return {"active": active, "pokemon": team}


def decision(**extra):
    state = {"us": "p2", "turn": 7, "sides": {"p2": side(status="tox"), "p1": side("gholdengo", 41, fainted=2)}}
    return {"turn": 7, "kind": "move", "choice": "move 2", "label": "Kowtow Cleave", "think_ms": 64.4,
            "fallback": False, "state": state, **extra}


def test_a_decision_shows_the_choice_in_words_and_both_actives_from_our_side():
    assert demo.format_line(decision()) == (
        "Turn   7 · Kowtow Cleave  (64 ms)\n"
        "    kingambit 80% tox (6 left)  vs  gholdengo 41% (4 left)")


def test_a_decision_without_a_label_or_leads_falls_back_to_the_raw_choice_and_dashes():
    line = decision(label=None, fallback=True)
    line["state"]["sides"]["p2"]["active"] = line["state"]["sides"]["p1"]["active"] = None
    assert demo.format_line(line).splitlines() == ["Turn   7 · move 2  (64 ms, fallback)", "    - (6 left)  vs  - (4 left)"]


def test_fields_the_agent_adds_are_shown_whatever_their_shape():
    text = demo.format_line(decision(win_probability=0.61234, top=[["move 2", 0.6]], note="steady", blob="y" * 300))
    assert "    win_probability: 0.612" in text
    assert '    top: [["move 2", 0.6]]' in text and "    note: steady" in text
    assert "    blob: " + "y" * 97 + "..." in text


@pytest.mark.parametrize("won, word", [(True, "won"), (False, "lost"), (None, "tied")])
def test_the_end_line_gives_the_result_and_the_numbers(won, word):
    end = {"kind": "end", "won": won, "turns": 30, "decisions": 33, "fallbacks": 2, "think_p50_ms": 60.0, "think_p99_ms": 400.0}
    assert demo.format_line(end) == f"Game over: {word} in 30 turns · 2/33 fallbacks · think p50 60.0 ms, p99 400.0 ms"


def test_a_retry_line_says_what_was_sent_instead():
    assert demo.format_line({"kind": "retry", "choice": "default"}) == "  Showdown rejected the choice; sent default instead"


def test_replay_prints_every_line_and_pauses_only_after_decisions(tmp_path):
    trace = tmp_path / "t.jsonl"
    lines = [decision(), {"kind": "retry", "choice": "move 1"}, decision(),
             {"kind": "end", "won": True, "turns": 8, "decisions": 2, "fallbacks": 1, "think_p50_ms": 1.0, "think_p99_ms": 2.0}]
    trace.write_text("".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8")
    printed, naps = [], []
    demo.replay(trace, 0.7, out=printed.append, sleep=naps.append)
    assert len(printed) == 4 and printed[-1].startswith("Game over: won")
    assert naps == [0.7, 0.7]


class FakeAgentPlayer:
    def __init__(self, make_agent, runs_dir, on_decision, **kwargs):
        self.on_decision, self.kwargs, self.summaries = on_decision, kwargs, []

    async def battle_against(self, rival, n_battles):
        self.on_decision("battle-gen9ou-5", decision())
        self.on_decision("battle-gen9ou-5", decision())
        self.summaries.append({"won": True, "turns": 9, "decisions": 2, "fallbacks": 0,
                               "think_p50_ms": 50.0, "think_p99_ms": 90.0})


def test_live_prints_the_watch_url_once_then_every_turn_and_the_result(monkeypatch, capsys):
    monkeypatch.setattr(demo, "AgentPlayer", FakeAgentPlayer)
    monkeypatch.setitem(demo.BASELINES, "simpleheuristics", lambda **kwargs: SimpleNamespace(**kwargs))
    naps = []
    monkeypatch.setattr(demo.time, "sleep", naps.append)
    summary = demo.live("TEAM", {"species": {}}, "simpleheuristics", 3.0, 1.5, "runs")
    out = capsys.readouterr().out
    assert out.count("http://localhost:8000/battle-gen9ou-5") == 1
    assert out.count("Kowtow Cleave") == 2 and "Game over: won in 9 turns" in out
    assert naps == [1.5, 1.5] and summary["turns"] == 9


def test_main_replays_a_trace(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(demo, "replay", lambda path, delay: calls.append((path, delay)))
    assert demo.main(["replay", str(tmp_path / "t.jsonl"), "--delay", "0.2"]) == 0
    assert calls == [(tmp_path / "t.jsonl", 0.2)]


def test_main_plays_live_with_a_team_from_the_pool_and_chosen_priors(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(demo, "live", lambda *args: calls.append(args))
    team = (tmp_path / "t.txt")
    team.write_text("Zapdos @ Heavy-Duty Boots\nAbility: Static\nTera Type: Grass\nEVs: 4 HP\nTimid Nature\n- Roost\n\n",
                    encoding="utf-8")
    priors = tmp_path / "p.json"
    priors.write_text('{"species": {}}', encoding="utf-8")
    demo.main(["live", "--teams", str(team), "--priors", str(priors), "--opponent", "random", "--pace", "0"])
    demo.main(["live", "--teams", str(team), "--priors-from-teams"])
    assert calls[0] == (team.read_text(encoding="utf-8").strip(), {"species": {}}, "random", 3.0, 0.0, "runs")
    assert "zapdos" in calls[1][1]["species"] and calls[1][2] == "simpleheuristics"
