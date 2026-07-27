"""Aggregate manifest-derived verdicts for EXT-REGRESSION-COMPACT-001.

This analyzer never launches fio. It consumes a JSON evidence index produced
after component analyzers have completed and writes a component CSV plus a
machine-readable profile verdict.
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
    """Load the deliberately flat component subset of the YAML profile."""
    profile: dict[str, Any] = {"components": []}
    current: dict[str, Any] | None = None
    in_components = False

    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip())

        if indent == 0 and stripped == "components:":
            in_components = True
            current = None
            continue
        if indent == 0 and stripped.endswith(":"):
            in_components = False
            current = None
            continue
        if indent == 0 and ":" in stripped:
            key, value = stripped.split(":", 1)
            profile[key] = scalar_value(value)
            continue

        if in_components and indent == 2 and stripped.startswith("- id:"):
            current = {"id": scalar_value(stripped.split(":", 1)[1])}
            profile["components"].append(current)
            continue
        if in_components and current is not None and indent == 4 and ":" in stripped:
            key, value = stripped.split(":", 1)
            current[key] = scalar_value(value)

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

    component_ids = [component["id"] for component in profile["components"]]
    if len(component_ids) != len(set(component_ids)):
        raise RegressionContractError("Profile component IDs must be unique")
    return profile


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


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


def evaluate_profile(
    profile: dict[str, Any],
    evidence_index: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if evidence_index.get("profile_id") != profile["profile_id"]:
        raise RegressionContractError(
            "Evidence index profile_id does not match the YAML profile"
        )

    evidence_components = evidence_index.get("components")
    if not isinstance(evidence_components, list):
        raise RegressionContractError("Evidence index components must be a list")

    by_id: dict[str, dict[str, Any]] = {}
    for component in evidence_components:
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

    rows: list[dict[str, Any]] = []
    integrity_values: list[str] = []
    performance_values: list[str] = []
    qos_values: list[str] = []
    host_values: list[str] = []
    evidence_values: list[str] = []

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
                EVIDENCE_STATUSES,
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
                    PERFORMANCE_VERDICTS,
                )
                qos_verdict = validate_choice(
                    component_id,
                    "qos_verdict",
                    record.get("qos_verdict"),
                    PERFORMANCE_VERDICTS,
                )
            if category == "integrity":
                integrity_verdict = validate_choice(
                    component_id,
                    "integrity_verdict",
                    record.get("integrity_verdict"),
                    INTEGRITY_VERDICTS,
                )
                host_status = validate_choice(
                    component_id,
                    "host_observer_status",
                    record.get("host_observer_status", "not_produced"),
                    HOST_OBSERVER_STATUSES,
                )
            source_manifest = str(record.get("source_manifest", ""))
            if not source_manifest:
                raise RegressionContractError(
                    f"{component_id}: source_manifest is required"
                )

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

    if "blocked" in evidence_values:
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

    if integrity_verdict == "Fail":
        release_verdict = "Fail"
    elif aggregate_evidence == "blocked" or integrity_verdict == "Blocked":
        release_verdict = "Blocked"
    elif "Regression" in {performance_verdict, qos_verdict}:
        release_verdict = "Review"
    elif "Observation" in {performance_verdict, qos_verdict}:
        release_verdict = "Observation"
    else:
        release_verdict = "Pass"

    verdict = {
        "schema_version": "1.0",
        "profile_id": profile["profile_id"],
        "requirement_id": profile["requirement_id"],
        "threshold_mode": profile["threshold_mode"],
        "run_id": evidence_index.get("run_id"),
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
    evidence_index = read_json(args.evidence_index)
    verdict, rows = evaluate_profile(profile, evidence_index)
    write_outputs(args.output_dir, verdict, rows)
    print(json.dumps(verdict, indent=2))


if __name__ == "__main__":
    main()
