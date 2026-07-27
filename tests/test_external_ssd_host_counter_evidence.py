from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


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

    def test_producer_error_is_not_mislabeled_as_zero_activity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result_dir = Path(temp_dir)
            host_dir = result_dir / "host_observer"
            host_dir.mkdir()
            csv_path = host_dir / "write.csv"
            self.write_counter_csv(csv_path, [4096])
            manifest_path = host_dir / "write_manifest.json"
            manifest_path.write_text(
                json.dumps({
                    "phase": "write",
                    "status": "limited",
                    "sampling": {"sample_count": 1},
                    "artifacts": {"counter_csv": str(csv_path)},
                }),
                encoding="utf-8",
            )

            with mock.patch.object(analyzer, "REPO_ROOT", result_dir):
                statuses = analyzer.load_host_observer_statuses(result_dir)

        self.assertEqual(statuses[0]["status"], "limited")
        self.assertEqual(statuses[0]["active_sample_count"], 1)
        self.assertIn("producer status was limited", statuses[0]["limitation"])


if __name__ == "__main__":
    unittest.main()
