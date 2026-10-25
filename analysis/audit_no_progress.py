"""Review executed capped-move signatures without enabling a strategic policy.

Prepare before native checks, then launch run by absolute script path so spawned
children can reload this analysis helper while decision imports remain isolated.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import resource
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def support_helper():
    path = ROOT / 'evaluation/strategic_guard_audit.py'
    spec = importlib.util.spec_from_file_location('cap_audit_support', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prepare(args):
    sys.path.insert(0, str(ROOT))  # preparation reads local analysis/data; native run isolates its own imports
    from analysis.mine_losses import HAZARDS, selected_move
    from decision.actions import our_actions
    from decision.opponent import MOVES
    helper = support_helper()
    report = json.loads(args.report.read_text())
    facts, native_cases = [], []
    for game in report['games']:
        if not (game['counts'].get('hazard_at_cap') or game['counts'].get('setup_at_cap')):
            continue
        path = Path(game['trace'])
        decisions = [(number, row) for number, text in enumerate(path.read_text().splitlines(), 1)
                     if (row := json.loads(text)).get('kind') in {'move', 'switch'}]
        for index, (number, row) in enumerate(decisions[:-1]):
            battle, after = row['state'], decisions[index + 1][1]['state']
            us = battle['us']
            them = 'p2' if us == 'p1' else 'p1'
            ours, foe = battle['sides'][us], battle['sides'][them]
            active = ours['active']
            if active is None or foe['active'] is None or any(row['request'].get('forceSwitch', [])):
                continue
            move = selected_move(row)
            executed = move and any(event['type'] == 'move' and event['side'] == us and
                                    event['pokemon'] == active and event['move'] == move for event in after['last_turn'])
            positive = {key: value for key, value in MOVES.get(move, {}).get('boosts', {}).items() if value > 0}
            hazard = executed and move in HAZARDS and foe['hazards'].get(move, 0) >= HAZARDS[move]
            setup = executed and positive and MOVES.get(move, {}).get('target') == 'self' and all(
                ours['boosts'].get(stat, 0) >= 6 for stat in positive)
            if not (hazard or setup):
                continue
            active_request = next(mon for mon in row['request']['side']['pokemon'] if mon['active'])
            support = row['search_support']
            alternatives = {choice: weight for choice, weight in support.items()
                            if choice != row['choice'] and 'terastallize' not in choice}
            best = max(alternatives, key=alternatives.get) if alternatives else None
            before_foe = foe['pokemon'][foe['active']]
            record = {'id': row['decision_id'], 'signature': 'hazard_at_cap' if hazard else 'setup_at_cap',
                      'outcome': game['outcome'], 'trace': str(path), 'trace_sha256': helper.sha(path), 'line': number,
                      'turn': row['turn'], 'choice': row['choice'], 'move': move,
                      'own_species': ours['pokemon'][active]['species'], 'own_hp_before': ours['pokemon'][active]['hp_percent'],
                      'own_hp_after': after['sides'][us]['pokemon'][active]['hp_percent'],
                      'own_boosts_before': ours['boosts'], 'own_boosts_after': after['sides'][us]['boosts'],
                      'own_ability_exact': active_request['ability'], 'own_item_exact': active_request['item'],
                      'own_volatiles': ours['volatiles'], 'own_moves_exact': row['request']['active'][0]['moves'],
                      'foe_species': before_foe['species'], 'foe_revealed_moves': before_foe['revealed_moves'],
                      'foe_hazards_before': foe['hazards'], 'foe_hazards_after': after['sides'][them]['hazards'],
                      'following_events': after['last_turn'], 'chosen_support': support[row['choice']],
                      'best_supported_nontera_alternative': best,
                      'alternative_support': alternatives.get(best) if best else None,
                      'support_gap': support[row['choice']] - alternatives[best] if best else None,
                      'legal_actions': [action.to_choice() for action in our_actions(row['request'])],
                      'recorded_usable_worlds': row['usable_worlds'], 'recorded_mapping_discards': len(row.get('mapping_failures', [])),
                      'recorded_fallback': row.get('fallback_reason')}
            facts.append(record)
            if hazard:
                tasks = []
                for sample, world in enumerate(row['worlds']):
                    visits = world['opponent_visits']
                    modal = max(visits, key=lambda visit: visit['visits'])
                    modal_share = modal['visits'] / sum(visit['visits'] for visit in visits)
                    for choice in (row['choice'], best):
                        tasks.append({'index': len(tasks), 'sample_index': sample, 'choice': choice,
                                      'modal_reply': modal['choice'], 'modal_share': modal_share})
                native_cases.append({'id': row['decision_id'], 'case': {'request': row['request'], 'battle': battle,
                                                                      'sampled_worlds': row['sampled_worlds']},
                                     'counterfactual_tasks': tasks})
    if len(facts) != 10 or len(native_cases) != 3:
        raise ValueError('expected exactly3hazard and7setup cases from the specified completed report')
    inputs = {'facts': facts, 'native_cases': native_cases}
    with args.inputs.open('x') as output:
        json.dump(inputs, output, indent=2)
        output.write('\n')
    plan = {'scope': 'Retrospective review of all3hazard-at-cap losses and all7setup-at-cap wins in the first60-game comparison. No causal/strength claim or new policy.',
            'frozen_before_native_checks': True, 'report': str(args.report), 'report_sha256': helper.sha(args.report),
            'inputs': str(args.inputs.resolve()), 'inputs_sha256': helper.sha(args.inputs),
            'snapshot': str(args.snapshot.resolve()), 'source': helper.helpers().source_identity(args.snapshot),
            'engine': helper.helpers().engine_identity(), 'runner_sha256': helper.sha(__file__),
            'support_helper_sha256': helper.sha(ROOT / 'evaluation/strategic_guard_audit.py'),
            'native_plan': 'For each of the3hazard decisions compare original capped Rock vs the recorded highest-supported nonTera alternative, using all8original sampled hypotheses and each original modal reply;48conditional successors total, equal occurrence mass.',
            'stopping': 'Three predetermined16-check batches.3s total allowance/2.7s worker cutoff each; retain successful streamed checks/errors. No added checks chosen from results.',
            'limits': 'First comparison arms include the previously diagnosed Tera bug and earlier belief behavior; current corrected adapter with old recorded world hypotheses is off-policy. No full current-agent history replay, hidden opponent set truth or new scoring-team fitting. Native root/modal support is not calibrated probability. Winning does not establish capped setup was useful.',
            'source_identity_note': 'Raw miner game battle fields are null for this new harness; trace stems and full decision IDs supply actual identities. Per-game example lists truncate at5, so all10cases were recovered from executed raw transitions.'}
    with args.plan.open('x') as output:
        json.dump(plan, output, indent=2)
        output.write('\n')
    print(json.dumps({'frozen_plan': str(args.plan), 'cases': len(facts), 'native_checks': 48}), flush=True)


def native_worker(connection, payload):
    helper = support_helper()
    if helper.sha(ROOT / 'evaluation/strategic_guard_audit.py') != payload['plan']['support_helper_sha256']:
        raise RuntimeError('support helper changed after freeze')
    helper._offline_worker(connection, payload)


def run(args):
    helper = support_helper()
    plan = json.loads(args.plan.read_text())
    if helper.sha(__file__) != plan['runner_sha256'] or helper.sha(plan['inputs']) != plan['inputs_sha256']:
        raise RuntimeError('analysis code/inputs changed after freeze')
    loaded = helper._runtime(plan)
    from decision.search import SearchWorker
    inputs = json.loads(Path(plan['inputs']).read_text())
    batches = []
    for case in inputs['native_cases']:
        started = time.monotonic()
        worker = SearchWorker({'plan': plan, 'input': case}, target=native_worker)
        results, other = [], []
        initial = resource.getrusage(resource.RUSAGE_SELF), resource.getrusage(resource.RUSAGE_CHILDREN)
        try:
            for message in worker.stream(case['case']['request'], case['case']['battle'], {'mode': 'counterfactuals'}, started + 2.7):
                if message['kind'] == 'world':
                    results.append(message['result'])
                else:
                    other.append(message)
        finally:
            worker.close()
        final = resource.getrusage(resource.RUSAGE_SELF), resource.getrusage(resource.RUSAGE_CHILDREN)
        cpu = sum(row.ru_utime + row.ru_stime for row in final) - sum(row.ru_utime + row.ru_stime for row in initial)
        batches.append({'id': case['id'], 'results': results, 'messages': other,
                        'wall_ms': (time.monotonic() - started) * 1000, 'cpu_ms': cpu * 1000})
    with args.raw.open('x') as output:
        json.dump({'batches': batches, 'loaded_modules': loaded}, output, indent=2)
        output.write('\n')
    summaries = []
    for batch in batches:
        choices = {}
        for row in batch['results']:
            if 'counterfactual' in row:
                choices.setdefault(row['choice'], []).append(row)
        summaries.append({'id': batch['id'], 'completed': len(batch['results']), 'wall_ms': batch['wall_ms'], 'cpu_ms': batch['cpu_ms'],
                          'choices': {choice: {'worlds': len(rows), 'expected': {key: sum(row['counterfactual']['expected'][key] for row in rows) / len(rows)
                                                                              for key in rows[0]['counterfactual']['expected']},
                                              'modal_replies': [{'world': row['sample_index'], 'reply': row['modal_reply'], 'share': row['modal_share']} for row in rows]}
                                      for choice, rows in choices.items()},
                          'failures': [message for message in batch['messages'] if message['kind'] == 'failure']})
    result = {'scope': plan['scope'], 'source_sha256': plan['source']['source_sha256'], 'facts': inputs['facts'],
              'conditional_native_comparisons': summaries, 'runtime_guard_enabled': False,
              'limits': plan['limits'], 'plan_sha256': helper.sha(args.plan), 'raw_sha256': helper.sha(args.raw)}
    with args.output.open('x') as output:
        json.dump(result, output, indent=2)
        output.write('\n')
    print(json.dumps({'completed': sum(row['completed'] for row in summaries), 'output': str(args.output)}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    prep = sub.add_parser('prepare')
    prep.add_argument('--report', type=Path, required=True)
    prep.add_argument('--snapshot', type=Path, required=True)
    prep.add_argument('--inputs', type=Path, required=True)
    prep.add_argument('--plan', type=Path, required=True)
    measure = sub.add_parser('run')
    measure.add_argument('--plan', type=Path, required=True)
    measure.add_argument('--raw', type=Path, required=True)
    measure.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    prepare(args) if args.command == 'prepare' else run(args)


if __name__ == '__main__':
    main()
