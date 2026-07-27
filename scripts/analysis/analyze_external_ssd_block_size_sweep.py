"""Analyze controlled 4K/64K/1M external-SSD block-size sweeps."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
RESULT_ROOT = REPO_ROOT / "results" / "external_ssd"
EXPERIMENT_ROOT = RESULT_ROOT / "_experiments"
PROTOCOL_WORKLOADS = {
    "EXT-BS-RANDREAD-001": "randread",
    "EXT-BS-RANDWRITE-002": "randwrite",
}
BLOCK_SIZE_ORDER = {"4k": 0, "64k": 1, "1m": 2}
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


def normalize_block_size(value: str) -> str:
    normalized = value.strip().lower()
    aliases = {
        "4096": "4k",
        "65536": "64k",
        "1048576": "1m",
        "1024k": "1m",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized not in BLOCK_SIZE_ORDER:
        raise ValueError(f"Unsupported block size: {value}")
    return normalized


def sample_stdev(values: list[float]) -> float:
    return statistics.stdev(values) if len(values) > 1 else 0.0


def cv(values: list[float]) -> float:
    mean_value = statistics.mean(values)
    return sample_stdev(values) / mean_value if mean_value else 0.0


def percentile_ms(direction: dict[str, Any], key: str) -> float | None:
    clat = direction.get("clat_ns") or {}
    value = (clat.get("percentile") or {}).get(PERCENTILES[key])
    return None if value is None else float(value) / 1_000_000.0


def summarize_phase(
    run: dict[str, Any],
    fio: dict[str, Any],
    expected_workload: str,
) -> dict[str, Any]:
    jobs = fio.get("jobs") or []
    if len(jobs) != 1:
        raise ValueError(
            f"Expected one fio job for phase {run['phase_order']}, found {len(jobs)}"
        )
    job = jobs[0]
    if int(job.get("error", -1)) != 0:
        raise ValueError(
            f"fio error in phase {run['phase_order']}: {job.get('error')}"
        )

    operation = "read" if expected_workload == "randread" else "write"
    opposite = "write" if operation == "read" else "read"
    direction = job.get(operation) or {}
    opposite_direction = job.get(opposite) or {}
    if int(direction.get("io_bytes", 0)) <= 0:
        raise ValueError(f"Phase {run['phase_order']} has no {operation} bytes")
    if int(opposite_direction.get("io_bytes", 0)) != 0:
        raise ValueError(f"Phase {run['phase_order']} contains unexpected {opposite} I/O")

    requested_bs = normalize_block_size(str(run["block_size"]))
    observed_bs = normalize_block_size(
        str((job.get("job options") or {}).get("bs", requested_bs))
    )
    if observed_bs != requested_bs:
        raise ValueError(
            f"Phase {run['phase_order']} block-size mismatch: "
            f"requested={requested_bs}, observed={observed_bs}"
        )

    clat = direction.get("clat_ns") or {}
    return {
        "phase_order": int(run["phase_order"]),
        "cycle": int(run["cycle"]),
        "position": int(run["position"]),
        "workload": expected_workload,
        "operation": operation,
        "block_size": requested_bs,
        "fio_version": fio.get("fio version"),
        "job_error": int(job.get("error", -1)),
        "io_bytes": int(direction.get("io_bytes", 0)),
        "bandwidth_mib_s": float(direction.get("bw_bytes", 0)) / (1024 * 1024),
        "iops": float(direction.get("iops", 0)),
        "clat_mean_ms": float(clat.get("mean", 0)) / 1_000_000.0,
        "clat_p99_ms": percentile_ms(direction, "p99"),
        "clat_p999_ms": percentile_ms(direction, "p999"),
        "clat_max_ms": float(clat.get("max", 0)) / 1_000_000.0,
        "source_json": str(run["fio_json"]),
    }


def validate_balance(rows: list[dict[str, Any]]) -> None:
    if len(rows) != 9:
        raise ValueError(f"Expected 9 phases, found {len(rows)}")
    for block_size in BLOCK_SIZE_ORDER:
        selected = [row for row in rows if row["block_size"] == block_size]
        if len(selected) != 3:
            raise ValueError(
                f"Expected three {block_size} phases, found {len(selected)}"
            )
        if {int(row["cycle"]) for row in selected} != {1, 2, 3}:
            raise ValueError(f"{block_size} is not represented in every cycle")
        if {int(row["position"]) for row in selected} != {1, 2, 3}:
            raise ValueError(f"{block_size} is not represented in every position")


def summarize_block_sizes(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    validate_balance(rows)
    output: list[dict[str, Any]] = []
    for block_size in BLOCK_SIZE_ORDER:
        selected = [row for row in rows if row["block_size"] == block_size]

        def values(field: str) -> list[float]:
            return [float(row[field]) for row in selected]

        output.append({
            "workload": selected[0]["workload"],
            "operation": selected[0]["operation"],
            "block_size": block_size,
            "repeat_count": len(selected),
            "phase_orders": ",".join(str(row["phase_order"]) for row in selected),
            "positions": ",".join(str(row["position"]) for row in selected),
            "bandwidth_mib_s_mean": statistics.mean(values("bandwidth_mib_s")),
            "bandwidth_mib_s_stdev": sample_stdev(values("bandwidth_mib_s")),
            "bandwidth_mib_s_cv": cv(values("bandwidth_mib_s")),
            "iops_mean": statistics.mean(values("iops")),
            "iops_stdev": sample_stdev(values("iops")),
            "iops_cv": cv(values("iops")),
            "clat_mean_ms_mean": statistics.mean(values("clat_mean_ms")),
            "clat_p99_ms_mean": statistics.mean(values("clat_p99_ms")),
            "clat_p99_ms_cv": cv(values("clat_p99_ms")),
            "clat_p999_ms_mean": statistics.mean(values("clat_p999_ms")),
            "clat_p999_ms_cv": cv(values("clat_p999_ms")),
            "clat_max_ms_max": max(values("clat_max_ms")),
        })
    return output


def summarize_dimensions(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for dimension in ("cycle", "position"):
        groups: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            groups[int(row[dimension])].append(row)
        for level in sorted(groups):
            selected = groups[level]
            output.append({
                "workload": selected[0]["workload"],
                "dimension": dimension,
                "level": level,
                "phase_count": len(selected),
                "block_sizes": ",".join(
                    sorted(
                        (str(row["block_size"]) for row in selected),
                        key=lambda item: BLOCK_SIZE_ORDER[item],
                    )
                ),
                "bandwidth_mib_s_mean": statistics.mean(
                    float(row["bandwidth_mib_s"]) for row in selected
                ),
                "iops_mean": statistics.mean(float(row["iops"]) for row in selected),
                "clat_p99_ms_mean": statistics.mean(
                    float(row["clat_p99_ms"]) for row in selected
                ),
                "clat_p999_ms_mean": statistics.mean(
                    float(row["clat_p999_ms"]) for row in selected
                ),
            })
    return output


def compare_workloads(
    read_rows: list[dict[str, Any]],
    write_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    read_by_bs = {row["block_size"]: row for row in read_rows}
    write_by_bs = {row["block_size"]: row for row in write_rows}
    if set(read_by_bs) != set(BLOCK_SIZE_ORDER) or set(write_by_bs) != set(BLOCK_SIZE_ORDER):
        raise ValueError("Both workload summaries must contain 4k, 64k, and 1m")

    output: list[dict[str, Any]] = []
    for block_size in BLOCK_SIZE_ORDER:
        read = read_by_bs[block_size]
        write = write_by_bs[block_size]
        output.append({
            "block_size": block_size,
            "read_bandwidth_mib_s_mean": read["bandwidth_mib_s_mean"],
            "write_bandwidth_mib_s_mean": write["bandwidth_mib_s_mean"],
            "write_over_read_bandwidth": (
                float(write["bandwidth_mib_s_mean"])
                / float(read["bandwidth_mib_s_mean"])
            ),
            "read_iops_mean": read["iops_mean"],
            "write_iops_mean": write["iops_mean"],
            "write_over_read_iops": (
                float(write["iops_mean"]) / float(read["iops_mean"])
            ),
            "read_clat_p99_ms_mean": read["clat_p99_ms_mean"],
            "write_clat_p99_ms_mean": write["clat_p99_ms_mean"],
            "write_over_read_p99": (
                float(write["clat_p99_ms_mean"])
                / float(read["clat_p99_ms_mean"])
            ),
            "read_clat_p999_ms_mean": read["clat_p999_ms_mean"],
            "write_clat_p999_ms_mean": write["clat_p999_ms_mean"],
            "write_over_read_p999": (
                float(write["clat_p999_ms_mean"])
                / float(read["clat_p999_ms_mean"])
            ),
            "interpretation_boundary": (
                "descriptive comparison across independent read/write sessions"
            ),
        })
    return output


def load_session(experiment_label: str) -> dict[str, Any]:
    experiment_path = EXPERIMENT_ROOT / experiment_label / "experiment_manifest.json"
    experiment = read_json(experiment_path)
    protocol_id = str(experiment.get("test_protocol_id"))
    if protocol_id not in PROTOCOL_WORKLOADS:
        raise ValueError(f"Unsupported protocol: {protocol_id}")
    if experiment.get("status") != "complete":
        raise ValueError(f"Experiment is not complete: {experiment_path}")

    result_dir = RESULT_ROOT / f"sustained_{experiment_label}"
    runner_path = result_dir / "runner_manifest.json"
    runner = read_json(runner_path)
    runs = runner.get("runs") or []
    if runner.get("status") != "complete" or len(runs) != 9:
        raise ValueError(f"Expected complete runner with 9 phases: {runner_path}")

    workload = PROTOCOL_WORKLOADS[protocol_id]
    phase_rows = [
        summarize_phase(run, read_json(Path(run["fio_json"])), workload)
        for run in runs
    ]
    phase_rows.sort(key=lambda row: int(row["phase_order"]))
    validate_balance(phase_rows)
    summary_rows = summarize_block_sizes(phase_rows)
    dimension_rows = summarize_dimensions(phase_rows)

    analysis_dir = result_dir / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "phase_summary": analysis_dir / "phase_summary.csv",
        "block_size_summary": analysis_dir / "block_size_summary.csv",
        "cycle_position_summary": analysis_dir / "cycle_position_summary.csv",
        "analysis_manifest": analysis_dir / "analysis_manifest.json",
    }
    write_csv(paths["phase_summary"], phase_rows)
    write_csv(paths["block_size_summary"], summary_rows)
    write_csv(paths["cycle_position_summary"], dimension_rows)

    manifest = {
        "schema_version": "1.0",
        "role": "analysis",
        "experiment_id": experiment_label,
        "test_protocol_id": protocol_id,
        "created_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "status": "complete",
        "classification": "counterbalanced_block_size_mapping",
        "analyzer": "scripts/analysis/analyze_external_ssd_block_size_sweep.py",
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
        "interpretation_boundary": (
            "Random file-target block-size mapping over USB, Windows, and exFAT; "
            "no device-internal root-cause claim."
        ),
    }
    write_json(paths["analysis_manifest"], manifest)

    experiment["analysis_evidence"] = {
        "status": "complete",
        "analysis_manifest": relative(paths["analysis_manifest"]),
        "classification": manifest["classification"],
        "derived_artifacts": manifest["derived_artifacts"],
    }
    write_json(experiment_path, experiment)
    return {
        "experiment_id": experiment_label,
        "protocol_id": protocol_id,
        "workload": workload,
        "result_dir": result_dir,
        "analysis_dir": analysis_dir,
        "phase_rows": phase_rows,
        "summary_rows": summary_rows,
        "dimension_rows": dimension_rows,
        "paths": paths,
    }


def analyze_pair(read_label: str, write_label: str) -> dict[str, Path]:
    read_session = load_session(read_label)
    write_session = load_session(write_label)
    if read_session["workload"] != "randread":
        raise ValueError(f"Expected randread session: {read_label}")
    if write_session["workload"] != "randwrite":
        raise ValueError(f"Expected randwrite session: {write_label}")

    comparison_rows = compare_workloads(
        read_session["summary_rows"],
        write_session["summary_rows"],
    )
    verdict_rows = [{
        "read_experiment_id": read_label,
        "write_experiment_id": write_label,
        "requirement_id": "REQ-BS-008",
        "requirement_verdict": "Pass",
        "read_phase_count": len(read_session["phase_rows"]),
        "write_phase_count": len(write_session["phase_rows"]),
        "block_sizes": "4k,64k,1m",
        "repeats_per_block_size_per_workload": 3,
        "sequence_balance": "each block size appears once in every cycle and position",
        "performance_verdict": "descriptive_block_size_mapping_complete",
        "interpretation_boundary": (
            "Read and write were independent reconnect-start sessions; "
            "cross-workload ratios are descriptive, not causal."
        ),
    }]

    analysis_dir = write_session["analysis_dir"]
    paths = {
        "cross_workload_comparison": analysis_dir / "cross_workload_comparison.csv",
        "verdict": analysis_dir / "verdict.csv",
        "paired_analysis_manifest": analysis_dir / "paired_analysis_manifest.json",
    }
    write_csv(paths["cross_workload_comparison"], comparison_rows)
    write_csv(paths["verdict"], verdict_rows)

    manifest = {
        "schema_version": "1.0",
        "role": "paired_analysis",
        "created_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "status": "complete",
        "classification": "controlled_read_write_block_size_mapping",
        "analyzer": "scripts/analysis/analyze_external_ssd_block_size_sweep.py",
        "source_experiments": {
            "randread": read_label,
            "randwrite": write_label,
        },
        "session_analysis_manifests": {
            "randread": relative(read_session["paths"]["analysis_manifest"]),
            "randwrite": relative(write_session["paths"]["analysis_manifest"]),
        },
        "derived_artifacts": {
            key: relative(path)
            for key, path in paths.items()
            if key != "paired_analysis_manifest"
        },
        "requirement_verdict": "Pass",
        "performance_verdict": "descriptive_block_size_mapping_complete",
        "interpretation_boundary": verdict_rows[0]["interpretation_boundary"],
    }
    write_json(paths["paired_analysis_manifest"], manifest)

    for session in (read_session, write_session):
        experiment_path = (
            EXPERIMENT_ROOT / session["experiment_id"] / "experiment_manifest.json"
        )
        experiment = read_json(experiment_path)
        experiment.setdefault("analysis_evidence", {})["paired_analysis"] = {
            "status": "complete",
            "paired_analysis_manifest": relative(paths["paired_analysis_manifest"]),
            "performance_verdict": manifest["performance_verdict"],
        }
        write_json(experiment_path, experiment)
    return paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--experiment-label",
        help="Analyze one completed randread or randwrite block-size session.",
    )
    parser.add_argument("--read-experiment-label")
    parser.add_argument("--write-experiment-label")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.experiment_label:
        if args.read_experiment_label or args.write_experiment_label:
            raise SystemExit(
                "Use --experiment-label alone, or provide both paired labels."
            )
        session = load_session(args.experiment_label)
        for name, path in session["paths"].items():
            print(f"[OK] {name}: {path}")
        return

    if not args.read_experiment_label or not args.write_experiment_label:
        raise SystemExit(
            "Use --experiment-label, or provide both "
            "--read-experiment-label and --write-experiment-label."
        )
    paths = analyze_pair(
        args.read_experiment_label,
        args.write_experiment_label,
    )
    for name, path in paths.items():
        print(f"[OK] {name}: {path}")


if __name__ == "__main__":
    main()
