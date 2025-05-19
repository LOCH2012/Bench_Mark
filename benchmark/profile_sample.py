from benchmark.model.profile import ProfilePhase, ProfileOperation, ProfileOperationType, ProfileFileSelection, \
    BenchmarkProfile

PHASE1 = ProfilePhase(threads=1, ops_cnt=1024, duration_sec=5, prepared_files=0, operations=[
    ProfileOperation(mode=ProfileOperationType.WRITE, random_access=True, ops_cnt=1024,
                     file_selection=ProfileFileSelection.NEW_FILE),
], files_sizes=[1024 ** 2 * 64])

PHASE2 = ProfilePhase(threads=1, ops_cnt=1024, duration_sec=5, prepared_files=8, operations=[
    ProfileOperation(mode=ProfileOperationType.READ, random_access=True, ops_cnt=1024,
                     file_selection=ProfileFileSelection.NEW_FILE),
], files_sizes=[1024 ** 2 * 64])

PHASE3 = ProfilePhase(threads=4, ops_cnt=1024, duration_sec=15, prepared_files=0, operations=[
    ProfileOperation(mode=ProfileOperationType.WRITE, random_access=True, ops_cnt=1024 * 8,
                     file_selection=ProfileFileSelection.NEW_FILE),
    ProfileOperation(mode=ProfileOperationType.READ, random_access=True, ops_cnt=1024 * 8,
                     file_selection=ProfileFileSelection.PREVIOUS_FILE),
], files_sizes=[1024 ** 2 * 1])

PHASE4 = ProfilePhase(threads=4, ops_cnt=1024, duration_sec=15, prepared_files=0, operations=[
    ProfileOperation(mode=ProfileOperationType.WRITE, random_access=False, ops_cnt=1024 * 8,
                     file_selection=ProfileFileSelection.NEW_FILE),
    ProfileOperation(mode=ProfileOperationType.READ, random_access=False, ops_cnt=1024 * 8,
                     file_selection=ProfileFileSelection.PREVIOUS_FILE),
], files_sizes=[1024 ** 2 * 1])


def gen_thread_increase(n):
    return [ProfilePhase(threads=i, ops_cnt=1024, duration_sec=10, prepared_files=0, operations=[
        ProfileOperation(mode=ProfileOperationType.WRITE, random_access=True, ops_cnt=8 * 1024,
                         file_selection=ProfileFileSelection.NEW_FILE),
        ProfileOperation(mode=ProfileOperationType.READ, random_access=True, ops_cnt=1024,
                         file_selection=ProfileFileSelection.PREVIOUS_FILE),
    ], files_sizes=[1024 ** 2 * 1])
            for i in range(1, n + 1)]


def gen_thread_increase2(n, op_cnt):
    return [ProfilePhase(threads=i, duration_sec=20, prepared_files=8, operations=[
        ProfileOperation(mode=ProfileOperationType.WRITE, random_access=True, ops_cnt=op_cnt,
                         file_selection=ProfileFileSelection.NEW_FILE),
        ProfileOperation(mode=ProfileOperationType.READ, random_access=True, ops_cnt=op_cnt,
                         file_selection=ProfileFileSelection.PREVIOUS_FILE),
    ], files_sizes=[1024 ** 2 * 1])
            for i in range(1, n + 1)]


PROFILE1 = BenchmarkProfile(phases=[PHASE3, PHASE4])
PROFILE2 = BenchmarkProfile(phases=gen_thread_increase(4))
PROFILE3 = BenchmarkProfile(phases=gen_thread_increase2(1, 64) + gen_thread_increase2(1, 1024))

# PHASE4 = ProfilePhase(threads=1, ops_cnt=1024, duration_sec=5, prepared_files=0, operations=[
#     ProfileOperation(mode=ProfileOperationType.WRITE, random_access=True, ops_cnt=1024,
#                      file_selection=ProfileFileSelection.NEW_FILE),
#     ProfileOperation(mode=ProfileOperationType.READ, random_access=True, ops_cnt=1024,
#                      file_selection=ProfileFileSelection.PREVIOUS_FILE),
#     ProfileOperation(mode=ProfileOperationType.READ, random_access=True, ops_cnt=1024,
#                      file_selection=ProfileFileSelection.RANDOM_FILE),
# ], files_sizes=[1024**2 * 512])
#
