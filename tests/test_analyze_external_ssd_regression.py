from __future__ import annotations

import sys
import unittest
from copy import deepcopy
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "analysis"))

import analyze_external_ssd_regression as analyzer  # noqa: E402


def complete_index(profile: dict) -> dict:
    components = []
    for definition in profile["components"]:
        record = {
            "component_id": definition["id"],
            "evidence_status": "complete",
            "source_manifest": f"results/{definition['id']}/run_manifest.json",
        }
        if definition["category"] == "integrity":
            record.update({
                "integrity_verdict": "Pass",
                "host_observer_status": "limited",
            })
        else:
            record.update({
                "performance_verdict": "Observation",
                "qos_verdict": "Observation",
            })
        components.append(record)
    return {
        "profile_id": profile["profile_id"],
        "run_id": "regression_contract_fixture",
        "components": components,
    }


class ExternalSsdRegressionContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.profile = analyzer.load_profile()

    def test_profile_declares_expected_compact_components(self) -> None:
        self.assertEqual(self.profile["profile_id"], "EXT-REGRESSION-COMPACT-001")
        self.assertEqual(self.profile["requirement_id"], "REQ-REG-011")
        self.assertEqual(len(self.profile["components"]), 8)
        self.assertEqual(
            {item["category"] for item in self.profile["components"]},
            {"performance", "sustained_qos", "integrity"},
        )

    def test_observation_profile_keeps_integrity_and_host_status_separate(self) -> None:
        verdict, rows = analyzer.evaluate_profile(
            self.profile,
            complete_index(self.profile),
        )

        self.assertEqual(len(rows), 8)
        self.assertEqual(verdict["integrity_verdict"], "Pass")
        self.assertEqual(verdict["host_observer_status"], "limited")
        self.assertEqual(verdict["evidence_status"], "limited")
        self.assertEqual(verdict["release_verdict"], "Observation")

    def test_integrity_failure_is_a_release_failure(self) -> None:
        evidence = complete_index(self.profile)
        integrity = next(
            item
            for item in evidence["components"]
            if item["component_id"] == "REG-DATA-CRC32C-4G"
        )
        integrity["integrity_verdict"] = "Fail"

        verdict, _ = analyzer.evaluate_profile(self.profile, evidence)

        self.assertEqual(verdict["integrity_verdict"], "Fail")
        self.assertEqual(verdict["release_verdict"], "Fail")

    def test_missing_component_blocks_the_profile(self) -> None:
        evidence = complete_index(self.profile)
        evidence["components"].pop()

        verdict, rows = analyzer.evaluate_profile(self.profile, evidence)

        self.assertEqual(verdict["evidence_status"], "blocked")
        self.assertEqual(verdict["release_verdict"], "Blocked")
        self.assertTrue(any(row["evidence_status"] == "blocked" for row in rows))

    def test_performance_regression_requires_review(self) -> None:
        evidence = complete_index(self.profile)
        changed = deepcopy(evidence)
        changed["components"][0]["performance_verdict"] = "Regression"

        verdict, _ = analyzer.evaluate_profile(self.profile, changed)

        self.assertEqual(verdict["performance_verdict"], "Regression")
        self.assertEqual(verdict["release_verdict"], "Review")


if __name__ == "__main__":
    unittest.main()
