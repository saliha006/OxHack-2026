import pytest

from analysis.coherent_forensics import audit_distribution, marginal_drift, parse_team


def test_team_truth_parser_retains_stat_order_zero_ivs_and_moves():
    rows=parse_team('''Pelipper (F) @ Damp Rock
Ability: Drizzle
Tera Type: Ground
EVs: 248 HP / 252 Def / 8 SpD
Relaxed Nature
IVs: 0 Atk / 0 Spe
- Hurricane
- Surf
- U-turn
- Roost
''')
    assert rows[0]['species']=='pelipper'
    assert rows[0]['evs']==[248,0,252,0,8,0]
    assert rows[0]['ivs']==[31,0,31,31,31,0]
    assert rows[0]['moves']==['hurricane','surf','uturn','roost']


def test_audit_measures_ground_truth_mass_without_changing_candidates():
    truth=parse_team('''Gholdengo @ Choice Scarf
Ability: Good as Gold
Tera Type: Steel
EVs: 252 SpA / 4 SpD / 252 Spe
Timid Nature
- Shadow Ball
- Make It Rain
- Trick
- Recover
''')[0]
    same={'weight':.4,'moves':truth['moves'],'item':'choicescarf','ability':'goodasgold','tera_type':'steel',
          'spread':{'nature':'timid','evs':truth['evs']}}
    other={**same,'weight':.6,'item':'airballoon'}
    score=audit_distribution([same,other],truth)
    assert score['move_recall_mass']==1
    assert score['item_mass']==pytest.approx(.4)
    assert score['moves_item_mass']==pytest.approx(.4)
    assert score['full_set_mass']==pytest.approx(.4)
    assert same['weight']==.4 and other['item']=='airballoon'


def test_marginal_drift_detects_probability_shift():
    make=lambda item,weight:{'weight':weight,'moves':['tackle'],'item':item,'ability':'runaway','tera_type':'normal',
                             'spread':{'nature':'serious','evs':[0]*6}}
    a={'species':{'eevee':{'sets':[make('leftovers',.9),make('airballoon',.1)]}}}
    b={'species':{'eevee':{'sets':[make('leftovers',.4),make('airballoon',.6)]}}}
    result=marginal_drift(a,b)[0]
    assert result['fields']['item']['total_variation']==pytest.approx(.5)
    assert result['fields']['nature']['total_variation']==0
