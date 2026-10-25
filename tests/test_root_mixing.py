"""Selection gates and seeded behavior, independent of native MCTS randomness."""
import copy
import json
from pathlib import Path
from random import Random

import pytest

from decision.actions import Action, our_actions
from decision.root_mixing import CONFIG, mix_near_ties
from decision.search_policy import pool_results
from tests.turn2 import REQUEST


class DrawSpy:
    def __init__(self, value=.99):
        self.value, self.calls = value, 0

    def random(self):
        self.calls += 1
        return self.value


def world(index, counts=None, **extra):
    counts = counts or {'swordsdance': 510, 'kowtowcleave': 490}
    return {'index': index, 'our_visits': [{'choice': choice, 'visits': visits} for choice, visits in counts.items()], **extra}


def setup(counts=None, n=4):
    request = copy.deepcopy(REQUEST)
    worlds = [world(index, counts) for index in range(n)]
    pooled = pool_results(worlds, request)
    return request, worlds, pooled


def test_configuration_matches_the_plan_frozen_before_stochastic_tests():
    plan = json.loads((Path(__file__).parents[1] / 'evaluation/mcts-improvements/stage6-mixing-policy-plan.json').read_text())
    assert CONFIG == plan['config']
    assert plan['frozen_before_stochastic_tests_or_new_games']


def test_mature_pair_uses_exactly_one_draw_and_keeps_pooled_support_unchanged():
    request, worlds, pooled = setup()
    before = copy.deepcopy(pooled)
    spy = DrawSpy()
    action, trace = mix_near_ties(Action('move', 1), pooled, request, worlds, spy, 7)
    assert action == Action('move', 2)
    assert spy.calls == 1
    assert trace['eligible_choices'] == ['move 1', 'move 2']
    assert trace['probabilities'] == {'move 1': .51, 'move 2': .49}
    assert trace['original_choice'] == 'move 1' and trace['final_choice'] == 'move 2'
    assert trace['usable_worlds'] == 4 and trace['total_root_visits'] == 4000
    assert pooled == before


def test_mature_uniform_two_way_root_is_allowed_at_the_visit_threshold():
    request, worlds, pooled = setup({'swordsdance': 125, 'kowtowcleave': 125})
    action, trace = mix_near_ties(pooled['action'], pooled, request, worlds, Random(2), 2)
    assert action == Action('move', 2)
    assert trace['sampled'] and trace['total_root_visits'] == 1000


@pytest.mark.parametrize('counts', [{'swordsdance': 334, 'kowtowcleave': 333, 'suckerpunch': 333},
                                   {'swordsdance': 250, 'kowtowcleave': 250, 'suckerpunch': 250, 'ironhead': 250}])
def test_diffuse_uniform_three_or_four_way_support_is_not_arbitrarily_truncated(counts):
    request, worlds, pooled = setup(counts)
    spy = DrawSpy()
    action, trace = mix_near_ties(pooled['action'], pooled, request, worlds, spy, 7)
    assert action == pooled['action']
    assert trace['reason'] == 'diffuse_root' and spy.calls == 0


@pytest.mark.parametrize('n,counts,reason', [(3, None, 'insufficient_usable_worlds'),
                                           (4, {'swordsdance': 25, 'kowtowcleave': 25}, 'insufficient_root_visits')])
def test_few_worlds_or_noisy_low_visit_roots_do_not_sample(n, counts, reason):
    request, worlds, pooled = setup(counts, n)
    spy = DrawSpy()
    action, trace = mix_near_ties(pooled['action'], pooled, request, worlds, spy, 8)
    assert action == pooled['action'] and trace['reason'] == reason
    assert spy.calls == 0


def test_request_order_and_separate_seeded_random_instances_are_repeatable():
    request, worlds, pooled = setup()
    rng_a, rng_b, native_sampler = Random(29), Random(29), Random(2026)
    untouched = native_sampler.getstate()
    choices_a = [mix_near_ties(pooled['action'], pooled, request, worlds, rng_a, 29)[0] for _ in range(20)]
    choices_b = [mix_near_ties(pooled['action'], pooled, request, worlds, rng_b, 29)[0] for _ in range(20)]
    assert choices_a == choices_b and len(set(choices_a)) == 2
    assert native_sampler.getstate() == untouched


def test_original_tera_and_switch_choices_stay_deterministic():
    request, worlds, pooled = setup()
    for original in [Action('move', 1, True), Action('switch', 2)]:
        spy = DrawSpy()
        action, trace = mix_near_ties(original, pooled, request, worlds, spy, 2)
        assert action == original and not trace['sampled'] and spy.calls == 0


def test_tera_alternative_is_never_silently_promoted():
    request, worlds, pooled = setup({'swordsdance': 500, 'swordsdance-tera': 500})
    spy = DrawSpy()
    action, trace = mix_near_ties(Action('move', 1), pooled, request, worlds, spy, 2)
    assert action == Action('move', 1) and not action.tera and not trace['sampled']
    assert spy.calls == 0


def test_disabled_alternative_or_any_mapping_failure_preserves_the_legal_choice():
    request, worlds, _ = setup()
    request['active'][0]['moves'][1]['disabled'] = True
    pooled = pool_results(worlds, request)
    spy = DrawSpy()
    action, trace = mix_near_ties(pooled['action'], pooled, request, worlds, spy, 2)
    assert action in our_actions(request) and action == pooled['action']
    assert trace['reason'] == 'pooled_mapping_failures' and spy.calls == 0


def test_vetoed_alternative_preserves_original_and_does_not_advance_rng():
    request, worlds, pooled = setup()
    spy = DrawSpy()
    action, trace = mix_near_ties(pooled['action'], pooled, request, worlds, spy, 2, excluded={Action('move', 2)})
    assert action == pooled['action'] and not trace['sampled'] and spy.calls == 0


def test_successful_worlds_are_retained_when_other_worlds_failed_or_returned_zero_visits():
    request, worlds, _ = setup()
    worlds += [world(4, error={'type': 'deadline'}), {'index': 5, 'our_visits': []}]
    pooled = pool_results(worlds, request)
    action, trace = mix_near_ties(pooled['action'], pooled, request, worlds, Random(2), 2)
    assert action in our_actions(request) and trace['sampled']
    assert trace['usable_worlds'] == 4 and trace['total_root_visits'] == 4000
    assert len(trace['ignored_worlds']) == 2


def test_maturity_counts_worlds_equally_even_when_two_trees_have_many_more_iterations():
    request = copy.deepcopy(REQUEST)
    def build(scale):
        # The root winner has >5% share in only two of six worlds. The four
        # other worlds' small 4% shares do not make this a mature cross-world choice.
        worlds = [world(n, {'swordsdance': 1 * scale, 'kowtowcleave': 999 * scale}) for n in range(2)]
        worlds += [world(n, {'swordsdance': 510, 'kowtowcleave': 40, 'swordsdance-tera': 450}) for n in range(2, 6)]
        return worlds, pool_results(worlds, request)
    for scale in [1, 1000]:
        worlds, pooled = build(scale)
        spy = DrawSpy()
        action, trace = mix_near_ties(pooled['action'], pooled, request, worlds, spy, 3)
        assert action == pooled['action'] == Action('move', 2)
        assert trace['reason'] == 'insufficient_world_support' and spy.calls == 0
        assert next(row['supporting_worlds'] for row in trace['support_maturity'] if row['choice'] == 'move 2') == 2
        assert trace['required_supporting_worlds'] == 3


def test_combined_mass_and_relative_closeness_are_independent_gates():
    for counts, reason in [({'swordsdance': 320, 'kowtowcleave': 310, 'suckerpunch': 190, 'ironhead': 180},
                            'insufficient_combined_mass'),
                           ({'swordsdance': 280, 'kowtowcleave': 250, 'suckerpunch': 240, 'ironhead': 230},
                            'not_exactly_two_supported_moves')]:
        request, worlds, pooled = setup(counts)
        spy = DrawSpy()
        action, trace = mix_near_ties(pooled['action'], pooled, request, worlds, spy, 3)
        assert action == pooled['action'] and trace['reason'] == reason and spy.calls == 0


def test_absolute_decimal_gap_boundary_is_inclusive():
    request, worlds, pooled = setup({'swordsdance': 500, 'kowtowcleave': 470, 'swordsdance-tera': 30})
    action, trace = mix_near_ties(pooled['action'], pooled, request, worlds, Random(2), 2)
    assert trace['sampled'] and action == Action('move', 2)


def test_explicit_fallback_does_not_sample_even_with_otherwise_mature_support():
    request, worlds, pooled = setup()
    pooled['fallback_reason'] = 'worker_failure'
    spy = DrawSpy()
    action, trace = mix_near_ties(pooled['action'], pooled, request, worlds, spy, 3)
    assert action == pooled['action'] and trace['reason'] == 'deterministic_fallback' and spy.calls == 0


def test_derived_unsupported_native_choice_does_not_trust_a_missing_pooled_error_record():
    request, worlds, pooled = setup()
    worlds[0]['our_visits'].append({'choice': 'not-a-real-move', 'visits': 10})
    spy = DrawSpy()
    action, trace = mix_near_ties(pooled['action'], pooled, request, worlds, spy, 3)
    assert action == pooled['action'] and trace['reason'] == 'native_mapping_failures' and spy.calls == 0
