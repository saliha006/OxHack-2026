"""Freeze four-game blocks balancing simulator sides and bot/team assignments.

The existing evaluation runner consumes explicit schedules and checks their whole
manifest hash. This separate planner leaves running evaluations and harness code
unchanged. With ten teams, each round is a perfect matching; 60 games use three
rounds and 200 games use ten rounds. Every team has equal exposure in each role.
"""
from collections import Counter
import argparse
import json
from pathlib import Path
import random

from evaluation.mcts_improvements.identity import json_hash, file_hash
from evaluation.mcts_improvements.run import write_json


def four_game_schedule(team_count, games, seed):
    if team_count < 2 or team_count % 2:
        raise ValueError('four-game matching needs an even number of teams')
    games_per_round = 2 * team_count
    if games < games_per_round or games % games_per_round:
        raise ValueError('game count must contain complete perfect-matching rounds')
    rng = random.Random(seed)
    order = list(range(team_count))
    rng.shuffle(order)
    matchings = []
    ring = order[:]
    for _ in range(team_count - 1):
        matchings.append([(ring[i],ring[-1-i]) for i in range(team_count//2)])
        ring = [ring[0],ring[-1],*ring[1:-1]]
    rows=[]
    remaining_rounds=games//games_per_round
    while remaining_rounds:
        indices=list(range(len(matchings)))
        rng.shuffle(indices)
        for index in indices[:remaining_rounds]:
            pairs=matchings[index][:]
            rng.shuffle(pairs)
            for first,second in pairs:
                simulator_seed=[rng.randrange(65536) for _ in range(4)]
                sampler_seed=rng.randrange(2**31)
                mixed_policy_seed=rng.randrange(2**31)
                block=len(rows)//4
                for assignment,(a,b) in enumerate(((first,second),(second,first))):
                    for side in ('p1','p2'):
                        rows.append({'game':len(rows),'block':block,'assignment':assignment,
                            'a_team':a,'b_team':b,'a_side':side,'simulator_seed':simulator_seed,
                            'sampler_seed':sampler_seed,'mixed_policy_seed':mixed_policy_seed})
            remaining_rounds-=1
    exposures={role:Counter(row[f'{role}_team'] for row in rows) for role in ('a','b')}
    assert len(rows)==games
    assert all(set(counts.values())=={games//team_count} for counts in exposures.values())
    return rows


def rebalance_manifest(source, output):
    source,output=Path(source).resolve(),Path(output).resolve()
    if output.exists():
        raise ValueError('new manifest path required; preserve the previous frozen plan')
    manifest=json.loads(source.read_text())
    previous_hash=manifest.pop('manifest_sha256')
    if json_hash(manifest)!=previous_hash:
        raise ValueError('source manifest hash is invalid')
    manifest['schedule']=four_game_schedule(len(manifest['teams']),len(manifest['schedule']),manifest['seed'])
    manifest['schedule_design']={
        'kind':'four-game blocks: both simulator-side swaps and both bot/team assignments',
        'planner':'evaluation/mcts_match_schedule.py','planner_sha256':file_hash(Path(__file__)),
        'equal_team_exposure':True,
        'supersedes_unrun_manifest':str(source),'supersedes_manifest_sha256':previous_hash,
        'outcome_separation':'Frozen before any outcome under this revised schedule. Earlier screening outcomes may already exist; this is not a retrospective claim about screening preregistration.'}
    manifest['manifest_sha256']=json_hash(manifest)
    write_json(output,manifest)
    return manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    result=rebalance_manifest(args.manifest,args.output)
    print(result['manifest_sha256'])


if __name__=='__main__': main()
