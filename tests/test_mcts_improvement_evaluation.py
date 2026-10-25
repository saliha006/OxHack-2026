"""Comparison safety: schedules, complete-source identity, and transparent failure accounting."""
import json
from pathlib import Path

import pytest

from evaluation.mcts_improvements.identity import source_identity, json_hash
from evaluation.mcts_improvements.run import balanced_schedule, summarize, run_manifest


def test_screen_schedule_is_side_balanced_paired_and_uses_all_teams():
    rows = balanced_schedule(10, 60, seed=17)
    assert rows == balanced_schedule(10, 60, seed=17)
    assert len({row['a_team'] for row in rows}) == 10
    assert len({row['b_team'] for row in rows}) == 10
    for first, second in zip(rows[::2], rows[1::2]):
        assert first['a_team'] != first['b_team']
        assert {first['a_side'], second['a_side']} == {'p1','p2'}
        for key in ('a_team','b_team','block','simulator_seed','sampler_seed','mixed_policy_seed'):
            assert first[key] == second[key]
        assert len(first['simulator_seed']) == 4
        assert first['mixed_policy_seed'] != first['sampler_seed']


def test_source_identity_covers_baseline_parser_adapter_belief_and_data(tmp_path):
    for folder in ('bot','decision','contracts','decision/data'):
        (tmp_path/folder).mkdir(parents=True,exist_ok=True)
    for file in ('bot/parser.py','decision/adapter.py','decision/belief.py','contracts/battle_state.py','decision/data/moves.json'):
        (tmp_path/file).write_text('original')
    before=source_identity(tmp_path)
    (tmp_path/'decision/belief.py').write_text('candidate')
    assert source_identity(tmp_path)['source_sha256'] != before['source_sha256']
    (tmp_path/'decision/belief.py').write_text('original')
    (tmp_path/'prediction').mkdir()
    (tmp_path/'prediction/tiger.py').write_text('unrelated pending work')
    assert source_identity(tmp_path) == before
    assert 'bot/parser.py' in before['files']
    assert 'decision/data/moves.json' in before['files']


def test_summary_keeps_voids_and_both_arms_resources():
    manifest={'schedule':[{}, {}, {}], 'seed':1,'teams':[{'style':'offense'},{'style':'balance'}]}
    measured={'decisions':2,'fallbacks':1,'decision_ms':[100,200],
              'actual_search_ms':[80,180],'cpu_seconds':.25, 'fallback_reasons':{'error':1}}
    rows=[{'winner':'a','a_team':0,'a_side':'p1','wall_seconds':1,'measured':{'a':measured,'b':measured}},
          {'winner':'b','a_team':1,'a_side':'p2','wall_seconds':2,'measured':{}},
          {'winner':'void','a_team':1,'a_side':'p2','wall_seconds':3,'measured':{},'error':'crash'}]
    result=summarize(rows,manifest)
    assert (result['wins'],result['losses'],result['draws'],result['voids']) == (1,1,0,1)
    assert result['score_rate'] == .5
    assert result['arms']['b']['cpu_seconds'] == .25
    assert result['arms']['a']['actual_search_ms'] == 260
    assert result['arms']['a']['max_ms'] == 200
    assert result['arms']['a']['fallback_reasons'] == {'error':1}


def test_manifest_tampering_rejected_before_any_child_launch(tmp_path):
    value={'schema':1, 'schedule':[]}
    value['manifest_sha256']=json_hash(value)
    value['schedule']=[{'changed':True}]
    manifest=tmp_path/'manifest.json'
    manifest.write_text(json.dumps(value))
    with pytest.raises(ValueError,match='frozen manifest changed'):
        run_manifest(manifest,tmp_path/'output')


def test_reserved_confirmation_rosters_differ_and_are_not_labelled_external_holdout():
    root=Path(__file__).resolve().parents[1]/'evaluation/mcts-improvements'
    pools=[json.loads((root/f'teams-{phase}-v1/teams.json').read_text()) for phase in ('screening','confirmation')]
    rosters=[{tuple(sorted(team['roster'])) for team in pool['teams']} for pool in pools]
    assert len(rosters[0]) == len(rosters[1]) == 10
    assert rosters[0].isdisjoint(rosters[1])
    for pool in pools:
        assert 'Not an independent external set holdout' in pool['provenance']['holdout_limit']
        assert all(not team['validation_errors'] for team in pool['teams'])


def test_worker_imports_entire_pipeline_from_selected_snapshot(tmp_path):
    import shutil
    import subprocess
    import sys
    from evaluation.mcts_improvements.identity import file_hash
    from evaluation.mcts_improvements.run import HERE, DEFAULT_CONFIG
    live=Path(__file__).resolve().parents[1]
    snapshot=tmp_path/'snapshot'
    for name in ('bot','decision','contracts'):
        shutil.copytree(live/name,snapshot/name,ignore=shutil.ignore_patterns('__pycache__','tests'))
    prior=tmp_path/'prior.json'
    prior.write_text('{}')
    initial={'root':str(snapshot),'source_sha256':source_identity(snapshot)['source_sha256'],
             'priors':str(prior),'priors_sha256':file_hash(prior),'config':DEFAULT_CONFIG,
             'side':'p1','runs':str(tmp_path/'runs'),'tag':'isolated-import-test'}
    process=subprocess.run([sys.executable,str(HERE/'worker.py')],
        input=json.dumps(initial)+'\n'+json.dumps({'op':'close','won':None,'turns':0})+'\n',
        capture_output=True,text=True,timeout=15,check=True)
    ready,closed=map(json.loads,process.stdout.splitlines())
    assert ready['kind']=='ready' and closed['kind']=='closed'
    assert {'bot.parser','bot.player','decision.agent','decision.belief','decision.adapter','decision.state','decision.search'} <= ready['loaded_modules'].keys()
    assert all(Path(path).is_relative_to(snapshot) for path in ready['loaded_modules'].values())
    assert ready['source_sha256']==initial['source_sha256']
    assert closed['summary']['cpu_seconds'] > 0


def test_native_visit_count_uses_actual_native_result_field(tmp_path):
    from evaluation.mcts_improvements.run import trace_metrics
    path=tmp_path/'trace.jsonl'
    path.write_text(json.dumps({'request':{},'worlds':[{'total_visits':123},{'total_visits':456}],'state_preparation_ms':3.5})+'\n')
    result=trace_metrics(path)
    assert result['native_visits']==579
    assert result['state_preparation_ms']==3.5


def test_compact_report_refuses_incomplete_final_and_preserves_voids(tmp_path):
    from evaluation.report_mcts_improvement import publish
    run=tmp_path/'run'
    game=run/'game-0000'
    game.mkdir(parents=True)
    manifest={'schedule':[{},{}], 'seed':1,'teams':[{'style':'offense'},{'style':'balance'}],
        'manifest_sha256':'frozen','phase':'screening','a':{'source_sha256':'candidate','config':{}},
        'b':{'source_sha256':'baseline','config':{}},'team_provenance':{'kind':'synthetic'}}
    row={'game':0,'block':0,'a_team':0,'b_team':1,'a_side':'p1','simulator_seed':[1,2,3,4],
         'sampler_seed':5,'mixed_policy_seed':6,'winner':'void','turns':0,'wall_seconds':1,
         'completion_verified':False,'artifacts':{},'error':'worker crashed','measured':{},'identities':{}}
    (run/'manifest.json').write_text(json.dumps(manifest))
    (game/'result.json').write_text(json.dumps(row))
    with pytest.raises(ValueError,match='only 1/2'):
        publish(run,tmp_path/'final',require_complete=True)
    result=publish(run,tmp_path/'partial')
    assert result['status']=='incomplete'
    assert result['voids']==1
    assert result['arms']['a']['unavailable_battle_perspectives']==1
    preserved=json.loads((tmp_path/'partial-games.jsonl').read_text())
    assert preserved['error']=='worker crashed'
    assert preserved['winner']=='void'
    assert 'Simulator/coordinator CPU is excluded' in result['cpu_scope']


@pytest.mark.parametrize('games',[60,200])
def test_four_game_blocks_balance_sides_and_team_assignments(games):
    from collections import Counter
    from evaluation.mcts_match_schedule import four_game_schedule
    rows=four_game_schedule(10,games,seed=44)
    assert rows==four_game_schedule(10,games,seed=44)
    assert len(rows)==games
    for offset in range(0,games,4):
        block=rows[offset:offset+4]
        first,second=block[0]['a_team'],block[0]['b_team']
        assert first!=second
        assert {(r['a_team'],r['b_team'],r['a_side']) for r in block} == {
            (first,second,'p1'),(first,second,'p2'),(second,first,'p1'),(second,first,'p2')}
        assert len({tuple(r['simulator_seed']) for r in block})==1
        assert len({r['sampler_seed'] for r in block})==1
    for role in ('a','b'):
        counts=Counter(r[f'{role}_team'] for r in rows)
        assert len(counts)==10
        assert set(counts.values())=={games//10}
    for team in range(10):
        assert Counter(r['a_side'] for r in rows if r['a_team']==team)=={'p1':games//20,'p2':games//20}
