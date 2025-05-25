import datetime
from abc import ABC, abstractmethod
from typing import List

from benchmark.model.results import PhaseThreadResult, StepResult


class ThreadPhaseMetricReporter(ABC):
    @abstractmethod
    def start_phase(self):
        pass

    @abstractmethod
    def report_operation(self, unit: StepResult):
        pass

    @abstractmethod
    def finish_phase(self, duration, n_ops):
        pass

    def phase_metric(self, used_files: List[str]) -> PhaseThreadResult:
        pass


class ThreadPhaseMetricReporterImpl(ThreadPhaseMetricReporter):

    def __init__(self, thread_name: str):
        self._thread_name = thread_name
        self._unit_results: List[StepResult] = []
        self._duration = 0
        self._n_ops = 0
        self._start_time = datetime.datetime.now()
        self._finish_time = self._start_time

    def start_phase(self):
        self._start_time = datetime.datetime.now()

    def report_operation(self, step: StepResult):
        self._unit_results.append(step)
        print(f"step in {self._thread_name}: {step.ops_cnt} {step.duration_sec}")

    def finish_phase(self, duration, n_ops):
        self._duration = duration
        self._n_ops = n_ops
        self._finish_time = datetime.datetime.now()
        print(f"end_phase {self._thread_name}: {duration} {n_ops}")

    def phase_metric(self, used_files: List[str]):
        return PhaseThreadResult(
            thread_name=self._thread_name,
            steps=self._unit_results,
            used_files=used_files,
            ops_cnt=self._n_ops,
            duration_sec=self._duration,
            start_time=self._start_time,
            finish_time=self._finish_time,
        )
