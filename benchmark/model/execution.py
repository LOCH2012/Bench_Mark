from typing import TypeAlias

from pydantic import BaseModel

from benchmark.model.profile import BenchmarkProfile


class StorageConfiguration(BaseModel):
    path: str
    device: str


class ExecutionRequest(BaseModel):
    profile_name: str
    profile: BenchmarkProfile
    storage_configuration: StorageConfiguration
