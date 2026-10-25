"""Chronological public replay evidence with explicit timing and uncertainty.

No guessed EVs, unused moves, unactivated items, or private requests are labels.
Includes current-state item changes separately from native-set evidence.
"""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import bot.parser as public_parser
from bot.parser import Parser, parse_tags, to_id

REVEAL_LINES = {'move','-item','-enditem','-ability','-terastallize','-damage','-heal','-status',
                '-activate','-start','detailschange','-formechange','replace','switch','drag','-transform'}
ITEM_CHANGES = {'trick','switcheroo','bestow','thief','covet'}
ABILITY_CHANGES = {'skillswap','roleplay','entrainment','simplebeam','worryseed','doodle'}


def file_sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def extract(log, battle_id, *, started_at=None, split=None, include_state=False):
    parser = Parser('p1')
    log_hash = hashlib.sha256(log.encode()).hexdigest()
    seen, transformed, altered_items, altered_abilities, illusion_sides = set(), set(), set(), set(), set()
    copied_slots = {}
    for offset, line in enumerate(log.splitlines()):
        parts = line.split('|')
        if len(parts) < 2:
            continue
        kind, args = parts[1], parts[2:]
        if kind == 'poke' and len(args)>1 and to_id(args[1].split(',')[0]).startswith(('zoroark','zorua')):
            illusion_sides.add(args[0])  # conservative: public identities on this side may be disguised
        if kind not in REVEAL_LINES:
            parser.feed(line)
            continue
        before = parser.snapshot()
        owners = {}
        for side, state in before['sides'].items():
            active = state.get('active')
            if active is not None:
                owners[side] = (side, active)
        if kind == 'move' and len(args)>1:
            move = to_id(args[1])
            if move in ('mimic','sketch') and args[0][:2] in owners:
                copied_slots[owners[args[0][:2]]] = (move, offset)
            if move in ITEM_CHANGES:
                altered_items.update(owners.values())  # before the exchange messages; failed exchanges are conservatively censored
            if move in ABILITY_CHANGES:
                altered_abilities.update(owners.values())
        # Retain lifetime censoring after Transform: this parser keeps observed
        # copied move/ability history after switching, so it is not a clean
        # original-set conditioning state even once the transformation ends.
        if kind == '-transform' and args:
            transformed.add(owners.get(args[0][:2]))
        parser.feed(line)
        after = parser.snapshot()
        observations = []
        if kind == '-enditem' and len(args)>1:
            owner = parser.mon(args[0])
            observations.append((owner, 'item', to_id(args[1]), 'held_before_loss', 'explicit_enditem'))
            observations.append((owner, 'current_item', '', 'current', 'explicit_enditem'))
        for side, state in after['sides'].items():
            for slot, mon in enumerate(state['pokemon']):
                old_team = before['sides'][side]['pokemon']
                old = old_team[slot] if slot < len(old_team) else {}
                owner = (side,slot)
                for move in mon.get('revealed_moves', []):
                    if move not in old.get('revealed_moves', []):
                        observations.append((owner, 'move', move, 'native_set', 'observed_native_move'))
                for field in ('item','ability','tera_type'):
                    if mon.get(field) and mon[field] != old.get(field):
                        observations.append((owner, field, mon[field], 'current', 'public_protocol_reveal'))
        for (side, slot), field, value, scope, provenance in observations:
            mon = after['sides'][side]['pokemon'][slot]
            native = field != 'current_item' and (side,slot) not in transformed and side not in illusion_sides
            reason = None
            if (side,slot) in transformed:
                reason = 'transformed_identity'
            if side in illusion_sides:
                reason = 'possible_illusion_identity; side excluded conservatively'
            # The public parser retains move history through switching. Censor subsequent
            # original-set labels for this owner rather than condition on a copied slot.
            if (side,slot) in copied_slots and copied_slots[(side,slot)][1] < offset:
                native, reason = False, 'move_slot_may_have_been_copied'
            if field == 'item' and (side,slot) in altered_items:
                native, reason = False, 'item_may_have_been_transferred'
            tags = parse_tags(args[2:])
            cause = tags.get('from', '')
            if field == 'item' and cause and any(word in to_id(cause) for word in ('trick','switcheroo','pickpocket','magician','symbiosis','harvest','recycle','pickup','bestow','thief','covet')):
                altered_items.add((side,slot))
                native, reason = False, 'item_acquisition_or_restoration'
            if field == 'ability' and ((side,slot) in altered_abilities or cause):
                native, reason = False, 'ability_may_have_changed_or_been_copied'
            ident = (side,slot,field,value,native)
            if native and ident in seen:
                continue
            seen.add(ident)
            row = {'battle_id':battle_id, 'started_at':started_at, 'split':split,
                   'side':side,'slot':slot,'species':mon['species'], 'field':field,'value':value,
                   'turn':after['turn'],'event_offset':offset,'provenance':provenance,
                   'scope':scope,'native_set_evidence':native,'exclusion_reason':reason,
                   'log_sha256':log_hash}
            if include_state:
                row['before'] = before
            yield row


def export_jsonl(input_path, output):
    if output.exists():
        raise FileExistsError('output exists')
    output.parent.mkdir(parents=True,exist_ok=True)
    part = output.with_name(output.name+'.part')
    counts, battles = Counter(), set()
    try:
        with input_path.open() as source, part.open('x') as sink:
            for line in source:
                battle=json.loads(line)
                ident=(battle['battle_id'],battle.get('started_at'))
                if ident in battles:
                    raise ValueError('duplicate battle; logs and turns are not independent samples')
                battles.add(ident)
                for record in extract(battle['log'], battle['battle_id'],started_at=battle.get('started_at'),split=battle.get('split')):
                    sink.write(json.dumps(record)+'\n')
                    counts[record['field']]+=1
                    counts['native_set_evidence']+=record['native_set_evidence']
        part.rename(output)
    except BaseException:
        part.unlink(missing_ok=True)
        raise
    report = {'battles':len(battles),'counts':dict(counts),'input_sha256':file_sha256(input_path),
              'extractor_sha256':file_sha256(__file__), 'public_parser_sha256':file_sha256(public_parser.__file__),
              'output_sha256':file_sha256(output)}
    output.with_suffix('.manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--logs',required=True,type=Path,help='JSONL with battle_id, started_at, split and log')
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    print(json.dumps(export_jsonl(args.logs,args.output),indent=2))


if __name__=='__main__': main()
