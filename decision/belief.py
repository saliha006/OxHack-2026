from itertools import product

from poke_engine import State, calculate_damage, generate_instructions

from contracts.battle_state import BattleState, Event
from contracts.set_candidates import CandidateSet, SetCandidates, Usage
from decision.actions import Action
from decision.adapter import build_state
from decision.opponent import CHOICE_ITEMS, MOVES
from decision.sets import PokemonSet
from decision.simulate import engine_move

Candidates = list[tuple[PokemonSet, float]]

# Fallback rebuild size: top items × top Tera types × top spreads, on one move list.
REBUILD_ITEMS, REBUILD_TERAS, REBUILD_SPREADS = 3, 2, 3

# Showdown rounds HP percentages up, so an observed drop can be up to a point off the true damage either way.
PERCENT_SLACK = 1.0
# Damage rolls run from 85% to 100% of the maximum.
MIN_ROLL = 0.85


class Belief:
    """What the opponent's six Pokémon are probably running, kept for one battle and updated every turn."""

    def __init__(self, priors: SetCandidates, battle: BattleState):
        self.priors = priors
        self.them = "p2" if battle["us"] == "p1" else "p1"
        team = battle["sides"][self.them]["pokemon"]
        self.candidates: list[Candidates] = [
            [(_to_set(c), c["weight"]) for c in priors["species"][mon["species"]]["sets"]] for mon in team
        ]
        self.moves_since_switch: list[set[str]] = [set() for _ in team]
        self.previous = battle["sides"][self.them]
        self.last_battle = battle
        self.last_request: dict | None = None
        self.last_choice: Action | None = None

    def chose(self, request: dict, action: Action) -> None:
        """Record our choice, so the next update can replay this turn against each candidate (feature 04)."""
        self.last_request, self.last_choice = request, action

    def update(self, battle: BattleState) -> None:
        """Apply what the latest BattleState reveals (the hard filter, feature 03)."""
        seen = battle["sides"][self.them]
        events = [e for e in battle["last_turn"] if e["side"] == self.them]
        rules = [set() for _ in self.candidates]  # per slot: item rules implied this turn
        for e in events:
            n = e["pokemon"]
            if e["type"] == "switch":
                self.moves_since_switch[n] = set()
                if self.previous["hazards"]["stealthrock"]:
                    # Boots (or Magic Guard) is the only way to take no Stealth Rock damage on the way in.
                    rules[n].add("not_boots" if _hit_by_rocks(events, n) else "boots")
            elif e["type"] == "move":
                self.moves_since_switch[n].add(e["move"])
                if MOVES[e["move"]]["category"] == "Status":
                    rules[n].add("not_av")
            if (e["source"] or "").startswith("item:"):
                rules[n].add("item:" + e["source"][5:])
        for n, moves in enumerate(self.moves_since_switch):
            if len(moves) >= 2:
                rules[n].add("not_choice")
        active = seen["active"]
        hp = seen["pokemon"][active]["hp_percent"] if active is not None else 100
        # Leftovers heals any damaged Pokémon at the end of every turn. A faint this turn means the current active may
        # have come in after the end of turn, so the rule is skipped then.
        fainted = any(e["type"] == "damage" and e["hp_percent"] == 0 for e in events)
        if 0 < hp < 100 and not fainted and not any(e["source"] == "item:leftovers" and e["pokemon"] == active for e in events):
            rules[active].add("not_leftovers")

        start_active = self.previous["active"]
        replayable = self.last_request is not None and start_active is not None
        for n, mon in enumerate(seen["pokemon"]):
            kept = [(s, w) for s, w in self.candidates[n] if _fits(s, mon, rules[n])]
            if replayable and n == start_active:
                kept = [(s, w) for s, w in kept if self._explains_turn(s, battle)]
            if not kept:
                kept = [(s, w) for s, w in _rebuild(self.priors["species"][mon["species"]]["usage"], mon)
                        if _fits(s, mon, rules[n])]
            self.candidates[n] = _normalised(kept)
        self.previous = seen
        self.last_battle = battle
        self.last_request = self.last_choice = None

    def _explains_turn(self, candidate: PokemonSet, battle: BattleState) -> bool:
        """Soft reweight (04), as a hard zero: can poke-engine, given this set, produce what happened last turn?

        Replays the turn from its starting state with the candidate in the opponent's active slot, then checks the
        move order and the damage each side took against the engine's outcomes and damage range.
        """
        start = self.last_battle
        n = self.previous["active"]
        sets = [max(c, key=lambda sw: sw[1])[0] for c in self.candidates]
        sets[n] = candidate
        state = build_state(self.last_request, start, sets)
        events = battle["last_turn"]
        us = battle["us"]
        theirs = _their_action(state, events, self.them, n)
        ours = self.last_choice
        if theirs is None or ours.kind != "move":
            return True  # a switch on either side gives no order or damage evidence about this Pokémon
        our_move, their_move = engine_move(state.side_one, ours), engine_move(state.side_two, theirs)

        observed = _first_mover(events, us, self.them)
        if observed is not None:
            ours_sig = _signature(state, our_move, "none")
            theirs_sig = _signature(state, "none", their_move)
            if ours_sig is not None and theirs_sig is not None and ours_sig != theirs_sig:
                orders = {_order(o.instruction_list, ours_sig, theirs_sig)
                          for o in generate_instructions(state, our_move, their_move)}
                if observed not in orders:
                    return False

        # Multi-hit totals can't be checked until BattleState carries hit counts (parked: contract `hit_count`).
        multihit = lambda move: "multihit" in MOVES[move]
        we_first = observed != "them"
        (our_max, our_crit), (their_max, their_crit) = calculate_damage(state, our_move, their_move, we_first)
        maxhp = state.side_two.pokemon[n].maxhp
        took = _hit_drop(events, start, self.them, n, us)
        if took is not None and not multihit(our_move.removesuffix("-tera")) and not _within(took, our_crit if took[2] else our_max, maxhp):
            return False
        our_maxhp = state.side_one.pokemon[int(state.side_one.active_index)].maxhp
        dealt = _hit_drop(events, start, us, start["sides"][us]["active"], self.them)
        if dealt is not None and not multihit(their_move.removesuffix("-tera")) and not _within(dealt, their_crit if dealt[2] else their_max, our_maxhp):
            return False
        return True

    def scenarios(self, k: int = 5) -> list[tuple[float, list[PokemonSet]]]:
        """Sets to simulate (feature 05): the active's top k, each with every benched Pokémon at its best guess."""
        active = self.previous["active"]
        best = [max(c, key=lambda sw: sw[1])[0] for c in self.candidates]
        top = sorted(self.candidates[active], key=lambda sw: -sw[1])[:k]
        total = sum(w for _, w in top)
        return [(w / total, best[:active] + [s] + best[active + 1:]) for s, w in top]


def _their_action(state: State, events: list[Event], them: str, n: int) -> Action | None:
    """The opponent's move last turn as an Action on the replayed state; None if it switched or didn't move."""
    used = next((e for e in events if e["type"] == "move" and e["side"] == them and e["pokemon"] == n), None)
    if used is None or any(e["type"] == "switch" and e["side"] == them for e in events[: events.index(used)]):
        return None
    # The hard filter has already kept only sets that contain every revealed move, this one included.
    ids = [m.id for m in state.side_two.pokemon[int(state.side_two.active_index)].moves]
    tera = any(e["type"] == "reveal" and e["side"] == them and (e["source"] or "").startswith("tera:") for e in events)
    return Action("move", ids.index(used["move"]) + 1, tera=tera)


def _first_mover(events: list[Event], us: str, them: str) -> str | None:
    movers = [e["side"] for e in events if e["type"] == "move"]
    if us not in movers or them not in movers:
        return None  # one side didn't act, so there's no order to compare
    return "us" if movers.index(us) < movers.index(them) else "them"


def _signature(state: State, side_one_move: str, side_two_move: str) -> str | None:
    """The kind of the first instruction a side's move makes when it acts alone, e.g. "Damage SideTwo"."""
    outcomes = generate_instructions(state, side_one_move, side_two_move)
    instructions = [str(i) for i in outcomes[0].instruction_list] if outcomes else []
    return instructions[0].split(":")[0] if instructions else None


def _order(instructions, ours: str, theirs: str) -> str | None:
    """Who acted first in one engine outcome; None if a side never acted in it (e.g. it flinched)."""
    text = [str(i).split(":")[0] for i in instructions]
    if ours not in text or theirs not in text:
        return None
    return "us" if text.index(ours) < text.index(theirs) else "them"


def _hit_drop(events: list[Event], start: BattleState, target_side: str, slot: int, attacker: str):
    """(hp % before, hp % after, crit) for the first hit the attacker's move did to the target; None if none."""
    hp = start["sides"][target_side]["pokemon"][slot]["hp_percent"]
    attacked = False
    for e in events:
        if e["type"] == "move" and e["side"] == attacker:
            attacked = True
        elif e["side"] == target_side and e["pokemon"] == slot and e["type"] in ("damage", "heal"):
            if attacked and e["type"] == "damage" and e["source"] == "move":
                if e["effectiveness"] == "immune":
                    return None
                return hp, e["hp_percent"], e["crit"]
            hp = e["hp_percent"]
        elif e["type"] == "switch" and e["side"] == target_side:
            return None
    return None


def _within(drop: tuple[int, int, bool], max_damage: int, maxhp: int) -> bool:
    before, after, _ = drop
    seen = before - after
    low, high = 100 * MIN_ROLL * max_damage / maxhp, 100 * max_damage / maxhp
    if after == 0:
        return high + PERCENT_SLACK >= seen  # a KO only shows the damage was at least the HP left
    return low - PERCENT_SLACK <= seen <= high + PERCENT_SLACK


def _to_set(c: CandidateSet) -> PokemonSet:
    return PokemonSet(moves=tuple(c["moves"]), item=c["item"] or "none", ability=c["ability"],
                      tera_type=c["tera_type"], nature=c["spread"]["nature"], evs=tuple(c["spread"]["evs"]))


def _fits(s: PokemonSet, mon: dict, rules: set[str]) -> bool:
    if not set(mon["revealed_moves"]) <= set(s.moves):
        return False
    # "" means it holds nothing now (knocked off, consumed), which says nothing about what it started with.
    if mon["item"] and s.item != mon["item"]:
        return False
    if mon["ability"] and s.ability != mon["ability"]:
        return False
    if mon["tera_type"] and s.tera_type != mon["tera_type"]:
        return False
    for rule in rules:
        if rule.startswith("item:") and s.item != rule[5:]:
            return False
    if "not_choice" in rules and s.item in CHOICE_ITEMS:
        return False
    if "not_av" in rules and s.item == "assaultvest":
        return False
    if "not_leftovers" in rules and s.item == "leftovers":
        return False
    if "boots" in rules and s.item != "heavydutyboots" and s.ability != "magicguard":
        return False
    if "not_boots" in rules and s.item == "heavydutyboots":
        return False
    return True


def _hit_by_rocks(events: list, n: int) -> bool:
    return any(e["type"] == "damage" and e["pokemon"] == n and e["source"] == "stealthrock" for e in events)


def _rebuild(usage: Usage, mon: dict) -> Candidates:
    """Sets combined from usage shares that agree with what's revealed (03's fallback when no candidate fits)."""
    top = lambda shares, n: sorted(shares.items(), key=lambda kv: -kv[1])[:n]
    revealed = mon["revealed_moves"]
    moves = revealed + [m for m, _ in top(usage["moves"], len(usage["moves"])) if m not in revealed]
    moves = tuple(moves[:4])
    has_status = any(MOVES[m]["category"] == "Status" for m in moves)
    items = [(mon["item"], 1.0)] if mon["item"] else top(usage["items"], REBUILD_ITEMS)
    teras = [(mon["tera_type"], 1.0)] if mon["tera_type"] else top(usage["tera_types"], REBUILD_TERAS)
    ability = mon["ability"] or top(usage["abilities"], 1)[0][0]
    spreads = sorted(usage["spreads"], key=lambda sp: -sp[1])[:REBUILD_SPREADS]
    sets = []
    for (item, pi), (tera, pt), (spread, ps) in product(items, teras, spreads):
        # A Choice item or Assault Vest blocks status moves, so they can't be in the same set.
        if has_status and (item in CHOICE_ITEMS or item == "assaultvest"):
            continue
        sets.append((PokemonSet(moves=moves, item=item, ability=ability, tera_type=tera,
                                nature=spread["nature"], evs=tuple(spread["evs"])), pi * pt * ps))
    return sets


def _normalised(candidates: Candidates) -> Candidates:
    total = sum(w for _, w in candidates)
    return [(s, w / total) for s, w in candidates] if total else candidates
