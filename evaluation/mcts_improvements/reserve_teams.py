"""Construct new roster combinations from existing regression sets, without prior fitting.

These are reserved synthetic teams, not an independent external holdout. Component
sets are familiar from regression history; only their roster combinations are new.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

from .run import validate_teams, write_json

SCREENING = [
('offense',['Darkrai','Gholdengo','Zamazenta','Dragonite','Great Tusk','Primarina']),
('offense',['Weavile','Darkrai','Dragonite','Iron Crown','Great Tusk','Cinderace']),
('offense',['Lokix','Latios','Zamazenta','Gholdengo','Great Tusk','Ogerpon-Wellspring']),
('sun offense',['Torkoal','Walking Wake','Hydrapple','Zamazenta','Cinderace','Great Tusk']),
('balance',['Ting-Lu','Corviknight','Darkrai','Primarina','Pecharunt','Great Tusk']),
('balance',['Garganacl','Gliscor','Moltres','Gholdengo','Dragonite','Alomomola']),
('balance',['Tinkaton','Slowking-Galar','Hydrapple','Cinderace','Kyurem','Zamazenta']),
('rain offense',['Pelipper','Barraskewda','Zapdos','Gholdengo','Great Tusk','Primarina']),
('semistall',['Blissey','Dondozo','Corviknight','Gliscor','Alomomola','Darkrai']),
('semistall',['Toxapex','Weezing-Galar','Iron Treads','Clefable','Moltres','Weavile']),
]
CONFIRMATION = [
('offense',['Darkrai','Gholdengo','Zamazenta','Dragonite','Great Tusk','Iron Crown']),
('offense',['Weavile','Latios','Dragonite','Iron Crown','Great Tusk','Cinderace']),
('offense',['Lokix','Darkrai','Zamazenta','Gholdengo','Great Tusk','Primarina']),
('sun offense',['Torkoal','Walking Wake','Hydrapple','Zamazenta','Tinkaton','Great Tusk']),
('balance',['Ting-Lu','Corviknight','Darkrai','Ogerpon-Wellspring','Pecharunt','Great Tusk']),
('balance',['Garganacl','Gliscor','Moltres','Gholdengo','Zamazenta','Alomomola']),
('balance',['Tinkaton','Slowking-Galar','Hydrapple','Cinderace','Kyurem','Dragonite']),
('rain offense',['Pelipper','Barraskewda','Zapdos','Iron Crown','Great Tusk','Ogerpon-Wellspring']),
('semistall',['Blissey','Dondozo','Corviknight','Gliscor','Alomomola','Weavile']),
('semistall',['Toxapex','Weezing-Galar','Iron Treads','Clefable','Pecharunt','Darkrai']),
]


WEATHER_COMPONENTS = {
'Torkoal': """Torkoal @ Heat Rock
Ability: Drought
Tera Type: Flying
EVs: 248 HP / 252 Def / 8 SpD
Bold Nature
IVs: 0 Atk
- Lava Plume
- Stealth Rock
- Rapid Spin
- Protect""",
'Pelipper': """Pelipper @ Damp Rock
Ability: Drizzle
Tera Type: Ground
EVs: 248 HP / 252 Def / 8 SpD
Relaxed Nature
IVs: 0 Spe
- Hurricane
- Surf
- U-turn
- Roost""",
'Barraskewda': """Barraskewda @ Choice Band
Ability: Swift Swim
Tera Type: Water
EVs: 252 Atk / 4 SpD / 252 Spe
Adamant Nature
- Liquidation
- Flip Turn
- Close Combat
- Aqua Jet""",
}

RATIONALES = {
'offense':'Multiple fast or priority attackers, setup/wallbreaking pressure, and Great Tusk hazard removal.',
'sun offense':'Drought plus Heat Rock supports Walking Wake and Protosynthesis attackers; hazard removal supports the setter. Team viability is a design hypothesis, not a competitive result.',
'rain offense':'Drizzle plus Damp Rock enables Swift Swim and accurate Hurricane; pivots, special attackers and Great Tusk hazard removal complement the physical rain attacker. Team viability remains unmeasured.',
'balance':'Defensive pivots/checks accompany hazard support and an offensive progress maker; no claim of tournament quality.',
'semistall':'Recovery-heavy defensive core plus an offensive progress maker; long-battle censoring is reported explicitly.',
}


def reserve(root, output, phase):
    root, output=Path(root).resolve(),Path(output).resolve()
    if output.exists():
        raise ValueError('reservation destination exists; never overwrite a frozen pool')
    components={}
    original_rosters=[]
    for path in sorted((root/'bot/teams/standin').glob('*.txt')):
        roster=[]
        for block in re.split(r'\n\s*\n',path.read_text().strip()):
            name=re.sub(r' \([MF]\)$','',block.splitlines()[0].split(' @ ')[0].strip())
            components.setdefault(name,(block,path.relative_to(root).as_posix()))
            roster.append(name)
        original_rosters.append(sorted(roster))
    for name,block in WEATHER_COMPONENTS.items():
        components[name]=(block,'evaluation/mcts_improvements/reserve_teams.py: hand-constructed legal weather component, not fitted')
    chosen=SCREENING if phase=='screening' else CONFIRMATION
    texts=[]
    for style,roster in chosen:
        assert len(set(roster))==6
        assert sorted(roster) not in original_rosters
        texts.append('\n\n'.join(components[name][0] for name in roster).strip())
    checked=validate_teams(root/'pokemon-showdown',texts)
    output.mkdir(parents=True)
    records=[]
    for index,((style,roster),text,validation) in enumerate(zip(chosen,texts,checked)):
        path=output/f'{index+1:02d}.txt'
        path.write_text(text+'\n')
        records.append({'id':f'{phase}-{index+1:02d}','path':str(path),
                        'sha256':hashlib.sha256(text.encode()).hexdigest(),'style':style,'roster':roster,'design_rationale':RATIONALES[style],
                        'component_sources':[components[name][1] for name in roster],
                        'validation_errors':validation['errors']})
    manifest={'phase':phase,'provenance':{
        'kind':'synthetic new roster combinations from existing regression sets plus three hand-constructed weather components',
        'reservation':'selected and validated before this stage outcome inspection; unchanged throughout screening',
        'holdout_limit':'Not an independent external set holdout. Components and species have appeared in regression; these exact six-species rosters are new combinations. No evaluation paste is used to fit priors. Confirmation roster combinations differ from screening, but share component sets.',
        'rules':'local pinned Showdown gen9ou TeamValidator'},'teams':records}
    write_json(output/'teams.json',manifest)
    return manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--phase',choices=('screening','confirmation'),required=True)
    args=parser.parse_args()
    print(json.dumps(reserve(args.root,args.output,args.phase),indent=2))


if __name__=='__main__': main()
