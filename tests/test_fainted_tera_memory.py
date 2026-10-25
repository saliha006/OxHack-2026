"""Real requests clear a fainted Tera user's flag; confirmed spent Tera is irreversible."""
import copy
import json
from pathlib import Path
from random import Random

import pytest
from poke_engine import monte_carlo_tree_search

from decision.adapter import build_state
from decision.belief import Belief
from decision.state import our_side

ROOT = Path(__file__).parents[1]
FRAMES = json.loads((ROOT / 'tests/fixtures/fainted_tera_showdown.json').read_text())['frames']


@pytest.mark.parametrize('frame', FRAMES, ids=lambda frame: frame['id'])
def test_public_fainted_tera_fact_survives_blank_request_flag(frame):
    request, battle = frame['request'], frame['battle']
    observed = battle['sides'][battle['us']]
    assert observed['tera_used']
    assert not request['active'][0].get('canTerastallize')
    assert not any(mon['terastallized'] for mon in request['side']['pokemon'])
    native = our_side(request, observed)
    kyurem = next(mon for mon in native.pokemon if mon.id == 'kyurem')
    assert kyurem.hp == 0
    assert kyurem.terastallized
    assert sum(mon.terastallized for mon in native.pokemon) == 1


@pytest.mark.parametrize('frame', FRAMES, ids=lambda frame: frame['id'])
def test_native_root_does_not_search_an_already_spent_tera(frame):
    priors = json.loads((ROOT / 'data/set_candidates.json').read_text())
    belief = Belief(priors, frame['battle'], inference_mode='reliable')
    belief.update(frame['battle'])
    guessed = belief.sample_worlds(1, Random(2026102544))[0]
    state = build_state(frame['request'], frame['battle'], guessed)
    result = monte_carlo_tree_search(state, iterations=50, threads=1)
    assert not any(row.move_choice.endswith('-tera') for row in result.side_one)


def test_blank_observation_does_not_erase_an_exact_request_tera_flag():
    frame = copy.deepcopy(FRAMES[0])
    for mon in frame['battle']['sides'][frame['battle']['us']]['pokemon']:
        mon['terastallized'] = False
    kyurem = next(mon for mon in frame['request']['side']['pokemon'] if mon['details'].split(',')[0] == 'Kyurem')
    kyurem['terastallized'] = 'Ice'
    side = our_side(frame['request'], frame['battle']['sides'][frame['battle']['us']])
    assert next(mon for mon in side.pokemon if mon.id == 'kyurem').terastallized


def test_no_confirmed_slot_never_invents_a_transformed_pokemon():
    frame = copy.deepcopy(FRAMES[0])
    for mon in frame['battle']['sides'][frame['battle']['us']]['pokemon']:
        mon['terastallized'] = False
    side = our_side(frame['request'], frame['battle']['sides'][frame['battle']['us']])
    assert not any(mon.terastallized for mon in side.pokemon)
