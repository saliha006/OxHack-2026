"""Reserve final cumulative comparison rosters separately from stage experiments."""
from itertools import product
import argparse
import hashlib
import json
from pathlib import Path
import random
import re

from evaluation.reserve_mcts_stage_teams import REPLACEMENTS
from evaluation.mcts_improvements.reserve_teams import SCREENING, WEATHER_COMPONENTS, RATIONALES
from evaluation.mcts_improvements.identity import file_hash
from evaluation.mcts_improvements.run import validate_teams,write_json


def reserve(root,output,seed=2026102590):
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
    batches=[]
    texts=[]
    for phase in ('screening','confirmation'):
        teams=[]
        for (style,template),replacements in zip(SCREENING,REPLACEMENTS):
            options=[]
            for first,second in product(replacements[0][1],replacements[1][1]):
                roster=[first if n==replacements[0][0] else second if n==replacements[1][0] else n for n in template]
                if len(set(roster))==6 and tuple(sorted(roster)) not in used: options.append(roster)
            rng.shuffle(options)
            if not options: raise ValueError('not enough unused role-preserving combinations')
            roster=options[0]
            used.add(tuple(sorted(roster)))
            text='\n\n'.join(components[n][0] for n in roster).strip()
            texts.append(text)
            teams.append({'roster':roster,'style':style,'design_rationale':RATIONALES[style],
                'component_sources':[components[n][1] for n in roster],
                'sha256':hashlib.sha256(text.encode()).hexdigest()})
        batches.append((phase,teams))
    checked=iter(validate_teams(root/'pokemon-showdown',texts))
    text_iterator=iter(texts)
    output.mkdir(parents=True)
    for phase,teams in batches:
        folder=output/phase
        folder.mkdir()
        for index,team in enumerate(teams):
            path=folder/f'{index+1:02d}.txt'
            path.write_text(next(text_iterator)+'\n')
            team.update(id=f'cumulative-{phase}-{index+1:02d}',path=str(path),validation_errors=next(checked)['errors'])
        write_json(folder/'teams.json',{'phase':phase,'stage':'final cumulative comparison','teams':teams,
            'provenance':{'kind':'new synthetic roster combinations, separated from all stage experiment reservations',
            'reservation_seed':seed,'construction_rules_sha256':file_hash(root/'evaluation/reserve_mcts_stage_teams.py'),
            'reservation_timing':'After some Stage1/Stage2 screening outcomes existed, before final cumulative comparison and later policy tuning; construction uses the earlier fixed role-substitution lists and a fixed seed, without outcome-dependent team selection.',
            'holdout_limit':'Not an independent external set holdout. Familiar component sets/species overlap with previous games, and handmade team quality is unmeasured. Exact six-species rosters are distinct from prior reservations and stand-in originals. No team paste is used for prior fitting.',
            'rules':'validated with pinned local Gen9OU TeamValidator'}})
    return len(texts)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    print(json.dumps({'reserved_teams':reserve(args.root,args.output),'root':str(args.output)}))


if __name__=='__main__': main()
