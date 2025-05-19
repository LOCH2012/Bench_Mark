import json
import os
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

from benchmark.config import BLOCK_SIZE, METRICS_PATH
from benchmark.model.results import PhaseThreadResult, StepResult, PhaseResult, BenchmarkResult
from benchmark.model.profile import ProfilePhase, BenchmarkProfile


class ThreadPhaseMetricReporter(ABC):
    @abstractmethod
    def report_operation(self, unit: StepResult):
        pass

    @abstractmethod
    def report_phase(self, duration, n_ops, time):
        pass

    def phase_metric(self, used_files: List[str]) -> PhaseThreadResult:
        pass


class ThreadPhaseMetricReporterImpl(ThreadPhaseMetricReporter):

    def __init__(self, thread_name: str):
        self._thread_name = thread_name
        self._unit_results: List[StepResult] = []
        self._duration = 0
        self._n_ops = 0

    def report_operation(self, step: StepResult):
        self._unit_results.append(step)
        print(f"step in {self._thread_name}: {step.ops_cnt} {step.duration_sec}")

    def report_phase(self, thread_name, duration, n_ops):
        self._duration = duration
        self._n_ops = n_ops
        print(f"end_phase {self._thread_name}: {duration} {n_ops}")

    def phase_metric(self, used_files: List[str]):
        return PhaseThreadResult(thread_name=self._thread_name, steps=self._unit_results, used_files=used_files,
                                 ops_cnt=self._n_ops, duration_sec=self._duration)
