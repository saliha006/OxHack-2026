import copy

from decision.actions import Action
from decision.lead import pick_lead
from tests.test_agent import load
from tests.turn2 import EXAMPLE

PREVIEW = load("team_preview_request")


def against(*species):
    battle = copy.deepcopy(EXAMPLE)
    for mon, name in zip(battle["sides"]["p2"]["pokemon"], species * 6):
        mon["species"] = name
    return battle


def test_leads_with_the_best_type_matchup():
    # Kingambit hits Gholdengo and Pecharunt super effectively and resists Dragonite: +3 over the six, best on the team.
    assert pick_lead(PREVIEW, copy.deepcopy(EXAMPLE)) == Action("lead", 1)


def test_switches_lead_when_the_matchup_favours_another():
    # Great Tusk's Ground is 4x on Fire/Steel and it resists both STABs back; Kingambit is hit 2x and resisted.
    assert pick_lead(PREVIEW, against("heatran")) == Action("lead", 2)


def test_an_immunity_counts_as_a_double_resist():
    # Normal and Ghost are immune to each other both ways: log2(0) without the floor, -2 - -2 = 0 with it.
    request = copy.deepcopy(PREVIEW)
    request["side"]["pokemon"] = [dict(request["side"]["pokemon"][0], details="Snorlax, L100"),
                                  dict(request["side"]["pokemon"][1], details="Kingambit, L100")]
    # Kingambit: Dark 2x on Gengar, Gengar's best (Ghost) resisted, Poison immune -> +2 per foe, beating Snorlax's 0.
    assert pick_lead(request, against("gengar")) == Action("lead", 2)


def test_ties_keep_team_order():
    request = copy.deepcopy(PREVIEW)
    # Dragapult and Gholdengo both score -2 against the example team.
    request["side"]["pokemon"] = [request["side"]["pokemon"][3], request["side"]["pokemon"][2]]
    assert pick_lead(request, copy.deepcopy(EXAMPLE)) == Action("lead", 1)
