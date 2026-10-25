"""Publish compact summaries from preserved simulator evaluation artifacts; never rerun search."""
from collections import Counter
import argparse
import json
from pathlib import Path

from evaluation.mcts_improvements.run import summarize, write_json
from evaluation.mcts_root_rejections import root_rejections
from evaluation.mcts_policy_metrics import policy_metrics


def publish(run, prefix, require_complete=False):
    run,prefix=Path(run).resolve(),Path(prefix).resolve()
    manifest=json.loads((run/'manifest.json').read_text())
    rows=[json.loads(path.read_text()) for path in sorted(run.glob('game-*/result.json'))]
    if require_complete and len(rows)!=len(manifest['schedule']):
        raise ValueError(f"only {len(rows)}/{len(manifest['schedule'])} frozen games have results")
    summary=summarize(rows,manifest)
    summary.update(manifest_sha256=manifest['manifest_sha256'],phase=manifest['phase'],
        status='complete' if len(rows)==len(manifest['schedule']) else 'incomplete',
        original_raw_run=str(run),
        source_sha256={role:manifest[role]['source_sha256'] for role in 'ab'},
        effective_configs={role:manifest[role]['config'] for role in 'ab'},
        cpu_scope='Bot Python process plus reaped native SearchWorker descendants, including startup/preparation. Simulator/coordinator CPU is excluded. Actual native search milliseconds are wall time, not CPU.',
        uncertainty='Intervals use whole games. Candidate-team bootstrap acknowledges sparse clusters; shared opposing teams create additional dependence. Native MCTS is not deterministic despite repeatable simulator/sampling seeds.',
        team_provenance=manifest['team_provenance'])
    for role in 'ab':
        counts=Counter()
        reasons=Counter()
        unavailable=0
        policy_counts=Counter()
        mixing_reasons=Counter()
        forecast_types=Counter()
        for row in rows:
            path=row.get('artifacts',{}).get(role,{}).get('trace')
            if path and Path(path).exists():
                values,why=root_rejections(path)
                counts.update(values)
                reasons.update(why)
                row.setdefault('measured',{}).setdefault(role,{}).update(values)
                row['measured'][role]['native_root_rejection_reasons']=why
                policy,declines,forecasts=policy_metrics(path)
                policy_counts.update(policy)
                mixing_reasons.update(declines)
                forecast_types.update(forecasts)
                row['measured'][role].update(policy)
                row['measured'][role]['mixing_reasons']=declines
            else:
                unavailable+=1
        summary['arms'][role].update(counts)
        summary['arms'][role].update(policy_counts)
        summary['arms'][role]['mixing_reasons']=dict(mixing_reasons)
        summary['arms'][role]['frequency_forecast_types']=dict(forecast_types)
        summary['arms'][role]['native_root_rejection_reasons']=dict(reasons)
        summary['arms'][role]['root_rejection_metric_unavailable_perspectives']=unavailable
        denominator=counts.get('native_root_visits_for_rejection_metric',0)
        summary['arms'][role]['native_rejected_root_visit_fraction']=counts.get('native_rejected_root_visits',0)/denominator if denominator else None
    summary['rejection_metric_scope']='Native root rejections count per-world supported options filtered during mapping/legality checks, separately from server-rejected choices. Visit counts are diagnostic exposure, not a CPU measurement or a playing-strength result.'
    compact=[]
    for row in rows:
        kept={key:row[key] for key in ('game','block','a_team','b_team','a_side','simulator_seed','sampler_seed','mixed_policy_seed','winner','turns','wall_seconds','completion_verified','artifacts')}
        for key in ('error','turn_limit_censored','assignment'):
            if key in row: kept[key]=row[key]
        kept['source_sha256']={role:row.get('identities',{}).get(role,{}).get('source_sha256') for role in 'ab'}
        kept['measured']={role:{key:value for key,value in row.get('measured',{}).get(role,{}).items()
                                   if key not in ('decision_ms','actual_search_ms')}
                          for role in 'ab'}
        for role in 'ab':
            kept['measured'][role]['actual_search_ms']=sum(row.get('measured',{}).get(role,{}).get('actual_search_ms',[]))
        compact.append(kept)
    write_json(prefix.with_name(prefix.name+'-results.json'),summary)
    games=prefix.with_name(prefix.name+'-games.jsonl')
    games.parent.mkdir(parents=True,exist_ok=True)
    games.write_text(''.join(json.dumps(row,separators=(',',':'))+'\n' for row in compact))
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',required=True,type=Path)
    parser.add_argument('--output-prefix',required=True,type=Path)
    parser.add_argument('--require-complete',action='store_true')
    args=parser.parse_args()
    result=publish(args.run,args.output_prefix,args.require_complete)
    print(json.dumps({key:result[key] for key in ('status','recorded','planned','wins','losses','draws','voids','wilson_95','candidate_team_cluster_95')},indent=2))


if __name__=='__main__': main()
