"""Evaluation harness: our agent and its ablations against baselines and each other, blind, sharded and resumable.

    uv run python -m bot.eval run --shards 6            # every pairing, skipping games already in runs/eval/
    uv run python -m bot.eval run --pairings headline --games 20
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
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from poke_env import AccountConfiguration
from poke_env.player import MaxBasePowerPlayer, RandomPlayer, SimpleHeuristicsPlayer

from bot.player import AgentPlayer
from bot.smoke import priors_from_teams
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


class Jitter:
    """Mixin: waits a random, right-skewed time before each move, so opponents don't all answer instantly."""

    jitter_rng: random.Random

    async def choose_move(self, battle):
        # Median 0.25 s with a long tail, capped well inside Showdown's per-turn timer.
        await asyncio.sleep(min(self.jitter_rng.lognormvariate(math.log(0.25), 1.0), 3.0))
        return super().choose_move(battle)


class EpsilonMix:
    """Mixin: plays a uniformly random legal move with probability `eps`, else the bot's own move; a strength dial."""

    eps: float
    move_rng: random.Random

    def choose_move(self, battle):
        if self.move_rng.random() < self.eps:
            return self.choose_random_move(battle)
        return super().choose_move(battle)


def _mixed(base, eps: float):
    return type(f"{base.__name__}Eps{round(eps * 100)}", (EpsilonMix, base), {"eps": eps})


ARMS = {
    "full": lambda priors, budget: Agent(priors, budget=budget),
    "prior": lambda priors, budget: AblatedAgent(priors, FrozenBelief, budget=budget),
    "flat": lambda priors, budget: AblatedAgent(priors, FlatBelief, budget=budget),
    "k1": lambda priors, budget: Agent(priors, k=1, budget=budget),
}
# Mix levels are deliberately uneven, so strength doesn't step up by a fixed amount; mb46 overlaps the sh levels.
BASELINES = {"simpleheuristics": SimpleHeuristicsPlayer, "maxbasepower": MaxBasePowerPlayer, "random": RandomPlayer,
             "sh12": _mixed(SimpleHeuristicsPlayer, 0.12), "sh31": _mixed(SimpleHeuristicsPlayer, 0.31),
             "sh58": _mixed(SimpleHeuristicsPlayer, 0.58), "sh83": _mixed(SimpleHeuristicsPlayer, 0.83),
             "mb46": _mixed(MaxBasePowerPlayer, 0.46)}

# pairing -> (side a, side b, games); results are from a's point of view, and b is the jittered opponent.
PAIRINGS = {
    "headline": ("full", "simpleheuristics", 300),
    "updating": ("full", "prior", 200),
    "usage": ("prior", "flat", 200),
    "uncertainty": ("full", "k1", 200),
    "maxbasepower": ("full", "maxbasepower", 100),
    "random": ("full", "random", 30),
}
# Rough weakest-to-strongest order. Only neighbours play each other; the rating fit works out the true order.
LADDER = ["random", "mb46", "sh83", "maxbasepower", "sh58", "sh31", "sh12", "simpleheuristics", "flat", "prior", "k1", "full"]


def ladder_pairings(core: dict, ladder: list[str], vs_agent: int = 40, neighbours: int = 30) -> dict:
    """The agent against every level, plus each neighbouring pair, skipping pairs the core matches already play."""
    played = {frozenset((a, b)) for a, b, _ in core.values()}
    extra = {}
    for level in ladder[:-1]:
        if frozenset(("full", level)) not in played:
            extra[f"full~{level}"] = ("full", level, vs_agent)
            played.add(frozenset(("full", level)))
    for low, high in zip(ladder, ladder[1:]):
        if frozenset((low, high)) not in played:
            extra[f"{low}~{high}"] = (low, high, neighbours)
            played.add(frozenset((low, high)))
    return extra


PAIRINGS |= ladder_pairings(PAIRINGS, LADDER)

FOUL_PLAY = Path(__file__).parent.parent / "foul-play"
# Search-time bands in ms, deliberately uneven; each Foul Play process draws its own time inside its band.
FOUL_PLAY_LEVELS = {"fplow": (40, 80), "fpmid": (150, 260), "fphigh": (450, 700)}
for level in FOUL_PLAY_LEVELS:
    PAIRINGS[f"full~{level}"] = ("full", level, 50)
    PAIRINGS[f"prior~{level}"] = ("prior", level, 20)


class FoulPlay:
    """A Foul Play bot in its own process, accepting our challenges and playing its team list in our game order."""

    def __init__(self, search_ms: int, team_paths: list[Path], runs: Path, username: str):
        self.username = username
        self.log = runs / f"{username}.log"
        team_list = runs / f"{username}.teams.txt"
        team_list.write_text("".join(f"{p.resolve()}\n" for p in team_paths), encoding="utf-8")
        python = FOUL_PLAY / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        self.output = open(self.log, "w", encoding="utf-8")
        self.process = subprocess.Popen(
            [str(python), "run.py", "--websocket-uri", "ws://localhost:8000/showdown/websocket",
             "--ps-username", username, "--bot-mode", "accept_challenge", "--pokemon-format", "gen9ou",
             "--team-list", str(team_list.resolve()), "--search-time-ms", str(search_ms),
             "--run-count", str(len(team_paths)), "--log-level", "INFO"],
            cwd=FOUL_PLAY, stdout=self.output, stderr=subprocess.STDOUT)
        self.games = 0

    def wait_ready(self, timeout: float = 180.0) -> None:
        """Block until Foul Play waits for its next challenge; a challenge sent earlier would find nobody to accept it."""
        deadline = time.monotonic() + timeout
        while self.log.read_text(encoding="utf-8").count("Waiting for a") <= self.games:
            if self.process.poll() is not None or time.monotonic() > deadline:
                raise RuntimeError(f"Foul Play {self.username} isn't ready; see {self.log}")
            time.sleep(0.5)
        self.games += 1

    def close(self) -> None:
        self.process.terminate()
        self.output.close()


def make_player(name: str, jittered: bool, priors: dict, budget: float, runs: str, team: str, rng: random.Random):
    # A random account name, so nothing in the battle tells either side what it's playing.
    config = dict(account_configuration=AccountConfiguration(f"ox{rng.getrandbits(32):08x}", None),
                  battle_format="gen9ou", team=team)
    if name in ARMS:
        cls, extra = AgentPlayer, {"make_agent": lambda: ARMS[name](priors, budget), "runs_dir": runs,
                                   "start_timer_on_battle_start": True}
    else:
        cls, extra = BASELINES[name], {}
    if jittered:
        cls = type(f"Jittered{cls.__name__}", (Jitter, cls), {})
    player = cls(**extra, **config)
    if jittered:
        player.jitter_rng = random.Random(rng.random())
    if isinstance(player, EpsilonMix):
        player.move_rng = random.Random(rng.random())
    return player


def done_games(runs: Path) -> set[tuple[str, int]]:
    return {(r["pairing"], r["game"]) for r in read_results(runs)}


def read_results(runs: Path) -> list[dict]:
    return [json.loads(line) for path in sorted((runs / "eval").glob("*.jsonl"))
            for line in path.read_text(encoding="utf-8").splitlines()]


def scored(rows: list[dict]) -> list[dict]:
    return [r for r in rows if r["winner"] != "void"]


def schedule(pairings: dict[str, int], shards: int, done: set[tuple[str, int]], seed: int) -> list[list[tuple[str, int]]]:
    """Every unplayed (pairing, game), shuffled together, so no shard plays one opponent in a predictable run."""
    todo = [(p, g) for p, games in pairings.items() for g in range(games) if (p, g) not in done]
    random.Random(seed).shuffle(todo)
    return [todo[s::shards] for s in range(shards) if todo[s::shards]]


def game_rng(seed: int, pairing: str, game: int) -> random.Random:
    # Seeded per game, so a resumed or re-sharded run gives each game the same team and side.
    return random.Random(f"{seed}:{pairing}:{game}")


def play_shard(games: list[tuple[str, int]], teams: list[str], priors: dict, budget: float, runs: str,
               machine: str, shard: int, seed: int) -> None:
    """One process: plays its games one at a time and appends a result line per game, so a crash loses one game."""
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    rng = random.Random(f"{seed}:{machine}:{shard}")
    out = Path(runs) / "eval" / f"{machine}-{shard}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    players = start_foul_play(games, teams, out.parent, rng, seed)
    try:
        with open(out, "a", encoding="utf-8", buffering=1) as results:
            for pairing, g in games:
                results.write(json.dumps(play_game(pairing, g, players, teams, priors, budget, runs, rng, seed)) + "\n")
    finally:
        for player in players.values():
            if isinstance(player, FoulPlay):
                player.close()


def start_foul_play(games: list[tuple[str, int]], teams: list[str], folder: Path, rng: random.Random,
                    seed: int) -> dict:
    """One Foul Play process per level this shard meets, given its teams in the order this shard will play them."""
    players = {}
    team_files = folder / "teams"
    team_files.mkdir(exist_ok=True)
    for i, team in enumerate(teams):
        (team_files / f"team_{i}.txt").write_text(team, encoding="utf-8")
    for level, (low, high) in FOUL_PLAY_LEVELS.items():
        mine = [(p, g) for p, g in games if PAIRINGS[p][1] == level]
        if mine:
            paths = [team_files / f"team_{game_rng(seed, p, g).randrange(len(teams))}.txt" for p, g in mine]
            players["b", level] = FoulPlay(rng.randint(low, high), paths, folder, f"ox{rng.getrandbits(32):08x}")
    return players


def play_game(pairing: str, g: int, players: dict, teams: list[str], priors: dict, budget: float, runs: str,
              rng: random.Random, seed: int) -> dict:
    a_name, b_name, _ = PAIRINGS[pairing]
    for role, name in (("a", a_name), ("b", b_name)):
        if (role, name) not in players:
            players[role, name] = make_player(name, role == "b", priors, budget, runs, teams[0], rng)
    a, b = players["a", a_name], players["b", b_name]
    pick = game_rng(seed, pairing, g)
    team = pick.randrange(len(teams))
    a.update_team(teams[team])
    if isinstance(b, FoulPlay):
        # Foul Play only accepts challenges, so our side is always p1 against it.
        b.wait_ready()
        asyncio.run(a.send_challenges(b.username, 1))
    else:
        b.update_team(teams[team])
        # Whoever challenges gets p1; a coin flip keeps sides balanced without a pattern.
        first, second = (a, b) if pick.random() < 0.5 else (b, a)
        asyncio.run(first.battle_against(second, n_battles=1))
    battle = list(a.battles.values())[-1]
    if battle.turn == 0:
        winner = "void"  # someone crashed or forfeited at team preview: no play to score
    else:
        winner = "tie" if battle.won is None else ("a" if battle.won else "b")
    line = {"pairing": pairing, "game": g, "a": a_name, "b": b_name, "team": team, "side": battle.player_role,
            "winner": winner, "turns": battle.turn, "battle": battle.battle_tag}
    if isinstance(a, AgentPlayer):
        s = a.summaries[-1]
        line.update(decisions=s["decisions"], fallbacks=s["fallbacks"],
                    think_p50_ms=s["think_p50_ms"], think_p99_ms=s["think_p99_ms"])
    return line


def wilson(wins: float, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = wins / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (centre - half, centre + half)


def score(row: dict) -> float:
    return {"a": 1.0, "tie": 0.5, "b": 0.0}[row["winner"]]


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


def report(rows: list[dict]) -> dict:
    table = {}
    for pairing, (a, b, planned) in PAIRINGS.items():
        mine = [r for r in rows if r["pairing"] == pairing]
        if not mine:
            continue
        n = len(mine)
        wins = sum(map(score, mine))
        decisions = sum(r.get("decisions", 0) for r in mine)
        p99s = sorted(r["think_p99_ms"] for r in mine if r.get("think_p99_ms") is not None)
        table[pairing] = {
            "a": a, "b": b, "games": n, "planned": planned, "win_rate": wins / n,
            "wilson_95": wilson(wins, n), "team_bootstrap_95": team_bootstrap(mine),
            "teams": len({r["team"] for r in mine}),
            "fallback_rate": sum(r.get("fallbacks", 0) for r in mine) / decisions if decisions else None,
            "worst_game_p99_ms": p99s[-1] if p99s else None,
        }
    return table


def ratings(rows: list[dict], anchor: str = "random", draws: int = 200, seed: int = 0) -> dict[str, dict]:
    """Bradley-Terry ratings on the Elo scale (anchor = 1000) from every game, with 95% bootstrap intervals."""
    point = _fit(rows, anchor)
    rng = random.Random(seed)
    samples = {name: [] for name in point}
    for _ in range(draws):
        fit = _fit([rng.choice(rows) for _ in rows], anchor)
        for name in point:
            if name in fit:
                samples[name].append(fit[name])
    out = {}
    for name, elo in point.items():
        xs = sorted(samples[name])
        out[name] = {"elo": elo, "elo_95": (xs[int(0.025 * len(xs))], xs[int(0.975 * len(xs)) - 1]) if xs else (elo, elo)}
    return out


def _fit(rows: list[dict], anchor: str, iterations: int = 500) -> dict[str, float]:
    # Each player also gets one virtual drawn game with the anchor, so a player who never lost keeps a finite rating.
    games: dict[tuple[str, str], list[float]] = {}  # (i, j) -> [i's score, games]
    for r in rows:
        for i, j, x in ((r["a"], r["b"], score(r)), (r["b"], r["a"], 1 - score(r))):
            g = games.setdefault((i, j), [0.0, 0])
            g[0] += x
            g[1] += 1
    names = {i for i, _ in games} | {anchor}
    for name in names - {anchor}:
        for i, j in ((name, anchor), (anchor, name)):
            g = games.setdefault((i, j), [0.0, 0])
            g[0] += 0.5
            g[1] += 1
    opponents: dict[str, list[tuple[str, int]]] = {i: [] for i in names}
    wins = dict.fromkeys(names, 0.0)
    for (i, j), (won, n) in games.items():
        opponents[i].append((j, n))
        wins[i] += won
    strength = dict.fromkeys(names, 1.0)
    for _ in range(iterations):
        # Hunter's MM update for Bradley-Terry: each strength = its wins / sum of games weighted by the matchup.
        strength = {i: wins[i] / sum(n / (strength[i] + strength[j]) for j, n in opponents[i]) for i in names}
    return {i: 1000 + 400 * math.log10(strength[i] / strength[anchor]) for i in names}


def neighbours(table: dict[str, dict], rows: list[dict], agent: str = "full", reach: int = 3) -> list[dict]:
    """The levels up to `reach` places above and below the agent's rating, with the agent's record against each."""
    ladder = sorted(table, key=lambda name: table[name]["elo"])
    at = ladder.index(agent)
    out = []
    for step in [s for s in range(-reach, reach + 1) if s and 0 <= at + s < len(ladder)]:
        name = ladder[at + step]
        mine = [r for r in rows if {r["a"], r["b"]} == {agent, name}]
        wins = sum(score(r) if r["a"] == agent else 1 - score(r) for r in mine)
        out.append({"step": step, "level": name, "elo": table[name]["elo"], "elo_95": table[name]["elo_95"],
                    "gap": table[name]["elo"] - table[agent]["elo"], "games": len(mine),
                    "agent_win_rate": wins / len(mine) if mine else None, "wilson_95": wilson(wins, len(mine))})
    return out


def load_teams(path: Path) -> list[str]:
    files = sorted(path.iterdir()) if path.is_dir() else [path]
    # Trailing blank lines make poke-env parse an empty seventh Pokémon, which breaks priors and team packing.
    return [f.read_text(encoding="utf-8").strip() for f in files if f.is_file()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--pairings", nargs="+", default=list(PAIRINGS), choices=list(PAIRINGS))
    run.add_argument("--games", type=int, help="override every pairing's planned game count")
    # Until the data layer's pool exists, games draw from the 11 validated stand-in teams.
    run.add_argument("--teams", default="bot/teams/standin", help="a team file or a folder of them")
    run.add_argument("--priors", default="data/set_candidates.json")
    run.add_argument("--priors-from-teams", action="store_true",
                     help="stand-in: priors = every set across the teams, weighted by how often it appears")
    # Measured think time is ~65 ms at p50, so 1 s rarely binds and lets six shards share a laptop.
    run.add_argument("--budget", type=float, default=1.0)
    run.add_argument("--shards", type=int, default=max(1, (os.cpu_count() or 4) - 2))
    run.add_argument("--machine", default=platform.node().lower() or "local")
    run.add_argument("--seed", type=int, default=2026)
    sub.add_parser("report")
    parser.add_argument("--runs", default="runs")
    args = parser.parse_args(argv)
    runs = Path(args.runs)
    runs.mkdir(parents=True, exist_ok=True)

    if args.command == "report":
        everything = read_results(runs)
        rows = scored(everything)
        table = report(rows)
        elo = ratings(rows) if rows else {}
        near = neighbours(elo, rows) if "full" in elo else []
        summary = {"pairings": table, "ratings": elo, "neighbours": near, "void_games": len(everything) - len(rows)}
        (runs / "eval-summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        for pairing, r in table.items():
            lo, hi = r["wilson_95"]
            blo, bhi = r["team_bootstrap_95"]
            fallbacks = "n/a" if r["fallback_rate"] is None else f"{r['fallback_rate']:.1%}"
            print(f"{pairing:21} {r['a']} vs {r['b']}: {r['win_rate']:.1%} over {r['games']}/{r['planned']} games "
                  f"(Wilson {lo:.1%}-{hi:.1%}, team bootstrap {blo:.1%}-{bhi:.1%}, {r['teams']} teams), fallbacks {fallbacks}")
        print(f"void games (a side dropped out at team preview, not scored): {summary['void_games']}")
        for name, r in sorted(elo.items(), key=lambda kv: -kv[1]["elo"]):
            print(f"elo {name:16} {r['elo']:6.0f}  (95% {r['elo_95'][0]:.0f}-{r['elo_95'][1]:.0f})")
        for n in near:
            record = "not played" if n["agent_win_rate"] is None else f"agent wins {n['agent_win_rate']:.0%} of {n['games']}"
            print(f"{n['step']:+d} {n['level']:16} gap {n['gap']:+5.0f}  {record}")
        return 0

    teams = load_teams(Path(args.teams))
    priors = priors_from_teams(teams) if args.priors_from_teams else json.loads(Path(args.priors).read_text(encoding="utf-8"))
    planned = {p: args.games or PAIRINGS[p][2] for p in args.pairings}
    shards = schedule(planned, args.shards, done_games(runs), args.seed)
    with ProcessPoolExecutor(max_workers=max(1, len(shards))) as pool:
        jobs = [pool.submit(play_shard, games, teams, priors, args.budget, str(runs), args.machine, s, args.seed)
                for s, games in enumerate(shards)]
        for job in jobs:
            job.result()
    return 0


if __name__ == "__main__":
    sys.exit(main())
