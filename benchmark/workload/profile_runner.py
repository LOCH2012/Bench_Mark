import time
from multiprocessing import RLock
from typing import Callable

from benchmark.metrics.metric_reporter import MetricReporter
from benchmark.model.execution import ExecutionRequest
from benchmark.model.profile import BenchmarkProfile
from benchmark.workload.file_handler import FileHandler, FSFileHandler
from benchmark.workload.phase_runner import PhaseRunner


class PhaseCallback:
    def __init__(self, lock: RLock, states, execution_id: str):
        self.lock = lock
        self.states = states
        self.execution_id = execution_id

    def set(self, phase: int):
        with self.lock:
            self.states[self.execution_id] = {'status': 'running', 'phase': phase}

        # self.phase = phase


class ProfileRunner:
    _request: ExecutionRequest
    _metric_reporter: MetricReporter

    def __init__(self, request: ExecutionRequest, metric_reporter: MetricReporter,
                 phase_callback: PhaseCallback):
        self._request = request
        self._metric_reporter = metric_reporter
        self._phase_callback = phase_callback

    def run(self, execution_id: str):
        self._metric_reporter.start_execution()

        for i, phase in enumerate(self._request.profile.phases):
            self._phase_callback.set(i + 1)
            # time.sleep(1)
            runner = PhaseRunner(phase, self._metric_reporter, self._request.storage_configuration)
            runner.run()

        self._metric_reporter.summarize()
