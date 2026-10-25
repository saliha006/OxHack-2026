import json

from analysis.coherent_prediction_diagnosis import condition,training_battles,records,sampling_diversity
from bot.parser import Parser
from decision.belief import Belief
from decision.sets import PokemonSet
from evaluation.score_reveal_evidence import target_probability
from tests.test_curated_sets import prior,document
from tests.test_reveal_evidence import START
from data.pipeline.import_curated_sets import import_bank,mix


def test_test_battle_contents_are_never_used_to_select_training_records(tmp_path):
    path=tmp_path/'logs.jsonl'
    train={'battle_id':'train','split':'train','log':START}
    forbidden={'battle_id':'test','split':'test','log':None,'future_label':'do not inspect'}
    path.write_text(json.dumps(forbidden)+'\n'+json.dumps(train)+'\n')
    assert training_battles(path)==[train]


def test_target_slot_filter_matches_runtime_revelation_mode():
    original=prior();mixed,_=mix(original,import_bank(document(),original),.5)
    parser=Parser('p2')
    for line in START.splitlines():parser.feed(line)
    parser.feed('|move|p1a: Gold|Nasty Plot|p2a: Dozo')
    state=parser.snapshot();mon=state['sides']['p1']['pokemon'][0]
    belief=Belief(mixed,state,inference_mode='revelations')
    filtered,stage=condition(belief.candidates[0],mixed['species']['gholdengo']['usage'],mon,set())
    belief.update(state)
    assert stage=='surviving_templates' and filtered==belief.candidates[0]


def test_limited_bank_can_lose_a_future_move_without_triggering_recovery():
    def candidate(moves):
        return PokemonSet(moves=tuple(moves),item='leftovers',ability='goodasgold',tera_type='steel',nature='timid',evs=(0,0,0,252,4,252))
    guesses=[(candidate(['shadowball','trick']),.5),(candidate(['recover','makeitrain']),.5)]
    mon={'species':'gholdengo','revealed_moves':['shadowball'],'item':None,'ability':None,'tera_type':None}
    kept,stage=condition(guesses,{},mon,set())
    assert stage=='surviving_templates'
    assert target_probability(guesses,'move','recover',mon['revealed_moves'])>0
    assert target_probability(kept,'move','recover',mon['revealed_moves'])==0


def test_later_item_exchange_does_not_change_an_earlier_context_label():
    log=START+'|move|p1a: Gold|Nasty Plot|p2a: Dozo\n'
    a={'battle_id':'train','started_at':'2026-01-01','split':'train','log':log}
    b=dict(a,log=log+'|turn|2\n|move|p1a: Gold|Trick|p2a: Dozo\n|-item|p1a: Gold|Leftovers|[from] move: Trick\n')
    first=lambda source:next(e for e in records([source]) if e['value']=='nastyplot')
    assert first(a)==first(b)
    assert first(b)['prior_item_change_context'] is False


def test_diversity_measures_probability_mass_rather_than_record_count():
    a=sampling_diversity({'sets':[{'weight':1.}]})
    b=sampling_diversity({'sets':[{'weight':.5},{'weight':.5}]})
    assert a['effective_set_count']==1 and a['expected_distinct_sets_in_worlds']==1
    assert b['effective_set_count']==2 and b['expected_distinct_sets_in_worlds']>1.99
