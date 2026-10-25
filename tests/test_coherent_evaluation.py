import copy
import json
from pathlib import Path
from types import SimpleNamespace

from data.pipeline.reveal_evidence import extract
from evaluation.score_reveal_evidence import score
from evaluation.mcts_improvements.run import freeze_manifest
from tests.test_curated_sets import prior, document
from data.pipeline.import_curated_sets import import_bank, mix
from tests.test_reveal_evidence import START


def test_independent_prior_files_are_frozen_in_each_arm(tmp_path,monkeypatch):
    import evaluation.mcts_improvements.run as runner
    root=tmp_path/'snapshot'
    for name in ('bot','decision/data','contracts'):
        (root/name).mkdir(parents=True,exist_ok=True)
    a=tmp_path/'a.json';b=tmp_path/'b.json'
    a.write_text('{"a":1}');b.write_text('{"b":2}')
    team=tmp_path/'team.txt';team.write_text('Test\n')
    import hashlib
    teams=tmp_path/'teams.json'
    teams.write_text(json.dumps({'teams':[{'path':str(team),'sha256':hashlib.sha256(b'Test').hexdigest()}]*2,
                                'provenance':{'kind':'fixture'}}))
    monkeypatch.setattr(runner,'engine_identity',lambda:{'version':'fixture'})
    monkeypatch.setattr(runner,'validate_teams',lambda *args:[{'packed':'fixture'}]*2)
    monkeypatch.setattr(runner.subprocess,'run',lambda *args,**kwargs:SimpleNamespace(stdout='fixture-commit\n'))
    result=freeze_manifest(root,root,a,teams,tmp_path,phase='smoke',games=2,b_priors=b)
    assert result['a']['priors']==str(a) and result['b']['priors']==str(b)
    assert result['a']['priors_sha256']!=result['b']['priors_sha256']


def test_scoring_uses_prefix_and_does_not_invent_hidden_labels(tmp_path):
    old=prior();new,_=mix(old,import_bank(document(),old),.5)
    # Owner Gholdengo is p1; Dondozo unsupported recovery is allowed but no labels invented.
    log=START+'|move|p1a: Gold|Nasty Plot|p2a: Dozo\n|turn|2\n|move|p1a: Gold|Shadow Ball|p2a: Dozo\n'
    path=tmp_path/'logs.jsonl'
    path.write_text(json.dumps({'battle_id':'fixture','started_at':'2026-01-01','split':'test','log':log})+'\n')
    result=score(path,{'baseline':old,'mixture':new},tmp_path/'result.json')
    assert result['metrics']['test']['mixture/prior']['move']['supported_fraction']==1
    assert result['metrics']['test']['baseline/prior']['move']['supported_fraction']==.5
    assert set(result['metrics']['test']['baseline/prior'])=={'move','all'}
    events=list(extract(log,'fixture',include_state=True))
    first=next(e for e in events if e['field']=='move')
    assert first['before']['sides']['p1']['pokemon'][0]['revealed_moves']==[]
