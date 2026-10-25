"""Conservative coherent-prior revision: usage-supported roles and bounded marginal drift.

No battle-team or future-revelation labels are consumed. Usage factors are a
heuristic compatibility score, not an estimated joint set likelihood.
"""
import argparse
import copy
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

from data.pipeline.import_curated_sets import key, mix


def marginal_probability(shares, value, *, floor=.005):
    if not shares:
        return 1.  # Missing category supplies no evidence.
    # Stored usage categories are truncated: absence is unknown residual, never impossibility.
    residual = max(0., 1.-sum(shares.values()))
    return max(floor, min(1., shares.get(value, max(floor, residual/10))))


def compatibility(candidate, usage, ev_scale=128.):
    factors = []
    for category, value, weight in [('items',candidate['item'],1.),
            ('abilities',candidate['ability'],.5),('tera_types',candidate['tera_type'],.5)]:
        if usage.get(category):
            factors.append((math.log(marginal_probability(usage[category],value)),weight))
    moves = usage.get('moves',{})
    if moves:
        # Move shares sum to around four, unlike a categorical item distribution.
        lp = sum(math.log(max(.005,min(1.,moves.get(m,.005)))) for m in candidate['moves'])/len(candidate['moves'])
        factors.append((lp,1.))
    spreads = usage.get('spreads',[])
    if spreads:
        nature = candidate['spread']['nature']
        nature_shares = defaultdict(float)
        for spread,weight in spreads:
            nature_shares[spread['nature']] += weight
        factors.append((math.log(marginal_probability(nature_shares,nature)),.5))
        evs = candidate['spread']['evs']
        support = sum(weight*math.exp(-sum(abs(a-b) for a,b in zip(evs,spread['evs']))/ev_scale)
                      for spread,weight in spreads)
        factors.append((math.log(max(.005,min(1.,support))),1.))
    return math.exp(sum(lp*w for lp,w in factors)/sum(w for _,w in factors)) if factors else 1.


def features(candidate):
    result = {('item',candidate['item']),('ability',candidate['ability']),('tera',candidate['tera_type']),
              ('nature',candidate['spread']['nature'])}
    result.update(('move',m) for m in candidate['moves'])
    for stat,ev in enumerate(candidate['spread']['evs']):
        bucket = 0 if ev<32 else 1 if ev<128 else 2 if ev<224 else 3
        result.add((f'ev_{stat}',bucket))
    return result


def marginal(candidates, weights=None):
    result = defaultdict(float)
    if weights is None:
        weights = [c['weight'] for c in candidates]
    total=sum(weights)
    if not total:
        return result
    for candidate,weight in zip(candidates,weights):
        for feature in features(candidate):result[feature] += weight/total
    return result


def calibrate(priors, bank, *, max_fraction=.25, max_shift=.075):
    if not 0 <= max_fraction < 1 or not 0 < max_shift <= 1:
        raise ValueError('finite fraction in [0,1), and marginal shift in (0,1] required')
    adjusted=copy.deepcopy(bank)
    grouped=defaultdict(list)
    for record in adjusted['records']:grouped[record['species']].append(record)
    role_weights=defaultdict(dict)
    scores={}
    for species,records in grouped.items():
        usage=priors['species'].get(species,{}).get('usage',{})
        roles=defaultdict(list)
        for r in records:roles[(r['section'],r['role'])].append(r)
        for (_,role), variants in roles.items():
            original_mass=sum(r['variant_weight'] for r in variants)
            weighted_mass=0.
            for record in variants:
                score=compatibility(record['candidate'],usage)
                scores[record['id']]=score
                record['variant_weight'] *= score
                weighted_mass += record['variant_weight']
            role_weights[species][role]=weighted_mass/original_mass
    if max_fraction == 0:
        return copy.deepcopy(priors), {'max_fraction':0,'max_marginal_shift':max_shift,'species':{}}
    proposed,provenance=mix(priors,adjusted,max_fraction,role_weights=role_weights)
    fractions,details={},{}
    for species,entry in provenance.items():
        if 'alias_of' in entry:continue
        candidates=proposed['species'][species]['sets']
        # Candidate order matches provenance; recover the normalized curated component.
        qweights=[record['curated_component_mass']/max_fraction for record in entry['candidates']]
        q=marginal(candidates,qweights)
        p=marginal(priors['species'][species]['sets'])
        drift=max((abs(q.get(k,0)-p.get(k,0)) for k in set(q)|set(p)),default=0)
        fraction=min(max_fraction,max_shift/drift) if drift else max_fraction
        fractions[species]=fraction
        biggest=sorted(((abs(q.get(k,0)-p.get(k,0)),k,p.get(k,0),q.get(k,0)) for k in set(p)|set(q)),reverse=True)[:8]
        details[species]={'effective_curated_fraction':fraction,'uncapped_max_component_drift':drift,
            'predicted_max_marginal_shift':fraction*drift,
            'largest_component_differences':[{'feature':list(k),'broad':pv,'curated':qv,'component_difference':d}
                                             for d,k,pv,qv in biggest]}
    result,final=mix(priors,adjusted,max_fraction,role_weights=role_weights,species_fractions=fractions)
    # Assert the promised bound on actual mixtures, rather than assuming assembly preserves it.
    for species in details:
        p=marginal(priors['species'][species]['sets']);q=marginal(result['species'][species]['sets'])
        actual=max((abs(p.get(k,0)-q.get(k,0)) for k in set(p)|set(q)),default=0)
        if actual>max_shift+1e-10:raise AssertionError('marginal drift bound violated')
        details[species]['actual_max_marginal_shift']=actual
    report={'method':'usage-supported coherent roles with conservative marginal-drift cap',
        'max_fraction':max_fraction,'max_marginal_shift':max_shift,
        'bounds_apply_to':'initial per-species priors; confirmed observations may shift posterior probabilities beyond the cap',
        'usage_compatibility':'tempered geometric score of item, moves, ability, Tera, nature and smooth EV proximity; heuristic, not joint frequency',
        'missingness':'missing categories neutral; absent trimmed values floored; EVs use smooth L1 kernel scale128',
        'role_compatibilities':scores,'species':details,'provenance':final,
        'tuning_inputs':'existing usage prior only; global parameters selected separately on training-only evidence',
        'runtime_changed':False,'default_changed':False}
    return result,report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--priors',type=Path,default=Path('data/set_candidates.json'))
    parser.add_argument('--bank',type=Path,default=Path('data/curated-v1/bank.json'))
    parser.add_argument('--max-fraction',type=float,default=.25)
    parser.add_argument('--max-shift',type=float,default=.075)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    if args.output.exists():parser.error('fresh output directory required')
    raw=args.priors.read_bytes();bankraw=args.bank.read_bytes()
    result,report=calibrate(json.loads(raw),json.loads(bankraw),max_fraction=args.max_fraction,max_shift=args.max_shift)
    report.update(broad_prior_sha256=hashlib.sha256(raw).hexdigest(),bank_sha256=hashlib.sha256(bankraw).hexdigest())
    args.output.mkdir(parents=True)
    (args.output/'priors.json').write_text(json.dumps(result,indent=1)+'\n')
    (args.output/'manifest.json').write_text(json.dumps(report,indent=1)+'\n')
    print(json.dumps({'species':len(report['species']),'max_fraction':args.max_fraction,'max_shift':args.max_shift}))


if __name__=='__main__':main()
