import signal
import threading
import sys
import os
import time
from functools import partial
from typing import Callable
from multiprocessing import Process, Semaphore, Pool, Condition, Lock, Barrier, Manager

from benchmark.metrics.metric_reporter import MetricReporter
from benchmark.metrics.phase_metric_reporter import ThreadPhaseMetricReporterImpl
from benchmark.model.execution import StorageConfiguration
from benchmark.model.results import PhaseThreadResult
from benchmark.model.profile import ProfilePhase
from benchmark.workload.file_handler import FileHandler
from benchmark.workload.phase_thread import PhaseThreadRunner

class PhaseRunner:
    def __init__(self, phase: ProfilePhase, metric_reporter: MetricReporter,
                 storage_configuration: StorageConfiguration):
        self._phase = phase
        self._metric_reporter = metric_reporter
        self._storage_configuration = storage_configuration

    def run(self):
        num_workers = self._phase.threads

        manager = Manager()
        shared_barrier = manager.Barrier(num_workers)

        with Pool(self._phase.threads) as pool:
            per_thread_results = pool.starmap(self._thread_worker, [(i, shared_barrier) for i in range(num_workers)])

        self._metric_reporter.report_phase(self._phase, per_thread_results)

    def _thread_worker(self, worker_id: int, start_barrier: Barrier) -> PhaseThreadResult:
        reporter = ThreadPhaseMetricReporterImpl(f"thread-{worker_id}")

        thread_name = f"thread-{worker_id}"

        runner = PhaseThreadRunner(self._phase, self._storage_configuration, reporter, thread_name)

        def SIGINT_handler(signum, frame):
            runner.cleanup()
            if signum == signal.SIGINT or signum == signal.SIGTERM:
                sys.exit(0)

        signal.signal(signal.SIGINT, SIGINT_handler)
        signal.signal(signal.SIGTERM, SIGINT_handler)

        runner.initialize()
        print(f"thread {worker_id} initialized")

        start_barrier.wait()
        print(f"thread {worker_id} started")
        runner.execute()

        print(f"thread {worker_id} finished")
        runner.cleanup()

        result = reporter.phase_metric([f.file_name() for f in runner.files])
        return result
