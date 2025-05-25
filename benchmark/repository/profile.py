from enum import Enum
from pathlib import Path
from typing import List, Optional, Any

import yaml
from pydantic import BaseModel

from benchmark.model.profile import BenchmarkProfile


class ProfileRepository:
    def __init__(self, profiles_path: Path):
        self._profiles_path = profiles_path

    def get(self, profile_name: str) -> Optional[BenchmarkProfile]:
        path = self._profiles_path / f"{profile_name}.yaml"
        if not path.exists():
            return None
        with open(path) as f:
            return yaml_to_profile(f)

    def get_raw(self, profile_name: str) -> Optional[str]:
        path = self._profiles_path / f"{profile_name}.yaml"
        if not path.exists():
            return None
        with open(path) as f:
            return f.read()

    def list(self) -> list[str]:
        return [i.name[:-5] for i in self._profiles_path.glob("*.yaml")]

    def set(self, profile_name: str, profile: BenchmarkProfile):
        path = self._profiles_path / f"{profile_name}.yaml"
        with open(path, "w") as f:
            if isinstance(profile, BenchmarkProfile):
                profile = profile_to_yaml(profile)
            f.write(profile)

    def delete(self, profile_name: str):
        path = self._profiles_path / f"{profile_name}.yaml"
        path.unlink()


def enum_representer(dumper, data):
    return dumper.represent_scalar('tag:yaml.org,2002:str', str(data.value))


yaml.add_representer(Enum, enum_representer)


def convert_enums_to_values(data: Any) -> Any:
    if isinstance(data, Enum):
        return data.value
    elif isinstance(data, list):
        return [convert_enums_to_values(item) for item in data]
    elif isinstance(data, dict):
        return {key: convert_enums_to_values(value) for key, value in data.items()}
    elif isinstance(data, BaseModel):
        return convert_enums_to_values(data.dict(by_alias=True))
    return data


def yaml_to_profile(profile: str | Any) -> BenchmarkProfile:
    data = yaml.safe_load(profile)
    return BenchmarkProfile.model_validate(data)


def profile_to_yaml(profile: BenchmarkProfile) -> str:
    clean_data = convert_enums_to_values(profile)

    yaml.SafeDumper.ignore_aliases = lambda *args: True
    return yaml.safe_dump(clean_data,
                          default_flow_style=False,
                          sort_keys=False,
                          allow_unicode=True,
                          indent=2,
                          encoding='utf-8').decode('utf-8')


profiles = ProfileRepository(Path("_profiles"))
