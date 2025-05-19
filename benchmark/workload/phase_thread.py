import random
import time
from datetime import datetime
from typing import Callable, List, Tuple

from benchmark.config import MAX_PHASE_TIME
from benchmark.metrics.phase_metric_reporter import ThreadPhaseMetricReporter
from benchmark.model.execution import StorageConfiguration
from benchmark.model.results import StepResult
from benchmark.model.profile import ProfilePhase, ProfileOperation, ProfileOperationType, ProfileFileSelection, \
    ProfileOperationSelectionType
from benchmark.workload.file_handler import FileHandler, FileHandlerException, FSFileHandler


class PhaseThreadRunner:
    phase: ProfilePhase
    files: List[FileHandler]
    file_creator: Callable[[int], FileHandler]
    operation_offset: int
    random: random.Random

    def __init__(self, phase: ProfilePhase, storage_configuration: StorageConfiguration,
                 metric_reporter: ThreadPhaseMetricReporter, thread_name: str):
        self.phase = phase
        self.files = []
        self.file_creator = lambda size: FSFileHandler(basepath=storage_configuration, size=size)
        self.operation_offset = 0
        self.random = random.Random()
        self.metric_reporter = metric_reporter
        self.thread_name = thread_name

    def initialize(self):
        """Create random files"""
        for i in range(self.phase.prepared_files):
            self.files.append(self._create_file())

    def cleanup(self):
        """Cleanup after phases"""
        for f in self.files:
            try:
                f.delete()
            except FileHandlerException as e:
                pass

        self.files.clear()

    def execute(self):
        start_time = time.time()
        deadline = start_time + (self.phase.duration_sec if self.phase.duration_sec else MAX_PHASE_TIME)
        n_ops = 0
        while time.time() < deadline and (not self.phase.ops_cnt or n_ops < self.phase.ops_cnt):
            op_id, op = self._choose_op()
            n_ops += 1
            self._execute_operation(op_id, op, deadline)
        self.metric_reporter.report_phase(self.thread_name, time.time() - start_time, n_ops)

    def _choose_op(self) -> tuple[int, ProfileOperation]:
        possible_ops = []
        if not self.files:
            for op_id,op in enumerate(self.phase.operations):
                if op.file_selection == ProfileFileSelection.NEW_FILE and op.mode == ProfileOperationType.WRITE:
                    possible_ops.append((op_id, op))
        else:
            possible_ops = list(enumerate(self.phase.operations))
        assert len(possible_ops) > 0, "No such possible ops"

        if self.phase.operations_selection_type == ProfileOperationSelectionType.RANDOM:
            return self.random.choice(possible_ops)
        else:
            op_id = self.operation_offset % len(self.phase.operations)
            op = self.phase.operations[op_id]
            self.operation_offset += 1
            return op_id, op

    def _execute_operation(self, op_id: int, op: ProfileOperation, phase_deadline: time.time()):
        if op.file_selection == ProfileFileSelection.NEW_FILE:
            self.files.append(self._create_file())
            f = self.files[-1]
        elif op.file_selection == ProfileFileSelection.RANDOM_FILE:
            f = self.random.choice(self.files)
        elif op.file_selection == ProfileFileSelection.PREVIOUS_FILE:
            f = self.files[-1]
        else:
            raise ValueError("Unknown profile file selection")

        f.create()

        start_time = time.time()
        start_date_time = datetime.now()
        deadline = min(phase_deadline, start_time + op.duration_sec) if op.duration_sec else phase_deadline
        try:
            if op.mode == ProfileOperationType.READ:
                (units, is_failed) = f.read_blocks(op.ops_cnt, deadline, op.random_access)
            elif op.mode == ProfileOperationType.WRITE:
                (units, is_failed) = f.write_blocks(op.ops_cnt, deadline, op.random_access)
            else:
                raise ValueError("Unknown profile operation mode")
            done_seconds = time.time() - start_time
            self._log_step(start_date_time, f, op_id, op, len(units), done_seconds, is_failed, units)
        except FileHandlerException as e:
            done_seconds = time.time() - start_time
            self._log_step(start_date_time, f, op_id, op, 0, done_seconds, True, [])
        if op.idle_time:
            idle_time = self.random.choice(op.idle_time)
            print(f"{self.thread_name} idle for {idle_time} msec")
            time.sleep(idle_time / 1000)

    def _log_step(self, start_time, f, op_id, op, done_ops, done_seconds, is_failed, units):
        self.metric_reporter.report_operation(StepResult(filename=f.file_name(),
                                                         operation_id=op_id,
                                                         operation_type=op.mode,
                                                         operation_random_access=op.random_access,
                                                         ops_cnt=done_ops, duration_sec=done_seconds,
                                                         is_failed=is_failed,
                                                         time=start_time,
                                                         units=units
                                                         ))

    def _create_file(self):
        return self.file_creator(self.random.choice(self.phase.files_sizes))
