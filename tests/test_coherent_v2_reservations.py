import json
from collections import Counter
from pathlib import Path

from evaluation.reserve_coherent_v2_teams import ROSTERS, SCHEDULE_SEED, prior_reservations
from evaluation.mcts_match_schedule import four_game_schedule


def test_new_rosters_are_disjoint_from_recorded_prior_snapshot_and_hashes_match():
    import hashlib
    root=Path(__file__).resolve().parents[1]
    manifest=json.loads((root/'evaluation/coherent-sets/v2-screening-teams/teams.json').read_text())
    rosters={tuple(sorted(t['roster'])) for t in manifest['teams']}
    assert len(rosters)==10
    assert rosters.isdisjoint({tuple(r) for r in manifest['excluded_rosters']})
    assert all(len(set(t['roster']))==6 and not t['validation_errors'] for t in manifest['teams'])
    assert 'Not an independent external set holdout' in manifest['provenance']['holdout_limit']
    for team in manifest['teams']:
        # Paths in a frozen historical reservation may be machine-specific.
        path=root/'evaluation/coherent-sets/v2-screening-teams'/Path(team['path']).name
        assert hashlib.sha256(path.read_text().strip().encode()).hexdigest()==team['sha256']


def test_fresh_schedule_balances_sides_assignments_and_team_exposure():
    rows=four_game_schedule(len(ROSTERS),60,SCHEDULE_SEED)
    assert len(rows)==60
    assert rows==four_game_schedule(len(ROSTERS),60,SCHEDULE_SEED)
    for role in ('a','b'):
        assert set(Counter(r[role+'_team'] for r in rows).values())=={6}
    for start in range(0,60,4):
        block=rows[start:start+4]
        assert {r['a_side'] for r in block}=={'p1','p2'}
        assert len({(r['a_team'],r['b_team']) for r in block})==2
        assert len({tuple(r['simulator_seed']) for r in block})==1
        assert len({r['sampler_seed'] for r in block})==1


def test_exclusion_snapshot_uses_rosters_not_outcome_fields(tmp_path):
    a=tmp_path/'old.json';b=tmp_path/'results.json'
    roster=['A','B','C','D','E','F']
    a.write_text(json.dumps({'teams':[{'roster':roster}], 'wins':999}))
    b.write_text(json.dumps({'wins':1000,'losses':0}))
    used,sources=prior_reservations([tmp_path])
    assert used=={tuple(roster)}
    assert [Path(s['path']).name for s in sources]==['old.json']
    a.write_text(json.dumps({'teams':[{'roster':roster}], 'wins':0}))
    assert prior_reservations([tmp_path])[0]==used
