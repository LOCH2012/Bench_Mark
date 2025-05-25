import datetime
import signal
import sys
import time
from multiprocessing import Pool, Barrier, Manager, Value, Process

from benchmark.config import DISKSTATUS_INTERVAL
from benchmark.metrics.disk_status import get_physical_disk, get_diskstats
from benchmark.metrics.metric_reporter import MetricReporter
from benchmark.metrics.phase_metric_reporter import ThreadPhaseMetricReporterImpl
from benchmark.model.execution import StorageConfiguration
from benchmark.model.profile import ProfilePhase
from benchmark.model.results import PhaseThreadResult, DiskStatusUnit
from benchmark.workload.phase_thread_runner import PhaseThreadRunner


class PhaseRunner:
    def __init__(self, phase_id: int, phase: ProfilePhase, metric_reporter: MetricReporter,
                 storage_configuration: StorageConfiguration):
        self._phase_id = phase_id
        self._phase = phase
        self._metric_reporter = metric_reporter
        self._storage_configuration = storage_configuration

    def run(self):
        num_workers = self._phase.threads

        manager = Manager()
        shared_barrier = manager.Barrier(num_workers)
        running = manager.Value('i', 1)
        diskstatus_results = manager.Value('O', [])

        p = Process(
            target=self._diskstatus_collector_worker,
            args=(self._storage_configuration, running, diskstatus_results)
        )
        p.start()

        with Pool(self._phase.threads) as pool:
            per_thread_results = pool.starmap(self._thread_worker, [(i, shared_barrier) for i in range(num_workers)])

        running.value = 0
        p.join()

        self._metric_reporter.report_phase(self._phase, per_thread_results)
        self._metric_reporter.report_disk_status(self._phase_id, diskstatus_results.value)

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

        return reporter.phase_metric([f.file_name() for f in runner.files])

    def _diskstatus_collector_worker(self, storage_configuration: StorageConfiguration, is_running: Value,
                                     results_value: Value):
        storage_device = storage_configuration.device
        if storage_device is None:
            print(f"No storage device found for {storage_configuration}")
            return

        units = []

        prev_status = get_diskstats(storage_device)
        while is_running.value == 1:
            time.sleep(DISKSTATUS_INTERVAL)
            status = get_diskstats(storage_device)
            diff = prev_status.compare(status, DISKSTATUS_INTERVAL)
            prev_status = status
            units.append(DiskStatusUnit(
                time=datetime.datetime.now(),
                read_utilization=diff['read_utilization'],
                write_utilization=diff['write_utilization'],
                total_utilization=diff['total_utilization'],
                queue_length=diff['queue_length']
            ))
        results_value.value = units
