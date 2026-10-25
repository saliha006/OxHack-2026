"""Stock poke-engine MCTS in one persistent, replaceable worker process.

Only ordinary Python records cross the pipe. Native preparation, belief replay
and search all run in the child; the caller owns the wall-clock deadline.
"""
import multiprocessing as mp
import time
from dataclasses import asdict, dataclass
from importlib.metadata import version
from random import Random
from queue import Empty, Queue
from threading import Event, Thread


@dataclass(frozen=True)
class RootVisit:
    choice: str
    visits: int
    total_score: float


@dataclass
class WorldResult:
    index: int
    our_visits: list[dict]
    opponent_visits: list[dict]
    total_visits: int = 0
    elapsed_ms: float = 0.0
    preparation_ms: float = 0.0
    error: dict | None = None


def failure(exc: BaseException, stage: str) -> dict:
    return {"stage": stage, "type": type(exc).__name__, "message": str(exc)}


def search_state(state, *, index: int = 0, duration_ms: int = 150, threads: int = 1) -> dict:
    """Convert the installed binding's native result, including PyO3 panics.

    OS-level aborts/segfaults cannot be caught here; SearchWorker contains those
    by detecting child exit and retaining previously streamed results.
    """
    from poke_engine import monte_carlo_tree_search

    start = time.monotonic()
    result = WorldResult(index, [], [])
    try:
        native = monte_carlo_tree_search(state, duration_ms=duration_ms, threads=threads)
        result.our_visits = [asdict(RootVisit(r.move_choice, int(r.visits), float(r.total_score)))
                            for r in native.side_one]
        result.opponent_visits = [asdict(RootVisit(r.move_choice, int(r.visits), float(r.total_score)))
                                 for r in native.side_two]
        result.total_visits = int(native.total_visits)
    except BaseException as exc:  # PanicException inherits BaseException, not Exception.
        result.error = failure(exc, "native_search")
    result.elapsed_ms = (time.monotonic() - start) * 1000
    return asdict(result)


def _worker(connection, priors: dict) -> None:
    from decision.actions import Action
    from decision.adapter import build_state, adapter_diagnostics
    from decision.belief import Belief

    belief = None
    rng = None
    try:
        while True:
            job = connection.recv()
            if job["kind"] == "close":
                return
            if job["kind"] == "invalidate":
                if belief is not None:
                    belief.last_request = belief.last_choice = None
                continue
            if job["kind"] == "chosen":
                if belief is not None:
                    belief.chose(job["request"], Action(**job["action"]))
                continue
            config = job["config"]
            request, battle = job["request"], job["battle"]
            preparation_start = time.monotonic()
            try:
                recovery_start = len(belief.recovery_events) if belief is not None else 0
                if belief is None:
                    belief = Belief(priors, battle)
                    recovery_start = 0
                if rng is None:
                    rng = Random(config["seed"])
                if config["frozen_beliefs"]:
                    # Preserve exactly the same hard revelations and accumulated item rules;
                    # this ablation disables only noisy damage/speed likelihood updates.
                    belief.last_request = belief.last_choice = None
                belief.update(battle)
                worlds = belief.sample_worlds(config["mcts_worlds"], rng,
                                              active_only=config["sampling"] == "active")
                connection.send({"kind": "prepared", "state_preparation_ms":
                                 (time.monotonic() - preparation_start) * 1000,
                                 "sampled_worlds": belief.last_sampled_worlds,
                                 "belief_candidates": belief.candidate_records(),
                                 "recovery_events": belief.recovery_events[recovery_start:],
                                 "state_approximations": adapter_diagnostics(request, battle),
                                 "engine_version": version("poke-engine")})
            except BaseException as exc:
                connection.send({"kind": "failure", "error": failure(exc, "preparation")})
                connection.send({"kind": "done", "scheduled_worlds": 0})
                continue
            scheduled = 0
            for index, sets in enumerate(worlds):
                if time.monotonic() + config["search_ms"] / 1000 > job["deadline"]:
                    break
                scheduled += 1
                connection.send({"kind": "world_started", "index": index})
                prepare = time.monotonic()
                try:
                    state = build_state(request, battle, sets)
                    preparation_ms = (time.monotonic() - prepare) * 1000
                    remaining = int((job["deadline"] - time.monotonic()) * 1000)
                    if remaining <= 0:
                        result = asdict(WorldResult(index, [], [], preparation_ms=preparation_ms,
                                                    error={"stage": "state_conversion", "type": "deadline",
                                                           "message": "deadline exhausted preparing world"}))
                    else:
                        result = search_state(state, index=index, duration_ms=min(config["search_ms"], remaining),
                                              threads=config["engine_threads"])
                        result["preparation_ms"] = preparation_ms
                except BaseException as exc:
                    result = asdict(WorldResult(index, [], [], preparation_ms=(time.monotonic() - prepare) * 1000,
                                                error=failure(exc, "state_conversion")))
                connection.send({"kind": "world", "result": result})
            connection.send({"kind": "done", "scheduled_worlds": scheduled})
    except (EOFError, BrokenPipeError):
        pass
    finally:
        connection.close()


def _entry(connection, target):
    """Keep the large prior payload out of Process.start's synchronous spawn pipe.

    A child stalled importing the caller's main module must not block its parent
    while that parent writes megabytes of priors into the spawn bootstrap pipe.
    The small bootstrap returns first; readiness is polled under the deadline.
    """
    try:
        connection.send({"kind": "ready"})
        initial = connection.recv()
        target(connection, initial["priors"])
    except (EOFError, BrokenPipeError):
        pass
    finally:
        connection.close()


class SearchWorker:
    """Sequential worlds, streamed immediately; deadlines kill and replace a stall.

    A new worker necessarily loses soft evidence accumulated inside its previous
    process. The next snapshot restores confirmed revelations; the trace records
    the restart rather than pretending that history was retained.
    """

    def __init__(self, priors: dict, *, target=_worker, context: str = "spawn"):
        self.priors, self.target = priors, target
        self.context = mp.get_context(context)
        self.process = None
        self.connection = None
        self.generation = 0
        self.initialised = False
        self.inbox = None
        self.receiver = None

    def _start(self):
        parent, child = self.context.Pipe()
        self.process = self.context.Process(target=_entry, args=(child, self.target), daemon=True)
        try:
            self.process.start()
        except BaseException:
            parent.close()
            child.close()
            self.process = None
            raise
        child.close()
        self.connection = parent
        self.generation += 1
        self.initialised = False
        inbox = Queue()
        self.inbox = inbox

        def receive():
            # These locals isolate generations: an old receiver can never deliver into a replacement worker's queue.
            while True:
                try:
                    message = parent.recv()
                except BaseException as exc:
                    inbox.put(("error", exc.with_traceback(None)))
                    return
                inbox.put(("message", message))

        self.receiver = Thread(target=receive, name="mcts-worker-receive", daemon=True)
        try:
            self.receiver.start()
        except BaseException:
            self.receiver = None
            self.close()
            raise

    def _send_before(self, message: dict, deadline: float) -> None:
        """Bound pipe writes as well as reads: a ready child may stop receiving immediately afterward."""
        if time.monotonic() >= deadline:
            self.close()
            raise TimeoutError("deadline expired before sending worker message")
        connection = self.connection  # restarting the worker must never redirect an outstanding sender
        finished = Event()
        errors = []

        def send():
            try:
                connection.send(message)
            except BaseException as exc:
                # A failed multiprocessing pickle/send traceback can retain an exported BytesIO buffer across
                # worker teardown. Preserve the exception record without keeping those transport frames alive.
                errors.append(exc.with_traceback(None))
            finally:
                finished.set()

        sender = Thread(target=send, name="mcts-worker-send", daemon=True)
        sender.start()
        while not finished.is_set():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                # Terminating the receiving process closes its pipe end and releases a blocked writer.
                self.close()
                sender.join(timeout=0.025)
                raise TimeoutError("worker message send exceeded decision search deadline")
            finished.wait(min(remaining, 0.02))
        if errors:
            self.close()
            raise errors[0]
        if time.monotonic() >= deadline:
            self.close()
            raise TimeoutError("deadline expired while sending worker message")

    def stream(self, request: dict, battle: dict, config: dict, deadline: float):
        if time.monotonic() >= deadline:
            yield {"kind": "failure", "error": {"stage": "worker", "type": "deadline",
                                                "message": "no time remaining before preparation"}}
            return
        stage = "worker_start"
        try:
            if self.process is None or not self.process.is_alive():
                self.close()
                self._start()
            stage = "worker_exit"
            if self.initialised:
                self._send_before({"kind": "search", "request": request, "battle": battle,
                                   "config": config, "deadline": deadline}, deadline)
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    yield {"kind": "failure", "error": {"stage": "worker", "type": "deadline",
                                                        "message": "worker exceeded decision search deadline"}}
                    self.close()
                    return
                try:
                    event, payload = self.inbox.get(timeout=min(remaining, 0.02))
                except Empty:
                    continue
                if event == "error":
                    # EOF is queued after every fully received result. Drain that order rather than racing
                    # process.is_alive(), which can discard a final world already waiting in the pipe.
                    raise payload
                message = payload
                if message["kind"] == "ready":
                    self._send_before({"priors": self.priors}, deadline)
                    self.initialised = True
                    self._send_before({"kind": "search", "request": request, "battle": battle,
                                       "config": config, "deadline": deadline}, deadline)
                    continue
                yield message
                if message["kind"] == "done":
                    return
        except TimeoutError as exc:
            yield {"kind": "failure", "error": {"stage": "worker", "type": "deadline", "message": str(exc)}}
            self.close()
        except (EOFError, BrokenPipeError, OSError) as exc:
            yield {"kind": "failure", "error": failure(exc, stage)}
            self.close()

    def chose(self, request: dict, action) -> None:
        if self.connection is not None and self.process is not None and self.process.is_alive():
            try:
                self.connection.send({"kind": "chosen", "request": request, "action": asdict(action)})
            except (BrokenPipeError, OSError):
                self.close()

    def invalidate_choice(self) -> None:
        if self.connection is not None and self.process is not None and self.process.is_alive():
            try:
                self.connection.send({"kind": "invalidate"})
            except (BrokenPipeError, OSError):
                self.close()

    def close(self) -> None:
        if self.process is not None and self.process.pid is not None:
            if self.process.is_alive():
                self.process.terminate()
            self.process.join(timeout=0.025)
            if self.process.is_alive():
                self.process.kill()
                self.process.join(timeout=0.025)
        if self.connection is not None:
            self.connection.close()
        if self.receiver is not None:
            self.receiver.join(timeout=0.025)
        self.process = self.connection = None
        self.receiver = self.inbox = None
        self.initialised = False
