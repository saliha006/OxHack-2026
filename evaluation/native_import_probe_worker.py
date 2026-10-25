"""Importable spawn target for one-shot provenance evidence; contains no battle policy."""
import hashlib
import os
from pathlib import Path
import sys


def recorded_worker(connection,priors):
    import decision.search
    import decision.belief
    import decision.adapter
    import decision.state
    import poke_engine
    names=('decision.search','decision.belief','decision.adapter','decision.state')
    files={name:str(Path(sys.modules[name].__file__).resolve()) for name in names}
    binaries={str(path.resolve()):hashlib.sha256(path.read_bytes()).hexdigest()
              for path in Path(poke_engine.__file__).parent.glob('*.so')}
    connection.send({'kind':'native_import_provenance','pid':os.getpid(),'parent_pid':os.getppid(),
        'pipeline_files':files,
        'pipeline_sha256':{name:hashlib.sha256(Path(path).read_bytes()).hexdigest() for name,path in files.items()},
        'poke_engine_package':str(Path(poke_engine.__file__).resolve()),'native_binaries':binaries,
        'loaded_native_extensions':{name:str(Path(module.__file__).resolve()) for name,module in list(sys.modules.items())
            if name.startswith('poke_engine') and getattr(module,'__file__','').endswith('.so')},
        'delegation':'Calls the selected snapshot decision.search._worker unchanged after recording imports.'})
    decision.search._worker(connection,priors)
