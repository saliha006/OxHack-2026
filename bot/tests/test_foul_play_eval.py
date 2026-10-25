"""External opponent integration: process arguments, balanced challenges and honest search telemetry."""
import asyncio
import random
from pathlib import Path
from types import SimpleNamespace

import pytest

from bot import eval as harness


def test_foul_play_world_log_deduplicates_child_and_parent_iterations(tmp_path):
    path = tmp_path / 'fp.log'
    path.write_text('INFO Sampling 2 battles at 150ms each\nINFO Iterations 0: 1200\n'
                    'INFO Iterations 1: 800\nINFO Iterations 0: 1200\nINFO Iterations 1: 800\n'
                    'INFO Sampling 1 battles at 150ms each\nINFO Iterations 0: 900\n')
    searches = harness.foul_play_search_log(path)
    assert [(s['requested_worlds'], s['completed_worlds'], s['total_visits']) for s in searches] == [
        (2, 2, 2000), (1, 1, 900)]
    assert all(s['search_ms_per_world'] == 150 for s in searches)
    assert not any('actual_search_ms' in search for search in searches)


def test_foul_play_revision_reads_loose_and_packed_refs(tmp_path):
    git = tmp_path / '.git'
    git.mkdir()
    revision = 'a' * 40
    (git / 'HEAD').write_text('ref: refs/heads/main\n')
    (git / 'packed-refs').write_text(f'{revision} refs/heads/main\n')
    assert harness.repository_revision(tmp_path) == revision
    (git / 'HEAD').write_text(revision)
    assert harness.repository_revision(tmp_path) == revision


def test_foul_play_challenger_has_explicit_engine_settings(tmp_path, monkeypatch):
    seen = []
    class Process:
        def __init__(self, args, **kwargs):
            seen.append(args)
        def terminate(self):
            pass
    monkeypatch.setattr(harness.subprocess, 'Popen', Process)
    fp = harness.FoulPlay(150, [tmp_path / 't.txt'], tmp_path, 'oxfp', challenge_user='oxagent')
    args = seen[0]
    assert args[args.index('--bot-mode') + 1] == 'challenge_user'
    assert args[args.index('--user-to-challenge') + 1] == 'oxagent'
    assert args[args.index('--search-threads') + 1] == '1'
    assert args[args.index('--search-parallelism') + 1] == '1'
    fp.close()


def test_foul_play_game_detects_process_failure(tmp_path):
    class Player:
        async def accept_challenges(self, *args):
            await asyncio.sleep(100)
    fp = SimpleNamespace(username='oxfp', log=tmp_path / 'fp.log', process=SimpleNamespace(poll=lambda: 1))
    with pytest.raises(RuntimeError, match='exited during game'):
        asyncio.run(harness._foul_game(Player(), fp, accepting=True))


def test_mcts_foul_play_pair_swaps_challenger_and_retains_same_compute(tmp_path, monkeypatch):
    started, challenged = [], []
    class Foul:
        def __init__(self, ms, paths, runs, username, *, challenge_user=None, parallelism=1):
            self.search_ms, self.username, self.challenge_user = ms, username, challenge_user
            self.process = SimpleNamespace(poll=lambda: None)
            self.log = runs / f'{username}.log'
            self.log.write_text('INFO Sampling 2 battles at 150ms each\nINFO Iterations 0: 1000\n')
            self.ready, self.closed = False, False
            started.append(self)
        def wait_ready(self):
            self.ready = True
        def close(self):
            self.closed = True
    class Player:
        username = 'oxagent'
        def __init__(self):
            self.battles, self.summaries = {}, []
        def update_team(self, team):
            self.team = team
        async def send_challenges(self, name, n):
            self.record(name, 'p1')
        async def accept_challenges(self, name, n):
            self.record(name, 'p2')
        def record(self, name, side):
            challenged.append((name, side))
            self.battles[len(self.battles)] = SimpleNamespace(turn=10, won=True, finished=True, player_role=side,
                                                             battle_tag=f'battle-{len(self.battles)}')
            self.summaries.append({'tag': f'battle-{len(self.battles)-1}', 'decisions': 10, 'fallbacks': 0})
    monkeypatch.setattr(harness, 'FoulPlay', Foul)
    monkeypatch.setattr(harness, 'AgentPlayer', Player)
    a = Player()
    players = {('a', 'mcts8'): a}
    rows = [harness.play_game('mcts-foulplay', g, players, ['TEAM0', 'TEAM1'], {}, 3,
                             str(tmp_path), random.Random(g), 42) for g in (0, 1)]
    assert [side for _, side in challenged] == ['p1', 'p2']
    assert rows[0]['team'] == rows[1]['team']
    assert started[0].search_ms == started[1].search_ms
    assert started[0].challenge_user is None and started[1].challenge_user == a.username
    assert started[0].ready and not started[1].ready
    assert all(fp.closed for fp in started)
    assert all(row['balanced_sides'] for row in rows)
    assert all(row['compute']['b']['compute_matched'] is False for row in rows)
    assert all(row['foul_play_searches'][0]['completed_worlds'] == 1 for row in rows)
