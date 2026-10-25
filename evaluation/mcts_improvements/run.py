"""Seeded head-to-head evaluations with complete source isolation.

Reserve teams before tuning, freeze a manifest, then run exactly that manifest. The
coordinator alone sees both teams; each subprocess loads its own snapshot's parser,
belief, adapter and agent. No evaluation paste is used to build a prior.
"""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import math
from pathlib import Path
import queue
import random
import statistics
import subprocess
import sys
import threading
import time

from .identity import source_identity, engine_identity, file_hash, json_hash

HERE = Path(__file__).parent.resolve()
def harness_identity():
    return {path.name:file_hash(path) for path in sorted(HERE.iterdir()) if path.suffix in {'.py','.cjs'}}


def simulator_identity(root):
    digest=hashlib.sha256()
    for folder in ('dist/sim','dist/data'):
        for path in sorted((Path(root)/folder).rglob('*.js')):
            digest.update(path.relative_to(root).as_posix().encode()+b'\0'+path.read_bytes()+b'\0')
    return digest.hexdigest()


DEFAULT_CONFIG = dict(backend='mcts', budget=3.0, mcts_worlds=8, search_ms=150,
                      engine_threads=1, sampling='team', frozen_beliefs=False, seed=2026)


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')


class JsonProcess:
    def __init__(self, command, stderr, cwd=None):
        self.error_file = open(stderr, 'w')
        self.process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=self.error_file, text=True, bufsize=1, cwd=cwd)
        self.messages = queue.Queue()
        def read():
            try:
                for line in self.process.stdout:
                    self.messages.put(json.loads(line))
            except Exception as error:
                self.messages.put({'kind':'error', 'error':repr(error)})
            finally:
                self.messages.put({'kind':'eof', 'code':self.process.poll()})
        self.reader = threading.Thread(target=read, daemon=True)
        self.reader.start()

    def send(self, value):
        self.process.stdin.write(json.dumps(value) + '\n')
        self.process.stdin.flush()

    def receive(self, timeout=30):
        try:
            result = self.messages.get(timeout=timeout)
        except queue.Empty:
            raise TimeoutError(f'process did not respond within {timeout} seconds') from None
        if result['kind'] in {'error','eof'}:
            raise RuntimeError(result)
        return result

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
        try:
            self.process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=3)
        self.error_file.close()


def validate_teams(simulator, teams):
    process = subprocess.run(['node', str(HERE/'simulator.cjs'), str(simulator)],
                             input=json.dumps({'op':'validate','teams':teams}) + '\n',
                             text=True, capture_output=True, timeout=60, check=True)
    result = json.loads(process.stdout.splitlines()[0])
    if result['kind'] != 'validated':
        raise ValueError(result)
    errors = {i:r['errors'] for i,r in enumerate(result['results']) if r['errors']}
    if errors:
        raise ValueError(errors)
    return result['results']


def balanced_schedule(team_count, games=60, seed=2026102501):
    if team_count < 2 or games < 2 or games % 2:
        raise ValueError('need at least two teams and an even game count')
    rng = random.Random(seed)
    order = list(range(team_count))
    rng.shuffle(order)
    rows = []
    for block in range(games//2):
        round_number, offset = divmod(block, team_count)
        a = order[offset]
        b = order[(offset + 1 + round_number % (team_count-1)) % team_count]
        sim_seed = [rng.randrange(65536) for _ in range(4)]
        sampler_seed = rng.randrange(2**31)
        mixed_policy_seed = rng.randrange(2**31)
        for swap in (False, True):
            rows.append({'game':len(rows), 'block':block, 'a_team':a, 'b_team':b,
                         'a_side':'p2' if swap else 'p1', 'simulator_seed':sim_seed,
                         'sampler_seed':sampler_seed, 'mixed_policy_seed':mixed_policy_seed})
    return rows


def freeze_arm(root, priors, config):
    root, priors = Path(root).resolve(), Path(priors).resolve()
    identity = source_identity(root)
    return {'root':str(root), 'source_sha256':identity['source_sha256'],
            'source_files':identity['files'], 'engine':engine_identity(),
            'priors':str(priors), 'priors_sha256':file_hash(priors), 'config':config}


def freeze_manifest(a_root, b_root, priors, teams, simulator, *, games=60, seed=2026102501,
                    concurrency=4, a_config=None, b_config=None, max_turns=600, phase='screening', b_priors=None):
    team_manifest_path = Path(teams).resolve()
    team_manifest = json.loads(team_manifest_path.read_text())
    records = team_manifest['teams']
    texts = [Path(t['path']).read_text().strip() for t in records]
    validated = validate_teams(simulator, texts)
    for team, text, checked in zip(records, texts, validated):
        if team['sha256'] != hashlib.sha256(text.encode()).hexdigest():
            raise ValueError('team content changed after reservation')
        team['packed'] = checked['packed']
    if phase == 'screening' and (games < 60 or len(records) < 10):
        raise ValueError('screening requires >=60 games and >=10 reserved teams')
    if phase == 'confirmation' and (games < 200 or len(records) < 10):
        raise ValueError('confirmation requires >=200 games and >=10 fresh reserved teams')
    sim_root = Path(simulator).resolve()
    sim_git = subprocess.run(['git','-C',str(sim_root),'rev-parse','HEAD'],capture_output=True,text=True,check=True).stdout.strip()
    manifest = {'schema':1, 'harness_files':harness_identity(), 'phase':phase, 'seed':seed, 'concurrent_games':concurrency,
                'teams':records, 'team_reservation':str(team_manifest_path),
                'team_provenance':team_manifest['provenance'],
                'simulator':{'root':str(sim_root), 'commit':sim_git, 'effective_js_sha256':simulator_identity(sim_root)},
                'a':freeze_arm(a_root,priors, DEFAULT_CONFIG | (a_config or {})),
                'b':freeze_arm(b_root,b_priors or priors, DEFAULT_CONFIG | (b_config or {})),
                'schedule':balanced_schedule(len(records),games,seed),
                'stopping_rule':{'games':games, 'max_turns':max_turns,
                    'censored_turn_limit':'void, never counted as a played draw or silently dropped',
                    'game_timeout_seconds':3600, 'no_outcome_stopping':True},
                'promotion_rule':'Correctness fixes may be enabled without proven strength. Policy changes remain off unless fresh confirmation supports benefit and reliability; screening alone is inconclusive.',
                'compute':'same requested settings except the allocation stage; one native thread; sequential worlds; actual CPU and search time reported'}
    manifest['manifest_sha256'] = json_hash(manifest)
    return manifest


def trace_metrics(path):
    rows = [json.loads(line) for line in Path(path).read_text().splitlines() if line]
    decisions = [r for r in rows if 'request' in r]
    counter = Counter()
    for row in decisions:
        for key in ('belief_history_reset','worker_restart_required','replay_not_recorded'):
            counter[key] += bool(row.get(key))
        counter['recoveries'] += len(row.get('recovery_events',[]))
    return {'native_visits':sum(sum(w.get('total_visits',0) for w in r.get('worlds',[])) for r in decisions),
            'state_preparation_ms':sum(r.get('state_preparation_ms',0) for r in decisions),
            'worker_wall_ms':sum(r.get('worker_wall_ms',0) for r in decisions), **dict(counter)}


def play_game(manifest, scheduled, output):
    folder = Path(output)/f"game-{scheduled['game']:04d}"
    folder.mkdir(parents=True, exist_ok=False)
    row = dict(scheduled, winner='void', turns=0, artifacts={}, measured={}, identities={},
               manifest_sha256=manifest['manifest_sha256'], completion_verified=False)
    processes = []
    started = time.monotonic()
    try:
        simulator = JsonProcess(['node',str(HERE/'simulator.cjs'),manifest['simulator']['root']],folder/'simulator.stderr')
        processes.append(simulator)
        sides = {}
        for role in ('a','b'):
            arm = manifest[role]
            side = scheduled['a_side'] if role=='a' else ('p2' if scheduled['a_side']=='p1' else 'p1')
            worker = JsonProcess([sys.executable,str(HERE/'worker.py')],folder/f'{role}.stderr',cwd=arm['root'])
            processes.append(worker)
            config = arm['config'] | {'seed':scheduled['sampler_seed']}
            # An optional mixed-policy seed is separate from hidden-world sampling and simulator seeds.
            if 'mix_seed' in config:
                config['mix_seed'] = scheduled['mixed_policy_seed']
            worker.send(dict(arm, config=config, side=side, runs=str(folder/role), tag=f"battle-mcts-{scheduled['game']}"))
            ready = worker.receive()
            if ready['source_sha256'] != arm['source_sha256'] or ready['engine'] != arm['engine']:
                raise RuntimeError('effective child identity mismatch')
            row['identities'][role] = ready
            sides[side]=(role,worker)
            row['artifacts'][role]={'trace':str(folder/role/f"battle-mcts-{scheduled['game']}.jsonl"),
                                     'raw_log':str(folder/role/f"battle-mcts-{scheduled['game']}.log")}
        teams={side:manifest['teams'][scheduled[f'{role}_team']]['packed'] for side,(role,_) in sides.items()}
        simulator.send({'op':'start','seed':scheduled['simulator_seed'],'teams':teams})
        turn_limit=False
        raw = open(folder/'omniscient.log','w')
        try:
            while True:
                message=simulator.receive(timeout=30)
                if time.monotonic()-started > manifest['stopping_rule']['game_timeout_seconds']:
                    raise TimeoutError('frozen game timeout exceeded')
                if message['kind']=='end':
                    winner=message.get('winner')
                    row['winner']=('void' if turn_limit else ('tie' if not winner else sides[winner][0]))
                    row['turns']=message['turns']
                    row['turn_limit_censored']=turn_limit
                    row['completion_verified']=True
                    break
                if message.get('side')=='omniscient':
                    raw.write(message['text']+'\n')
                    raw.flush()
                    turns=[int(l.split('|')[2]) for l in message['text'].splitlines() if l.startswith('|turn|')]
                    if turns and max(turns)>=manifest['stopping_rule']['max_turns'] and not turn_limit:
                        turn_limit=True
                        simulator.send({'op':'tie'})
                    continue
                role,worker=sides[message['side']]
                worker.send({'op':'feed','text':message['text']})
                response=worker.receive(timeout=15)
                for choice in response['choices']:
                    simulator.send({'op':'choose','side':message['side'],'choice':choice})
        finally:
            raw.close()
        for role,worker in sides.values():
            worker.send({'op':'close','won':None if row['winner'] in {'tie','void'} else row['winner']==role,'turns':row['turns']})
            row['measured'][role]=worker.receive()['summary']
            row['measured'][role].update(trace_metrics(row['artifacts'][role]['trace']))
    except Exception as error:
        row['error']=repr(error)
    finally:
        for process in processes:
            process.close()
    row['wall_seconds']=time.monotonic()-started
    write_json(folder/'result.json',row)
    return row


def run_manifest(manifest_path, output):
    manifest=json.loads(Path(manifest_path).read_text())
    expected=manifest.pop('manifest_sha256')
    if json_hash(manifest)!=expected:
        raise ValueError('frozen manifest changed')
    manifest['manifest_sha256']=expected
    if manifest.get('harness_files') != harness_identity():
        raise ValueError('evaluation harness changed after freeze')
    if manifest['simulator']['effective_js_sha256'] != simulator_identity(Path(manifest['simulator']['root'])):
        raise ValueError('simulator changed after freeze')
    output=Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    frozen=output/'manifest.json'
    if frozen.exists() and json.loads(frozen.read_text())!=manifest:
        raise ValueError('output belongs to a different manifest')
    write_json(frozen,manifest)
    done=[]
    for item in manifest['schedule']:
        path=output/f"game-{item['game']:04d}"/'result.json'
        if path.exists():
            saved=json.loads(path.read_text())
            if saved['manifest_sha256']!=expected:
                raise ValueError('existing game identity differs')
            done.append(saved)
    todo=[g for g in manifest['schedule'] if g['game'] not in {r['game'] for r in done}]
    with ThreadPoolExecutor(max_workers=manifest['concurrent_games']) as pool:
        futures={pool.submit(play_game,manifest,g,output):g['game'] for g in todo}
        for future in as_completed(futures):
            result=future.result()
            done.append(result)
            print(json.dumps({'completed':len(done),'planned':len(manifest['schedule']),'game':result['game'],
                              'winner':result['winner'],'turns':result['turns'],'error':result.get('error')}),flush=True)
            write_json(output/'summary.json',summarize(done,manifest))
    return summarize(done,manifest)


def wilson(wins,n):
    if not n: return [0,1]
    z=1.96
    p=wins/n
    centre=(p+z*z/(2*n))/(1+z*z/n)
    width=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/(1+z*z/n)
    return [centre-width,centre+width]


def summarize(rows,manifest):
    scored=[r for r in rows if r['winner']!='void']
    wins=sum(r['winner']=='a' for r in scored)
    ties=sum(r['winner']=='tie' for r in scored)
    by_team=defaultdict(list)
    for row in scored:
        by_team[row['a_team']].append({'a':1,'tie':.5,'b':0}[row['winner']])
    clusters=list(by_team.values())
    rates=[]
    rng=random.Random(manifest['seed'])
    if clusters:
        for _ in range(2000):
            sample=[rng.choice(clusters) for _ in clusters]
            rates.append(sum(map(sum,sample))/sum(map(len,sample)))
        rates.sort()
    result={'planned':len(manifest['schedule']),'recorded':len(rows),'wins':wins,
            'losses':len(scored)-wins-ties,'draws':ties,'voids':len(rows)-len(scored),
            'score_rate':(wins+.5*ties)/len(scored) if scored else None,
            'wilson_95':wilson(wins+.5*ties,len(scored)),
            'candidate_team_cluster_95':[rates[50],rates[1949]] if rates else [0,1],
            'cluster_limit':'Resamples candidate teams; shared opposing teams still create dependence, and ten clusters remain sparse.',
            'wall_seconds_sum':sum(r['wall_seconds'] for r in rows),'arms':{},
            'side_breakdown':{},'team_breakdown':{}}
    for side in ('p1','p2'):
        subset=[r for r in scored if r['a_side']==side]
        result['side_breakdown'][side]=dict(Counter(r['winner'] for r in subset))
    for team in range(len(manifest['teams'])):
        subset=[r for r in scored if r['a_team']==team]
        result['team_breakdown'][str(team)]={'style':manifest['teams'][team].get('style'),**dict(Counter(r['winner'] for r in subset))}
    for role in ('a','b'):
        summaries=[r.get('measured',{}).get(role,{}) for r in rows]
        latency=[x for s in summaries for x in s.get('decision_ms',[])]
        cuts=statistics.quantiles(latency,n=100,method='inclusive') if len(latency)>1 else [latency[0] if latency else None]*99
        totals={key:sum(s.get(key,0) for s in summaries) for key in ('decisions','fallbacks','rejected_choices','requested_worlds','completed_worlds','failed_worlds','usable_worlds','cpu_seconds','native_visits','state_preparation_ms','worker_wall_ms','recoveries','belief_history_reset','worker_restart_required','replay_not_recorded')}
        totals.update(actual_search_ms=sum(sum(s.get('actual_search_ms',[])) for s in summaries),
                      p50_ms=cuts[49],p95_ms=cuts[94],p99_ms=cuts[98],max_ms=max(latency) if latency else None,
                      over_3000_ms=sum(x>3000 for x in latency))
        reasons=Counter()
        for summary in summaries: reasons.update(summary.get('fallback_reasons',{}))
        totals['fallback_reasons']=dict(reasons)
        totals['measured_battle_perspectives']=sum(bool(s) for s in summaries)
        totals['unavailable_battle_perspectives']=sum(not s for s in summaries)
        result['arms'][role]=totals
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    freeze=sub.add_parser('freeze')
    for name in ('a-root','b-root','priors','teams','simulator','output'):
        freeze.add_argument('--'+name,required=True,type=Path)
    freeze.add_argument('--a-config',default='{}')
    freeze.add_argument('--b-config',default='{}')
    freeze.add_argument('--b-priors',type=Path,help='optional independent frozen prior for arm B')
    freeze.add_argument('--games',type=int,default=60)
    freeze.add_argument('--seed',type=int,default=2026102501)
    freeze.add_argument('--concurrency',type=int,default=4)
    freeze.add_argument('--max-turns',type=int,default=600)
    freeze.add_argument('--phase',choices=('smoke','development','screening','confirmation'),default='screening')
    run=sub.add_parser('run')
    run.add_argument('manifest',type=Path)
    run.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    if args.command=='freeze':
        manifest=freeze_manifest(args.a_root,args.b_root,args.priors,args.teams,args.simulator,
            games=args.games,seed=args.seed,concurrency=args.concurrency,a_config=json.loads(args.a_config),
            b_config=json.loads(args.b_config),max_turns=args.max_turns,phase=args.phase,b_priors=args.b_priors)
        write_json(args.output,manifest)
        print(manifest['manifest_sha256'])
    else:
        print(json.dumps(run_manifest(args.manifest,args.output),indent=2))


if __name__=='__main__': main()
