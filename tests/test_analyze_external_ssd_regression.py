from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "analysis"))

import analyze_external_ssd_regression as analyzer  # noqa: E402


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def complete_index(profile: dict, root: Path) -> tuple[dict, dict[str, Path]]:
    components = []
    manifests: dict[str, Path] = {}
    for definition in profile["components"]:
        component_id = definition["id"]
        result_set = f"fixture_{component_id.lower()}"
        result_dir = root / "results" / component_id
        manifest_path = result_dir / "run_manifest.json"
        manifests[component_id] = manifest_path
        runs = []

        if definition["category"] == "integrity":
            option_sets = [
                {
                    "rw": "write",
                    "bs": definition["bs"],
                    "iodepth": str(definition["iodepth"]),
                    "size": definition["size"],
                    "verify": definition["verify"],
                    "do_verify": "0",
                },
                {
                    "rw": "read",
                    "bs": definition["bs"],
                    "iodepth": str(definition["iodepth"]),
                    "size": definition["size"],
                    "verify": definition["verify"],
                    "verify_only": "1",
                    "do_verify": "1",
                },
            ]
        else:
            option_sets = [
                {
                    "rw": definition["rw"],
                    "bs": definition["bs"],
                    "iodepth": str(definition["iodepth"]),
                    "runtime": str(definition["runtime_sec"]),
                }
                for _ in range(int(definition["repeats"]))
            ]

        for number, options in enumerate(option_sets, start=1):
            fio_path = result_dir / f"run{number}.json"
            write_json(
                fio_path,
                {
                    "jobs": [
                        {
                            "error": 0,
                            "job options": options,
                        }
                    ]
                },
            )
            runs.append({
                "run": number,
                "fio_json": relative(fio_path, root),
                "error": 0,
            })

        artifacts: dict[str, object] = {"raw_dir": relative(result_dir, root)}
        if definition["category"] != "integrity":
            summary_path = result_dir / "summary.csv"
            summary_rows = [
                {
                    "result_set": result_set,
                    "rw": definition["rw"],
                    "bs": definition["bs"],
                    "iodepth": definition["iodepth"],
                    "clat_p99_us": 100 + number,
                    "clat_p999_us": 200 + number,
                }
                for number in range(int(definition["repeats"]))
            ]
            write_csv(
                summary_path,
                [
                    "result_set",
                    "rw",
                    "bs",
                    "iodepth",
                    "clat_p99_us",
                    "clat_p999_us",
                ],
                summary_rows,
            )
            artifacts["summary_csv"] = relative(summary_path, root)

        if definition["category"] == "sustained_qos":
            timeseries = result_dir / "timeseries.csv"
            windows = result_dir / "windows.csv"
            write_csv(
                timeseries,
                ["result_set", "sec"],
                [{"result_set": result_set, "sec": 1}],
            )
            write_csv(
                windows,
                ["result_set", "window"],
                [{"result_set": result_set, "window": "first_third"}],
            )
            artifacts["timeseries_csv"] = relative(timeseries, root)
            artifacts["window_summary_csv"] = relative(windows, root)

        links: dict[str, object] = {}
        status = "complete"
        record = {
            "component_id": component_id,
            "evidence_status": "complete",
            "source_manifest": relative(manifest_path, root),
        }
        if definition["category"] == "integrity":
            status = "limited"
            record.update({
                "evidence_status": "limited",
                "integrity_verdict": "Pass",
                "host_observer_status": "limited",
            })
            analysis_path = result_dir / "analysis_manifest.json"
            write_json(
                analysis_path,
                {
                    "test_protocol_id": definition["source_test_case"],
                    "status": "complete",
                    "integrity_verdict": "Pass",
                    "host_observers": [{"phase": "write", "status": "limited"}],
                },
            )
            links["analysis_manifest"] = relative(analysis_path, root)
        else:
            record.update({
                "performance_verdict": "Observation",
                "qos_verdict": "Observation",
            })

        write_json(
            manifest_path,
            {
                "schema_version": "1.0",
                "run_id": result_set,
                "result_set": result_set,
                "test_case_id": definition["source_test_case"],
                "status": status,
                "evidence_links": links,
                "artifacts": artifacts,
                "runs": runs,
            },
        )
        components.append(record)

    return {
        "profile_id": profile["profile_id"],
        "run_id": "regression_contract_fixture",
        "components": components,
    }, manifests


class ExternalSsdRegressionContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.profile = analyzer.load_profile()

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.temp_dir.name)
        self.evidence, self.manifests = complete_index(
            self.profile,
            self.repo_root,
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def evaluate(self, evidence: dict | None = None):
        return analyzer.evaluate_profile(
            self.profile,
            evidence or self.evidence,
            repo_root=self.repo_root,
        )

    def test_profile_declares_expected_compact_components_and_policy(self) -> None:
        self.assertEqual(self.profile["profile_id"], "EXT-REGRESSION-COMPACT-001")
        self.assertEqual(self.profile["requirement_id"], "REQ-REG-011")
        self.assertEqual(len(self.profile["components"]), 8)
        self.assertEqual(
            {item["category"] for item in self.profile["components"]},
            {"performance", "sustained_qos", "integrity"},
        )
        self.assertEqual(
            self.profile["verdict_policy"]["release_precedence"],
            ["Fail", "Blocked", "Review", "Observation", "Pass"],
        )

    def test_verified_observation_keeps_integrity_and_host_status_separate(
        self,
    ) -> None:
        verdict, rows = self.evaluate()

        self.assertEqual(len(rows), 8)
        self.assertEqual(verdict["integrity_verdict"], "Pass")
        self.assertEqual(verdict["host_observer_status"], "limited")
        self.assertEqual(verdict["evidence_status"], "limited")
        self.assertEqual(verdict["release_verdict"], "Observation")

    def test_integrity_failure_is_read_from_analysis_manifest(self) -> None:
        evidence = deepcopy(self.evidence)
        integrity = next(
            item
            for item in evidence["components"]
            if item["component_id"] == "REG-DATA-CRC32C-4G"
        )
        integrity["integrity_verdict"] = "Fail"
        manifest = json.loads(
            self.manifests["REG-DATA-CRC32C-4G"].read_text(encoding="utf-8")
        )
        analysis_path = self.repo_root / manifest["evidence_links"]["analysis_manifest"]
        analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
        analysis["integrity_verdict"] = "Fail"
        write_json(analysis_path, analysis)

        verdict, _ = self.evaluate(evidence)

        self.assertEqual(verdict["integrity_verdict"], "Fail")
        self.assertEqual(verdict["release_verdict"], "Fail")

    def test_missing_component_blocks_the_profile(self) -> None:
        evidence = deepcopy(self.evidence)
        evidence["components"].pop()

        verdict, rows = self.evaluate(evidence)

        self.assertEqual(verdict["evidence_status"], "blocked")
        self.assertEqual(verdict["release_verdict"], "Blocked")
        self.assertTrue(any(row["evidence_status"] == "blocked" for row in rows))

    def test_performance_regression_requires_review(self) -> None:
        evidence = deepcopy(self.evidence)
        evidence["components"][0]["performance_verdict"] = "Regression"

        verdict, _ = self.evaluate(evidence)

        self.assertEqual(verdict["performance_verdict"], "Regression")
        self.assertEqual(verdict["release_verdict"], "Review")

    def test_missing_run_id_is_rejected(self) -> None:
        evidence = deepcopy(self.evidence)
        evidence.pop("run_id")

        with self.assertRaisesRegex(
            analyzer.RegressionContractError,
            "run_id is required",
        ):
            self.evaluate(evidence)

    def test_nonexistent_source_manifest_is_rejected(self) -> None:
        evidence = deepcopy(self.evidence)
        evidence["components"][0]["source_manifest"] = "missing/run_manifest.json"

        with self.assertRaisesRegex(
            analyzer.RegressionContractError,
            "does not exist",
        ):
            self.evaluate(evidence)

    def test_source_manifest_cannot_escape_repository(self) -> None:
        evidence = deepcopy(self.evidence)
        evidence["components"][0]["source_manifest"] = "../run_manifest.json"

        with self.assertRaisesRegex(
            analyzer.RegressionContractError,
            "escapes the repository",
        ):
            self.evaluate(evidence)

    def test_source_test_case_mismatch_is_rejected(self) -> None:
        first_id = self.evidence["components"][0]["component_id"]
        manifest_path = self.manifests[first_id]
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["test_case_id"] = "WRONG-TEST-CASE"
        write_json(manifest_path, manifest)

        with self.assertRaisesRegex(
            analyzer.RegressionContractError,
            "test_case_id does not match",
        ):
            self.evaluate()

    def test_index_cannot_upgrade_limited_manifest_to_complete(self) -> None:
        first_id = self.evidence["components"][0]["component_id"]
        manifest_path = self.manifests[first_id]
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["status"] = "limited"
        write_json(manifest_path, manifest)

        with self.assertRaisesRegex(
            analyzer.RegressionContractError,
            "cannot upgrade source status",
        ):
            self.evaluate()

    def test_missing_required_summary_is_rejected(self) -> None:
        first_id = self.evidence["components"][0]["component_id"]
        manifest_path = self.manifests[first_id]
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["artifacts"]["summary_csv"] = "missing/summary.csv"
        write_json(manifest_path, manifest)

        with self.assertRaisesRegex(
            analyzer.RegressionContractError,
            "summary_csv does not exist",
        ):
            self.evaluate()

    def test_manual_pass_is_invalid_in_observation_mode(self) -> None:
        evidence = deepcopy(self.evidence)
        evidence["components"][0]["performance_verdict"] = "Pass"
        evidence["components"][0]["qos_verdict"] = "Pass"

        with self.assertRaisesRegex(
            analyzer.RegressionContractError,
            "Pass is invalid",
        ):
            self.evaluate(evidence)

    def test_integrity_verdict_must_match_analysis_manifest(self) -> None:
        evidence = deepcopy(self.evidence)
        integrity = next(
            item
            for item in evidence["components"]
            if item["component_id"] == "REG-DATA-CRC32C-4G"
        )
        integrity["integrity_verdict"] = "Fail"

        with self.assertRaisesRegex(
            analyzer.RegressionContractError,
            "does not match analysis_manifest",
        ):
            self.evaluate(evidence)

    def test_fio_job_options_must_match_component_condition(self) -> None:
        first_id = self.evidence["components"][0]["component_id"]
        manifest = json.loads(
            self.manifests[first_id].read_text(encoding="utf-8")
        )
        fio_path = self.repo_root / manifest["runs"][0]["fio_json"]
        fio = json.loads(fio_path.read_text(encoding="utf-8"))
        fio["jobs"][0]["job options"]["bs"] = "8k"
        write_json(fio_path, fio)

        with self.assertRaisesRegex(
            analyzer.RegressionContractError,
            "matching fio_json records",
        ):
            self.evaluate()

    def test_host_observer_gating_blocks_without_overwriting_integrity(self) -> None:
        gated_profile = deepcopy(self.profile)
        integrity = next(
            item
            for item in gated_profile["components"]
            if item["id"] == "REG-DATA-CRC32C-4G"
        )
        integrity["host_observer_gating"] = True

        verdict, _ = analyzer.evaluate_profile(
            gated_profile,
            self.evidence,
            repo_root=self.repo_root,
        )

        self.assertEqual(verdict["integrity_verdict"], "Pass")
        self.assertEqual(verdict["host_observer_status"], "limited")
        self.assertEqual(verdict["evidence_status"], "blocked")
        self.assertEqual(verdict["release_verdict"], "Blocked")

    def test_errored_fio_cannot_support_successful_evidence(self) -> None:
        first_id = self.evidence["components"][0]["component_id"]
        manifest_path = self.manifests[first_id]
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["runs"][0]["error"] = 5
        write_json(manifest_path, manifest)
        fio_path = self.repo_root / manifest["runs"][0]["fio_json"]
        fio = json.loads(fio_path.read_text(encoding="utf-8"))
        fio["jobs"][0]["error"] = 5
        write_json(fio_path, fio)

        with self.assertRaisesRegex(
            analyzer.RegressionContractError,
            "errored fio evidence",
        ):
            self.evaluate()




if __name__ == "__main__":
    unittest.main()
