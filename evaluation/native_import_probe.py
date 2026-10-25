"""Verify actual spawned native-worker imports without changing any frozen source.

This is an integrity probe: one 20 ms requested native world on a development
position. It is not a playing-strength or latency benchmark.
"""
import argparse
import json
from pathlib import Path
import sys
import time

HERE=Path(__file__).parent.resolve()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',required=True,type=Path)
    parser.add_argument('--priors',required=True,type=Path)
    parser.add_argument('--position',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--belief-mode',choices=('legacy','reliable'),default='legacy')
    args=parser.parse_args()
    root=args.root.resolve()
    live=HERE.parent
    sys.path=[str(root),str(HERE)]+[path for path in sys.path if path and Path(path).resolve() not in (live,root,HERE)]
    from mcts_improvements.identity import source_identity,file_hash,engine_identity
    from native_import_probe_worker import recorded_worker
    from decision.search import SearchWorker
    identity=source_identity(root)
    priors=json.loads(args.priors.read_text())
    position=json.loads(args.position.read_text())
    config={'mcts_worlds':1,'search_ms':20,'engine_threads':1,'sampling':'team','frozen_beliefs':False,
            'seed':2026102599,'belief_mode':args.belief_mode}
    worker=SearchWorker(priors,target=recorded_worker)
    started=time.monotonic()
    try:
        messages=list(worker.stream(position['request'],position['battle'],config,started+3.0))
    finally:
        worker.close()
    record=next(message for message in messages if message['kind']=='native_import_provenance')
    expected_engine=engine_identity()
    assert all(Path(path).is_relative_to(root) for path in record['pipeline_files'].values())
    assert {Path(path).name:value for path,value in record['native_binaries'].items()}==expected_engine['binaries']
    worlds=[message['result'] for message in messages if message['kind']=='world']
    failures=[message for message in messages if message['kind']=='failure']
    assert len(worlds)==1 and not worlds[0].get('error') and not failures
    assert source_identity(root)['source_sha256']==identity['source_sha256']
    result={'purpose':'Actual spawned-native-worker import integrity only, no strength claim',
        'root':str(root),'source_sha256':identity['source_sha256'],
        'priors_sha256':file_hash(args.priors),'position_sha256':file_hash(args.position),
        'engine':expected_engine,'config':config,'actual_child_imports':record,
        'native_world':{key:worlds[0].get(key) for key in ('total_visits','elapsed_ms','preparation_ms','error')},
        'elapsed_probe_ms':(time.monotonic()-started)*1000,'verified':True,
        'probe_sources':{path.name:file_hash(path) for path in (Path(__file__),HERE/'native_import_probe_worker.py')}}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'root':str(root),'source_sha256':result['source_sha256'],'verified':True,'native_pid':record['pid'],'native_ms':worlds[0]['elapsed_ms']}))


if __name__=='__main__': main()
