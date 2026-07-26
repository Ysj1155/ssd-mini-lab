from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "analysis"))

import analyze_external_ssd_idle_ramp as analyzer  # noqa: E402


class IdleRampAnalyzerTests(unittest.TestCase):
    def test_ramp_present_requires_late_transition_and_material_rise(self) -> None:
        self.assertTrue(analyzer.ramp_present({
            "transition_sec": 45,
            "plateau_over_first_third": 1.4,
        }))
        self.assertFalse(analyzer.ramp_present({
            "transition_sec": 1,
            "plateau_over_first_third": 1.4,
        }))
        self.assertFalse(analyzer.ramp_present({
            "transition_sec": 45,
            "plateau_over_first_third": 1.1,
        }))

    def test_symmetric_condition_summary_and_verdict(self) -> None:
        phase_rows = []
        transition_rows = []
        specs = [
            (1, 300, 1, 52),
            (2, 60, 1, 35),
            (3, 0, 1, 1),
            (4, 0, 2, 1),
            (5, 60, 2, 42),
            (6, 300, 2, 60),
        ]
        for phase, idle, replicate, transition in specs:
            phase_rows.append({
                "phase_order": phase,
                "total_bandwidth_mib_s": 180,
                "read_clat_p99_ms": 0.7,
                "read_clat_p999_ms": 1.2,
            })
            transition_rows.append({
                "phase_order": phase,
                "requested_pre_probe_idle_sec": idle,
                "condition_replicate": replicate,
                "actual_controlled_idle_sec": idle,
                "previous_fio_gap_sec": idle + 1,
                "transition_sec": transition,
                "plateau_over_first_third": 1.4 if idle else 1.0,
                "last_over_first_total_bandwidth": 1.4 if idle else 1.0,
            })

        conditions = analyzer.summarize_conditions(phase_rows, transition_rows)
        verdict = analyzer.build_verdict("idle_ramp_test", conditions)[0]

        self.assertEqual([row["requested_pre_probe_idle_sec"] for row in conditions], [0, 60, 300])
        self.assertTrue(all(row["pair_consistent"] for row in conditions))
        self.assertEqual(verdict["idle_0_ramp_present_count"], 0)
        self.assertEqual(verdict["idle_60_ramp_present_count"], 2)
        self.assertEqual(verdict["idle_300_ramp_present_count"], 2)
        self.assertEqual(
            verdict["performance_verdict"],
            "idle_duration_association_observed",
        )


    def test_inconsistent_idle_pair_blocks_positive_association(self) -> None:
        rows = [
            {
                "requested_pre_probe_idle_sec": idle,
                "pair_consistent": idle != 60,
                "ramp_present_count": count,
                "transition_sec_median_when_present": transition,
            }
            for idle, count, transition in (
                (0, 0, None),
                (60, 1, 35),
                (300, 2, 50),
            )
        ]

        verdict = analyzer.build_verdict("idle_ramp_test", rows)[0]

        self.assertEqual(verdict["pair_consistent_condition_count"], 2)
        self.assertEqual(
            verdict["performance_verdict"],
            "no_clear_idle_duration_association",
        )


if __name__ == "__main__":
    unittest.main()
