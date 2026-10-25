"""Public protocol / private request transitions reproduced before the stage-1 fixes."""
import copy
import json
from pathlib import Path

from bot.parser import Parser
from decision.adapter import adapter_diagnostics, build_state
from decision.state import our_side
from tests.turn2 import EXAMPLE, REQUEST, SETS


def parser_with_request(request):
    parser = Parser(request['side']['id'])
    for mon in request['side']['pokemon']:
        parser.feed(f"|poke|p1|{mon['details']}")
    parser.feed('|poke|p2|Corviknight')
    parser.feed('|switch|p1a: Kingambit|Kingambit|300/400')
    parser.feed('|switch|p2a: Raven|Corviknight|100/100')
    parser.feed('|request|' + json.dumps(request))
    return parser


def switched_request(request):
    request = copy.deepcopy(request)
    request['side']['pokemon'][0]['active'] = False
    request['side']['pokemon'][1]['active'] = True
    request.pop('active', None)
    request['forceSwitch'] = [True]
    # Request slots can move; remembered PP must follow identity rather than slot.
    request['side']['pokemon'][0], request['side']['pokemon'][4] = (
        request['side']['pokemon'][4], request['side']['pokemon'][0])
    return request


def test_remembered_pp_follows_benched_identity_and_move_id():
    request = copy.deepcopy(REQUEST)
    request['active'][0]['moves'][1]['pp'] = 0
    parser = parser_with_request(request)
    later = switched_request(request)
    side = our_side(later, parser.snapshot()['sides']['p1'])
    king = next(mon for mon in side.pokemon if mon.id == 'kingambit')
    assert {move.id: move.pp for move in king.moves}['kowtowcleave'] == 0


def test_pp_spend_before_pivot_is_estimated_then_exact_request_overrides():
    request = copy.deepcopy(REQUEST)
    request['active'][0]['moves'][1]['pp'] = 5
    parser = parser_with_request(request)
    parser.feed('|-ability|p2a: Raven|Pressure')
    parser.feed('|move|p1a: Kingambit|Kowtow Cleave|p2a: Raven')
    observed = parser.snapshot()['sides']['p1']['pokemon'][0]
    assert observed['move_pp']['kowtowcleave']['pp'] == 3
    assert observed['move_pp']['kowtowcleave']['certainty'] == 'estimated'
    request['active'][0]['moves'][1]['pp'] = 4
    parser.feed('|request|' + json.dumps(request))
    observed = parser.snapshot()['sides']['p1']['pokemon'][0]
    assert observed['move_pp']['kowtowcleave']['pp'] == 4
    assert observed['move_pp']['kowtowcleave']['certainty'] == 'exact'


def test_called_and_locked_moves_do_not_spend_remembered_pp():
    parser = parser_with_request(copy.deepcopy(REQUEST))
    parser.feed('|move|p1a: Kingambit|Kowtow Cleave|p2a: Raven|[from] move: Sleep Talk')
    parser.feed('|move|p1a: Kingambit|Kowtow Cleave|p2a: Raven|[from] lockedmove')
    state = parser.snapshot()
    assert state['sides']['p1']['pokemon'][0]['move_pp']['kowtowcleave']['pp'] == 16
    assert [event['source'] for event in state['last_turn'] if event['type'] == 'move'] == [
        'move:sleeptalk', 'lockedmove']


def test_pp_restoration_invalidates_remembered_amount_until_next_request():
    parser = parser_with_request(copy.deepcopy(REQUEST))
    parser.feed('|-enditem|p1a: Kingambit|Leppa Berry|[eat]')
    assert 'move_pp' not in parser.snapshot()['sides']['p1']['pokemon'][0]


def test_fainted_own_maxhp_is_remembered_from_request():
    request = copy.deepcopy(REQUEST)
    parser = parser_with_request(request)
    request = switched_request(request)
    king = next(mon for mon in request['side']['pokemon'] if mon['ident'] == 'p1: Kingambit')
    king['condition'] = '0 fnt'
    native = our_side(request, parser.snapshot()['sides']['p1'])
    assert next(mon for mon in native.pokemon if mon.id == 'kingambit').maxhp == 400


def test_successful_protect_streak_is_retained_and_nonprotect_turn_resets():
    parser = parser_with_request(copy.deepcopy(REQUEST))
    for turn in (1, 2):
        parser.feed(f'|turn|{turn}')
        parser.feed('|move|p1a: Kingambit|Protect|p1a: Kingambit')
        parser.feed('|-singleturn|p1a: Kingambit|Protect')
        parser.feed('|upkeep')
    battle = copy.deepcopy(EXAMPLE)
    battle['sides']['p1']['protect_streak'] = parser.snapshot()['sides']['p1']['protect_streak']
    assert build_state(REQUEST, battle, SETS).side_one.side_conditions.protect == 2
    parser.feed('|turn|3')
    parser.feed('|move|p1a: Kingambit|Iron Head|p2a: Raven')
    parser.feed('|upkeep')
    assert parser.snapshot()['sides']['p1']['protect_streak'] == 0


def test_failed_protect_and_switch_reset_streak():
    parser = parser_with_request(copy.deepcopy(REQUEST))
    parser.feed('|move|p1a: Kingambit|Protect|p1a: Kingambit')
    parser.feed('|-singleturn|p1a: Kingambit|Protect')
    parser.feed('|upkeep')
    parser.feed('|move|p1a: Kingambit|Protect|p1a: Kingambit')
    parser.feed('|-fail|p1a: Kingambit')
    assert parser.snapshot()['sides']['p1']['protect_streak'] == 0
    parser.feed('|-singleturn|p1a: Kingambit|Protect')
    parser.feed('|switch|p1a: Tusk|Great Tusk|380/380')
    assert parser.snapshot()['sides']['p1']['protect_streak'] == 0


def test_still_visible_extended_effects_are_not_removed_at_default_expiry():
    battle = copy.deepcopy(EXAMPLE)
    battle['sides']['p1']['side_effects']['reflect'] = 6
    battle['field'].update(weather='raindance', weather_turns=6,
                          terrain='electricterrain', terrain_turns=6)
    state = build_state(REQUEST, battle, SETS)
    assert state.side_one.side_conditions.reflect == 1
    assert state.weather_turns_remaining == 1
    assert state.terrain_turns_remaining == 1


def test_diagnostics_separate_request_pp_from_remembered_and_estimated():
    parser = parser_with_request(copy.deepcopy(REQUEST))
    request = switched_request(copy.deepcopy(REQUEST))
    records = adapter_diagnostics(request, {'us': 'p1', **parser.snapshot()})
    king_records = [row for row in records if row.get('species') == 'kingambit' and row['field'] == 'move_pp']
    assert king_records and {row['certainty'] for row in king_records} == {'remembered'}


def test_continuation_does_not_claim_a_completed_turn():
    parser = parser_with_request(copy.deepcopy(REQUEST))
    parser.feed('|upkeep')
    assert parser.snapshot()['last_turn_complete'] is True
    parser.feed('|move|p1a: Kingambit|U-turn|p2a: Raven')
    assert parser.snapshot()['last_turn_complete'] is False


def test_null_final_request_is_harmless():
    parser = parser_with_request(copy.deepcopy(REQUEST))
    parser.feed('|request|null')
    assert parser.snapshot()['sides']['p1']['pokemon'][0]['move_pp']['kowtowcleave']['pp'] == 16


def test_simulator_generated_protect_and_pivot_requests_match_native_state():
    from tests.turn2 import guess

    fixture = json.loads((Path(__file__).parent / 'fixtures' / 'state_reconstruction_showdown.json').read_text())
    parser = Parser()
    for frame in fixture['frames']:
        for line in frame['protocol']:
            parser.feed(line)
        parser.feed('|request|' + json.dumps(frame['request']))
        battle = parser.snapshot()
        state = build_state(frame['request'], battle, [guess('splash', ability='naturalcure', item='none')])
        ours = state.side_one
        assert ours.pokemon[int(ours.active_index)].id == frame['expected']['active'], frame['label']
        assert ours.side_conditions.protect == frame['expected']['protect_streak'], frame['label']
        # Only Corviknight has supplied active PP. Never-seen Kingambit PP is estimated.
        corviknight = next(mon for mon in ours.pokemon if mon.id == 'corviknight')
        assert {move.id: move.pp for move in corviknight.moves} == frame['expected']['own_pp']['corviknight'], frame['label']
        if frame['request'].get('forceSwitch'):
            assert battle['last_turn_complete'] is False
            assert ours.force_switch
            assert ours.switch_out_move_second_saved_move == 'none'  # hidden future action is never invented
