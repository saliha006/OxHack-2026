from analysis.coherent_position_diagnostic import CONFIG, SEEDS, scarf_summary


def test_fixed_diagnostic_budget_and_posterior_summary():
    assert len(SEEDS)==3 and CONFIG['mcts_worlds']==8 and CONFIG['search_ms']==150
    battle={'us':'p1','sides':{'p2':{'active':0,'pokemon':[{'species':'gholdengo'}]}}}
    trace={'belief_candidates':[{'sets':[{'weight':.3,'item':'choicescarf'},{'weight':.7,'item':'airballoon'}]}],
           'sampled_worlds':[[{'item':'choicescarf'}],[{'item':'airballoon'}]]}
    result=scarf_summary(trace,battle)
    assert result['scarf_posterior_mass']==.3
    assert result['scarf_worlds']==1 and result['sampled_worlds']==2
