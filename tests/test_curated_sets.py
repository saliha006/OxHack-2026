import copy
import json
import math
from pathlib import Path

import pytest

from data.pipeline.import_curated_sets import import_bank, key, mix
from decision.belief import _to_set


def prior():
    return {'source':{'format':'gen9ou'},'species':{'gholdengo':{'sets':[{
        'weight':1.,'moves':['shadowball','makeitrain','trick','recover'],'item':'choicescarf',
        'ability':'goodasgold','tera_type':'ghost','spread':{'nature':'timid','evs':[0,0,0,252,4,252]}}],
        'usage':{'moves':{},'items':{},'abilities':{},'spreads':[], 'tera_types':{'steel':.7,'ghost':.3}}}}}


def document():
    return {'dex':{'Gholdengo':{'Bulky':{'moves':['Nasty Plot','Shadow Ball','Recover','Make It Rain'],
        'item':'Air Balloon','ability':'Good as Gold','nature':'Bold','teraType':'Fairy',
        'evs':{'hp':252,'def':196,'spe':60},'ivs':{'atk':0}}}}}


def test_preserves_whole_roles_and_zero_iv_in_serving():
    bank=import_bank(document(),prior())
    assert not bank['rejected']
    candidate=bank['records'][0]['candidate']
    native=_to_set(candidate)
    assert native.ivs==(31,0,31,31,31,31)
    assert native.evs==(252,0,196,0,0,60)
    assert native.item=='airballoon' and native.nature=='bold'
    assert _to_set(prior()['species']['gholdengo']['sets'][0]).ivs==(31,)*6


def test_mixture_keeps_broad_mass_and_never_changes_input():
    old=prior(); saved=copy.deepcopy(old)
    result,provenance=mix(old,import_bank(document(),old),.5)
    assert old==saved
    sets=result['species']['gholdengo']['sets']
    assert len(sets)==2 and math.isclose(sum(s['weight'] for s in sets),1)
    assert {s['item']:s['weight'] for s in sets}=={'airballoon':.5,'choicescarf':.5}
    assert provenance['gholdengo']['roles']==1
    with pytest.raises(ValueError): mix(old,import_bank(document(),old),1)


def test_alternative_slots_and_unknown_tera_keep_completion_provenance():
    doc=document(); entry=doc['dex']['Gholdengo']['Bulky']; entry['moves'][-1]=['Make It Rain','Thunderbolt']
    del entry['teraType']
    bank=import_bank(doc,prior())
    assert len(bank['records'])==4
    assert sum(r['variant_weight'] for r in bank['records'])==1
    assert all(r['unknown_in_source']==['tera_type'] for r in bank['records'])
    assert all('recover' in r['candidate']['moves'] for r in bank['records'])


def test_deduplication_and_uncovered_species_unchanged():
    old=prior(); doc=document()
    doc['dex']['Gholdengo']['Duplicate']=copy.deepcopy(doc['dex']['Gholdengo']['Bulky'])
    result,_=mix(old,import_bank(doc,old),.5)
    assert len(result['species']['gholdengo']['sets'])==2
    result0,_=mix(old,import_bank(doc,old),0)
    assert result0==old


def test_duplicate_role_does_not_outvote_a_distinct_role():
    old=prior(); doc=document()
    doc['dex']['Gholdengo']['Duplicate']=copy.deepcopy(doc['dex']['Gholdengo']['Bulky'])
    other=copy.deepcopy(doc['dex']['Gholdengo']['Bulky']);other['item']='Leftovers'
    doc['dex']['Gholdengo']['Other']=other
    result,_=mix(old,import_bank(doc,old),.5)
    assert {s['item']:s['weight'] for s in result['species']['gholdengo']['sets']}=={
        'airballoon':.25,'leftovers':.25,'choicescarf':.5}


def test_invalid_stats_are_rejected_and_reported():
    doc=document(); doc['dex']['Gholdengo']['Bulky']['evs']={'hp':252,'def':252,'spe':252}
    bank=import_bank(doc,prior())
    assert not bank['records'] and 'EV sum' in bank['rejected'][0]['reason']
