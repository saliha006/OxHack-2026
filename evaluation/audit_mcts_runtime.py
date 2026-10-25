"""Incrementally inspect recorded decisions for reliability/deadline events during a run."""
import argparse
import json
from pathlib import Path


def audit(roots,cursor_file):
    cursor_file=Path(cursor_file)
    cursors=json.loads(cursor_file.read_text()) if cursor_file.exists() else {}
    events=[]
    for root in roots:
        for path in sorted(Path(root).glob('game-*/*/*.jsonl')):
            key=str(path.resolve())
            offset=cursors.get(key,0)
            if path.stat().st_size < offset: offset=0
            with path.open() as stream:
                stream.seek(offset)
                while True:
                    position=stream.tell()
                    line=stream.readline()
                    if not line or not line.endswith('\n'):
                        stream.seek(position)
                        break
                    row=json.loads(line)
                    if 'request' not in row and row.get('kind')!='retry': continue
                    causes=[]
                    if row.get('fallback') or row.get('fallback_reason'): causes.append('fallback')
                    if row.get('kind')=='retry': causes.append('rejected_choice')
                    if row.get('think_ms',0)>3000 or row.get('total_ms',0)>3000: causes.append('over_3000_ms')
                    if row.get('interrupted_worlds',0): causes.append('interrupted_world')
                    if row.get('failures'): causes.append('failure')
                    if row.get('mapping_failures'): causes.append('native_root_rejection')
                    if causes:
                        events.append({'trace':key,'decision_id':row.get('decision_id'),'turn':row.get('turn'),
                            'causes':causes,'fallback_reason':row.get('fallback_reason'),'failures':row.get('failures'),
                            'think_ms':row.get('think_ms'),'total_ms':row.get('total_ms'),
                            'native_root_rejections':len(row.get('mapping_failures',[])),
                            'native_tera_root_rejections':sum((failure.get('choice') or '').endswith('-tera') for failure in row.get('mapping_failures',[]))})
                cursors[key]=stream.tell()
    cursor_file.parent.mkdir(parents=True,exist_ok=True)
    cursor_file.write_text(json.dumps(cursors,indent=2)+'\n')
    return events


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runs',nargs='+',type=Path)
    parser.add_argument('--cursors',required=True,type=Path)
    parser.add_argument('--events',required=True,type=Path)
    args=parser.parse_args()
    events=audit(args.runs,args.cursors)
    args.events.parent.mkdir(parents=True,exist_ok=True)
    with args.events.open('a') as stream:
        for event in events: stream.write(json.dumps(event)+'\n')
    print(json.dumps({'new_events':events,'run_count':len(args.runs)}))


if __name__=='__main__': main()
