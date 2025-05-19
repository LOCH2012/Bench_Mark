import json
import os
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

from benchmark.config import BLOCK_SIZE, METRICS_PATH
from benchmark.model.execution import ExecutionRequest
from benchmark.model.results import PhaseThreadResult, StepResult, PhaseResult, BenchmarkResult
from benchmark.model.profile import ProfilePhase, BenchmarkProfile


class MetricReporter(ABC):
    @abstractmethod
    def start_execution(self):
        pass

    @abstractmethod
    def report_phase(self, phase: ProfilePhase, thread_results: List[PhaseThreadResult]):
        pass

    @abstractmethod
    def summarize(self):
        pass


def metricFileReporter(execution_id: str, request: ExecutionRequest):
    return MetricToFileReporter(request, METRICS_PATH, execution_id)


class MetricToFileReporter(MetricReporter):
    _phases_results: List[PhaseResult]
    _metric_file_name_operations: Path
    _metric_file_name_units: Path
    _phase_id = 0

    def __init__(self, request: ExecutionRequest, metrics_directory: Path, execution_id: str):
        self._execution_id = execution_id
        self._start_time = None
        self._request = request
        execution_id = execution_id if execution_id else f"{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self._metric_file_name_operations = metrics_directory / (execution_id + "_ops.csv")
        self._metric_file_name_units = metrics_directory / (execution_id + "_units.csv")
        self._metric_file_name_summary = metrics_directory / (execution_id + "_summary.json")
        self._phases_results: List[PhaseResult] = []

        with open(self._metric_file_name_operations, "w") as f:
            f.write(
                "time,phase_id,thread_id,step_id,filename,operation_id,operation_type,operation_random_access,is_failed,bytes,duration\n")
        with open(self._metric_file_name_units, "w") as f:
            f.write(
                "time,phase_id,thread_id,step_id,unit_id,filename,operation_id,operation_type,operation_random_access,is_failed,bytes,duration\n")

    def start_execution(self):
        self._start_time = datetime.now()
        self._phases_results = []
        r = BenchmarkResult(execution_id=self._execution_id,
                            start_time=self._start_time,
                            finish_time=None,
                            profile_name=self._request.profile_name,
                            profile=self._request.profile,
                            storage_configuration=self._request.storage_configuration,
                            phases_results=[])
        with open(self._metric_file_name_summary, "w") as f:
            f.write(r.get_summary().model_dump_json(indent=2))

    def report_phase(self, phase: ProfilePhase, thread_results: List[PhaseThreadResult]):
        print(f"phase {self._phase_id} finished")
        self._phase_id += 1
        phases_result = PhaseResult(threads=thread_results)
        self._phases_results.append(phases_result)

        operations = []
        units = []
        for (thread_id, thread_result) in enumerate(thread_results):
            thread_result: PhaseThreadResult
            for s_id, s in enumerate(thread_result.steps):
                s: StepResult
                operations.append((
                    s.time.strftime("%Y-%m-%d %H:%M:%S.%f"), self._phase_id, thread_id, s_id, s.filename,
                    s.operation_id, s.operation_type,
                    int(s.operation_random_access), int(s.is_failed), s.ops_cnt * BLOCK_SIZE, s.duration_sec))

                for u_id, u in enumerate(s.units):
                    u: Tuple[float, float]
                    units.append((
                        (s.time + timedelta(seconds=u[0])).strftime("%Y-%m-%d %H:%M:%S.%f"), self._phase_id, thread_id,
                        s_id, u_id, s.filename, s.operation_id, s.operation_type,
                        int(s.operation_random_access), int(s.is_failed), BLOCK_SIZE, u[1]))

        operations.sort()
        units.sort()

        with open(self._metric_file_name_operations, "a") as f:
            f.writelines(map(lambda u: ",".join(map(str, u)) + "\n", operations))
        with open(self._metric_file_name_units, "a") as f:
            f.writelines(map(lambda u: ",".join(map(str, u)) + "\n", units))
        print(f"{len(operations)} operations, {len(units)} units")

    def summarize(self):
        r = BenchmarkResult(execution_id=self._execution_id,
                            start_time=self._start_time,
                            finish_time=datetime.now(),
                            profile_name=self._request.profile_name,
                            profile=self._request.profile,
                            storage_configuration=self._request.storage_configuration,
                            phases_results=self._phases_results)
        with open(self._metric_file_name_summary, "w") as f:
            f.write(r.get_summary().model_dump_json(indent=2))
