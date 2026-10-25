"""Publish compact summaries from preserved simulator evaluation artifacts; never rerun search."""
import argparse
import json
from pathlib import Path

from evaluation.mcts_improvements.run import summarize, write_json


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
    compact=[]
    for row in rows:
        kept={key:row[key] for key in ('game','block','a_team','b_team','a_side','simulator_seed','sampler_seed','mixed_policy_seed','winner','turns','wall_seconds','completion_verified','artifacts')}
        for key in ('error','turn_limit_censored'):
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
