from pathlib import Path

from benchmark.model.execution import StorageConfiguration

MAX_PHASE_TIME = 24 * 3600

BLOCK_SIZE = 4096

METRICS_PATH = Path("_results")
STORAGE_CONFIG: StorageConfiguration = "_test"

