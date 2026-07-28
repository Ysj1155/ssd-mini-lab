from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
COLLECTOR = (
    REPO_ROOT
    / "scripts"
    / "observers"
    / "collect_windows_storage_counters.ps1"
)
sys.path.insert(0, str(REPO_ROOT / "scripts" / "analysis"))

import analyze_external_ssd_data_integrity as analyzer  # noqa: E402


class ExternalSsdHostObserverPathContractTests(unittest.TestCase):
    def write_counter_csv(self, path: Path, value: int = 4096) -> None:
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
            writer.writerow({
                "disk_bytes_per_sec": value,
                "disk_read_bytes_per_sec": 0,
                "disk_write_bytes_per_sec": value,
            })

    def write_manifest(
        self,
        host_dir: Path,
        counter_csv: str,
        *,
        status: str = "complete",
    ) -> None:
        (host_dir / "write_manifest.json").write_text(
            json.dumps({
                "phase": "write",
                "status": status,
                "sampling": {"sample_count": 1},
                "artifacts": {"counter_csv": counter_csv},
            }),
            encoding="utf-8",
        )

    def load_status(self, root: Path, result_dir: Path) -> dict[str, object]:
        with mock.patch.object(analyzer, "REPO_ROOT", root):
            return analyzer.load_host_observer_statuses(result_dir)[0]

    def test_manifest_relative_counter_csv_can_complete(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            result_dir = root / "result"
            host_dir = result_dir / "host_observer"
            host_dir.mkdir(parents=True)
            self.write_counter_csv(host_dir / "write.csv")
            self.write_manifest(host_dir, "write.csv")

            status = self.load_status(root, result_dir)

        self.assertEqual(status["status"], "complete")
        self.assertEqual(status["artifact_path_mode"], "manifest_relative")
        self.assertEqual(status["active_sample_count"], 1)
        self.assertEqual(
            status["counter_csv"],
            "result/host_observer/write.csv",
        )

    def test_legacy_absolute_path_uses_only_local_basename(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            result_dir = root / "result"
            host_dir = result_dir / "host_observer"
            host_dir.mkdir(parents=True)
            self.write_counter_csv(host_dir / "write.csv")
            self.write_manifest(host_dir, "C:/old/repository/write.csv")

            status = self.load_status(root, result_dir)

        self.assertEqual(status["status"], "complete")
        self.assertEqual(
            status["artifact_path_mode"],
            "legacy_absolute_basename",
        )
        self.assertEqual(status["active_sample_count"], 1)

    def test_external_absolute_csv_cannot_upgrade_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            result_dir = root / "result"
            host_dir = result_dir / "host_observer"
            host_dir.mkdir(parents=True)
            outside_csv = root / "outside.csv"
            self.write_counter_csv(outside_csv)
            self.write_manifest(host_dir, str(outside_csv.resolve()))

            status = self.load_status(root, result_dir)

        self.assertEqual(status["status"], "limited")
        self.assertEqual(status["active_sample_count"], 0)
        self.assertIsNone(status["counter_csv"])
        self.assertIn("missing from the host-observer", status["limitation"])

    def test_relative_escape_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            result_dir = root / "result"
            host_dir = result_dir / "host_observer"
            host_dir.mkdir(parents=True)
            self.write_counter_csv(result_dir / "outside.csv")
            self.write_manifest(host_dir, "../outside.csv")

            status = self.load_status(root, result_dir)

        self.assertEqual(status["status"], "limited")
        self.assertEqual(status["active_sample_count"], 0)
        self.assertIn("escapes the host-observer", status["limitation"])

    def test_alternate_data_stream_name_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            result_dir = root / "result"
            host_dir = result_dir / "host_observer"
            host_dir.mkdir(parents=True)
            self.write_manifest(host_dir, "write.csv:stream")

            status = self.load_status(root, result_dir)

        self.assertEqual(status["status"], "limited")
        self.assertIn("alternate data stream", status["limitation"])

    def test_collector_emits_manifest_relative_artifact_names(self) -> None:
        text = COLLECTOR.read_text(encoding="utf-8-sig")

        self.assertIn('path_base = "manifest_directory"', text)
        self.assertIn(
            "[System.IO.Path]::GetFileName($CsvPath)",
            text,
        )
        self.assertIn(
            "[System.IO.Path]::GetFileName($StopFile)",
            text,
        )


if __name__ == "__main__":
    unittest.main()
