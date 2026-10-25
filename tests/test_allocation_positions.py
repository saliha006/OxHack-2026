"""Compute diagnostics count worlds/games correctly rather than root-visit totals."""
from types import SimpleNamespace

from evaluation.allocation_positions import percentile, root_metrics, summarize


def test_world_disagreement_does_not_weight_the_larger_native_tree_more():
    trace = {'search_support': {'move 1': .5, 'move 2': .5}, 'worlds': [
        {'index': 0, 'counts': {'move 1': 90, 'move 2': 10}},
        {'index': 1, 'counts': {'move 1': 1, 'move 2': 9}},
        {'index': 2, 'error': 'failed native search'}]}
    def pool(worlds, request):
        world = worlds[0]
        if world.get('error'):
            return {'action': None}
        total = sum(world['counts'].values())
        winner = max(world['counts'], key=world['counts'].get)
        return {'action': SimpleNamespace(to_choice=lambda: winner),
                'search_support': {key: value / total for key, value in world['counts'].items()}}
    result = root_metrics(trace, {}, pool)
    assert result['world_winner_disagreement'] == .5
    assert result['pooled_top_two_margin'] == 0
    assert result['world_winner_counts'] == {'move 1': 1, 'move 2': 1}
    assert all(sum(row['support'].values()) == 1 for row in result['per_world_normalised_support'])


def test_failed_scheduled_calls_are_retained_in_summary():
    summary = {'choice': 'move 1', 'choice_legal': True, 'latency_ms': 1200,
               'native_elapsed_ms': 1100, 'preparation_ms': 10, 'cpu_ms': 1000,
               'visits': 20, 'completed_worlds': 4, 'usable_worlds': 4,
               'failed_worlds': 0, 'world_winner_disagreement': 0, 'pooled_top_two_margin': 1,
               'fallback_reason': None}
    rows = [{'allocation': '4x300', 'position': 'p', 'result': {'summary': summary}},
            {'allocation': '4x300', 'position': 'p', 'error': {'message': 'worker failed'}}]
    plan = {'purpose': 'test', 'schedule': [1, 2], 'source': {'source_sha256': 'source'},
            'engine': {}, 'priors_sha256': 'prior', 'cpu_scope': 'test'}
    result = summarize(rows, plan)
    assert result['recorded_calls'] == 2
    assert result['allocations']['4x300']['worker_errors'] == 1
    assert result['allocations']['4x300']['statistics']['latency_ms']['n'] == 1


def test_empty_or_single_measurement_quantiles_are_defined():
    assert percentile([], .95) is None
    assert percentile([5], .99) == 5
