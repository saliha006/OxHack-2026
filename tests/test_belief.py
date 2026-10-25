import copy
import math

import pytest

from decision.belief import Belief, sets_from_game
from tests.turn2 import EXAMPLE

SPREAD = {"nature": "serious", "evs": [84] * 6}


def cand(weight, moves, item="leftovers", ability="pressure", tera="normal"):
    return {"weight": weight, "moves": moves, "item": item, "ability": ability, "tera_type": tera, "spread": SPREAD}


def usage(moves, items, teras=("normal",), ability="pressure"):
    share = lambda xs: {x: round(1 / len(xs), 3) for x in xs}
    return {"moves": {m: 4 / len(moves) for m in moves}, "items": share(items), "abilities": {ability: 1.0},
            "tera_types": share(teras), "spreads": [[SPREAD, 1.0]]}


def filler(species):
    return {"sets": [cand(1.0, ["tackle"])], "usage": usage(["tackle"], ["leftovers"])}


GHOLDENGO = {
    "sets": [
        cand(0.5, ["makeitrain", "shadowball", "trick", "focusblast"], item="choicescarf", ability="goodasgold", tera="steel"),
        cand(0.3, ["nastyplot", "shadowball", "makeitrain", "recover"], item="airballoon", ability="goodasgold", tera="fairy"),
        cand(0.2, ["nastyplot", "shadowball", "makeitrain", "recover"], item="leftovers", ability="goodasgold", tera="steel"),
    ],
    "usage": usage(["makeitrain", "shadowball", "nastyplot", "recover", "trick", "focusblast"],
                   ["choicescarf", "airballoon", "leftovers", "assaultvest"], teras=("steel", "fairy"), ability="goodasgold"),
}
DRAGONITE = {
    "sets": [
        cand(0.6, ["extremespeed", "earthquake", "dragondance", "roost"], item="heavydutyboots", ability="multiscale"),
        cand(0.4, ["extremespeed", "earthquake", "dragondance", "roost"], item="leftovers", ability="multiscale"),
    ],
    "usage": usage(["extremespeed", "earthquake", "dragondance", "roost"], ["heavydutyboots", "leftovers"], ability="multiscale"),
}
PRIORS = {"source": {"format": "gen9ou", "month": "2026-09", "cutoff": 1825, "battles": 1},
          "species": {"dragonite": DRAGONITE, "samurotthisui": filler("samurotthisui"), "gholdengo": GHOLDENGO,
                      "pecharunt": filler("pecharunt"), "walkingwake": filler("walkingwake"), "tinglu": filler("tinglu")}}


@pytest.fixture
def battle():
    return copy.deepcopy(EXAMPLE)


def turn(battle, events, **side):
    """The next turn's BattleState: Bob's side updated, last_turn replaced."""
    battle = copy.deepcopy(battle)
    battle["turn"] += 1
    battle["sides"]["p2"].update(side)
    battle["last_turn"] = events
    return battle


def event(type_, pokemon, **kw):
    base = {"type": type_, "side": "p2", "pokemon": pokemon, "move": None, "target": None, "hp_percent": None,
            "source": None, "crit": False, "effectiveness": None, "reason": None}
    return {**base, **kw}


def weights(belief, slot):
    return [round(w, 6) for _, w in belief.candidates[slot]]


def items(belief, slot):
    return [s.item for s, _ in belief.candidates[slot]]


def test_priors_load_per_opponent_slot(battle):
    belief = Belief(PRIORS, battle)
    assert len(belief.candidates) == 6
    assert weights(belief, 0) == [0.6, 0.4]


def test_revealed_moves_item_ability_and_tera_filter(battle):
    belief = Belief(PRIORS, battle)  # the example already shows Make It Rain + Tera Steel
    belief.update(battle)
    assert items(belief, 2) == ["choicescarf", "leftovers"]
    assert math.isclose(sum(w for _, w in belief.candidates[2]), 1.0)
    assert weights(belief, 2) == [round(0.5 / 0.7, 6), round(0.2 / 0.7, 6)]


def test_revealed_item(battle):
    belief = Belief(PRIORS, battle)
    battle["sides"]["p2"]["pokemon"][2]["item"] = "leftovers"
    belief.update(battle)
    assert items(belief, 2) == ["leftovers"]


def test_known_no_item_does_not_filter(battle):
    # "" can mean it was knocked off, so it says nothing about the original item.
    belief = Belief(PRIORS, battle)
    battle["sides"]["p2"]["pokemon"][2]["item"] = ""
    belief.update(battle)
    assert items(belief, 2) == ["choicescarf", "leftovers"]


def test_two_different_moves_without_switching_rules_out_choice(battle):
    belief = Belief(PRIORS, battle)
    belief.update(battle)  # turn 1: Make It Rain
    belief.update(turn(battle, [event("move", 2, move="shadowball", target="p1")]))
    assert items(belief, 2) == ["leftovers"]


def test_switching_resets_the_moves_seen(battle):
    belief = Belief(PRIORS, battle)
    belief.update(battle)
    belief.update(turn(battle, [event("switch", 2), event("move", 2, move="shadowball", target="p1")]))
    assert items(belief, 2) == ["choicescarf", "leftovers"]


def test_damaged_without_a_leftovers_heal_rules_out_leftovers(battle):
    belief = Belief(PRIORS, battle)
    belief.update(battle)
    battle["sides"]["p2"]["pokemon"][2]["hp_percent"] = 70
    belief.update(turn(battle, [event("damage", 2, hp_percent=70, source="move")]))
    assert items(belief, 2) == ["choicescarf"]


def test_a_leftovers_heal_keeps_leftovers(battle):
    belief = Belief(PRIORS, battle)
    belief.update(battle)
    battle["sides"]["p2"]["pokemon"][2]["hp_percent"] = 76
    belief.update(turn(battle, [event("damage", 2, hp_percent=70, source="move"),
                                event("heal", 2, hp_percent=76, source="item:leftovers")]))
    assert items(belief, 2) == ["leftovers"]  # healed, so it really is Leftovers


def test_switching_into_rocks_without_damage_means_boots(battle):
    battle["sides"]["p2"]["hazards"]["stealthrock"] = 1
    belief = Belief(PRIORS, battle)
    belief.update(battle)
    belief.update(turn(battle, [event("switch", 0)], active=0))
    assert items(belief, 0) == ["heavydutyboots"]


def test_rock_damage_on_switch_in_rules_out_boots(battle):
    battle["sides"]["p2"]["hazards"]["stealthrock"] = 1
    belief = Belief(PRIORS, battle)
    belief.update(battle)
    belief.update(turn(battle, [event("switch", 0), event("damage", 0, hp_percent=88, source="stealthrock")], active=0))
    assert items(belief, 0) == ["leftovers"]


def test_a_status_move_rules_out_assault_vest(battle):
    priors = copy.deepcopy(PRIORS)
    priors["species"]["gholdengo"]["sets"] = [
        cand(0.5, ["makeitrain", "shadowball", "focusblast", "nastyplot"], item="leftovers", ability="goodasgold", tera="steel"),
        cand(0.5, ["makeitrain", "shadowball", "focusblast", "nastyplot"], item="assaultvest", ability="goodasgold", tera="steel"),
    ]
    belief = Belief(priors, battle)
    belief.update(battle)
    belief.update(turn(battle, [event("move", 2, move="nastyplot", target="p2")]))
    assert items(belief, 2) == ["leftovers"]


def test_nothing_left_rebuilds_from_usage(battle):
    belief = Belief(PRIORS, battle)
    battle["sides"]["p2"]["pokemon"][2]["revealed_moves"] = ["makeitrain", "focusblast", "recover"]
    belief.update(battle)
    rebuilt = belief.candidates[2]
    assert rebuilt
    assert all({"makeitrain", "focusblast", "recover"} <= set(s.moves) and s.tera_type == "steel" for s, _ in rebuilt)
    # A Choice item or Assault Vest can't run Recover (a status move).
    assert {s.item for s, _ in rebuilt} == {"airballoon", "leftovers"}
    assert math.isclose(sum(w for _, w in rebuilt), 1.0)


def test_nothing_fitting_even_after_a_rebuild_keeps_the_old_guesses(battle):
    # Samurott's only set and its usage both say Leftovers, but taking no rock damage says Boots.
    battle["sides"]["p2"]["hazards"]["stealthrock"] = 1
    belief = Belief(PRIORS, battle)
    belief.update(battle)
    belief.update(turn(battle, [event("switch", 1)], active=1))
    assert items(belief, 1) == ["leftovers"]
    assert weights(belief, 1) == [1.0]
    assert len(belief.scenarios()) == 1


def test_scenarios_vary_the_active_and_fix_the_bench(battle):
    belief = Belief(PRIORS, battle)
    belief.update(battle)
    scenarios = belief.scenarios(k=5)
    assert len(scenarios) == 2  # only two Gholdengo sets survive
    assert math.isclose(sum(p for p, _ in scenarios), 1.0)
    for _, sets in scenarios:
        assert len(sets) == 6
        assert sets[0].item == "heavydutyboots"  # the bench's single best guess
    assert [sets[2].item for _, sets in scenarios] == ["choicescarf", "leftovers"]


def test_scenarios_keep_only_the_top_k(battle):
    battle["sides"]["p2"]["pokemon"][2]["revealed_moves"] = []
    battle["sides"]["p2"]["pokemon"][2]["tera_type"] = None
    belief = Belief(PRIORS, battle)
    scenarios = belief.scenarios(k=2)
    assert [round(p, 6) for p, _ in scenarios] == [round(0.5 / 0.8, 6), round(0.3 / 0.8, 6)]


def test_revealed_ability_filters_and_survives_a_rebuild(battle):
    belief = Belief(PRIORS, battle)
    battle["sides"]["p2"]["pokemon"][0]["ability"] = "innerfocus"  # no Dragonite candidate has it
    belief.update(battle)
    assert {s.ability for s, _ in belief.candidates[0]} == {"innerfocus"}


KINGAMBIT = {
    "sets": [
        cand(0.6, ["kowtowcleave", "suckerpunch", "ironhead", "swordsdance"], item="blackglasses",
             ability="supremeoverlord", tera="dark"),
        cand(0.4, ["kowtowcleave", "suckerpunch", "lowkick", "swordsdance"], item="leftovers",
             ability="supremeoverlord", tera="flying"),
    ],
    "usage": usage(["kowtowcleave", "suckerpunch", "ironhead", "swordsdance", "lowkick"], ["blackglasses", "leftovers"],
                   teras=("dark", "flying"), ability="supremeoverlord"),
}
OUR_PRIORS = {**PRIORS, "species": {**PRIORS["species"], "kingambit": KINGAMBIT,
                                    **{s: filler(s) for s in ("meowscarada", "ragingbolt", "hatterene", "cinderace",
                                                              "landorustherian")}}}


def game_of(battle, *kingambit_turns):
    """One BattleState per turn, with our Kingambit (p1 slot 6) showing what each turn reveals."""
    game = []
    for fields in kingambit_turns:
        state = copy.deepcopy(battle)
        state["sides"]["p1"]["pokemon"][5].update(fields)
        game.append(state)
    return game


def test_our_moves_and_tera_come_from_the_whole_game(battle):
    game = game_of(battle, {}, {"revealed_moves": ["lowkick"]},
                   {"revealed_moves": ["lowkick", "kowtowcleave"], "tera_type": "flying"})
    kingambit = sets_from_game(game, OUR_PRIORS)[5]
    # Only the lighter set runs Low Kick and Tera Flying; what was seen leads the move list.
    assert kingambit.moves == ("lowkick", "kowtowcleave", "suckerpunch", "swordsdance")
    assert (kingambit.item, kingambit.tera_type) == ("leftovers", "flying")


def test_items_shown_in_the_game_dont_pick_our_set(battle):
    # The BattleState shows Leftovers, but items can change hands, so the heavier Black Glasses set still wins.
    assert sets_from_game([battle], OUR_PRIORS)[5].item == "blackglasses"


def test_no_listed_set_fits_so_ours_is_rebuilt_from_usage(battle):
    favours_low_kick = copy.deepcopy(KINGAMBIT)
    favours_low_kick["usage"]["moves"]["lowkick"] = 1.0
    priors = {**OUR_PRIORS, "species": {**OUR_PRIORS["species"], "kingambit": favours_low_kick}}
    kingambit = sets_from_game(game_of(battle, {"revealed_moves": ["ironhead"], "tera_type": "flying"}), priors)[5]
    # Iron Head with Tera Flying is in neither listed set; the rebuild leads with what was seen, then the most used.
    assert kingambit.moves[:2] == ("ironhead", "lowkick")
    assert kingambit.tera_type == "flying"


def test_nothing_rebuilds_so_what_was_seen_is_forced_onto_the_heaviest_set(battle):
    scarf_only = {"sets": [cand(1.0, ["tackle"], item="choicescarf")], "usage": usage(["tackle"], ["choicescarf"])}
    priors = {**OUR_PRIORS, "species": {**OUR_PRIORS["species"], "kingambit": scarf_only}}
    # A status move can't sit with a Choice item, so the usage rebuild has nothing to offer.
    kingambit = sets_from_game(game_of(battle, {"revealed_moves": ["swordsdance"]}), priors)[5]
    assert kingambit.moves == ("swordsdance", "tackle")
    assert kingambit.item == "choicescarf"
