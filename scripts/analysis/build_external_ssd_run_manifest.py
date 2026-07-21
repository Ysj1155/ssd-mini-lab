r"""
scripts/analysis/build_external_ssd_run_manifest.py

Purpose:
    Build traceable run_manifest.json files for external SSD fio result sets.

The manifest connects one validation result set to its DUT, requirement IDs,
YAML test case, fio conditions, raw artifacts, parsed CSVs, environment snapshot,
telemetry snapshot, and interpretation boundary.

Usage:
    cd D:\ssd_lab
    python .\scripts\analysis\build_external_ssd_run_manifest.py --all
    python .\scripts\analysis\build_external_ssd_run_manifest.py --result-set sustained_rand_write_300s_qd32_repeat3
"""

from __future__ import annotations

import argparse
import json
import platform
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
RESULT_ROOT = REPO_ROOT / "results" / "external_ssd"
MATRIX_PATH = REPO_ROOT / "configs" / "external_ssd_validation_matrix.yaml"
DUT_PROFILE = REPO_ROOT / "docs" / "reports" / "external_ssd_dut_profile.md"
REQUIREMENT_MATRIX = REPO_ROOT / "docs" / "reports" / "external_ssd_requirement_matrix.md"
PRODUCT_REPORT = REPO_ROOT / "docs" / "reports" / "external_ssd_product_validation.md"
ENV_MANIFEST = REPO_ROOT / "results" / "env" / "latest" / "manifest.json"
TELEMETRY_MANIFEST = REPO_ROOT / "results" / "telemetry" / "latest" / "manifest.json"
INTERPRETATION_BOUNDARY = "USB, Windows, exFAT file-target result; not internal FTL/GC proof"


class ManifestError(RuntimeError):
    pass


def rel(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def read_fio_json(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8-sig")
    start = text.find("{")
    if start == -1:
        raise ManifestError(f"No JSON object found in {path}")
    return json.loads(text[start:])


def extract_run(path: Path) -> int | None:
    match = re.search(r"run(\d+)", path.stem, re.IGNORECASE)
    return int(match.group(1)) if match else None


def scalar_value(value: str) -> Any:
    value = value.strip().strip('"').strip("'")
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    if value.startswith("[") and value.endswith("]"):
        items = [item.strip() for item in value[1:-1].split(",") if item.strip()]
        return [scalar_value(item) for item in items]
    return value


def load_test_cases(path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    in_requirements = False

    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if stripped.startswith("- id:"):
            if current:
                cases.append(current)
            current = {"id": stripped.split(":", 1)[1].strip(), "requirement_links": []}
            in_requirements = False
            continue

        if current is None:
            continue

        if stripped == "requirement_links:":
            in_requirements = True
            continue

        if in_requirements and stripped.startswith("-"):
            current.setdefault("requirement_links", []).append(stripped[1:].strip())
            continue

        in_requirements = False
        if ":" in stripped:
            key, value = stripped.split(":", 1)
            current[key.strip()] = scalar_value(value)

    if current:
        cases.append(current)

    return cases


def select_io_section(job: dict[str, Any], rw: str | None) -> tuple[str, dict[str, Any]]:
    if rw and "read" in rw.lower() and "write" not in rw.lower():
        candidates = ["read", "write"]
    elif rw and "write" in rw.lower() and "read" not in rw.lower():
        candidates = ["write", "read"]
    else:
        candidates = ["read", "write"]

    for operation in candidates:
        section = job.get(operation, {})
        if section.get("iops") or section.get("bw_bytes") or section.get("io_bytes"):
            return operation, section
    return candidates[0], job.get(candidates[0], {})


def normalize_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def find_test_case(
    cases: list[dict[str, Any]], rw: str | None, bs: str | None, iodepth: int | None, runtime_sec: int | None, size: str | None
) -> dict[str, Any] | None:
    matches: list[dict[str, Any]] = []
    for case in cases:
        case_qds = case.get("iodepth")
        if not isinstance(case_qds, list):
            case_qds = [case_qds]
        if (
            case.get("rw") == rw
            and str(case.get("bs")) == str(bs)
            and str(case.get("size")) == str(size)
            and normalize_int(case.get("runtime_sec")) == runtime_sec
            and iodepth in [normalize_int(qd) for qd in case_qds]
        ):
            matches.append(case)

    if not matches:
        return None

    exact_qd_matches = [case for case in matches if normalize_int(case.get("iodepth", [None])[0] if isinstance(case.get("iodepth"), list) else case.get("iodepth")) == iodepth]
    return exact_qd_matches[0] if exact_qd_matches else matches[0]


def is_fio_run_json(path: Path) -> bool:
    return bool(re.search(r"run\d+", path.stem, re.IGNORECASE))


def result_dirs(result_root: Path) -> list[Path]:
    return sorted(
        path
        for path in result_root.iterdir()
        if path.is_dir()
        and path.name.startswith("sustained_")
        and any(is_fio_run_json(json_path) for json_path in path.glob("*.json"))
    )

def log_artifacts_for_json(json_path: Path) -> dict[str, str | None]:
    stem = json_path.stem
    suffixes = {
        "bw_log": "_bw.1.log",
        "iops_log": "_iops.1.log",
        "clat_log": "_clat.1.log",
        "lat_log": "_lat.1.log",
        "slat_log": "_slat.1.log",
    }
    artifacts: dict[str, str | None] = {}
    for key, suffix in suffixes.items():
        candidate = json_path.parent / f"{stem}{suffix}"
        artifacts[key] = rel(candidate) if candidate.exists() else None
    return artifacts


def build_manifest(result_dir: Path, test_cases: list[dict[str, Any]]) -> dict[str, Any]:
    json_paths = sorted(
        (path for path in result_dir.glob("*.json") if is_fio_run_json(path)),
        key=lambda path: (extract_run(path) or 0, path.name),
    )
    runner_manifest_path = result_dir / "runner_manifest.json"
    observer_manifest_paths = sorted(result_dir.glob("observer_manifest_*.json"))
    observer_phases = {
        path.stem.removeprefix("observer_manifest_")
        for path in observer_manifest_paths
    }
    if not json_paths:
        raise ManifestError(f"No fio JSON files found in {result_dir}")

    first = read_fio_json(json_paths[0])
    first_job = first.get("jobs", [{}])[0]
    opts = first_job.get("job options", {})
    rw = opts.get("rw")
    operation, first_io = select_io_section(first_job, rw)
    runtime_sec = round(float(first_io.get("runtime", 0)) / 1000.0)
    iodepth = normalize_int(opts.get("iodepth"))
    direct = normalize_int(opts.get("direct"))
    numjobs = normalize_int(opts.get("numjobs")) or 1
    bs = opts.get("bs")
    size = opts.get("size")
    test_case = find_test_case(test_cases, rw, bs, iodepth, runtime_sec, size)

    runs: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    missing_artifacts: list[dict[str, Any]] = []
    fio_versions: set[str] = set()
    traceability_gaps: list[dict[str, Any]] = []

    if not runner_manifest_path.exists():
        traceability_gaps.append({"type": "missing_runner_manifest", "expected": rel(runner_manifest_path)})
    for required_phase in ("pre", "post"):
        if required_phase not in observer_phases:
            traceability_gaps.append(
                {
                    "type": "missing_observer_manifest",
                    "phase": required_phase,
                    "expected": rel(result_dir / f"observer_manifest_{required_phase}.json"),
                }
            )

    for json_path in json_paths:
        data = read_fio_json(json_path)
        job = data.get("jobs", [{}])[0]
        run_no = extract_run(json_path)
        error = job.get("error")
        if error not in (0, None):
            errors.append({"run": run_no, "error": error, "file": rel(json_path)})
        if data.get("fio version"):
            fio_versions.add(data["fio version"])
        logs = log_artifacts_for_json(json_path)
        missing = [name for name, path in logs.items() if path is None]
        if missing:
            missing_artifacts.append({"run": run_no, "missing": missing, "file": rel(json_path)})
        runs.append(
            {
                "run": run_no,
                "fio_json": rel(json_path),
                "error": error,
                "artifacts": logs,
            }
        )

    expected_repeats = normalize_int(test_case.get("repeats")) if test_case else None
    status = "complete"
    if expected_repeats and len(json_paths) < expected_repeats:
        status = "incomplete"
    elif errors or missing_artifacts or test_case is None or traceability_gaps:
        status = "limited"

    anomalies: list[dict[str, Any]] = []
    if errors:
        anomalies.append({"type": "fio_error", "details": errors})
    if missing_artifacts:
        anomalies.append({"type": "missing_artifact", "details": missing_artifacts})
    if test_case is None:
        anomalies.append({"type": "unmatched_test_case", "details": "No YAML test case matched observed fio conditions."})
    if traceability_gaps:
        anomalies.append({"type": "missing_execution_evidence", "details": traceability_gaps})

    manifest = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator": "scripts/analysis/build_external_ssd_run_manifest.py",
        "run_id": result_dir.name,
        "result_set": result_dir.name,
        "test_case_id": test_case.get("id") if test_case else None,
        "requirement_ids": test_case.get("requirement_links", []) if test_case else [],
        "dut_id": "external_ssd_dut_01",
        "status": status,
        "result": "observation",
        "tool_versions": {
            "fio": sorted(fio_versions),
            "python": platform.python_version(),
        },
        "conditions": {
            "operation": operation,
            "rw": rw,
            "bs": bs,
            "iodepth": iodepth,
            "runtime_sec": runtime_sec,
            "size": size,
            "direct": direct,
            "numjobs": numjobs,
        },
        "evidence_links": {
            "dut_profile": rel(DUT_PROFILE) if DUT_PROFILE.exists() else None,
            "requirement_matrix": rel(REQUIREMENT_MATRIX) if REQUIREMENT_MATRIX.exists() else None,
            "validation_matrix": rel(MATRIX_PATH) if MATRIX_PATH.exists() else None,
            "product_report": rel(PRODUCT_REPORT) if PRODUCT_REPORT.exists() else None,
            "runner_manifest": rel(runner_manifest_path) if runner_manifest_path.exists() else None,
            "observer_manifests": [rel(path) for path in observer_manifest_paths],
            "snapshot_scope": "run-specific environment and telemetry outputs are referenced by observer manifests",
        },
        "execution_model": {
            "runner_observer_separation": "fio runner and read-only observer evidence are recorded as separate artifacts and connected by run_id",
            "runner_status": "present" if runner_manifest_path.exists() else "missing",
            "observer_status": (
                "complete"
                if {"pre", "post"}.issubset(observer_phases)
                else "incomplete"
            ),
        },
        "artifacts": {
            "raw_dir": rel(result_dir),
            "summary_csv": rel(REPO_ROOT / "results" / "external_ssd_sustained_summary.csv"),
            "timeseries_csv": rel(REPO_ROOT / "results" / "external_ssd_sustained_timeseries.csv"),
            "window_summary_csv": rel(REPO_ROOT / "results" / "external_ssd_sustained_window_summary.csv"),
            "repeatability_csv": rel(REPO_ROOT / "results" / "external_ssd_sustained_repeatability.csv"),
        },
        "runs": runs,
        "anomalies": anomalies,
        "interpretation_boundary": INTERPRETATION_BOUNDARY,
    }
    return manifest

def write_manifest(result_dir: Path, manifest: dict[str, Any], dry_run: bool) -> None:
    manifest_path = result_dir / "run_manifest.json"
    if dry_run:
        print(json.dumps(manifest, indent=2, ensure_ascii=False))
        return
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[OK] Saved {rel(manifest_path)} status={manifest['status']} test_case={manifest['test_case_id']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build external SSD run_manifest.json files.")
    parser.add_argument("--result-set", help="Result-set directory name under results/external_ssd.")
    parser.add_argument("--all", action="store_true", help="Build manifests for all sustained result sets.")
    parser.add_argument("--dry-run", action="store_true", help="Print manifest JSON instead of writing files.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.all and not args.result_set:
        raise SystemExit("Use --all or --result-set <name>.")

    test_cases = load_test_cases(MATRIX_PATH)
    targets = result_dirs(RESULT_ROOT) if args.all else [RESULT_ROOT / args.result_set]

    for target in targets:
        if not target.exists():
            raise SystemExit(f"Result set not found: {target}")
        manifest = build_manifest(target, test_cases)
        write_manifest(target, manifest, args.dry_run)


if __name__ == "__main__":
    main()