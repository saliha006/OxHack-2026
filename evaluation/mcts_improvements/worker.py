"""Run one snapshot's complete parser/session/agent; stdin never contains the other private team.

Executed by absolute path, not imported through the candidate's package. The snapshot is the
first and only project source root in sys.path; immutable hashes are checked before import.
"""
import json
import os
from pathlib import Path
import resource
import sys
import time

# This helper has no runtime dependencies on the project being measured.
sys.path.insert(0, str(Path(__file__).parent))
from identity import source_identity, engine_identity, file_hash


def send(value):
    print(json.dumps(value), flush=True)


def main():
    initial = json.loads(sys.stdin.readline())
    root = Path(initial['root']).resolve()
    expected = initial['source_sha256']
    identity = source_identity(root)
    if identity['source_sha256'] != expected:
        raise RuntimeError('snapshot source differs from frozen manifest')
    sys.path = [str(root)] + [p for p in sys.path if p and Path(p).resolve() != Path(__file__).parents[2]]
    os.chdir(root)
    from bot.player import BattleSession
    from decision.agent import Agent
    import bot.parser
    import decision.belief
    import decision.adapter
    import decision.state
    import decision.search
    loaded = {name: str(Path(module.__file__).resolve()) for name,module in list(sys.modules.items())
              if name.startswith(('bot.', 'decision.', 'contracts.')) and getattr(module,'__file__',None)}
    if any(not Path(path).is_relative_to(root) for path in loaded.values()):
        raise RuntimeError('source imports escaped isolated snapshot')
    priors_path = Path(initial['priors'])
    if file_hash(priors_path) != initial['priors_sha256']:
        raise RuntimeError('prior changed after manifest freeze')
    priors = json.loads(priors_path.read_text())
    runs = Path(initial['runs'])
    runs.mkdir(parents=True, exist_ok=True)
    agent = Agent(priors, **initial['config'])
    session = BattleSession(initial['tag'], agent, runs)
    side = initial['side']
    latest_request = None
    rqid = 0
    started = time.monotonic()
    send({'kind':'ready', 'source_sha256':identity['source_sha256'], 'loaded_modules':loaded,
          'engine':engine_identity(), 'config':agent.config, 'priors_sha256':file_hash(priors_path)})
    for encoded in sys.stdin:
        command = json.loads(encoded)
        if command['op'] == 'close':
            summary = session.close(command.get('won'), command.get('turns', 0))
            own = resource.getrusage(resource.RUSAGE_SELF)
            children = resource.getrusage(resource.RUSAGE_CHILDREN)
            summary.update(cpu_seconds=own.ru_utime + own.ru_stime + children.ru_utime + children.ru_stime,
                           process_wall_seconds=time.monotonic() - started)
            send({'kind':'closed', 'summary':summary})
            return
        choices = []
        for line in command['text'].splitlines():
            if not line:
                continue
            session.feed(line)
            if line.startswith('|request|'):
                latest_request = json.loads(line[len('|request|'):])
                rqid += 1
                latest_request['rqid'] = rqid
                choice = session.decide(latest_request, side)
                if choice is not None:
                    choices.append(choice)
            elif line.startswith('|error|') and latest_request is not None:
                # Simulator streams emit errors without a second request; keep the exact rqid for retry tracking.
                choices.append(session.decide(latest_request, side))
        send({'kind':'fed', 'choices':choices})


if __name__ == '__main__':
    main()
