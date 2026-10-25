"""Native-root integration checks: legality, resources and future-turn state survive conversion."""
import copy

from poke_engine import monte_carlo_tree_search

from bot.parser import Parser
from decision.actions import Action, our_actions
from decision.adapter import adapter_diagnostics, build_state
from tests.turn2 import EXAMPLE, REQUEST, SETS


def choices(state):
    # Test supported root actions, not nondeterministic visit shares.
    result = monte_carlo_tree_search(state, iterations=30, threads=1)
    return {row.move_choice for row in result.side_one}, {row.move_choice for row in result.side_two}


def test_native_root_respects_request_pp_disabled_and_trapping():
    request = copy.deepcopy(REQUEST)
    request['active'][0].update(trapped=True)
    request['active'][0]['moves'][0]['disabled'] = True
    request['active'][0]['moves'][1]['pp'] = 0
    state = build_state(request, EXAMPLE, SETS)
    ours, _ = choices(state)
    assert ours == {'suckerpunch', 'suckerpunch-tera', 'ironhead', 'ironhead-tera'}
    assert not any(action.kind == 'switch' for action in our_actions(request))
    assert Action('move', 2) not in our_actions(request)


def test_choice_and_encore_apply_to_opponent_native_actions():
    battle = copy.deepcopy(EXAMPLE)
    battle['sides']['p2']['pokemon'][2]['terastallized'] = False
    battle['sides']['p2']['tera_used'] = False
    side = battle['sides']['p2']
    side['last_move'] = 'makeitrain'
    # SETS[2] is Choice Scarf. Disable its other moves in the native state as well as the Python action list.
    state = build_state(REQUEST, battle, SETS)
    _, theirs = choices(state)
    assert not ({'shadowball', 'nastyplot', 'recover'} & theirs)
    assert {'makeitrain', 'makeitrain-tera'} <= theirs
    side['volatiles'] = ['encore']
    side['volatile_turns'] = {'encore': 1}
    state = build_state(REQUEST, battle, SETS)
    assert state.side_two.last_used_move == 'move:0'
    assert state.side_two.volatile_status_durations.encore == 1
    _, theirs = choices(state)
    assert not ({'shadowball', 'nastyplot', 'recover'} & theirs)


def test_native_forced_replacement_and_request_order():
    request = copy.deepcopy(REQUEST)
    request['forceSwitch'] = [True]
    request.pop('active')
    request['side']['pokemon'][0]['condition'] = '0 fnt'
    # A switch's native species maps to its position in this request, not preview position.
    request['side']['pokemon'][1], request['side']['pokemon'][4] = request['side']['pokemon'][4], request['side']['pokemon'][1]
    state = build_state(request, EXAMPLE, SETS)
    ours, theirs = choices(state)
    assert state.side_one.force_switch
    assert theirs == {'No Move'}
    assert ours == {f'switch {mon.id}' for mon in state.side_one.pokemon[1:] if mon.hp > 0}
    assert state.side_one.pokemon[1].id == 'corviknight'


def test_native_living_pivot_replacement_is_supported():
    request = copy.deepcopy(REQUEST)
    request['forceSwitch'] = [True]
    request.pop('active')
    ours, theirs = choices(build_state(request, EXAMPLE, SETS))
    assert all(choice.startswith('switch ') for choice in ours)
    assert theirs == {'No Move'}


def test_fainted_benched_tera_user_still_spends_team_resource():
    request = copy.deepcopy(REQUEST)
    request['side']['pokemon'][3].update(condition='0 fnt', terastallized='Ghost')
    state = build_state(request, EXAMPLE, SETS)
    assert state.side_one.pokemon[3].id == 'dragapult'
    assert state.side_one.pokemon[3].terastallized
    ours, _ = choices(state)
    assert not any(choice.endswith('-tera') for choice in ours)
    battle = copy.deepcopy(EXAMPLE)
    battle['sides']['p2']['pokemon'][2]['hp_percent'] = 0
    battle['sides']['p2']['active'] = 0
    _, theirs = choices(build_state(request, battle, SETS))
    assert not any(choice.endswith('-tera') for choice in theirs)


def test_force_switch_false_is_not_a_replacement_request():
    request = copy.deepcopy(REQUEST)
    request['forceSwitch'] = [False]
    assert any(action.kind == 'move' for action in our_actions(request))
    assert not build_state(request, EXAMPLE, SETS).side_one.force_switch


def test_delayed_effects_and_estimates_are_preserved_across_switch_and_upkeep():
    parser = Parser()
    for line in [
        '|poke|p1|Kingambit', '|poke|p1|Great Tusk', '|poke|p2|Gholdengo',
        '|switch|p1a: King|Kingambit|100/100', '|switch|p2a: Gold|Gholdengo|100/100',
        '|move|p1a: King|Wish|p1a: King', '|move|p2a: Gold|Future Sight|p1a: King',
        '|-start|p1a: King|move: Future Sight', '|upkeep',
        '|switch|p1a: Tusk|Great Tusk|100/100',
        '|-start|p1a: Tusk|Substitute', '|-start|p1a: Tusk|Taunt',
    ]:
        parser.feed(line)
    battle = parser.snapshot()
    assert battle['sides']['p1']['wish'] == {'turns': 1, 'source': 0}
    assert battle['sides']['p2']['future_sight'] == {'turns': 1, 'source': 0}
    # Reuse full fixture teams, copying extension fields from the replay fragment.
    full = copy.deepcopy(EXAMPLE)
    full['sides']['p1'].update(wish=battle['sides']['p1']['wish'],
                               volatiles=['substitute', 'taunt'], volatile_turns={'taunt': 1})
    full['sides']['p2']['future_sight'] = {'turns': 1, 'source': 2}
    state = build_state(REQUEST, full, SETS)
    assert state.side_one.wish == (1, state.side_one.pokemon[0].maxhp // 2)
    assert state.side_two.future_sight == (2, '2')
    assert state.side_one.volatile_status_durations.taunt == 1
    assert state.side_one.substitute_health == state.side_one.pokemon[0].maxhp // 4
    fields = {row['field'] for row in adapter_diagnostics(REQUEST, full)}
    assert {'wish_hp', 'substitute_hp', 'our_bench_pp', 'opponent_pp', 'taunt'} <= fields
    parser.feed('|upkeep')
    assert 'wish' not in parser.snapshot()['sides']['p1']
    parser.feed('|-end|p1a: Tusk|move: Future Sight')
    assert 'future_sight' not in parser.snapshot()['sides']['p2']


def test_known_delayed_hp_and_substitute_hp_override_estimates():
    battle = copy.deepcopy(EXAMPLE)
    side = battle['sides']['p1']
    side.update(wish={'turns': 1, 'source': 0, 'hp': 123}, volatiles=['substitute'], substitute_hp=23)
    state = build_state(REQUEST, battle, SETS)
    assert state.side_one.wish == (1, 123)
    assert state.side_one.substitute_health == 23
    assert not {'wish_hp', 'substitute_hp'} & {row['field'] for row in adapter_diagnostics(REQUEST, battle)}


def test_parser_failed_delayed_move_does_not_create_pending_effect():
    parser = Parser()
    for line in ['|poke|p1|Kingambit', '|switch|p1a: King|Kingambit|100/100',
                 '|move|p1a: King|Wish|p1a: King', '|-fail|p1a: King']:
        parser.feed(line)
    assert 'wish' not in parser.snapshot()['sides']['p1']


def test_legacy_hp_colour_and_tera_details_are_retained():
    parser = Parser()
    for line in ['|poke|p1|Kingambit', '|switch|p1a: King|Kingambit, tera:Dark|20/100y']:
        parser.feed(line)
    side = parser.snapshot()['sides']['p1']
    assert side['pokemon'][0]['hp_percent'] == 20
    assert side['tera_used'] and side['pokemon'][0]['terastallized']


def test_observed_sleep_attempts_and_rest_counters_do_not_advance_on_upkeep():
    parser = Parser()
    for line in ['|poke|p1|Kingambit', '|switch|p1a: King|Kingambit|100/100',
                 '|move|p1a: King|Rest|p1a: King', '|-status|p1a: King|slp|[from] move: Rest',
                 '|upkeep', '|cant|p1a: King|slp', '|upkeep']:
        parser.feed(line)
    observed = parser.snapshot()['sides']['p1']
    assert observed['pokemon'][0]['sleep_turns'] == 1
    assert observed['pokemon'][0]['rest_turns'] == 2
    assert observed['pokemon'][0]['status_turns'] == 2
    from decision.state import our_side
    request = copy.deepcopy(REQUEST)
    request['side']['pokemon'][0]['condition'] = '300/400 slp'
    king = our_side(request, observed).pokemon[0]
    assert (king.sleep_turns, king.rest_turns) == (1, 2)
    parser.feed('|-curestatus|p1a: King|slp')
    assert 'sleep_turns' not in parser.snapshot()['sides']['p1']['pokemon'][0]


def test_native_taunt_and_yawn_counters_use_elapsed_not_remaining_turns():
    from decision.simulate import simulate
    battle = copy.deepcopy(EXAMPLE)
    battle['sides']['p1']['volatiles'] = ['taunt', 'yawn']
    battle['sides']['p1']['volatile_turns'] = {'taunt': 0, 'yawn': 1}
    state = build_state(REQUEST, battle, SETS)
    assert state.side_one.volatile_status_durations.taunt == 0
    assert state.side_one.volatile_status_durations.yawn == 1
    # A mistaken remaining-duration value of 3 (Taunt) or 2 (Yawn) panics in native generate_instructions.
    outcomes = simulate(state, Action('move', 4), Action('move', 1))
    assert outcomes
    assert any(next_state.side_one.pokemon[0].status.lower() == 'sleep' for _, next_state in outcomes)


def test_delayed_effect_native_simulation_counts_down_and_wish_heals():
    from poke_engine import generate_instructions
    battle = copy.deepcopy(EXAMPLE)
    battle['sides']['p1']['wish'] = {'turns': 1, 'source': 0, 'hp': 40}
    battle['sides']['p2']['future_sight'] = {'turns': 1, 'source': 2}
    state = build_state(REQUEST, battle, SETS)
    outcome = generate_instructions(state, 'none', 'none')[0]
    next_state = state.apply_instructions(outcome)
    assert next_state.side_one.wish[0] == 0
    assert next_state.side_one.pokemon[0].hp > state.side_one.pokemon[0].hp
    assert next_state.side_two.future_sight == (1, '2')
    later = next_state.apply_instructions(generate_instructions(next_state, 'none', 'none')[0])
    assert later.side_two.future_sight[0] == 0


def test_simulator_generated_replay_matches_native_delayed_side_and_timing():
    import json
    from pathlib import Path
    from bot.parser import states_from_log
    from tests.turn2 import guess
    fixtures = Path(__file__).parent / 'fixtures'
    states = states_from_log((fixtures / 'delayed_effects_showdown.log').read_text().splitlines())
    turn3 = next(state for state in states if state['turn'] == 3)
    assert turn3['sides']['p1']['future_sight'] == {'turns': 2, 'source': 0}
    assert turn3['sides']['p1']['wish'] == {'turns': 1, 'source': 0}
    assert 'future_sight' not in turn3['sides']['p2']
    request = json.loads((fixtures / 'delayed_effects_turn3_request.json').read_text())
    state = build_state(request, turn3, [guess('tackle', item='none', ability='none')])
    assert state.side_one.future_sight == (1, '0')
    assert state.side_one.wish == (1, state.side_one.pokemon[0].maxhp // 2)
    assert state.side_two.future_sight == (0, '0')
    turn4 = next(state for state in states if state['turn'] == 4)
    assert 'future_sight' not in turn4['sides']['p1']
    assert 'wish' not in turn4['sides']['p1']
    assert turn4['sides']['p1']['active'] == 1  # Wish survives the source's switch.
    assert turn4['sides']['p1']['pokemon'][1]['hp_percent'] == 100
    assert turn4['sides']['p2']['pokemon'][0]['hp_percent'] < 100  # Future Sight damaged the other side.
