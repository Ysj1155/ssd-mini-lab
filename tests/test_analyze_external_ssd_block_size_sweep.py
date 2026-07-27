from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "analysis"))

import analyze_external_ssd_block_size_sweep as analyzer  # noqa: E402


def phase_row(
    phase: int,
    cycle: int,
    position: int,
    block_size: str,
    workload: str = "randread",
    bandwidth: float = 100.0,
) -> dict:
    return {
        "phase_order": phase,
        "cycle": cycle,
        "position": position,
        "workload": workload,
        "operation": "read" if workload == "randread" else "write",
        "block_size": block_size,
        "bandwidth_mib_s": bandwidth,
        "iops": bandwidth * 100,
        "clat_mean_ms": 1.0,
        "clat_p99_ms": 2.0,
        "clat_p999_ms": 3.0,
        "clat_max_ms": 4.0,
    }


class BlockSizeSweepAnalyzerTests(unittest.TestCase):
    def balanced_rows(self, workload: str = "randread") -> list[dict]:
        specs = [
            (1, 1, 1, "4k"),
            (2, 1, 2, "64k"),
            (3, 1, 3, "1m"),
            (4, 2, 1, "64k"),
            (5, 2, 2, "1m"),
            (6, 2, 3, "4k"),
            (7, 3, 1, "1m"),
            (8, 3, 2, "4k"),
            (9, 3, 3, "64k"),
        ]
        return [
            phase_row(
                phase,
                cycle,
                position,
                block_size,
                workload,
                bandwidth=100.0 * (analyzer.BLOCK_SIZE_ORDER[block_size] + 1),
            )
            for phase, cycle, position, block_size in specs
        ]

    def test_latin_square_balance_and_summary(self) -> None:
        rows = self.balanced_rows()

        analyzer.validate_balance(rows)
        summary = analyzer.summarize_block_sizes(rows)

        self.assertEqual(
            [row["block_size"] for row in summary],
            ["4k", "64k", "1m"],
        )
        self.assertTrue(all(row["repeat_count"] == 3 for row in summary))
        self.assertEqual(summary[0]["positions"], "1,3,2")
        self.assertAlmostEqual(summary[2]["bandwidth_mib_s_mean"], 300.0)

    def test_missing_position_is_rejected(self) -> None:
        rows = self.balanced_rows()
        rows[7]["position"] = 1

        with self.assertRaisesRegex(ValueError, "every position"):
            analyzer.validate_balance(rows)

    def test_cross_workload_ratios(self) -> None:
        read_summary = analyzer.summarize_block_sizes(self.balanced_rows("randread"))
        write_rows = self.balanced_rows("randwrite")
        for row in write_rows:
            row["bandwidth_mib_s"] *= 0.5
            row["iops"] *= 0.5
            row["clat_p99_ms"] *= 2
            row["clat_p999_ms"] *= 3
        write_summary = analyzer.summarize_block_sizes(write_rows)

        comparison = analyzer.compare_workloads(read_summary, write_summary)

        self.assertEqual(len(comparison), 3)
        self.assertTrue(
            all(row["write_over_read_bandwidth"] == 0.5 for row in comparison)
        )
        self.assertTrue(all(row["write_over_read_p99"] == 2.0 for row in comparison))
        self.assertTrue(all(row["write_over_read_p999"] == 3.0 for row in comparison))


    def test_fio_phase_direction_and_block_size_are_validated(self) -> None:
        run = {
            "phase_order": 1,
            "cycle": 1,
            "position": 1,
            "block_size": "64k",
            "fio_json": "phase1.json",
        }
        direction = {
            "io_bytes": 1024,
            "bw_bytes": 200 * 1024 * 1024,
            "iops": 3200,
            "clat_ns": {
                "mean": 1_000_000,
                "max": 4_000_000,
                "percentile": {
                    "99.000000": 2_000_000,
                    "99.900000": 3_000_000,
                },
            },
        }
        fio = {
            "fio version": "fio-3.42",
            "jobs": [{
                "error": 0,
                "job options": {"bs": "64k"},
                "read": direction,
                "write": {"io_bytes": 0},
            }],
        }

        row = analyzer.summarize_phase(run, fio, "randread")

        self.assertEqual(row["block_size"], "64k")
        self.assertEqual(row["operation"], "read")
        self.assertAlmostEqual(row["bandwidth_mib_s"], 200.0)
        self.assertAlmostEqual(row["clat_p999_ms"], 3.0)

        fio["jobs"][0]["write"]["io_bytes"] = 1
        with self.assertRaisesRegex(ValueError, "unexpected write"):
            analyzer.summarize_phase(run, fio, "randread")


if __name__ == "__main__":
    unittest.main()
