from pathlib import Path

import pytest

from bot import smoke
from contracts.set_candidates import SetCandidates

TEAM = (Path(__file__).parent.parent / "teams" / "standin-gen9ou.txt").read_text(encoding="utf-8")


def test_priors_from_one_team_give_each_species_its_exact_set():
    priors: SetCandidates = smoke.priors_from_teams([TEAM])
    assert list(priors["species"]) == ["zapdos", "hydrapple", "zamazenta", "slowkinggalar", "tinkaton", "tinglu"]
    zapdos = priors["species"]["zapdos"]
    assert zapdos["sets"] == [{"weight": 1.0, "moves": ["hurricane", "weatherball", "voltswitch", "roost"],
                               "item": "heavydutyboots", "ability": "static", "tera_type": "grass",
                               "spread": {"nature": "timid", "evs": [248, 0, 76, 0, 0, 184]}}]
    assert zapdos["usage"]["moves"] == {"hurricane": 1.0, "weatherball": 1.0, "voltswitch": 1.0, "roost": 1.0}


def game(won=True, decisions=40, fallbacks=0):
    return {"tag": "battle-gen9ou-1", "won": won, "turns": 30, "decisions": decisions, "fallbacks": fallbacks,
            "think_p50_ms": 60.0, "think_p99_ms": 400.0}


@pytest.mark.parametrize("games, summaries, code", [
    (2, [game(), game(won=False, fallbacks=2)], 0),   # 2 of 80 decisions = 2.5%
    (2, [game(), game(fallbacks=5)], 1),               # 5 of 80 = 6.25%, over 5%
    (2, [game()], 1),                                  # a game never finished
    (1, [], 1),                                        # nothing finished: no decisions at all
])
def test_main_passes_only_when_every_game_finishes_under_the_fallback_limit(monkeypatch, capsys, games, summaries, code):
    calls = []
    monkeypatch.setattr(smoke, "run", lambda *args: calls.append(args) or summaries)
    assert smoke.main(["--games", str(games)]) == code
    assert calls[0][0] == games and "kingambit" in calls[0][2]["species"]
    assert calls[0][5:] == ("mcts", 8, 150, 1)
    assert f"{len(summaries)}/{games} games finished" in capsys.readouterr().out


def test_main_can_build_priors_from_the_team(monkeypatch):
    calls = []
    monkeypatch.setattr(smoke, "run", lambda *args: calls.append(args) or [game()])
    assert smoke.main(["--games", "1", "--priors-from-team", "--budget", "1.0"]) == 0
    assert "zapdos" in calls[0][2]["species"] and calls[0][3] == 1.0


def test_priors_from_several_teams_weigh_each_set_by_how_often_it_appears():
    other_zapdos = TEAM.replace("- Roost", "- Discharge", 1)
    priors = smoke.priors_from_teams([TEAM, TEAM, other_zapdos])
    zapdos = priors["species"]["zapdos"]
    assert [round(s["weight"], 3) for s in zapdos["sets"]] == [0.667, 0.333]
    assert zapdos["sets"][1]["moves"] == ["hurricane", "weatherball", "voltswitch", "discharge"]
    assert round(zapdos["usage"]["moves"]["roost"], 3) == 0.667 and zapdos["usage"]["moves"]["hurricane"] == 1.0
    assert priors["species"]["tinglu"]["sets"][0]["weight"] == 1.0
