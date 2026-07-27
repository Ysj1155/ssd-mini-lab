from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKER = (
    REPO_ROOT
    / "scripts"
    / "observers"
    / "check_external_ssd_dut_preflight.ps1"
)
IDENTITY_CONFIG = REPO_ROOT / "configs" / "external_ssd_dut_identity.json"
EVIDENCE = (
    REPO_ROOT
    / "results"
    / "external_ssd"
    / "dut_preflight_readonly_20260727"
    / "preflight.json"
)
NEGATIVE_EVIDENCE = EVIDENCE.with_name(
    "preflight_negative_size_mismatch.json"
)


class ExternalSsdPreflightEvidenceTests(unittest.TestCase):
    def test_checker_is_read_only_and_fail_closed(self) -> None:
        text = CHECKER.read_text(encoding="utf-8-sig")

        self.assertIn("Assert-ExternalSsdTarget", text)
        self.assertIn("-RequireExistingTarget", text)
        self.assertIn("-ExpectedFileBytes", text)
        self.assertIn('status = "Fail"', text)
        self.assertIn("exit 1", text)
        for forbidden in (
            "fio.exe",
            "New-Item",
            "Remove-Item",
            "SetLength",
            "Start-Process",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, text)

    def test_preserved_actual_dut_evidence_is_a_read_only_pass(self) -> None:
        evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        preflight = evidence["preflight"]
        identity = preflight["identity"]

        self.assertEqual(evidence["status"], "Pass")
        self.assertEqual(evidence["mode"], "read_only_existing_target")
        self.assertFalse(evidence["workload_invoked"])
        self.assertFalse(evidence["target_mutated"])
        self.assertEqual(evidence["expected_file_bytes"], 4_294_967_296)
        self.assertTrue(preflight["target_exists"])
        self.assertTrue(identity["identity_match"])
        self.assertFalse(identity["is_boot"])
        self.assertFalse(identity["is_system"])
        self.assertEqual(preflight["health_status"], "Healthy")
        self.assertIn("OK", preflight["operational_status"])
        self.assertNotIn("serial_number", EVIDENCE.read_text(encoding="utf-8"))

    def test_actual_size_mismatch_control_failed_closed(self) -> None:
        evidence = json.loads(
            NEGATIVE_EVIDENCE.read_text(encoding="utf-8")
        )

        self.assertEqual(evidence["status"], "Fail")
        self.assertEqual(evidence["test_role"], "negative_control")
        self.assertFalse(evidence["workload_invoked"])
        self.assertFalse(evidence["target_mutated"])
        self.assertIn("Target size mismatch", evidence["error"])

    def test_actual_identity_matches_enrollment(self) -> None:
        expected = json.loads(
            IDENTITY_CONFIG.read_text(encoding="utf-8")
        )["expected"]
        observed = json.loads(
            EVIDENCE.read_text(encoding="utf-8")
        )["preflight"]["identity"]

        for field in (
            "drive_letter",
            "file_system",
            "volume_label",
            "volume_unique_id",
            "size_bytes",
            "disk_friendly_name",
            "bus_type",
            "disk_fingerprint_sha256",
        ):
            with self.subTest(field=field):
                self.assertEqual(observed[field], expected[field])


if __name__ == "__main__":
    unittest.main()
