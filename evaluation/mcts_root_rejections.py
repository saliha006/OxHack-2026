"""Read native-root legality rejections from preserved traces, separately from server retries."""
from collections import Counter
import json
from pathlib import Path


def root_rejections(path):
    counts=Counter()
    reasons=Counter()
    for line in Path(path).read_text().splitlines(keepends=True):
        if not line.endswith('\n'):
            counts['root_rejection_metric_incomplete_trace_tails']+=1
            break
        try:
            row=json.loads(line)
        except json.JSONDecodeError:
            counts['root_rejection_metric_malformed_records']+=1
            continue
        if 'request' not in row: continue
        failures=row.get('mapping_failures',[])
        counts['native_root_rejections']+=len(failures)
        counts['native_root_rejection_decisions']+=bool(failures)
        state=row.get('state',{})
        side=state.get('sides',{}).get(state.get('us'),{})
        fainted_tera=any(mon.get('terastallized') and mon.get('hp_percent',100)<=0
                          for mon in side.get('pokemon',[]))
        counts['decisions_after_confirmed_tera']+=bool(side.get('tera_used'))
        counts['decisions_after_confirmed_tera_user_fainted']+=fainted_tera
        by_world={world.get('index',i):world for i,world in enumerate(row.get('worlds',[]))}
        rejected={(failure.get('index'),failure.get('choice')) for failure in failures}
        tera_rejected={(index,choice) for index,choice in rejected if (choice or '').endswith('-tera')}
        counts['native_tera_root_rejections']+=len(tera_rejected)
        counts['native_tera_root_rejection_decisions']+=bool(tera_rejected)
        counts['native_tera_root_rejections_after_faint']+=len(tera_rejected) if fainted_tera else 0
        for failure in failures: reasons[failure.get('reason','unknown')]+=1
        for index,world in by_world.items():
            for visit in world.get('our_visits',[]):
                visits=visit.get('visits',0)
                if not isinstance(visits,(int,float)) or visits<=0: continue
                choice=visit.get('choice',visit.get('move_choice',''))
                counts['native_root_visits_for_rejection_metric']+=visits
                if (index,choice) in rejected:
                    counts['native_rejected_root_visits']+=visits
                if (index,choice) in tera_rejected:
                    counts['native_rejected_tera_root_visits']+=visits
                    if fainted_tera: counts['native_rejected_tera_root_visits_after_faint']+=visits
    return dict(counts),dict(reasons)
