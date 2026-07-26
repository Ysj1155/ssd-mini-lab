"""Analyze EXT-IDLE-RAMP-001 symmetric idle-duration evidence."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import analyze_external_ssd_mixed_ratio_sweep as mixed


REPO_ROOT = Path(__file__).resolve().parents[2]
RESULT_ROOT = REPO_ROOT / "results" / "external_ssd"
EXPERIMENT_ROOT = RESULT_ROOT / "_experiments"
PROTOCOL_ID = "EXT-IDLE-RAMP-001"
RAMP_MIN_TRANSITION_SEC = 10.0
RAMP_MIN_PLATEAU_OVER_FIRST = 1.30
PAIR_TRANSITION_TOLERANCE_SEC = 20.0


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def relative(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def ramp_present(row: dict[str, Any]) -> bool:
    transition = row.get("transition_sec")
    return (
        transition not in (None, "")
        and float(transition) >= RAMP_MIN_TRANSITION_SEC
        and float(row["plateau_over_first_third"]) >= RAMP_MIN_PLATEAU_OVER_FIRST
    )


def summarize_conditions(
    phase_rows: list[dict[str, Any]],
    transition_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    phases = {int(row["phase_order"]): row for row in phase_rows}
    groups: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in transition_rows:
        groups[int(row["requested_pre_probe_idle_sec"])].append(row)

    output: list[dict[str, Any]] = []
    for idle_sec, rows in sorted(groups.items()):
        rows.sort(key=lambda row: int(row["condition_replicate"]))
        if len(rows) != 2:
            raise ValueError(f"Expected two repeats for idle={idle_sec}, found {len(rows)}")
        ramp_values = [ramp_present(row) for row in rows]
        transition_values = [
            float(row["transition_sec"])
            for row in rows
            if ramp_present(row)
        ]
        phase_matches = [phases[int(row["phase_order"])] for row in rows]
        same_ramp_value = len(set(ramp_values)) == 1
        transition_range = (
            max(transition_values) - min(transition_values)
            if len(transition_values) == 2
            else None
        )
        pair_consistent = same_ramp_value and (
            not all(ramp_values)
            or (
                transition_range is not None
                and transition_range <= PAIR_TRANSITION_TOLERANCE_SEC
            )
        )
        output.append({
            "requested_pre_probe_idle_sec": idle_sec,
            "repeat_count": len(rows),
            "phase_orders": ",".join(str(row["phase_order"]) for row in rows),
            "actual_controlled_idle_sec_mean": statistics.mean(
                float(row["actual_controlled_idle_sec"]) for row in rows
            ),
            "previous_fio_gap_sec_mean": statistics.mean(
                float(row["previous_fio_gap_sec"])
                for row in rows
                if row.get("previous_fio_gap_sec") not in (None, "")
            )
            if any(row.get("previous_fio_gap_sec") not in (None, "") for row in rows)
            else None,
            "ramp_present_count": sum(ramp_values),
            "ramp_present_repeat1": ramp_values[0],
            "ramp_present_repeat2": ramp_values[1],
            "transition_sec_median_when_present": (
                statistics.median(transition_values) if transition_values else None
            ),
            "transition_sec_min_when_present": (
                min(transition_values) if transition_values else None
            ),
            "transition_sec_max_when_present": (
                max(transition_values) if transition_values else None
            ),
            "transition_sec_pair_range": transition_range,
            "plateau_over_first_third_mean": statistics.mean(
                float(row["plateau_over_first_third"]) for row in rows
            ),
            "last_over_first_total_bandwidth_mean": statistics.mean(
                float(row["last_over_first_total_bandwidth"]) for row in rows
            ),
            "total_bandwidth_mib_s_mean": statistics.mean(
                float(row["total_bandwidth_mib_s"]) for row in phase_matches
            ),
            "read_clat_p99_ms_mean": statistics.mean(
                float(row["read_clat_p99_ms"]) for row in phase_matches
            ),
            "read_clat_p999_ms_mean": statistics.mean(
                float(row["read_clat_p999_ms"]) for row in phase_matches
            ),
            "pair_consistent": pair_consistent,
        })
    if [row["requested_pre_probe_idle_sec"] for row in output] != [0, 60, 300]:
        raise ValueError("Expected idle conditions 0, 60, and 300 seconds")
    return output


def build_verdict(
    experiment_id: str,
    condition_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_idle = {
        int(row["requested_pre_probe_idle_sec"]): row
        for row in condition_rows
    }
    consistent_count = sum(bool(row["pair_consistent"]) for row in condition_rows)
    ramp_counts = [int(by_idle[idle]["ramp_present_count"]) for idle in (0, 60, 300)]
    transition_medians = [
        by_idle[idle]["transition_sec_median_when_present"]
        for idle in (0, 60, 300)
    ]
    available_medians = [
        float(value) for value in transition_medians if value is not None
    ]
    monotonic_ramp_count = ramp_counts == sorted(ramp_counts)
    monotonic_transition = (
        len(available_medians) == 3
        and available_medians == sorted(available_medians)
        and available_medians[-1] - available_medians[0] >= 10.0
    )
    association_observed = (
        consistent_count == len(condition_rows)
        and monotonic_ramp_count
        and (
            monotonic_transition
            or ramp_counts[-1] > ramp_counts[0]
        )
    )
    return [{
        "experiment_id": experiment_id,
        "test_protocol_id": PROTOCOL_ID,
        "requirement_verdict": "Pass",
        "complete_phase_count": 6,
        "pair_consistent_condition_count": consistent_count,
        "idle_0_ramp_present_count": ramp_counts[0],
        "idle_60_ramp_present_count": ramp_counts[1],
        "idle_300_ramp_present_count": ramp_counts[2],
        "ramp_count_nondecreasing_with_idle": monotonic_ramp_count,
        "idle_0_transition_sec_median": transition_medians[0],
        "idle_60_transition_sec_median": transition_medians[1],
        "idle_300_transition_sec_median": transition_medians[2],
        "transition_time_nondecreasing_with_idle": monotonic_transition,
        "performance_verdict": (
            "idle_duration_association_observed"
            if association_observed
            else "no_clear_idle_duration_association"
        ),
        "interpretation_boundary": (
            "Externally controlled requested idle intervals and fio file-target "
            "evidence; association does not identify a device-internal cause."
        ),
    }]


def latest_experiment_label() -> str:
    candidates: list[tuple[str, str]] = []
    for path in EXPERIMENT_ROOT.glob("*/experiment_manifest.json"):
        manifest = read_json(path)
        if (
            manifest.get("test_protocol_id") == PROTOCOL_ID
            and manifest.get("status") == "complete"
        ):
            candidates.append((str(manifest["started_at"]), str(manifest["experiment_id"])))
    if not candidates:
        raise SystemExit(f"No complete {PROTOCOL_ID} experiment found.")
    return max(candidates)[1]


def analyze(experiment_label: str) -> dict[str, Path]:
    experiment_path = EXPERIMENT_ROOT / experiment_label / "experiment_manifest.json"
    experiment = read_json(experiment_path)
    if experiment.get("test_protocol_id") != PROTOCOL_ID:
        raise ValueError(f"Unsupported protocol: {experiment.get('test_protocol_id')}")
    if experiment.get("status") != "complete":
        raise ValueError(f"Experiment is not complete: {experiment_path}")

    result_dir = RESULT_ROOT / f"sustained_{experiment_label}"
    runner_path = result_dir / "runner_manifest.json"
    runner = read_json(runner_path)
    runs = runner.get("runs") or []
    if runner.get("status") != "complete" or len(runs) != 6:
        raise ValueError(f"Expected complete runner with 6 phases: {runner_path}")

    runtime_sec = int(experiment["fixed_controls"]["runtime_sec"])
    phase_rows: list[dict[str, Any]] = []
    window_rows: list[dict[str, Any]] = []
    transition_rows: list[dict[str, Any]] = []

    for run in runs:
        helper_run = {
            **run,
            "cycle": int(run["condition_replicate"]),
            "position": int(run["phase_order"]),
        }
        fio_path = Path(run["fio_json"])
        phase = mixed.summarize_phase(helper_run, read_json(fio_path))
        phase.pop("cycle")
        phase.pop("position")
        phase.update({
            "experiment_id": experiment_label,
            "phase_code": run["phase_code"],
            "requested_pre_probe_idle_sec": int(run["requested_pre_probe_idle_sec"]),
            "condition_replicate": int(run["condition_replicate"]),
            "actual_controlled_idle_sec": float(run["actual_controlled_idle_sec"]),
            "previous_fio_gap_sec": run.get("previous_fio_gap_sec"),
            "source_json": relative(fio_path),
        })
        phase_rows.append(phase)

        windows = mixed.summarize_windows(helper_run, runtime_sec)
        for row in windows:
            row.pop("cycle")
            row.pop("position")
            row.update({
                "experiment_id": experiment_label,
                "phase_code": run["phase_code"],
                "requested_pre_probe_idle_sec": int(run["requested_pre_probe_idle_sec"]),
                "condition_replicate": int(run["condition_replicate"]),
            })
        window_rows.extend(windows)

        transition = mixed.summarize_transition(helper_run, runtime_sec)
        transition.pop("cycle")
        transition.pop("position")
        transition.update({
            "experiment_id": experiment_label,
            "phase_code": run["phase_code"],
            "requested_pre_probe_idle_sec": int(run["requested_pre_probe_idle_sec"]),
            "condition_replicate": int(run["condition_replicate"]),
            "actual_controlled_idle_sec": float(run["actual_controlled_idle_sec"]),
            "previous_fio_gap_sec": run.get("previous_fio_gap_sec"),
        })
        transition_rows.append(transition)

    phase_rows.sort(key=lambda row: int(row["phase_order"]))
    window_rows.sort(
        key=lambda row: (
            int(row["phase_order"]),
            {"first": 0, "middle": 1, "last": 2}[str(row["window"])],
        )
    )
    transition_rows.sort(key=lambda row: int(row["phase_order"]))
    mixed.add_window_ratios(transition_rows, window_rows)
    for row in transition_rows:
        row["ramp_present"] = ramp_present(row)

    condition_rows = summarize_conditions(phase_rows, transition_rows)
    verdict_rows = build_verdict(experiment_label, condition_rows)

    analysis_dir = result_dir / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "phase_summary": analysis_dir / "phase_summary.csv",
        "window_summary": analysis_dir / "window_summary.csv",
        "transition_summary": analysis_dir / "transition_summary.csv",
        "idle_condition_summary": analysis_dir / "idle_condition_summary.csv",
        "verdict": analysis_dir / "verdict.csv",
        "analysis_manifest": analysis_dir / "analysis_manifest.json",
    }
    mixed.write_csv(paths["phase_summary"], phase_rows)
    mixed.write_csv(paths["window_summary"], window_rows)
    mixed.write_csv(paths["transition_summary"], transition_rows)
    mixed.write_csv(paths["idle_condition_summary"], condition_rows)
    mixed.write_csv(paths["verdict"], verdict_rows)

    manifest = {
        "schema_version": "1.0",
        "role": "analysis",
        "experiment_id": experiment_label,
        "test_protocol_id": PROTOCOL_ID,
        "created_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "status": "complete",
        "classification": "symmetric_idle_duration_ramp_observation",
        "analyzer": "scripts/analysis/analyze_external_ssd_idle_ramp.py",
        "source_artifacts": {
            "experiment_manifest": relative(experiment_path),
            "runner_manifest": relative(runner_path),
            "fio_json_count": len(runs),
            "fio_log_count": len(list(result_dir.glob("*.log"))),
        },
        "transition_definition": {
            "plateau_window": "last_third",
            "plateau_fraction": 0.80,
            "consecutive_samples": 5,
            "ramp_min_transition_sec": RAMP_MIN_TRANSITION_SEC,
            "ramp_min_plateau_over_first": RAMP_MIN_PLATEAU_OVER_FIRST,
        },
        "pair_consistency": {
            "required_repeat_count": 2,
            "transition_tolerance_sec": PAIR_TRANSITION_TOLERANCE_SEC,
        },
        "derived_artifacts": {
            key: relative(path)
            for key, path in paths.items()
            if key != "analysis_manifest"
        },
        "performance_verdict": verdict_rows[0]["performance_verdict"],
        "interpretation_boundary": verdict_rows[0]["interpretation_boundary"],
    }
    write_json(paths["analysis_manifest"], manifest)

    experiment["analysis_evidence"] = {
        "status": "complete",
        "analysis_manifest": relative(paths["analysis_manifest"]),
        "classification": manifest["classification"],
        "performance_verdict": manifest["performance_verdict"],
        "derived_artifacts": manifest["derived_artifacts"],
    }
    write_json(experiment_path, experiment)
    return paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--experiment-label",
        help="Experiment directory name; defaults to the latest complete idle-ramp run.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    experiment_label = args.experiment_label or latest_experiment_label()
    paths = analyze(experiment_label)
    for name, path in paths.items():
        print(f"[OK] {name}: {path}")


if __name__ == "__main__":
    main()
