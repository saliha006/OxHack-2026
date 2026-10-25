"""Demo: a live battle with every decision streamed to the terminal, or a saved battle replayed offline.

    uv run python -m bot.demo live --priors-from-teams        # watch the printed URL in the Showdown client
    uv run python -m bot.demo replay runs/battle-gen9ou-12.jsonl
"""
import argparse
import asyncio
import json
import random
import sys
import time
from collections.abc import Callable
from pathlib import Path

from poke_env import AccountConfiguration

from bot.eval import BASELINES, load_teams
from bot.player import AgentPlayer
from bot.smoke import priors_from_teams
from decision.agent import Agent

# Trace fields this module renders itself; any other field (e.g. the agent's own predictions) is shown as it comes.
OWN_FIELDS = {"turn", "kind", "choice", "label", "think_ms", "fallback", "state", "request", "decision_id"}


def active_text(side: dict) -> str:
    if side.get("active") is None:
        return "-"
    p = side["pokemon"][side["active"]]
    status = f" {p['status']}" if p.get("status") else ""
    return f"{p['species']} {p['hp_percent']}%{status}"


def remaining(side: dict) -> int:
    return sum(p["hp_percent"] > 0 for p in side["pokemon"])


def show(value) -> str:
    if isinstance(value, float):
        text = f"{value:.3g}"
    elif isinstance(value, str):
        text = value
    else:
        text = json.dumps(value)
    return text if len(text) <= 100 else text[:97] + "..."


def format_line(line: dict) -> str:
    if line["kind"] == "observation":
        reply = line.get("opponent_actions")
        return f"    Opponent reply to {line['decision_id']}: {show(reply) if reply else 'unknown'}"
    if line.get("kind") == "end":
        result = "won" if line["won"] else "lost" if line["won"] is False else "tied"
        return (f"Game over: {result} in {line['turns']} turns · {line['fallbacks']}/{line['decisions']} fallbacks · "
                f"think p50 {line['think_p50_ms']} ms, p99 {line['think_p99_ms']} ms")
    if line.get("kind") == "retry":
        return f"  Showdown rejected the choice; sent {line['choice']} instead"
    state = line["state"]
    us = state["us"]
    them = "p2" if us == "p1" else "p1"
    flags = ", fallback" if line.get("fallback") else ""
    lines = [f"Turn {state['turn']:>3} · {line.get('label') or line['choice']}  ({line['think_ms']:.0f} ms{flags})",
             f"    {active_text(state['sides'][us])} ({remaining(state['sides'][us])} left)  vs  "
             f"{active_text(state['sides'][them])} ({remaining(state['sides'][them])} left)"]
    lines += [f"    {key}: {show(value)}" for key, value in line.items() if key not in OWN_FIELDS]
    return "\n".join(lines)


def replay(path: Path, delay: float, out: Callable[[str], None] = print, sleep: Callable[[float], None] = time.sleep):
    for text in path.read_text(encoding="utf-8").splitlines():
        line = json.loads(text)
        out(format_line(line))
        if line.get("kind") not in ("end", "retry", "observation"):
            sleep(delay)


def live(team: str, priors: dict, opponent: str, budget: float, pace: float, runs: str,
         backend: str = "one_ply", worlds: int = 1, search_ms: int = 150, engine_threads: int = 1) -> dict:
    watched = set()

    def on_decision(tag: str, line: dict) -> None:
        if tag not in watched:
            watched.add(tag)
            print(f"Watch it live: http://localhost:8000/{tag}  (the Showdown client needs internet)")
        print(format_line(line))
        # Slows our side down so a judge can follow each turn in the client.
        time.sleep(pace)

    ours = AgentPlayer(make_agent=lambda: Agent(priors, budget=budget, backend=backend, mcts_worlds=worlds,
                                               search_ms=search_ms, engine_threads=engine_threads),
                       runs_dir=runs, on_decision=on_decision,
                       account_configuration=AccountConfiguration("oxhack demo", None), battle_format="gen9ou",
                       team=team, start_timer_on_battle_start=True)
    rival = BASELINES[opponent](account_configuration=AccountConfiguration("oxhack rival", None),
                                battle_format="gen9ou", team=team)
    asyncio.run(ours.battle_against(rival, n_battles=1))
    summary = ours.summaries[-1]
    print(format_line({"kind": "end", **summary}))
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    play = sub.add_parser("live")
    play.add_argument("--opponent", default="simpleheuristics", choices=list(BASELINES))
    play.add_argument("--teams", default="bot/teams/standin", help="a team file or a folder; one is picked at random")
    play.add_argument("--priors", default="data/set_candidates.json")
    play.add_argument("--priors-from-teams", action="store_true",
                      help="stand-in: priors = every set across the teams, weighted by how often it appears")
    play.add_argument("--budget", type=float, default=3.0)
    play.add_argument("--backend", choices=("one_ply", "mcts"), default="one_ply")
    play.add_argument("--worlds", type=int, default=1)
    play.add_argument("--search-ms", type=int, default=150)
    play.add_argument("--engine-threads", type=int, default=1)
    play.add_argument("--pace", type=float, default=1.5, help="seconds to wait after each of our decisions")
    play.add_argument("--runs", default="runs")
    again = sub.add_parser("replay")
    again.add_argument("trace", type=Path)
    again.add_argument("--delay", type=float, default=1.0, help="seconds between turns")
    args = parser.parse_args(argv)

    if args.command == "replay":
        replay(args.trace, args.delay)
        return 0
    teams = load_teams(Path(args.teams))
    priors = priors_from_teams(teams) if args.priors_from_teams else json.loads(Path(args.priors).read_text(encoding="utf-8"))
    options = () if (args.backend, args.worlds, args.search_ms, args.engine_threads) == ("one_ply", 1, 150, 1) else (
        args.backend, args.worlds, args.search_ms, args.engine_threads)
    live(random.choice(teams), priors, args.opponent, args.budget, args.pace, args.runs, *options)
    return 0


if __name__ == "__main__":
    sys.exit(main())
