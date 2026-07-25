from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "analysis"))

import analyze_external_ssd_mixed_ratio_sweep as analyzer  # noqa: E402


def direction(io_bytes: int, bw_bytes: int, p99: int, p999: int, maximum: int) -> dict:
    return {
        "io_bytes": io_bytes,
        "bw_bytes": bw_bytes,
        "iops": bw_bytes / 4096,
        "clat_ns": {
            "mean": 250_000,
            "max": maximum,
            "percentile": {
                "99.000000": p99,
                "99.900000": p999,
            },
        },
    }


class MixedRatioSweepAnalyzerTests(unittest.TestCase):
    def test_summarize_phase_preserves_directional_qos(self) -> None:
        run = {
            "phase_order": 1,
            "cycle": 1,
            "position": 1,
            "ratio": "70:30",
            "read_pct": 70,
            "write_pct": 30,
            "fio_json": "phase1.json",
        }
        fio = {
            "fio version": "fio-3.42",
            "jobs": [{
                "error": 0,
                "read": direction(700, 70 * 1024 * 1024, 600_000, 900_000, 2_000_000),
                "write": direction(300, 30 * 1024 * 1024, 500_000, 800_000, 1_500_000),
            }],
        }

        row = analyzer.summarize_phase(run, fio)

        self.assertAlmostEqual(row["observed_read_pct"], 70.0)
        self.assertAlmostEqual(row["total_bandwidth_mib_s"], 100.0)
        self.assertAlmostEqual(row["read_clat_p99_ms"], 0.6)
        self.assertAlmostEqual(row["write_clat_p999_ms"], 0.8)

    def test_summarize_windows_splits_runtime_into_thirds(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            prefix = Path(tmpdir) / "phase1"
            bw_lines = []
            clat_lines = []
            for second in range(1, 7):
                read_bw = 1024 * second
                write_bw = 512 * second
                bw_lines.extend([
                    f"{second * 1000}, {read_bw}, 0, 0, 0",
                    f"{second * 1000}, {write_bw}, 1, 0, 0",
                ])
                clat_lines.extend([
                    f"{second * 1000}, {second * 100000}, 0, 0, 0",
                    f"{second * 1000}, {second * 200000}, 1, 0, 0",
                ])
            Path(f"{prefix}_bw.1.log").write_text("\n".join(bw_lines), encoding="utf-8")
            Path(f"{prefix}_clat.1.log").write_text("\n".join(clat_lines), encoding="utf-8")
            run = {
                "phase_order": 1,
                "cycle": 1,
                "position": 1,
                "ratio": "70:30",
                "log_prefix": str(prefix),
            }

            rows = analyzer.summarize_windows(run, runtime_sec=6)

        self.assertEqual([row["window"] for row in rows], ["first", "middle", "last"])
        self.assertAlmostEqual(rows[0]["read_bandwidth_mib_s"], 1.5)
        self.assertAlmostEqual(rows[2]["read_bandwidth_mib_s"], 5.5)
        self.assertAlmostEqual(rows[2]["read_clat_mean_ms"], 0.55)

    def test_detect_anomalies_flags_late_drop_and_maximum(self) -> None:
        phase_rows = [{
            "phase_order": 5,
            "cycle": 2,
            "position": 2,
            "ratio": "50:50",
            "read_clat_max_ms": 120.0,
            "write_clat_max_ms": 100.0,
        }]
        window_rows = [
            {"phase_order": 5, "window": "first", "total_bandwidth_mib_s": 100.0},
            {"phase_order": 5, "window": "middle", "total_bandwidth_mib_s": 90.0},
            {"phase_order": 5, "window": "last", "total_bandwidth_mib_s": 50.0},
        ]

        rows = analyzer.detect_anomalies(phase_rows, window_rows)

        self.assertEqual(
            {row["anomaly_type"] for row in rows},
            {"late_bandwidth_drop", "maximum_latency_outlier"},
        )


    def test_transition_summary_finds_first_five_second_plateau_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            prefix = Path(tmpdir) / "phase1"
            lines = []
            for second in range(1, 13):
                total_kib = 20 if second <= 4 else 100
                lines.extend([
                    f"{second * 1000}, {total_kib * 0.7}, 0, 0, 0",
                    f"{second * 1000}, {total_kib * 0.3}, 1, 0, 0",
                ])
            Path(f"{prefix}_bw.1.log").write_text("\n".join(lines), encoding="utf-8")
            run = {
                "phase_order": 1,
                "cycle": 1,
                "position": 1,
                "ratio": "70:30",
                "log_prefix": str(prefix),
            }

            row = analyzer.summarize_transition(run, runtime_sec=12)

        self.assertTrue(row["transition_found"])
        self.assertAlmostEqual(row["plateau_bandwidth_mib_s"], 100 / 1024)
        self.assertAlmostEqual(row["transition_sec"], 5.0)
        self.assertAlmostEqual(row["plateau_over_first_third"], 5.0)

    def test_cross_session_verdict_detects_direction_disagreement(self) -> None:
        def ratio_row(ratio: str, bandwidth: float, p99: float) -> dict:
            return {
                "ratio": ratio,
                "total_bandwidth_mib_s_mean": bandwidth,
                "total_bandwidth_mib_s_cv": 0.1,
                "read_clat_p99_ms_mean": p99,
                "read_clat_p999_ms_mean": p99 * 2,
            }

        def dimension_rows(order: list[int]) -> list[dict]:
            rows = []
            for dimension in ("cycle", "position"):
                rows.extend(
                    {
                        "dimension": dimension,
                        "level": str(level),
                        "total_bandwidth_mib_s_mean": value,
                    }
                    for level, value in zip((1, 2, 3), order)
                )
            return rows

        def phase_rows(total: float, p99: float) -> list[dict]:
            return [
                {
                    "total_bandwidth_mib_s": total,
                    "read_clat_p99_ms": p99,
                    "read_clat_p999_ms": p99 * 2,
                }
                for _ in range(3)
            ]

        session1 = {
            "experiment_id": "session1",
            "ratio_rows": [
                ratio_row("90:10", 110, 3.0),
                ratio_row("70:30", 130, 2.0),
                ratio_row("50:50", 100, 2.5),
            ],
            "dimension_rows": dimension_rows([100, 110, 120]),
            "transition_rows": [{
                "phase_order": "5",
                "ratio": "50:50",
                "transition_sec": "1",
                "plateau_over_first_third": "0.5",
                "last_over_first_total_bandwidth": "0.5",
            }],
            "phase_rows": phase_rows(110, 2.5),
        }
        session2 = {
            "experiment_id": "session2",
            "ratio_rows": [
                ratio_row("90:10", 190, 0.6),
                ratio_row("70:30", 180, 0.7),
                ratio_row("50:50", 170, 0.8),
            ],
            "dimension_rows": dimension_rows([120, 110, 100]),
            "transition_rows": [{
                "phase_order": "5",
                "ratio": "90:10",
                "transition_sec": "45",
                "plateau_over_first_third": "1.4",
                "last_over_first_total_bandwidth": "1.4",
            }],
            "phase_rows": phase_rows(180, 0.7),
        }

        comparisons, verdicts = analyzer.cross_session_evidence(session1, session2)

        self.assertEqual(len(comparisons), 3)
        verdict = verdicts[0]
        self.assertFalse(verdict["bandwidth_rank_reproduced"])
        self.assertFalse(verdict["read_p99_rank_reproduced"])
        self.assertFalse(verdict["ramp_pattern_reproduced"])
        self.assertFalse(verdict["cycle_rank_reproduced"])
        self.assertFalse(verdict["position_rank_reproduced"])
        self.assertFalse(verdict["phase5_direction_reproduced"])
        self.assertEqual(verdict["session1_phase5_direction"], "drop")
        self.assertEqual(verdict["session2_phase5_direction"], "rise")
        self.assertEqual(
            verdict["performance_verdict"],
            "not_reproduced_across_independent_counterbalanced_sessions",
        )


if __name__ == "__main__":
    unittest.main()
