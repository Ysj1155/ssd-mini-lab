from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = (
    REPO_ROOT
    / "scripts"
    / "runners"
    / "run_external_ssd_data_integrity.ps1"
)


class ExternalSsdIntegrityRunnerContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.script = RUNNER.read_text(encoding="utf-8-sig")

    def test_runner_precreates_a_new_exact_length_file(self) -> None:
        self.assertIn("[System.IO.FileMode]::CreateNew", self.script)
        self.assertIn("$Stream.SetLength($ExpectedBytes)", self.script)
        self.assertIn(
            "Initialize-DedicatedVerificationFile\n"
            '    Invoke-StaticObserver -Phase "pre"',
            self.script,
        )

    def test_runner_refuses_an_existing_target(self) -> None:
        self.assertIn("$DutPreflight = Assert-ExternalSsdTarget", self.script)
        self.assertIn("-RequireNewTarget", self.script)

    def test_write_and_verify_contract_is_explicit(self) -> None:
        for option in (
            '"--verify=crc32c"',
            '"--verify_state_save=0"',
            '"--do_verify=0"',
            '"--overwrite=1"',
            '"--verify_only=1"',
            '"--do_verify=1"',
            '"--readonly"',
        ):
            with self.subTest(option=option):
                self.assertIn(option, self.script)


if __name__ == "__main__":
    unittest.main()
