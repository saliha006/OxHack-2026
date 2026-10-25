"""Evaluation harness: our agent and its ablations against baselines and each other, blind, sharded and resumable.

    uv run python -m bot.eval run --shards 6            # every pairing, skipping games already in runs/eval/
    uv run python -m bot.eval run --pairings headline --games 20
    uv run python -m bot.eval report                    # merge every machine's files into one table
"""
import argparse
import asyncio
import copy
import functools
import hashlib
import json
import logging
import math
import multiprocessing
import os
import platform
import random
import secrets
import re
import subprocess
import sys
import time
from collections import Counter
from importlib.metadata import version
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from poke_env import AccountConfiguration
from poke_env.player import MaxBasePowerPlayer, RandomPlayer, SimpleHeuristicsPlayer

from bot.player import AgentPlayer, _percentiles
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
        kwargs.setdefault("backend", "one_ply")
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
    "full": lambda priors, budget: Agent(priors, budget=budget, backend="one_ply"),
    "prior": lambda priors, budget: AblatedAgent(priors, FrozenBelief, budget=budget),
    "flat": lambda priors, budget: AblatedAgent(priors, FlatBelief, budget=budget),
    "k1": lambda priors, budget: Agent(priors, k=1, budget=budget, backend="one_ply"),
}
MCTS_ARM_OPTIONS = {
    "mcts1": {"mcts_worlds": 1, "search_ms": 150},
    "mcts8": {"mcts_worlds": 8, "search_ms": 150},
    "mcts1long": {"mcts_worlds": 1, "search_ms": 1200},
    "mcts8active": {"mcts_worlds": 8, "search_ms": 150, "sampling": "active"},
    "mcts8frozen": {"mcts_worlds": 8, "search_ms": 150, "frozen_beliefs": True},
    # Same 1.2 s as mcts8, so the 3 s turn budget is untouched: fewer, deeper trees per turn.
    "mcts4x300": {"mcts_worlds": 4, "search_ms": 300},
    # Observed complete sets blended into the usage candidates (data/pipeline/joint_sets.py), Foul Play's prior.
    "mcts8joint": {"mcts_worlds": 8, "search_ms": 150, "priors": "data/set_candidates_joint.json"},
}


@functools.cache
def arm_priors(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


for arm_name, arm_options in MCTS_ARM_OPTIONS.items():
    ARMS[arm_name] = lambda priors, budget, options=arm_options: Agent(
        arm_priors(options["priors"]) if "priors" in options else priors, budget=budget, backend="mcts",
        engine_threads=1, **{k: v for k, v in options.items() if k != "priors"})

MCTS_PAIRINGS = {
    "mcts-current": ("mcts1", "full", 20),
    "mcts-current-pooled": ("mcts8", "full", 200),
    "mcts-worlds-equal-total": ("mcts1long", "mcts8", 200),
    "mcts-worlds-equal-per-world": ("mcts1", "mcts8", 200),
    "mcts-bench": ("mcts8", "mcts8active", 200),
    "mcts-inference": ("mcts8", "mcts8frozen", 200),
    "mcts-foulplay": ("mcts8", "fpmid", 100),
    # `headline` and `full~*` measure the one-ply arm; these measure the bot the demo actually runs.
    "mcts-headline": ("mcts8", "simpleheuristics", 200),
    "mcts-foulplay-high": ("mcts8", "fphigh", 60),
    "mcts-deeper-foulplay-high": ("mcts4x300", "fphigh", 60),
    "mcts-deeper": ("mcts4x300", "mcts8", 80),
    "mcts-foulplay-hard": ("mcts8", "fphard", 60),
    "mcts-deeper-foulplay-hard": ("mcts4x300", "fphard", 60),
    "mcts-joint-foulplay-hard": ("mcts8joint", "fphard", 60),
    "mcts-joint": ("mcts8joint", "mcts8", 80),
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
PAIRINGS |= MCTS_PAIRINGS

FOUL_PLAY = Path(__file__).parent.parent / "foul-play"
# Search-time bands in ms, deliberately uneven; each Foul Play process draws its own time inside its band.
FOUL_PLAY_LEVELS = {"fplow": (40, 80), "fpmid": (150, 260), "fphigh": (450, 700), "fphard": (900, 1100)}
# Foul Play's parallelism is its world count (doubled until it has seen three of the active's moves). fphard is
# close to how it plays the ladder: four worlds at once, each searched ~7x longer than one of our eight.
FOUL_PLAY_PARALLELISM = {"fphard": 4}
for level in FOUL_PLAY_LEVELS:
    PAIRINGS[f"full~{level}"] = ("full", level, 50)
    PAIRINGS[f"prior~{level}"] = ("prior", level, 20)


class FoulPlay:
    """A Foul Play bot in its own process, accepting our challenges and playing its team list in our game order."""

    def __init__(self, search_ms: int, team_paths: list[Path], runs: Path, username: str,
                 *, challenge_user: str | None = None, parallelism: int = 1):
        self.username = username
        self.search_ms = search_ms
        self.challenge_user = challenge_user
        self.source_commit = repository_revision(FOUL_PLAY)
        self.log = runs / f"{username}.log"
        team_list = runs / f"{username}.teams.txt"
        team_list.write_text("".join(f"{p.resolve()}\n" for p in team_paths), encoding="utf-8")
        python = FOUL_PLAY / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        self.output = open(self.log, "w", encoding="utf-8")
        args = [str(python), "run.py", "--websocket-uri", "ws://localhost:8000/showdown/websocket",
             "--ps-username", username, "--bot-mode", "challenge_user" if challenge_user else "accept_challenge",
             "--pokemon-format", "gen9ou",
             "--team-list", str(team_list.resolve()), "--search-time-ms", str(search_ms),
             "--search-threads", "1", "--search-parallelism", str(parallelism),
             "--run-count", str(len(team_paths)), "--log-level", "INFO"]
        if challenge_user:
            args += ["--user-to-challenge", challenge_user]
        self.process = subprocess.Popen(args,
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
        # Reap real subprocesses. Test doubles need only terminate().
        if hasattr(self.process, "wait"):
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        self.output.close()


def repository_revision(folder: Path) -> str | None:
    """Read a local checkout's commit without depending on credentials or invoking Git in each game."""
    git = folder / ".git"
    try:
        head = (git / "HEAD").read_text().strip()
        if head.startswith("ref: "):
            ref = head[5:]
            if (git / ref).exists():
                head = (git / ref).read_text().strip()
            else:
                head = next(line.split()[0] for line in (git / "packed-refs").read_text().splitlines()
                            if line.endswith(" " + ref))
        return head if re.fullmatch(r"[0-9a-f]{40}", head) else None
    except (OSError, StopIteration):
        return None


def foul_play_search_log(path: Path) -> list[dict]:
    """Extract observed world settings/visits, deduplicating child and parent iteration messages.

    Stock Foul Play logs do not contain search wall time, so this never calls the configured budget measured time.
    """
    searches = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return searches
    for line in lines:
        settings = re.search(r"Sampling (\d+) battles at (\d+)ms each", line)
        if settings:
            searches.append({"requested_worlds": int(settings[1]), "search_ms_per_world": int(settings[2]),
                             "visits_by_world": {}})
        iterations = re.search(r"Iterations (\d+): (\d+)", line)
        if iterations and searches:
            searches[-1]["visits_by_world"][iterations[1]] = int(iterations[2])
    for search in searches:
        search["completed_worlds"] = len(search["visits_by_world"])
        search["total_visits"] = sum(search["visits_by_world"].values())
    return searches


async def _finished_game(dispatch, participants: list[tuple[object, set]], *,
                         external=None, timeout: float = 900.0) -> list[tuple[object, dict | None]]:
    """Wait for new battle identities, terminal state and their matching summaries.

    poke-env's challenge coroutine may return early when a reused player changes challenge direction. Its
    semaphore is therefore not evidence that this game's Battle or summary has completed.
    """
    task = asyncio.ensure_future(dispatch)
    deadline = time.monotonic() + timeout
    try:
        while True:
            if task.done():
                task.result()  # surface dispatch errors immediately
            completed = []
            for player, previous_tags in participants:
                new = [(key, battle) for key, battle in list(getattr(player, "battles", {}).items())
                       if key not in previous_tags]
                if len(new) > 1:
                    raise RuntimeError("evaluation overlap: more than one new battle for a scheduled game")
                if not new or not new[0][1].finished:
                    break
                battle = new[0][1]
                summary = None
                if isinstance(player, AgentPlayer):
                    summary = next((row for row in player.summaries if row.get("tag") == battle.battle_tag), None)
                    if summary is None:
                        break
                completed.append((battle, summary))
            if len(completed) == len(participants) and task.done():
                if len({battle.battle_tag for battle, _ in completed}) != 1:
                    raise RuntimeError("evaluation participants completed different battle tags")
                return completed
            if external is not None and external.process.poll() not in (None, 0):
                raise RuntimeError(f"Foul Play exited during game; see {external.log}")
            if time.monotonic() >= deadline:
                raise TimeoutError(f"evaluation game did not complete within {timeout}s")
            if task.done():
                await asyncio.sleep(0.05)
            else:
                await asyncio.wait({task}, timeout=0.05)
    finally:
        if not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)


def _battle_snapshot(player) -> set:
    battles = list(getattr(player, "battles", {}).items())
    if any(not battle.finished for _, battle in battles):
        raise RuntimeError("evaluation overlap: previous battle has not finished")
    return {key for key, _ in battles}


async def _foul_game(player, opponent: FoulPlay, *, accepting: bool, timeout: float = 900.0,
                     previous_tags: set | None = None):
    previous_tags = _battle_snapshot(player) if previous_tags is None else previous_tags
    dispatch = (player.accept_challenges(opponent.username, 1) if accepting
                else player.send_challenges(opponent.username, 1))
    return await _finished_game(dispatch, [(player, previous_tags)], external=opponent, timeout=timeout)


def make_player(name: str, jittered: bool, priors: dict, budget: float, runs: str, team: str, rng: random.Random):
    # A random account name, so nothing in the battle tells either side what it's playing.
    # Account IDs must be fresh across resumed/repeated runs: Showdown reconnects
    # a reused name to unfinished old games, invalidating the scheduled matchup.
    username = "ox" + secrets.token_hex(4)
    config = dict(account_configuration=AccountConfiguration(username, None),
                  battle_format="gen9ou", team=team)
    if name in ARMS:
        cls, extra = AgentPlayer, {"make_agent": lambda: ARMS[name](priors, budget),
                                   "runs_dir": Path(runs) / "players" / username,
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


def team_index(seed: int, pairing: str, game: int, count: int) -> int:
    """MCTS comparisons share the same team per adjacent side-swapped game pair, across arms."""
    if pairing in MCTS_PAIRINGS:
        # Reserve each shuffled block of teams for one side-balanced pair apiece. Sampling with replacement can
        # otherwise leave a small comparison playing the same team throughout, even with an apparently varied pool.
        block, offset = divmod(game // 2, count)
        order = list(range(count))
        game_rng(seed, "mcts-matched-teams", block).shuffle(order)
        return order[offset]
    return game_rng(seed, pairing, game).randrange(count)


def arm_config(name: str, budget: float) -> dict:
    if name in MCTS_ARM_OPTIONS:
        return {"backend": "mcts", "budget_seconds": budget, "engine_threads": 1,
                "sampling": "team", "frozen_beliefs": False, **MCTS_ARM_OPTIONS[name]}
    if name in ARMS:
        return {"backend": "one_ply", "budget_seconds": budget, "arm": name}
    if name in FOUL_PLAY_LEVELS:
        parallelism = FOUL_PLAY_PARALLELISM.get(name, 1)
        return {"backend": "foul_play", "search_ms_band": FOUL_PLAY_LEVELS[name],
                "engine_threads": 1, "search_parallelism": parallelism, "source_commit": repository_revision(FOUL_PLAY),
                "world_policy": f"{2 * parallelism} early/preview, {parallelism} after >=3 opposing moves; stock source decides",
                "compute_matched": False}
    return {"backend": name}


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
            for session in list(getattr(player, "sessions", {}).values()):
                session.close(None, session.parser.state["turn"] if session.parser else 0)


def start_foul_play(games: list[tuple[str, int]], teams: list[str], folder: Path, rng: random.Random,
                    seed: int) -> dict:
    """One Foul Play process per level this shard meets, given its teams in the order this shard will play them."""
    players = {}
    team_files = folder / "teams"
    team_files.mkdir(exist_ok=True)
    for i, team in enumerate(teams):
        (team_files / f"team_{i}.txt").write_text(team, encoding="utf-8")
    for level, (low, high) in FOUL_PLAY_LEVELS.items():
        mine = [(p, g) for p, g in games if PAIRINGS[p][1] == level and p not in MCTS_PAIRINGS]
        if mine:
            paths = [team_files / f"team_{team_index(seed, p, g, len(teams))}.txt" for p, g in mine]
            players["b", level] = FoulPlay(rng.randint(low, high), paths, folder, "ox" + secrets.token_hex(4),
                                           parallelism=FOUL_PLAY_PARALLELISM.get(level, 1))
    return players


def play_game(pairing: str, g: int, players: dict, teams: list[str], priors: dict, budget: float, runs: str,
              rng: random.Random, seed: int) -> dict:
    a_name, b_name, _ = PAIRINGS[pairing]
    for role, name in (("a", a_name), ("b", b_name)):
        if role == "b" and name in FOUL_PLAY_LEVELS and pairing in MCTS_PAIRINGS:
            continue  # side-balanced external comparisons use one process per game
        if (role, name) not in players:
            players[role, name] = make_player(name, role == "b" and pairing not in MCTS_PAIRINGS,
                                             priors, budget, runs, teams[0], rng)
    a = players["a", a_name]
    transient_fp = b_name in FOUL_PLAY_LEVELS and pairing in MCTS_PAIRINGS
    pick = game_rng(seed, pairing, g)
    team = team_index(seed, pairing, g, len(teams))
    a.update_team(teams[team])
    previous_a = _battle_snapshot(a)
    if transient_fp:
        folder = Path(runs) / "eval" / "foul-play"
        folder.mkdir(parents=True, exist_ok=True)
        team_path = folder / f"team_{team}.txt"
        team_path.write_text(teams[team], encoding="utf-8")
        low, high = FOUL_PLAY_LEVELS[b_name]
        # Each adjacent pair uses the same team and per-world search setting on opposite sides.
        search_ms = game_rng(seed, pairing, g // 2).randint(low, high)
        b = FoulPlay(search_ms, [team_path], folder, "ox" + secrets.token_hex(4),
                     challenge_user=a.username if g % 2 else None,
                     parallelism=FOUL_PLAY_PARALLELISM.get(b_name, 1))
    else:
        b = players["b", b_name]
    if isinstance(b, FoulPlay):
        try:
            if transient_fp and g % 2:
                finished = asyncio.run(_foul_game(a, b, accepting=True, previous_tags=previous_a))
            else:
                b.wait_ready()
                if transient_fp:
                    finished = asyncio.run(_foul_game(a, b, accepting=False, previous_tags=previous_a))
                else:
                    finished = asyncio.run(_finished_game(a.send_challenges(b.username, 1), [(a, previous_a)]))
        finally:
            if transient_fp:
                b.close()
    else:
        b.update_team(teams[team])
        previous_b = _battle_snapshot(b)
        # Whoever challenges gets p1; a coin flip keeps sides balanced without a pattern.
        first_a = g % 2 == 0 if pairing in MCTS_PAIRINGS else pick.random() < 0.5
        first, second = (a, b) if first_a else (b, a)
        finished = asyncio.run(_finished_game(first.battle_against(second, n_battles=1),
                                              [(a, previous_a), (b, previous_b)]))
    battle, our_summary = finished[0]
    if battle.turn == 0:
        winner = "void"  # someone crashed or forfeited at team preview: no play to score
    else:
        winner = "tie" if battle.won is None else ("a" if battle.won else "b")
    line = {"pairing": pairing, "game": g, "a": a_name, "b": b_name, "team": team, "side": battle.player_role,
            "winner": winner, "turns": battle.turn, "battle": battle.battle_tag,
            "completion_verified": True,
            "compute": {"a": arm_config(a_name, budget), "b": arm_config(b_name, budget)},
            "balanced_sides": pairing in MCTS_PAIRINGS}
    line["artifacts"] = {}
    for role, player in (("a", a), ("b", b)):
        if isinstance(player, AgentPlayer) and hasattr(player, "runs_dir"):
            folder = player.runs_dir.resolve()
            line["artifacts"][role] = {kind: str(folder / f"{battle.battle_tag}{suffix}") for kind, suffix in
                                       (("raw_log", ".log"), ("trace", ".jsonl"), ("decision_log", ".decision.log"))}
    if isinstance(b, FoulPlay):
        line["compute"]["b"]["configured_search_ms_per_world"] = getattr(b, "search_ms", None)
        if hasattr(b, "log"):
            line["artifacts"]["b"] = {"foul_play_log": str(b.log.resolve())}
            line["foul_play_searches"] = foul_play_search_log(b.log)
    if isinstance(a, AgentPlayer):
        s = our_summary
        line.update({k: v for k, v in s.items() if k not in ("tag", "side", "won", "turns")})
    if isinstance(b, AgentPlayer) and b.summaries:
        line["opponent_metrics"] = finished[1][1]
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
        raw_ms = [ms for r in mine for ms in r.get("decision_ms", [])]
        search_ms = [ms for r in mine for ms in r.get("actual_search_ms", [])]
        reasons: dict[str, int] = {}
        for r in mine:
            for reason, count in r.get("fallback_reasons", {}).items():
                reasons[reason] = reasons.get(reason, 0) + count
        table[pairing] = {
            "a": a, "b": b, "games": n, "planned": planned, "win_rate": wins / n,
            "wilson_95": wilson(wins, n), "team_bootstrap_95": team_bootstrap(mine),
            "teams": len({r["team"] for r in mine}),
            "fallback_rate": sum(r.get("fallbacks", 0) for r in mine) / decisions if decisions else None,
            "worst_game_p99_ms": p99s[-1] if p99s else None,
            **_percentiles(raw_ms),
            "actual_search_ms": sum(search_ms),
            "rejected_choices": sum(r.get("rejected_choices", 0) for r in mine),
            "fallback_reasons": reasons,
            **{key: sum(r.get(key, 0) for r in mine) for key in
               ("requested_worlds", "completed_worlds", "failed_worlds", "usable_worlds")},
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


def evaluation_manifest(teams: list[str], priors: dict, budget: float, seed: int,
                        shards: int, team_role: str) -> dict:
    """Record the actual inputs; a declared held-out pool remains the evaluator's responsibility."""
    digest = lambda data: hashlib.sha256(data.encode("utf-8")).hexdigest()
    revision = subprocess.run(["git", "rev-parse", "HEAD"], text=True, capture_output=True, check=False)
    root = Path(__file__).resolve().parent.parent
    source = [root / "pyproject.toml"] + [p for folder in ("bot", "decision", "contracts")
                                          for p in sorted((root / folder).glob("*.py"))]
    source_hash = hashlib.sha256()
    for path in source:
        source_hash.update(str(path.relative_to(root)).encode("utf-8") + b"\0" + path.read_bytes() + b"\0")
    return {"engine_version": version("poke-engine"), "python_version": platform.python_version(),
            "git_revision": revision.stdout.strip(), "source_sha256": source_hash.hexdigest(),
            "seed": seed, "concurrent_games": shards,
            "budget_seconds": budget, "team_role": team_role,
            "team_hashes": [digest(t) for t in teams],
            "priors_sha256": digest(json.dumps(priors, sort_keys=True)), "priors_source": priors.get("source"),
            "arms": {name: arm_config(name, budget) for name in (*ARMS, *FOUL_PLAY_LEVELS)},
            "final_randomisation": False, "learned_reranker": False,
            "side_balance": "adjacent MCTS games share teams and swap challenge direction, including Foul Play; legacy FP arms accept only"}


def action_agreement(make_agent, request: dict, battle: dict, repeats: int) -> dict:
    """Repeat a position with reset beliefs and RNG; compare actions, never exact native visits."""
    if repeats < 2:
        raise ValueError("action agreement requires at least two repeats")
    choices: Counter[str] = Counter()
    traces = []
    for _ in range(repeats):
        agent = make_agent()
        try:
            choices[str(agent.choose(copy.deepcopy(request), copy.deepcopy(battle)))] += 1
            traces.append(copy.deepcopy(getattr(agent, "last_trace", {})))
        finally:
            close = getattr(agent, "close", None)
            if close:
                close()
    return {"repeats": repeats, "choices": dict(choices),
            "pairwise_action_agreement": sum(n * (n - 1) for n in choices.values()) / (repeats * (repeats - 1)),
            "fallbacks": sum(bool(t.get("fallback_reason")) for t in traces), "traces": traces}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--config", type=Path, help="saved evaluation settings; explicit command-line options override them")
    run.add_argument("--pairings", nargs="+", default=list(PAIRINGS), choices=list(PAIRINGS))
    run.add_argument("--games", type=int, help="override every pairing's planned game count")
    # Until the data layer's pool exists, games draw from the 11 validated stand-in teams.
    run.add_argument("--teams", default="bot/teams/standin", help="a team file or a folder of them")
    run.add_argument("--priors", default="data/set_candidates.json")
    run.add_argument("--priors-from-teams", action="store_true",
                     help="stand-in: priors = every set across the teams, weighted by how often it appears")
    # Measured think time is ~65 ms at p50, so 1 s rarely binds and lets six shards share a laptop.
    run.add_argument("--budget", type=float, default=3.0)
    run.add_argument("--shards", type=int, default=max(1, (os.cpu_count() or 4) - 2))
    run.add_argument("--machine", default=platform.node().lower() or "local")
    run.add_argument("--seed", type=int, default=2026)
    run.add_argument("--team-role", choices=("integration", "held-out"), default="integration",
                     help="record whether the supplied teams were held out from training and tuning")
    sub.add_parser("report")
    agreement = sub.add_parser("agreement", help="repeat a saved {request, battle} JSON position")
    agreement.add_argument("position", type=Path)
    agreement.add_argument("--priors", default="data/set_candidates.json")
    agreement.add_argument("--repeats", type=int, default=10)
    agreement.add_argument("--worlds", type=int, default=1)
    agreement.add_argument("--search-ms", type=int, default=150)
    agreement.add_argument("--engine-threads", type=int, default=1)
    agreement.add_argument("--budget", type=float, default=3.0)
    agreement.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--runs", default="runs")
    args = parser.parse_args(argv)
    if args.command == "run" and args.config:
        saved = json.loads(args.config.read_text(encoding="utf-8"))
        allowed = {"pairings", "games", "teams", "priors", "priors_from_teams", "budget", "shards", "machine", "seed", "team_role"}
        if set(saved) - allowed:
            parser.error(f"unknown evaluation config fields: {sorted(set(saved) - allowed)}")
        explicit = argv if argv is not None else sys.argv[1:]
        for key, value in saved.items():
            option = "--" + key.replace("_", "-")
            if not any(arg == option or arg.startswith(option + "=") for arg in explicit):
                setattr(args, key, value)
        if not isinstance(args.pairings, list) or any(p not in PAIRINGS for p in args.pairings):
            parser.error("config pairings must name known evaluation pairings")
        if args.team_role not in ("integration", "held-out"):
            parser.error("config team_role must be integration or held-out")
    runs = Path(args.runs)
    runs.mkdir(parents=True, exist_ok=True)

    if args.command == "agreement":
        position = json.loads(args.position.read_text(encoding="utf-8"))
        priors = json.loads(Path(args.priors).read_text(encoding="utf-8"))
        measured = action_agreement(lambda: Agent(
            priors, backend="mcts", budget=args.budget, mcts_worlds=args.worlds, search_ms=args.search_ms,
            engine_threads=args.engine_threads, seed=args.seed), position["request"], position["battle"], args.repeats)
        measured["engine_version"] = version("poke-engine")
        (runs / "action-agreement.json").write_text(json.dumps(measured, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({k: v for k, v in measured.items() if k != "traces"}, indent=2))
        return 0

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
    if not teams:
        parser.error("--teams must contain at least one team")
    if args.games is not None and args.games < 1:
        parser.error("--games must be positive")
    if args.shards < 1 or args.budget <= 0:
        parser.error("--shards and --budget must be positive")
    priors = priors_from_teams(teams) if args.priors_from_teams else json.loads(Path(args.priors).read_text(encoding="utf-8"))
    if args.priors_from_teams and args.team_role == "held-out":
        parser.error("priors built from evaluation teams cannot be declared held-out")
    planned = {p: args.games or PAIRINGS[p][2] for p in args.pairings}
    shards = schedule(planned, args.shards, done_games(runs), args.seed)
    manifest = evaluation_manifest(teams, priors, args.budget, args.seed, max(1, len(shards)), args.team_role)
    manifest_path = runs / "eval-manifest.json"
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))
        fields = ("engine_version", "source_sha256", "budget_seconds", "team_role", "team_hashes", "priors_sha256", "seed", "arms")
        if any(previous.get(k) != manifest.get(k) for k in fields):
            parser.error("evaluation inputs changed; use a new --runs directory to avoid mixing configurations")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    # poke-env creates an event-loop thread at import; forking that process can inherit a locked loop.
    with ProcessPoolExecutor(max_workers=max(1, len(shards)), mp_context=multiprocessing.get_context("spawn")) as pool:
        jobs = [pool.submit(play_shard, games, teams, priors, args.budget, str(runs), args.machine, s, args.seed)
                for s, games in enumerate(shards)]
        for job in jobs:
            job.result()
    return 0


if __name__ == "__main__":
    sys.exit(main())
