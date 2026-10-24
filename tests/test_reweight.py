import copy

import pytest
from poke_engine import calculate_damage

from decision.actions import Action
from decision.adapter import build_state
from decision.belief import Belief
from tests.test_belief import PRIORS, cand, event, turn
from tests.turn2 import EXAMPLE, REQUEST

GHOLDENGO_MOVES = ["makeitrain", "shadowball", "trick", "focusblast"]
IRON_HEAD = Action("move", 4)  # our Kingambit's slot 4 in the request fixture


def spread(nature, evs):
    return {"nature": nature, "evs": evs}


def priors_with(**sets):
    """Two Gholdengo candidates differing only where a test needs them to; both fit the hard filter."""
    priors = copy.deepcopy(PRIORS)
    priors["species"]["gholdengo"]["sets"] = [
        {**cand(0.5, GHOLDENGO_MOVES, ability="goodasgold", tera="steel"), **fields, "weight": 0.5}
        for fields in sets.values()
    ]
    return priors, list(sets)


def us(type_, **kw):
    return {**event(type_, 5, **kw), "side": "p1"}


def belief_after(priors, events):
    battle = copy.deepcopy(EXAMPLE)
    belief = Belief(priors, battle)
    belief.update(battle)
    belief.chose(REQUEST, IRON_HEAD)
    belief.update(turn(battle, events))
    return belief


def survivors(belief, names, priors):
    left = {s for s, _ in belief.candidates[2]}
    return [name for name, c in zip(names, priors["species"]["gholdengo"]["sets"])
            if any(s.item == c["item"] and s.evs == tuple(c["spread"]["evs"]) and s.nature == c["spread"]["nature"]
                   for s in left)]


# Our Kingambit has 200 Speed in the request fixture.
FAST_SLOW = dict(
    scarf=dict(item="choicescarf", spread=spread("timid", [0, 0, 0, 252, 4, 252])),     # 293 x 1.5
    slow=dict(item="leftovers", spread=spread("relaxed", [252, 0, 252, 0, 4, 0])),       # 183
)


def test_moving_first_rules_out_the_slower_set():
    priors, names = priors_with(**FAST_SLOW)
    belief = belief_after(priors, [event("move", 2, move="makeitrain", target="p1"), us("move", move="ironhead", target="p2")])
    assert survivors(belief, names, priors) == ["scarf"]


def test_moving_second_rules_out_the_faster_set():
    priors, names = priors_with(**FAST_SLOW)
    belief = belief_after(priors, [us("move", move="ironhead", target="p2"), event("move", 2, move="makeitrain", target="p1")])
    assert survivors(belief, names, priors) == ["slow"]


def test_without_our_choice_there_is_no_replay():
    priors, names = priors_with(**FAST_SLOW)
    battle = copy.deepcopy(EXAMPLE)
    belief = Belief(priors, battle)
    belief.update(battle)
    belief.update(turn(battle, [us("move", move="ironhead", target="p2"), event("move", 2, move="makeitrain", target="p1")]))
    assert survivors(belief, names, priors) == ["scarf", "slow"]


def test_a_switch_gives_no_evidence():
    priors, names = priors_with(**FAST_SLOW)
    belief = belief_after(priors, [event("switch", 0), us("move", move="ironhead", target="p2")])
    assert survivors(belief, names, priors) == ["scarf", "slow"]


def damage_range(priors, n_set, ours_first=True, crit=False, defender="them"):
    """(low %, high %) the engine gives for a hit with candidate n_set in Gholdengo's slot."""
    candidates = Belief(priors, copy.deepcopy(EXAMPLE)).candidates
    sets = [max(c, key=lambda sw: sw[1])[0] for c in candidates]
    sets[2] = candidates[2][n_set][0]
    state = build_state(REQUEST, EXAMPLE, sets)
    (ours_max, ours_crit), (theirs_max, theirs_crit) = calculate_damage(state, "ironhead", "makeitrain", ours_first)
    if defender == "them":
        top, maxhp = (ours_crit if crit else ours_max), state.side_two.pokemon[2].maxhp
    else:
        top, maxhp = (theirs_crit if crit else theirs_max), state.side_one.pokemon[0].maxhp
    return 100 * 0.85 * top / maxhp, 100 * top / maxhp


FRAIL_BULKY = dict(
    frail=dict(item="choicescarf", spread=spread("timid", [0, 0, 0, 252, 4, 252])),
    bulky=dict(item="choicescarf", spread=spread("bold", [252, 0, 252, 0, 4, 0])),
)


def test_damage_taken_rules_out_the_wrong_bulk():
    priors, names = priors_with(**FRAIL_BULKY)
    frail, bulky = damage_range(priors, 0), damage_range(priors, 1)
    assert frail[1] > bulky[1] + 2  # the test only works if the ranges really separate
    drop = round(frail[1])
    belief = belief_after(priors, [event("move", 2, move="makeitrain", target="p1"), us("move", move="ironhead", target="p2"),
                                   event("damage", 2, hp_percent=100 - drop, source="move", effectiveness="resisted")])
    assert survivors(belief, names, priors) == ["frail"]


STRONG_WEAK = dict(
    strong=dict(item="choicescarf", spread=spread("timid", [0, 0, 0, 252, 4, 252])),
    weak=dict(item="choicescarf", spread=spread("bold", [252, 0, 252, 0, 4, 252])),
)


def test_damage_dealt_rules_out_the_wrong_power():
    priors, names = priors_with(**STRONG_WEAK)
    strong, weak = (damage_range(priors, n, ours_first=False, defender="us") for n in (0, 1))
    assert strong[1] > weak[1] + 2
    drop = round(strong[1])
    hp = EXAMPLE["sides"]["p1"]["pokemon"][5]["hp_percent"]
    belief = belief_after(priors, [event("move", 2, move="makeitrain", target="p1"),
                                   us("damage", hp_percent=hp - drop, source="move", effectiveness="resisted"),
                                   us("move", move="ironhead", target="p2")])
    assert survivors(belief, names, priors) == ["strong"]


def test_a_crit_is_checked_against_the_crit_range():
    priors, names = priors_with(**FRAIL_BULKY)
    crit = damage_range(priors, 1, crit=True)
    drop = round(crit[1])
    hits = lambda is_crit: [event("move", 2, move="makeitrain", target="p1"), us("move", move="ironhead", target="p2"),
                            event("damage", 2, hp_percent=100 - drop, source="move", crit=is_crit, effectiveness="resisted")]
    assert "bulky" in survivors(belief_after(priors, hits(True)), names, priors)
    assert "bulky" not in survivors(belief_after(priors, hits(False)), names, priors)


def test_a_ko_only_needs_enough_damage():
    priors, names = priors_with(**FRAIL_BULKY)
    battle_hp = 10  # little HP left, so any real hit can KO
    belief_battle = copy.deepcopy(EXAMPLE)
    belief_battle["sides"]["p2"]["pokemon"][2]["hp_percent"] = battle_hp
    belief = Belief(priors, belief_battle)
    belief.update(belief_battle)
    belief.chose(REQUEST, IRON_HEAD)
    belief.update(turn(belief_battle, [event("move", 2, move="makeitrain", target="p1"), us("move", move="ironhead", target="p2"),
                                       event("damage", 2, hp_percent=0, source="move", effectiveness="resisted")]))
    assert survivors(belief, names, priors) == ["frail", "bulky"]


def test_only_one_side_acting_gives_no_order_evidence():
    priors, names = priors_with(**FAST_SLOW)
    belief = belief_after(priors, [event("move", 2, move="makeitrain", target="p1"), us("cant", reason="slp")])
    assert survivors(belief, names, priors) == ["scarf", "slow"]


def test_an_immune_hit_gives_no_damage_evidence():
    priors, names = priors_with(**FRAIL_BULKY)
    belief = belief_after(priors, [event("move", 2, move="makeitrain", target="p1"), us("move", move="ironhead", target="p2"),
                                   event("damage", 2, hp_percent=100, source="move", effectiveness="immune")])
    assert survivors(belief, names, priors) == ["frail", "bulky"]


def test_damage_is_measured_from_the_hp_just_before_the_hit():
    priors, names = priors_with(**FRAIL_BULKY)
    frail = damage_range(priors, 0)
    drop = round(frail[1])
    # Gholdengo drops to 90 from something that reveals nothing (sandstorm chip), then takes our hit.
    belief = belief_after(priors, [event("move", 2, move="makeitrain", target="p1"),
                                   event("damage", 2, hp_percent=90, source="sandstorm"),
                                   us("move", move="ironhead", target="p2"),
                                   event("damage", 2, hp_percent=90 - drop, source="move", effectiveness="resisted")])
    assert survivors(belief, names, priors) == ["frail"]


def test_a_hit_after_they_pivot_out_is_not_about_this_pokemon():
    # U-turn style: they act, switch out, and our hit lands on the replacement.
    priors, names = priors_with(**FRAIL_BULKY)
    belief = belief_after(priors, [event("move", 2, move="makeitrain", target="p1"), event("switch", 0),
                                   us("move", move="ironhead", target="p2"),
                                   event("damage", 0, hp_percent=50, source="move", effectiveness="neutral")])
    assert survivors(belief, names, priors) == ["frail", "bulky"]


def test_a_multi_hit_move_gives_no_damage_evidence():
    # Until BattleState carries hit counts, a 2-5 hit total can't be checked against a single-hit range.
    priors, names = priors_with(**FRAIL_BULKY)
    request = copy.deepcopy(REQUEST)
    request["active"][0]["moves"][3].update(move="Bullet Seed", id="bulletseed")
    request["side"]["pokemon"][0]["moves"][3] = "bulletseed"
    battle = copy.deepcopy(EXAMPLE)
    belief = Belief(priors, battle)
    belief.update(battle)
    belief.chose(request, IRON_HEAD)  # slot 4 is now Bullet Seed
    belief.update(turn(battle, [event("move", 2, move="makeitrain", target="p1"), us("move", move="bulletseed", target="p2"),
                                event("damage", 2, hp_percent=1, source="move", effectiveness="resisted")]))
    assert survivors(belief, names, priors) == ["frail", "bulky"]
