"""Frozen fixed-own-team benchmark against a pinned external Foul Play process.

Each game runs in a disposable process. Existing evaluations are observed, never
stopped or modified. All scheduled outcomes and errors are retained.
"""
import argparse
import asyncio
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import random
import secrets
import signal
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tree_hash(root):
    files = {}
    for p in sorted(Path(root).rglob('*')):
        if p.is_symlink() or not p.is_file() or any(x in p.parts for x in ('.venv', '__pycache__', 'logs', 'node_modules')):
            continue
        if p.suffix in ('.py', '.json', '.js', '.so'):
            files[str(p.relative_to(root))] = sha(p)
    return hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()


def schedule(count, opponents, seed):
    if count % 2 or count < 2 or not opponents:
        raise ValueError('Need an even game count and at least one opponent team')
    rng = random.Random(seed)
    assignments = []
    while len(assignments) < count // 2:
        cycle = list(range(len(opponents)))
        rng.shuffle(cycle)
        assignments.extend(cycle)
    games = []
    for pair, team in enumerate(assignments[:count // 2]):
        for side in ('p1', 'p2'):
            games.append({'game': len(games), 'pair': pair, 'opponent_team': team,
                          'side': side, 'sampler_seed': rng.randrange(1, 2**31),
                          'foul_play_seed': rng.randrange(1, 2**31)})
    rng.shuffle(games)
    return games


def other_evaluations():
    blockers = []
    for p in Path('/proc').iterdir():
        if not p.name.isdigit() or int(p.name) == os.getpid():
            continue
        try:
            argv = (p / 'cmdline').read_bytes().decode().split('\0')
            if (('evaluation.mcts_improvements.run' in argv and 'run' in argv) or
                    'evaluation.mcts_queue_supervisor' in argv or
                    ('bot.eval' in argv and 'run' in argv)):
                blockers.append({'pid': int(p.name), 'command': argv})
        except (OSError, UnicodeError):
            pass
    return blockers


def freeze(folder, count=400, seed=2026102527):
    from evaluation.mcts_improvements.identity import source_identity, engine_identity
    folder = Path(folder).resolve()
    target = folder / 'manifest.json'
    if target.exists():
        raise FileExistsError('Never overwrite a frozen benchmark manifest')
    teams = folder / 'teams'
    teams.mkdir()
    own = ROOT / 'bot/teams/standin/team_6.txt'
    (teams / 'own.txt').write_bytes(own.read_bytes())
    candidates = sorted((ROOT / 'bot/teams').rglob('*.txt'))
    opponents = []
    seen = {sha(own)}
    for source in candidates:
        if sha(source) in seen:
            continue
        seen.add(sha(source))
        dest = teams / f'opponent-{len(opponents):02d}.txt'
        dest.write_bytes(source.read_bytes())
        opponents.append({'path': str(dest), 'sha256': sha(dest), 'source': str(source.relative_to(ROOT))})
    validation_input = json.dumps({'op': 'validate', 'teams': [str((teams/'own.txt').read_text())] +
                                   [Path(t['path']).read_text() for t in opponents]}) + '\n'
    result = subprocess.run(['node', str(ROOT/'evaluation/mcts_improvements/simulator.cjs'),
                             str(folder/'showdown')], input=validation_input, text=True,
                            capture_output=True, check=True, timeout=30)
    checks = json.loads(result.stdout)['results']
    if any(x['errors'] for x in checks):
        raise ValueError(checks)
    config = {'backend': 'mcts', 'budget': 3.0, 'mcts_worlds': 8, 'search_ms': 150,
              'engine_threads': 1, 'sampling': 'team', 'belief_mode': 'reliable',
              'lead_policy': 'types', 'mix_root': False}
    priors = folder / 'priors.json'
    priors.write_bytes((ROOT/'data/set_candidates.json').read_bytes())
    manifest = {'schema': 1, 'root': str(ROOT), 'folder': str(folder),
                'candidate_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                'source': source_identity(ROOT), 'engine': engine_identity(),
                'runner_sha256': sha(__file__), 'seed': seed,
                'own_team': {'path': str(teams/'own.txt'), 'sha256': sha(teams/'own.txt'), 'source': 'bot/teams/standin/team_6.txt'},
                'opponents': opponents, 'priors': str(priors), 'priors_sha256': sha(priors),
                'config': config, 'foul_play_search_ms_per_world': 600,
                'foul_play_world_policy': 'Stock adaptive policy: 2 early/preview, 1 after >=3 known moves; 1 under time pressure',
                'foul_play_threads': 1, 'foul_play_parallelism': 1, 'compute_matched': False,
                'external_revisions': read(folder/'external-revisions.json'),
                'foul_play_runtime': read(folder/'foul-play-runtime.json'),
                'foul_play_tree_sha256': tree_hash(folder/'foul-play'),
                'showdown_tree_sha256': tree_hash(folder/'showdown'),
                'port': 8127, 'concurrency': 2, 'game_timeout_seconds': 1800,
                'smoke': [{'game': -2, 'pair': -1, 'opponent_team': 0, 'side': 'p1', 'sampler_seed': seed+1, 'foul_play_seed': seed+2},
                          {'game': -1, 'pair': -1, 'opponent_team': 0, 'side': 'p2', 'sampler_seed': seed+3, 'foul_play_seed': seed+4}],
                'games': schedule(count, opponents, seed),
                'stopping_rule': 'All 400 scheduled games, no outcome-based early stopping. Stop on infrastructure errors; preserve them and require review before resuming.',
                'inference_scope': 'Fixed own team, familiar synthetic/component opponent pool; not ladder Elo or unseen-team generalization.',
                'randomness': 'Scheduling and Python sampler seeds frozen; native wall-budget search and live Showdown battle seeds are not deterministic.',
                'uncertainty': 'Wilson interval for wins; approximate score interval with half ties; score bootstrap over opponent-team clusters. Repeated teams limit independence.'}
    write(target, manifest)
    print(json.dumps({'manifest': str(target), 'games': count, 'opponent_teams': len(opponents)}))


def verify(manifest):
    from evaluation.mcts_improvements.identity import source_identity, engine_identity
    assert source_identity(ROOT) == manifest['source'], 'Candidate runtime changed'
    assert engine_identity() == manifest['engine'], 'Native engine changed'
    assert sha(__file__) == manifest['runner_sha256'], 'Runner changed after freeze'
    assert sha(manifest['priors']) == manifest['priors_sha256']
    for team in [manifest['own_team'], *manifest['opponents']]:
        assert sha(team['path']) == team['sha256'], 'Team changed after freeze'


def game(manifest, spec):
    from poke_env import AccountConfiguration, ServerConfiguration
    from bot.player import AgentPlayer
    from bot.eval import FoulPlay, _foul_game, foul_play_search_log
    from decision.agent import Agent
    verify(manifest)
    folder = Path(manifest['folder']) / 'games' / str(spec['game'])
    folder.mkdir(parents=True, exist_ok=False)
    fp_root = Path(manifest['folder']) / 'foul-play'
    port = manifest['port']
    uri = f'ws://127.0.0.1:{port}/showdown/websocket'
    username = 'ox' + secrets.token_hex(5)
    config = {**manifest['config'], 'seed': spec['sampler_seed']}
    agents = []
    def make_agent():
        agent = Agent(read(manifest['priors']), **config)
        agents.append(agent)
        return agent
    player = AgentPlayer(make_agent=make_agent, runs_dir=folder,
                         account_configuration=AccountConfiguration(username, None),
                         server_configuration=ServerConfiguration(uri, f'http://127.0.0.1:{port}/action.php?'),
                         battle_format='gen9ou', team=Path(manifest['own_team']['path']).read_text().strip(),
                         start_timer_on_battle_start=True)
    # Reuse completion/readiness handling without altering the general harness or its port.
    opponent = FoulPlay.__new__(FoulPlay)
    opponent.username = 'fp' + secrets.token_hex(5)
    opponent.search_ms = manifest['foul_play_search_ms_per_world']
    opponent.games = 0
    opponent.log = folder / 'foul-play.log'
    opponent.output = opponent.log.open('w')
    team_list = folder/'foul-play.teams.txt'
    team_list.write_text(manifest['opponents'][spec['opponent_team']]['path']+'\n')
    wrapper = "import random,runpy,sys;random.seed(int(sys.argv.pop(1)));sys.argv[0]='run.py';runpy.run_path('run.py',run_name='__main__')"
    args = [str(fp_root/'.venv/bin/python'), '-c', wrapper, str(spec['foul_play_seed']),
            '--websocket-uri', uri, '--ps-username', opponent.username,
            '--bot-mode', 'challenge_user' if spec['side']=='p2' else 'accept_challenge',
            '--pokemon-format', 'gen9ou', '--team-list', str(team_list),
            '--search-time-ms', str(opponent.search_ms), '--search-threads', '1',
            '--search-parallelism', '1', '--run-count', '1', '--log-level', 'INFO']
    if spec['side']=='p2':
        args += ['--user-to-challenge', username]
    opponent.process = subprocess.Popen(args, cwd=fp_root, stdout=opponent.output, stderr=subprocess.STDOUT)
    started = time.monotonic()
    try:
        if spec['side']=='p1':
            opponent.wait_ready()
        battle, metrics = asyncio.run(_foul_game(player, opponent, accepting=spec['side']=='p2',
                                                timeout=manifest['game_timeout_seconds']))[0]
        assert battle.turn > 0, 'No played turns'
        assert battle.player_role == spec['side'], 'Side assignment mismatch'
        return {**spec, 'winner': 'tie' if battle.won is None else 'a' if battle.won else 'b',
                'battle': battle.battle_tag, 'turns': battle.turn,
                'wall_seconds': time.monotonic()-started, 'metrics': metrics,
                'foul_play_searches': foul_play_search_log(opponent.log),
                'artifacts': str(folder), 'completion_verified': True}
    finally:
        opponent.close()
        for agent in agents:
            agent.close()
        try:
            asyncio.run(player.ps_client.stop_listening())
        except Exception:
            pass


def summarize(rows, planned):
    from bot.eval import wilson
    valid = [r for r in rows if r.get('completion_verified')]
    counts = Counter(r['winner'] for r in valid)
    n = len(valid)
    wins = counts['a']; ties = counts['tie']
    by_team = defaultdict(list)
    for row in valid:
        by_team[row['opponent_team']].append(1.0 if row['winner']=='a' else .5 if row['winner']=='tie' else 0.)
    bootstrap = []
    rng = random.Random(2026102527)
    keys = sorted(by_team)
    if keys:
        for _ in range(5000):
            sample = [score for _ in keys for score in by_team[rng.choice(keys)]]
            bootstrap.append(sum(sample)/len(sample))
        bootstrap.sort()
    return {'planned': planned, 'completed': n, 'errors': len(rows)-n,
            'wins': wins, 'losses': counts['b'], 'ties': ties,
            'win_rate': wins/n if n else None,
            'score_rate': (wins+.5*ties)/n if n else None,
            'win_wilson_95': wilson(wins,n) if n else None,
            'score_wilson_95_approx': wilson(wins+.5*ties,n) if n else None,
            'opponent_team_bootstrap_score_95': [bootstrap[125],bootstrap[4874]] if bootstrap else None,
            'by_team': {str(k): {'games': len(v), 'score_rate': sum(v)/len(v)} for k,v in by_team.items()},
            'sides': dict(Counter(r['side'] for r in valid)),
            'fallbacks': sum((r.get('metrics') or {}).get('fallbacks',0) for r in valid),
            'rejected_choices': sum((r.get('metrics') or {}).get('rejected_choices',0) for r in valid),
            'status': 'complete' if n == planned and len(rows)==n else 'incomplete',
            'interpretation': 'This fixed-team matchup and compute configuration only; no ladder or equal-compute claim.'}


def launch_one(manifest_path, spec):
    manifest = read(manifest_path)
    folder = Path(manifest['folder'])
    spec_path = folder / f'job-{spec["game"]}.json'
    write(spec_path, spec)
    result_path = folder / f'result-{spec["game"]}.json'
    log_path = folder / f'job-{spec["game"]}.log'
    with log_path.open('w') as log:
        child = subprocess.Popen([sys.executable, '-m', 'evaluation.foulplay_benchmark',
                                  'game', str(manifest_path), '--spec', str(spec_path), '--output', str(result_path)],
                                 cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = child.wait(timeout=manifest['game_timeout_seconds']+210)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
            code = -1
        finally:
            # Reap only this game's process group, including any external workers.
            try:
                os.killpg(child.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
    if code or not result_path.exists():
        return {**spec, 'completion_verified': False,
                'error': f'Game failed, code={code}; inspect {log_path}',
                'artifacts': str(folder/'games'/str(spec['game']))}
    return read(result_path)


def run(manifest_path):
    manifest_path = Path(manifest_path).resolve()
    manifest = read(manifest_path)
    folder = Path(manifest['folder'])
    status = folder/'status.json'
    verify(manifest)
    while manifest.get('wait_for_existing_evaluations', True) and (blockers := other_evaluations()):
        write(status, {'state': 'waiting_for_existing_evaluations', 'blockers': blockers, 'planned':len(manifest['games'])})
        time.sleep(30)
    verify(manifest)
    if tree_hash(folder/'foul-play') != manifest['foul_play_tree_sha256']:
        raise RuntimeError('Foul Play snapshot changed')
    if tree_hash(folder/'showdown') != manifest['showdown_tree_sha256']:
        raise RuntimeError('Showdown snapshot changed')
    with socket.socket() as sock:
        if sock.connect_ex(('127.0.0.1',manifest['port'])) == 0:
            raise RuntimeError('Private server port is occupied; refusing to reuse it')
    server_log=(folder/'showdown.log').open('w')
    (folder/'showdown/logs/repl').mkdir(parents=True, exist_ok=True)
    server=subprocess.Popen(['node','pokemon-showdown','start','--skip-build',str(manifest['port'])],
                            cwd=folder/'showdown',stdout=server_log,stderr=subprocess.STDOUT,start_new_session=True)
    rows=[]
    try:
        for _ in range(120):
            if server.poll() is not None:
                raise RuntimeError('Private Showdown failed; inspect showdown.log')
            with socket.socket() as sock:
                if sock.connect_ex(('127.0.0.1',manifest['port']))==0:
                    break
            time.sleep(.5)
        else:
            raise TimeoutError('Private Showdown startup timed out')
        write(status,{'state':'smoke','planned':len(manifest['games'])})
        smoke=[]
        for spec in manifest['smoke']:
            smoke.append(launch_one(manifest_path,spec))
            write(folder/'smoke.json',smoke)
        if any(not r.get('completion_verified') or
               (r.get('metrics') or {}).get('fallbacks',0) or
               (r.get('metrics') or {}).get('rejected_choices',0) for r in smoke):
            raise RuntimeError('Smoke reliability gate failed; no main games launched')
        result_file=folder/'games.jsonl'
        if result_file.exists():
            rows=[json.loads(line) for line in result_file.read_text().splitlines()]
        done={r['game'] for r in rows}
        pending=[s for s in manifest['games'] if s['game'] not in done]
        with ThreadPoolExecutor(max_workers=manifest['concurrency']) as pool:
            # Submit only one wave: a failing game must not queue the whole benchmark.
            for offset in range(0,len(pending),manifest['concurrency']):
                jobs=[pool.submit(launch_one,manifest_path,spec) for spec in pending[offset:offset+manifest['concurrency']]]
                for future in as_completed(jobs):
                    row=future.result()
                    rows.append(row)
                    with result_file.open('a') as handle:
                        handle.write(json.dumps(row)+'\n')
                    summary=summarize(rows,len(manifest['games']))
                    write(folder/'summary.json',summary)
                    write(status,{'state':'running',**summary})
                    if not row.get('completion_verified'):
                        raise RuntimeError(row['error'])
        write(status,{'state':'complete',**summarize(rows,len(manifest['games']))})
    except BaseException as error:
        write(status,{'state':'failed','error':str(error),'completed':len(rows),'planned':len(manifest['games'])})
        raise
    finally:
        if server.poll() is None:
            os.killpg(server.pid,signal.SIGTERM)
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(server.pid,signal.SIGKILL)
                server.wait()
        server_log.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('freeze','run','game','report'))
    parser.add_argument('path',type=Path)
    parser.add_argument('--spec',type=Path)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.command=='freeze':
        freeze(args.path)
    elif args.command=='run':
        import fcntl
        folder = Path(read(args.path)['folder'])
        with (folder/'runner.lock').open('w') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            try:
                run(args.path)
            except BaseException as error:
                previous = read(folder/'status.json') if (folder/'status.json').exists() else {}
                write(folder/'status.json',{**previous,'state':'failed','error':str(error)})
                raise
    elif args.command=='game':
        write(args.output,game(read(args.path),read(args.spec)))
    else:
        manifest=read(args.path)
        rows=[json.loads(line) for line in (Path(manifest['folder'])/'games.jsonl').read_text().splitlines()]
        print(json.dumps(summarize(rows,len(manifest['games'])),indent=2))


if __name__=='__main__':
    main()
