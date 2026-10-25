"""Reserve different synthetic rosters from the concurrent search-policy study.

Known regression component sets; these are not independent external team holdouts.
No set in this pool is used to fit the prior mixture.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

from evaluation.mcts_improvements.reserve_teams import WEATHER_COMPONENTS, SCREENING, CONFIRMATION
from evaluation.mcts_improvements.run import validate_teams, write_json

ROSTERS = [
('offense',['Darkrai','Gholdengo','Zamazenta','Weavile','Great Tusk','Primarina']),
('offense',['Weavile','Darkrai','Dragonite','Latios','Great Tusk','Cinderace']),
('offense',['Lokix','Iron Crown','Zamazenta','Gholdengo','Great Tusk','Ogerpon-Wellspring']),
('sun offense',['Torkoal','Walking Wake','Hydrapple','Dragonite','Cinderace','Great Tusk']),
('balance',['Ting-Lu','Corviknight','Iron Crown','Primarina','Pecharunt','Great Tusk']),
('balance',['Garganacl','Gliscor','Moltres','Gholdengo','Kyurem','Alomomola']),
('balance',['Tinkaton','Slowking-Galar','Hydrapple','Cinderace','Primarina','Zamazenta']),
('rain offense',['Pelipper','Barraskewda','Zapdos','Gholdengo','Iron Crown','Primarina']),
('semistall',['Blissey','Dondozo','Corviknight','Gliscor','Alomomola','Iron Crown']),
('semistall',['Toxapex','Weezing-Galar','Iron Treads','Clefable','Pecharunt','Weavile']),
]


def reserve(root,simulator,output):
    if output.exists(): raise FileExistsError('reservation exists')
    components={}; used={tuple(sorted(roster)) for _,roster in SCREENING+CONFIRMATION}
    for path in sorted((root/'bot/teams/standin').glob('*.txt')):
        roster=[]
        for block in re.split(r'\n\s*\n',path.read_text().strip()):
            name=re.sub(r' \([MF]\)$','',block.splitlines()[0].split(' @ ')[0].strip())
            components.setdefault(name,(block,path.relative_to(root).as_posix()))
            roster.append(name)
        used.add(tuple(sorted(roster)))
    components.update({name:(text,'existing hand-constructed weather component') for name,text in WEATHER_COMPONENTS.items()})
    texts=[]
    for _,roster in ROSTERS:
        if tuple(sorted(roster)) in used: raise ValueError('roster reused')
        texts.append('\n\n'.join(components[name][0] for name in roster).strip())
    checked=validate_teams(simulator,texts)
    output.mkdir(parents=True)
    records=[]
    for i,((style,roster),text) in enumerate(zip(ROSTERS,texts)):
        path=output/f'{i+1:02d}.txt';path.write_text(text+'\n')
        records.append({'id':f'coherent-screening-{i+1:02d}','path':str(path.resolve()),'style':style,'roster':roster,
                        'sha256':hashlib.sha256(text.encode()).hexdigest(),
                        'component_sources':[components[name][1] for name in roster]})
    result={'teams':records,'provenance':{'kind':'new synthetic rosters using known regression component sets',
            'holdout_limit':'No independent external set holdout; roster combinations differ from frozen data-independent screening/confirmation pools. Source-wide usage overlap cannot be excluded.',
            'reservation':'fixed before outcomes; no fitting on these team files','validator':'pinned local Gen9 OU TeamValidator'}}
    write_json(output/'teams.json',result)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--simulator',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    reserve(Path('.'),args.simulator,args.output)
