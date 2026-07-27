"""Aggregate verified evidence for EXT-REGRESSION-COMPACT-001.

This analyzer never launches fio. It validates repository-local component
evidence, then writes a component CSV and a machine-readable profile verdict.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROFILE = REPO_ROOT / "configs" / "external_ssd_regression_profile.yaml"

EVIDENCE_STATUSES = {"complete", "limited", "blocked"}
PERFORMANCE_VERDICTS = {"Observation", "Pass", "Regression", "Blocked"}
INTEGRITY_VERDICTS = {"Pass", "Fail", "Blocked"}
HOST_OBSERVER_STATUSES = {"complete", "limited", "not_produced"}
RELEASE_VERDICTS = ["Fail", "Blocked", "Review", "Observation", "Pass"]
SUPPORTED_EVIDENCE = {
    "run_manifest",
    "fio_json",
    "summary_csv",
    "time_series_csv",
    "window_csv",
    "p99",
    "p999",
    "write_json",
    "verify_json",
    "integrity_verdict",
}


class RegressionContractError(ValueError):
    """Raised when the profile or evidence index violates the contract."""


def scalar_value(value: str) -> Any:
    value = value.strip()
    if not value:
        return ""
    if value.startswith("[") and value.endswith("]"):
        return [
            scalar_value(item)
            for item in value[1:-1].split(",")
            if item.strip()
        ]
    unquoted = value.strip('"').strip("'")
    if re.fullmatch(r"-?\d+", unquoted):
        return int(unquoted)
    if unquoted.lower() in {"true", "false"}:
        return unquoted.lower() == "true"
    return unquoted


def load_profile(path: Path = DEFAULT_PROFILE) -> dict[str, Any]:
    """Load the deliberately constrained YAML subset used by this profile."""
    profile: dict[str, Any] = {"components": [], "verdict_policy": {}}
    current: dict[str, Any] | None = None
    section = ""

    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip())

        if indent == 0 and stripped == "components:":
            section = "components"
            current = None
            continue
        if indent == 0 and stripped == "verdict_policy:":
            section = "verdict_policy"
            current = None
            continue
        if indent == 0 and ":" in stripped:
            section = ""
            current = None
            key, value = stripped.split(":", 1)
            profile[key] = scalar_value(value)
            continue

        if section == "components" and indent == 2 and stripped.startswith("- id:"):
            current = {"id": scalar_value(stripped.split(":", 1)[1])}
            profile["components"].append(current)
            continue
        if section == "components" and current is not None and indent == 4:
            key, value = stripped.split(":", 1)
            current[key] = scalar_value(value)
            continue
        if section == "verdict_policy" and indent == 2:
            key, value = stripped.split(":", 1)
            profile["verdict_policy"][key] = scalar_value(value)

    required_globals = {
        "schema_version",
        "profile_id",
        "requirement_id",
        "threshold_mode",
    }
    missing_globals = sorted(required_globals - set(profile))
    if missing_globals:
        raise RegressionContractError(
            f"Profile is missing fields: {', '.join(missing_globals)}"
        )
    if not profile["components"]:
        raise RegressionContractError("Profile contains no components")

    required_component_fields = {
        "id",
        "source_test_case",
        "category",
        "required_evidence",
        "repeats",
    }
    component_ids: list[str] = []
    for component in profile["components"]:
        missing = sorted(required_component_fields - set(component))
        if missing:
            raise RegressionContractError(
                f"{component.get('id', '<unknown>')}: profile fields missing: "
                f"{', '.join(missing)}"
            )
        unsupported = sorted(
            set(component["required_evidence"]) - SUPPORTED_EVIDENCE
        )
        if unsupported:
            raise RegressionContractError(
                f"{component['id']}: unsupported required evidence: "
                f"{', '.join(unsupported)}"
            )
        component_ids.append(str(component["id"]))
    if len(component_ids) != len(set(component_ids)):
        raise RegressionContractError("Profile component IDs must be unique")

    policy = profile["verdict_policy"]
    expected_policy = {
        "evidence_status": EVIDENCE_STATUSES,
        "integrity_verdict": INTEGRITY_VERDICTS,
        "performance_verdict": PERFORMANCE_VERDICTS,
        "qos_verdict": PERFORMANCE_VERDICTS,
        "host_observer_status": HOST_OBSERVER_STATUSES,
    }
    for field, expected in expected_policy.items():
        if set(policy.get(field, [])) != expected:
            raise RegressionContractError(
                f"verdict_policy.{field} must contain {sorted(expected)}"
            )
    if policy.get("release_precedence") != RELEASE_VERDICTS:
        raise RegressionContractError(
            "verdict_policy.release_precedence must be "
            f"{RELEASE_VERDICTS}"
        )
    return profile


def read_json(path: Path, label: str = "JSON") -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RegressionContractError(f"{label} is unreadable: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise RegressionContractError(f"{label} must contain a JSON object: {path}")
    return value


def resolve_evidence_path(value: Any, repo_root: Path, label: str) -> Path:
    text = str(value or "").strip()
    if not text:
        raise RegressionContractError(f"{label} is required")
    relative = Path(text)
    if relative.is_absolute():
        raise RegressionContractError(f"{label} must be repository-relative: {text}")
    root = repo_root.resolve()
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise RegressionContractError(
            f"{label} escapes the repository: {text}"
        ) from exc
    if not candidate.is_file():
        raise RegressionContractError(f"{label} does not exist: {text}")
    return candidate


def validate_choice(
    component_id: str,
    field: str,
    value: Any,
    allowed: set[str],
) -> str:
    text = str(value)
    if text not in allowed:
        raise RegressionContractError(
            f"{component_id}: {field}={text!r}; expected one of {sorted(allowed)}"
        )
    return text


def normalized(value: Any) -> str:
    return str(value).strip().lower()


def matching_fio_records(
    component: dict[str, Any],
    manifest: dict[str, Any],
    repo_root: Path,
) -> list[dict[str, Any]]:
    component_id = component["id"]
    runs = manifest.get("runs")
    if not isinstance(runs, list):
        raise RegressionContractError(f"{component_id}: manifest runs must be a list")

    records: list[dict[str, Any]] = []
    for run in runs:
        if not isinstance(run, dict):
            raise RegressionContractError(f"{component_id}: manifest run is invalid")
        fio_path = resolve_evidence_path(
            run.get("fio_json"),
            repo_root,
            f"{component_id}: fio_json",
        )
        fio = read_json(fio_path, f"{component_id}: fio_json")
        jobs = fio.get("jobs")
        if not isinstance(jobs, list) or not jobs:
            raise RegressionContractError(
                f"{component_id}: fio_json has no jobs: {fio_path}"
            )
        for job in jobs:
            options = job.get("job options", {})
            if not isinstance(options, dict):
                continue
            if component["category"] == "integrity":
                matches = (
                    normalized(options.get("bs")) == normalized(component.get("bs"))
                    and normalized(options.get("iodepth"))
                    == normalized(component.get("iodepth"))
                    and normalized(options.get("size"))
                    == normalized(component.get("size"))
                    and normalized(options.get("verify"))
                    == normalized(component.get("verify"))
                )
            else:
                matches = (
                    normalized(options.get("rw")) == normalized(component.get("rw"))
                    and normalized(options.get("bs")) == normalized(component.get("bs"))
                    and normalized(options.get("iodepth"))
                    == normalized(component.get("iodepth"))
                    and normalized(options.get("runtime"))
                    == normalized(component.get("runtime_sec"))
                )
            if matches:
                records.append({
                    "path": fio_path,
                    "options": options,
                    "job": job,
                    "manifest_run": run,
                })
    return records


def csv_rows(path: Path, label: str) -> tuple[list[str], list[dict[str, str]]]:
    try:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
            fields = list(reader.fieldnames or [])
    except OSError as exc:
        raise RegressionContractError(f"{label} is unreadable: {path}: {exc}") from exc
    if not fields:
        raise RegressionContractError(f"{label} has no header: {path}")
    return fields, rows


def validate_summary_evidence(
    component: dict[str, Any],
    manifest: dict[str, Any],
    repo_root: Path,
    required: set[str],
) -> None:
    component_id = component["id"]
    artifacts = manifest.get("artifacts", {})
    candidates = [artifacts.get("summary_csv")]
    analysis_csvs = artifacts.get("analysis_csvs", [])
    if isinstance(analysis_csvs, list):
        candidates.extend(analysis_csvs)
    result_set = str(manifest.get("result_set", ""))
    errors: list[str] = []

    for candidate in candidates:
        try:
            summary_path = resolve_evidence_path(
                candidate,
                repo_root,
                f"{component_id}: summary_csv",
            )
        except RegressionContractError as exc:
            errors.append(str(exc))
            continue
        fields, rows = csv_rows(summary_path, f"{component_id}: summary_csv")
        if {"result_set", "rw", "bs", "iodepth"} <= set(fields):
            matched = [
                row
                for row in rows
                if row.get("result_set") == result_set
                and normalized(row.get("rw")) == normalized(component.get("rw"))
                and normalized(row.get("bs")) == normalized(component.get("bs"))
                and normalized(row.get("iodepth"))
                == normalized(component.get("iodepth"))
            ]
            metric_fields = {"p99": "clat_p99_us", "p999": "clat_p999_us"}
            enough_repeats = len(matched) >= int(component["repeats"])
        elif {"workload", "block_size", "repeat_count"} <= set(fields):
            matched = [
                row
                for row in rows
                if normalized(row.get("workload")) == normalized(component.get("rw"))
                and normalized(row.get("block_size"))
                == normalized(component.get("bs"))
            ]
            metric_fields = {
                "p99": "clat_p99_ms_mean",
                "p999": "clat_p999_ms_mean",
            }
            enough_repeats = bool(matched) and all(
                int(row.get("repeat_count", 0)) >= int(component["repeats"])
                for row in matched
            )
        else:
            errors.append(f"{summary_path}: unsupported summary schema")
            continue

        metrics_complete = all(
            evidence_name not in required
            or (
                field in fields
                and all(row.get(field) for row in matched)
            )
            for evidence_name, field in metric_fields.items()
        )
        if enough_repeats and metrics_complete:
            return
        errors.append(f"{summary_path}: condition, repeat, or percentile mismatch")

    raise RegressionContractError(
        f"{component_id}: no usable summary_csv evidence: {'; '.join(errors)}"
    )


def validate_series_evidence(
    component: dict[str, Any],
    manifest: dict[str, Any],
    repo_root: Path,
    artifact_key: str,
) -> None:
    component_id = component["id"]
    artifacts = manifest.get("artifacts", {})
    path = resolve_evidence_path(
        artifacts.get(artifact_key),
        repo_root,
        f"{component_id}: {artifact_key}",
    )
    _, rows = csv_rows(path, f"{component_id}: {artifact_key}")
    result_set = str(manifest.get("result_set", ""))
    if not any(row.get("result_set") == result_set for row in rows):
        raise RegressionContractError(
            f"{component_id}: {artifact_key} has no rows for {result_set}"
        )


def validate_integrity_analysis(
    component: dict[str, Any],
    record: dict[str, Any],
    manifest: dict[str, Any],
    repo_root: Path,
) -> tuple[str, str]:
    component_id = component["id"]
    links = manifest.get("evidence_links", {})
    analysis_path = resolve_evidence_path(
        links.get("analysis_manifest"),
        repo_root,
        f"{component_id}: analysis_manifest",
    )
    analysis = read_json(analysis_path, f"{component_id}: analysis_manifest")
    if analysis.get("test_protocol_id") != component["source_test_case"]:
        raise RegressionContractError(
            f"{component_id}: analysis test_protocol_id does not match profile"
        )
    actual_integrity = validate_choice(
        component_id,
        "analysis integrity_verdict",
        analysis.get("integrity_verdict"),
        INTEGRITY_VERDICTS,
    )
    if record.get("integrity_verdict") != actual_integrity:
        raise RegressionContractError(
            f"{component_id}: evidence index integrity_verdict does not match "
            "analysis_manifest"
        )

    observers = analysis.get("host_observers", [])
    statuses = {
        str(item.get("status"))
        for item in observers
        if isinstance(item, dict) and item.get("status")
    }
    actual_host = (
        "limited"
        if "limited" in statuses
        else "complete"
        if statuses and statuses == {"complete"}
        else "not_produced"
    )
    if record.get("host_observer_status", "not_produced") != actual_host:
        raise RegressionContractError(
            f"{component_id}: evidence index host_observer_status does not match "
            "analysis_manifest"
        )
    return actual_integrity, actual_host


def validate_source_evidence(
    component: dict[str, Any],
    record: dict[str, Any],
    repo_root: Path,
) -> tuple[str, str, str]:
    component_id = component["id"]
    source_text = str(record.get("source_manifest", "")).strip()
    source_path = resolve_evidence_path(
        source_text,
        repo_root,
        f"{component_id}: source_manifest",
    )
    if source_path.name != "run_manifest.json":
        raise RegressionContractError(
            f"{component_id}: source_manifest must name run_manifest.json"
        )
    manifest = read_json(source_path, f"{component_id}: source_manifest")
    if not manifest.get("run_id") or not manifest.get("result_set"):
        raise RegressionContractError(
            f"{component_id}: source manifest requires run_id and result_set"
        )
    if manifest.get("test_case_id") != component["source_test_case"]:
        raise RegressionContractError(
            f"{component_id}: source manifest test_case_id does not match profile"
        )
    manifest_status = validate_choice(
        component_id,
        "source manifest status",
        manifest.get("status"),
        EVIDENCE_STATUSES,
    )
    status_rank = {"blocked": 0, "limited": 1, "complete": 2}
    if status_rank[record["evidence_status"]] > status_rank[manifest_status]:
        raise RegressionContractError(
            f"{component_id}: evidence index cannot upgrade source status "
            f"{manifest_status} to {record['evidence_status']}"
        )

    required = set(component["required_evidence"])
    fio_records = matching_fio_records(component, manifest, repo_root)
    errored_fio_records = [
        item
        for item in fio_records
        if normalized(item["job"].get("error", 0)) != "0"
        or normalized(item["manifest_run"].get("error", 0)) != "0"
    ]
    error_claims_success = (
        component["category"] != "integrity"
        or record.get("integrity_verdict") == "Pass"
    )
    if (
        errored_fio_records
        and record["evidence_status"] != "blocked"
        and error_claims_success
    ):
        raise RegressionContractError(
            f"{component_id}: errored fio evidence cannot support a successful claim"
        )
    if "fio_json" in required and len(fio_records) < int(component["repeats"]):
        raise RegressionContractError(
            f"{component_id}: found {len(fio_records)} matching fio_json records; "
            f"expected at least {component['repeats']}"
        )
    if {"summary_csv", "p99", "p999"} & required:
        validate_summary_evidence(component, manifest, repo_root, required)
    if "time_series_csv" in required:
        validate_series_evidence(
            component, manifest, repo_root, "timeseries_csv"
        )
    if "window_csv" in required:
        validate_series_evidence(
            component, manifest, repo_root, "window_summary_csv"
        )

    actual_integrity = ""
    actual_host = ""
    if component["category"] == "integrity":
        write_records = [
            item for item in fio_records
            if normalized(item["options"].get("rw")) == "write"
            and normalized(item["options"].get("do_verify")) in {"", "0"}
        ]
        verify_records = [
            item for item in fio_records
            if normalized(item["options"].get("verify_only")) == "1"
            and normalized(item["options"].get("do_verify")) == "1"
        ]
        if "write_json" in required and not write_records:
            raise RegressionContractError(
                f"{component_id}: matching write_json evidence is missing"
            )
        if "verify_json" in required and not verify_records:
            raise RegressionContractError(
                f"{component_id}: matching verify_json evidence is missing"
            )
        if "integrity_verdict" in required:
            actual_integrity, actual_host = validate_integrity_analysis(
                component, record, manifest, repo_root
            )
    return source_text, actual_integrity, actual_host


def evaluate_profile(
    profile: dict[str, Any],
    evidence_index: dict[str, Any],
    repo_root: Path = REPO_ROOT,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if evidence_index.get("profile_id") != profile["profile_id"]:
        raise RegressionContractError(
            "Evidence index profile_id does not match the YAML profile"
        )
    run_id = evidence_index.get("run_id")
    if not isinstance(run_id, str) or not run_id.strip():
        raise RegressionContractError("Evidence index run_id is required")

    evidence_components = evidence_index.get("components")
    if not isinstance(evidence_components, list):
        raise RegressionContractError("Evidence index components must be a list")

    by_id: dict[str, dict[str, Any]] = {}
    for component in evidence_components:
        if not isinstance(component, dict):
            raise RegressionContractError("Evidence component must be an object")
        component_id = str(component.get("component_id", ""))
        if not component_id:
            raise RegressionContractError("Evidence component_id is required")
        if component_id in by_id:
            raise RegressionContractError(
                f"Duplicate evidence component: {component_id}"
            )
        by_id[component_id] = component

    expected = {component["id"]: component for component in profile["components"]}
    unknown = sorted(set(by_id) - set(expected))
    if unknown:
        raise RegressionContractError(
            f"Unknown evidence components: {', '.join(unknown)}"
        )

    policy = profile["verdict_policy"]
    rows: list[dict[str, Any]] = []
    integrity_values: list[str] = []
    performance_values: list[str] = []
    qos_values: list[str] = []
    host_values: list[str] = []
    evidence_values: list[str] = []
    host_gating_blocked = False

    for component_id, definition in expected.items():
        record = by_id.get(component_id)
        if record is None:
            evidence_status = "blocked"
            performance_verdict = (
                "Blocked" if definition["category"] != "integrity" else ""
            )
            qos_verdict = (
                "Blocked"
                if definition["category"] in {"performance", "sustained_qos"}
                else ""
            )
            integrity_verdict = (
                "Blocked" if definition["category"] == "integrity" else ""
            )
            host_status = (
                "not_produced" if definition["category"] == "integrity" else ""
            )
            source_manifest = ""
        else:
            evidence_status = validate_choice(
                component_id,
                "evidence_status",
                record.get("evidence_status"),
                set(policy["evidence_status"]),
            )
            category = definition["category"]
            performance_verdict = ""
            qos_verdict = ""
            integrity_verdict = ""
            host_status = ""

            if category in {"performance", "sustained_qos"}:
                performance_verdict = validate_choice(
                    component_id,
                    "performance_verdict",
                    record.get("performance_verdict"),
                    set(policy["performance_verdict"]),
                )
                qos_verdict = validate_choice(
                    component_id,
                    "qos_verdict",
                    record.get("qos_verdict"),
                    set(policy["qos_verdict"]),
                )
                if (
                    profile["threshold_mode"] == "observation"
                    and "Pass" in {performance_verdict, qos_verdict}
                ):
                    raise RegressionContractError(
                        f"{component_id}: Pass is invalid while threshold_mode "
                        "is observation"
                    )
            if category == "integrity":
                integrity_verdict = validate_choice(
                    component_id,
                    "integrity_verdict",
                    record.get("integrity_verdict"),
                    set(policy["integrity_verdict"]),
                )
                host_status = validate_choice(
                    component_id,
                    "host_observer_status",
                    record.get("host_observer_status", "not_produced"),
                    set(policy["host_observer_status"]),
                )

            source_manifest, actual_integrity, actual_host = (
                validate_source_evidence(definition, record, repo_root)
            )
            if actual_integrity:
                integrity_verdict = actual_integrity
            if actual_host:
                host_status = actual_host
            if (
                definition.get("host_observer_gating", False)
                and host_status != "complete"
            ):
                host_gating_blocked = True

        evidence_values.append(evidence_status)
        if performance_verdict:
            performance_values.append(performance_verdict)
        if qos_verdict:
            qos_values.append(qos_verdict)
        if integrity_verdict:
            integrity_values.append(integrity_verdict)
        if host_status:
            host_values.append(host_status)

        rows.append({
            "component_id": component_id,
            "source_test_case": definition["source_test_case"],
            "category": definition["category"],
            "evidence_status": evidence_status,
            "performance_verdict": performance_verdict,
            "qos_verdict": qos_verdict,
            "integrity_verdict": integrity_verdict,
            "host_observer_status": host_status,
            "source_manifest": source_manifest,
        })

    if "blocked" in evidence_values or host_gating_blocked:
        aggregate_evidence = "blocked"
    elif "limited" in evidence_values or "limited" in host_values:
        aggregate_evidence = "limited"
    else:
        aggregate_evidence = "complete"

    integrity_verdict = (
        "Fail"
        if "Fail" in integrity_values
        else "Blocked"
        if "Blocked" in integrity_values
        else "Pass"
    )
    performance_verdict = (
        "Regression"
        if "Regression" in performance_values
        else "Blocked"
        if "Blocked" in performance_values
        else "Observation"
        if "Observation" in performance_values
        else "Pass"
    )
    qos_verdict = (
        "Regression"
        if "Regression" in qos_values
        else "Blocked"
        if "Blocked" in qos_values
        else "Observation"
        if "Observation" in qos_values
        else "Pass"
    )

    release_candidates: set[str] = set()
    if integrity_verdict == "Fail":
        release_candidates.add("Fail")
    if aggregate_evidence == "blocked" or integrity_verdict == "Blocked":
        release_candidates.add("Blocked")
    if "Regression" in {performance_verdict, qos_verdict}:
        release_candidates.add("Review")
    if (
        profile["threshold_mode"] == "observation"
        or "Observation" in {performance_verdict, qos_verdict}
    ):
        release_candidates.add("Observation")
    if not release_candidates:
        release_candidates.add("Pass")
    release_verdict = next(
        item
        for item in policy["release_precedence"]
        if item in release_candidates
    )

    verdict = {
        "schema_version": "1.0",
        "profile_id": profile["profile_id"],
        "requirement_id": profile["requirement_id"],
        "threshold_mode": profile["threshold_mode"],
        "run_id": run_id,
        "expected_component_count": len(expected),
        "received_component_count": len(by_id),
        "evidence_status": aggregate_evidence,
        "integrity_verdict": integrity_verdict,
        "performance_verdict": performance_verdict,
        "qos_verdict": qos_verdict,
        "host_observer_status": (
            "limited"
            if "limited" in host_values
            else "complete"
            if host_values and all(value == "complete" for value in host_values)
            else "not_produced"
        ),
        "release_verdict": release_verdict,
        "interpretation_boundary": profile.get("interpretation_boundary"),
    }
    return verdict, rows


def write_outputs(
    output_dir: Path,
    verdict: dict[str, Any],
    rows: list[dict[str, Any]],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "regression_component_summary.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (output_dir / "regression_verdict.json").write_text(
        json.dumps(verdict, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--evidence-index", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    profile = load_profile(args.profile)
    evidence_index = read_json(args.evidence_index, "evidence index")
    verdict, rows = evaluate_profile(profile, evidence_index)
    write_outputs(args.output_dir, verdict, rows)
    print(json.dumps(verdict, indent=2))


if __name__ == "__main__":
    main()
