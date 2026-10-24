"""Smoke battle: our agent vs poke-env's RandomPlayer on the local server.

    uv run python -m bot.smoke --games 10
"""
import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

from poke_env import AccountConfiguration
from poke_env.player import RandomPlayer
from poke_env.teambuilder import Teambuilder

from bot.parser import to_id
from bot.player import AgentPlayer
from decision.agent import Agent


def priors_from_teams(teams: list[str]) -> dict:
    """Stand-in priors: every set a species runs across the teams, weighted by how often it appears.

    In a mirror match on one team it tells belief the truth, so a single team tests plumbing, not play.
    """
    counts: dict[str, dict[str, tuple[dict, int]]] = {}
    for team in teams:
        for mon in Teambuilder.parse_showdown_team(team):
            moves = [to_id(m) for m in mon.moves]
            candidate = {"moves": moves, "item": to_id(mon.item), "ability": to_id(mon.ability),
                         "tera_type": mon.tera_type.lower(), "spread": {"nature": to_id(mon.nature), "evs": list(mon.evs)}}
            sets = counts.setdefault(to_id(mon.species or mon.nickname), {})
            key = json.dumps(candidate, sort_keys=True)
            sets[key] = (candidate, sets.get(key, (candidate, 0))[1] + 1)
    species = {}
    for name, sets in counts.items():
        total = sum(n for _, n in sets.values())
        ranked = sorted(sets.values(), key=lambda cn: -cn[1])
        share = lambda pick: {k: round(sum(n for c, n in ranked if pick(c) == k) / total, 3) for k in {pick(c) for c, _ in ranked}}
        moves: dict[str, float] = {}
        for c, n in ranked:
            for m in c["moves"]:
                moves[m] = moves.get(m, 0) + n / total
        species[name] = {
            "sets": [{"weight": n / total, **c} for c, n in ranked],
            "usage": {"moves": moves, "items": share(lambda c: c["item"]), "abilities": share(lambda c: c["ability"]),
                      "tera_types": share(lambda c: c["tera_type"]), "spreads": [(c["spread"], n / total) for c, n in ranked]},
        }
    return {"source": {"format": "gen9ou", "month": "teams", "cutoff": 0, "battles": 0}, "species": species}


def run(games: int, team: str, priors: dict, budget: float, runs_dir: str) -> list[dict]:
    agent_player = AgentPlayer(
        make_agent=lambda: Agent(priors, budget=budget),
        runs_dir=runs_dir,
        account_configuration=AccountConfiguration("oxhack agent", None),
        battle_format="gen9ou",
        team=team,
        # Showdown's own timer ends a battle that stalls, so one hang can't freeze an unattended run.
        start_timer_on_battle_start=True,
    )
    opponent = RandomPlayer(account_configuration=AccountConfiguration("oxhack random", None),
                            battle_format="gen9ou", team=team)
    asyncio.run(agent_player.battle_against(opponent, n_battles=games))
    return agent_player.summaries


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--games", type=int, default=10)
    parser.add_argument("--team", default="bot/teams/standin-gen9ou.txt")
    # The example priors cover two species; data/set_candidates.json replaces them once the data layer ships it.
    parser.add_argument("--priors", default="contracts/examples/set_candidates_example.json")
    parser.add_argument("--priors-from-team", action="store_true", help="test only: priors = the team's exact sets")
    parser.add_argument("--budget", type=float, default=3.0, help="decision deadline per turn, seconds")
    parser.add_argument("--max-fallback", type=float, default=0.05, help="fail above this share of decisions")
    parser.add_argument("--runs", default="runs")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

    team = Path(args.team).read_text(encoding="utf-8").strip()
    priors = priors_from_teams([team]) if args.priors_from_team else json.loads(Path(args.priors).read_text(encoding="utf-8"))
    summaries = run(args.games, team, priors, args.budget, args.runs)

    for s in summaries:
        print(f"{s['tag']}: {'won' if s['won'] else 'lost'} in {s['turns']} turns, "
              f"{s['fallbacks']}/{s['decisions']} fallbacks, think p50 {s['think_p50_ms']} ms p99 {s['think_p99_ms']} ms")
    decisions = sum(s["decisions"] for s in summaries)
    fallbacks = sum(s["fallbacks"] for s in summaries)
    rate = fallbacks / decisions if decisions else 1.0
    wins = sum(bool(s["won"]) for s in summaries)
    print(f"{len(summaries)}/{args.games} games finished, {wins} won, fallback rate {rate:.1%}")
    return 0 if len(summaries) == args.games and rate <= args.max_fallback else 1


if __name__ == "__main__":
    sys.exit(main())
