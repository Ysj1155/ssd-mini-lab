"""Analyze the EXT-DATA-INTEGRITY-001 file-target write/verify experiment."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
RESULT_ROOT = REPO_ROOT / "results" / "external_ssd"
EXPERIMENT_ROOT = RESULT_ROOT / "_experiments"
EXPECTED_BYTES = 4 * 1024**3
PERCENTILES = {"p99": "99.000000", "p999": "99.900000"}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"No rows to write: {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def relative(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def option_enabled(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def percentile_ms(direction: dict[str, Any], key: str) -> float | None:
    percentile = (direction.get("clat_ns") or {}).get("percentile") or {}
    value = percentile.get(PERCENTILES[key])
    return None if value is None else float(value) / 1_000_000.0


def extract_verify_errors(job: dict[str, Any]) -> tuple[int, bool]:
    """Return the sum of explicit verify-error fields and whether one existed."""
    values: list[int] = []

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key.lower() in {"verify_errors", "verify_error"}:
                    try:
                        values.append(int(child))
                    except (TypeError, ValueError):
                        values.append(1)
                else:
                    visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(job)
    return sum(values), bool(values)


def summarize_fio_phase(
    fio: dict[str, Any],
    *,
    phase_order: int,
    phase_name: str,
    operation: str,
    source_json: str,
) -> dict[str, Any]:
    jobs = fio.get("jobs") or []
    if len(jobs) != 1:
        raise ValueError(
            f"Expected one fio job in {source_json}, found {len(jobs)}"
        )

    job = jobs[0]
    direction_name = "write" if operation == "write" else "read"
    direction = job.get(direction_name) or {}
    options = job.get("job options") or {}
    verify_errors, verify_errors_reported = extract_verify_errors(job)
    verify_method = str(options.get("verify", "")).lower()
    verify_only = option_enabled(options.get("verify_only", 0))
    do_verify = option_enabled(options.get("do_verify", 0))
    clat = direction.get("clat_ns") or {}

    return {
        "phase_order": phase_order,
        "phase_name": phase_name,
        "operation": operation,
        "fio_version": fio.get("fio version", ""),
        "job_error": int(job.get("error", -1)),
        "io_bytes": int(direction.get("io_bytes", 0)),
        "bandwidth_mib_s": float(direction.get("bw_bytes", 0)) / 1024**2,
        "iops": float(direction.get("iops", 0)),
        "clat_mean_ms": float(clat.get("mean", 0)) / 1_000_000.0,
        "clat_p99_ms": percentile_ms(direction, "p99"),
        "clat_p999_ms": percentile_ms(direction, "p999"),
        "clat_max_ms": float(clat.get("max", 0)) / 1_000_000.0,
        "verify_method": verify_method,
        "verify_only": verify_only,
        "do_verify": do_verify,
        "verify_errors": verify_errors,
        "verify_errors_reported": verify_errors_reported,
        "source_json": source_json,
    }


def evaluate_integrity(rows: list[dict[str, Any]]) -> tuple[str, list[str]]:
    failures: list[str] = []
    if len(rows) != 2:
        failures.append(f"expected two phases, found {len(rows)}")
        return "Fail", failures

    write_row = next((row for row in rows if row["operation"] == "write"), None)
    verify_row = next(
        (row for row in rows if row["operation"] == "read_verify"), None
    )
    if write_row is None or verify_row is None:
        failures.append("write and verify phases were not both identified")
        return "Fail", failures

    for row in rows:
        if row["job_error"] != 0:
            failures.append(
                f"{row['phase_name']} reported fio error {row['job_error']}"
            )
        if row["io_bytes"] != EXPECTED_BYTES:
            failures.append(
                f"{row['phase_name']} processed {row['io_bytes']} bytes, "
                f"expected {EXPECTED_BYTES}"
            )
        if row["verify_method"] != "crc32c":
            failures.append(
                f"{row['phase_name']} did not report verify=crc32c"
            )

    if not verify_row["verify_only"] and not verify_row["do_verify"]:
        failures.append("verify phase did not report verify_only/do_verify enabled")
    if verify_row["verify_errors"] != 0:
        failures.append(
            f"verify phase reported {verify_row['verify_errors']} verification errors"
        )

    return ("Pass" if not failures else "Fail"), failures


def count_active_host_samples(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = csv.DictReader(handle)
        return sum(
            1
            for row in rows
            if any(
                float(row.get(field) or 0) > 0
                for field in (
                    "disk_bytes_per_sec",
                    "disk_read_bytes_per_sec",
                    "disk_write_bytes_per_sec",
                )
            )
        )


def resolve_host_observer_artifact(
    value: Any,
    *,
    manifest_path: Path,
    host_dir: Path,
) -> tuple[Path | None, str | None, str | None]:
    text = str(value or "").strip()
    if not text:
        return None, None, "counter CSV artifact is not declared"

    declared = Path(text)
    if declared.is_absolute():
        candidate = manifest_path.parent / declared.name
        path_mode = "legacy_absolute_basename"
    else:
        candidate = manifest_path.parent / declared
        path_mode = "manifest_relative"

    if ":" in candidate.name:
        return None, path_mode, "counter CSV artifact uses an alternate data stream"
    if candidate.suffix.lower() != ".csv":
        return None, path_mode, "counter CSV artifact must name a .csv file"

    allowed_root = host_dir.resolve()
    resolved = candidate.resolve()
    try:
        resolved.relative_to(allowed_root)
    except ValueError:
        return None, path_mode, "counter CSV artifact escapes the host-observer directory"
    if not resolved.is_file():
        return None, path_mode, "counter CSV artifact is missing from the host-observer directory"
    return resolved, path_mode, None


def load_host_observer_statuses(result_dir: Path) -> list[dict[str, Any]]:
    statuses: list[dict[str, Any]] = []
    host_dir = result_dir / "host_observer"
    for path in sorted(host_dir.glob("*_manifest.json")):
        manifest = read_json(path)
        sampling = manifest.get("sampling") or {}
        csv_value = (manifest.get("artifacts") or {}).get("counter_csv")
        csv_path, artifact_path_mode, artifact_limitation = (
            resolve_host_observer_artifact(
                csv_value,
                manifest_path=path,
                host_dir=host_dir,
            )
        )
        active_sample_count = 0
        if csv_path is not None:
            try:
                active_sample_count = count_active_host_samples(csv_path)
            except (OSError, csv.Error, TypeError, ValueError) as exc:
                artifact_limitation = f"counter CSV artifact is unreadable: {exc}"
        producer_status = manifest.get("status", "limited")
        effective_status = (
            "complete"
            if (
                producer_status == "complete"
                and artifact_limitation is None
                and active_sample_count > 0
            )
            else "limited"
        )
        statuses.append({
            "phase": manifest.get("phase", path.stem),
            "status": effective_status,
            "producer_status": producer_status,
            "sample_count": sampling.get("sample_count", 0),
            "active_sample_count": active_sample_count,
            "counter_csv": relative(csv_path) if csv_path is not None else None,
            "artifact_path_mode": artifact_path_mode,
            "limitation": (
                None
                if effective_status == "complete"
                else artifact_limitation
                if artifact_limitation is not None
                else "no nonzero synchronized disk activity was observed"
                if active_sample_count == 0
                else (
                    f"host observer producer status was {producer_status}; "
                    "inspect observer errors and limitations"
                )
            ),
            "manifest": relative(path),
        })
    return statuses


def analyze_experiment(experiment_id: str) -> dict[str, Any]:
    experiment_path = EXPERIMENT_ROOT / experiment_id / "experiment_manifest.json"
    if not experiment_path.exists():
        raise FileNotFoundError(f"Experiment manifest not found: {experiment_path}")

    experiment = read_json(experiment_path)
    if experiment.get("test_protocol_id") != "EXT-DATA-INTEGRITY-001":
        raise ValueError(
            f"Unexpected protocol: {experiment.get('test_protocol_id')}"
        )

    run_id = f"sustained_{experiment_id}"
    result_dir = RESULT_ROOT / run_id
    runner_path = result_dir / "runner_manifest.json"
    runner = read_json(runner_path)
    rows: list[dict[str, Any]] = []

    for run in sorted(runner.get("runs") or [], key=lambda item: item["phase_order"]):
        fio_path = Path(run["fio_json"])
        if not fio_path.is_absolute():
            fio_path = REPO_ROOT / fio_path
        rows.append(summarize_fio_phase(
            read_json(fio_path),
            phase_order=int(run["phase_order"]),
            phase_name=str(run["phase_name"]),
            operation=str(run["operation"]),
            source_json=relative(fio_path),
        ))

    verdict, failures = evaluate_integrity(rows)
    host_observers = load_host_observer_statuses(result_dir)
    evidence_status = (
        "complete"
        if len(host_observers) == 2
        and all(item["status"] == "complete" for item in host_observers)
        else "limited"
    )

    summary_path = result_dir / "integrity_summary.csv"
    verdict_path = result_dir / "integrity_verdict.csv"
    analysis_manifest_path = result_dir / "analysis_manifest.json"
    write_csv(summary_path, rows)
    write_csv(verdict_path, [{
        "experiment_id": experiment_id,
        "test_protocol_id": "EXT-DATA-INTEGRITY-001",
        "integrity_verdict": verdict,
        "evidence_status": evidence_status,
        "expected_bytes_per_phase": EXPECTED_BYTES,
        "verification_method": "crc32c",
        "failure_count": len(failures),
        "failures": "; ".join(failures),
        "interpretation_boundary": (
            "Windows/USB/exFAT file-target path only; not power-loss, endurance, "
            "NAND, FTL, or internal ECC validation"
        ),
    }])

    analysis_manifest = {
        "schema_version": "1.0",
        "analysis_id": f"{experiment_id}_integrity",
        "experiment_id": experiment_id,
        "test_protocol_id": "EXT-DATA-INTEGRITY-001",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "analyzer": "scripts/analysis/analyze_external_ssd_data_integrity.py",
        "status": "complete",
        "integrity_verdict": verdict,
        "evidence_status": evidence_status,
        "failures": failures,
        "host_observers": host_observers,
        "artifacts": {
            "integrity_summary_csv": relative(summary_path),
            "integrity_verdict_csv": relative(verdict_path),
            "runner_manifest": relative(runner_path),
            "experiment_manifest": relative(experiment_path),
        },
        "interpretation_boundary": (
            "One file-target write/readback observation; internal SSD mechanisms "
            "and power-loss behavior are outside this evidence."
        ),
    }
    write_json(analysis_manifest_path, analysis_manifest)

    evidence = [
        relative(summary_path),
        relative(verdict_path),
        relative(analysis_manifest_path),
    ]
    experiment["analysis_evidence"] = sorted(set(
        list(experiment.get("analysis_evidence") or []) + evidence
    ))
    write_json(experiment_path, experiment)
    return analysis_manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--experiment-id",
        required=True,
        help="Experiment folder name under results/external_ssd/_experiments",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = analyze_experiment(args.experiment_id)
    print(f"Integrity verdict: {result['integrity_verdict']}")
    print(f"Evidence status  : {result['evidence_status']}")
    for failure in result["failures"]:
        print(f"- {failure}")


if __name__ == "__main__":
    main()
