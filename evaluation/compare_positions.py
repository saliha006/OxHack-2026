"""Counterfactual backend comparisons on frozen observed positions; never dispatches games.

Freeze inputs before examining new backend results:
    uv run python -m evaluation.compare_positions --select --prepare-only
Run the same embedded inputs with fresh agents, beliefs and seed:
    uv run python -m evaluation.compare_positions
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import platform
import subprocess
import time
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

from decision.actions import our_actions
from decision.agent import Agent
from decision.opponent import MOVES

ROOT = Path(__file__).resolve().parents[1]
PROTECT = {'protect', 'detect', 'spikyshield', 'kingsshield', 'banefulbunker', 'silktrap', 'burningbulwark', 'obstruct'}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds')


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def describe(choice: str | None, request: dict) -> dict:
    result = {'choice': choice, 'kind': None, 'label': choice, 'move_id': None, 'category': None,
              'setup': False, 'recovery': False, 'protect': False, 'switch': False,
              'forced_replacement': False, 'tera': 'terastallize' in (choice or '')}
    parts = (choice or '').split()
    if len(parts) < 2:
        return result
    result['kind'] = parts[0]
    if parts[0] == 'switch':
        result.update(switch=True, forced_replacement=bool(request.get('forceSwitch')),
                      label='switch to ' + request['side']['pokemon'][int(parts[1]) - 1]['details'].split(',')[0])
    elif parts[0] == 'move':
        move = request['active'][0]['moves'][int(parts[1]) - 1]
        entry = MOVES.get(move['id'], {})
        boost = entry.get('boosts', {}) if entry.get('target') == 'self' else entry.get('self', {}).get('boosts', {})
        result.update(move_id=move['id'], category=entry.get('category'),
                      label=entry.get('name', move.get('move', move['id'])) + (' + Tera' if result['tera'] else ''),
                      setup=any(amount > 0 for amount in boost.values()),
                      recovery=bool(entry.get('heal') or move['id'] in {'wish', 'rest', 'strengthsap', 'painsplit'}),
                      protect=move['id'] in PROTECT)
    return result


def _actual_rows(source: Path) -> list[dict]:
    rows = []
    for path in sorted(source.glob('players/**/*.jsonl')):
        file_sha = sha(path.read_bytes())
        for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
            row = json.loads(line)
            if not row.get('request') or not row.get('state') or row.get('kind') == 'team':
                continue
            choice = row.get('choice')
            rows.append({'request': row['request'], 'battle': row['state'],
                         'source': {'kind': 'actual_bot_decision', 'file': str(path.relative_to(ROOT)),
                                    'line': number, 'file_sha256': file_sha, 'decision_id': row.get('decision_id'),
                                    'recorded_backend': row.get('backend'), 'recorded_choice': choice,
                                    'recorded_action': describe(choice, row['request']),
                                    'recorded_search_support': row.get('search_support', {}),
                                    'recorded_total_ms': row.get('total_ms', row.get('think_ms'))}})
    return rows


def freeze_inputs(source: Path, fixture_request: Path, fixture_battle: Path) -> dict:
    rows = _actual_rows(source)
    selected, used = [], set()
    requests = [
        ('observed_setup', lambda row: row['source']['recorded_action']['setup']),
        ('observed_recovery', lambda row: row['source']['recorded_action']['recovery']),
        ('observed_voluntary_switch', lambda row: row['source']['recorded_action']['switch'] and
         not row['source']['recorded_action']['forced_replacement']),
        ('forced_replacement', lambda row: row['source']['recorded_action']['forced_replacement']),
        ('observed_tera', lambda row: row['source']['recorded_action']['tera']),
        ('protect_available', lambda row: any(describe(action.to_choice(), row['request'])['protect']
                                             for action in our_actions(row['request']))),
    ]
    unavailable = []
    for reason, predicate in requests:
        found = next((i for i, row in enumerate(rows) if i not in used and predicate(row)), None)
        if found is None:
            unavailable.append(reason)
            continue
        row = copy.deepcopy(rows[found])
        row['selection_reason'] = reason
        selected.append(row)
        used.add(found)
    for index, row in enumerate(rows):
        if len(selected) == 7:
            break
        if index not in used:
            selected.append({**copy.deepcopy(row), 'selection_reason': 'earliest_remaining_observed_position'})
            used.add(index)
    if len(selected) != 7:
        raise ValueError('need at least seven eligible saved positions')
    selected.append({'selection_reason': 'existing_known_swords_dance_fixture',
                     'request': json.loads(fixture_request.read_text()), 'battle': json.loads(fixture_battle.read_text()),
                     'source': {'kind': 'existing_contract_fixture',
                                'request_file': str(fixture_request.relative_to(ROOT)),
                                'request_sha256': sha(fixture_request.read_bytes()),
                                'battle_file': str(fixture_battle.relative_to(ROOT)),
                                'battle_sha256': sha(fixture_battle.read_bytes())}})
    for index, row in enumerate(selected):
        row['position_id'] = f'position-{index + 1:02d}'
    return {'frozen_at_utc': utc_now(), 'source_directory': str(source.relative_to(ROOT)),
            'selection_method': 'Before new searches: earliest unique row by sorted relative file path then line, '
             'in setup/recovery/voluntary-switch/forced-replacement/Tera/Protect-available priority; fill to seven '
             'actual rows with earliest remaining rows, then append the pre-existing turn-2 fixture.',
            'eligible_actual_positions': len(rows), 'unavailable_selection_categories': unavailable,
            'positions': selected}


def source_digest() -> str:
    hasher = hashlib.sha256()
    paths = [ROOT / 'pyproject.toml'] + [path for folder in ('bot', 'decision', 'contracts')
                                       for path in sorted((ROOT / folder).glob('*.py'))]
    for path in paths:
        hasher.update(str(path.relative_to(ROOT)).encode() + b'\0' + path.read_bytes() + b'\0')
    return hasher.hexdigest()


def compare(position: dict, priors: dict, backend: str, seed: int) -> dict:
    agent = Agent(priors, backend=backend, budget=3.0, mcts_worlds=8, search_ms=150,
                  engine_threads=1, seed=seed)
    started = time.monotonic()
    try:
        choice = agent.choose(copy.deepcopy(position['request']), copy.deepcopy(position['battle']))
        trace = copy.deepcopy(agent.last_trace or {})
        elapsed = (time.monotonic() - started) * 1000
    finally:
        agent.close()
    fields = ('total_ms', 'state_preparation_ms', 'search_ms', 'worker_wall_ms', 'requested_worlds',
              'scheduled_worlds', 'completed_worlds', 'failed_worlds', 'usable_worlds', 'fallback_reason',
              'failures', 'mapping_failures', 'recovery_events', 'state_approximations', 'opponent_support',
              'worker_generation', 'belief_history_reset')
    support = trace.get('search_support', {})
    return {'backend': backend, 'action': describe(choice, position['request']), 'observed_wall_ms': elapsed,
            'choice_is_legal': choice in {a.to_choice() for a in our_actions(position['request'])},
            'search_support': support,
            'labelled_search_support': [{**describe(action, position['request']), 'support': share}
                                       for action, share in sorted(support.items(), key=lambda item: (-item[1], item[0]))],
            'trace': {key: trace.get(key) for key in fields}, 'worlds': trace.get('worlds', [])}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, default=ROOT / 'evaluation/mcts-position-inputs.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'evaluation/mcts-position-comparison.json')
    parser.add_argument('--source', type=Path, default=ROOT / 'runs/mcts-final-gate')
    parser.add_argument('--priors', type=Path, default=ROOT / 'data/set_candidates.json')
    parser.add_argument('--seed', type=int, default=2026)
    parser.add_argument('--select', action='store_true', help='freeze inputs before inspecting new choices')
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--pause', type=float, default=.25, help='seconds between sequential positions')
    args = parser.parse_args(argv)
    if args.select:
        inputs = freeze_inputs(args.source.resolve(), ROOT / 'tests/fixtures/move_request.json',
                               ROOT / 'contracts/examples/battle_state_turn2.json')
        args.inputs.write_text(json.dumps(inputs, indent=2) + '\n')
    inputs = json.loads(args.inputs.read_text())
    if args.prepare_only:
        print(json.dumps({'selected': len(inputs['positions']),
                          'unavailable_categories': inputs['unavailable_selection_categories']}))
        return 0
    priors = json.loads(args.priors.read_text())
    output = {'analysis_started_at_utc': utc_now(), 'engine_version': version('poke-engine'),
              'python_version': platform.python_version(), 'source_sha256': source_digest(),
              'git_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'inputs_file': str(args.inputs.relative_to(ROOT)), 'inputs_sha256': sha(args.inputs.read_bytes()),
              'priors_sha256': sha(args.priors.read_bytes()), 'priors_source': priors.get('source'),
              'selection': {key: value for key, value in inputs.items() if key != 'positions'},
              'settings': {'seed': args.seed, 'fresh_agent_per_position_and_backend': True, 'budget_seconds': 3,
                           'mcts_worlds': 8, 'search_ms_per_world': 150, 'engine_threads': 1,
                           'search_support_is_win_probability': False, 'native_search_is_deterministic': False,
                           'pause_between_positions_seconds': args.pause},
              'interpretation': 'Counterfactual choices using the same saved request/state, real priors, reset beliefs '
               'and seed per backend. Historical soft evidence and worker history are discarded; these are not exact '
               'reproductions of recorded decisions. Native visit shares are search support, not win probabilities. '
               'No rollout outcomes were measured here, so disagreement does not establish which action was stronger.',
              'load_overlap': 'Sequential offline analysis overlapped the main four-concurrent-game pilot; these '
               'timings are diagnostics under shared load, not isolated latency benchmarks. The start/end window '
               'allows pilot latency contention to be identified.',
              'positions': []}
    for position in inputs['positions']:
        one = compare(position, priors, 'one_ply', args.seed)
        mcts = compare(position, priors, 'mcts', args.seed)
        result = {'position_id': position['position_id'], 'selection_reason': position['selection_reason'],
                  'source': position['source'], 'turn': position['battle']['turn'],
                  'one_ply': one, 'mcts8': mcts,
                  'disagree': one['action']['choice'] != mcts['action']['choice']}
        output['positions'].append(result)
        args.output.write_text(json.dumps(output, indent=2) + '\n')
        print(f"{result['position_id']} turn {result['turn']}: {one['action']['label']} | "
              f"{mcts['action']['label']} (different={result['disagree']})", flush=True)
        if args.pause:
            time.sleep(args.pause)
    output['analysis_finished_at_utc'] = utc_now()
    output['disagreements'] = sum(row['disagree'] for row in output['positions'])
    args.output.write_text(json.dumps(output, indent=2) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
