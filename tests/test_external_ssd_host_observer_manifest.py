from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "analysis"))

import build_external_ssd_run_manifest as builder  # noqa: E402


class HostObserverManifestTests(unittest.TestCase):
    def test_integrated_manifest_links_synchronized_host_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            result_root = root / "results" / "external_ssd"
            result_dir = result_root / "sustained_integrity_fixture"
            host_dir = result_dir / "host_observer"
            host_dir.mkdir(parents=True)

            fio = {
                "fio version": "fio-3.42",
                "jobs": [{
                    "error": 0,
                    "job options": {
                        "rw": "write",
                        "bs": "1M",
                        "iodepth": "4",
                        "direct": "1",
                        "numjobs": "1",
                        "size": "4G",
                    },
                    "read": {"io_bytes": 0, "runtime": 0},
                    "write": {
                        "io_bytes": 4 * 1024**3,
                        "runtime": 1000,
                        "iops": 100,
                        "bw_bytes": 100 * 1024**2,
                    },
                }],
            }
            fio_path = result_dir / "sustained_integrity_fixture_phase1_write.json"
            fio_path.write_text(json.dumps(fio), encoding="utf-8")
            for suffix in (
                "_bw.1.log",
                "_iops.1.log",
                "_clat.1.log",
                "_lat.1.log",
                "_slat.1.log",
            ):
                (result_dir / f"{fio_path.stem}{suffix}").write_text(
                    "0, 1, 0, 0\n", encoding="utf-8"
                )

            (result_dir / "runner_manifest.json").write_text(
                json.dumps({
                    "test_case_id": "EXT-DATA-INTEGRITY-001",
                    "experiment_id": "integrity_fixture",
                }),
                encoding="utf-8",
            )
            for phase in ("pre", "post"):
                (result_dir / f"observer_manifest_{phase}.json").write_text(
                    json.dumps({"status": "complete"}), encoding="utf-8"
                )
            (host_dir / "write_crc32c_manifest.json").write_text(
                json.dumps({"status": "complete", "phase": "write_crc32c"}),
                encoding="utf-8",
            )

            test_cases = [{
                "id": "EXT-DATA-INTEGRITY-001",
                "requirement_links": ["REQ-DATA-009", "REQ-HOST-OBS-010"],
            }]
            with (
                mock.patch.object(builder, "REPO_ROOT", root),
                mock.patch.object(builder, "RESULT_ROOT", result_root),
            ):
                manifest = builder.build_manifest(result_dir, test_cases)

            self.assertEqual(
                manifest["execution_model"]["synchronized_host_observer_status"],
                "present",
            )
            self.assertEqual(
                manifest["evidence_links"]["host_observer_manifests"],
                [
                    "results/external_ssd/sustained_integrity_fixture/"
                    "host_observer/write_crc32c_manifest.json"
                ],
            )


if __name__ == "__main__":
    unittest.main()
