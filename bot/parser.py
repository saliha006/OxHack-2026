"""Showdown protocol lines -> BattleState (contracts/battle-state.md).

Pure: no network, so the same code reads a live battle and a saved replay log.
"""
import copy
import logging
import re
from collections.abc import Iterable

from contracts.battle_state import BattleState, Event, PokemonState, SideId, SideState

log = logging.getLogger("bot.parser")

HAZARDS = ("stealthrock", "spikes", "toxicspikes", "stickyweb")
BOOSTS = ("atk", "def", "spa", "spd", "spe", "accuracy", "evasion")
STATUSES = ("", "brn", "par", "slp", "frz", "psn", "tox")
COUNTED_STATUSES = ("slp", "tox")
EFFECTIVENESS = {"-supereffective": "super", "-resisted": "resisted", "-immune": "immune"}


def to_id(text: str) -> str:
    """Showdown's toID: lowercase letters and digits only."""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def effect_id(text: str) -> str:
    # "move: Stealth Rock", "ability: Flash Fire" and "item: Leftovers" name the effect after the colon.
    return to_id(text.split(":", 1)[1] if ":" in text else text)


def parse_details(details: str) -> tuple[str, bool, int, str | None]:
    """'Urshifu-*, L50, tera:Water' -> ('urshifu', False, 50, 'water')."""
    name, *flags = (part.strip() for part in details.split(","))
    level = next((int(flag[1:]) for flag in flags if re.fullmatch(r"L\d+", flag)), 100)
    tera = next((to_id(flag[5:]) for flag in flags if flag.startswith("tera:")), None)
    return to_id(name.removesuffix("-*")), not name.endswith("-*"), level, tera


def parse_hp(text: str) -> tuple[int, str | None]:
    """'60/100 par' -> (60, 'par'); '0 fnt' -> (0, None), where None keeps the current status."""
    hp, _, status = text.partition(" ")
    if status == "fnt" or hp == "0":
        return 0, None
    current, _, total = hp.partition("/")
    # Legacy replays append a colour code (e.g. 20/100y); it is presentation, not part of the HP value.
    current, total = int(current), int(re.sub(r"[a-z]+$", "", total) or 100)
    # Our own side's lines carry exact HP; the contract wants Showdown's 0-100 scale for both sides.
    percent = current if total == 100 else max(1, round(current * 100 / total))
    return percent, status


def split_ref(ref: str) -> tuple[SideId, str]:
    """'p2a: Samurott' -> ('p2', 'Samurott'); 'p1: Alice' -> ('p1', 'Alice')."""
    side_id, _, name = ref.partition(": ")
    return side_id[:2], name


def parse_tags(args: Iterable[str]) -> dict[str, str]:
    """'[from] item: Leftovers', '[of] p1a: Landorus' -> {'from': 'item: Leftovers', 'of': 'p1a: Landorus'}."""
    tags = {}
    for arg in args:
        if arg.startswith("["):
            key, _, value = arg[1:].partition("]")
            tags[key] = value.strip()
    return tags


def new_pokemon(species: str, forme_known: bool, level: int = 100) -> PokemonState:
    return {"species": species, "forme_known": forme_known, "level": level, "hp_percent": 100, "status": "",
            "status_turns": 0, "revealed_moves": [], "item": None, "ability": None, "tera_type": None,
            "terastallized": False}


def new_side() -> SideState:
    return {"player": "", "rating": None, "pokemon": [], "active": None, "tera_used": False,
            "boosts": dict.fromkeys(BOOSTS, 0), "volatiles": [], "last_move": None,
            "hazards": dict.fromkeys(HAZARDS, 0), "side_effects": {}}


class Parser:
    """Feed it every protocol line of one battle; snapshot() at each request."""

    def __init__(self, us: SideId = "p1"):
        self.state: BattleState = {
            "us": us, "turn": 0, "sides": {"p1": new_side(), "p2": new_side()},
            "field": {"weather": "", "weather_turns": 0, "terrain": "", "terrain_turns": 0, "effects": {}},
            "last_turn": [],
        }
        self.names: dict[SideId, dict[str, int]] = {"p1": {}, "p2": {}}  # ident name -> team index
        self.pending_hits: dict[tuple[SideId, int], dict] = {}  # crit / effectiveness waiting for their -damage

    def feed(self, line: str) -> None:
        kind, *args = line.rstrip("\r\n").split("|")[1:] or [""]
        handler = self.HANDLERS.get(kind)
        if handler is None:
            return
        try:
            handler(self, args)
        except (IndexError, KeyError, TypeError, ValueError):
            # A malformed line costs one fact, not the battle: the bot must keep answering requests.
            log.warning("skipped malformed line: %s", line)

    def snapshot(self) -> BattleState:
        """The state for the request being answered; last_turn then starts over."""
        state = copy.deepcopy(self.state)
        self.state["last_turn"] = []
        return state

    def side(self, side_id: SideId) -> SideState:
        return self.state["sides"][side_id]

    def mon(self, ref: str) -> tuple[SideId, int]:
        """'p2a: Samurott' -> ('p2', index). An unknown name means the active Pokémon."""
        side_id, name = split_ref(ref)
        return side_id, self.names[side_id].get(name, self.side(side_id)["active"])

    def pokemon(self, side_id: SideId, index: int) -> PokemonState:
        return self.side(side_id)["pokemon"][index]

    def find(self, side_id: SideId, species: str, forme_known: bool) -> int:
        team = self.side(side_id)["pokemon"]
        for i, mon in enumerate(team):
            if mon["species"] == species:
                return i
        for i, mon in enumerate(team):
            # Team preview hid the forme ('Urshifu-*'), so the base ID is a prefix of the real one.
            if not mon["forme_known"] and species.startswith(mon["species"]):
                return i
        team.append(new_pokemon(species, forme_known))  # formats without team preview
        return len(team) - 1

    def event(self, kind: str, side_id: SideId, index: int, **fields) -> None:
        event: Event = {"type": kind, "side": side_id, "pokemon": index, "move": None, "target": None,
                        "hp_percent": None, "source": None, "crit": False, "effectiveness": None, "reason": None}
        event.update(fields)
        self.state["last_turn"].append(event)

    def set_hp(self, mon: PokemonState, hp: int, status: str | None) -> None:
        mon["hp_percent"] = hp
        if status is not None and status in STATUSES and status != mon["status"]:
            mon["status"], mon["status_turns"] = status, 0
            mon.pop("sleep_turns", None)
            mon.pop("rest_turns", None)

    def reveal(self, tags: dict[str, str], owner: tuple[SideId, int] | None) -> str | None:
        """Record what a [from] tag gives away; return it as an Event.source string."""
        origin = tags.get("from")
        if origin is None:
            return None
        if "of" in tags:
            owner = self.mon(tags["of"])
        if origin.startswith(("item:", "ability:")) and owner is not None:
            kind, effect = origin.split(":", 1)[0], effect_id(origin)
            self.pokemon(*owner)[kind] = effect
            return f"{kind}:{effect}"
        return effect_id(origin)

    def _player(self, args):
        side = self.side(args[0])
        if args[1]:  # a bare '|player|p1|' marks a player leaving
            side["player"] = args[1]
            side["rating"] = int(args[3]) if len(args) > 3 and args[3].isdigit() else None

    def _poke(self, args):
        species, forme_known, level, _ = parse_details(args[1])
        team = self.side(args[0])["pokemon"]
        if all(mon["species"] != species for mon in team):
            team.append(new_pokemon(species, forme_known, level))

    def _switch(self, args):
        side_id, name = split_ref(args[0])
        species, forme_known, level, tera = parse_details(args[1])
        side, index = self.side(side_id), self.find(side_id, species, forme_known)
        mon = self.pokemon(side_id, index)
        if forme_known:
            mon["species"], mon["forme_known"] = species, True
        mon["level"] = level
        if tera:
            mon["tera_type"], mon["terastallized"] = tera, True
            side["tera_used"] = True
        self.set_hp(mon, *parse_hp(args[2]))
        previous = side["active"]
        if previous is not None and previous != index and self.pokemon(side_id, previous)["status"] == "tox":
            self.pokemon(side_id, previous)["status_turns"] = 0  # the toxic counter restarts on switch-out
        side["active"] = index
        side["boosts"] = dict.fromkeys(BOOSTS, 0)
        side["volatiles"] = []
        side.pop("volatile_turns", None)
        side.pop("substitute_hp", None)
        side["last_move"] = None
        self.names[side_id][name] = index
        self.event("switch", side_id, index)

    def _replace(self, args):
        # Illusion broke: the active Pokémon was really this one all along.
        side_id, name = split_ref(args[0])
        species, forme_known, _, _ = parse_details(args[1])
        index = self.find(side_id, species, forme_known)
        self.side(side_id)["active"] = index
        self.names[side_id][name] = index

    def _move(self, args):
        side_id, index = self.mon(args[0])
        move, tags = to_id(args[1]), parse_tags(args[3:])
        self.pending_hits = {}
        # A move called by another one (Sleep Talk, Metronome) isn't in this Pokémon's set; a locked-in repeat is.
        if tags.get("from", "lockedmove") == "lockedmove":
            moves = self.pokemon(side_id, index)["revealed_moves"]
            if move not in moves:
                moves.append(move)
            self.side(side_id)["last_move"] = move
        target = args[2][:2] if len(args) > 2 and args[2][:2] in ("p1", "p2") else None
        self.event("move", side_id, index, move=move, target=target)
        if move == "sleeptalk" and self.pokemon(side_id, index)["status"] == "slp":
            self._sleep_attempt(self.pokemon(side_id, index))
        if move in ("wish", "futuresight") and not tags.get("from"):
            key = "wish" if move == "wish" else "future_sight"
            self.side(side_id).setdefault(key, {"turns": 0, "source": index})

    def _hp_change(self, kind, args):
        side_id, index = self.mon(args[0])
        hp, status = parse_hp(args[1])
        self.set_hp(self.pokemon(side_id, index), hp, status)
        source = self.reveal(parse_tags(args[2:]), (side_id, index)) or "move"
        hit = self.pending_hits.pop((side_id, index), {})
        from_move = kind == "damage" and source == "move"
        self.event(kind, side_id, index, hp_percent=hp, source=source, crit=hit.get("crit", False),
                   effectiveness=hit.get("effectiveness", "neutral") if from_move else None)

    def _sethp(self, args):
        side_id, index = self.mon(args[0])
        self.set_hp(self.pokemon(side_id, index), *parse_hp(args[1]))

    def _hit_flag(self, kind, args):
        target = self.mon(args[0])
        hit = self.pending_hits.setdefault(target, {})
        if kind == "-crit":
            hit["crit"] = True
        else:
            hit["effectiveness"] = EFFECTIVENESS[kind]
            self.reveal(parse_tags(args[1:]), target)  # e.g. '[from] ability: Levitate'

    def _miss(self, args):
        self.event("miss", *self.mon(args[0]))

    def _cant(self, args):
        move = to_id(args[2]) if len(args) > 2 else None
        self.event("cant", *self.mon(args[0]), reason=effect_id(args[1]), move=move)
        if effect_id(args[1]) == "slp":
            self._sleep_attempt(self.pokemon(*self.mon(args[0])))

    @staticmethod
    def _sleep_attempt(mon):
        mon["sleep_turns"] = mon.get("sleep_turns", 0) + 1
        if mon.get("rest_turns", 0):
            mon["rest_turns"] = max(1, mon["rest_turns"] - 1)

    def _item(self, args):
        owner = self.mon(args[0])
        self.reveal(parse_tags(args[2:]), None)  # Frisk names its owner with [of]
        item = to_id(args[1])
        self.pokemon(*owner)["item"] = item
        self.event("reveal", *owner, source=f"item:{item}")

    def _enditem(self, args):
        owner = self.mon(args[0])
        self.pokemon(*owner)["item"] = ""  # consumed, knocked off or popped: known to hold nothing now
        self.event("reveal", *owner, source=f"item:{to_id(args[1])}")

    def _ability(self, args):
        owner = self.mon(args[0])
        ability = to_id(args[1])
        self.pokemon(*owner)["ability"] = ability
        self.event("reveal", *owner, source=f"ability:{ability}")

    def _terastallize(self, args):
        side_id, index = self.mon(args[0])
        tera = to_id(args[1])
        mon = self.pokemon(side_id, index)
        mon["tera_type"], mon["terastallized"] = tera, True
        self.side(side_id)["tera_used"] = True
        self.event("reveal", side_id, index, source=f"tera:{tera}")

    def _boost(self, args, sign=1):
        side = self.side(self.mon(args[0])[0])
        stat = args[1]
        side["boosts"][stat] = max(-6, min(6, side["boosts"][stat] + sign * int(args[2])))

    def _setboost(self, args):
        self.side(self.mon(args[0])[0])["boosts"][args[1]] = int(args[2])

    def _clearboost(self, args):
        self.side(self.mon(args[0])[0])["boosts"] = dict.fromkeys(BOOSTS, 0)

    def _clearallboost(self, args):
        for side in self.state["sides"].values():
            side["boosts"] = dict.fromkeys(BOOSTS, 0)

    def _clearnegativeboost(self, args):
        boosts = self.side(self.mon(args[0])[0])["boosts"]
        for stat, stage in boosts.items():
            boosts[stat] = max(stage, 0)

    def _start(self, args):
        owner = self.mon(args[0])
        if args[1].startswith(("ability:", "item:")):
            self.reveal({"from": args[1]}, owner)
        volatiles, effect = self.side(owner[0])["volatiles"], effect_id(args[1])
        if effect == "futuresight":
            return  # Showdown marks the source; the delayed attack is tracked separately from active volatiles
        if effect not in volatiles:
            volatiles.append(effect)
        self.side(owner[0]).setdefault("volatile_turns", {})[effect] = 0
        self.reveal(parse_tags(args[2:]), owner)  # e.g. Libero: '[from] ability: Libero'

    def _end(self, args):
        volatiles, effect = self.side(self.mon(args[0])[0])["volatiles"], effect_id(args[1])
        if effect in volatiles:
            volatiles.remove(effect)
        self.side(self.mon(args[0])[0]).get("volatile_turns", {}).pop(effect, None)
        if effect == "substitute":
            self.side(self.mon(args[0])[0]).pop("substitute_hp", None)
        if effect == "futuresight":
            owner = self.mon(args[0])[0]
            self.side("p2" if owner == "p1" else "p1").pop("future_sight", None)

    def _activate(self, args):
        if args[1].startswith(("ability:", "item:")):
            self.reveal({"from": args[1]}, self.mon(args[0]))

    def _status(self, args):
        side_id, index = self.mon(args[0])
        mon = self.pokemon(side_id, index)
        mon["status"], mon["status_turns"] = args[1], 0
        mon.pop("sleep_turns", None)
        mon.pop("rest_turns", None)
        if args[1] == "slp":
            mon["sleep_turns"] = 0
            if effect_id(parse_tags(args[2:]).get("from", "")) == "rest":
                mon["rest_turns"] = 3
        self.reveal(parse_tags(args[2:]), (side_id, index))  # e.g. '[from] item: Flame Orb'

    def _curestatus(self, args):
        mon = self.pokemon(*self.mon(args[0]))
        mon["status"], mon["status_turns"] = "", 0
        mon.pop("sleep_turns", None)
        mon.pop("rest_turns", None)

    def _cureteam(self, args):
        for mon in self.side(self.mon(args[0])[0])["pokemon"]:
            mon["status"], mon["status_turns"] = "", 0
            mon.pop("sleep_turns", None)
            mon.pop("rest_turns", None)

    def _faint(self, args):
        self.pokemon(*self.mon(args[0]))["hp_percent"] = 0

    def _formechange(self, args):
        mon = self.pokemon(*self.mon(args[0]))
        species, _, _, tera = parse_details(args[1])
        mon["species"], mon["forme_known"] = species, True
        if tera:
            mon["tera_type"], mon["terastallized"] = tera, True
            self.side(self.mon(args[0])[0])["tera_used"] = True

    def _sidestart(self, args):
        side = self.side(args[0][:2])
        effect = effect_id(args[1])
        if effect in HAZARDS:
            side["hazards"][effect] += 1  # Showdown sends one -sidestart per layer
        else:
            side["side_effects"][effect] = 0

    def _sideend(self, args):
        side = self.side(args[0][:2])
        effect = effect_id(args[1])
        if effect in HAZARDS:
            side["hazards"][effect] = 0
        else:
            side["side_effects"].pop(effect, None)

    def _swapsideconditions(self, args):
        p1, p2 = self.side("p1"), self.side("p2")
        for key in ("hazards", "side_effects"):
            p1[key], p2[key] = p2[key], p1[key]

    def _weather(self, args):
        field, tags = self.state["field"], parse_tags(args[1:])
        if args[0] == "none":
            field["weather"], field["weather_turns"] = "", 0
        elif "upkeep" not in tags:  # '[upkeep]' only says the weather is still there
            field["weather"], field["weather_turns"] = to_id(args[0]), 0
            self.reveal(tags, None)

    def _fieldstart(self, args):
        field, effect = self.state["field"], effect_id(args[0])
        if effect.endswith("terrain"):
            field["terrain"], field["terrain_turns"] = effect, 0
        else:
            field["effects"][effect] = 0
        self.reveal(parse_tags(args[1:]), None)

    def _fieldend(self, args):
        field, effect = self.state["field"], effect_id(args[0])
        if effect == field["terrain"]:
            field["terrain"], field["terrain_turns"] = "", 0
        else:
            field["effects"].pop(effect, None)

    def _upkeep(self, args):
        # Every counter in the contract counts end-of-turns, and |upkeep is the end of a turn.
        field = self.state["field"]
        if field["weather"]:
            field["weather_turns"] += 1
        if field["terrain"]:
            field["terrain_turns"] += 1
        for effect in field["effects"]:
            field["effects"][effect] += 1
        for side in self.state["sides"].values():
            for effect in side["side_effects"]:
                side["side_effects"][effect] += 1
            for effect in side.get("volatile_turns", {}):
                side["volatile_turns"][effect] += 1
            for effect, duration in (("wish", 2), ("future_sight", 3)):
                if effect in side:
                    side[effect]["turns"] += 1
                    if side[effect]["turns"] >= duration:
                        del side[effect]
            if side["active"] is not None:
                mon = side["pokemon"][side["active"]]
                if mon["status"] in COUNTED_STATUSES:
                    mon["status_turns"] += 1

    def _turn(self, args):
        self.state["turn"] = int(args[0])

    def _fail(self, args):
        # A just-attempted delayed effect that Showdown rejected must not become a pending effect.
        side = self.side(self.mon(args[0])[0])
        key = {"wish": "wish", "futuresight": "future_sight"}.get(side["last_move"])
        if key and side.get(key, {}).get("turns") == 0:
            side.pop(key, None)

    HANDLERS = {
        "player": _player, "poke": _poke, "switch": _switch, "drag": _switch, "replace": _replace, "move": _move,
        "-damage": lambda self, args: self._hp_change("damage", args),
        "-heal": lambda self, args: self._hp_change("heal", args),
        "-sethp": _sethp, "-miss": _miss, "cant": _cant,
        "-crit": lambda self, args: self._hit_flag("-crit", args),
        "-supereffective": lambda self, args: self._hit_flag("-supereffective", args),
        "-resisted": lambda self, args: self._hit_flag("-resisted", args),
        "-immune": lambda self, args: self._hit_flag("-immune", args),
        "-item": _item, "-enditem": _enditem, "-ability": _ability, "-terastallize": _terastallize,
        "-boost": _boost, "-unboost": lambda self, args: self._boost(args, sign=-1),
        "-setboost": _setboost, "-clearboost": _clearboost,
        "-clearallboost": _clearallboost, "-clearnegativeboost": _clearnegativeboost,
        "-start": _start, "-end": _end, "-activate": _activate,
        "-fail": _fail,
        "-status": _status, "-curestatus": _curestatus, "-cureteam": _cureteam, "faint": _faint,
        "detailschange": _formechange, "-formechange": _formechange,
        "-sidestart": _sidestart, "-sideend": _sideend, "-swapsideconditions": _swapsideconditions,
        "-weather": _weather, "-fieldstart": _fieldstart, "-fieldend": _fieldend,
        "upkeep": _upkeep, "turn": _turn,
    }


def states_from_log(lines: Iterable[str], us: SideId = "p1") -> list[BattleState]:
    """One state per decision point of a saved log: team preview, then each |turn|.

    Forced switches after a faint have no marker in a spectator log, so they get no state of their own.
    """
    parser, states = Parser(us), []
    for line in lines:
        parser.feed(line)
        if line.startswith(("|teampreview", "|turn|")):
            states.append(parser.snapshot())
    return states
