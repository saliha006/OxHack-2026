"""Independent descriptive marginal/diversity audit; never consumes game truth."""
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path


def distribution(candidates):
    result=defaultdict(float);mass=sum(c['weight'] for c in candidates)
    for c in candidates:
        features=[('item',c['item']),('ability',c['ability']),('tera',c['tera_type']),('nature',c['spread']['nature'])]
        features += [('move',m) for m in set(c['moves'])]
        for i,ev in enumerate(c['spread']['evs']):
            bucket=next(j for j,maximum in enumerate((31,127,223,252)) if ev<=maximum)
            features.append((f'ev_{i}',bucket))
        for feature in features:result[feature]+=c['weight']/mass
    return result


def diversity(candidates):
    # Compare distributions over complete unordered move-set identities, not duplicate records.
    weights=defaultdict(float)
    for c in candidates:
        ident=json.dumps([sorted(c['moves']),c['item'],c['ability'],c['tera_type'],c['spread'],c.get('ivs',[31]*6)],sort_keys=True)
        weights[ident]+=c['weight']
    total=sum(weights.values());w=[p/total for p in weights.values() if p>0]
    return {'distinct_complete_sets':len(w),'effective_set_count':1/sum(p*p for p in w),
            'entropy_nats':-sum(p*math.log(p) for p in w),'maximum_set_mass':max(w)}


def audit(broad,alternatives):
    rows=[];summaries={}
    for name,priors in alternatives.items():
        shifts=[];diversities=[]
        for species,old in broad['species'].items():
            new=priors['species'][species]
            p,q=distribution(old['sets']),distribution(new['sets'])
            changes=sorted(((abs(q.get(k,0)-p.get(k,0)),k,p.get(k,0),q.get(k,0)) for k in set(p)|set(q)),reverse=True)
            maxshift=changes[0][0] if changes else 0
            by_family=defaultdict(float)
            for shift,(family,_),_,_ in changes:by_family[family]=max(by_family[family],shift)
            olddiv,newdiv=diversity(old['sets']),diversity(new['sets'])
            row={'arm':name,'species':species,'maximum_absolute_marginal_shift':maxshift,
                 'maximum_shift_by_family':dict(by_family),'broad_diversity':olddiv,'diversity':newdiv,
                 'largest_shifts':[{'feature':list(k),'shift':d,'broad':pv,'alternative':qv} for d,k,pv,qv in changes[:8]]}
            rows.append(row);shifts.append(maxshift);diversities.append((olddiv,newdiv))
        summaries[name]={'species_and_aliases':len(shifts),'max_absolute_marginal_shift':max(shifts),
            'mean_species_max_shift':sum(shifts)/len(shifts),
            'species_over_075_shift':sum(d>.075+1e-10 for d in shifts),
            'mean_effective_set_count':sum(d[1]['effective_set_count'] for d in diversities)/len(diversities),
            'mean_broad_effective_set_count':sum(d[0]['effective_set_count'] for d in diversities)/len(diversities),
            'mean_maximum_set_mass':sum(d[1]['maximum_set_mass'] for d in diversities)/len(diversities)}
    return {'scope':'General static prior audit only; no private teams, revelations or battle outcomes consumed',
            'feature_definition':'categorical item/ability/Tera/nature, Bernoulli move inclusion, EV bins0..31/32..127/128..223/224..252',
            'weighting':'Unweighted descriptive averages across species/form aliases; not a population distribution',
            'summary':summaries,'rows':rows}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default='evaluation/coherent-sets/v2/marginal-audit.json',type=Path)
    args=parser.parse_args()
    paths={'broad':Path('data/set_candidates.json'),'v1':Path('data/curated-v1/priors.json'),'revised':Path('data/curated-v2/priors.json')}
    inputs={name:json.loads(path.read_text()) for name,path in paths.items()}
    result=audit(inputs['broad'],{k:v for k,v in inputs.items() if k!='broad'})
    result['inputs']={name:{'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()} for name,path in paths.items()}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result['summary'],indent=2))


if __name__=='__main__':main()
