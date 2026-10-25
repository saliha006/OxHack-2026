"""Bounded read-only replay sample, joined on ID and timestamp. Never a full-table export."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from data.tiger import connect


def sample(env_file, output, per_split=100, seed='coherent-v1', exclude_logs=None):
    if output.exists() or not 1 <= per_split <= 1000:
        raise ValueError('fresh output required and per-split limit must be 1..1000')
    output.parent.mkdir(parents=True, exist_ok=True)
    excluded = set()
    if exclude_logs is not None:
        with Path(exclude_logs).open() as source:
            excluded = {(row['battle_id'],row['started_at']) for row in map(json.loads,source)}
    part = output.with_name(output.name+'.part')
    selected, missing, hashes = [], [], []
    created = False
    try:
        with connect(env_file, timeout_ms=120000) as conn, conn.cursor() as cur, part.open('x') as sink:
            created = True
            for split in ('train','test'):
                cur.execute('''SELECT battle_id, started_at FROM public.turns WHERE turn=1 AND split=%s
                    ORDER BY md5(battle_id || started_at::text || %s), battle_id, started_at LIMIT %s''',
                    (split,seed,per_split+len(excluded)))
                keys=[key for key in cur.fetchall() if (key[0],key[1].isoformat()) not in excluded][:per_split]
                for battle_id,started_at in keys:
                    cur.execute('''SELECT l.log,b.p1,b.p2,b.p1_team,b.p2_team FROM public.battle_logs l
                     JOIN public.battles b ON b.id=l.id AND b.started_at=l.started_at
                     WHERE l.id=%s AND l.started_at=%s''',(battle_id,started_at))
                    row=cur.fetchone()
                    key={'battle_id':battle_id,'started_at':started_at.isoformat(),'split':split}
                    if row is None:
                        missing.append(key)
                        continue
                    log,p1,p2,team1,team2=row
                    digest=hashlib.sha256(log.encode()).hexdigest()
                    sink.write(json.dumps(key | {'log':log,'log_sha256':digest,'p1':p1,'p2':p2,
                                                'p1_team':team1,'p2_team':team2})+'\n')
                    selected.append(key | {'log_sha256':digest})
            conn.rollback()
        part.rename(output)
    except BaseException:
        if created:
            part.unlink(missing_ok=True)
        raise
    manifest={'source':'Tiger turns/battle_logs/battles','source_label':'public_ladder','human_status':'unverified',
              'read_only':True,'sample_seed':seed,'per_split_limit':per_split,'selected':selected,'missing':missing,
              'input_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
              'selected_at':datetime.now(timezone.utc).isoformat(),'selection':'MD5 of battle ID/timestamp/seed; whole battles',
              'team_identity':'preview_roster_proxy','labels':'public revelations only, no exact hidden sets'}
    if exclude_logs is not None:
        manifest['excluded_battles']=len(excluded)
        with Path(exclude_logs).open('rb') as source:
            manifest['exclusion_file_sha256']=hashlib.file_digest(source,'sha256').hexdigest()
    output.with_suffix('.manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--per-split',type=int,default=100)
    parser.add_argument('--seed',default='coherent-v1')
    parser.add_argument('--exclude-logs',type=Path,help='exclude battle identities already used; no outcome labels inspected')
    args=parser.parse_args()
    try:
        result=sample(args.env_file,args.output,args.per_split,args.seed,args.exclude_logs)
    except Exception as exc:
        # Never print database error text: it can contain connection secrets.
        print(json.dumps({'error_type':type(exc).__name__,'sqlstate':getattr(exc,'sqlstate',None)}))
        raise SystemExit(1)
    print(json.dumps({'battles':len(result['selected']),'missing':len(result['missing']),'input_sha256':result['input_sha256']}))


if __name__=='__main__': main()
