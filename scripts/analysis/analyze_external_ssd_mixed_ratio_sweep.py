"""Analyze counterbalanced external-SSD mixed-ratio sweep evidence."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
RESULT_ROOT = REPO_ROOT / "results" / "external_ssd"
EXPERIMENT_ROOT = RESULT_ROOT / "_experiments"
SUPPORTED_PROTOCOLS = {
    "EXT-MIXED-RATIO-SWEEP-001",
    "EXT-MIXED-RATIO-SWEEP-REPRO-002",
}
PERCENTILES = {
    "p99": "99.000000",
    "p999": "99.900000",
}


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


def percentile_ms(direction: dict[str, Any], name: str) -> float | None:
    clat = direction.get("clat_ns") or {}
    value = (clat.get("percentile") or {}).get(PERCENTILES[name])
    return None if value is None else float(value) / 1_000_000.0


def direction_metrics(direction: dict[str, Any], prefix: str) -> dict[str, Any]:
    clat = direction.get("clat_ns") or {}
    return {
        f"{prefix}_bandwidth_mib_s": float(direction.get("bw_bytes", 0)) / (1024 * 1024),
        f"{prefix}_iops": float(direction.get("iops", 0)),
        f"{prefix}_clat_mean_ms": float(clat.get("mean", 0)) / 1_000_000.0,
        f"{prefix}_clat_p99_ms": percentile_ms(direction, "p99"),
        f"{prefix}_clat_p999_ms": percentile_ms(direction, "p999"),
        f"{prefix}_clat_max_ms": float(clat.get("max", 0)) / 1_000_000.0,
    }


def summarize_phase(run: dict[str, Any], fio: dict[str, Any]) -> dict[str, Any]:
    jobs = fio.get("jobs") or []
    if len(jobs) != 1:
        raise ValueError(f"Expected one fio job for phase {run['phase_order']}, found {len(jobs)}")
    job = jobs[0]
    if int(job.get("error", -1)) != 0:
        raise ValueError(f"fio error in phase {run['phase_order']}: {job.get('error')}")

    read = job.get("read") or {}
    write = job.get("write") or {}
    read_bytes = int(read.get("io_bytes", 0))
    write_bytes = int(write.get("io_bytes", 0))
    total_bytes = read_bytes + write_bytes
    if read_bytes <= 0 or write_bytes <= 0 or total_bytes <= 0:
        raise ValueError(f"Phase {run['phase_order']} does not contain mixed read/write I/O")

    row: dict[str, Any] = {
        "phase_order": int(run["phase_order"]),
        "cycle": int(run["cycle"]),
        "position": int(run["position"]),
        "ratio": run["ratio"],
        "requested_read_pct": float(run["read_pct"]),
        "requested_write_pct": float(run["write_pct"]),
        "observed_read_pct": read_bytes / total_bytes * 100.0,
        "observed_write_pct": write_bytes / total_bytes * 100.0,
        "fio_version": fio.get("fio version"),
        "job_error": int(job.get("error", -1)),
        "source_json": str(run["fio_json"]),
    }
    row.update(direction_metrics(read, "read"))
    row.update(direction_metrics(write, "write"))
    row["total_bandwidth_mib_s"] = (
        row["read_bandwidth_mib_s"] + row["write_bandwidth_mib_s"]
    )
    row["total_iops"] = row["read_iops"] + row["write_iops"]
    return row


def parse_log(path: Path) -> list[dict[str, float | int]]:
    rows: list[dict[str, float | int]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        fields = [field.strip() for field in line.split(",")]
        if len(fields) < 3:
            raise ValueError(f"Malformed fio log line {path}:{line_number}")
        rows.append(
            {
                "timestamp_ms": float(fields[0]),
                "value": float(fields[1]),
                "direction": int(fields[2]),
            }
        )
    if not rows:
        raise ValueError(f"Empty fio log: {path}")
    return rows


def mean(values: Iterable[float]) -> float:
    collected = list(values)
    if not collected:
        raise ValueError("Cannot calculate a mean from an empty sequence")
    return statistics.mean(collected)


def summarize_windows(
    run: dict[str, Any],
    runtime_sec: int,
) -> list[dict[str, Any]]:
    prefix = Path(run["log_prefix"])
    bw_rows = parse_log(Path(f"{prefix}_bw.1.log"))
    clat_rows = parse_log(Path(f"{prefix}_clat.1.log"))
    window_sec = runtime_sec / 3.0
    windows = (
        ("first", 0.0, window_sec),
        ("middle", window_sec, window_sec * 2),
        ("last", window_sec * 2, float("inf")),
    )
    output: list[dict[str, Any]] = []

    for label, low_sec, high_sec in windows:
        low_ms = low_sec * 1000.0
        high_ms = high_sec * 1000.0

        def selected(rows: list[dict[str, float | int]], direction: int) -> list[float]:
            return [
                float(row["value"])
                for row in rows
                if int(row["direction"]) == direction
                and float(row["timestamp_ms"]) > low_ms
                and float(row["timestamp_ms"]) <= high_ms
            ]

        read_bw = mean(selected(bw_rows, 0)) / 1024.0
        write_bw = mean(selected(bw_rows, 1)) / 1024.0
        output.append(
            {
                "phase_order": int(run["phase_order"]),
                "cycle": int(run["cycle"]),
                "position": int(run["position"]),
                "ratio": run["ratio"],
                "window": label,
                "read_bandwidth_mib_s": read_bw,
                "write_bandwidth_mib_s": write_bw,
                "total_bandwidth_mib_s": read_bw + write_bw,
                "read_clat_mean_ms": mean(selected(clat_rows, 0)) / 1_000_000.0,
                "write_clat_mean_ms": mean(selected(clat_rows, 1)) / 1_000_000.0,
            }
        )
    return output


def total_bandwidth_series(run: dict[str, Any]) -> list[dict[str, float]]:
    prefix = Path(run["log_prefix"])
    rows = parse_log(Path(f"{prefix}_bw.1.log"))
    by_timestamp: dict[float, float] = defaultdict(float)
    for row in rows:
        by_timestamp[float(row["timestamp_ms"])] += float(row["value"]) / 1024.0
    return [
        {
            "timestamp_sec": timestamp_ms / 1000.0,
            "total_bandwidth_mib_s": by_timestamp[timestamp_ms],
        }
        for timestamp_ms in sorted(by_timestamp)
    ]


def first_consecutive_at_or_above(
    series: list[dict[str, float]],
    threshold: float,
    consecutive_samples: int,
) -> float | None:
    if consecutive_samples < 1:
        raise ValueError("consecutive_samples must be positive")
    for index in range(0, len(series) - consecutive_samples + 1):
        window = series[index:index + consecutive_samples]
        if all(row["total_bandwidth_mib_s"] >= threshold for row in window):
            return float(window[0]["timestamp_sec"])
    return None


def summarize_transition(
    run: dict[str, Any],
    runtime_sec: int,
    plateau_fraction: float = 0.80,
    consecutive_samples: int = 5,
) -> dict[str, Any]:
    if not 0.0 < plateau_fraction <= 1.0:
        raise ValueError("plateau_fraction must be within (0, 1]")
    series = total_bandwidth_series(run)
    plateau_start_sec = runtime_sec * 2.0 / 3.0
    plateau_values = [
        row["total_bandwidth_mib_s"]
        for row in series
        if row["timestamp_sec"] > plateau_start_sec
    ]
    plateau_mean = mean(plateau_values)
    threshold = plateau_mean * plateau_fraction
    transition_sec = first_consecutive_at_or_above(
        series,
        threshold,
        consecutive_samples,
    )
    initial_values = [
        row["total_bandwidth_mib_s"]
        for row in series
        if row["timestamp_sec"] <= runtime_sec / 3.0
    ]
    initial_mean = mean(initial_values)
    return {
        "phase_order": int(run["phase_order"]),
        "cycle": int(run["cycle"]),
        "position": int(run["position"]),
        "ratio": run["ratio"],
        "plateau_window": "last_third",
        "plateau_bandwidth_mib_s": plateau_mean,
        "plateau_fraction": plateau_fraction,
        "transition_threshold_mib_s": threshold,
        "consecutive_samples": consecutive_samples,
        "transition_sec": transition_sec,
        "transition_found": transition_sec is not None,
        "first_third_bandwidth_mib_s": initial_mean,
        "plateau_over_first_third": plateau_mean / initial_mean,
    }


def add_window_ratios(
    transition_rows: list[dict[str, Any]],
    window_rows: list[dict[str, Any]],
) -> None:
    by_phase: dict[int, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in window_rows:
        by_phase[int(row["phase_order"])][str(row["window"])] = row
    for row in transition_rows:
        windows = by_phase[int(row["phase_order"])]
        first = windows["first"]
        last = windows["last"]
        row["last_over_first_total_bandwidth"] = (
            float(last["total_bandwidth_mib_s"])
            / float(first["total_bandwidth_mib_s"])
        )
        row["last_over_first_read_bandwidth"] = (
            float(last["read_bandwidth_mib_s"])
            / float(first["read_bandwidth_mib_s"])
        )
        row["last_over_first_write_bandwidth"] = (
            float(last["write_bandwidth_mib_s"])
            / float(first["write_bandwidth_mib_s"])
        )
        row["last_over_first_read_clat"] = (
            float(last["read_clat_mean_ms"])
            / float(first["read_clat_mean_ms"])
        )
        row["last_over_first_write_clat"] = (
            float(last["write_clat_mean_ms"])
            / float(first["write_clat_mean_ms"])
        )

def sample_stdev(values: list[float]) -> float:
    return statistics.stdev(values) if len(values) > 1 else 0.0


def grouped_summary(
    phase_rows: list[dict[str, Any]],
    group_field: str,
    output_field: str,
) -> list[dict[str, Any]]:
    groups: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for row in phase_rows:
        groups[row[group_field]].append(row)

    output: list[dict[str, Any]] = []
    for group_value, rows in sorted(groups.items(), key=lambda item: str(item[0])):
        total_bw = [float(row["total_bandwidth_mib_s"]) for row in rows]
        read_p99 = [float(row["read_clat_p99_ms"]) for row in rows]
        read_p999 = [float(row["read_clat_p999_ms"]) for row in rows]
        write_p99 = [float(row["write_clat_p99_ms"]) for row in rows]
        write_p999 = [float(row["write_clat_p999_ms"]) for row in rows]
        total_mean = statistics.mean(total_bw)
        output.append(
            {
                output_field: group_value,
                "sample_count": len(rows),
                "total_bandwidth_mib_s_mean": total_mean,
                "total_bandwidth_mib_s_min": min(total_bw),
                "total_bandwidth_mib_s_max": max(total_bw),
                "total_bandwidth_mib_s_stdev": sample_stdev(total_bw),
                "total_bandwidth_mib_s_cv": (
                    sample_stdev(total_bw) / total_mean if total_mean else None
                ),
                "read_bandwidth_mib_s_mean": statistics.mean(
                    float(row["read_bandwidth_mib_s"]) for row in rows
                ),
                "write_bandwidth_mib_s_mean": statistics.mean(
                    float(row["write_bandwidth_mib_s"]) for row in rows
                ),
                "read_clat_p99_ms_mean": statistics.mean(read_p99),
                "read_clat_p99_ms_min": min(read_p99),
                "read_clat_p99_ms_max": max(read_p99),
                "read_clat_p999_ms_mean": statistics.mean(read_p999),
                "read_clat_p999_ms_min": min(read_p999),
                "read_clat_p999_ms_max": max(read_p999),
                "write_clat_p99_ms_mean": statistics.mean(write_p99),
                "write_clat_p999_ms_mean": statistics.mean(write_p999),
            }
        )
    return output


def cycle_position_summary(phase_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for field, dimension in (("cycle", "cycle"), ("position", "position")):
        for row in grouped_summary(phase_rows, field, "level"):
            output.append({"dimension": dimension, **row})
    return output


def detect_anomalies(
    phase_rows: list[dict[str, Any]],
    window_rows: list[dict[str, Any]],
    late_shift_threshold: float = 0.30,
    max_latency_threshold_ms: float = 100.0,
) -> list[dict[str, Any]]:
    by_phase: dict[int, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in window_rows:
        by_phase[int(row["phase_order"])][str(row["window"])] = row

    anomalies: list[dict[str, Any]] = []
    for phase in phase_rows:
        phase_order = int(phase["phase_order"])
        windows = by_phase[phase_order]
        first_bw = float(windows["first"]["total_bandwidth_mib_s"])
        last_bw = float(windows["last"]["total_bandwidth_mib_s"])
        ratio = last_bw / first_bw
        common = {
            "phase_order": phase_order,
            "cycle": phase["cycle"],
            "position": phase["position"],
            "ratio": phase["ratio"],
        }
        if ratio <= 1.0 - late_shift_threshold:
            anomalies.append(
                {
                    **common,
                    "anomaly_type": "late_bandwidth_drop",
                    "metric": "last_over_first_total_bandwidth",
                    "observed_value": ratio,
                    "threshold": f"<= {1.0 - late_shift_threshold}",
                }
            )
        elif ratio >= 1.0 + late_shift_threshold:
            anomalies.append(
                {
                    **common,
                    "anomaly_type": "late_bandwidth_rise",
                    "metric": "last_over_first_total_bandwidth",
                    "observed_value": ratio,
                    "threshold": f">= {1.0 + late_shift_threshold}",
                }
            )

        max_latency = max(
            float(phase["read_clat_max_ms"]),
            float(phase["write_clat_max_ms"]),
        )
        if max_latency >= max_latency_threshold_ms:
            anomalies.append(
                {
                    **common,
                    "anomaly_type": "maximum_latency_outlier",
                    "metric": "max_direction_clat_ms",
                    "observed_value": max_latency,
                    "threshold": f">= {max_latency_threshold_ms}",
                }
            )
    return anomalies


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def ranked_labels(
    rows: list[dict[str, Any]],
    label_field: str,
    metric_field: str,
    descending: bool,
) -> list[str]:
    return [
        str(row[label_field])
        for row in sorted(
            rows,
            key=lambda row: float(row[metric_field]),
            reverse=descending,
        )
    ]


def shift_direction(value: float, threshold: float = 0.30) -> str:
    if value <= 1.0 - threshold:
        return "drop"
    if value >= 1.0 + threshold:
        return "rise"
    return "stable"


def cross_session_evidence(
    session1: dict[str, Any],
    session2: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ratio1 = {row["ratio"]: row for row in session1["ratio_rows"]}
    ratio2 = {row["ratio"]: row for row in session2["ratio_rows"]}
    ratios = sorted(set(ratio1) & set(ratio2), reverse=True)
    if ratios != ["90:10", "70:30", "50:50"]:
        raise ValueError(f"Expected three matched ratios, found {ratios}")

    bw_rank1 = ranked_labels(
        list(ratio1.values()), "ratio", "total_bandwidth_mib_s_mean", True
    )
    bw_rank2 = ranked_labels(
        list(ratio2.values()), "ratio", "total_bandwidth_mib_s_mean", True
    )
    p99_rank1 = ranked_labels(
        list(ratio1.values()), "ratio", "read_clat_p99_ms_mean", False
    )
    p99_rank2 = ranked_labels(
        list(ratio2.values()), "ratio", "read_clat_p99_ms_mean", False
    )
    rank_position1 = {ratio: index + 1 for index, ratio in enumerate(bw_rank1)}
    rank_position2 = {ratio: index + 1 for index, ratio in enumerate(bw_rank2)}

    comparison_rows: list[dict[str, Any]] = []
    for ratio in ratios:
        first = ratio1[ratio]
        second = ratio2[ratio]
        first_bw = float(first["total_bandwidth_mib_s_mean"])
        second_bw = float(second["total_bandwidth_mib_s_mean"])
        first_p99 = float(first["read_clat_p99_ms_mean"])
        second_p99 = float(second["read_clat_p99_ms_mean"])
        first_p999 = float(first["read_clat_p999_ms_mean"])
        second_p999 = float(second["read_clat_p999_ms_mean"])
        comparison_rows.append({
            "ratio": ratio,
            "session1_experiment_id": session1["experiment_id"],
            "session2_experiment_id": session2["experiment_id"],
            "session1_total_bandwidth_mib_s_mean": first_bw,
            "session2_total_bandwidth_mib_s_mean": second_bw,
            "session2_vs_session1_total_bandwidth_delta_pct": (
                second_bw / first_bw - 1.0
            ) * 100.0,
            "session1_total_bandwidth_cv": float(first["total_bandwidth_mib_s_cv"]),
            "session2_total_bandwidth_cv": float(second["total_bandwidth_mib_s_cv"]),
            "session1_bandwidth_rank": rank_position1[ratio],
            "session2_bandwidth_rank": rank_position2[ratio],
            "session1_read_clat_p99_ms_mean": first_p99,
            "session2_read_clat_p99_ms_mean": second_p99,
            "session2_vs_session1_read_p99_delta_pct": (
                second_p99 / first_p99 - 1.0
            ) * 100.0,
            "session1_read_clat_p999_ms_mean": first_p999,
            "session2_read_clat_p999_ms_mean": second_p999,
            "session2_vs_session1_read_p999_delta_pct": (
                second_p999 / first_p999 - 1.0
            ) * 100.0,
        })

    dimensions1 = session1["dimension_rows"]
    dimensions2 = session2["dimension_rows"]
    cycle1 = [row for row in dimensions1 if row["dimension"] == "cycle"]
    cycle2 = [row for row in dimensions2 if row["dimension"] == "cycle"]
    position1 = [row for row in dimensions1 if row["dimension"] == "position"]
    position2 = [row for row in dimensions2 if row["dimension"] == "position"]
    cycle_rank1 = ranked_labels(cycle1, "level", "total_bandwidth_mib_s_mean", True)
    cycle_rank2 = ranked_labels(cycle2, "level", "total_bandwidth_mib_s_mean", True)
    position_rank1 = ranked_labels(
        position1, "level", "total_bandwidth_mib_s_mean", True
    )
    position_rank2 = ranked_labels(
        position2, "level", "total_bandwidth_mib_s_mean", True
    )

    transition1 = session1["transition_rows"]
    transition2 = session2["transition_rows"]
    phase5_1 = next(row for row in transition1 if int(row["phase_order"]) == 5)
    phase5_2 = next(row for row in transition2 if int(row["phase_order"]) == 5)
    phase5_ratio1 = float(phase5_1["last_over_first_total_bandwidth"])
    phase5_ratio2 = float(phase5_2["last_over_first_total_bandwidth"])
    phase5_direction1 = shift_direction(phase5_ratio1)
    phase5_direction2 = shift_direction(phase5_ratio2)

    def transition_seconds(rows: list[dict[str, Any]]) -> list[float]:
        return [
            float(row["transition_sec"])
            for row in rows
            if row.get("transition_sec") not in (None, "")
        ]

    transition_sec1 = transition_seconds(transition1)
    transition_sec2 = transition_seconds(transition2)

    def ramp_count(rows: list[dict[str, Any]]) -> int:
        return sum(
            row.get("transition_sec") not in (None, "")
            and 30.0 <= float(row["transition_sec"]) <= 60.0
            and float(row["plateau_over_first_third"]) >= 1.30
            for row in rows
        )

    ramp_count1 = ramp_count(transition1)
    ramp_count2 = ramp_count(transition2)
    phase_rows1 = session1["phase_rows"]
    phase_rows2 = session2["phase_rows"]

    def aggregate(rows: list[dict[str, Any]], field: str) -> float:
        return statistics.mean(float(row[field]) for row in rows)

    critical_reproduced = (
        bw_rank1 == bw_rank2
        and p99_rank1 == p99_rank2
        and cycle_rank1 == cycle_rank2
        and position_rank1 == position_rank2
        and phase5_direction1 == phase5_direction2
        and ramp_count1 == ramp_count2
    )
    verdict_rows = [{
        "study_id": "mixed_ratio_sweep_cross_session",
        "session1_experiment_id": session1["experiment_id"],
        "session2_experiment_id": session2["experiment_id"],
        "complete_session_count": 2,
        "requirement_verdict": "Pass",
        "session1_total_bandwidth_mib_s_mean": aggregate(
            phase_rows1, "total_bandwidth_mib_s"
        ),
        "session2_total_bandwidth_mib_s_mean": aggregate(
            phase_rows2, "total_bandwidth_mib_s"
        ),
        "session1_read_p99_ms_mean": aggregate(phase_rows1, "read_clat_p99_ms"),
        "session2_read_p99_ms_mean": aggregate(phase_rows2, "read_clat_p99_ms"),
        "session1_read_p999_ms_mean": aggregate(
            phase_rows1, "read_clat_p999_ms"
        ),
        "session2_read_p999_ms_mean": aggregate(
            phase_rows2, "read_clat_p999_ms"
        ),
        "session1_bandwidth_rank": ">".join(bw_rank1),
        "session2_bandwidth_rank": ">".join(bw_rank2),
        "bandwidth_rank_reproduced": bw_rank1 == bw_rank2,
        "session1_read_p99_rank_best_to_worst": ">".join(p99_rank1),
        "session2_read_p99_rank_best_to_worst": ">".join(p99_rank2),
        "read_p99_rank_reproduced": p99_rank1 == p99_rank2,
        "session1_cycle_bandwidth_rank": ">".join(cycle_rank1),
        "session2_cycle_bandwidth_rank": ">".join(cycle_rank2),
        "cycle_rank_reproduced": cycle_rank1 == cycle_rank2,
        "session1_position_bandwidth_rank": ">".join(position_rank1),
        "session2_position_bandwidth_rank": ">".join(position_rank2),
        "position_rank_reproduced": position_rank1 == position_rank2,
        "session1_phase5_ratio": phase5_1["ratio"],
        "session2_phase5_ratio": phase5_2["ratio"],
        "session1_phase5_last_over_first_bandwidth": phase5_ratio1,
        "session2_phase5_last_over_first_bandwidth": phase5_ratio2,
        "session1_phase5_direction": phase5_direction1,
        "session2_phase5_direction": phase5_direction2,
        "phase5_direction_reproduced": phase5_direction1 == phase5_direction2,
        "session1_transition_sec_median": statistics.median(transition_sec1),
        "session2_transition_sec_median": statistics.median(transition_sec2),
        "session1_ramp_30_60_sec_phase_count": ramp_count1,
        "session2_ramp_30_60_sec_phase_count": ramp_count2,
        "ramp_pattern_reproduced": ramp_count1 == ramp_count2,
        "performance_verdict": (
            "reproduced_across_independent_counterbalanced_sessions"
            if critical_reproduced
            else "not_reproduced_across_independent_counterbalanced_sessions"
        ),
        "interpretation_boundary": (
            "USB, Windows, exFAT file-target evidence; cross-session disagreement "
            "does not identify a device-internal root cause"
        ),
    }]
    return comparison_rows, verdict_rows


def complete_experiment_by_protocol(protocol_id: str) -> tuple[str, Path] | None:
    candidates: list[tuple[str, Path]] = []
    for path in EXPERIMENT_ROOT.glob("*/experiment_manifest.json"):
        manifest = read_json(path)
        if manifest.get("test_protocol_id") == protocol_id and manifest.get("status") == "complete":
            candidates.append((str(manifest["started_at"]), path))
    if not candidates:
        return None
    _, path = max(candidates, key=lambda item: item[0])
    return path.parent.name, path


def load_session_analysis(experiment_label: str) -> dict[str, Any]:
    analysis_dir = RESULT_ROOT / f"sustained_{experiment_label}" / "analysis"
    required = {
        "phase_rows": analysis_dir / "phase_summary.csv",
        "ratio_rows": analysis_dir / "ratio_summary.csv",
        "dimension_rows": analysis_dir / "cycle_position_summary.csv",
        "transition_rows": analysis_dir / "transition_summary.csv",
    }
    missing = [path for path in required.values() if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "Missing analysis artifacts for "
            f"{experiment_label}: {', '.join(str(path) for path in missing)}"
        )
    return {
        "experiment_id": experiment_label,
        **{name: read_csv(path) for name, path in required.items()},
    }

def latest_experiment_label() -> str:
    candidates: list[tuple[float, str]] = []
    for path in EXPERIMENT_ROOT.glob("*/experiment_manifest.json"):
        manifest = read_json(path)
        if (
            manifest.get("test_protocol_id") in SUPPORTED_PROTOCOLS
            and manifest.get("status") == "complete"
        ):
            candidates.append((path.stat().st_mtime, str(manifest["experiment_id"])))
    if not candidates:
        raise SystemExit("No complete mixed-ratio sweep experiment found.")
    return max(candidates)[1]


def relative(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def analyze(experiment_label: str, include_cross_session: bool = True) -> dict[str, Path]:
    experiment_path = EXPERIMENT_ROOT / experiment_label / "experiment_manifest.json"
    if not experiment_path.exists():
        raise FileNotFoundError(experiment_path)
    experiment = read_json(experiment_path)
    if experiment.get("test_protocol_id") not in SUPPORTED_PROTOCOLS:
        raise ValueError(f"Unsupported protocol: {experiment.get('test_protocol_id')}")
    if experiment.get("status") != "complete":
        raise ValueError(f"Experiment is not complete: {experiment_path}")

    run_label = f"sustained_{experiment_label}"
    result_dir = RESULT_ROOT / run_label
    runner_path = result_dir / "runner_manifest.json"
    runner = read_json(runner_path)
    runs = runner.get("runs") or []
    if runner.get("status") != "complete" or len(runs) != 9:
        raise ValueError(f"Expected complete runner with 9 phases: {runner_path}")

    runtime_sec = int(experiment["fixed_controls"]["runtime_sec"])
    phase_rows: list[dict[str, Any]] = []
    window_rows: list[dict[str, Any]] = []
    transition_rows: list[dict[str, Any]] = []
    for run in runs:
        fio_path = Path(run["fio_json"])
        phase_row = summarize_phase(run, read_json(fio_path))
        phase_row["source_json"] = relative(fio_path)
        phase_rows.append(phase_row)
        window_rows.extend(summarize_windows(run, runtime_sec))
        transition_rows.append(summarize_transition(run, runtime_sec))

    phase_rows.sort(key=lambda row: int(row["phase_order"]))
    window_rows.sort(
        key=lambda row: (
            int(row["phase_order"]),
            {"first": 0, "middle": 1, "last": 2}[str(row["window"])],
        )
    )
    transition_rows.sort(key=lambda row: int(row["phase_order"]))
    add_window_ratios(transition_rows, window_rows)
    transition_rows = [
        {"experiment_id": experiment_label, **row}
        for row in transition_rows
    ]
    ratio_rows = grouped_summary(phase_rows, "ratio", "ratio")
    dimension_rows = cycle_position_summary(phase_rows)
    anomaly_rows = detect_anomalies(phase_rows, window_rows)

    analysis_dir = result_dir / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "phase_summary": analysis_dir / "phase_summary.csv",
        "ratio_summary": analysis_dir / "ratio_summary.csv",
        "cycle_position_summary": analysis_dir / "cycle_position_summary.csv",
        "window_summary": analysis_dir / "window_summary.csv",
        "transition_summary": analysis_dir / "transition_summary.csv",
        "anomalies": analysis_dir / "anomalies.csv",
        "analysis_manifest": analysis_dir / "analysis_manifest.json",
    }
    write_csv(paths["phase_summary"], phase_rows)
    write_csv(paths["ratio_summary"], ratio_rows)
    write_csv(paths["cycle_position_summary"], dimension_rows)
    write_csv(paths["window_summary"], window_rows)
    write_csv(paths["transition_summary"], transition_rows)
    write_csv(
        paths["anomalies"],
        anomaly_rows
        or [{
            "phase_order": "",
            "cycle": "",
            "position": "",
            "ratio": "",
            "anomaly_type": "none",
            "metric": "",
            "observed_value": "",
            "threshold": "",
        }],
    )

    cross_session_summary: dict[str, Any] = {"available": False}
    if include_cross_session:
        session1_match = complete_experiment_by_protocol("EXT-MIXED-RATIO-SWEEP-001")
        session2_match = complete_experiment_by_protocol(
            "EXT-MIXED-RATIO-SWEEP-REPRO-002"
        )
        if session1_match and session2_match:
            session1_label, _ = session1_match
            session2_label, _ = session2_match
            for label in (session1_label, session2_label):
                transition_path = (
                    RESULT_ROOT
                    / f"sustained_{label}"
                    / "analysis"
                    / "transition_summary.csv"
                )
                if not transition_path.exists() and label != experiment_label:
                    analyze(label, include_cross_session=False)
            session1 = load_session_analysis(session1_label)
            session2 = load_session_analysis(session2_label)
            comparison_rows, verdict_rows = cross_session_evidence(session1, session2)
            paths["cross_session_ratio_comparison"] = (
                analysis_dir / "cross_session_ratio_comparison.csv"
            )
            paths["cross_session_verdict"] = (
                analysis_dir / "cross_session_verdict.csv"
            )
            write_csv(paths["cross_session_ratio_comparison"], comparison_rows)
            write_csv(paths["cross_session_verdict"], verdict_rows)
            cross_session_summary = {
                "available": True,
                "session1_experiment_id": session1_label,
                "session2_experiment_id": session2_label,
                "performance_verdict": verdict_rows[0]["performance_verdict"],
                "ratio_comparison": relative(
                    paths["cross_session_ratio_comparison"]
                ),
                "verdict": relative(paths["cross_session_verdict"]),
            }
    manifest = {
        "schema_version": "1.0",
        "role": "analysis",
        "experiment_id": experiment_label,
        "test_protocol_id": experiment["test_protocol_id"],
        "created_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "status": "complete",
        "classification": "descriptive_ratio_by_cycle_by_position_mapping",
        "hypothesis_status": experiment.get("hypothesis_status"),
        "analyzer": "scripts/analysis/analyze_external_ssd_mixed_ratio_sweep.py",
        "source_artifacts": {
            "experiment_manifest": relative(experiment_path),
            "runner_manifest": relative(runner_path),
            "fio_json_count": len(runs),
            "fio_log_count": len(list(result_dir.glob("*.log"))),
        },
        "derived_artifacts": {
            key: relative(path)
            for key, path in paths.items()
            if key != "analysis_manifest"
        },
        "anomaly_thresholds": {
            "late_total_bandwidth_shift_fraction": 0.30,
            "maximum_completion_latency_ms": 100.0,
        },
        "transition_definition": {
            "plateau_window": "last_third",
            "plateau_fraction": 0.80,
            "consecutive_samples": 5,
            "metric": "total_bandwidth_mib_s",
        },
        "anomaly_count": len(anomaly_rows),
        "cross_session": cross_session_summary,
        "interpretation_boundary": (
            "USB, Windows, exFAT file-target evidence; balanced ratio means are "
            "descriptive and do not prove a device-internal causal mechanism."
        ),
    }
    write_json(paths["analysis_manifest"], manifest)
    experiment["analysis_evidence"] = {
        "status": "complete",
        "analysis_manifest": relative(paths["analysis_manifest"]),
        "classification": manifest["classification"],
        "anomaly_count": len(anomaly_rows),
        "cross_session": cross_session_summary,
        "derived_artifacts": manifest["derived_artifacts"],
    }
    write_json(experiment_path, experiment)
    return paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--experiment-label",
        help="Experiment directory name; defaults to the latest complete supported sweep.",
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
