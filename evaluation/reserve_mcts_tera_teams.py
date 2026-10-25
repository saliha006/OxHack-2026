"""Reserve new follow-up rosters for the confirmed fainted-Tera reconstruction defect."""
from itertools import product
import argparse
import hashlib
import json
from pathlib import Path
import random
import re

from evaluation.reserve_mcts_stage_teams import REPLACEMENTS
from evaluation.mcts_improvements.reserve_teams import SCREENING, WEATHER_COMPONENTS, RATIONALES
from evaluation.mcts_improvements.run import validate_teams,write_json
from evaluation.mcts_improvements.identity import file_hash

THIRD_ROLE = [
 ('Darkrai',['Darkrai','Latios','Weavile','Lokix','Walking Wake','Kyurem']),
 ('Darkrai',['Darkrai','Gholdengo','Primarina','Walking Wake','Kyurem']),
 ('Latios',['Latios','Iron Crown','Primarina','Kyurem','Walking Wake']),
 ('Hydrapple',['Hydrapple','Iron Crown','Dragonite','Kyurem']),
 ('Corviknight',['Corviknight','Zapdos','Moltres','Skarmory','Weezing-Galar']),
 ('Moltres',['Moltres','Zapdos','Corviknight','Skarmory','Tornadus-Therian']),
 ('Slowking-Galar',['Slowking-Galar','Pecharunt','Zapdos','Moltres','Clefable']),
 ('Zapdos',['Zapdos','Tornadus-Therian','Latios','Hydrapple']),
 ('Corviknight',['Corviknight','Skarmory','Weezing-Galar','Toxapex','Moltres']),
 ('Weezing-Galar',['Weezing-Galar','Corviknight','Skarmory','Pecharunt']),
]


def reserve(root,output,seed=2026102515):
    root,output=Path(root).resolve(),Path(output).resolve()
    if output.exists(): raise ValueError('preserve existing reservations')
    used=set()
    for path in (root/'evaluation/mcts-improvements').rglob('teams.json'):
        for team in json.loads(path.read_text()).get('teams',[]):
            if 'roster' in team: used.add(tuple(sorted(team['roster'])))
    components={}
    for path in sorted((root/'bot/teams/standin').glob('*.txt')):
        roster=[]
        for block in re.split(r'\n\s*\n',path.read_text().strip()):
            name=re.sub(r' \([MF]\)$','',block.splitlines()[0].split(' @ ')[0].strip())
            roster.append(name)
            components.setdefault(name,(block,path.relative_to(root).as_posix()))
        used.add(tuple(sorted(roster)))
    for name,block in WEATHER_COMPONENTS.items():
        components[name]=(block,'evaluation/mcts_improvements/reserve_teams.py: constructed weather component')
    rng=random.Random(seed)
    pools=[]
    texts=[]
    for phase in ('screening','confirmation'):
        records=[]
        for index,((style,template),replacements,third) in enumerate(zip(SCREENING,REPLACEMENTS,THIRD_ROLE)):
            options=[]
            for first,second,last in product(replacements[0][1],replacements[1][1],third[1]):
                substitutions={replacements[0][0]:first,replacements[1][0]:second,third[0]:last}
                roster=[substitutions.get(name,name) for name in template]
                if len(set(roster))==6 and tuple(sorted(roster)) not in used: options.append(roster)
            rng.shuffle(options)
            if not options: raise ValueError('not enough unused role-preserving combinations')
            roster=options[0]
            used.add(tuple(sorted(roster)))
            text='\n\n'.join(components[name][0] for name in roster).strip()
            texts.append(text)
            records.append({'id':f'tera-followup-{phase}-{index+1:02d}','roster':roster,
                'style':style,'design_rationale':RATIONALES[style],
                'component_sources':[components[name][1] for name in roster],
                'sha256':hashlib.sha256(text.encode()).hexdigest()})
        pools.append((phase,records))
    validations=iter(validate_teams(root/'pokemon-showdown',texts))
    text_iterator=iter(texts)
    output.mkdir(parents=True)
    for phase,records in pools:
        folder=output/phase
        folder.mkdir()
        for index,record in enumerate(records):
            path=folder/f'{index+1:02d}.txt'
            path.write_text(next(text_iterator)+'\n')
            record.update(path=str(path),validation_errors=next(validations)['errors'])
        write_json(folder/'teams.json',{'phase':phase,'stage':'fainted-Tera state follow-up','teams':records,
            'provenance':{'kind':'new handmade roster combinations with familiar component sets',
                'reservation_seed':seed,'construction_source_sha256':file_hash(Path(__file__)),
                'reservation_timing':'After earlier Stage1/Stage2 screen outcomes and discovery of a fainted-Tera state defect, before follow-up outcomes. Fixed role substitutions and seed; no winning/losing roster selection.',
                'holdout_limit':'Not an external set holdout. Exact six-species rosters are disjoint from previous reservation pools and stand-in originals; component sets overlap. Styles are design intentions, competitive viability unmeasured. No evaluation paste fits priors.',
                'rules':'validated using pinned local Gen9OU TeamValidator'}})
    return len(texts)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    print(json.dumps({'reserved_teams':reserve(args.root,args.output),'root':str(args.output)}))


if __name__=='__main__': main()
