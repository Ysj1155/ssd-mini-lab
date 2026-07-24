"""Build paired session evidence for EXT-STATE-REPRO-002."""

from __future__ import annotations

import csv
import json
import statistics
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
RESULT_ROOT = REPO_ROOT / "results" / "external_ssd"
EXPERIMENT_ROOT = RESULT_ROOT / "_experiments"
SUMMARY_CSV = REPO_ROOT / "results" / "external_ssd_sustained_summary.csv"
PAIR_CSV = REPO_ROOT / "results" / "external_ssd_state_repro_pairs.csv"
STUDY_CSV = REPO_ROOT / "results" / "external_ssd_state_repro_study_summary.csv"
PROTOCOL_ID = "EXT-STATE-REPRO-002"

METRICS = (
    "bandwidth_mib_s",
    "iops",
    "clat_mean_us",
    "clat_p99_us",
    "clat_p999_us",
    "clat_max_us",
)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_summary_rows(path: Path) -> dict[str, list[dict[str, str]]]:
    by_result_set: dict[str, list[dict[str, str]]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            by_result_set.setdefault(row["result_set"], []).append(row)
    return by_result_set


def one_summary_row(rows: dict[str, list[dict[str, str]]], result_set: str) -> dict[str, str]:
    matches = rows.get(result_set, [])
    if len(matches) != 1:
        raise ValueError(f"Expected one summary row for {result_set}, found {len(matches)}")
    return matches[0]


def as_float(row: dict[str, str], key: str) -> float:
    return float(row[key])


def ratio(post: float, baseline: float) -> float:
    return post / baseline


def delta_pct(post: float, baseline: float) -> float:
    return (ratio(post, baseline) - 1.0) * 100.0


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"No rows to write: {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def direction(values: list[float]) -> str:
    if all(value > 0 for value in values):
        return "positive"
    if all(value < 0 for value in values):
        return "negative"
    return "mixed"


def main() -> None:
    if not SUMMARY_CSV.exists():
        raise SystemExit("Run analyze_external_ssd_sustained.py first.")

    summaries = load_summary_rows(SUMMARY_CSV)
    pair_rows: list[dict[str, Any]] = []

    for manifest_path in sorted(EXPERIMENT_ROOT.glob("*/experiment_manifest.json")):
        manifest = read_json(manifest_path)
        if manifest.get("test_protocol_id") != PROTOCOL_ID:
            continue
        if manifest.get("status") != "complete":
            raise ValueError(f"Session is not complete: {manifest_path}")

        phases = {phase["state_phase"]: phase for phase in manifest["phases"]}
        baseline_id = phases["session_baseline_probe"]["run_id"]
        condition_id = phases["session_write_condition"]["run_id"]
        post_id = phases["session_post_write_probe"]["run_id"]

        baseline = one_summary_row(summaries, baseline_id)
        condition = one_summary_row(summaries, condition_id)
        post = one_summary_row(summaries, post_id)
        controls = manifest["fixed_controls"]
        pair: dict[str, Any] = {
            "study_id": manifest["study_id"],
            "session_index": manifest["session_index"],
            "session_id": manifest["experiment_id"],
            "started_at": manifest["started_at"],
            "completed_at": manifest["completed_at"],
            "reconnect_start_confirmed": controls["reconnect_start_confirmed"],
            "same_port_confirmed": controls["same_physical_usb_port_confirmed"],
            "disconnect_sec": controls["user_confirmed_disconnect_sec"],
            "initial_idle_sec": controls["initial_idle_sec"],
            "post_condition_idle_sec": controls["post_condition_idle_sec"],
            "baseline_result_set": baseline_id,
            "condition_result_set": condition_id,
            "post_result_set": post_id,
        }

        for metric in METRICS:
            baseline_value = as_float(baseline, metric)
            condition_value = as_float(condition, metric)
            post_value = as_float(post, metric)
            pair[f"baseline_{metric}"] = baseline_value
            pair[f"condition_{metric}"] = condition_value
            pair[f"post_{metric}"] = post_value
            pair[f"post_over_baseline_{metric}"] = ratio(post_value, baseline_value)
            pair[f"post_vs_baseline_{metric}_delta_pct"] = delta_pct(post_value, baseline_value)

        pair_rows.append(pair)

    pair_rows.sort(key=lambda row: int(row["session_index"]))
    if not pair_rows:
        raise SystemExit(f"No complete {PROTOCOL_ID} sessions found.")

    bandwidth_deltas = [float(row["post_vs_baseline_bandwidth_mib_s_delta_pct"]) for row in pair_rows]
    iops_deltas = [float(row["post_vs_baseline_iops_delta_pct"]) for row in pair_rows]
    p99_deltas = [float(row["post_vs_baseline_clat_p99_us_delta_pct"]) for row in pair_rows]
    p999_deltas = [float(row["post_vs_baseline_clat_p999_us_delta_pct"]) for row in pair_rows]
    max_deltas = [float(row["post_vs_baseline_clat_max_us_delta_pct"]) for row in pair_rows]
    bw_direction = direction(bandwidth_deltas)

    study_rows = [{
        "study_id": pair_rows[0]["study_id"],
        "test_protocol_id": PROTOCOL_ID,
        "complete_session_count": len(pair_rows),
        "planned_session_count": 3,
        "bandwidth_positive_session_count": sum(value > 0 for value in bandwidth_deltas),
        "bandwidth_negative_session_count": sum(value < 0 for value in bandwidth_deltas),
        "bandwidth_delta_direction": bw_direction,
        "bandwidth_delta_pct_median": statistics.median(bandwidth_deltas),
        "bandwidth_delta_pct_min": min(bandwidth_deltas),
        "bandwidth_delta_pct_max": max(bandwidth_deltas),
        "iops_delta_pct_median": statistics.median(iops_deltas),
        "p99_delta_pct_median": statistics.median(p99_deltas),
        "p999_delta_pct_median": statistics.median(p999_deltas),
        "max_latency_delta_pct_median": statistics.median(max_deltas),
        "verdict": "reproduced_direction" if bw_direction != "mixed" and len(pair_rows) == 3 else "not_reproduced_under_controlled_external_sequence",
        "interpretation_boundary": "USB, Windows, exFAT file-target evidence; reconnect-start does not prove internally reset SSD state",
    }]

    write_csv(PAIR_CSV, pair_rows)
    write_csv(STUDY_CSV, study_rows)
    print(f"[OK] Saved paired sessions: {PAIR_CSV}")
    print(f"[OK] Saved study summary: {STUDY_CSV}")


if __name__ == "__main__":
    main()
