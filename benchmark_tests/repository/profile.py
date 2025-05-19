import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from benchmark.model.profile import BenchmarkProfile, ProfilePhase, ProfileOperation, ProfileOperationType, \
    ProfileFileSelection
from benchmark.repository.profile import ProfileRepository, profile_to_yaml

profile1 = BenchmarkProfile(
    phases=[
        ProfilePhase(threads=1, ops_cnt=1024, duration_sec=5, prepared_files=0,
                     operations=[
                         ProfileOperation(mode=ProfileOperationType.WRITE, random_access=True, ops_cnt=1024,
                                          file_selection=ProfileFileSelection.NEW_FILE),
                     ], files_sizes=[1024 ** 2 * 64]),
    ])
profile2 = BenchmarkProfile(
    phases=[
        ProfilePhase(threads=1, ops_cnt=1024, duration_sec=5, prepared_files=10,
                     operations=[
                         ProfileOperation(mode=ProfileOperationType.READ, random_access=True, ops_cnt=1024,
                                          file_selection=ProfileFileSelection.PREVIOUS_FILE),
                         ProfileOperation(mode=ProfileOperationType.WRITE, random_access=True, ops_cnt=1024,
                                          file_selection=ProfileFileSelection.PREVIOUS_FILE),
                     ], files_sizes=[1024 ** 2 * 64]),
    ])


@pytest.fixture
def repo():
    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        write_profile(profile1, temp_path / "default.yaml")
        write_profile(profile2, temp_path / "advanced.yaml")

        yield ProfileRepository(temp_path)


def write_profile_text(profile, path):
    with open(path, "w") as f:
        f.write(profile)


def write_profile(profile: BenchmarkProfile, path):
    write_profile_text(profile_to_yaml(profile), path)


def test_get_existing_profile(repo):
    result = repo.get("default")

    assert result is not None
    assert result == profile1


def test_get_existing_adv_profile(repo):
    result = repo.get("advanced")

    assert result is not None
    assert result == profile2


def test_get_nonexistent_profile(repo):
    assert repo.get("unknown") is None


def test_list_profiles(repo):
    profiles = repo.list()

    assert len(profiles) == 2
    assert set(profiles) == {"default", "advanced"}


def test_profile_from_text(repo):
    profile = """phases:
- threads: 1
  ops_cnt: 1024
  duration_sec: 5
  prepared_files: 0
  files_sizes:
  - 67108864
  operations:
  - mode: write
    random_access: true
    ops_cnt: 1024
    file_selection: new_file
  operations_selection_type: random
"""
    write_profile_text(profile, repo._profiles_path / "new.yaml")
    repo.get("new")


def test_profile_from_text2(repo):
    profile = """phases:
- threads: 1
  ops_cnt: 1024
  duration_sec: 5
  prepared_files: 0
  files_sizes:
  - 67108864
  operations:
  - mode: write
    random_access: true
    duration_sec: 1
    file_selection: new_file
  operations_selection_type: random
"""
    write_profile_text(profile, repo._profiles_path / "new.yaml")
    repo.get("new")


def test_profile_op_idle_time_number(repo):
    profile = """phases:
- threads: 1
  ops_cnt: 1024
  duration_sec: 5
  prepared_files: 0
  files_sizes:
  - 67108864
  operations:
  - mode: write
    random_access: true
    duration_sec: 1
    file_selection: new_file
    idle_time: 100
  operations_selection_type: random
"""
    write_profile_text(profile, repo._profiles_path / "new.yaml")
    assert repo.get("new").phases[0].operations[0].idle_time == [100]


def test_profile_op_idle_time_list(repo):
    profile = """phases:
- threads: 1
  ops_cnt: 1024
  duration_sec: 5
  prepared_files: 0
  files_sizes:
  - 67108864
  operations:
  - mode: write
    random_access: true
    duration_sec: 1
    file_selection: new_file
    idle_time:
    - 100.5
    - 200
  operations_selection_type: random
"""
    write_profile_text(profile, repo._profiles_path / "new.yaml")
    assert repo.get("new").phases[0].operations[0].idle_time == [100.5, 200]


def test_profile_phase_idle_time_list(repo):
    profile = """phases:
- threads: 1
  ops_cnt: 1024
  duration_sec: 5
  prepared_files: 0
  files_sizes:
  - 67108864
  operations:
  - mode: write
    random_access: true
    duration_sec: 1
    file_selection: new_file
  idle_time:
  - 100.5
  - 200
  operations_selection_type: random
"""
    write_profile_text(profile, repo._profiles_path / "new.yaml")
    assert repo.get("new").phases[0].idle_time == [100.5, 200]
    assert repo.get("new").phases[0].operations[0].idle_time == [100.5, 200]


def test_profile_profile_idle_time_float(repo):
    profile = """phases:
- threads: 1
  ops_cnt: 1024
  duration_sec: 5
  prepared_files: 0
  files_sizes:
  - 67108864
  operations:
  - mode: write
    random_access: true
    duration_sec: 1
    file_selection: new_file
  operations_selection_type: random
idle_time: 100.5
"""
    write_profile_text(profile, repo._profiles_path / "new.yaml")
    assert repo.get("new").idle_time == [100.5]
    assert repo.get("new").phases[0].idle_time == [100.5]
    assert repo.get("new").phases[0].operations[0].idle_time == [100.5]
