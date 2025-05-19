from pathlib import Path
from typing import Optional

from benchmark.model.results import BenchmarkResultSummary


class ReportRepository:
    def __init__(self, reports_path: Path):
        self._reports_path = reports_path

    def get_summary(self, report_name: str) -> Optional[BenchmarkResultSummary]:
        path = self._reports_path / f"{report_name}_summary.json"
        if not path.exists():
            return None
        with open(path) as f:
            return BenchmarkResultSummary.parse_raw(f.read())

    def list(self) -> list[str]:
        return [i.name[:-13] for i in self._reports_path.glob("*_summary.json")]


reports = ReportRepository(Path("_results"))
