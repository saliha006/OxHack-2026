"""Observed opening metrics, separated from whole-game strength and causality.

All lead comparisons use the preview snapshot. Own checkpoint HP is private
request truth; opponent HP remains a last-observed public proxy. No native search
or opposing private team file is used by this analysis.
"""
import argparse
from collections import Counter, defaultdict
import copy
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
CHECKPOINTS = (4, 6)


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def analysis_identity():
    paths = ['analysis/openings.py', 'decision/lead.py', 'decision/actions.py', 'decision/state.py',
             'decision/data/typechart.json', 'decision/data/pokedex.json']
    return {path: file_hash(ROOT / path) for path in paths}


def _identity(mon):
    details = mon.get('details', '').split(',', 1)[0]
    return {'ident': mon.get('ident'), 'species': re.sub('[^a-z0-9]', '', details.lower())}


def _resolve(identity, team):
    if identity is None:
        return None, 'unknown_lead_identity'
    if identity.get('ident'):
        matches = [(slot, mon) for slot, mon in enumerate(team, 1) if mon.get('ident') == identity['ident']]
        if len(matches) == 1:
            return matches[0], None
        if len(matches) > 1:
            matches = [(slot, mon) for slot, mon in matches if _identity(mon)['species'] == identity['species']]
    else:
        matches = [(slot, mon) for slot, mon in enumerate(team, 1) if _identity(mon)['species'] == identity['species']]
    if len(matches) == 1:
        return matches[0], None
    return None, 'missing_or_ambiguous_lead_identity'


def _lead_from_choice(choice, team):
    match = re.match(r'^team\s+([1-6])', choice or '')
    if not match or not 0 < int(match.group(1)) <= len(team):
        return None
    slot = int(match.group(1))
    return {'preview_slot': slot, **_identity(team[slot - 1])}


def _ordinary(row):
    request = row.get('request') or {}
    return (isinstance(row.get('state'), dict) and bool(request.get('active')) and
            not request.get('teamPreview') and not request.get('wait') and
            not any(request.get('forceSwitch', [])))


def _turn(row):
    value = (row.get('state') or {}).get('turn', row.get('turn'))
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _hp(condition):
    match = re.match(r'^(\d+)/(\d+)(?:\s|$)', condition or '')
    if match:
        current, maximum = map(int, match.groups())
        if maximum > 0 and 0 <= current <= maximum:
            return current, current / maximum
    if re.match(r'^0(?:\s+fnt)?$', condition or ''):
        return 0, 0.0  # Zero HP is exact even though the fainted request omits max HP.
    return None


def _side(row):
    value = (row.get('state') or {}).get('us') or (row.get('request') or {}).get('side', {}).get('id')
    return value if value in {'p1', 'p2'} else None


def _components(preview, slot):
    for row in preview.get('lead', {}).get('rows', []) if preview else []:
        if row.get('slot') == slot:
            return {'score': row.get('score'), 'components': copy.deepcopy(row.get('components'))}
    return None


def _tera_observed(rows, own_side, opponent=False):
    if own_side not in {'p1', 'p2'}:
        return None
    side_id = ('p2' if own_side == 'p1' else 'p1') if opponent else own_side
    known_unused = False
    for row in rows:
        public = (row.get('state') or {}).get('sides', {}).get(side_id, {})
        if public.get('tera_used') is True or any(mon.get('terastallized') for mon in public.get('pokemon', [])):
            return True
        if public.get('tera_used') is False:
            known_unused = True
        if not opponent and (row.get('request') or {}).get('side', {}).get('id') == side_id:
            if any(mon.get('terastallized') for mon in row['request']['side'].get('pokemon', [])):
                return True
    return False if known_unused else None


def _checkpoint(row, prefix, actual_lead, preview_team, target, game, trace_status):
    missing = {'target_request_turn': target, 'after_resolved_turns_target': target - 1,
               'actual_request_turn': None, 'source_line': None, 'overshoot_turns': None,
               'own_hp_sum': None, 'own_hp_fraction_sum': None, 'own_team_fainted': None,
               'own_lead_fainted': None, 'own_lead_hp_fraction': None,
               'opponent_public_fainted': None, 'opponent_public_hp_fraction_proxy': None,
               'own_tera_used': None, 'opponent_tera_used': None}
    early_end = (game.get('completion_verified') is True and not game.get('turn_limit_censored') and
                 isinstance(game.get('turns'), int) and game['turns'] < target)
    if row is None:
        return {**missing, 'status': 'missing_trace' if trace_status != 'available' else
                'early_finished' if early_end else 'missing_future_state', 'early_finished': early_end}
    turn = _turn(row)
    result = {**missing, 'status': 'available', 'early_finished': False, 'actual_request_turn': turn,
              'source_line': row.get('_source_line'), 'overshoot_turns': turn - target,
              'own_hp_source': 'authoritative private request conditions',
              'opponent_proxy_note': 'Last observed public HP; bench values can be stale, including Regenerator. Not hidden HP truth.'}
    request = row['request']
    team = request.get('side', {}).get('pokemon', [])
    expected_size = len(preview_team) if preview_team else 6
    hp = [_hp(mon.get('condition')) for mon in team]
    expected = [_resolve(_identity(mon), team)[0] for mon in preview_team]
    roster_valid = len(team) == expected_size and (not preview_team or all(match is not None for match in expected))
    if roster_valid and all(value is not None for value in hp):
        result.update(own_hp_sum=sum(value[0] for value in hp), own_hp_fraction_sum=sum(value[1] for value in hp),
                      own_team_fainted=sum(value[0] == 0 for value in hp))
    else:
        result['own_team_metric_unavailable_reason'] = 'incomplete roster or invalid private HP condition'
    lead, reason = _resolve(actual_lead, team)
    if lead is not None and (lead_hp := _hp(lead[1].get('condition'))) is not None:
        result.update(own_lead_fainted=lead_hp[0] == 0, own_lead_hp_fraction=lead_hp[1])
    else:
        result['own_lead_metric_unavailable_reason'] = reason or 'invalid private lead HP condition'
    us = _side(row)
    if request.get('side', {}).get('id') not in {None, us}:
        result.update(own_hp_sum=None, own_hp_fraction_sum=None, own_team_fainted=None,
                      own_lead_fainted=None, own_lead_hp_fraction=None,
                      own_team_metric_unavailable_reason='request/public side mismatch')
    them = 'p2' if us == 'p1' else 'p1'
    public_team = row.get('state', {}).get('sides', {}).get(them, {}).get('pokemon', []) if us else []
    percentages = [mon.get('hp_percent') for mon in public_team]
    if public_team and all(isinstance(hp, (int, float)) and math.isfinite(hp) and 0 <= hp <= 100 for hp in percentages):
        result.update(opponent_public_fainted=sum(hp == 0 for hp in percentages),
                      opponent_public_hp_fraction_proxy=sum(percentages) / 100)
    result['own_tera_used'] = _tera_observed(prefix, us)
    result['opponent_tera_used'] = _tera_observed(prefix, us, opponent=True)
    return result


def analyze_trace(rows, *, game, role, team=None, opponent_team=None, trace_status='available'):
    """One perspective. Missing future snapshots never borrow a later end/winner state."""
    preview = next((row for row in rows if (row.get('request') or {}).get('teamPreview')), None)
    preview_team = preview.get('request', {}).get('side', {}).get('pokemon', []) if preview else []
    ordinary = [(index, row) for index, row in enumerate(rows) if _ordinary(row) and _turn(row) is not None]
    initial = next((row for _, row in ordinary if _turn(row) == 1), None)
    selected = _lead_from_choice(preview.get('choice'), preview_team) if preview else None
    actual = None
    if initial:
        active = [mon for mon in initial['request']['side']['pokemon'] if mon.get('active')]
        if len(active) == 1:
            actual = _identity(active[0])
            match, _ = _resolve(actual, preview_team)
            actual['preview_slot'] = match[0] if match else None
    historical, historical_source, baseline_error = None, None, None
    if preview:
        recorded = preview.get('lead', {}).get('historical_choice')
        historical = _lead_from_choice(recorded, preview_team)
        if historical:
            historical_source = 'preview trace historical_choice'
        else:
            try:
                from decision.lead import pick_lead
                choice = pick_lead(preview['request'], preview['state']).to_choice()
                historical = _lead_from_choice(choice, preview_team)
                historical_source = 'unchanged pure type scorer on preview only'
            except (KeyError, TypeError, ValueError) as exc:
                baseline_error = f'{type(exc).__name__}: {exc}'
    actual_disagrees = (actual['preview_slot'] != historical['preview_slot'] if actual and historical and
                        actual.get('preview_slot') is not None else None)
    selected_disagrees = selected['preview_slot'] != historical['preview_slot'] if selected and historical else None
    points = {}
    for target in CHECKPOINTS:
        point = next(((index, row) for index, row in ordinary if _turn(row) >= target), None)
        points[str(target)] = _checkpoint(point[1] if point else None, rows[:point[0] + 1] if point else [],
                                          actual, preview_team, target, game, trace_status)
    team, opponent_team = team or {}, opponent_team or {}
    declared_side = game.get('a_side')
    if role == 'b' and declared_side in {'p1', 'p2'}:
        declared_side = 'p2' if declared_side == 'p1' else 'p1'
    observed_side = _side(initial or preview or {})
    declared_side = declared_side if declared_side in {'p1', 'p2'} else None
    result = {'game': game.get('game', game.get('battle')), 'role': role, 'trace_status': trace_status,
              'side': observed_side or declared_side, 'observed_side': observed_side, 'declared_side': declared_side,
              'side_identity_matches': observed_side == declared_side if observed_side and declared_side else None,
              'team_id': team.get('id'), 'team_style': team.get('style'),
              'team_sha256': team.get('sha256'), 'opponent_team_id': opponent_team.get('id'),
              'opponent_style': opponent_team.get('style'), 'game_completion_verified': game.get('completion_verified'),
              'turn_limit_censored': bool(game.get('turn_limit_censored')), 'preview_available': preview is not None,
              'preview_source_line': preview.get('_source_line') if preview else None,
              'lead_policy': preview.get('lead', {}).get('policy', preview.get('config', {}).get('lead_policy', 'unrecorded')) if preview else None,
              'selected_lead': selected, 'actual_lead': actual, 'actual_lead_confirmation': 'turn1 private active' if actual else 'unavailable',
              'historical_type_lead': historical, 'historical_choice_source': historical_source,
              'historical_baseline_error': baseline_error, 'selected_lead_disagrees': selected_disagrees,
              'actual_lead_disagrees': actual_disagrees,
              'preview_choice_matches_observed_lead': selected['preview_slot'] == actual.get('preview_slot') if selected and actual else None,
              'selected_lead_score': _components(preview, selected['preview_slot']) if selected else None,
              'actual_lead_score': _components(preview, actual.get('preview_slot')) if actual else None,
              'historical_lead_score_under_candidate_model': _components(preview, historical['preview_slot']) if historical else None,
              'lead_model_weights': copy.deepcopy(preview.get('lead', {}).get('weights')) if preview else None,
              'checkpoints': points}
    return result


def load_opening(path):
    rows = []
    with Path(path).open() as source:
        for number, line in enumerate(source, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            row['_source_line'] = number
            rows.append(row)
            if _ordinary(row) and (_turn(row) or 0) >= max(CHECKPOINTS):
                break  # Later battle outcomes cannot be opening features.
    return rows


def _aggregate(rows):
    def mean(values):
        values = [float(value) for value in values if value is not None]
        return {'n': len(values), 'mean': sum(values) / len(values) if values else None}
    result = {'perspectives': len(rows), 'preview_available': sum(row['preview_available'] for row in rows),
              'actual_lead_available': sum(row['actual_lead'] is not None for row in rows),
              'trace_status_counts': dict(Counter(row['trace_status'] for row in rows)),
              'completion_verified': sum(row['game_completion_verified'] is True for row in rows),
              'turn_limit_censored': sum(row['turn_limit_censored'] for row in rows),
              'actual_lead_disagreement': mean([row['actual_lead_disagrees'] for row in rows]), 'checkpoints': {}}
    for target in map(str, CHECKPOINTS):
        points = [row['checkpoints'][target] for row in rows]
        fields = ['own_lead_fainted', 'own_team_fainted', 'own_hp_sum', 'own_hp_fraction_sum',
                  'opponent_public_fainted', 'opponent_public_hp_fraction_proxy', 'own_tera_used', 'opponent_tera_used']
        result['checkpoints'][target] = {'status_counts': dict(Counter(point['status'] for point in points)),
                                         'early_finished': sum(point.get('early_finished', False) for point in points),
                                         'overshot': sum((point['overshoot_turns'] or 0) > 0 for point in points),
                                         'actual_turns': dict(Counter(str(point['actual_request_turn']) for point in points
                                                                      if point['actual_request_turn'] is not None)),
                                         **{field: mean([point[field] for point in points]) for field in fields}}
    return result


def summarize(rows):
    result = {'overall': _aggregate(rows)}
    for name, keys in [('by_role', ('role',)), ('by_role_side', ('role', 'side')),
                       ('by_role_style', ('role', 'team_style')), ('by_role_team', ('role', 'team_id')),
                       ('by_role_style_matchup', ('role', 'team_style', 'opponent_style'))]:
        groups = defaultdict(list)
        for row in rows:
            groups['|'.join(str(row.get(key) or 'unknown') for key in keys)].append(row)
        result[name] = {key: _aggregate(group) for key, group in groups.items()}
    result['disagreement_cases'] = [{key: row[key] for key in ('game', 'role', 'side', 'team_id', 'team_style',
                                                             'selected_lead', 'actual_lead', 'historical_type_lead',
                                                             'actual_lead_score', 'historical_lead_score_under_candidate_model', 'checkpoints')}
                                    for row in rows if row['actual_lead_disagrees'] is True]
    result['interpretation'] = ('Observed opening positions, not win probabilities or causal lead evaluations. Both perspectives of a battle are correlated. '
                                'Overshot checkpoints have a later exposure horizon. Opponent HP is a stale-bench public proxy; own HP uses only private requests. '
                                'Unavailable future states remain null; no winner/end-state imputation. Winning or early fainting alone does not establish lead quality.')
    return result


def freeze_plan(path):
    plan = {'schema': 1, 'frozen_utc': datetime.now(timezone.utc).isoformat(),
            'scope': 'Stage3 observed opening mechanisms; freeze before full-game scoring outcomes; no lead-weight tuning',
            'analysis_identity': analysis_identity(), 'roles_per_game': ['a', 'b'], 'checkpoint_request_turns': list(CHECKPOINTS),
            'checkpoint_rule': 'First recorded ordinary move request at turn>=4/6 (target after3/5resolved turns). Keep actual turn and overshoot; forced switches/wait/preview are excluded.',
            'lead_rule': 'Selected preview choice plus independently turn1-confirmed actual lead; resolve private ident across party reorder. Historical choice from preview trace, otherwise original unchanged pure types function on preview only.',
            'own_hp_rule': 'Sum exact private current HP and sum current/max fractions across the complete request party; fainted0 is exact even when maxHP omitted. Never use own public bench HP.',
            'faint_rule': 'Current fainted state at checkpoint, not an imputed cumulative count through unseen revival events.',
            'opponent_rule': 'Last-observed public faint count/HP fraction proxy, explicitly estimated and possibly stale on bench.',
            'tera_rule': 'Confirmed public spent-Tera/resource or private transformed flags observed only up to the checkpoint; no future snapshot leakage.',
            'missingness': 'Missing trace/future states and verified early finishes have null checkpoint metrics; never fill from winner or terminal state. Report all counts, void/censored records and both roles.',
            'breakdowns': ['role', 'role+side', 'role+ownstyle', 'role+ownteam', 'role+ownstyle+opponentstyle'],
            'provenance': 'Hash games, manifest, traces, analysis code and original type-scoring code/data. Store per-perspective JSON/CSV and disagreement components. No opponent private team files are read.',
            'claims': 'Descriptive mechanisms only; no causal blunder, calibrated win-probability or general strength claim.'}
    with Path(path).open('x') as output:
        json.dump(plan, output, indent=2)
        output.write('\n')


def run(args):
    plan = json.loads(args.plan.read_text())
    if plan['analysis_identity'] != analysis_identity():
        raise RuntimeError('opening analysis changed after plan freeze')
    games = [json.loads(line) for line in args.games.read_text().splitlines() if line.strip()]
    manifest = json.loads(args.manifest.read_text())
    teams = manifest.get('teams', [])
    output = []
    seen = set()
    for game in games:
        identity = game.get('game', game.get('battle'))
        if identity is None or identity in seen:
            raise ValueError('duplicate or missing game identity')
        seen.add(identity)
        if game.get('manifest_sha256') and manifest.get('manifest_sha256') and game['manifest_sha256'] != manifest['manifest_sha256']:
            raise ValueError('game refers to a different frozen manifest')
        for role, other in [('a', 'b'), ('b', 'a')]:
            trace = game.get('artifacts', {}).get(role, {}).get('trace')
            available = bool(trace and Path(trace).is_file())
            team_index, opponent_index = game.get(role + '_team'), game.get(other + '_team')
            team = teams[team_index] if isinstance(team_index, int) and 0 <= team_index < len(teams) else None
            opponent = teams[opponent_index] if isinstance(opponent_index, int) and 0 <= opponent_index < len(teams) else None
            error = None
            try:
                row = analyze_trace(load_opening(trace) if available else [], game=game, role=role, team=team,
                                    opponent_team=opponent, trace_status='available' if available else 'missing_trace')
            except (OSError, UnicodeDecodeError, json.JSONDecodeError, AttributeError, KeyError, TypeError, ValueError) as exc:
                error = f'{type(exc).__name__}: {exc}'
                row = analyze_trace([], game=game, role=role, team=team, opponent_team=opponent, trace_status='invalid_trace')
            if row['side_identity_matches'] is False:
                raise ValueError('trace side does not match the declared game schedule')
            recorded = game.get('source_sha256')
            recorded = recorded.get(role) if isinstance(recorded, dict) else None
            recorded = recorded or game.get('identities', {}).get(role, {}).get('source_sha256')
            declared = manifest.get(role, {}).get('source_sha256')
            if recorded and declared and recorded != declared:
                raise ValueError('game effective source does not match the declared arm')
            row.update(trace=trace, trace_sha256=file_hash(trace) if available else None,
                       trace_error=error, source_sha256=recorded, declared_manifest_source_sha256=declared,
                       source_identity_status='confirmed' if recorded and declared else 'partially_available')
            output.append(row)
    payload = summarize(output)
    payload['provenance'] = {'games_sha256': file_hash(args.games), 'manifest_sha256': file_hash(args.manifest),
                             'declared_manifest_id': manifest.get('manifest_sha256'), 'plan_sha256': file_hash(args.plan),
                             'analysis_identity': analysis_identity(), 'games': len(games), 'perspectives': len(output)}
    for path, value in [(args.output, payload), (args.raw_output, output)]:
        with path.open('x') as handle:
            json.dump(value, handle, indent=2)
            handle.write('\n')
    columns = ['game', 'role', 'side', 'team_id', 'team_style', 'opponent_team_id', 'opponent_style',
               'trace_status', 'trace_sha256', 'source_sha256',
               'lead_policy', 'actual_lead_disagrees']
    lead_fields = ['selected_lead_species', 'selected_lead_slot', 'actual_lead_species', 'actual_lead_slot',
                   'historical_type_lead_species', 'historical_type_lead_slot', 'actual_lead_score_json',
                   'historical_lead_score_under_candidate_model_json']
    metrics = ['status', 'early_finished', 'actual_request_turn', 'overshoot_turns', 'own_lead_fainted', 'own_team_fainted',
               'own_lead_hp_fraction', 'own_hp_sum', 'own_hp_fraction_sum', 'opponent_public_fainted',
               'opponent_public_hp_fraction_proxy', 'own_tera_used', 'opponent_tera_used']
    fields = columns + lead_fields + [name + '_t' + str(target) for target in CHECKPOINTS for name in metrics]
    with args.csv.open('x', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in output:
            lead_data = {}
            for name in ['selected_lead', 'actual_lead', 'historical_type_lead']:
                identity = row[name] or {}
                lead_data.update({name + '_species': identity.get('species'), name + '_slot': identity.get('preview_slot')})
            for name in ['actual_lead_score', 'historical_lead_score_under_candidate_model']:
                lead_data[name + '_json'] = json.dumps(row[name], sort_keys=True) if row[name] is not None else None
            writer.writerow({**{key: row[key] for key in columns},
                             **lead_data,
                             **{key + '_t' + target: value for target, point in row['checkpoints'].items()
                                for key, value in point.items() if key in metrics}})


def main():
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--freeze-plan', type=Path)
    parser.add_argument('--plan', type=Path)
    parser.add_argument('--games', type=Path)
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--raw-output', type=Path)
    parser.add_argument('--csv', type=Path)
    args = parser.parse_args()
    if args.freeze_plan:
        freeze_plan(args.freeze_plan)
    elif all((args.plan, args.games, args.manifest, args.output, args.raw_output, args.csv)):
        run(args)
    else:
        parser.error('supply --freeze-plan or all run inputs/outputs')


if __name__ == '__main__':
    main()
