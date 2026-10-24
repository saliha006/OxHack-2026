"""Evaluation harness: our agent and its ablations against baselines and each other, sharded and resumable.

    uv run python -m bot.eval run --shards 6            # every match, skipping games already in runs/
    uv run python -m bot.eval run --matches headline --games 20
    uv run python -m bot.eval report                    # merge every machine's files into one table
"""
import argparse
import asyncio
import copy
import json
import logging
import math
import os
import platform
import random
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from poke_env import AccountConfiguration
from poke_env.player import MaxBasePowerPlayer, RandomPlayer, SimpleHeuristicsPlayer

from bot.player import AgentPlayer
from bot.smoke import priors_from_team
from decision.agent import Agent
from decision.belief import Belief


class FrozenBelief(Belief):
    """Ablation: keeps the usage-stats prior for the whole battle, ignoring everything the opponent reveals."""

    def __init__(self, priors, battle):
        super().__init__(priors, battle)
        self.prior = copy.deepcopy(self.candidates)

    def update(self, battle):
        super().update(battle)  # still tracks the active slot, which scenarios() needs
        self.candidates = copy.deepcopy(self.prior)


class FlatBelief(FrozenBelief):
    """Ablation: knows which sets each species runs but not how common each one is."""

    def __init__(self, priors, battle):
        super().__init__(priors, battle)
        self.prior = [[(s, 1 / len(slot)) for s, _ in slot] for slot in self.prior]
        self.candidates = copy.deepcopy(self.prior)


class AblatedAgent(Agent):
    """An Agent whose belief is one of the ablations; Agent only builds a plain Belief when it has none yet."""

    def __init__(self, priors, belief_cls, **kwargs):
        super().__init__(priors, **kwargs)
        self.belief_cls = belief_cls

    def choose(self, request, battle):
        if self.belief is None and not request.get("wait"):
            try:
                self.belief = self.belief_cls(self.priors, battle)
            except Exception:
                pass  # Agent.choose meets the same error inside its own fallback and logs it there
        return super().choose(request, battle)


ARMS = {
    "full": lambda priors, budget: Agent(priors, budget=budget),
    "prior": lambda priors, budget: AblatedAgent(priors, FrozenBelief, budget=budget),
    "flat": lambda priors, budget: AblatedAgent(priors, FlatBelief, budget=budget),
    "k1": lambda priors, budget: Agent(priors, k=1, budget=budget),
}
BASELINES = {"simpleheuristics": SimpleHeuristicsPlayer, "maxbasepower": MaxBasePowerPlayer, "random": RandomPlayer}

# match -> (our arm, opponent arm or baseline, games). Same team on both sides, so the result measures play, not teams.
MATCHES = {
    "headline": ("full", "simpleheuristics", 300),
    "updating": ("full", "prior", 200),
    "usage": ("prior", "flat", 200),
    "uncertainty": ("full", "k1", 200),
    "maxbasepower": ("full", "maxbasepower", 100),
    "random": ("full", "random", 30),
}


def done_games(runs: Path, match: str) -> set[int]:
    done = set()
    for path in runs.glob(f"eval-{match}-*.jsonl"):
        for line in path.read_text(encoding="utf-8").splitlines():
            done.add(json.loads(line)["game"])
    return done


def shard_games(games: int, shards: int, done: set[int]) -> list[list[int]]:
    todo = [g for g in range(games) if g not in done]
    return [todo[s::shards] for s in range(shards) if todo[s::shards]]


def play_shard(match: str, game_ids: list[int], teams: list[str], priors: dict, budget: float,
               runs: str, machine: str, shard: int) -> None:
    """One process: plays its games one at a time and appends a result line per game, so a crash loses one game."""
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    ours_arm, theirs_name, _ = MATCHES[match]
    tag = f"{match[:6]}{shard}"
    ours = AgentPlayer(make_agent=lambda: ARMS[ours_arm](priors, budget), runs_dir=runs,
                       account_configuration=AccountConfiguration(f"ox {tag} a", None), battle_format="gen9ou",
                       team=teams[0], start_timer_on_battle_start=True)
    opponent_config = dict(account_configuration=AccountConfiguration(f"ox {tag} b", None), battle_format="gen9ou",
                           team=teams[0])
    if theirs_name in ARMS:
        theirs = AgentPlayer(make_agent=lambda: ARMS[theirs_name](priors, budget), runs_dir=runs, **opponent_config)
    else:
        theirs = BASELINES[theirs_name](**opponent_config)

    out = Path(runs) / f"eval-{match}-{machine}-{shard}.jsonl"
    with open(out, "a", encoding="utf-8", buffering=1) as results:
        for g in game_ids:
            team = g % len(teams)
            ours.update_team(teams[team])
            theirs.update_team(teams[team])
            # Alternating who challenges alternates p1 and p2.
            first, second = (ours, theirs) if g % 2 == 0 else (theirs, ours)
            asyncio.run(first.battle_against(second, n_battles=1))
            s = ours.summaries[-1]
            winner = "tie" if s["won"] is None else ("ours" if s["won"] else "theirs")
            results.write(json.dumps({"match": match, "game": g, "team": team, "winner": winner, **s}) + "\n")


def wilson(wins: float, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = wins / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (centre - half, centre + half)


def team_bootstrap(rows: list[dict], draws: int = 2000, seed: int = 0) -> tuple[float, float]:
    """95% interval that resamples whole teams, since games on the same team aren't independent."""
    by_team: dict[int, list[float]] = {}
    for r in rows:
        by_team.setdefault(r["team"], []).append(score(r))
    teams = list(by_team.values())
    rng = random.Random(seed)
    rates = []
    for _ in range(draws):
        picked = [rng.choice(teams) for _ in teams]
        rates.append(sum(map(sum, picked)) / sum(map(len, picked)))
    rates.sort()
    return (rates[int(0.025 * draws)], rates[int(0.975 * draws) - 1])


def score(row: dict) -> float:
    return {"ours": 1.0, "tie": 0.5, "theirs": 0.0}[row["winner"]]


def report(runs: Path) -> dict:
    table = {}
    for match, (ours, theirs, planned) in MATCHES.items():
        rows = [json.loads(line) for path in sorted(runs.glob(f"eval-{match}-*.jsonl"))
                for line in path.read_text(encoding="utf-8").splitlines()]
        if not rows:
            continue
        n = len(rows)
        wins = sum(map(score, rows))
        decisions = sum(r["decisions"] for r in rows)
        p99s = sorted(r["think_p99_ms"] for r in rows if r["think_p99_ms"] is not None)
        table[match] = {
            "ours": ours, "theirs": theirs, "games": n, "planned": planned, "win_rate": wins / n,
            "wilson_95": wilson(wins, n), "team_bootstrap_95": team_bootstrap(rows),
            "teams": len({r["team"] for r in rows}),
            "fallback_rate": sum(r["fallbacks"] for r in rows) / decisions if decisions else None,
            "worst_game_p99_ms": p99s[-1] if p99s else None,
        }
    return table


def load_teams(path: Path) -> list[str]:
    files = sorted(path.iterdir()) if path.is_dir() else [path]
    return [f.read_text(encoding="utf-8") for f in files if f.is_file()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--matches", nargs="+", default=list(MATCHES), choices=list(MATCHES))
    run.add_argument("--games", type=int, help="override every match's planned game count")
    # Until the data layer's pool exists, every game uses the one stand-in team.
    run.add_argument("--teams", default="bot/teams/standin-gen9ou.txt", help="a team file or a folder of them")
    run.add_argument("--priors", default="data/set_candidates.json")
    run.add_argument("--priors-from-team", action="store_true", help="test only: priors = the first team's exact sets")
    # Measured think time is ~65 ms at p50, so 1 s rarely binds and lets six shards share a laptop.
    run.add_argument("--budget", type=float, default=1.0)
    run.add_argument("--shards", type=int, default=max(1, (os.cpu_count() or 4) - 2))
    run.add_argument("--machine", default=platform.node().lower() or "local")
    sub.add_parser("report")
    parser.add_argument("--runs", default="runs")
    args = parser.parse_args(argv)
    runs = Path(args.runs)
    runs.mkdir(parents=True, exist_ok=True)

    if args.command == "report":
        table = report(runs)
        (runs / "eval-summary.json").write_text(json.dumps(table, indent=2), encoding="utf-8")
        for match, r in table.items():
            lo, hi = r["wilson_95"]
            blo, bhi = r["team_bootstrap_95"]
            print(f"{match:13} {r['ours']} vs {r['theirs']}: {r['win_rate']:.1%} over {r['games']}/{r['planned']} games "
                  f"(Wilson {lo:.1%}-{hi:.1%}, team bootstrap {blo:.1%}-{bhi:.1%}, {r['teams']} teams), "
                  f"fallbacks {r['fallback_rate']:.1%}")
        return 0

    teams = load_teams(Path(args.teams))
    priors = priors_from_team(teams[0]) if args.priors_from_team else json.loads(Path(args.priors).read_text(encoding="utf-8"))
    with ProcessPoolExecutor(max_workers=args.shards) as pool:
        jobs = []
        for match in args.matches:
            games = args.games or MATCHES[match][2]
            for shard, ids in enumerate(shard_games(games, args.shards, done_games(runs, match))):
                jobs.append(pool.submit(play_shard, match, ids, teams, priors, args.budget, str(runs), args.machine, shard))
        for job in jobs:
            job.result()
    return 0


if __name__ == "__main__":
    sys.exit(main())
