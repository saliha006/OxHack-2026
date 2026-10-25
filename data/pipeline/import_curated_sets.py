"""Import coherent OU role templates and build an explicit mixture with usage priors.

Offline only. The artifact has the existing SetCandidates shape; selecting its
path is the opt-in switch. No automatic changes to live bot defaults.
"""
import argparse
import copy
import hashlib
import json
import math
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from itertools import product
from pathlib import Path

from data.pipeline.build_set_candidates import MOVES, forme_aliases, to_id
from decision.sets import NATURES, STAT_ORDER
from decision.state import DEX

URL = 'https://play.pokemonshowdown.com/data/sets/gen9ou.json'
NEUTRAL = {'hardy', 'docile', 'serious', 'bashful', 'quirky'}


def key(candidate):
    """Complete-set identity, not preview-roster identity; move order is irrelevant."""
    return json.dumps([sorted(candidate['moves']), candidate['item'], candidate['ability'], candidate['tera_type'],
                       candidate['spread'], candidate.get('ivs', [31]*6)], sort_keys=True)


def choices(value):
    return value if isinstance(value, list) else [value]


def vector(value, default, maximum):
    if not isinstance(value, dict) or set(value)-set(STAT_ORDER):
        raise ValueError('invalid stat keys')
    result = [value.get(s, default) for s in STAT_ORDER]
    if any(type(v) is not int or not 0 <= v <= maximum for v in result):
        raise ValueError('invalid stat value')
    return result


def import_bank(document, priors):
    records, rejected = [], []
    for section in ('dex', 'stats'):
        for species_name, roles in document.get(section, {}).items():
            species = to_id(species_name)
            for role, template in roles.items():
                try:
                    if species not in DEX:
                        raise ValueError('unknown species/forme')
                    evs = vector(template.get('evs', {}), 0, 252)
                    ivs = vector(template.get('ivs', {}), 31, 31)
                    if sum(evs) > 510:
                        raise ValueError('EV sum exceeds 510')
                    slots = template['moves']
                    if not 1 <= len(slots) <= 4:
                        raise ValueError('requires one to four move slots')
                    missing_tera = not any(k in template for k in ('teraType', 'teratypes'))
                    if missing_tera:
                        teras = list(priors['species'].get(species, {}).get('usage', {}).get('tera_types', {}))
                        if not teras:
                            raise ValueError('no Tera fallback for incomplete template')
                    else:
                        teras = choices(template.get('teraType', template.get('teratypes')))
                    axes = [*[choices(m) for m in slots], choices(template['item']),
                            choices(template['ability']), choices(template['nature']), teras]
                    if math.prod(map(len, axes)) > 2048:
                        raise ValueError('too many alternatives; avoid silent truncation')
                    valid = []
                    for variant in product(*axes):
                        *moves, item, ability, nature, tera = map(to_id, variant)
                        if len(set(moves)) != len(moves):
                            continue
                        if set(moves)-set(MOVES):
                            raise ValueError('move missing from pinned native move snapshot')
                        if nature not in set(NATURES) | NEUTRAL:
                            raise ValueError('unknown nature')
                        candidate = dict(weight=1., moves=moves, item='' if item in ('nothing','none') else item,
                                         ability=ability, tera_type=tera, spread={'nature': nature, 'evs': evs}, ivs=ivs)
                        valid.append(candidate)
                    valid = list({key(candidate): candidate for candidate in valid}.values())
                    if not valid:
                        raise ValueError('no valid variants')
                    for i, candidate in enumerate(valid):
                        ident = hashlib.sha256((section+'\0'+species+'\0'+role+'\0'+key(candidate)).encode()).hexdigest()[:20]
                        records.append({'id': ident, 'species': species, 'section': section, 'role': role,
                            'variant': i, 'variant_weight': 1/len(valid), 'candidate': candidate,
                            'unknown_in_source': ['tera_type'] if missing_tera else [],
                            'completion': 'usage Tera choices, equal variant mass; not observed' if missing_tera else None,
                            'iv_convention': 'unspecified stats default 31; source convention, not opponent observation'})
                except (KeyError, TypeError, ValueError) as exc:
                    rejected.append({'species': species, 'section': section, 'role': role, 'reason': str(exc)})
    return {'schema': 1, 'records': records, 'rejected': rejected,
            'weighting': 'equal role mass; equal alternative mass within role; not measured joint frequencies'}


def validate(bank, simulator):
    validator = Path(__file__).with_name('validate_curated.cjs')
    result = subprocess.run(['node', str(validator), str(Path(simulator).resolve())],
                            input=json.dumps(bank['records']), text=True, capture_output=True, timeout=120, check=True)
    errors = {r['id']: r['errors'] for r in json.loads(result.stdout) if r['errors']}
    kept = []
    for record in bank['records']:
        if record['id'] in errors:
            bank['rejected'].append({k: record[k] for k in ('id','species','role','section')} | {'reason': errors[record['id']]})
        else:
            kept.append(record)
    bank['records'] = kept
    bank['validation'] = {'format': 'gen9ou', 'simulator_root': str(Path(simulator).resolve()),
        'simulator_commit': subprocess.check_output(['git','-C',str(simulator),'rev-parse','HEAD'], text=True).strip(),
        'validator_sha256': hashlib.sha256(validator.read_bytes()).hexdigest(), 'invalid_variants': len(errors)}


def mix(priors, bank, fraction=.5, *, role_weights=None, species_fractions=None):
    if not 0 <= fraction < 1:
        raise ValueError('curated fraction must be in [0,1); retain a nonzero broad fallback')
    if fraction == 0:
        return copy.deepcopy(priors), {}
    output = copy.deepcopy(priors)
    grouped, provenance = defaultdict(list), {}
    for record in bank['records']:
        grouped[record['species']].append(record)
    for species, records in grouped.items():
        if species not in priors['species']:
            continue  # broad fallback is mandatory; report bank-only species separately
        local_fraction = (species_fractions or {}).get(species, fraction)
        if not math.isfinite(local_fraction) or not 0 <= local_fraction <= fraction:
            raise ValueError('species fraction must be finite and no larger than the global cap')
        if local_fraction == 0:
            continue
        # Prefer curated dex roles; stats are supplemental only where dex has no role.
        section = 'dex' if any(r['section']=='dex' for r in records) else 'stats'
        records = [r for r in records if r['section']==section]
        roles = defaultdict(list)
        for record in records:
            roles[record['role']].append(record)
        # Repeated named copies of the same role distribution are not independent evidence.
        distinct_roles = {}
        for role_records in roles.values():
            total = sum(r['variant_weight'] for r in role_records)
            signature = tuple(sorted((key(r['candidate']), round(r['variant_weight']/total, 14))
                                     for r in role_records))
            distinct_roles.setdefault(signature, role_records)
        curated = defaultdict(float)
        variants, origins = {}, defaultdict(list)
        role_mass = {signature: (role_weights or {}).get(species, {}).get(records[0]['role'], 1.)
                     for signature, records in distinct_roles.items()}
        if any(not math.isfinite(w) or w <= 0 for w in role_mass.values()):
            raise ValueError('role weights must be positive and finite')
        total_role_mass = sum(role_mass.values())
        for signature, role_records in distinct_roles.items():
            total = sum(r['variant_weight'] for r in role_records)
            for record in role_records:
                ident = key(record['candidate'])
                curated[ident] += record['variant_weight']/total*role_mass[signature]/total_role_mass
                variants[ident] = record['candidate']
                origins[ident].append(record['id'])
        weighted = defaultdict(float)
        old = priors['species'][species]['sets']
        old_mass = sum(c['weight'] for c in old)
        if not old_mass > 0 or not math.isfinite(old_mass):
            raise ValueError('invalid broad prior mass')
        for candidate in old:
            ident = key(candidate)
            variants.setdefault(ident, candidate)
            weighted[ident] += (1-local_fraction)*candidate['weight']/old_mass
        for ident, weight in curated.items():
            weighted[ident] += local_fraction*weight
        candidates = []
        details = []
        for ident, weight in sorted(weighted.items(), key=lambda item: (-item[1], item[0])):
            if weight <= 0:
                continue
            candidates.append(copy.deepcopy(variants[ident]) | {'weight': weight})
            details.append({'candidate_sha256': hashlib.sha256(ident.encode()).hexdigest(),
                            'curated_ids': origins.get(ident, []), 'weight': weight,
                            'curated_component_mass': local_fraction*curated.get(ident, 0)})
        output['species'][species]['sets'] = candidates
        provenance[species] = {'section': section, 'roles': len(distinct_roles), 'candidates': details}
        if species_fractions is not None:
            provenance[species]['effective_curated_fraction'] = local_fraction
    # The usage builder aliases in-battle forms; keep their augmented bank coherent too.
    for alias, base in forme_aliases(set(grouped)).items():
        if base in provenance and alias in output['species'] and alias not in provenance:
            output['species'][alias] = copy.deepcopy(output['species'][base])
            provenance[alias] = {'alias_of': base}
    return output, provenance


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--priors', type=Path, default=Path('data/set_candidates.json'))
    parser.add_argument('--simulator', required=True, type=Path)
    parser.add_argument('--fraction', type=float, default=.5)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args(argv)
    if args.output.exists():
        parser.error('output exists; preserve frozen artifacts and choose a fresh directory')
    source, priors_raw = args.source.read_bytes(), args.priors.read_bytes()
    priors = json.loads(priors_raw)
    bank = import_bank(json.loads(source), priors)
    validate(bank, args.simulator)
    mixed, provenance = mix(priors, bank, args.fraction)
    report = {'source_url': URL, 'source_file': str(args.source),
              'source_sha256': hashlib.sha256(source).hexdigest(), 'source_snapshot_date': '2026-10-25',
              'built_at': datetime.now(timezone.utc).isoformat(),
              'broad_prior_sha256': hashlib.sha256(priors_raw).hexdigest(), 'curated_fraction': args.fraction,
              'role_weights': bank['weighting'], 'valid_variants': len(bank['records']),
              'rejected': bank['rejected'], 'validation': bank['validation'], 'species': provenance,
              'bank_species_without_broad_fallback': sorted(set(r['species'] for r in bank['records'])-set(priors['species'])),
              'default_changed': False, 'claim': 'candidate prior experiment; no learned joint-team model'}
    args.output.mkdir(parents=True)
    for name, value in [('bank.json', bank), ('priors.json', mixed), ('manifest.json', report)]:
        (args.output/name).write_text(json.dumps(value, indent=1)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('species','validation')}, indent=2))


if __name__ == '__main__': main()
