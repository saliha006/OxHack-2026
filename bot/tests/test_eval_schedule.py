"""Matched MCTS schedules cover a reserved team pool before repeating teams."""
import random

import pytest

from bot import eval as harness


@pytest.mark.parametrize('count', [1, 3, 4, 7])
@pytest.mark.parametrize('seed', [0, 17, 2026])
def test_mcts_balanced_pairs_cover_each_pool_once_per_shuffled_block(count, seed):
    pairing = next(iter(harness.MCTS_PAIRINGS))
    for block in range(3):
        start = 2 * count * block
        teams = [harness.team_index(seed, pairing, g, count) for g in range(start, start + 2 * count)]
        assert set(teams) == set(range(count))
        assert teams[::2] == teams[1::2]
        assert sorted(teams[::2]) == list(range(count))


def test_all_mcts_comparisons_share_team_schedule_including_external_opponents():
    expected = None
    for pairing in harness.MCTS_PAIRINGS:
        actual = [harness.team_index(2026, pairing, g, 4) for g in range(24)]
        if expected is None:
            expected = actual
        assert actual == expected


def test_schedule_is_reproducible_when_queried_out_of_order_or_resharded():
    pairing = next(iter(harness.MCTS_PAIRINGS))
    games = list(range(30))
    expected = {g: harness.team_index(2026, pairing, g, 4) for g in games}
    random.Random(7).shuffle(games)
    assert {g: harness.team_index(2026, pairing, g, 4) for g in games} == expected


def test_legacy_pairings_preserve_original_seeded_sampling_with_replacement():
    pairing = next(name for name in harness.PAIRINGS if name not in harness.MCTS_PAIRINGS)
    for g in range(20):
        assert harness.team_index(2026, pairing, g, 4) == harness.game_rng(2026, pairing, g).randrange(4)
