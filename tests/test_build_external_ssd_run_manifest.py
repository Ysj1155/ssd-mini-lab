from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "analysis"))

import build_external_ssd_run_manifest as builder  # noqa: E402


class ExternalSsdRunManifestTests(unittest.TestCase):
    def test_run_number_filename_remains_supported(self) -> None:
        path = Path("sustained_rand_write_qd16_run3.json")

        self.assertEqual(builder.extract_run(path), 3)
        self.assertTrue(builder.is_fio_run_json(path))

    def test_phase_number_filename_is_supported(self) -> None:
        path = Path("sustained_idle_ramp_phase6_A2_idle300.json")

        self.assertEqual(builder.extract_run(path), 6)
        self.assertTrue(builder.is_fio_run_json(path))

    def test_manifest_json_is_not_misclassified_as_fio(self) -> None:
        for name in (
            "runner_manifest.json",
            "observer_manifest_pre.json",
            "run_manifest.json",
        ):
            with self.subTest(name=name):
                self.assertIsNone(builder.extract_run(Path(name)))
                self.assertFalse(builder.is_fio_run_json(Path(name)))


if __name__ == "__main__":
    unittest.main()
