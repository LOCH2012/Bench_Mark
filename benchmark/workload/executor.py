import os
import random
import signal
from datetime import datetime
from typing import Callable
from multiprocessing import Manager, Process, RLock

from benchmark.metrics.metric_reporter import MetricReporter
from benchmark.model.execution import ExecutionRequest
from benchmark.model.profile import BenchmarkProfile
from benchmark.workload.file_handler import FileHandler, FSFileHandler
from benchmark.workload.profile_runner import ProfileRunner, PhaseCallback


class BenchmarkExecutor:
    def __init__(self):
        self._manager = Manager()
        self._states = self._manager.dict()
        self._current_pid = self._manager.Value('i', 0)
        self._current_execution_id = self._manager.Value('s', None)
        self._lock = self._manager.RLock()

    def execute(self, request: ExecutionRequest, metric_reporter: Callable[[str, ExecutionRequest], MetricReporter]):
        execution_id = datetime.now().strftime('%Y%m%d_%H%M%S') + '_' + hex(random.randint(0, 0xffff))[2:].zfill(4)
        with self._lock:
            print(self._current_execution_id.value)
            if self._current_execution_id.value is not None:
                raise Exception("An oter execution is already running")
            self._current_execution_id.value = execution_id
            self._current_pid.value = 0
            self._states[execution_id] = {'status': 'initialized', 'phase': 0}

        p = Process(
            target=self._execute_profile,
            args=(execution_id, request, metric_reporter(execution_id, request), self._lock)
        )
        p.start()
        with self._lock:
            if self._states[execution_id]['status'] != 'initialized':
                raise Exception("An execution is already running")
            self._current_pid.value = p.pid
            self._states[execution_id] = {'status': 'running', 'phase': 0}

        return execution_id

    def _execute_profile(self, execution_id: str, request: ExecutionRequest, metric_reporter: MetricReporter,
                         lock: RLock):
        try:
            callback = PhaseCallback(self._lock, self._states, execution_id)
            runner = ProfileRunner(request, metric_reporter, callback)
            runner.run(execution_id)
            with lock:
                self._states[execution_id] = {'status': 'done', 'phase': self._states[execution_id]['phase']}
                self._current_execution_id.value = None
            print(f"Benchmark execution {execution_id} finished")
        except KeyboardInterrupt as e:
            print(f"Execution {execution_id} interrupted")

    def _phase_callback(self, execution_id: str, phase: int):
        with self._lock:
            self._states[execution_id] = {'status': 'running', 'phase': phase}

    def interrupt(self, execution_id: str):
        with self._lock:
            if self._states.get(execution_id, {'status': None})['status'] != 'running' or \
                    self._current_execution_id.value != execution_id:
                raise Exception("An execution is not running")
            pid = self._current_pid.value
            self._current_pid.value = 0
            self._current_execution_id.value = None
            self._states[execution_id] = {'status': 'interrupted',
                                          'phase': self._states[execution_id]['phase']}

        os.kill(pid, signal.SIGINT)

    def status(self, execution_id: str):
        with self._lock:
            return self._states.get(execution_id, None)

    def all_executions(self):
        with self._lock:
            return dict(self._states)

    def close(self):
        self._manager.shutdown()

BENCHMARK_EXECUTOR = BenchmarkExecutor()