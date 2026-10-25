"""Retrospective next-public-revelation diagnostic; never full-set accuracy.

Uses only the state strictly before each new event. Remaining moves are assumed
uniform within a candidate; results mix choice/reveal frequency with set quality.
"""
import argparse
import copy
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

from data.pipeline.reveal_evidence import extract
from decision.belief import Belief, _to_set


def target_probability(candidates, field, value, known_moves):
    total = 0.
    for candidate, weight in candidates:
        if field == 'move':
            remaining = set(candidate.moves)-set(known_moves)
            total += weight/len(remaining) if value in remaining else 0
        else:
            total += weight*(getattr(candidate, field)==value)
    return total


def metrics(values):
    if not values:
        return None
    return {'examples':len(values),'mean_log_loss':sum(-math.log(max(1e-6,min(1.,p))) for p in values)/len(values),
            'supported_fraction':sum(p>0 for p in values)/len(values),
            'mean_target_mass':sum(values)/len(values),'probability_floor':1e-6}


def score(logs_path, arms, output):
    if output.exists():
        raise FileExistsError('use a fresh result path')
    results=defaultdict(lambda:defaultdict(lambda:defaultdict(list)))
    recoveries=defaultdict(int)
    exclusions=defaultdict(int)
    seen=set()
    per_battle=[]
    for line in logs_path.open():
        battle=json.loads(line)
        ident=(battle['battle_id'],battle['started_at'])
        if ident in seen:
            raise ValueError('duplicate battle')
        seen.add(ident)
        local=defaultdict(list)
        for event in extract(battle['log'],battle['battle_id'],include_state=True):
            if not event['native_set_evidence']:
                exclusions[event['exclusion_reason'] or event['field']]+=1
                continue
            field, value, side, slot=event['field'],event['value'],event['side'],event['slot']
            before=event['before']
            # Do not evaluate facts already public at the prediction point.
            mon=before['sides'][side]['pokemon'][slot]
            if field=='move' and value in mon['revealed_moves'] or field!='move' and mon.get(field)==value:
                continue
            for name, priors in arms.items():
                state=copy.deepcopy(before)
                state['us']='p2' if side=='p1' else 'p1'
                belief=Belief(priors,state,inference_mode='revelations')
                original=belief.candidates[slot]
                prior_p=target_probability(original,field,value,mon['revealed_moves'])
                belief.update(state)
                posterior_p=target_probability(belief.candidates[slot],field,value,mon['revealed_moves'])
                recoveries[name]+=len(belief.recovery_events)
                for stage,p in (('prior',prior_p),('observed_facts',posterior_p)):
                    arm=name+'/'+stage
                    results[battle['split']][arm][field].append(p)
                    results[battle['split']][arm]['all'].append(p)
                    local[arm].append(p)
        per_battle.append({'battle_id':battle['battle_id'],'started_at':battle['started_at'],'split':battle['split'],
                           'metrics':{arm:metrics(values) for arm,values in local.items()}})
    report={'claim':'retrospective next-public-revelation diagnostic, not exact-set/spread accuracy or battle strength',
        'source_time_limit':'current curated and September 2026 usage snapshots postdate many source games; not forward-time deployment evidence',
        'move_model':'uniform over candidate moves not previously observed; not a calibrated action policy',
        'selection':'fixed bounded Tiger sample; no mixture tuning on these scores',
        'input_sha256':hashlib.sha256(logs_path.read_bytes()).hexdigest(),
        'arms':{name:{'prior_sha256':hashlib.sha256(json.dumps(priors,sort_keys=True).encode()).hexdigest()} for name,priors in arms.items()},
        'metrics':{split:{arm:{field:metrics(ps) for field,ps in fields.items()} for arm,fields in aa.items()} for split,aa in results.items()},
        'recovery_events_across_reconstructed_predictions':dict(recoveries), 'excluded_observations':dict(exclusions),
        'battle_count':len(seen),'per_battle':per_battle}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+'\n')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--logs',required=True,type=Path)
    parser.add_argument('--baseline',required=True,type=Path)
    parser.add_argument('--mixture',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    report=score(args.logs,{'baseline':json.loads(args.baseline.read_text()),'mixture':json.loads(args.mixture.read_text())},args.output)
    print(json.dumps({'battle_count':report['battle_count'],'metrics':report['metrics']},indent=2))


if __name__=='__main__': main()
