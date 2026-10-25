"""Train-only diagnosis of coherent-prior filtering and marginal distortion.

This analysis never reads test labels to select weights. It scores target-slot
prefix filtering, using the runtime revelation predicates and fallback builder.
A surviving candidate bank can still exclude the later target: observing one
move is not evidence that every incompatible limited template is impossible.
"""
import argparse
import copy
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

from bot.parser import Parser,to_id
from data.pipeline.reveal_evidence import extract
from data.pipeline.import_curated_sets import key
from decision.belief import (_apply_revelations, _fits, _normalised, _prior_entry,
                            _rebuild, _recovery_set, _to_set)
from evaluation.score_reveal_evidence import target_probability


def training_battles(path, limit=None):
    """Select whole source-training battles before examining any log content."""
    result=[]
    for line in Path(path).open():
        row=json.loads(line)
        if row['split']!='train':
            continue
        result.append(row)
        if limit and len(result)>=limit:break
    return result


def prefix_rules(before, side, slot):
    mon=before['sides'][side]['pokemon'][slot]
    return {'item:'+event['source'][5:] for event in before['last_turn']
            if event.get('side')==side and event.get('pokemon')==slot
            and (event.get('source') or '').startswith('item:') and mon['item'] is None}


def condition(candidates, usage, mon, rules):
    """Pure target-slot revelation filter. Targets/future evidence are not arguments."""
    kept=[(s,w) for s,w in candidates if _fits(s,mon,rules)]
    stage='surviving_templates'
    if not kept:
        kept=[(s,w) for s,w in _rebuild(usage,mon) if _fits(s,mon,rules)]
        stage='rebuilt_from_usage'
        if not kept:
            # Exact runtime revelation-mode recovery if even rebuilt candidates miss facts.
            kept=[(s,w) for s,w in candidates+_rebuild(usage,mon) if _fits(s,mon,rules)]
            stage='relaxed_recovery'
            if not kept:
                seed=max(candidates,key=lambda sw:sw[1],default=(None,0))[0]
                candidate=_recovery_set(mon,seed)
                from dataclasses import replace
                item=next((r[5:] for r in rules if r.startswith('item:')),None)
                if item and mon['item'] is None:candidate=replace(candidate,item=item)
                kept=[(candidate,1.)];stage='reconstructed_facts'
    return [(_apply_revelations(s,mon),w) for s,w in _normalised(kept)],stage


def records(battles):
    for battle in battles:
        changed = item_change_offsets(battle['log'])
        for event in extract(battle['log'],battle['battle_id'],include_state=True):
            if not event['native_set_evidence']:continue
            mon=event['before']['sides'][event['side']]['pokemon'][event['slot']]
            field,value=event['field'],event['value']
            if field=='move' and value in mon['revealed_moves'] or field!='move' and mon.get(field)==value:continue
            yield {'battle_id':battle['battle_id'],'started_at':battle['started_at'],
                   'species':event['species'],'side':event['side'],'slot':event['slot'],
                   'field':field,'value':value,'mon':mon,
                   'rules':prefix_rules(event['before'],event['side'],event['slot']),
                   'prior_item_change_context':changed.get((event['side'],event['slot']),float('inf'))<event['event_offset'],
                   'event_offset':event['event_offset'],'turn':event['turn']}


def item_change_offsets(log):
    """Conservative prefix-only context flag; failed exchanges may be censored too."""
    parser=Parser('p1');changed={}
    for offset,line in enumerate(log.splitlines()):
        parts=line.split('|')
        if len(parts)>3 and parts[1]=='move' and to_id(parts[3]) in {'trick','switcheroo','bestow','thief','covet'}:
            for side,state in parser.state['sides'].items():
                if state['active'] is not None:changed.setdefault((side,state['active']),offset)
        parser.feed(line)
    return changed


def loss(p):return -math.log(max(1e-6,min(1.,p)))


def summarize(values):
    if not values:return None
    return {'targets':len(values),'loss':sum(loss(p) for p in values)/len(values),
            'support':sum(p>0 for p in values)/len(values)}


def diagnose(priors, events):
    prepared={};cache={};bins=defaultdict(lambda:defaultdict(list));counts=Counter();examples=[]
    per_field=defaultdict(lambda:defaultdict(list));per_species=defaultdict(lambda:defaultdict(list))
    item_context=defaultdict(lambda:defaultdict(list))
    per_battle=defaultdict(lambda:defaultdict(list))
    for event in events:
        species=event['species'];mon=event['mon'];field=event['field'];target=event['value']
        if species not in prepared:
            entry,source=_prior_entry(priors,species)
            candidates=_normalised([(_to_set(c),c['weight']) for c in entry.get('sets',[])])
            prepared[species]=(entry,candidates)
        entry,original=prepared[species]
        original=original or _normalised(_rebuild(entry.get('usage',{}),mon)) or [(_recovery_set(mon),1.)]
        cachekey=(species,tuple(mon['revealed_moves']),mon['item'],mon['ability'],mon['tera_type'],tuple(sorted(event['rules'])))
        if cachekey not in cache:cache[cachekey]=condition(original,entry.get('usage',{}),mon,event['rules'])
        posterior,stage=cache[cachekey]
        p=target_probability(original,field,target,mon['revealed_moves'])
        q=target_probability(posterior,field,target,mon['revealed_moves'])
        group=stage if q else stage+'/zero_target'
        bins[group]['prior'].append(p);bins[group]['posterior'].append(q)
        per_field[field]['prior'].append(p);per_field[field]['posterior'].append(q)
        per_species[species]['prior'].append(p);per_species[species]['posterior'].append(q)
        battle_key=event['battle_id']+'@'+event['started_at']
        per_battle[battle_key]['prior'].append(p);per_battle[battle_key]['posterior'].append(q)
        context='known_current_item_after_possible_transfer' if event.get('prior_item_change_context') and mon['item'] else 'other'
        item_context[context]['prior'].append(p);item_context[context]['posterior'].append(q)
        counts['targets']+=1;counts[stage]+=1
        if p>0 and q==0:
            counts['prior_supported_to_zero']+=1
            if len(examples)<30:
                examples.append({k:event[k] for k in ('battle_id','species','field','value','turn','event_offset')}
                 | {'known_moves':mon['revealed_moves'],'known_item':mon['item'],'known_ability':mon['ability'],
                    'known_tera':mon['tera_type'],'stage':stage,'prior_mass':p,
                    'posterior_candidates':len(posterior)})
        if p==0 and q>0:counts['zero_to_supported']+=1
    allprior=[p for b in bins.values() for p in b['prior']];allpost=[p for b in bins.values() for p in b['posterior']]
    return {'counts':dict(counts),'overall':{'prior':summarize(allprior),'posterior':summarize(allpost)},
      'by_filter_path':{k:{s:summarize(v) for s,v in b.items()} for k,b in bins.items()},
      'by_field':{k:{s:summarize(v) for s,v in b.items()} for k,b in per_field.items()},
      'by_species':{k:{s:summarize(v) for s,v in b.items()} for k,b in per_species.items()},
      'by_item_history_context':{k:{s:summarize(v) for s,v in b.items()} for k,b in item_context.items()},
      'per_battle':{k:{s:summarize(v) for s,v in b.items()} for k,b in per_battle.items()},
      'support_loss_examples':examples}


def marginal(entry,field):
    result=defaultdict(float)
    for c in entry['sets']:
        value=c['spread']['nature'] if field=='nature' else tuple(c['spread']['evs']) if field=='evs' else c[field]
        result[value]+=c['weight']
    return result


def distortion(old,new):
    result=[]
    for species in old['species']:
        if species not in new['species']:continue
        data={}
        for field in ('item','tera_type','nature','evs'):
            a,b=marginal(old['species'][species],field),marginal(new['species'][species],field)
            tv=sum(abs(a.get(k,0)-b.get(k,0)) for k in set(a)|set(b))/2
            if tv>1e-10:
                top=sorted(((str(k),b.get(k,0)-a.get(k,0),a.get(k,0),b.get(k,0)) for k in set(a)|set(b)),key=lambda x:-abs(x[1]))[:3]
                data[field]={'total_variation':tv,'largest_changes':[{'value':v,'delta':d,'old':a0,'new':b0} for v,d,a0,b0 in top]}
        if data:result.append({'species':species,'fields':data})
    return sorted(result,key=lambda x:-max(v['total_variation'] for v in x['fields'].values()))


def sampling_diversity(entry, worlds=8):
    weights=[c['weight'] for c in entry['sets']]
    total=sum(weights);weights=[w/total for w in weights]
    return {'candidate_records':len(weights),'effective_set_count':1/sum(w*w for w in weights),
            'largest_set_mass':max(weights),
            'expected_distinct_sets_in_worlds':sum(1-(1-w)**worlds for w in weights),'worlds':worlds}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--logs',type=Path,default=Path('runs/reveals/tiger-200.jsonl'))
    parser.add_argument('--baseline',type=Path,default=Path('data/set_candidates.json'))
    parser.add_argument('--mixture',type=Path,default=Path('data/curated-v1/priors.json'))
    parser.add_argument('--output',type=Path,default=Path('evaluation/coherent-sets/v2-diagnosis-predictions.json'))
    args=parser.parse_args()
    battles=training_battles(args.logs)
    events=list(records(battles))
    old=json.loads(args.baseline.read_text());new=json.loads(args.mixture.read_text())
    shifts=distortion(old,new)
    report={'scope':'train100 only; old test100 excluded from analysis/tuning',
      'source_sha256':hashlib.sha256(args.logs.read_bytes()).hexdigest(),'training_battles':len(battles),
      'targets':len(events),'filter_model':'shared target-slot revelation filter, direct prefix facts and confirmed item events; no damage/speed replay',
      'baseline':diagnose(old,events),'v1_mixture':diagnose(new,events),
      'marginal_distortions':shifts,
      'initial_per_pokemon_sampling_diversity':{d['species']:{'baseline':sampling_diversity(old['species'][d['species']]),
                                                          'v1':sampling_diversity(new['species'][d['species']])} for d in shifts},
      'limitations':['Targets are partial and selection-biased revelations, not complete hidden sets.',
       'Uniform remaining-move model is not action prediction or decision-weighted value.',
       'Filtering on a small truncated hypothesis bank can eliminate future truth while retaining other compatible hypotheses.',
       'Observed item/ability changes can make current state a poor proxy for original-role identity; no full EV labels.']}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('training_battles','targets')},indent=2))
    for name in ('baseline','v1_mixture'):print(name,json.dumps(report[name]['overall']),report[name]['counts'])


if __name__=='__main__':main()
