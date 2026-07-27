from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "analysis"))

import analyze_external_ssd_data_integrity as analyzer  # noqa: E402


def fio_result(
    operation: str,
    *,
    error: int = 0,
    io_bytes: int = analyzer.EXPECTED_BYTES,
    verify_errors: int | None = 0,
    verify_only: bool = False,
) -> dict:
    direction = "write" if operation == "write" else "read"
    job = {
        "error": error,
        "job options": {
            "verify": "crc32c",
            "verify_only": "1" if verify_only else "0",
            "do_verify": "1" if verify_only else "0",
        },
        "read": {"io_bytes": 0},
        "write": {"io_bytes": 0},
    }
    job[direction] = {
        "io_bytes": io_bytes,
        "bw_bytes": 100 * 1024**2,
        "iops": 100,
        "clat_ns": {
            "mean": 1_000_000,
            "max": 3_000_000,
            "percentile": {
                "99.000000": 2_000_000,
                "99.900000": 2_500_000,
            },
        },
    }
    if verify_errors is not None:
        job["verify_errors"] = verify_errors
    return {"fio version": "fio-3.42", "jobs": [job]}


def rows(
    *,
    write_error: int = 0,
    verify_error: int = 0,
    verify_errors: int | None = 0,
    verify_bytes: int = analyzer.EXPECTED_BYTES,
) -> list[dict]:
    return [
        analyzer.summarize_fio_phase(
            fio_result("write", error=write_error),
            phase_order=1,
            phase_name="write_crc32c",
            operation="write",
            source_json="write.json",
        ),
        analyzer.summarize_fio_phase(
            fio_result(
                "read",
                error=verify_error,
                io_bytes=verify_bytes,
                verify_errors=verify_errors,
                verify_only=True,
            ),
            phase_order=2,
            phase_name="verify_crc32c",
            operation="read_verify",
            source_json="verify.json",
        ),
    ]


class ExternalSsdDataIntegrityTests(unittest.TestCase):
    def test_complete_crc32c_write_and_verify_passes(self) -> None:
        verdict, failures = analyzer.evaluate_integrity(rows())

        self.assertEqual(verdict, "Pass")
        self.assertEqual(failures, [])

    def test_synthetic_verification_error_fails(self) -> None:
        verdict, failures = analyzer.evaluate_integrity(rows(verify_errors=1))

        self.assertEqual(verdict, "Fail")
        self.assertTrue(any("verification errors" in item for item in failures))

    def test_fio_job_error_fails(self) -> None:
        verdict, failures = analyzer.evaluate_integrity(rows(verify_error=84))

        self.assertEqual(verdict, "Fail")
        self.assertTrue(any("fio error 84" in item for item in failures))

    def test_short_verify_read_fails(self) -> None:
        verdict, failures = analyzer.evaluate_integrity(
            rows(verify_bytes=analyzer.EXPECTED_BYTES - 4096)
        )

        self.assertEqual(verdict, "Fail")
        self.assertTrue(any("processed" in item for item in failures))

    def test_missing_explicit_verify_error_counter_can_still_pass(self) -> None:
        verdict, failures = analyzer.evaluate_integrity(rows(verify_errors=None))

        self.assertEqual(verdict, "Pass")
        self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
