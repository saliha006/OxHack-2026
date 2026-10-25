"""Nine bounded fresh-belief calls at one saved public/own-request position.

This does NOT replay historical belief state, supply hidden opponent truth, or
simulate a counterfactual battle outcome. Seeds control set sampling, not native
MCTS determinism. Never tune a candidate from these outcomes.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import time

from decision.agent import Agent
from decision.sets import PokemonSet, stats
from evaluation.mcts_improvements.identity import engine_identity, source_identity

SEEDS=(2026102526,2026102527,2026102528)
CONFIG={'backend':'mcts','budget':3.,'mcts_worlds':8,'search_ms':150,'engine_threads':1,
        'sampling':'team','belief_mode':'reliable','lead_policy':'types'}


def digest(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def scarf_summary(trace, battle):
    us=battle['us'];them='p2' if us=='p1' else 'p1'
    slot=battle['sides'][them]['active']
    beliefs=trace.get('belief_candidates',[])
    candidates=beliefs[slot]['sets'] if slot is not None and slot<len(beliefs) else []
    mass=sum(c['weight'] for c in candidates if c['item']=='choicescarf')
    worlds=trace.get('sampled_worlds',[])
    return {'active_opponent_species':battle['sides'][them]['pokemon'][slot]['species'],
            'scarf_posterior_mass':mass,'scarf_worlds':sum(w[slot]['item']=='choicescarf' for w in worlds),
            'sampled_worlds':len(worlds)}


def fast_branch_summary(trace, battle, request):
    """This saved position has no speed stages/weather/status modifiers."""
    us=battle['us'];them='p2' if us=='p1' else 'p1';slot=battle['sides'][them]['active']
    own=next(mon for mon in request['side']['pokemon'] if mon.get('active'))
    own_speed=own['stats']['spe']*(1.5 if own.get('item')=='choicescarf' else 1)
    per_world=[]
    for i,world in enumerate(trace.get('sampled_worlds',[])):
        mon=world[slot]
        candidate=PokemonSet(tuple(mon['moves']),mon['item'],mon['ability'],mon['tera_type'],
                             mon['nature'],tuple(mon['evs']),tuple(mon.get('ivs',[31]*6)))
        speed=stats(mon['species'],100,candidate)[5]*(1.5 if mon['item']=='choicescarf' else 1)
        native=next((w for w in trace['worlds'] if w['index']==i),{})
        visits=native.get('our_visits',[])
        top=max(visits,key=lambda v:v['visits']) if visits else {}
        per_world.append({'index':i,'item':mon['item'],'hypothesized_speed':speed,
                          'faster_than_us':speed>own_speed,'native_visit_winner':top.get('choice')})
    return {'our_speed':own_speed,'sampled_fast_worlds':sum(w['faster_than_us'] for w in per_world),
            'per_world':per_world,
            'speed_model_scope':'base stats plus Choice Scarf; saved position has no speed stages/weather/status modifiers'}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--position',default='evaluation/coherent-sets/v2-diagnosis-cinderace-position.json',type=Path)
    parser.add_argument('--output',default='evaluation/coherent-sets/v2/position-diagnostic.json',type=Path)
    parser.add_argument('--traces',default='runs/coherent-evaluation/v2-position-diagnostic',type=Path)
    args=parser.parse_args(argv)
    if args.output.exists() or args.traces.exists():raise FileExistsError('fresh outputs required; exactly nine calls per plan')
    position=json.loads(args.position.read_text())
    arms={'broad':Path('data/set_candidates.json'),'v1':Path('data/curated-v1/priors.json'),
          'revised':Path('data/curated-v2/priors.json')}
    inputs={name:{'path':str(path),'sha256':digest(path)} for name,path in arms.items()}
    priors={name:json.loads(path.read_text()) for name,path in arms.items()}
    root=Path.cwd();identity=source_identity(root)
    args.traces.mkdir(parents=True)
    rows=[]
    for seed in SEEDS:
        for name in arms:
            agent=Agent(copy.deepcopy(priors[name]),seed=seed,**CONFIG)
            started=time.monotonic()
            try:
                choice=agent.choose(copy.deepcopy(position['request']),copy.deepcopy(position['battle']))
                trace=copy.deepcopy(agent.last_trace)
            finally:agent.close()
            trace_path=args.traces/f'{name}-{seed}.json'
            trace_path.write_text(json.dumps(trace,indent=1)+'\n')
            row={'arm':name,'seed':seed,'choice':choice,'support':trace.get('search_support',{}),
                 **scarf_summary(trace,position['battle']),
                 'fast_branch':fast_branch_summary(trace,position['battle'],position['request']),
                 'decision_ms':trace.get('total_ms'),'call_and_close_ms':(time.monotonic()-started)*1000,
                 'fallback':trace.get('fallback_reason'),'failures':trace.get('failures',[]),
                 'requested_worlds':trace.get('requested_worlds'),'completed_worlds':trace.get('completed_worlds'),
                 'usable_worlds':trace.get('usable_worlds'),'trace':str(trace_path),'trace_sha256':digest(trace_path)}
            rows.append(row)
            print(json.dumps(row),flush=True)
    assert len(rows)==9
    assert source_identity(root)==identity
    assert all(digest(path)==inputs[name]['sha256'] for name,path in arms.items())
    report={'scope':'fresh-midbattle-beliefs PUBLIC-position diagnostic; not historical persistent replay, oracle, counterfactual outcome, or strength evaluation',
        'exact_call_count':9,'configuration':CONFIG,'seeds':SEEDS,'order':'seed-major; broad, v1, revised sequentially; no concurrent native calls',
        'native_randomness':'Sampler seeds are repeatable; native MCTS results are stochastic.',
        'position':str(args.position),'position_sha256':digest(args.position),'source':identity,'engine':engine_identity(),
        'prior_inputs':inputs,'calls':rows,
        'interpretation':'Changing posterior or choice does not establish a better action; these outcomes must not be used to retune the frozen candidate.'}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
