"""Demo: a live battle with every decision streamed to the terminal, or a saved battle replayed offline.

    uv run python -m bot.demo live --priors-from-teams        # watch the printed URL in the Showdown client
    uv run python -m bot.demo live --opponent human           # a person challenges "oxhack demo" (gen9ou) in the browser
    uv run python -m bot.demo replay runs/battle-gen9ou-12.jsonl
"""
import argparse
import asyncio
import json
import random
import sys
import time
from collections import Counter
from collections.abc import Callable
from pathlib import Path

from poke_env import AccountConfiguration

from bot.eval import BASELINES, load_teams
from bot.player import AgentPlayer, label
from bot.smoke import priors_from_teams
from decision.agent import Agent

# Trace fields this module renders itself; any other field (e.g. the agent's own predictions) is shown as it comes.
OWN_FIELDS = {"turn", "kind", "choice", "label", "think_ms", "fallback", "state", "request", "decision_id"}
HUMAN = "human"


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
    if "search_support" in line:
        lines += thinking(line, state["sides"][them])
    else:
        lines += [f"    {key}: {show(value)}" for key, value in line.items() if key not in OWN_FIELDS]
    return "\n".join(lines)


def top(shares: dict, name: Callable[[str], str], n: int = 3) -> str:
    best = sorted(shares.items(), key=lambda kv: -kv[1])[:n]
    return " · ".join(f"{name(choice)} {share:.0%}" for choice, share in best) or "-"


def thinking(line: dict, their_side: dict) -> list[str]:
    """The search's view in words; the raw trace (every world's visits) stays in the .jsonl for replay."""
    request = line.get("request") or {}
    worlds = f"{line['usable_worlds']}/{line['requested_worlds']} worlds"
    lines = [f"    Weighing: {top(line['search_support'], lambda c: label(request, c) or c)}  ({worlds})",
             f"    Expects them: {top(line['opponent_support'], lambda c: c.replace('-tera', ' + Tera'))}"]
    if their_side.get("active") is not None:
        species = their_side["pokemon"][their_side["active"]]["species"]
        guesses = [mon for world in line.get("sampled_worlds", []) for mon in world if mon.get("species") == species]
        if guesses:
            item, n = Counter(mon.get("item") for mon in guesses).most_common(1)[0]
            tera, m = Counter(mon.get("tera_type") for mon in guesses).most_common(1)[0]
            lines.append(f"    Guessing their {species}: {item} ({n}/{len(guesses)} worlds) · Tera {tera} ({m}/{len(guesses)})")
    if line.get("fallback_reason"):
        lines.append(f"    Fallback: {line['fallback_reason']}")
    return lines


def replay(path: Path, delay: float, out: Callable[[str], None] = print, sleep: Callable[[float], None] = time.sleep):
    for text in path.read_text(encoding="utf-8").splitlines():
        line = json.loads(text)
        out(format_line(line))
        if line.get("kind") not in ("end", "retry", "observation"):
            sleep(delay)


def chat_text(line: dict) -> str:
    # Showdown drops chat messages over 300 characters.
    return " | ".join(part.strip() for part in format_line(line).splitlines())[:300]


def live(team: str, priors: dict, opponent: str, budget: float, pace: float, runs: str,
         backend: str = "mcts", worlds: int = 8, search_ms: int = 150, engine_threads: int = 1,
         tera_min_wins: int = 0) -> dict:
    watched = set()
    chats = set()  # the loop only keeps weak references to tasks

    def on_decision(tag: str, line: dict) -> None:
        if tag not in watched:
            watched.add(tag)
            print(f"Watch it live: http://localhost:8000/{tag}  (the Showdown client needs internet)")
        print(format_line(line))
        if line.get("kind") not in ("observation", "retry"):
            # The battle chat sits beside the field in the browser, so viewers see the search's view too.
            task = asyncio.get_running_loop().create_task(ours.ps_client.send_message(chat_text(line), tag))
            chats.add(task)
            task.add_done_callback(chats.discard)
        # Slows our side down so a judge can follow each turn in the client.
        time.sleep(pace)

    ours = AgentPlayer(make_agent=lambda: Agent(priors, budget=budget, backend=backend, mcts_worlds=worlds,
                                               search_ms=search_ms, engine_threads=engine_threads,
                                               tera_min_wins=tera_min_wins),
                       runs_dir=runs, on_decision=on_decision,
                       account_configuration=AccountConfiguration("oxhack demo", None), battle_format="gen9ou",
                       team=team, start_timer_on_battle_start=True)
    if opponent == HUMAN:
        print('Waiting for a challenge: in the Showdown client, /challenge oxhack demo, gen9ou')
        asyncio.run(ours.accept_challenges(None, 1))
    else:
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
    play.add_argument("--opponent", default="simpleheuristics", choices=[*BASELINES, HUMAN])
    play.add_argument("--teams", default="bot/teams/standin", help="a team file or a folder; one is picked at random")
    play.add_argument("--priors", default="data/set_candidates.json")
    play.add_argument("--priors-from-teams", action="store_true",
                      help="stand-in: priors = every set across the teams, weighted by how often it appears")
    play.add_argument("--budget", type=float, default=3.0)
    play.add_argument("--backend", choices=("one_ply", "mcts"), default="mcts")
    play.add_argument("--worlds", type=int, default=8)
    play.add_argument("--search-ms", type=int, default=150)
    play.add_argument("--engine-threads", type=int, default=1)
    play.add_argument("--tera-min-wins", type=int, default=0, help="Tera only if it tops this many worlds (0 = off)")
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
    chosen = (args.backend, args.worlds, args.search_ms, args.engine_threads, args.tera_min_wins)
    options = () if chosen == ("mcts", 8, 150, 1, 0) else chosen
    live(random.choice(teams), priors, args.opponent, args.budget, args.pace, args.runs, *options)
    return 0


if __name__ == "__main__":
    sys.exit(main())
