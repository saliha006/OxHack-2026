"""Revelations, inference and missing evidence stay distinct in the reliable mode."""
import copy
from random import Random

import pytest

from decision.actions import Action
from decision.belief import Belief, FLOOR
from tests.test_belief import PRIORS, cand, event, turn
from tests.turn2 import EXAMPLE, REQUEST


def initial(mode='reliable', priors=PRIORS):
    battle = copy.deepcopy(EXAMPLE)
    belief = Belief(priors, battle, inference_mode=mode)
    belief.update(battle)
    return belief, battle


def items(belief, slot=2):
    return {candidate.item for candidate, _ in belief.candidates[slot]}


def skip_reasons(belief):
    return {row['reason'] for row in belief.last_diagnostics['skipped']}


@pytest.mark.parametrize('mode,expected', [('legacy', {'leftovers'}), ('reliable', {'choicescarf', 'leftovers'})])
def test_called_second_move_does_not_refute_choice(mode, expected):
    belief, battle = initial(mode)
    later = turn(battle, [event('move', 2, move='shadowball', target='p1', source='move:sleeptalk')])
    belief.update(later)
    assert items(belief) == expected
    if mode == 'reliable':
        assert 'called_or_forced_move' in skip_reasons(belief)


@pytest.mark.parametrize('completion', [None, False])
def test_midturn_or_missing_completion_does_not_refute_leftovers(completion):
    belief, battle = initial()
    later = turn(battle, [event('damage', 2, hp_percent=70, source='move')])
    later['sides']['p2']['pokemon'][2]['hp_percent'] = 70
    if completion is not None:
        later['last_turn_complete'] = completion
    belief.update(later)
    assert 'leftovers' in items(belief)
    assert 'no_completed_upkeep_observed' in skip_reasons(belief)


def test_completed_supported_upkeep_can_refute_leftovers():
    belief, battle = initial()
    later = turn(battle, [event('damage', 2, hp_percent=70, source='move')])
    later['sides']['p2']['pokemon'][2]['hp_percent'] = 70
    later['last_turn_complete'] = True
    belief.update(later)
    assert items(belief) == {'choicescarf'}
    assert belief.last_diagnostics['inferred_exclusions'] == 1


@pytest.mark.parametrize('suppression', ['magicroom', 'embargo', 'healblock', 'klutz'])
def test_leftovers_absence_under_suppression_is_not_an_exclusion(suppression):
    belief, battle = initial()
    later = turn(battle, [])
    mon = later['sides']['p2']['pokemon'][2]
    mon['hp_percent'] = 70
    later['last_turn_complete'] = True
    if suppression == 'magicroom':
        later['field']['effects']['magicroom'] = 0
    elif suppression == 'klutz':
        mon['ability'] = 'klutz'
    else:
        later['sides']['p2']['volatiles'].append(suppression)
    belief.update(later)
    assert 'leftovers' in items(belief)
    assert 'item_or_healing_suppressed' in skip_reasons(belief)


def test_choice_history_resets_at_first_item_revelation():
    belief, battle = initial()
    later = turn(battle, [event('reveal', 2, source='item:choicescarf'),
                          event('move', 2, move='shadowball', target='p1')])
    later['sides']['p2']['pokemon'][2]['item'] = 'choicescarf'
    belief.update(later)
    assert items(belief) == {'choicescarf'}
    assert not belief.last_diagnostics['recoveries']
    assert 'item_period_changed_or_first_revealed' in skip_reasons(belief)


def test_trick_interval_never_combines_moves_from_different_item_periods():
    belief, battle = initial()
    later = turn(battle, [event('move', 2, move='trick', target='p1'),
                          event('reveal', 2, source='item:choicescarf')])
    later['sides']['p2']['pokemon'][2]['item'] = 'choicescarf'
    later['sides']['p2']['pokemon'][2]['revealed_moves'].append('trick')
    belief.update(later)
    assert items(belief) == {'choicescarf'}
    assert not belief.last_diagnostics['recoveries']


def test_confirmed_current_item_has_priority_over_absence_inference():
    belief, battle = initial()
    later = turn(battle, [])
    later['sides']['p2']['pokemon'][2].update(item='leftovers', hp_percent=70)
    later['last_turn_complete'] = True
    belief.update(later)
    assert items(belief) == {'leftovers'}
    assert not belief.last_diagnostics['recoveries']


def test_removed_rocks_do_not_imply_boots():
    battle = copy.deepcopy(EXAMPLE)
    battle['sides']['p2']['hazards']['stealthrock'] = 1
    belief = Belief(PRIORS, battle, inference_mode='reliable')
    belief.update(battle)
    later = turn(battle, [event('switch', 0)], active=0)
    later['sides']['p2']['hazards']['stealthrock'] = 0
    belief.update(later)
    assert items(belief, 0) == {'leftovers', 'heavydutyboots'}
    assert 'hazard_or_item_period_not_stable' in skip_reasons(belief)


def test_possible_hazard_removal_and_reset_with_same_layer_count_is_ambiguous():
    battle = copy.deepcopy(EXAMPLE)
    battle['sides']['p2']['hazards']['stealthrock'] = 1
    belief = Belief(PRIORS, battle, inference_mode='reliable')
    belief.update(battle)
    later = turn(battle, [event('move', 2, move='defog', target='p1'), event('switch', 0)], active=0)
    belief.update(later)
    assert items(belief, 0) == {'leftovers', 'heavydutyboots'}


def test_revelations_only_has_no_inferred_exclusions_and_no_soft_replay(monkeypatch):
    belief, battle = initial('revelations')
    belief.chose(REQUEST, Action('move', 4))
    monkeypatch.setattr(belief, '_explains_turn', lambda *args: pytest.fail('revelations-only must not replay'))
    later = turn(battle, [event('move', 2, move='shadowball', target='p1')])
    later['last_turn_complete'] = True
    later['sides']['p2']['pokemon'][2]['hp_percent'] = 70
    belief.update(later)
    assert items(belief) == {'choicescarf', 'leftovers'}
    assert belief.last_diagnostics['inferred_exclusions'] == 0
    assert belief.last_diagnostics['soft']['replayed'] == 0
    assert 'revelations_only' in skip_reasons(belief)


@pytest.mark.parametrize('change', ['called', 'item', 'ability'])
def test_unsupported_soft_intervals_are_missing_evidence(monkeypatch, change):
    belief, battle = initial()
    before = copy.deepcopy(belief.candidates[2])
    belief.chose(REQUEST, Action('move', 4))
    later = turn(battle, [])
    later['last_turn_complete'] = True
    if change == 'called':
        later['last_turn'] = [event('move', 2, move='makeitrain', target='p1', source='move:metronome')]
    else:
        # An observed change on our side also makes a static native replay unsupported.
        later['sides']['p1']['pokemon'][0][change] = 'none'
    monkeypatch.setattr(belief, '_explains_turn', lambda *args: pytest.fail('unsupported interval replayed'))
    belief.update(later)
    assert belief.candidates[2] == before
    assert belief.last_diagnostics['soft'] == {'replayed': 0, 'floored': 0, 'failed': 0, 'skipped': 1}


def test_soft_floor_diagnostics_preserve_revealed_facts(monkeypatch):
    belief, battle = initial()
    belief.chose(REQUEST, Action('move', 4))
    later = turn(battle, [event('move', 2, move='makeitrain', target='p1')])
    later['last_turn_complete'] = True
    monkeypatch.setattr(belief, '_explains_turn', lambda *args: False)
    belief.update(later)
    assert FLOOR == .03
    assert belief.last_diagnostics['soft']['floored'] == 2
    assert all('makeitrain' in candidate.moves and candidate.tera_type == 'steel'
               for candidate, _ in belief.candidates[2])


def test_reliable_current_no_item_is_explicit_in_candidates_and_worlds():
    belief, battle = initial()
    later = turn(battle, [])
    later['sides']['p2']['pokemon'][2]['item'] = ''
    belief.update(later)
    assert items(belief) == {'none'}
    assert all(world[2].item == 'none' for world in belief.sample_worlds(5, Random(8)))


def test_unknown_mode_fails_explicitly():
    with pytest.raises(ValueError, match='unknown belief inference mode'):
        Belief(PRIORS, copy.deepcopy(EXAMPLE), inference_mode='invented')


@pytest.mark.parametrize('source,expected', [('ability:dancer', {'assaultvest', 'leftovers'}), (None, {'leftovers'})])
def test_external_dancer_status_move_does_not_refute_assault_vest(source, expected):
    # Dancer calls Quiver Dance externally; it does not require selecting a
    # status move through Assault Vest's ordinary move-selection restriction.
    battle = copy.deepcopy(EXAMPLE)
    battle['sides']['p2']['pokemon'][2].update(species='oricorio', revealed_moves=['revelationdance'],
                                             ability='dancer', tera_type=None, terastallized=False)
    priors = copy.deepcopy(PRIORS)
    priors['species']['oricorio'] = {'sets': [
        cand(.5, ['revelationdance', 'airslash', 'uturn', 'roost'], item=item, ability='dancer')
        for item in ['assaultvest', 'leftovers']], 'usage': {}}
    belief = Belief(priors, battle, inference_mode='reliable')
    belief.update(battle)
    later = turn(battle, [event('move', 2, move='quiverdance' if source else 'roost', target='p2', source=source)])
    belief.update(later)
    assert items(belief) == expected


@pytest.mark.parametrize('mode', ['reliable', 'revelations'])
def test_recovery_keeps_every_confirmed_fact(mode):
    belief, battle = initial(mode)
    later = turn(battle, [])
    mon = later['sides']['p2']['pokemon'][2]
    mon.update(revealed_moves=['trick', 'recover'], item='assaultvest', ability='pressure', tera_type='fire')
    belief.update(later)
    assert all(candidate.item == 'assaultvest' and candidate.ability == 'pressure' and candidate.tera_type == 'fire'
               and {'trick', 'recover'} <= set(candidate.moves) for candidate, _ in belief.candidates[2])
    assert belief.last_diagnostics['recoveries']


def test_reliable_native_replay_error_is_missing_evidence(monkeypatch):
    belief, battle = initial()
    before = copy.deepcopy(belief.candidates[2])
    belief.chose(REQUEST, Action('move', 4))
    later = turn(battle, [event('move', 2, move='makeitrain', target='p1')])
    later['last_turn_complete'] = True
    def broken(*args):
        raise ValueError('unsupported reconstruction')
    monkeypatch.setattr(belief, '_explains_turn', broken)
    belief.update(later)
    assert belief.candidates[2] == before
    assert belief.last_diagnostics['soft']['failed'] == 2
    assert belief.last_diagnostics['soft']['floored'] == 0
