"""Opening observations use own requests and never invent missing futures."""
import argparse
import copy
import csv
import json

import pytest

from analysis.openings import analyze_trace, freeze_plan, run, summarize
from tests.turn2 import EXAMPLE, REQUEST


def snapshot(turn, *, active='p1: Gholdengo', faint_lead=False, tera=False):
    request = copy.deepcopy(REQUEST)
    team = request['side']['pokemon']
    for mon in team:
        mon['active'] = mon['ident'] == active
        mon['terastallized'] = ''
        if faint_lead and mon['ident'] == 'p1: Gholdengo':
            mon['condition'] = '0 fnt'
    # A different ordering at each request must not redefine the opening lead.
    request['side']['pokemon'] = sorted(team, key=lambda mon: not mon['active'])
    if faint_lead:
        lead = next(mon for mon in request['side']['pokemon'] if mon['ident'] == 'p1: Gholdengo')
        request['side']['pokemon'].remove(lead)
        request['side']['pokemon'].append(lead)
    battle = copy.deepcopy(EXAMPLE)
    battle['turn'] = turn
    for side in battle['sides'].values():
        side['tera_used'] = False
        for mon in side['pokemon']:
            mon['terastallized'] = False
    battle['sides']['p1']['tera_used'] = tera
    return {'kind': 'move', 'turn': turn, 'request': request, 'state': battle, 'choice': 'move 1'}


def preview(*, recorded_history=True):
    request = copy.deepcopy(REQUEST)
    request['teamPreview'] = True
    request.pop('active')
    row = {'kind': 'team', 'turn': 0, 'choice': 'team 312456', 'request': request, 'state': snapshot(0)['state']}
    if recorded_history:
        row['lead'] = {'policy': 'moves_stats_v1', 'historical_choice': 'team 123456', 'weights': {'offense': 1},
                       'rows': [{'slot': 1, 'score': .1, 'components': {'offense': .1}},
                                {'slot': 3, 'score': .7, 'components': {'offense': .8, 'fragility': .1}}]}
    return row


def game(**changes):
    return {'game': 7, 'turns': 8, 'completion_verified': True, 'a_team': 0, 'b_team': 1, **changes}


def rows():
    return [preview(), snapshot(1), snapshot(4, active='p1: Great Tusk', faint_lead=True), snapshot(6)]


def test_private_hp_is_authoritative_over_stale_own_public_bench_and_party_reordering():
    data = rows()
    for mon in data[2]['state']['sides']['p1']['pokemon']:
        mon['hp_percent'] = 100  # stale public view incorrectly suggests the lead is still healthy
    result = analyze_trace(data, game=game(), role='a')
    point = result['checkpoints']['4']
    assert result['actual_lead']['ident'] == 'p1: Gholdengo'
    assert result['actual_lead']['preview_slot'] == 3
    assert data[2]['request']['side']['pokemon'][-1]['ident'] == 'p1: Gholdengo'
    assert point['own_lead_fainted'] is True and point['own_team_fainted'] == 1
    assert point['own_hp_sum'] == 1660
    assert point['own_hp_fraction_sum'] == pytest.approx(4.75)


def test_preview_components_and_historical_type_disagreement_are_preserved():
    result = analyze_trace(rows(), game=game(), role='a')
    assert result['actual_lead_disagrees'] is True
    assert result['historical_choice_source'] == 'preview trace historical_choice'
    assert result['actual_lead_score']['components'] == {'offense': .8, 'fragility': .1}
    assert result['historical_lead_score_under_candidate_model']['components'] == {'offense': .1}


def test_missing_historical_trace_uses_only_original_preview_types(monkeypatch):
    def expensive(*args, **kwargs):
        pytest.fail('opening analysis must not invoke native search or simulation')
    monkeypatch.setattr('poke_engine.monte_carlo_tree_search', expensive)
    monkeypatch.setattr('poke_engine.generate_instructions', expensive)
    data = [preview(recorded_history=False), snapshot(1), snapshot(4)]
    # A later foe roster must not enter the preview comparison.
    for mon in data[2]['state']['sides']['p2']['pokemon']:
        mon['species'] = 'heatran'
    result = analyze_trace(data, game=game(), role='a')
    assert result['historical_type_lead']['preview_slot'] == 1
    assert result['historical_choice_source'] == 'unchanged pure type scorer on preview only'


def test_missing_future_checkpoint_is_not_filled_from_winner_or_terminal_state():
    terminal = snapshot(9, faint_lead=True)
    terminal.update(kind='end', request=None, won=False)
    result = analyze_trace([preview(), snapshot(1), terminal], game=game(winner='b', turns=9), role='a')
    for point in result['checkpoints'].values():
        assert point['status'] == 'missing_future_state'
        assert point['own_lead_fainted'] is None and point['own_hp_fraction_sum'] is None


def test_battle_ending_before_checkpoint_is_counted_unavailable_without_imputed_faints():
    result = analyze_trace([preview(), snapshot(1)], game=game(turns=2, winner='b'), role='a')
    assert result['checkpoints']['4']['status'] == 'early_finished'
    assert result['checkpoints']['4']['own_team_fainted'] is None
    aggregate = summarize([result])
    assert aggregate['overall']['checkpoints']['4']['early_finished'] == 1
    assert aggregate['overall']['checkpoints']['4']['own_team_fainted']['n'] == 0


def test_checkpoint_skips_continuations_and_waits_then_reports_actual_overshoot():
    continuation, waiting = snapshot(4), snapshot(5)
    continuation['request']['forceSwitch'] = [True]
    waiting['request']['wait'] = True
    result = analyze_trace([preview(), snapshot(1), continuation, waiting, snapshot(6)], game=game(), role='a')
    assert result['checkpoints']['4']['actual_request_turn'] == 6
    assert result['checkpoints']['4']['overshoot_turns'] == 2
    assert result['checkpoints']['6']['actual_request_turn'] == 6


def test_later_tera_does_not_leak_back_and_confirmed_spent_tera_survives_blank_request_slots():
    result = analyze_trace([preview(), snapshot(1), snapshot(4), snapshot(6, tera=True)], game=game(), role='a')
    assert result['checkpoints']['4']['own_tera_used'] is False
    assert result['checkpoints']['6']['own_tera_used'] is True
    data = [preview(), snapshot(1), snapshot(4, faint_lead=True, active='p1: Great Tusk', tera=True)]
    assert not any(mon['terastallized'] for mon in data[-1]['request']['side']['pokemon'])
    assert analyze_trace(data, game=game(), role='a')['checkpoints']['4']['own_tera_used'] is True


def test_opposing_hp_is_only_a_labelled_public_proxy():
    data = [preview(), snapshot(1), snapshot(4)]
    for mon in data[-1]['state']['sides']['p2']['pokemon']:
        mon['hp_percent'] = 50
    point = analyze_trace(data, game=game(), role='a')['checkpoints']['4']
    assert point['opponent_public_hp_fraction_proxy'] == 3
    assert 'Regenerator' in point['opponent_proxy_note']


def test_preview_attempt_and_confirmed_actual_lead_are_separate():
    data = [preview(), snapshot(1, active='p1: Great Tusk'), snapshot(4)]
    result = analyze_trace(data, game=game(), role='a')
    assert result['selected_lead']['preview_slot'] == 3
    assert result['actual_lead']['preview_slot'] == 2
    assert result['preview_choice_matches_observed_lead'] is False


def test_missing_turn1_keeps_selected_lead_but_does_not_invent_actual_lead():
    result = analyze_trace([preview(), snapshot(4)], game=game(), role='a')
    assert result['selected_lead']['preview_slot'] == 3
    assert result['actual_lead'] is None and result['actual_lead_disagrees'] is None
    assert result['checkpoints']['4']['own_lead_fainted'] is None
    assert result['checkpoints']['4']['own_hp_fraction_sum'] is not None


def test_hp_measurement_does_not_require_private_pp_or_move_details():
    data = [preview(), snapshot(1), snapshot(4)]
    data[-1]['request']['active'] = [{}]
    point = analyze_trace(data, game=game(), role='a')['checkpoints']['4']
    assert point['own_hp_fraction_sum'] == pytest.approx(5.75)


def test_cli_writes_both_roles_breakdowns_csv_and_missing_trace_counts_without_team_file_access(tmp_path):
    trace = tmp_path / 'a.jsonl'
    trace.write_text(''.join(json.dumps(row) + '\n' for row in rows()))
    games = tmp_path / 'games.jsonl'
    games.write_text(json.dumps(game(artifacts={'a': {'trace': str(trace)}, 'b': {'trace': str(tmp_path / 'missing.jsonl')}})) + '\n')
    manifest = tmp_path / 'manifest.json'
    manifest.write_text(json.dumps({'teams': [{'id': 'offense-team', 'style': 'offense', 'sha256': 'a', 'path': '/never/read/own-team.txt'},
                                             {'id': 'balance-team', 'style': 'balance', 'sha256': 'b', 'path': '/never/read/opponent-team.txt'}]}))
    plan = tmp_path / 'plan.json'
    freeze_plan(plan)
    args = argparse.Namespace(plan=plan, games=games, manifest=manifest, output=tmp_path / 'result.json',
                              raw_output=tmp_path / 'records.json', csv=tmp_path / 'records.csv')
    run(args)
    result = json.loads(args.output.read_text())
    records = json.loads(args.raw_output.read_text())
    assert len(records) == 2 and result['provenance']['perspectives'] == 2
    assert records[1]['trace_status'] == 'missing_trace'
    assert records[1]['checkpoints']['4']['own_team_fainted'] is None
    assert 'a|offense' in result['by_role_style'] and 'b|balance' in result['by_role_style']
    with args.csv.open() as handle:
        csv_rows = list(csv.DictReader(handle))
    assert len(csv_rows) == 2 and csv_rows[0]['actual_lead_species'] == 'gholdengo'


def test_censored_record_is_not_claimed_to_have_ended_early():
    result = analyze_trace([preview(), snapshot(1)], game=game(turns=2, turn_limit_censored=True), role='a')
    assert result['checkpoints']['4']['status'] == 'missing_future_state'
    assert result['checkpoints']['4']['early_finished'] is False


def test_valid_both_role_sides_resolve_private_lead_identity_and_missing_trace_keeps_scheduled_side():
    b_rows = copy.deepcopy(rows())
    for row in b_rows:
        row['request']['side']['id'] = 'p2'
        for mon in row['request']['side']['pokemon']:
            mon['ident'] = mon['ident'].replace('p1:', 'p2:')
        row['state']['us'] = 'p2'
        sides = row['state']['sides']
        sides['p1'], sides['p2'] = sides['p2'], sides['p1']
    a = analyze_trace(rows(), game=game(a_side='p1'), role='a')
    b = analyze_trace(b_rows, game=game(a_side='p1'), role='b')
    assert a['side'] == 'p1' and b['side'] == 'p2'
    assert a['side_identity_matches'] is True and b['side_identity_matches'] is True
    assert b['actual_lead']['ident'] == 'p2: Gholdengo'
    assert b['checkpoints']['4']['own_hp_sum'] == a['checkpoints']['4']['own_hp_sum']
    assert b['checkpoints']['4']['own_lead_fainted'] is True
    missing = analyze_trace([], game=game(a_side='p1'), role='b', trace_status='missing_trace')
    assert missing['side'] == 'p2' and missing['observed_side'] is None


@pytest.mark.parametrize('mismatch', ['source', 'side'])
def test_cli_rejects_mismatched_effective_source_or_scheduled_side(tmp_path, mismatch):
    trace = tmp_path / 'trace.jsonl'
    trace.write_text(''.join(json.dumps(row) + '\n' for row in rows()))
    games = tmp_path / 'games.jsonl'
    games.write_text(json.dumps(game(a_side='p2' if mismatch == 'side' else 'p1',
                                    source_sha256={'a': 'wrong' if mismatch == 'source' else 'expected'},
                                    artifacts={'a': {'trace': str(trace)}})) + '\n')
    manifest = tmp_path / 'manifest.json'
    manifest.write_text(json.dumps({'a': {'source_sha256': 'expected'}}))
    plan = tmp_path / 'plan.json'
    freeze_plan(plan)
    args = argparse.Namespace(plan=plan, games=games, manifest=manifest, output=tmp_path / 'result.json',
                              raw_output=tmp_path / 'records.json', csv=tmp_path / 'records.csv')
    with pytest.raises(ValueError, match='source|side'):
        run(args)
    assert not args.output.exists()
