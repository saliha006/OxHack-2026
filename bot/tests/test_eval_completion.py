"""Battle identity/terminal-state gates must supersede poke-env's challenge semaphores."""
import asyncio
import random
from types import SimpleNamespace

import pytest

from bot import eval as harness


class Player:
    def __init__(self):
        self.battles = {'old': SimpleNamespace(battle_tag='old', finished=True, turn=50)}
        self.summaries = [{'tag': 'old', 'decisions': 50}]

    def update_team(self, team):
        self.team = team

    async def battle_against(self, other, n_battles):
        # Model poke-env returning at team preview due an old send/accept semaphore token.
        a, b = self, other
        battle = SimpleNamespace(battle_tag='new', finished=False, turn=0, won=None, player_role='p1')
        a.battles['new'] = b.battles['new'] = battle
        loop = asyncio.get_running_loop()
        def finish():
            battle.finished, battle.turn, battle.won = True, 20, True
        def summaries():
            for player in (a, b):
                player.summaries.append({'tag': 'new', 'decisions': 21, 'fallbacks': 0})
        loop.call_later(0.02, finish)
        loop.call_later(0.04, summaries)
        return  # the battle has not finished and its matching summary does not yet exist


def test_play_game_waits_for_new_finished_battle_and_matching_summary(tmp_path, monkeypatch):
    monkeypatch.setattr(harness, 'AgentPlayer', Player)
    a, b = Player(), Player()
    players = {('a', 'mcts1'): a, ('b', 'full'): b}
    row = harness.play_game('mcts-current', 0, players, ['TEAM'], {}, 3, str(tmp_path), random.Random(0), 0)
    assert row['battle'] == 'new' and row['turns'] == 20 and row['winner'] == 'a'
    assert row['decisions'] == 21
    assert row['opponent_metrics']['tag'] == 'new'


def test_completion_waits_for_battle_creation_after_dispatch_returns(monkeypatch):
    monkeypatch.setattr(harness, 'AgentPlayer', Player)
    player = Player()
    async def dispatch():
        loop = asyncio.get_running_loop()
        def create():
            player.battles['new'] = SimpleNamespace(battle_tag='new', finished=True)
            player.summaries.append({'tag': 'new', 'decisions': 3})
        loop.call_later(0.02, create)
    done = asyncio.run(harness._finished_game(dispatch(), [(player, {'old'})], timeout=1))
    assert done[0][0].battle_tag == 'new' and done[0][1]['decisions'] == 3


def test_more_than_one_new_battle_is_an_overlap_error(monkeypatch):
    monkeypatch.setattr(harness, 'AgentPlayer', Player)
    player = Player()
    async def dispatch():
        player.battles.update({tag: SimpleNamespace(battle_tag=tag, finished=True) for tag in ('new1', 'new2')})
    with pytest.raises(RuntimeError, match='overlap'):
        asyncio.run(harness._finished_game(dispatch(), [(player, {'old'})], timeout=1))


def test_unfinished_previous_battle_cannot_schedule_another_game():
    player = Player()
    player.battles['old'].finished = False
    with pytest.raises(RuntimeError, match='previous battle'):
        harness._battle_snapshot(player)


def test_missing_new_battle_times_out_instead_of_reporting_old_result():
    player = Player()
    async def dispatch():
        pass
    with pytest.raises(TimeoutError, match='did not complete'):
        asyncio.run(harness._finished_game(dispatch(), [(player, {'old'})], timeout=0))
