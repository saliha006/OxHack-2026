"""Reserve fresh synthetic roster combinations for a second coherent-prior study.

Component sets remain familiar regression data. Only roster combinations are new;
this is not an independent external competitive-team holdout. No reserved team
is imported into mixture fitting or used to choose the candidate revision.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from evaluation.mcts_improvements.reserve_teams import WEATHER_COMPONENTS, RATIONALES
from evaluation.mcts_improvements.run import validate_teams, write_json
from evaluation.mcts_match_schedule import four_game_schedule

ROSTERS = [
    ('offense', ['Darkrai','Gholdengo','Zamazenta','Tornadus-Therian','Great Tusk','Primarina']),
    ('offense', ['Weavile','Darkrai','Dragonite','Iron Crown','Great Tusk','Ogerpon-Wellspring']),
    ('offense', ['Lokix','Latios','Zamazenta','Gholdengo','Cinderace','Great Tusk']),
    ('sun offense', ['Torkoal','Walking Wake','Hydrapple','Iron Crown','Cinderace','Great Tusk']),
    ('balance', ['Ting-Lu','Skarmory','Darkrai','Primarina','Pecharunt','Great Tusk']),
    ('balance', ['Garganacl','Gliscor','Moltres','Gholdengo','Walking Wake','Alomomola']),
    ('balance', ['Tinkaton','Slowking-Galar','Hydrapple','Tornadus-Therian','Kyurem','Zamazenta']),
    ('rain offense', ['Pelipper','Barraskewda','Tornadus-Therian','Gholdengo','Iron Treads','Primarina']),
    ('semistall', ['Blissey','Dondozo','Corviknight','Gliscor','Toxapex','Darkrai']),
    ('semistall', ['Toxapex','Weezing-Galar','Iron Treads','Clefable','Tornadus-Therian','Weavile']),
]
SCHEDULE_SEED = 2026102521


def roster_key(roster):
    return tuple(sorted(roster))


def prior_reservations(roots):
    """Snapshot only explicit team-roster metadata, never scores or raw battle logs."""
    used, files = set(), []
    for root in roots:
        if not Path(root).exists():
            continue
        for path in sorted(Path(root).rglob('*.json')):
            try:
                encoded = path.read_bytes()
                data = json.loads(encoded)
            except (OSError, ValueError):
                continue  # another chat may be writing an unrelated progress artifact
            teams = data.get('teams') if isinstance(data, dict) else None
            if not isinstance(teams, list):
                continue
            rosters = [t['roster'] for t in teams if isinstance(t, dict) and t.get('roster')]
            if not rosters:
                continue
            used.update(roster_key(roster) for roster in rosters)
            files.append({'path':str(path.resolve()), 'sha256':hashlib.sha256(encoded).hexdigest(),
                          'rosters':len(rosters)})
    return used, files


def reserve(root, simulator, output, *, other_evaluation=None):
    root, simulator, output = Path(root).resolve(), Path(simulator).resolve(), Path(output).resolve()
    if output.exists():
        raise FileExistsError('reservation exists; never rewrite a frozen pool')
    roots = [root/'evaluation']
    if other_evaluation is not None:
        roots.append(Path(other_evaluation).resolve())
    used, exclusion_sources = prior_reservations(roots)
    components = {}
    for path in sorted((root/'bot/teams/standin').glob('*.txt')):
        old_roster = []
        for block in re.split(r'\n\s*\n', path.read_text().strip()):
            name = re.sub(r' \([MF]\)$', '', block.splitlines()[0].split(' @ ')[0].strip())
            components.setdefault(name, (block, path.relative_to(root).as_posix()))
            old_roster.append(name)
        used.add(roster_key(old_roster))
    components.update({name:(text,'existing hand-constructed weather component from evaluation/mcts_improvements/reserve_teams.py')
                       for name,text in WEATHER_COMPONENTS.items()})
    keys = [roster_key(roster) for _,roster in ROSTERS]
    if len(set(keys)) != 10 or any(len(set(roster))!=6 for _,roster in ROSTERS):
        raise ValueError('need ten distinct six-species rosters')
    overlap = set(keys)&used
    if overlap:
        raise ValueError(f'proposed roster already reserved: {sorted(overlap)}')
    texts = ['\n\n'.join(components[name][0] for name in roster).strip() for _,roster in ROSTERS]
    checked = validate_teams(simulator, texts)
    output.mkdir(parents=True)
    records = []
    for i,((style,roster),text,validation) in enumerate(zip(ROSTERS,texts,checked)):
        path=output/f'{i+1:02d}.txt'
        path.write_text(text+'\n')
        records.append({'id':f'coherent-v2-screening-{i+1:02d}', 'path':str(path), 'style':style,
                        'roster':roster, 'sha256':hashlib.sha256(text.encode()).hexdigest(),
                        'component_sources':[components[name][1] for name in roster],
                        'design_rationale':RATIONALES[style], 'validation_errors':validation['errors']})
    result = {'schema':1, 'reserved_at':datetime.now(timezone.utc).isoformat(), 'teams':records,
              'provenance':{'kind':'new synthetic roster combinations of known regression component sets',
                  'holdout_limit':'Not an independent external set holdout. Component sets are known, and overlap with source-wide usage cannot be excluded.',
                  'selection':'fixed before candidate selection and all v2 game outcomes; no outcome scores read by this planner',
                  'fit_rule':'Do not fit mixture weights, candidate rules, or priors from these reserved team files.',
                  'freshness':'disjoint from explicit rosters in the checked reservation snapshot; later reservations in the other chat are outside this snapshot',
                  'rules':'pinned local Gen9 OU TeamValidator'},
              'checked_prior_rosters':len(used), 'excluded_rosters':[list(key) for key in sorted(used)],
              'reservation_source_files':exclusion_sources,
              'schedule_design':{'games':60, 'seed':SCHEDULE_SEED,
                  'kind':'four-game blocks: both simulator sides and both bot/team assignments',
                  'equal_team_exposure':True, 'source_and_prior_manifest':'not frozen yet; requires selected candidate'},
              'schedule':four_game_schedule(10,60,SCHEDULE_SEED)}
    write_json(output/'teams.json', result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path('.'))
    parser.add_argument('--simulator',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--other-evaluation',type=Path)
    args=parser.parse_args()
    result=reserve(args.root,args.simulator,args.output,other_evaluation=args.other_evaluation)
    print(json.dumps({'teams':len(result['teams']), 'excluded_rosters':result['checked_prior_rosters'],
                      'validation_errors':sum(bool(t['validation_errors']) for t in result['teams']),
                      'schedule_games':len(result['schedule']), 'source_manifest_frozen':False}))


if __name__=='__main__': main()
