import datetime
from typing import List, Tuple, Optional, Dict, Union
from pydantic import BaseModel

from benchmark.model.execution import StorageConfiguration
from benchmark.model.profile import ProfileOperationType, BenchmarkProfile


class StepResult(BaseModel):
    filename: str
    operation_id: int
    operation_type: ProfileOperationType
    operation_random_access: bool
    ops_cnt: int
    duration_sec: float
    is_failed: bool
    time: datetime.datetime
    units: list[Tuple[float, float]]


class PhaseThreadResult(BaseModel):
    thread_name: str
    start_time: datetime.datetime
    finish_time: datetime.datetime
    steps: List[StepResult]
    used_files: List[str]
    ops_cnt: int
    duration_sec: float


class PhaseResult(BaseModel):
    threads: List[PhaseThreadResult]
    start_time: datetime.datetime
    finish_time: datetime.datetime


class BenchmarkResultSummary(BaseModel):
    execution_id: str
    start_time: datetime.datetime
    finish_time: Optional[datetime.datetime]
    profile_name: str
    profile: BenchmarkProfile
    storage_configuration: StorageConfiguration
    system_info: Dict[str, Union[str, int, float]]


class BenchmarkResult(BaseModel):
    execution_id: str
    start_time: datetime.datetime
    finish_time: Optional[datetime.datetime]
    profile_name: str
    profile: BenchmarkProfile
    storage_configuration: StorageConfiguration
    system_info: Dict[str, Union[str, int, float]]
    phases_results: List[PhaseResult]

    def get_summary(self) -> BenchmarkResultSummary:
        return BenchmarkResultSummary(**self.dict())


class DiskStatusUnit(BaseModel):
    time: datetime.datetime
    read_utilization: float
    write_utilization: float
    total_utilization: float
    queue_length: int
