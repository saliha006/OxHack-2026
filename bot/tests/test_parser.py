import json
import logging
from pathlib import Path

from bot.parser import Parser, parse_details, parse_hp, states_from_log

ROOT = Path(__file__).parent.parent.parent
REPLAY = (Path(__file__).parent / "fixtures" / "gen9ou-2703852247.log").read_text().splitlines()
EXAMPLE = json.loads((ROOT / "contracts" / "examples" / "battle_state_turn2.json").read_text())

# p1: Kingambit (0), Urshifu with its forme hidden (1); p2: Samurott-Hisui (0), Zoroark-Hisui (1).
PREVIEW = ["|player|p1|Alice|1|1500", "|player|p2|Bob|2|", "|poke|p1|Kingambit, F|", "|poke|p1|Urshifu-*|",
           "|poke|p2|Samurott-Hisui, F|", "|poke|p2|Zoroark-Hisui, M|"]
LEADS = ["|switch|p1a: Kingambit|Kingambit, F|100/100", "|switch|p2a: Samurott|Samurott-Hisui, F|100/100"]


def parse(*lines, us="p1", preview=True):
    parser = Parser(us)
    for line in [*(PREVIEW if preview else []), *lines]:
        parser.feed(line)
    return parser


def side(parser, side_id):
    return parser.state["sides"][side_id]


def mon(parser, side_id, index):
    return side(parser, side_id)["pokemon"][index]


def events(parser):
    return parser.state["last_turn"]


def test_replay_turn_two_matches_the_contract_example():
    state = states_from_log(REPLAY)[2]
    assert state.pop("last_turn_complete") is True
    assert state == EXAMPLE


def test_whole_replay_parses_without_a_skipped_line(caplog):
    with caplog.at_level(logging.WARNING, logger="bot.parser"):
        states = states_from_log(REPLAY)
        parser = parse(*REPLAY, preview=False)
    assert not caplog.records
    assert len(states) == 35  # team preview + turns 1-34
    assert [s["turn"] for s in states] == list(range(35))
    assert states[4]["sides"]["p2"]["pokemon"][1]["hp_percent"] == 0  # Samurott fainted on turn 3
    assert states[5]["sides"]["p1"]["pokemon"][4]["item"] == "rockyhelmet"  # revealed via [of] on Dragonite's damage
    p1 = side(parser, "p1")["pokemon"]
    assert p1[4]["item"] == ""  # Walking Wake knocked it off on turn 30
    assert p1[3]["ability"] == "libero"


def test_snapshot_hands_over_events_once():
    parser = parse(*LEADS)
    assert [e["type"] for e in parser.snapshot()["last_turn"]] == ["switch", "switch"]
    assert parser.snapshot()["last_turn"] == []


def test_hidden_forme_resolves_on_switch_in():
    parser = parse("|switch|p1a: Urshifu|Urshifu-Rapid-Strike, M|100/100 par")
    assert mon(parser, "p1", 1)["status"] == "par"  # statused before this log started, e.g. a reconnect
    assert mon(parser, "p1", 1)["species"] == "urshifurapidstrike"
    assert mon(parser, "p1", 1)["forme_known"]
    assert side(parser, "p1")["active"] == 1


def test_nickname_maps_to_the_species_slot():
    parser = parse("|switch|p2a: Sammy|Samurott-Hisui, F|100/100", "|-damage|p2a: Sammy|40/100")
    assert mon(parser, "p2", 0)["hp_percent"] == 40


def test_exact_hp_becomes_a_percentage():
    parser = parse("|switch|p1a: Kingambit|Kingambit, F|341/341", "|-damage|p1a: Kingambit|250/341")
    assert mon(parser, "p1", 0)["hp_percent"] == 73
    parser.feed("|-damage|p1a: Kingambit|1/341")
    assert mon(parser, "p1", 0)["hp_percent"] == 1  # a sliver of HP never rounds down to fainted


def test_faint_zeroes_hp_and_keeps_status():
    parser = parse(*LEADS, "|-status|p1a: Kingambit|par", "|-damage|p1a: Kingambit|0 fnt", "|faint|p1a: Kingambit")
    assert mon(parser, "p1", 0)["hp_percent"] == 0
    assert mon(parser, "p1", 0)["status"] == "par"


def test_double_faint_then_both_sides_switch():
    parser = parse(*LEADS, "|faint|p1a: Kingambit", "|faint|p2a: Samurott",
                   "|switch|p1a: Urshifu|Urshifu-Rapid-Strike, M|100/100",
                   "|switch|p2a: Zoroark|Zoroark-Hisui, M|100/100")
    assert (side(parser, "p1")["active"], side(parser, "p2")["active"]) == (1, 1)
    assert mon(parser, "p1", 0)["hp_percent"] == mon(parser, "p2", 0)["hp_percent"] == 0


def test_switch_clears_boosts_volatiles_and_last_move():
    parser = parse(*LEADS, "|move|p1a: Kingambit|Swords Dance|p1a: Kingambit", "|-boost|p1a: Kingambit|atk|4",
                   "|-boost|p1a: Kingambit|atk|4", "|-start|p1a: Kingambit|Substitute")
    assert side(parser, "p1")["boosts"]["atk"] == 6
    assert side(parser, "p1")["last_move"] == "swordsdance"
    assert side(parser, "p1")["volatiles"] == ["substitute"]
    parser.feed("|switch|p1a: Urshifu|Urshifu-Rapid-Strike, M|100/100")
    assert side(parser, "p1")["boosts"]["atk"] == 0
    assert side(parser, "p1")["volatiles"] == []
    assert side(parser, "p1")["last_move"] is None


def test_illusion_break_moves_the_active_slot():
    parser = parse(*LEADS, "|replace|p2a: Zoroark|Zoroark-Hisui, M", "|-damage|p2a: Zoroark|50/100")
    assert side(parser, "p2")["active"] == 1
    assert mon(parser, "p2", 1)["hp_percent"] == 50
    assert mon(parser, "p2", 0)["hp_percent"] == 100


def test_tera_from_terastallize_and_from_details():
    parser = parse(*LEADS, "|-terastallize|p2a: Samurott|Dark")
    assert (mon(parser, "p2", 0)["tera_type"], mon(parser, "p2", 0)["terastallized"]) == ("dark", True)
    assert side(parser, "p2")["tera_used"]
    assert events(parser)[-1]["source"] == "tera:dark"
    parser.feed("|switch|p1a: Urshifu|Urshifu-Rapid-Strike, M, tera:Water|100/100")
    assert (mon(parser, "p1", 1)["tera_type"], mon(parser, "p1", 1)["terastallized"]) == ("water", True)


def test_from_tags_reveal_on_the_right_pokemon():
    parser = parse(*LEADS,
                   "|-damage|p2a: Samurott|90/100|[from] item: Rocky Helmet|[of] p1a: Kingambit",
                   "|-heal|p2a: Samurott|96/100|[from] item: Leftovers",
                   "|-item|p2a: Samurott|Choice Scarf|[from] ability: Frisk|[of] p1a: Kingambit")
    assert mon(parser, "p2", 0)["hp_percent"] == 96
    assert mon(parser, "p1", 0)["item"] == "rockyhelmet"
    assert mon(parser, "p1", 0)["ability"] == "frisk"
    assert mon(parser, "p2", 0)["item"] == "choicescarf"  # -item states the current item, after Leftovers
    assert [e["source"] for e in events(parser)[-3:]] == ["item:rockyhelmet", "item:leftovers", "item:choicescarf"]
    parser.feed("|-enditem|p2a: Samurott|Choice Scarf|[from] move: Knock Off")
    assert mon(parser, "p2", 0)["item"] == ""
    assert (events(parser)[-1]["type"], events(parser)[-1]["source"]) == ("reveal", "item:choicescarf")


def test_ability_reveals_from_every_line_kind():
    parser = parse(*LEADS, "|-ability|p2a: Samurott|Sharpness", "|-immune|p1a: Kingambit|[from] ability: Levitate",
                   "|-start|p2a: Samurott|ability: Flash Fire", "|-activate|p1a: Kingambit|item: Air Balloon",
                   "|-status|p1a: Kingambit|brn|[from] item: Flame Orb")
    assert events(parser)[-1]["source"] == "ability:sharpness"
    assert side(parser, "p2")["volatiles"] == ["flashfire"]
    assert mon(parser, "p2", 0)["ability"] == "flashfire"
    assert mon(parser, "p1", 0)["ability"] == "levitate"
    assert mon(parser, "p1", 0)["item"] == "flameorb"
    assert mon(parser, "p1", 0)["status"] == "brn"
    parser.feed("|-activate|p1a: Kingambit|move: Protect")  # not a reveal
    assert mon(parser, "p1", 0)["item"] == "flameorb"


def test_damage_events_carry_crit_effectiveness_and_source():
    parser = parse(*LEADS, "|move|p1a: Kingambit|Low Kick|p2a: Samurott", "|-crit|p2a: Samurott",
                   "|-supereffective|p2a: Samurott", "|-damage|p2a: Samurott|20/100",
                   "|move|p2a: Samurott|Ceaseless Edge|p1a: Kingambit", "|-damage|p1a: Kingambit|90/100",
                   "|-damage|p2a: Samurott|8/100|[from] Stealth Rock", "|-heal|p1a: Kingambit|100/100")
    low_kick, ceaseless, rocks, heal = [e for e in events(parser) if e["type"] in ("damage", "heal")]
    assert (low_kick["crit"], low_kick["effectiveness"], low_kick["source"]) == (True, "super", "move")
    assert (ceaseless["crit"], ceaseless["effectiveness"]) == (False, "neutral")
    assert (rocks["source"], rocks["effectiveness"]) == ("stealthrock", None)
    assert (heal["source"], heal["effectiveness"]) == ("move", None)
    move = events(parser)[2]
    assert (move["type"], move["move"], move["target"]) == ("move", "lowkick", "p2")


def test_called_moves_are_not_revealed_but_locked_ones_are():
    parser = parse(*LEADS, "|move|p1a: Kingambit|Sleep Talk|p1a: Kingambit",
                   "|move|p1a: Kingambit|Sucker Punch|p2a: Samurott|[from]Sleep Talk",
                   "|move|p2a: Samurott|Outrage|p1a: Kingambit",
                   "|move|p2a: Samurott|Outrage|p1a: Kingambit|[from]lockedmove",
                   "|move|p2a: Samurott|Recharge|")
    assert mon(parser, "p1", 0)["revealed_moves"] == ["sleeptalk"]
    assert side(parser, "p1")["last_move"] == "sleeptalk"
    assert mon(parser, "p2", 0)["revealed_moves"] == ["outrage", "recharge"]
    assert events(parser)[-1]["target"] is None


def test_miss_and_cant_events():
    parser = parse(*LEADS, "|-miss|p1a: Kingambit|p2a: Samurott", "|cant|p2a: Samurott|par",
                   "|cant|p2a: Samurott|Disable|Sucker Punch")
    miss, para, disabled = events(parser)[-3:]
    assert (miss["type"], miss["side"], miss["pokemon"]) == ("miss", "p1", 0)
    assert (para["reason"], para["move"]) == ("par", None)
    assert (disabled["reason"], disabled["move"]) == ("disable", "suckerpunch")


def test_hazards_side_effects_and_court_change():
    parser = parse(*LEADS, "|-sidestart|p1: Alice|Spikes", "|-sidestart|p1: Alice|Spikes",
                   "|-sidestart|p1: Alice|move: Stealth Rock", "|-sidestart|p2: Bob|Reflect", "|upkeep")
    assert side(parser, "p1")["hazards"] == {"stealthrock": 1, "spikes": 2, "toxicspikes": 0, "stickyweb": 0}
    assert side(parser, "p2")["side_effects"] == {"reflect": 1}
    parser.feed("|-swapsideconditions|")
    assert side(parser, "p2")["hazards"]["spikes"] == 2
    assert side(parser, "p1")["side_effects"] == {"reflect": 1}
    parser.feed("|-sideend|p2: Bob|Spikes")
    parser.feed("|-sideend|p1: Alice|Reflect")
    assert side(parser, "p2")["hazards"]["spikes"] == 0
    assert side(parser, "p1")["side_effects"] == {}


def test_weather_terrain_and_field_effects_count_end_of_turns():
    parser = parse(*LEADS, "|-weather|SunnyDay|[from] ability: Drought|[of] p1a: Kingambit", "|upkeep",
                   "|-weather|SunnyDay|[upkeep]", "|upkeep", "|-fieldstart|move: Electric Terrain",
                   "|-fieldstart|move: Trick Room|[of] p2a: Samurott", "|upkeep")
    field = parser.state["field"]
    assert (field["weather"], field["weather_turns"]) == ("sunnyday", 3)
    assert mon(parser, "p1", 0)["ability"] == "drought"
    assert (field["terrain"], field["terrain_turns"], field["effects"]) == ("electricterrain", 1, {"trickroom": 1})
    for line in ("|-fieldend|move: Electric Terrain", "|-fieldend|move: Trick Room", "|-weather|none"):
        parser.feed(line)
    assert field == {"weather": "", "weather_turns": 0, "terrain": "", "terrain_turns": 0, "effects": {}}


def test_status_counters_and_cures():
    parser = parse(*LEADS, "|-status|p1a: Kingambit|tox", "|upkeep", "|upkeep")
    assert mon(parser, "p1", 0)["status_turns"] == 2
    parser.feed("|switch|p1a: Urshifu|Urshifu-Rapid-Strike, M|100/100")
    assert mon(parser, "p1", 0)["status_turns"] == 0  # toxic restarts on switch-out
    parser.feed("|-status|p1a: Urshifu|slp")
    parser.feed("|upkeep")
    parser.feed("|-curestatus|p1: Urshifu|slp|[msg]")
    assert (mon(parser, "p1", 1)["status"], mon(parser, "p1", 1)["status_turns"]) == ("", 0)
    parser.feed("|-cureteam|p1a: Urshifu|[from] move: Heal Bell")
    assert mon(parser, "p1", 0)["status"] == ""


def test_boost_variants():
    parser = parse(*LEADS, "|-unboost|p2a: Samurott|def|8", "|-setboost|p1a: Kingambit|atk|6")
    assert side(parser, "p2")["boosts"]["def"] == -6
    assert side(parser, "p1")["boosts"]["atk"] == 6
    parser.feed("|-clearnegativeboost|p2a: Samurott")
    assert side(parser, "p2")["boosts"]["def"] == 0
    parser.feed("|-boost|p2a: Samurott|spe|1")
    parser.feed("|-clearboost|p2a: Samurott")
    assert side(parser, "p2")["boosts"]["spe"] == 0
    parser.feed("|-clearallboost")
    assert side(parser, "p1")["boosts"]["atk"] == 0


def test_volatile_end_and_forme_change():
    parser = parse(*LEADS, "|-start|p1a: Kingambit|confusion", "|-end|p1a: Kingambit|confusion",
                   "|-end|p1a: Kingambit|Substitute", "|-formechange|p2a: Samurott|Samurott-Hisui-Tera, F, tera:Dark",
                   "|detailschange|p1a: Kingambit|Kingambit-Mega, F", "|-sethp|p1a: Kingambit|55/100")
    assert side(parser, "p1")["volatiles"] == []
    assert (mon(parser, "p2", 0)["species"], mon(parser, "p2", 0)["tera_type"]) == ("samurotthisuitera", "dark")
    assert mon(parser, "p1", 0)["species"] == "kingambitmega"
    assert mon(parser, "p1", 0)["hp_percent"] == 55


def test_no_team_preview_adds_pokemon_on_switch_in():
    parser = parse("|switch|p1a: Pikachu|Pikachu, L88, M|100/100", preview=False)
    assert [(m["species"], m["level"]) for m in side(parser, "p1")["pokemon"]] == [("pikachu", 88)]


def test_player_lines():
    parser = parse("|player|p1|")  # a player leaving keeps their name
    assert (side(parser, "p1")["player"], side(parser, "p1")["rating"]) == ("Alice", 1500)
    assert (side(parser, "p2")["player"], side(parser, "p2")["rating"]) == ("Bob", None)


def test_malformed_and_unknown_lines_are_skipped(caplog):
    with caplog.at_level(logging.WARNING, logger="bot.parser"):
        parser = parse(*LEADS, "|-damage|", "|-boost|p1a: Kingambit|atk|x", "garbage", "|someday|new|line", "", "|")
    assert len(caplog.records) == 2
    assert mon(parser, "p1", 0)["hp_percent"] == 100


def test_detail_and_hp_helpers():
    assert parse_details("Urshifu-*, L50, tera:Water") == ("urshifu", False, 50, "water")
    assert parse_details("Kingambit, F") == ("kingambit", True, 100, None)
    assert parse_hp("60/100 par") == (60, "par")
    assert parse_hp("0 fnt") == (0, None)
    assert parse_hp("100/100") == (100, "")
