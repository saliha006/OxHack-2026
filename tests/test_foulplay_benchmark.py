from collections import Counter, defaultdict

import pytest

from evaluation.foulplay_benchmark import schedule, summarize


def test_fixed_schedule_balances_every_matchup_and_side_without_outcome_stopping():
    games = schedule(400, list(range(14)), 42)
    assert len(games) == 400
    assert {g['game'] for g in games} == set(range(400))
    assert Counter(g['side'] for g in games) == {'p1': 200, 'p2': 200}
    pairs = defaultdict(list)
    for game in games:
        pairs[game['pair']].append(game)
    assert len(pairs) == 200
    for pair in pairs.values():
        assert {g['side'] for g in pair} == {'p1', 'p2'}
        assert len({g['opponent_team'] for g in pair}) == 1
    counts = Counter(g['opponent_team'] for g in games)
    assert len(counts) == 14 and max(counts.values())-min(counts.values()) == 2
    assert games == schedule(400, list(range(14)), 42)


@pytest.mark.parametrize('count,teams', [(0, [1]), (3, [1]), (400, [])])
def test_invalid_schedule_is_rejected(count, teams):
    with pytest.raises(ValueError):
        schedule(count, teams, 42)


def test_draws_and_errors_are_visible_and_do_not_become_wins():
    rows = [{'completion_verified': True, 'winner': winner, 'side': side,
             'opponent_team': i % 2, 'metrics': {'fallbacks': i, 'rejected_choices': 0}}
            for i, (winner, side) in enumerate([('a', 'p1'), ('b', 'p2'), ('tie', 'p1')])]
    rows.append({'error': 'external process failed'})
    result = summarize(rows, 400)
    assert result['completed'] == 3 and result['errors'] == 1
    assert result['wins'] == result['losses'] == result['ties'] == 1
    assert result['win_rate'] == 1 / 3 and result['score_rate'] == .5
    assert result['status'] == 'incomplete'
    assert result['fallbacks'] == 3
    assert result['win_wilson_95'][0] < 1 / 3 < result['win_wilson_95'][1]
    assert result['opponent_team_bootstrap_score_95'] is not None


def test_completed_plan_and_empty_run_are_distinct():
    assert summarize([], 400)['status'] == 'incomplete'
    assert summarize([], 400)['win_rate'] is None
    row = {'completion_verified': True, 'winner': 'a', 'side': 'p1', 'opponent_team': 0}
    assert summarize([row], 1)['status'] == 'complete'


def test_live_player_does_not_import_a_trailing_blank_as_a_seventh_pokemon(tmp_path, monkeypatch):
    from pathlib import Path
    from poke_env.teambuilder import Teambuilder
    import bot.player
    import evaluation.foulplay_benchmark as benchmark

    team = Path('bot/teams/standin/team_6.txt').read_text().strip() + '\n\n'
    own = tmp_path / 'own.txt'
    own.write_text(team)
    monkeypatch.setattr(benchmark, 'verify', lambda manifest: None)

    class Captured(Exception):
        pass

    def capture_player(**kwargs):
        assert len(Teambuilder.parse_showdown_team(kwargs['team'])) == 6
        assert own.read_text() == team
        raise Captured

    monkeypatch.setattr(bot.player, 'AgentPlayer', capture_player)
    with pytest.raises(Captured):
        benchmark.game({'folder': str(tmp_path), 'port': 8127, 'config': {},
                        'own_team': {'path': str(own)}},
                       {'game': 0, 'sampler_seed': 42})
