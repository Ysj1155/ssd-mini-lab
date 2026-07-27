from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "analysis"))

import analyze_external_ssd_data_integrity as analyzer  # noqa: E402


class ExternalSsdHostCounterEvidenceTests(unittest.TestCase):
    def write_counter_csv(self, path: Path, values: list[int]) -> None:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "disk_bytes_per_sec",
                    "disk_read_bytes_per_sec",
                    "disk_write_bytes_per_sec",
                ],
            )
            writer.writeheader()
            for value in values:
                writer.writerow({
                    "disk_bytes_per_sec": value,
                    "disk_read_bytes_per_sec": 0,
                    "disk_write_bytes_per_sec": value,
                })

    def test_all_zero_samples_are_not_active_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "counters.csv"
            self.write_counter_csv(path, [0, 0, 0])

            self.assertEqual(analyzer.count_active_host_samples(path), 0)

    def test_nonzero_sample_is_active_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "counters.csv"
            self.write_counter_csv(path, [0, 4096, 0])

            self.assertEqual(analyzer.count_active_host_samples(path), 1)


if __name__ == "__main__":
    unittest.main()
