"""Regression fixtures for revelation-safe recovery and complete-team posterior draws."""
import copy
import json
import math
import random
from pathlib import Path

import pytest

from decision.belief import Belief, _normalised, _rebuild
from decision.sets import PokemonSet
from decision.state import DEX
from tests.test_belief import PRIORS, cand, event, turn
from tests.turn2 import EXAMPLE, REQUEST


def mon(battle, slot=2):
    return battle['sides']['p2']['pokemon'][slot]


def test_missing_species_recovers_known_facts_without_a_lookup_failure():
    battle = copy.deepcopy(EXAMPLE)
    mon(battle).update(species='urshifu', revealed_moves=['wickedblow'], ability='unseenfist',
                       item='choicescarf', tera_type='dark')
    belief = Belief(PRIORS, battle)
    belief.update(battle)
    assert belief.recovery_events[0]['reason'] == 'missing_species_prior'
    assert all(s.item == 'choicescarf' and s.ability == 'unseenfist' and s.tera_type == 'dark'
               and 'wickedblow' in s.moves for s, _ in belief.candidates[2])
    assert len(belief.sample_worlds(1, random.Random(1))[0]) == 6


def test_battle_only_forme_resolves_to_its_parent_prior():
    battle = copy.deepcopy(EXAMPLE)
    mon(battle, 0).update(species='keldeoresolute', revealed_moves=[], ability=None, item=None,
                          tera_type=None)
    priors = copy.deepcopy(PRIORS)
    priors['species']['keldeo'] = priors['species'].pop('dragonite')
    belief = Belief(priors, battle)
    assert belief.candidates[0][0][0].item == 'heavydutyboots'
    assert belief.recovery_events[0] == {'turn': 2, 'slot': 0, 'species': 'keldeoresolute',
                                          'reason': 'forme_prior_alias', 'prior_species': 'keldeo'}


def test_regional_forme_does_not_borrow_another_types_prior():
    battle = copy.deepcopy(EXAMPLE)
    mon(battle, 0).update(species='slowkinggalar', revealed_moves=[], ability=None, item=None, tera_type=None)
    priors = copy.deepcopy(PRIORS)
    priors['species']['slowking'] = priors['species'].pop('dragonite')
    belief = Belief(priors, battle)
    assert belief.recovery_events[0]['reason'] == 'missing_species_prior'
    assert belief.candidates[0][0][0].ability == 'curiousmedicine'


def test_recovery_never_restores_candidates_contradicting_revelations():
    battle = copy.deepcopy(EXAMPLE)
    belief = Belief(PRIORS, battle)
    mon(battle).update(revealed_moves=['trick', 'recover'], item='assaultvest', ability='pressure', tera_type='fire')
    # This explicitly inconsistent observation cannot be repaired by resurrecting the old Scarf/Steel guesses.
    belief.update(battle)
    assert belief.recovery_events[-1]['reason'] == 'reconstructed_revealed_facts'
    assert all(s.item == 'assaultvest' and s.ability == 'pressure' and s.tera_type == 'fire'
               and {'trick', 'recover'} <= set(s.moves) for s, _ in belief.candidates[2])


def test_choice_scarf_trick_is_retained_in_usage_rebuild():
    battle = copy.deepcopy(EXAMPLE)
    mon(battle).update(revealed_moves=['trick'], item='choicescarf')
    assert _rebuild(PRIORS['species']['gholdengo']['usage'], mon(battle))
    assert all(s.item == 'choicescarf' and 'trick' in s.moves
               for s, _ in _rebuild(PRIORS['species']['gholdengo']['usage'], mon(battle)))


def test_empty_usage_and_zero_candidate_weights_still_produce_a_distribution():
    battle = copy.deepcopy(EXAMPLE)
    priors = copy.deepcopy(PRIORS)
    priors['species']['gholdengo'] = {'sets': [], 'usage': {}}
    belief = Belief(priors, battle)
    belief.update(battle)
    assert belief.candidates[2]
    assert math.isclose(sum(w for _, w in belief.candidates[2]), 1)
    candidate = belief.candidates[2][0][0]
    assert _normalised([(candidate, 0)]) == [(candidate, 1.0)]
    assert _normalised([]) == []
    assert _normalised([(candidate, math.nan), (candidate, -1)]) == []


def test_sampling_draws_all_slots_with_reproducible_frequencies_and_no_mutation():
    battle = copy.deepcopy(EXAMPLE)
    belief = Belief(PRIORS, battle)
    belief.update(battle)
    before = copy.deepcopy(belief.candidates)
    draws = belief.sample_worlds(5000, random.Random(17))
    assert draws == belief.sample_worlds(5000, random.Random(17))
    assert before == belief.candidates
    assert all(len(world) == 6 for world in draws)
    boots = sum(world[0].item == 'heavydutyboots' for world in draws) / len(draws)
    scarf = sum(world[2].item == 'choicescarf' for world in draws) / len(draws)
    assert boots == pytest.approx(.6, abs=.025)
    assert scarf == pytest.approx(.5 / .7, abs=.025)
    assert len({(world[0].item, world[2].item) for world in draws}) == 4
    assert [entry['species'] for entry in belief.last_sampled_worlds[0]] == list(belief.preview_species)
    assert all('makeitrain' in world[2].moves and world[2].tera_type == 'steel' for world in draws)


def test_sample_overlay_preserves_known_current_no_item_and_all_revelations():
    battle = copy.deepcopy(EXAMPLE)
    mon(battle).update(item='', ability='goodasgold', tera_type='steel')
    belief = Belief(PRIORS, battle)
    belief.update(battle)
    draws = belief.sample_worlds(10, random.Random(12))
    assert all(world[2].item == 'none' and world[2].ability == 'goodasgold' for world in draws)


def test_active_only_ablation_freezes_bench_but_samples_active():
    belief = Belief(PRIORS, copy.deepcopy(EXAMPLE))
    belief.update(copy.deepcopy(EXAMPLE))
    draws = belief.sample_worlds(200, random.Random(1), active_only=True)
    assert {world[0].item for world in draws} == {'heavydutyboots'}
    assert {world[2].item for world in draws} == {'choicescarf', 'leftovers'}
    assert belief.sample_worlds(0, random.Random(1)) == []


def test_preview_scenarios_do_not_index_a_missing_active():
    battle = copy.deepcopy(EXAMPLE)
    battle['sides']['p2']['active'] = None
    belief = Belief(PRIORS, battle)
    assert len(belief.scenarios()) == 1
    assert belief.scenarios(k=0) == []


def test_real_ou_priors_are_normalised_and_use_known_species_and_moves():
    from decision.opponent import MOVES
    priors = json.loads((Path(__file__).parents[1] / 'data/set_candidates.json').read_text())
    assert priors['source'] == {'format': 'gen9ou', 'month': '2026-09', 'cutoff': 1825, 'battles': 574541}
    assert len(priors['species']) == 321
    for species, entry in priors['species'].items():
        assert species in DEX
        assert entry['sets']
        assert sum(candidate['weight'] for candidate in entry['sets']) == pytest.approx(1)
        for candidate in entry['sets']:
            assert candidate['weight'] >= 0
            assert 1 <= len(candidate['moves']) <= 4
            assert set(candidate['moves']) <= MOVES.keys()


def test_empty_damage_results_are_missing_evidence(monkeypatch):
    from decision.actions import Action
    import decision.belief as module
    battle = copy.deepcopy(EXAMPLE)
    belief = Belief(PRIORS, battle)
    belief.update(battle)
    before = copy.deepcopy(belief.candidates[2])
    belief.chose(REQUEST, Action('move', 4))
    monkeypatch.setattr(module, 'calculate_damage', lambda *args: ([], []))
    belief.update(turn(battle, [event('move', 2, move='makeitrain', target='p1'),
                                {**event('damage', 5, hp_percent=1, source='move'), 'side': 'p1'}]))
    assert belief.candidates[2] == before


def test_replay_failure_is_recorded_without_changing_weights(monkeypatch):
    from decision.actions import Action
    battle = copy.deepcopy(EXAMPLE)
    belief = Belief(PRIORS, battle)
    belief.update(battle)
    before = copy.deepcopy(belief.candidates[2])
    belief.chose(REQUEST, Action('move', 4))
    def broken(*args):
        raise ValueError('imperfect engine evidence')
    monkeypatch.setattr(belief, '_explains_turn', broken)
    belief.update(turn(battle, []))
    assert belief.candidates[2] == before
    assert belief.recovery_events[-1]['reason'] == 'evidence_replay_failed'


def test_soft_floor_cannot_restore_a_revelation_contradiction(monkeypatch):
    from decision.actions import Action
    battle = copy.deepcopy(EXAMPLE)
    belief = Belief(PRIORS, battle)
    belief.update(battle)
    belief.chose(REQUEST, Action('move', 4))
    monkeypatch.setattr(belief, '_explains_turn', lambda *args: False)
    later = turn(battle, [])
    mon(later).update(item='leftovers')
    belief.update(later)
    assert {s.item for s, _ in belief.candidates[2]} == {'leftovers'}
    assert sum(w for _, w in belief.candidates[2]) == pytest.approx(1)


def test_candidate_records_export_exact_weights_and_detached_set_details():
    belief = Belief(PRIORS, copy.deepcopy(EXAMPLE))
    belief.update(copy.deepcopy(EXAMPLE))
    records = belief.candidate_records()
    assert len(records) == len(belief.candidates) == 6
    assert [row['species'] for row in records] == [mon['species'] for mon in belief.previous['pokemon']]
    assert [row['weight'] for row in records[2]['sets']] == [weight for _, weight in belief.candidates[2]]
    for record, candidates in zip(records, belief.candidates):
        assert sum(row['weight'] for row in record['sets']) == pytest.approx(1)
        assert {PokemonSet(**{k: v for k, v in row.items() if k != 'weight'}) for row in record['sets']} == {
            candidate for candidate, _ in candidates}
    records[2]['sets'][0]['item'] = 'corrupted copy'
    assert belief.candidates[2][0][0].item != 'corrupted copy'
