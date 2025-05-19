from enum import Enum
from typing import List, Union, Annotated

from pydantic import BaseModel, Field, BeforeValidator, field_validator
from pydantic_core.core_schema import FieldValidationInfo


class ProfileOperationType(Enum):
    READ = "read"
    WRITE = "write"

    def __str__(self) -> str:
        return self.name.lower()


class ProfileFileSelection(Enum):
    NEW_FILE = 'new_file'
    PREVIOUS_FILE = 'previous_file'
    RANDOM_FILE = 'random_file'

    def __str__(self) -> str:
        return self.name.lower()


def idle_time_validator(v: Union[int, float, List[float], None]) -> List[float]:
    if v is None:
        return []
    if isinstance(v, (int, float)):
        return [float(v)]
    if isinstance(v, list):
        return [float(x) for x in v]
    raise ValueError("idle_time must be number or list of numbers")


IDLE_TIME = Annotated[List[float], Field(default_factory=list), BeforeValidator(idle_time_validator)]


class ProfileOperation(BaseModel):
    mode: ProfileOperationType
    random_access: bool = True
    block_offset: int = 0
    ops_cnt: int | None = None
    duration_sec: int | None = None
    file_selection: ProfileFileSelection = ProfileFileSelection.RANDOM_FILE
    idle_time: IDLE_TIME


class ProfileOperationSelectionType(Enum):
    RANDOM = "random"
    SEQUENTIAL = "sequential"


class ProfilePhase(BaseModel):
    idle_time: IDLE_TIME
    threads: int = 1
    ops_cnt: int | None = None
    duration_sec: int | None = None
    prepared_files: int = 8
    files_sizes: List[int] = Field(default_factory=lambda: [1024 ** 2])
    operations: List[ProfileOperation] = Field(default_factory=list)
    operations_selection_type: ProfileOperationSelectionType = ProfileOperationSelectionType.RANDOM

    @field_validator('operations', mode='after')
    def propagate_idle_time(cls, operations: List[ProfileOperation], values):
        parent_idle_time = values.data.get('idle_time')
        if parent_idle_time:
            for op in operations:
                if not op.idle_time:
                    op.idle_time = parent_idle_time
        return operations


class BenchmarkProfile(BaseModel):
    idle_time: IDLE_TIME
    phases: List[ProfilePhase]

    @field_validator('phases', mode='after')
    def propagate_profile_idle_time(cls, phases: List[ProfilePhase], info: FieldValidationInfo):
        parent_idle_time = info.data.get('idle_time')
        if parent_idle_time:
            for phase in phases:
                if not phase.idle_time:
                    phase.idle_time = parent_idle_time
                    for op in phase.operations:
                        if not op.idle_time:
                            op.idle_time = parent_idle_time
        return phases
