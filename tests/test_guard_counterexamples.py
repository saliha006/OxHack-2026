"""Concrete mechanics counterexamples to broad strategic vetoes; no guard is enabled."""
from poke_engine import Move, Pokemon, Side, State

from decision.actions import Action
from decision.opponent import MOVES
from decision.sets import PokemonSet, stats
from decision.simulate import simulate
from decision.state import DEX


def pokemon(species, moves, ability, *, item='none', evs=(0, 0, 0, 0, 0, 0), nature='serious',
            ivs=(31, 31, 31, 31, 31, 31), hp=None):
    """Use actual DEX-derived stats, legal named moves and ordinary full/base PP."""
    estimated = PokemonSet(tuple(moves), item, ability, 'normal', nature, evs, ivs)
    maxhp, attack, defense, special_attack, special_defense, speed = stats(species, 100, estimated)
    types = tuple(t.lower() for t in DEX[species]['types'])
    types += ('typeless',) * (2 - len(types))
    return Pokemon(id=species, level=100, types=types, base_types=types, hp=maxhp if hp is None else hp,
                   maxhp=maxhp, attack=attack, defense=defense, special_attack=special_attack,
                   special_defense=special_defense, speed=speed, ability=ability, item=item,
                   weight_kg=DEX[species]['weightkg'], moves=[Move(id=move, pp=MOVES[move]['pp']) for move in moves])


def test_full_hp_slow_recovery_heals_damage_taken_before_its_action():
    ours = pokemon('toxapex', ['recover', 'toxic'], 'regenerator', evs=(252, 0, 252, 0, 4, 0),
                   nature='relaxed', ivs=(31, 31, 31, 31, 31, 0))
    foe = pokemon('snorlax', ['tackle'], 'thickfat', evs=(252, 252, 0, 0, 4, 0), nature='adamant')
    assert ours.speed < foe.speed and ours.hp == ours.maxhp
    state = State(side_one=Side(pokemon=[ours]), side_two=Side(pokemon=[foe]))
    recovery = simulate(state, Action('move', 1), Action('move', 1))
    without = simulate(state, Action('move', 2), Action('move', 1))
    assert all(after.side_one.pokemon[0].hp == ours.maxhp for _, after in recovery)
    assert all(after.side_one.pokemon[0].hp < ours.maxhp for _, after in without)


def test_protect_blocks_damage_and_can_gain_residual_recovery():
    ours = pokemon('blissey', ['protect'], 'naturalcure', item='leftovers',
                   evs=(252, 0, 252, 0, 4, 0), nature='bold', hp=500)
    foe = pokemon('snorlax', ['tackle'], 'thickfat', evs=(252, 252, 0, 0, 4, 0), nature='adamant')
    state = State(side_one=Side(pokemon=[ours]), side_two=Side(pokemon=[foe]))
    outcomes = simulate(state, Action('move', 1), Action('move', 1))
    assert all(after.side_one.pokemon[0].hp == ours.hp + ours.maxhp // 16 for _, after in outcomes)


def test_current_immunity_does_not_make_attack_useless_against_a_switch():
    ours = pokemon('gengar', ['shadowball'], 'cursedbody', evs=(0, 0, 0, 252, 4, 252), nature='timid')
    normal = pokemon('snorlax', ['tackle'], 'thickfat')
    reserve = pokemon('toxapex', ['recover'], 'regenerator')
    state = State(side_one=Side(pokemon=[ours]), side_two=Side(pokemon=[normal, reserve]))
    stays = simulate(state, Action('move', 1), Action('move', 1))
    switches = simulate(state, Action('move', 1), Action('switch', 2))
    assert all(after.side_two.pokemon[0].hp == normal.maxhp for _, after in stays)
    assert all(after.side_two.pokemon[1].hp < reserve.maxhp for _, after in switches)


def test_switch_can_regenerate_and_receive_a_ground_attack_with_immunity():
    ours = pokemon('toxapex', ['recover'], 'regenerator', hp=60)
    reserve = pokemon('corviknight', ['roost'], 'pressure')
    foe = pokemon('garchomp', ['earthquake'], 'roughskin', evs=(0, 252, 0, 0, 4, 252), nature='jolly')
    state = State(side_one=Side(pokemon=[ours, reserve]), side_two=Side(pokemon=[foe]))
    outcomes = simulate(state, Action('switch', 2), Action('move', 1))
    assert all(after.side_one.pokemon[0].hp > ours.hp for _, after in outcomes)
    assert all(after.side_one.pokemon[1].hp == reserve.maxhp for _, after in outcomes)
    assert all(after.side_one.active_index == '1' for _, after in outcomes)
