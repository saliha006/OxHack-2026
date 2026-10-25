"""Postprocess recorded policy diagnostics without changing evaluation processes."""
from collections import Counter
import json
from pathlib import Path


def policy_metrics(path):
    counts=Counter(); reasons=Counter(); forecasts=Counter()
    for line in Path(path).read_text().splitlines(keepends=True):
        if not line.endswith('\n'):
            counts['policy_metric_incomplete_trace_tails']+=1
            break
        try: row=json.loads(line)
        except json.JSONDecodeError:
            counts['policy_metric_malformed_records']+=1
            continue
        if 'request' not in row: continue
        enabled=bool(row.get('config',{}).get('mix_root'))
        counts['mixing_enabled_decisions']+=enabled
        mixing=row.get('root_mixing')
        if isinstance(mixing,dict):
            counts['mixing_evaluated_decisions']+=1
            counts['mixing_sampled_decisions']+=bool(mixing.get('sampled'))
            counts['mixing_selection_changed_decisions']+=bool(mixing.get('selection_changed'))
            counts['mixing_eligible_decisions']+=bool(mixing.get('eligible_choices'))
            counts['mixing_candidate_pair_decisions']+=len(mixing.get('candidate_choices',[]))==2
            reasons[mixing.get('reason') or 'unknown']+=1
        prediction=row.get('history_prediction')
        if isinstance(prediction,dict):
            counts['frequency_policy_decisions']+=1
            if prediction.get('predicted_type'):
                counts['frequency_prediction_decisions']+=1
                forecasts[prediction['predicted_type']]+=1
                counts['frequency_prediction_switch_choices']+=(row.get('choice') or '').startswith('switch ')
    return dict(counts),dict(reasons),dict(forecasts)
