"""Reserve later-stage synthetic roster pools before seeing scored outcomes.

This constructs role-preserving variations of the screening design. They remain
unproven handmade teams with familiar sets, not external holdouts. The manifest
records every source block, substitution, validation result and reservation seed.
"""
import argparse
import hashlib
from itertools import product
import json
from pathlib import Path
import random
import re

from evaluation.mcts_improvements.reserve_teams import SCREENING, WEATHER_COMPONENTS, RATIONALES
from evaluation.mcts_improvements.run import validate_teams, write_json

# Each pair changes specified roles only. These are design intentions, not measured team quality.
REPLACEMENTS = [
 [('Primarina',['Kyurem','Latios','Walking Wake','Iron Crown']),('Zamazenta',['Zamazenta','Weavile','Lokix','Ogerpon-Wellspring'])],
 [('Iron Crown',['Iron Crown','Gholdengo','Primarina','Latios','Kyurem']),('Cinderace',['Cinderace','Zapdos','Moltres','Slowking-Galar'])],
 [('Ogerpon-Wellspring',['Ogerpon-Wellspring','Darkrai','Walking Wake','Primarina','Kyurem']),('Lokix',['Lokix','Weavile','Dragonite','Cinderace'])],
 [('Cinderace',['Cinderace','Tinkaton','Iron Crown','Dragonite','Moltres']),('Zamazenta',['Zamazenta','Weavile','Ogerpon-Wellspring','Lokix'])],
 [('Ting-Lu',['Ting-Lu','Garganacl','Tinkaton','Iron Treads']),('Pecharunt',['Pecharunt','Slowking-Galar','Moltres','Zapdos','Gliscor'])],
 [('Garganacl',['Garganacl','Ting-Lu','Tinkaton','Iron Treads']),('Dragonite',['Dragonite','Zamazenta','Weavile','Darkrai','Latios'])],
 [('Kyurem',['Kyurem','Iron Crown','Latios','Primarina','Walking Wake']),('Zamazenta',['Zamazenta','Dragonite','Weavile','Lokix'])],
 [('Gholdengo',['Gholdengo','Iron Crown','Latios','Darkrai']),('Primarina',['Primarina','Ogerpon-Wellspring','Walking Wake','Kyurem','Hydrapple'])],
 [('Darkrai',['Darkrai','Weavile','Latios','Zamazenta','Lokix','Dragonite']),('Gliscor',['Gliscor','Ting-Lu','Garganacl','Tinkaton'])],
 [('Weavile',['Weavile','Darkrai','Latios','Zamazenta','Lokix','Dragonite']),('Clefable',['Clefable','Blissey','Slowking-Galar','Pecharunt'])],
]


def reserve_all(root, output, seed=2026102503):
    root,output=Path(root).resolve(),Path(output).resolve()
    if output.exists():
        raise ValueError('do not overwrite an existing reservation')
    components={}
    used=set()
    for path in sorted((root/'bot/teams/standin').glob('*.txt')):
        roster=[]
        for block in re.split(r'\n\s*\n',path.read_text().strip()):
            name=re.sub(r' \([MF]\)$','',block.splitlines()[0].split(' @ ')[0].strip())
            components.setdefault(name,(block,path.relative_to(root).as_posix()))
            roster.append(name)
        used.add(tuple(sorted(roster)))
    for path in (root/'evaluation/mcts-improvements').glob('teams-*/teams.json'):
        for team in json.loads(path.read_text())['teams']:
            used.add(tuple(sorted(team['roster'])))
    for name,block in WEATHER_COMPONENTS.items():
        components[name]=(block,'evaluation/mcts_improvements/reserve_teams.py: hand-constructed weather component')
    rng=random.Random(seed)
    possibilities=[]
    for (style,roster),replacements in zip(SCREENING,REPLACEMENTS):
        options=[]
        for first,second in product(replacements[0][1],replacements[1][1]):
            candidate=[first if name==replacements[0][0] else second if name==replacements[1][0] else name for name in roster]
            if len(set(candidate))==6:
                options.append(candidate)
        rng.shuffle(options)
        possibilities.append((style,roster,options))
    pools=[]
    texts=[]
    for stage in ('stage2','stage3','stage4-fixed','stage4-adaptive','stage5-guard','stage6-mixing'):
        for phase in ('screening','confirmation'):
            pool=[]
            for index,(style,template,options) in enumerate(possibilities):
                roster=next((r for r in options if tuple(sorted(r)) not in used),None)
                if roster is None:
                    raise ValueError(f'not enough distinct design variants for {stage}/{phase}/template{index}')
                used.add(tuple(sorted(roster)))
                text='\n\n'.join(components[name][0] for name in roster).strip()
                pool.append({'id':f'{stage}-{phase}-{index+1:02d}', 'style':style,
                             'roster':roster,'template_roster':template,
                             'design_rationale':RATIONALES[style],
                             'substitutions':[{'from':old,'to':new} for old,new in zip(template,roster) if old!=new],
                             'component_sources':[components[name][1] for name in roster],
                             'sha256':hashlib.sha256(text.encode()).hexdigest()})
                texts.append(text)
            pools.append((stage,phase,pool))
    validations=iter(validate_teams(root/'pokemon-showdown',texts))
    text_iterator=iter(texts)
    output.mkdir(parents=True)
    index=[]
    for stage,phase,pool in pools:
        folder=output/f'{stage}-{phase}'
        folder.mkdir()
        for i,record in enumerate(pool):
            path=folder/f'{i+1:02d}.txt'
            path.write_text(next(text_iterator)+'\n')
            record.update(path=str(path),validation_errors=next(validations)['errors'])
        provenance={'kind':'new handmade roster combinations of familiar regression sets and three weather components',
            'reserved_date':'2026-10-25','reservation_seed':seed,
            'reservation':'frozen before inspecting any scored stage1 outcome; later-stage pools have disjoint six-species rosters from each other, prior reservations and regression originals',
            'holdout_limit':'Not an independent external set holdout. Species and component sets overlap; role/style labels are design intentions and team viability is unproven. No team paste is used for prior fitting.',
            'comparison_pairing':'Within a stage the same pool is reserved jointly for comparisons to original baseline and predecessor; paired schedule controls matchup difficulty. It is fresh relative to prior-stage evaluations, not independent between these paired arms.',
            'rules':'all teams validated using pinned local gen9ou TeamValidator before any scored outcomes'}
        manifest={'phase':phase,'stage':stage,'provenance':provenance,'teams':pool}
        write_json(folder/'teams.json',manifest)
        index.append({'stage':stage,'phase':phase,'manifest':str(folder/'teams.json'),
                      'team_hashes':[record['sha256'] for record in pool]})
    write_json(output/'index.json',{'reservation_seed':seed,'pools':index})
    return index


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    index=reserve_all(args.root,args.output)
    print(json.dumps({'pools':len(index),'teams':sum(len(pool['team_hashes']) for pool in index),'index':str(args.output/'index.json')}))


if __name__=='__main__': main()
