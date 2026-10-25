import copy
import os
import struct
import time

import pytest

from decision.actions import our_actions
from decision.agent import Agent
from decision.search import SearchWorker, search_state
from tests.test_belief import PRIORS
from tests.turn2 import EXAMPLE, REQUEST, SETS


def stalled(connection, priors):
    connection.recv()
    time.sleep(30)


def partial_then_stall(connection, priors):
    connection.recv()
    connection.send({"kind": "world", "result": {
        "index": 0, "our_visits": [{"choice": "ironhead", "visits": 25}],
        "opponent_visits": [], "elapsed_ms": 2, "total_visits": 25, "error": None}})
    time.sleep(30)


def crash(connection, priors):
    connection.recv()
    connection.send({"kind": "world_started", "index": 0})
    os._exit(23)


@pytest.mark.parametrize("target,partial", [(stalled, False), (partial_then_stall, True)])
def test_stalled_native_or_preparation_worker_cannot_hold_parent(target, partial):
    agent = Agent(PRIORS, backend="mcts", budget=0.6)
    agent.worker = SearchWorker(PRIORS, target=target)
    before = time.monotonic()
    try:
        choice = agent.choose(REQUEST, copy.deepcopy(EXAMPLE))
        assert time.monotonic() - before < 0.9
        assert choice in {a.to_choice() for a in our_actions(REQUEST)}
        assert agent.last_trace["failures"][0]["type"] == "deadline"
        assert agent.worker.process is None
        if partial:
            assert choice == "move 4"
            assert agent.last_trace["completed_worlds"] == agent.last_trace["usable_worlds"] == 1
            assert agent.last_trace["fallback_reason"] is None
        else:
            assert agent.last_trace["fallback_reason"] == "worker_failure"
    finally:
        agent.close()


def test_native_process_exit_returns_legal_fallback_and_restart_is_recorded():
    agent = Agent(PRIORS, backend="mcts", budget=0.6)
    agent.worker = SearchWorker(PRIORS, target=crash)
    try:
        for _ in range(2):
            assert agent.choose(REQUEST, copy.deepcopy(EXAMPLE)) == our_actions(REQUEST)[0].to_choice()
            assert agent.last_trace["failures"]
            assert agent.last_trace["scheduled_worlds"] == 1
            assert agent.last_trace["failed_worlds"] == agent.last_trace["interrupted_worlds"] == 1
        assert agent.last_trace["worker_generation"] == 2
        assert agent.last_trace["belief_history_reset"]
    finally:
        agent.close()


def test_native_result_maps_to_a_legal_choice_and_worker_is_reused():
    agent = Agent(PRIORS, backend="mcts", mcts_worlds=1, search_ms=20)
    try:
        first = agent.choose(REQUEST, copy.deepcopy(EXAMPLE))
        assert first in {a.to_choice() for a in our_actions(REQUEST)}
        assert agent.last_trace["usable_worlds"] == 1, agent.last_trace
        assert agent.last_trace["engine_version"] == "0.0.48"
        process_id = agent.worker.process.pid
        agent.choose(REQUEST, copy.deepcopy(EXAMPLE))
        assert agent.worker.process.pid == process_id
        assert agent.last_trace["worker_generation"] == 1
        assert agent.last_trace["search_support"]
    finally:
        agent.close()


def test_native_panic_exception_is_a_structured_failure(monkeypatch):
    class PanicException(BaseException):
        pass

    def panic(*args, **kwargs):
        raise PanicException("native test panic")

    monkeypatch.setattr("poke_engine.monte_carlo_tree_search", panic)
    result = search_state(None)
    assert result["error"] == {"stage": "native_search", "type": "PanicException", "message": "native test panic"}
    assert result["our_visits"] == []


def test_mcts_preview_uses_lead_without_starting_worker():
    from tests.test_agent import load
    agent = Agent(PRIORS, backend="mcts")
    assert agent.choose(load("team_preview_request"), copy.deepcopy(EXAMPLE)) == "team 123456"
    assert agent.worker is None


def test_every_native_root_switch_maps_correctly_on_forced_replacement():
    from tests.test_agent import load
    agent = Agent(PRIORS, backend="mcts", mcts_worlds=1, search_ms=20)
    request = load("force_switch_request")
    try:
        choice = agent.choose(request, copy.deepcopy(EXAMPLE))
        assert choice in {a.to_choice() for a in our_actions(request)}
        assert agent.last_trace["usable_worlds"] == 1, agent.last_trace
        assert not agent.last_trace["mapping_failures"], agent.last_trace
    finally:
        agent.close()


def result_then_second_world_stalls(connection, priors):
    connection.recv()
    connection.send({'kind': 'world_started', 'index': 0})
    connection.send({'kind': 'world', 'result': {
        'index': 0, 'our_visits': [{'choice': 'ironhead', 'visits': 25}],
        'opponent_visits': [], 'elapsed_ms': 2, 'total_visits': 25, 'error': None}})
    connection.send({'kind': 'world_started', 'index': 1})
    time.sleep(30)


def test_stalled_announced_world_is_failed_without_discarding_completed_world():
    agent = Agent(PRIORS, backend='mcts', budget=.6)
    agent.worker = SearchWorker(PRIORS, target=result_then_second_world_stalls)
    try:
        assert agent.choose(REQUEST, copy.deepcopy(EXAMPLE)) == 'move 4'
        trace = agent.last_trace
        assert trace['scheduled_worlds'] == 2
        assert trace['completed_worlds'] == trace['usable_worlds'] == 1
        assert trace['failed_worlds'] == trace['interrupted_worlds'] == 1
        assert trace['worlds'][-1]['error']['type'] == 'deadline'
        assert trace['fallback_reason'] is None
    finally:
        agent.close()


def persistent_result(connection, priors):
    while True:
        job = connection.recv()
        if job['kind'] == 'close':
            return
        if job['kind'] != 'search':
            continue
        connection.send({'kind': 'world', 'result': {
            'index': 0, 'our_visits': [{'choice': 'ironhead', 'visits': 25}],
            'opponent_visits': [], 'elapsed_ms': 2, 'total_visits': 25, 'error': None}})
        connection.send({'kind': 'done', 'scheduled_worlds': 1})


def test_history_reset_is_per_decision_and_cumulative_history_flag_stays_true():
    agent = Agent(PRIORS, backend='mcts', budget=.6)
    agent.worker = SearchWorker(PRIORS, target=persistent_result)
    try:
        agent.choose(REQUEST, copy.deepcopy(EXAMPLE))
        assert not agent.last_trace['belief_history_reset']
        agent.worker.close()  # replace a failed worker before the next request
        agent.choose(REQUEST, copy.deepcopy(EXAMPLE))
        assert agent.last_trace['belief_history_reset']
        assert agent.last_trace['belief_history_was_reset']
        agent.choose(REQUEST, copy.deepcopy(EXAMPLE))
        assert not agent.last_trace['belief_history_reset']
        assert agent.last_trace['belief_history_was_reset']
    finally:
        agent.close()


def bootstrap_never_ready(connection, target):
    time.sleep(30)


def bootstrap_ready_but_never_receives(connection, target):
    connection.send({'kind': 'ready'})
    time.sleep(30)


@pytest.mark.parametrize('entry', [bootstrap_never_ready, bootstrap_ready_but_never_receives])
def test_stalled_bootstrap_or_prior_pipe_write_is_deadline_bounded(monkeypatch, entry):
    import decision.search as module
    monkeypatch.setattr(module, '_entry', entry)
    # This exceeds the OS pipe buffer; a synchronous send would hang after the ready message.
    worker = SearchWorker({'large': 'x' * (4 * 1024 * 1024)})
    before = time.monotonic()
    try:
        messages = list(worker.stream(REQUEST, copy.deepcopy(EXAMPLE), {}, before + .6))
        assert time.monotonic() - before < .95
        assert messages[-1]['error']['type'] == 'deadline'
        assert worker.process is None and worker.connection is None
        assert not worker.initialised
    finally:
        worker.close()


def test_ready_consumed_after_cutoff_does_not_initialize_or_start_work(monkeypatch):
    import decision.search as module
    clock = [0.0]
    class Process:
        pid = 1
        alive = True
        def is_alive(self): return self.alive
        def terminate(self): self.alive = False
        def join(self, timeout=None): pass
    class Connection:
        sent = []
        closed = False
        def send(self, message): self.sent.append(message)
        def close(self): self.closed = True
    worker = SearchWorker(PRIORS)
    connection = Connection()
    class Inbox:
        def get(self, timeout):
            clock[0] = 11.0  # ready becomes visible only after the decision's cutoff
            return 'message', {'kind': 'ready'}
    worker.process, worker.connection, worker.inbox = Process(), connection, Inbox()
    monkeypatch.setattr(module.time, 'monotonic', lambda: clock[0])
    messages = list(worker.stream(REQUEST, copy.deepcopy(EXAMPLE), {}, 10.0))
    assert messages[-1]['error']['type'] == 'deadline'
    assert connection.sent == []
    assert connection.closed and worker.process is None and not worker.initialised


def target_never_receives_search(connection, priors):
    time.sleep(30)


def test_search_job_pipe_write_is_deadline_bounded_when_ready_child_stops_reading():
    worker = SearchWorker(PRIORS, target=target_never_receives_search)
    request = {**REQUEST, 'padding': 'x' * (4 * 1024 * 1024)}
    before = time.monotonic()
    try:
        messages = list(worker.stream(request, copy.deepcopy(EXAMPLE), {}, before + .6))
        assert time.monotonic() - before < .95
        assert messages[-1]['error']['type'] == 'deadline'
        assert worker.process is None and worker.connection is None
        assert not worker.initialised
    finally:
        worker.close()


def partial_frame_stall(connection, priors):
    connection.recv()
    # A valid Connection length header followed by an incomplete pickle payload makes recv() wait indefinitely.
    os.write(connection.fileno(), struct.pack('!i', 4096) + b'xx')
    time.sleep(30)


def result_then_partial_frame_stall(connection, priors):
    connection.recv()
    connection.send({'kind': 'world_started', 'index': 0})
    connection.send({'kind': 'world', 'result': {
        'index': 0, 'our_visits': [{'choice': 'ironhead', 'visits': 25}],
        'opponent_visits': [], 'elapsed_ms': 2, 'total_visits': 25, 'error': None}})
    connection.send({'kind': 'world_started', 'index': 1})
    os.write(connection.fileno(), struct.pack('!i', 4096) + b'xx')
    time.sleep(30)


@pytest.mark.parametrize('target,partial', [(partial_frame_stall, False), (result_then_partial_frame_stall, True)])
def test_partial_child_frame_cannot_block_parent_or_erase_previous_results(target, partial):
    agent = Agent(PRIORS, backend='mcts', budget=.6)
    agent.worker = SearchWorker(PRIORS, target=target)
    before = time.monotonic()
    try:
        choice = agent.choose(REQUEST, copy.deepcopy(EXAMPLE))
        assert time.monotonic() - before < .95
        assert choice in {a.to_choice() for a in our_actions(REQUEST)}
        assert agent.last_trace['failures'][-1]['type'] == 'deadline'
        assert agent.worker.process is None
        assert agent.worker.receiver is None and agent.worker.inbox is None
        if partial:
            assert choice == 'move 4'
            assert agent.last_trace['usable_worlds'] == agent.last_trace['completed_worlds'] == 1
            assert agent.last_trace['failed_worlds'] == agent.last_trace['interrupted_worlds'] == 1
        else:
            assert agent.last_trace['fallback_reason'] == 'worker_failure'
    finally:
        agent.close()


def result_then_native_exit(connection, priors):
    connection.recv()
    connection.send({'kind': 'world_started', 'index': 0})
    connection.send({'kind': 'world', 'result': {
        'index': 0, 'our_visits': [{'choice': 'ironhead', 'visits': 25}],
        'opponent_visits': [], 'elapsed_ms': 2, 'total_visits': 25, 'error': None}})
    os._exit(23)


def test_final_completed_world_is_drained_before_native_exit_error():
    agent = Agent(PRIORS, backend='mcts', budget=.6)
    agent.worker = SearchWorker(PRIORS, target=result_then_native_exit)
    try:
        assert agent.choose(REQUEST, copy.deepcopy(EXAMPLE)) == 'move 4'
        assert agent.last_trace['usable_worlds'] == agent.last_trace['completed_worlds'] == 1
        assert agent.last_trace['failures']
        assert agent.last_trace['fallback_reason'] is None
    finally:
        agent.close()


def test_process_start_failure_closes_bootstrap_pipes_and_allows_clean_restart():
    class Connection:
        closed = False
        def close(self): self.closed = True
    parent, child = Connection(), Connection()
    class Unstarted:
        pid = None
        def start(self): raise OSError('deliberate spawn failure')
        def join(self, **kwargs): raise AssertionError('cannot join an unstarted process')
    class Context:
        def Pipe(self): return parent, child
        def Process(self, **kwargs): return Unstarted()
    worker = SearchWorker(PRIORS)
    real_context = worker.context
    worker.context = Context()
    try:
        messages = list(worker.stream(REQUEST, copy.deepcopy(EXAMPLE), {}, time.monotonic() + .6))
        assert messages[-1]['error']['stage'] == 'worker_start'
        assert messages[-1]['error']['type'] == 'OSError'
        assert parent.closed and child.closed
        assert worker.process is None and worker.connection is None
        worker.close()  # safe even after a start that never assigned a pid
        worker.context = real_context
        worker.target = persistent_result
        messages = list(worker.stream(REQUEST, copy.deepcopy(EXAMPLE), {}, time.monotonic() + .6))
        assert messages[-1]['kind'] == 'done'
    finally:
        worker.close()


def done_then_stalls_receiving(connection, priors):
    connection.recv()
    connection.send({'kind': 'prepared', 'state_preparation_ms': 0})
    connection.send({'kind': 'world', 'result': {
        'index': 0, 'our_visits': [{'choice': 'ironhead', 'visits': 25}],
        'opponent_visits': [], 'elapsed_ms': 2, 'total_visits': 25, 'error': None}})
    connection.send({'kind': 'done', 'scheduled_worlds': 1})
    time.sleep(30)


def fill_parent_write_buffer(worker):
    descriptor = worker.connection.fileno()
    os.set_blocking(descriptor, False)
    try:
        while True:
            os.write(descriptor, b'x' * 65536)
    except BlockingIOError:
        pass
    finally:
        os.set_blocking(descriptor, True)


class FullPipeAfterDone(SearchWorker):
    def stream(self, *args, **kwargs):
        for message in super().stream(*args, **kwargs):
            if message['kind'] == 'done':
                fill_parent_write_buffer(self)
            yield message


def test_compact_chosen_message_does_not_resend_large_request_to_stalled_worker():
    agent = Agent(PRIORS, backend='mcts', budget=3)
    agent.worker = SearchWorker(PRIORS, target=done_then_stalls_receiving)
    request = {**REQUEST, 'padding': 'x' * (4 * 1024 * 1024)}
    before = time.monotonic()
    try:
        assert agent.choose(request, copy.deepcopy(EXAMPLE)) == 'move 4'
        assert time.monotonic() - before < 3
        assert not agent.last_trace['replay_not_recorded']
        assert agent.last_trace['fallback_reason'] is None
    finally:
        agent.close()


def test_post_search_bookkeeping_cannot_stall_or_replace_the_completed_choice():
    agent = Agent(PRIORS, backend='mcts', budget=3)
    agent.worker = FullPipeAfterDone(PRIORS, target=done_then_stalls_receiving)
    before = time.monotonic()
    try:
        assert agent.choose(REQUEST, copy.deepcopy(EXAMPLE)) == 'move 4'
        assert time.monotonic() - before < 3
        assert agent.last_trace['usable_worlds'] == 1
        assert agent.last_trace['bookkeeping_error']['type'] == 'TimeoutError'
        assert agent.last_trace['replay_not_recorded'] and agent.last_trace['worker_restart_required']
        assert agent.last_trace['fallback_reason'] is None
        assert agent.worker.process is None
    finally:
        agent.close()


def test_invalidation_pipe_write_is_bounded_and_discards_uncleared_replay_worker():
    worker = SearchWorker(PRIORS, target=done_then_stalls_receiving)
    try:
        assert list(worker.stream(REQUEST, copy.deepcopy(EXAMPLE), {}, time.monotonic() + 3))[-1]['kind'] == 'done'
        fill_parent_write_buffer(worker)
        before = time.monotonic()
        error = worker.invalidate_choice(deadline=before + .05)
        assert time.monotonic() - before < .3
        assert error['stage'] == 'choice_invalidation' and error['type'] == 'TimeoutError'
        assert worker.process is None and worker.connection is None
    finally:
        worker.close()


def partially_failed_preparation(connection, priors):
    import decision.belief
    from decision.search import _worker

    class BrokenBelief:
        def __init__(self, *args):
            self.recovery_events = []
            self.last_request = {'stale': True}
            self.last_choice = 'stale'
            self.updates = 0

        def update(self, battle):
            self.updates += 1
            if self.updates > 1:
                assert self.last_request is None and self.last_choice is None
            raise ValueError('deliberate partial preparation failure')

        def chose(self, *args):
            raise AssertionError('an unprepared fallback must never become replay evidence')

    decision.belief.Belief = BrokenBelief
    _worker(connection, priors)


def test_failed_preparation_cannot_record_fallback_against_stale_belief_snapshot():
    from decision.actions import Action
    worker = SearchWorker(PRIORS, target=partially_failed_preparation)
    config = {'seed': 2026, 'frozen_beliefs': False}
    try:
        first = list(worker.stream(REQUEST, copy.deepcopy(EXAMPLE), config, time.monotonic() + 3))
        assert first[0]['error']['stage'] == 'preparation'
        pid = worker.process.pid
        worker.chose(REQUEST, Action('move', 1))
        second = list(worker.stream(REQUEST, copy.deepcopy(EXAMPLE), config, time.monotonic() + 3))
        assert second[0]['error']['stage'] == 'preparation'
        assert second[0]['error']['type'] == 'ValueError'
        assert worker.process.pid == pid and worker.process.is_alive()
    finally:
        worker.close()


def test_failed_preparation_trace_marks_replay_unrecorded_without_inventing_send_failure():
    class PreparationFailure:
        generation = 1

        def stream(self, *args):
            yield {'kind': 'failure', 'error': {'stage': 'preparation', 'type': 'ValueError', 'message': 'bad state'}}
            yield {'kind': 'done', 'scheduled_worlds': 0}

        def chose(self, *args, **kwargs):
            raise AssertionError('unprepared choice must not be sent for replay')

        def close(self):
            pass

    agent = Agent(PRIORS, backend='mcts')
    agent.worker = PreparationFailure()
    try:
        assert agent.choose(REQUEST, copy.deepcopy(EXAMPLE)) == our_actions(REQUEST)[0].to_choice()
        assert agent.last_trace['replay_not_recorded']
        assert agent.last_trace['replay_not_recorded_reason'] == 'preparation_failed'
        assert 'bookkeeping_error' not in agent.last_trace
    finally:
        agent.close()
