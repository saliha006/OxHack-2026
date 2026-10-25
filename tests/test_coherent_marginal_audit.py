import pytest
from analysis.coherent_marginal_audit import audit, diversity


def candidate(weight,item='leftovers',ev=0):
    return {'weight':weight,'moves':['tackle'],'item':item,'ability':'runaway','tera_type':'normal',
            'spread':{'nature':'serious','evs':[ev,0,0,0,0,0]}}


def test_independent_audit_checks_all_marginals_and_duplicate_diversity():
    a={'species':{'eevee':{'sets':[candidate(1)]}}}
    b={'species':{'eevee':{'sets':[candidate(.9),candidate(.1,'airballoon',252)]}}}
    r=audit(a,{'test':b});row=r['rows'][0]
    assert row['maximum_absolute_marginal_shift']==pytest.approx(.1)
    assert row['maximum_shift_by_family']['ev_0']==pytest.approx(.1)
    assert row['maximum_shift_by_family']['move']==0
    assert diversity([candidate(.5),candidate(.5)])['effective_set_count']==1
