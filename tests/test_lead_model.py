"""Mechanism tests for the optional preview model; no playing-strength claim."""
import copy
import json
import math

import pytest

from bot.parser import new_pokemon
from decision.actions import Action
from decision.lead import pick_lead
from decision.lead_model import _damage, _opponent_models, _own_model, pick_lead_model
from tests.test_belief import cand
from tests.test_lead import PREVIEW


def own(species='Azelf', moves=('psychic',), **changes):
    mon = copy.deepcopy(PREVIEW['side']['pokemon'][0])
    mon.update(details=species + ', L100', ident='p1: ' + species, condition='300/300',
               moves=list(moves), item='', ability='levitate')
    mon['stats'] = {'atk': 250, 'def': 200, 'spa': 250, 'spd': 200, 'spe': 300}
    mon.update(changes)
    return mon


def matchup(ours, foe='toxapex', moves=('surf', 'recover'), ability='regenerator', item='leftovers'):
    request = {'teamPreview': True, 'side': {'pokemon': ours}}
    battle = {'us': 'p1', 'sides': {'p2': {'pokemon': [new_pokemon(foe, True)]}}}
    priors = {'species': {foe: {'sets': [cand(1.0, list(moves), item=item, ability=ability)], 'usage': {}}}}
    return request, battle, priors


def test_actual_moves_can_change_a_lead_between_identical_types():
    request, battle, priors = matchup([own('Gholdengo', ('tackle',)), own('Gholdengo', ('shadowball',))],
                                     foe='gengar', moves=('shadowball',), ability='cursedbody')
    assert pick_lead(request, battle) == Action('lead', 1)
    assert pick_lead_model(request, battle, priors)[0] == Action('lead', 2)
    request['side']['pokemon'][0]['moves'], request['side']['pokemon'][1]['moves'] = (
        request['side']['pokemon'][1]['moves'], request['side']['pokemon'][0]['moves'])
    assert pick_lead_model(request, battle, priors)[0] == Action('lead', 1)


def test_exact_supplied_special_attack_changes_the_choice():
    mons = [own('Gholdengo', ('shadowball',)), own('Gholdengo', ('shadowball',))]
    mons[0]['stats']['spa'], mons[1]['stats']['spa'] = 80, 400
    request, battle, priors = matchup(mons)
    assert pick_lead_model(request, battle, priors)[0] == Action('lead', 2)
    mons[0]['stats']['spa'], mons[1]['stats']['spa'] = 500, 80
    assert pick_lead_model(request, battle, priors)[0] == Action('lead', 1)


def test_priority_prices_the_risk_of_fainting_before_attacking():
    mons = [own('Dragonite', ('dragonclaw',), condition='100/100', ability='innerfocus'),
            own('Dragonite', ('extremespeed',), condition='100/100', ability='innerfocus')]
    for mon in mons:
        mon['stats'].update(atk=800, spd=40, spe=40)
    request, battle, priors = matchup(mons, foe='deoxysattack', moves=('psychic',), ability='pressure')
    action, trace = pick_lead_model(request, battle, priors)
    assert action == Action('lead', 2)
    assert trace['rows'][0]['components']['fragility'] > trace['rows'][1]['components']['fragility']
    assert trace['rows'][1]['components']['tempo'] == .5


@pytest.mark.parametrize('tool,component', [('stealthrock', 'hazard'), ('uturn', 'pivot'), ('taunt', 'taunt')])
def test_actual_opening_tools_have_explicit_components(tool, component):
    request, battle, priors = matchup([own(moves=('psychic', 'splash')), own(moves=('psychic', tool))],
                                     moves=('recover', 'haze'))
    action, trace = pick_lead_model(request, battle, priors)
    assert action == Action('lead', 2)
    assert trace['rows'][0]['components'][component] == 0
    assert trace['rows'][1]['components'][component] > 0


def test_magic_bounce_and_good_as_gold_block_relevant_status_utility():
    request, battle, priors = matchup([own(moves=('psychic', 'stealthrock', 'taunt'))],
                                     foe='hatterene', moves=('calmmind',), ability='magicbounce')
    _, trace = pick_lead_model(request, battle, priors)
    assert trace['rows'][0]['components']['hazard'] == 0
    assert trace['rows'][0]['components']['taunt'] == 0
    request, battle, priors = matchup([own(moves=('psychic', 'taunt'))],
                                     foe='gholdengo', moves=('nastyplot',), ability='goodasgold')
    assert pick_lead_model(request, battle, priors)[1]['rows'][0]['components']['taunt'] == 0


def test_immune_volt_switch_does_not_gain_pivot_utility():
    request, battle, priors = matchup([own('Rotom', ('voltswitch', 'shadowball'))],
                                     foe='greattusk', moves=('stealthrock',), ability='protosynthesis')
    assert pick_lead_model(request, battle, priors)[1]['rows'][0]['components']['pivot'] == 0


def test_identical_scores_keep_party_order_and_inputs_are_unchanged():
    request, battle, priors = matchup([own(), own()])
    before = json.dumps([request, battle, priors], sort_keys=True)
    action, trace = pick_lead_model(request, battle, priors)
    assert action == Action('lead', 1)
    assert trace['rows'][0]['score'] == trace['rows'][1]['score']
    assert before == json.dumps([request, battle, priors], sort_keys=True)


def test_no_opposing_private_team_fields_or_files_are_read(monkeypatch):
    request, battle, priors = matchup([own(), own(moves=('shadowball',))])
    action, trace = pick_lead_model(request, battle, priors)
    battle['sides']['p2']['private_team_file'] = '/unreadable/private-team.txt'
    battle['sides']['p2']['pokemon'][0].update(private_actual_set={'moves': ['explosion'], 'atk': 9999},
                                            stats={'spa': 9999}, moves=['explosion'])
    def forbidden(*args, **kwargs):
        pytest.fail('preview tried to read a file')
    monkeypatch.setattr('builtins.open', forbidden)
    again, second = pick_lead_model(request, battle, priors)
    assert again == action
    assert second['rows'] == trace['rows']


def test_missing_own_stats_returns_traced_historical_fallback():
    request, battle, priors = matchup([own(), own('Kingambit')])
    request['side']['pokemon'][0].pop('stats')
    action, trace = pick_lead_model(request, battle, priors)
    assert action == pick_lead(request, battle)
    assert trace['fallback']['policy'] == 'historical_types'


def test_tera_equivalent_preview_hypotheses_keep_their_full_mass():
    request, battle, priors = matchup([own()])
    source = priors['species']['toxapex']['sets'][0]
    other = copy.deepcopy(source)
    source['weight'] = .3
    other.update(weight=.7, tera_type='water')
    priors['species']['toxapex']['sets'].append(other)
    _, models, _ = _opponent_models(battle['sides']['p2']['pokemon'][0], priors)
    assert len(models) == 1
    assert models[0][1] == 1.0


def test_incompatible_prior_fallback_preserves_confirmed_facts():
    _, battle, priors = matchup([own()], item='choicescarf')
    mon = battle['sides']['p2']['pokemon'][0]
    mon.update(item='assaultvest', ability='limber', revealed_moves=['poisonjab'])
    _, models, note = _opponent_models(mon, priors)
    assert 'fallback' in note
    assert models[0][0]['item'] == 'assaultvest'
    assert models[0][0]['ability'] == 'limber'
    assert 'poisonjab' in models[0][0]['moves']


def test_body_press_uses_our_defense_and_foul_play_the_opponents_attack():
    attacker = _own_model(own('Corviknight', ('bodypress', 'foulplay')))
    defender = _own_model(own('Toxapex'))
    press = _damage('bodypress', attacker, defender)
    attacker['stats']['atk'] *= 10
    assert _damage('bodypress', attacker, defender) == press
    attacker['stats']['def'] *= 2
    assert _damage('bodypress', attacker, defender) > press
    foul = _damage('foulplay', attacker, defender)
    attacker['stats']['atk'] *= 10
    assert _damage('foulplay', attacker, defender) == foul
    defender['stats']['atk'] *= 2
    assert _damage('foulplay', attacker, defender) > foul


def test_assault_vest_only_modifies_the_special_defense_stat():
    attacker, defender = _own_model(own()), _own_model(own('Blissey'))
    psychic, psyshock = _damage('psychic', attacker, defender), _damage('psyshock', attacker, defender)
    defender['item'] = 'assaultvest'
    assert _damage('psychic', attacker, defender) < psychic
    assert _damage('psyshock', attacker, defender) == psyshock


def test_ground_immunity_sources_stay_distinct_for_thousand_arrows():
    attacker, defender = _own_model(own('Garchomp')), _own_model(own('Flygon', ability='levitate'))
    assert _damage('earthquake', attacker, defender) == 0
    assert _damage('thousandarrows', attacker, defender) > 0
    defender['ability'] = 'eartheater'
    assert _damage('thousandarrows', attacker, defender) == 0


def test_variable_power_and_unknown_callbacks_do_not_create_nan():
    request, battle, priors = matchup([own('Ferrothorn', ('gyroball', 'grassknot', 'counter', 'protect'))])
    _, trace = pick_lead_model(request, battle, priors)
    assert trace['fallback'] is None
    assert all(math.isfinite(value) for value in trace['rows'][0]['components'].values())
