"""Post-hoc audit of fixed v1 priors against known simulator evaluation teams.

Private team files are used ONLY for retrospective auditing. They must not be
inputs to prior fitting, live decisions, or a claim of fresh confirmation.
"""
import argparse
import hashlib
import json
import math
import re
import random
from collections import Counter, defaultdict
from pathlib import Path

from decision.belief import _to_set, _prior_entry
from decision.sets import PokemonSet, STAT_ORDER, stats
from decision.state import to_id


def parse_team(text):
    result=[]
    aliases={'HP':'hp','Atk':'atk','Def':'def','SpA':'spa','SpD':'spd','Spe':'spe'}
    for block in re.split(r'\n\s*\n',text.strip()):
        lines=[line.strip() for line in block.splitlines() if line.strip()]
        head,*rest=lines
        name,_,item=head.partition(' @ ')
        name=re.sub(r' \([MF]\)$','',name)
        if '(' in name and name.endswith(')'):name=name.rsplit('(',1)[1][:-1]
        mon={'species':to_id(name),'moves':[],'item':to_id(item) or 'none','ability':'',
             'tera_type':'','nature':'serious','evs':[0]*6,'ivs':[31]*6}
        for line in rest:
            if line.startswith('- '):mon['moves'].append(to_id(line[2:]))
            elif line.startswith('Ability:'):mon['ability']=to_id(line.split(':',1)[1])
            elif line.startswith('Tera Type:'):mon['tera_type']=to_id(line.split(':',1)[1])
            elif line.endswith(' Nature'):mon['nature']=to_id(line[:-7])
            elif line.startswith(('EVs:','IVs:')):
                kind='evs' if line.startswith('EVs:') else 'ivs'
                for pair in line.split(':',1)[1].strip().split(' / '):
                    amount,label=pair.split()
                    mon[kind][STAT_ORDER.index(aliases[label])]=int(amount)
        result.append(mon)
    return result


def to_set(mon):
    return PokemonSet(tuple(mon['moves']),mon['item'] or 'none',mon['ability'],mon['tera_type'],
                      mon['nature'],tuple(mon['evs']),tuple(mon.get('ivs',[31]*6)))


def candidate_record_set(candidate):
    if 'spread' in candidate:return _to_set(candidate)
    return to_set(candidate)


def audit_distribution(candidates, truth):
    pairs=[(candidate_record_set(c),float(c.get('weight',1))) for c in candidates]
    mass=sum(w for _,w in pairs)
    if not mass:return None
    pairs=[(c,w/mass) for c,w in pairs]
    actual=to_set(truth); actual_stats=stats(truth['species'],100,actual)
    def total(predicate):return sum(w for c,w in pairs if predicate(c))
    actual_moves=set(actual.moves)
    result={
        'move_recall_mass':sum(w*len(set(c.moves)&actual_moves)/len(actual_moves) for c,w in pairs),
        'exact_moves_mass':total(lambda c:set(c.moves)==actual_moves),
        'item_mass':total(lambda c:c.item==actual.item),
        'ability_mass':total(lambda c:c.ability==actual.ability),
        'tera_mass':total(lambda c:c.tera_type==actual.tera_type),
        'nature_mass':total(lambda c:c.nature==actual.nature),
        'moves_item_mass':total(lambda c:set(c.moves)==actual_moves and c.item==actual.item),
        'full_set_mass':total(lambda c:c==actual),
        'speed_underestimate_mass':total(lambda c:stats(truth['species'],100,c)[5]<actual_stats[5]),
        'expected_speed':sum(w*stats(truth['species'],100,c)[5] for c,w in pairs),
        'true_speed':actual_stats[5],
        'expected_hp_relative_absolute_error':sum(w*abs(stats(truth['species'],100,c)[0]-actual_stats[0])/actual_stats[0] for c,w in pairs),
        'move_mass':{m:total(lambda c:m in c.moves) for m in actual.moves},
    }
    return result


def priors_truth_audit(priors, truths):
    rows=[]
    for truth in truths:
        entry,source=_prior_entry(priors,truth['species'])
        measured=audit_distribution(entry.get('sets',[]),truth)
        rows.append({'species':truth['species'],'truth':truth,'prior_source':source,'metrics':measured})
    return rows


def prior_summary(rows):
    metrics=[r['metrics'] for r in rows if r['metrics']]
    names=('move_recall_mass','exact_moves_mass','item_mass','moves_item_mass','ability_mass',
           'nature_mass','tera_mass','full_set_mass','speed_underestimate_mass','expected_hp_relative_absolute_error')
    return {'unique_component_sets':len(rows),'supported_component_sets':len(metrics),
            **{name:sum(r[name] for r in metrics)/len(metrics) for name in names}} if metrics else None


def block_summary(games):
    groups=defaultdict(list)
    for game in games:groups[game['block']].append(game)
    counts=Counter(sum(row['winner']=='a' for row in rows) for rows in groups.values())
    rng=random.Random(2026102521);blocks=list(groups.values());rates=[]
    for _ in range(5000):
        sample=[rng.choice(blocks) for _ in blocks]
        rates.append(sum(sum(row['winner']=='a' for row in rows) for rows in sample)/sum(map(len,sample)))
    rates.sort()
    return {'blocks':len(blocks),'mixture_wins_per_four_game_block':dict(counts),
            'block_bootstrap_95':[rates[125],rates[4874]],'bootstrap_seed':2026102521,
            'limit':'Resamples side/team-swapped seed blocks; shared teams remain dependent. Not a population-strength estimate.'}


def marginal_drift(base,mixed):
    records=[]
    for species,new in mixed['species'].items():
        if species not in base['species']:continue
        old=base['species'][species]
        fields={}
        for field in ('item','ability','tera_type','nature'):
            def distribution(entry):
                d=defaultdict(float)
                for c in entry['sets']:
                    value=c['spread']['nature'] if field=='nature' else c[field]
                    d[value]+=c['weight']
                return dict(d)
            a,b=distribution(old),distribution(new)
            tv=sum(abs(a.get(k,0)-b.get(k,0)) for k in set(a)|set(b))/2
            fields[field]={'total_variation':tv,'baseline':a,'mixture':b}
        records.append({'species':species,'fields':fields,'max_tv':max(v['total_variation'] for v in fields.values())})
    return sorted(records,key=lambda row:-row['max_tv'])


def load_decisions(path):
    rows=[]
    with Path(path).open() as stream:
        for line in stream:
            row=json.loads(line)
            if 'request' in row and row.get('belief_candidates'):rows.append(row)
    return rows


def selected_name(row):
    words=row['choice'].split()
    if words[0]=='switch':return 'switch '+row['request']['side']['pokemon'][int(words[1])-1]['details'].split(',')[0]
    if words[0]=='move':return row['request']['active'][0]['moves'][int(words[1])-1]['id']+(' tera' if 'terastallize' in words else '')
    return row['choice']


def opening_audit(games):
    """Matched opening diagnostics, never a causal replay/counterfactual claim."""
    groups=defaultdict(list)
    for game in games:
        for role in ('a','b'):
            decisions=load_decisions(game['artifacts'][role]['trace'])
            if not decisions:continue
            row=decisions[0];us=row['state']['us'];them='p2' if us=='p1' else 'p1'
            foe=row['state']['sides'][them];own=row['state']['sides'][us]
            active=foe['active']
            if active is None:continue
            candidate=row['belief_candidates'][active]
            items=defaultdict(float)
            for c in candidate['sets']:items[c['item']]+=c['weight']
            samples=Counter(w[active]['item'] for w in row['sampled_worlds'])
            record={'game':game['game'],'role':role,'own_team':game[role+'_team'],
                'opposing_team':game['b_team' if role=='a' else 'a_team'],'won':game['winner']==role,
                'turn':row['turn'],'own_active':own['pokemon'][own['active']]['species'],
                'foe_active':candidate['species'],'choice':row['choice'],'choice_name':selected_name(row),
                'foe_item_posterior':dict(items),'foe_item_world_counts':dict(samples),
                'trace':game['artifacts'][role]['trace'],'decision_id':row.get('decision_id'),
                'search_support':row['search_support']}
            groups[(game['block'],record['own_team'],record['opposing_team'])].append(record)
    return [{'block':key[0],'own_team':key[1],'opposing_team':key[2],'records':rows}
            for key,rows in groups.items()]


def trace_audit(games,manifest):
    truths=[{mon['species']:mon for mon in parse_team(Path(t['path']).read_text())} for t in manifest['teams']]
    totals=defaultdict(lambda:defaultdict(list)); examples=[]; by_game=[]
    for game in games:
        for role in ('a','b'):
            decisions=load_decisions(game['artifacts'][role]['trace'])
            target_team=truths[game['b_team'] if role=='a' else game['a_team']]
            local=defaultdict(list)
            for decision in decisions:
                us=decision['state']['us'];them='p2' if us=='p1' else 'p1'
                foe=decision['state']['sides'][them];slot=foe['active']
                if slot is None or slot>=len(decision['belief_candidates']):continue
                species=foe['pokemon'][slot]['species']
                if species not in target_team:continue
                truth=target_team[species]
                candidates=decision['belief_candidates'][slot]['sets']
                # Original moves remain a valid audit for these known input teams;
                # original item/spread tests below are prior-only, not post-Trick truth.
                audit=audit_distribution(candidates,truth)
                if not audit:continue
                local['active_move_recall_mass'].append(audit['move_recall_mass'])
                local['active_exact_moves_mass'].append(audit['exact_moves_mass'])
                for move,p in audit['move_mass'].items():
                    if move not in foe['pokemon'][slot]['revealed_moves']:
                        local['unrevealed_move_mass'].append(p)
                        local['unrevealed_zero_support'].append(float(p==0))
                        worlds=decision.get('sampled_worlds',[])
                        if worlds:
                            present=sum(slot<len(world) and move in world[slot]['moves'] for world in worlds)
                            local['unrevealed_move_world_coverage'].append(float(present>0))
                            if p>0:
                                local['supported_move_missed_by_worlds'].append(float(present==0))
                        if p<.05 and len(examples)<200:
                            examples.append({'game':game['game'],'role':role,'won':game['winner']==role,
                                'turn':decision['turn'],'decision_id':decision.get('decision_id'),
                                'choice':decision['choice'],'foe_species':species,'unrevealed_true_move':move,
                                'posterior_mass':p,'trace':game['artifacts'][role]['trace'],
                                'known_moves':foe['pokemon'][slot]['revealed_moves']})
            result={key:sum(values)/len(values) for key,values in local.items() if values}
            outcome='win' if game['winner']==role else 'loss'
            for key,values in local.items():
                totals[role][key].extend(values)
                totals[role+'/'+outcome][key].extend(values)
            by_game.append({'game':game['game'],'role':role,'won':game['winner']==role,'metrics':result})
    summary={arm:{key:{'count':len(v),'mean':sum(v)/len(v)} for key,v in fields.items()} for arm,fields in totals.items()}
    return {'summary':summary,'by_game':by_game,'low_support_examples':examples,
            'limit':'Post-hoc truth audit; A/B visit different states/game lengths, so averages are not matched-state causal effects. Move occurrences/decisions correlated; no held-out strength claim or fitting.'}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',default='evaluation/coherent-sets/screening-v2-manifest.json',type=Path)
    parser.add_argument('--games',default='evaluation/coherent-sets/screening-v2-games.jsonl',type=Path)
    parser.add_argument('--baseline',default='data/set_candidates.json',type=Path)
    parser.add_argument('--mixture',default='data/curated-v1/priors.json',type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args(argv)
    manifest=json.loads(args.manifest.read_text());games=[json.loads(l) for l in args.games.read_text().splitlines()]
    truth_occurrences=[mon for t in manifest['teams'] for mon in parse_team(Path(t['path']).read_text())]
    unique={json.dumps(t,sort_keys=True):t for t in truth_occurrences}
    base=json.loads(args.baseline.read_text());mix=json.loads(args.mixture.read_text())
    prior={name:priors_truth_audit(p,list(unique.values())) for name,p in [('baseline',base),('mixture',mix)]}
    report={'scope':'post-hoc diagnosis only; known private teams never fed to bot or prior fitting',
        'teams':len(manifest['teams']),'unique_component_sets':len(unique),'component_occurrences':len(truth_occurrences),
        'prior_truth_audit':prior,'prior_truth_summary':{name:prior_summary(rows) for name,rows in prior.items()},
        'block_results':block_summary(games),
        'marginal_drift':marginal_drift(base,mix),'trace_audit':trace_audit(games,manifest),
        'matched_openings':opening_audit(games),
        'source_inputs':{'manifest_sha256':hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
                         'games_sha256':hashlib.sha256(args.games.read_bytes()).hexdigest()}}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n')
    for name,rows in prior.items():
        valid=[r['metrics'] for r in rows if r['metrics']]
        print(name,{k:round(sum(r[k] for r in valid)/len(valid),4) for k in ('move_recall_mass','exact_moves_mass','item_mass','moves_item_mass','nature_mass','tera_mass','full_set_mass','speed_underestimate_mass','expected_hp_relative_absolute_error')})
    print('trace summary',json.dumps(report['trace_audit']['summary']))


if __name__=='__main__':main()
