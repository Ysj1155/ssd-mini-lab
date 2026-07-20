from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "tests" / "fixtures"
sys.path.insert(0, str(REPO_ROOT / "scripts" / "analysis"))

import parse_fio_results as parser  # noqa: E402


class ParseFioResultsCompatibilityTests(unittest.TestCase):
    def test_parses_supported_fio_3_42_randread(self) -> None:
        rows = parser.parse_one_json(FIXTURES / "fio_3_42_randread.json")

        self.assertEqual(len(rows), 1)
        row = rows[0]

        self.assertEqual(row["fio_version"], "fio-3.42")
        self.assertTrue(row["fio_version_supported"])
        self.assertEqual(row["job_error"], 0)
        self.assertEqual(row["active_direction"], "read")
        self.assertEqual(row["rw"], "randread")
        self.assertEqual(row["bs"], "4k")
        self.assertEqual(row["iodepth"], "16")
        self.assertAlmostEqual(row["runtime_sec"], 120.001)
        self.assertAlmostEqual(row["bandwidth_mib_s"], 187191296 / (1024 * 1024))
        self.assertAlmostEqual(row["clat_p99_us"], 692.224)

    def test_missing_percentiles_are_preserved_as_none(self) -> None:
        rows = parser.parse_one_json(FIXTURES / "fio_missing_percentile.json")

        self.assertEqual(len(rows), 1)
        row = rows[0]

        self.assertAlmostEqual(row["clat_p95_us"], 150.0)
        self.assertIsNone(row["clat_p99_us"])
        self.assertIsNone(row["clat_p999_us"])

    def test_error_job_is_not_hidden(self) -> None:
        rows = parser.parse_one_json(FIXTURES / "fio_error_job.json")

        self.assertEqual(len(rows), 1)
        row = rows[0]

        self.assertEqual(row["job_error"], 5)
        self.assertEqual(row["active_direction"], "write")
        self.assertAlmostEqual(row["clat_p99_us"], 1200.0)

    def test_mixed_job_emits_read_and_write_rows(self) -> None:
        rows = parser.parse_one_json(FIXTURES / "fio_mixed_job.json")

        self.assertEqual(len(rows), 2)
        by_direction = {row["active_direction"]: row for row in rows}

        self.assertEqual(set(by_direction), {"read", "write"})
        self.assertEqual(by_direction["read"]["rw"], "randrw")
        self.assertEqual(by_direction["write"]["rw"], "randrw")
        self.assertAlmostEqual(by_direction["read"]["clat_p99_us"], 400.0)
        self.assertAlmostEqual(by_direction["write"]["clat_p99_us"], 600.0)

    def test_unsupported_fio_version_is_flagged_best_effort(self) -> None:
        fixture = json.loads((FIXTURES / "fio_3_42_randread.json").read_text(encoding="utf-8"))
        fixture["fio version"] = "fio-4.0"

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "rand_read_qd16_run1.json"
            path.write_text(json.dumps(fixture), encoding="utf-8")
            rows = parser.parse_one_json(path)

        self.assertEqual(rows[0]["fio_version"], "fio-4.0")
        self.assertFalse(rows[0]["fio_version_supported"])

    def test_write_csv_includes_compatibility_fields(self) -> None:
        rows = parser.parse_one_json(FIXTURES / "fio_3_42_randread.json")

        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "summary.csv"
            parser.write_csv(rows, output)

            with output.open("r", newline="", encoding="utf-8-sig") as f:
                csv_rows = list(csv.DictReader(f))

        self.assertEqual(len(csv_rows), 1)
        self.assertIn("fio_version_supported", csv_rows[0])
        self.assertIn("job_error", csv_rows[0])
        self.assertEqual(csv_rows[0]["fio_version_supported"], "True")
        self.assertEqual(csv_rows[0]["job_error"], "0")


if __name__ == "__main__":
    unittest.main()
