import copy
import math

import pytest

from data.pipeline.calibrate_curated_sets import calibrate,compatibility,marginal
from data.pipeline.import_curated_sets import import_bank,mix
from tests.test_curated_sets import prior,document


def test_legacy_mixture_still_matches_versioned_artifact():
    import json
    from pathlib import Path
    old=json.loads(Path('data/set_candidates.json').read_text())
    bank=json.loads(Path('data/curated-v1/bank.json').read_text())
    assert mix(old,bank,.5)[0]==json.loads(Path('data/curated-v1/priors.json').read_text())


def test_bound_applies_even_to_single_role_and_keeps_coherent_iv_spread():
    old=prior();bank=import_bank(document(),old);saved=copy.deepcopy(old)
    result,report=calibrate(old,bank,max_fraction=.25,max_shift=.05)
    assert old==saved
    alpha=report['species']['gholdengo']['effective_curated_fraction']
    assert 0<alpha<=.05+1e-10  # Curated item absent from broad component.
    p=marginal(old['species']['gholdengo']['sets']);q=marginal(result['species']['gholdengo']['sets'])
    assert max(abs(p.get(k,0)-q.get(k,0)) for k in set(p)|set(q))<=.05+1e-10
    curated=next(c for c in result['species']['gholdengo']['sets'] if c['item']=='airballoon')
    assert curated['ivs'][1]==0 and curated['spread']['evs']==[252,0,196,0,0,60]
    assert math.isclose(sum(c['weight'] for c in result['species']['gholdengo']['sets']),1)


def test_usage_supported_role_outweighs_rare_role_without_hard_exclusion():
    old=prior();old['species']['gholdengo']['usage']['items']={'airballoon':.9,'leftovers':.001}
    doc=document();other=copy.deepcopy(doc['dex']['Gholdengo']['Bulky']);other['item']='Leftovers'
    doc['dex']['Gholdengo']['Rare']=other
    bank=import_bank(doc,old)
    result,_=calibrate(old,bank,max_fraction=.25,max_shift=.25)
    mass={c['item']:c['weight'] for c in result['species']['gholdengo']['sets']}
    assert mass['airballoon']>mass['leftovers']>0
    assert mass['choicescarf']>=.75


def test_missing_categories_neutral_and_zero_fraction_exact():
    old=prior();bank=import_bank(document(),old)
    c=bank['records'][0]['candidate']
    assert compatibility(c,{})==1
    result,_=calibrate(old,bank,max_fraction=0,max_shift=.05)
    assert result==old
    with pytest.raises(ValueError):calibrate(old,bank,max_fraction=float('nan'))
    with pytest.raises(ValueError):calibrate(old,bank,max_shift=0)


def test_ev_distance_is_smooth_not_exact_equality():
    c=import_bank(document(),prior())['records'][0]['candidate']
    close={'nature':c['spread']['nature'],'evs':[248,0,200,0,0,60]}
    far={'nature':c['spread']['nature'],'evs':[0,0,0,252,4,252]}
    assert compatibility(c,{'spreads':[(close,1)]})>compatibility(c,{'spreads':[(far,1)]})>0
