"""
analyze_sustained_smoke.py

Purpose:
    Analyze conservative sustained fio smoke-test output.

Inputs:
    results/sustained_smoke/**/*_sustained_run*.json
    results/sustained_smoke/**/*_sustained_run*_bw.1.log
    results/sustained_smoke/**/*_sustained_run*_iops.1.log
    results/sustained_smoke/**/*_sustained_run*_clat.1.log

Outputs:
    results/sustained_smoke_summary.csv
    results/sustained_smoke_timeseries.csv
    results/sustained_smoke_window_summary.csv
    results/sustained_smoke_latency_spikes.csv
    results/sustained_smoke_repeatability.csv
    results/sustained_smoke_result_set_comparison.csv
    results/sustained_smoke_workload_comparison.csv
    results/sustained_smoke_plots/*.png

Usage:
    cd D:\\ssd_lab
    python .\\analyze_sustained_smoke.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from parse_fio_results import get_percentile, ns_to_us


BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "results" / "sustained_smoke"
SUMMARY_CSV = BASE_DIR / "results" / "sustained_smoke_summary.csv"
TIMESERIES_CSV = BASE_DIR / "results" / "sustained_smoke_timeseries.csv"
WINDOW_CSV = BASE_DIR / "results" / "sustained_smoke_window_summary.csv"
SPIKES_CSV = BASE_DIR / "results" / "sustained_smoke_latency_spikes.csv"
REPEATABILITY_CSV = BASE_DIR / "results" / "sustained_smoke_repeatability.csv"
RESULT_SET_COMPARISON_CSV = (
    BASE_DIR / "results" / "sustained_smoke_result_set_comparison.csv"
)
WORKLOAD_COMPARISON_CSV = BASE_DIR / "results" / "sustained_smoke_workload_comparison.csv"
PLOT_DIR = BASE_DIR / "results" / "sustained_smoke_plots"


def read_fio_json(path: Path) -> dict[str, Any]:
    """Read fio JSON that may include warning text before the JSON object."""
    text = path.read_text(encoding="utf-8-sig")
    json_start = text.find("{")
    if json_start == -1:
        raise ValueError(f"No JSON object found in {path}")
    return json.loads(text[json_start:])


def extract_run(path: Path) -> int | None:
    """Extract run number from sustained filename."""
    match = re.search(r"run(\d+)", path.stem, re.IGNORECASE)
    if not match:
        return None
    return int(match.group(1))


def result_set_name(path: Path) -> str:
    """Return the sustained result-set label for root or nested outputs."""
    if path.parent == INPUT_DIR:
        return "legacy_root"
    return path.parent.name


def select_io_section(job: dict[str, Any], rw: str | None) -> tuple[str, dict[str, Any]]:
    """Select the fio read/write section that contains the measured I/O."""
    candidates = ["read", "write"]
    if rw and "read" in rw.lower() and "write" not in rw.lower():
        candidates = ["read", "write"]
    elif rw and "write" in rw.lower() and "read" not in rw.lower():
        candidates = ["write", "read"]

    for operation in candidates:
        section = job.get(operation, {})
        if section.get("iops") or section.get("bw_bytes") or section.get("io_bytes"):
            return operation, section

    return candidates[0], job.get(candidates[0], {})


def load_json_summary() -> pd.DataFrame:
    """Load per-run aggregate metrics from fio JSON."""
    rows: list[dict[str, Any]] = []

    for path in sorted(INPUT_DIR.rglob("*_sustained_run*.json")):
        data = read_fio_json(path)
        jobs = data.get("jobs", [])
        if not jobs:
            continue

        job = jobs[0]
        job_options = job.get("job options", {})
        rw = job_options.get("rw")
        operation, io_section = select_io_section(job, rw)
        clat_ns = io_section.get("clat_ns", {})
        percentiles = clat_ns.get("percentile", {})

        p99_ns = get_percentile(percentiles, "99.000000")
        p999_ns = get_percentile(percentiles, "99.900000")

        rows.append(
            {
                "file": path.name,
                "result_set": result_set_name(path),
                "relative_path": str(path.relative_to(BASE_DIR)),
                "workload": job.get("jobname"),
                "run": extract_run(path),
                "operation": operation,
                "rw": rw,
                "bs": job_options.get("bs"),
                "iodepth": job_options.get("iodepth"),
                "size": job_options.get("size"),
                "direct": job_options.get("direct"),
                "runtime_sec": (float(io_section["runtime"]) / 1000.0)
                if io_section.get("runtime") is not None
                else None,
                "bandwidth_mib_s": float(io_section.get("bw_bytes", 0)) / (1024 * 1024),
                "iops": io_section.get("iops"),
                "clat_mean_us": ns_to_us(clat_ns.get("mean")),
                "clat_p99_us": ns_to_us(p99_ns),
                "clat_p999_us": ns_to_us(p999_ns),
                "clat_max_us": ns_to_us(clat_ns.get("max")),
                "fio_version": data.get("fio version"),
                "timestamp": data.get("timestamp"),
                "timestamp_ms": data.get("timestamp_ms"),
            }
        )

    if not rows:
        raise FileNotFoundError(f"No sustained JSON files found in {INPUT_DIR}")

    return (
        pd.DataFrame(rows)
        .sort_values(["result_set", "workload", "run"])
        .reset_index(drop=True)
    )


def read_fio_log(path: Path, value_name: str, scale: float = 1.0) -> pd.DataFrame:
    """
    Read a fio time-series log.

    fio logs are comma-separated and usually contain:
        msec, value, direction, block_size, offset
    """
    rows: list[dict[str, Any]] = []

    with path.open("r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            parts = [part.strip() for part in line.split(",")]
            if len(parts) < 2:
                continue

            try:
                msec = float(parts[0])
                value = float(parts[1]) / scale
            except ValueError:
                continue

            rows.append(
                {
                    "msec": msec,
                    "sec": msec / 1000.0,
                    value_name: value,
                }
            )

    return pd.DataFrame(rows)


def load_timeseries() -> pd.DataFrame:
    """Load and merge bw/iops/clat logs per sustained run."""
    rows: list[pd.DataFrame] = []

    for json_path in sorted(INPUT_DIR.rglob("*_sustained_run*.json")):
        stem = json_path.stem
        run = extract_run(json_path)
        workload = "unknown"

        try:
            data = read_fio_json(json_path)
            workload = data["jobs"][0].get("jobname", "unknown")
        except Exception:
            pass

        bw_path = json_path.parent / f"{stem}_bw.1.log"
        iops_path = json_path.parent / f"{stem}_iops.1.log"
        clat_path = json_path.parent / f"{stem}_clat.1.log"

        if not bw_path.exists() or not iops_path.exists() or not clat_path.exists():
            print(f"[WARN] Missing one or more logs for {json_path.name}")
            continue

        # fio bandwidth logs are KiB/s. Convert to MiB/s.
        bw = read_fio_log(bw_path, "bandwidth_mib_s", scale=1024.0)
        iops = read_fio_log(iops_path, "iops", scale=1.0)
        # fio latency logs are ns. Convert to us.
        clat = read_fio_log(clat_path, "clat_avg_us", scale=1000.0)

        merged = bw.merge(iops, on=["msec", "sec"], how="outer").merge(
            clat, on=["msec", "sec"], how="outer"
        )
        merged["workload"] = workload
        merged["run"] = run
        merged["result_set"] = result_set_name(json_path)
        merged["source_file"] = str(json_path.relative_to(BASE_DIR))
        rows.append(merged)

    if not rows:
        raise FileNotFoundError(f"No sustained time-series logs found in {INPUT_DIR}")

    return (
        pd.concat(rows, ignore_index=True)
        .sort_values(["result_set", "workload", "run", "sec"])
        .reset_index(drop=True)
    )


def assign_window(df: pd.DataFrame) -> pd.DataFrame:
    """Assign each sample to first/middle/last third by elapsed time."""
    result = df.copy()
    result["window"] = "middle"

    for (_, _, _), part in result.groupby(["result_set", "workload", "run"]):
        max_sec = part["sec"].max()
        first_cut = max_sec / 3.0
        last_cut = max_sec * 2.0 / 3.0

        idx = part.index
        result.loc[idx[part["sec"] <= first_cut], "window"] = "first_third"
        result.loc[idx[part["sec"] > last_cut], "window"] = "last_third"

    return result


def make_window_summary(ts: pd.DataFrame) -> pd.DataFrame:
    """Summarize time-series metrics by first/middle/last windows."""
    ts = assign_window(ts)
    summary = (
        ts.groupby(["result_set", "workload", "run", "window"], as_index=False)
        .agg(
            sample_count=("sec", "count"),
            sec_min=("sec", "min"),
            sec_max=("sec", "max"),
            bandwidth_mib_s_mean=("bandwidth_mib_s", "mean"),
            bandwidth_mib_s_min=("bandwidth_mib_s", "min"),
            bandwidth_mib_s_max=("bandwidth_mib_s", "max"),
            iops_mean=("iops", "mean"),
            iops_min=("iops", "min"),
            iops_max=("iops", "max"),
            clat_avg_us_mean=("clat_avg_us", "mean"),
            clat_avg_us_min=("clat_avg_us", "min"),
            clat_avg_us_max=("clat_avg_us", "max"),
        )
        .sort_values(["result_set", "workload", "run", "window"])
        .reset_index(drop=True)
    )

    rows = []
    for (result_set, workload, run), part in summary.groupby(["result_set", "workload", "run"]):
        first = part[part["window"] == "first_third"]
        last = part[part["window"] == "last_third"]
        if first.empty or last.empty:
            continue

        first_row = first.iloc[0]
        last_row = last.iloc[0]
        rows.append(
            {
                "workload": workload,
                "result_set": result_set,
                "run": run,
                "first_iops_mean": first_row["iops_mean"],
                "last_iops_mean": last_row["iops_mean"],
                "iops_last_over_first": last_row["iops_mean"] / first_row["iops_mean"],
                "first_bandwidth_mib_s_mean": first_row["bandwidth_mib_s_mean"],
                "last_bandwidth_mib_s_mean": last_row["bandwidth_mib_s_mean"],
                "bandwidth_last_over_first": last_row["bandwidth_mib_s_mean"]
                / first_row["bandwidth_mib_s_mean"],
                "first_clat_avg_us_mean": first_row["clat_avg_us_mean"],
                "last_clat_avg_us_mean": last_row["clat_avg_us_mean"],
                "clat_last_over_first": last_row["clat_avg_us_mean"]
                / first_row["clat_avg_us_mean"],
            }
        )

    ratio_summary = pd.DataFrame(rows)
    return summary.merge(ratio_summary, on=["result_set", "workload", "run"], how="left")


def make_latency_spikes(ts: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
    """List the highest average-latency intervals per sustained run."""
    rows: list[dict[str, Any]] = []

    for (result_set, workload, run), part in ts.dropna(subset=["clat_avg_us"]).groupby(
        ["result_set", "workload", "run"]
    ):
        clat = part["clat_avg_us"]
        median = clat.median()
        mad = (clat - median).abs().median()

        ranked = part.sort_values("clat_avg_us", ascending=False).head(top_n)
        for rank, row in enumerate(ranked.itertuples(index=False), start=1):
            robust_z = None
            if mad and pd.notna(mad):
                robust_z = 0.6745 * (float(row.clat_avg_us) - float(median)) / float(mad)

            rows.append(
                {
                    "workload": workload,
                    "result_set": result_set,
                    "run": run,
                    "rank": rank,
                    "sec": row.sec,
                    "clat_avg_us": row.clat_avg_us,
                    "iops": row.iops,
                    "bandwidth_mib_s": row.bandwidth_mib_s,
                    "run_clat_avg_us_median": median,
                    "run_clat_avg_us_mad": mad,
                    "robust_z": robust_z,
                    "is_candidate_spike": bool(
                        (robust_z is not None and robust_z >= 3.5)
                        or row.clat_avg_us >= 1000.0
                    ),
                }
            )

    return pd.DataFrame(rows)


def coefficient_of_variation(series: pd.Series) -> float | None:
    """Return sample CV for a numeric series."""
    values = pd.to_numeric(series, errors="coerce").dropna()
    if len(values) < 2:
        return None
    mean = values.mean()
    if mean == 0:
        return None
    return values.std(ddof=1) / mean


def make_repeatability_summary(
    summary: pd.DataFrame, window_summary: pd.DataFrame, latency_spikes: pd.DataFrame
) -> pd.DataFrame:
    """Summarize run-to-run repeatability by result set and workload."""
    ratio_cols = [
        "result_set",
        "workload",
        "run",
        "iops_last_over_first",
        "bandwidth_last_over_first",
        "clat_last_over_first",
    ]
    ratios = window_summary[ratio_cols].drop_duplicates()
    spike_counts = (
        latency_spikes[latency_spikes["is_candidate_spike"]]
        .groupby(["result_set", "workload", "run"], as_index=False)
        .agg(candidate_spike_count=("rank", "count"))
    )

    merged = summary.merge(ratios, on=["result_set", "workload", "run"], how="left").merge(
        spike_counts, on=["result_set", "workload", "run"], how="left"
    )
    merged["candidate_spike_count"] = merged["candidate_spike_count"].fillna(0)

    rows: list[dict[str, Any]] = []
    metric_cols = [
        "bandwidth_mib_s",
        "iops",
        "clat_mean_us",
        "clat_p99_us",
        "clat_p999_us",
        "clat_max_us",
        "iops_last_over_first",
        "bandwidth_last_over_first",
        "clat_last_over_first",
        "candidate_spike_count",
    ]

    for (result_set, workload), part in merged.groupby(["result_set", "workload"]):
        row: dict[str, Any] = {
            "result_set": result_set,
            "workload": workload,
            "operation": part["operation"].dropna().iloc[0]
            if "operation" in part and not part["operation"].dropna().empty
            else None,
            "rw": part["rw"].dropna().iloc[0]
            if "rw" in part and not part["rw"].dropna().empty
            else None,
            "bs": part["bs"].dropna().iloc[0]
            if "bs" in part and not part["bs"].dropna().empty
            else None,
            "iodepth": part["iodepth"].dropna().iloc[0]
            if "iodepth" in part and not part["iodepth"].dropna().empty
            else None,
            "size": part["size"].dropna().iloc[0]
            if "size" in part and not part["size"].dropna().empty
            else None,
            "direct": part["direct"].dropna().iloc[0]
            if "direct" in part and not part["direct"].dropna().empty
            else None,
            "runtime_sec_mean": pd.to_numeric(part["runtime_sec"], errors="coerce").mean(),
            "run_count": part["run"].nunique(),
        }

        for col in metric_cols:
            values = pd.to_numeric(part[col], errors="coerce")
            row[f"{col}_mean"] = values.mean()
            row[f"{col}_std"] = values.std(ddof=1) if values.count() >= 2 else None
            row[f"{col}_cv"] = coefficient_of_variation(values)

        rows.append(row)

    return pd.DataFrame(rows).sort_values(["result_set", "workload"]).reset_index(drop=True)


def ratio(numerator: Any, denominator: Any) -> float | None:
    """Return numerator / denominator when both values are valid."""
    if numerator is None or denominator is None or pd.isna(numerator) or pd.isna(denominator):
        return None
    if denominator == 0:
        return None
    return float(numerator) / float(denominator)


def make_result_set_comparison(repeatability: pd.DataFrame) -> pd.DataFrame:
    """Create pairwise comparisons between sustained result sets."""
    metric_cols = [
        "bandwidth_mib_s_mean",
        "iops_mean",
        "clat_mean_us_mean",
        "clat_p99_us_mean",
        "clat_p999_us_mean",
        "clat_max_us_mean",
        "iops_last_over_first_mean",
        "clat_last_over_first_mean",
        "candidate_spike_count_mean",
    ]
    cv_cols = [
        "bandwidth_mib_s_cv",
        "iops_cv",
        "clat_p99_us_cv",
        "clat_p999_us_cv",
        "clat_max_us_cv",
    ]
    rows: list[dict[str, Any]] = []

    for workload, part in repeatability.groupby("workload"):
        ordered = part.sort_values("result_set").reset_index(drop=True)
        for left_idx in range(len(ordered)):
            for right_idx in range(left_idx + 1, len(ordered)):
                base = ordered.iloc[left_idx]
                compare = ordered.iloc[right_idx]
                row: dict[str, Any] = {
                    "workload": workload,
                    "base_result_set": base["result_set"],
                    "compare_result_set": compare["result_set"],
                    "base_run_count": base["run_count"],
                    "compare_run_count": compare["run_count"],
                }

                for col in metric_cols:
                    base_value = base.get(col)
                    compare_value = compare.get(col)
                    row[f"base_{col}"] = base_value
                    row[f"compare_{col}"] = compare_value
                    row[f"{col}_ratio"] = ratio(compare_value, base_value)

                for col in cv_cols:
                    row[f"base_{col}"] = base.get(col)
                    row[f"compare_{col}"] = compare.get(col)

                rows.append(row)

    return pd.DataFrame(rows)


def make_workload_comparison(repeatability: pd.DataFrame) -> pd.DataFrame:
    """Compare different workloads under the same sustained test condition."""
    metric_cols = [
        "bandwidth_mib_s_mean",
        "iops_mean",
        "clat_mean_us_mean",
        "clat_p99_us_mean",
        "clat_p999_us_mean",
        "clat_max_us_mean",
        "iops_last_over_first_mean",
        "clat_last_over_first_mean",
        "candidate_spike_count_mean",
    ]
    group_cols = ["bs", "iodepth", "size", "direct", "runtime_sec_mean", "run_count"]
    rows: list[dict[str, Any]] = []

    comparable = repeatability.dropna(subset=["operation", "runtime_sec_mean"])
    for key, part in comparable.groupby(group_cols, dropna=False):
        if part["workload"].nunique() < 2:
            continue

        ordered = part.sort_values("workload").reset_index(drop=True)
        for left_idx in range(len(ordered)):
            for right_idx in range(left_idx + 1, len(ordered)):
                base = ordered.iloc[left_idx]
                compare = ordered.iloc[right_idx]
                if base["workload"] == compare["workload"]:
                    continue

                row: dict[str, Any] = {
                    "base_workload": base["workload"],
                    "compare_workload": compare["workload"],
                    "base_result_set": base["result_set"],
                    "compare_result_set": compare["result_set"],
                    "base_operation": base["operation"],
                    "compare_operation": compare["operation"],
                    "bs": key[0],
                    "iodepth": key[1],
                    "size": key[2],
                    "direct": key[3],
                    "runtime_sec_mean": key[4],
                    "run_count": key[5],
                }

                for col in metric_cols:
                    base_value = base.get(col)
                    compare_value = compare.get(col)
                    row[f"base_{col}"] = base_value
                    row[f"compare_{col}"] = compare_value
                    row[f"{col}_ratio"] = ratio(compare_value, base_value)

                rows.append(row)

    return pd.DataFrame(rows)


def plot_timeseries(ts: pd.DataFrame, y_col: str, ylabel: str, title: str, output: Path) -> None:
    """Plot one time-series metric."""
    fig, ax = plt.subplots(figsize=(10, 5))

    for (result_set, workload, run), part in ts.groupby(["result_set", "workload", "run"]):
        label = f"{result_set} {workload} run{int(run)}"
        ax.plot(part["sec"], part[y_col], label=label)

    ax.set_title(title)
    ax.set_xlabel("Elapsed time (s)")
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=150)
    plt.close(fig)
    print(f"[OK] Saved plot: {output}")


def print_summary(
    summary: pd.DataFrame,
    window_summary: pd.DataFrame,
    latency_spikes: pd.DataFrame,
    repeatability: pd.DataFrame,
    result_set_comparison: pd.DataFrame,
    workload_comparison: pd.DataFrame,
) -> None:
    """Print compact console summary."""
    print()
    print("=== Sustained Aggregate Summary ===")
    print(
        summary.to_string(
            index=False,
            formatters={
                "bandwidth_mib_s": "{:.2f}".format,
                "iops": "{:.2f}".format,
                "clat_mean_us": "{:.2f}".format,
                "clat_p99_us": "{:.2f}".format,
                "clat_p999_us": "{:.2f}".format,
                "clat_max_us": "{:.2f}".format,
            },
        )
    )

    ratio_cols = [
        "workload",
        "result_set",
        "run",
        "first_iops_mean",
        "last_iops_mean",
        "iops_last_over_first",
        "first_clat_avg_us_mean",
        "last_clat_avg_us_mean",
        "clat_last_over_first",
    ]
    ratios = window_summary.dropna(subset=["iops_last_over_first"])[ratio_cols].drop_duplicates()
    print()
    print("=== First vs Last Third ===")
    print(
        ratios.to_string(
            index=False,
            formatters={
                "first_iops_mean": "{:.2f}".format,
                "last_iops_mean": "{:.2f}".format,
                "iops_last_over_first": "{:.3f}".format,
                "first_clat_avg_us_mean": "{:.2f}".format,
                "last_clat_avg_us_mean": "{:.2f}".format,
                "clat_last_over_first": "{:.3f}".format,
            },
        )
    )

    print()
    print("=== Highest Average-Latency Intervals ===")
    print(
        latency_spikes.to_string(
            index=False,
            columns=[
                "workload",
                "result_set",
                "run",
                "rank",
                "sec",
                "clat_avg_us",
                "robust_z",
                "is_candidate_spike",
            ],
            formatters={
                "sec": "{:.3f}".format,
                "clat_avg_us": "{:.2f}".format,
                "robust_z": lambda value: "" if pd.isna(value) else f"{value:.2f}",
            },
        )
    )

    print()
    print("=== Repeatability Summary ===")
    display_cols = [
        "result_set",
        "workload",
        "run_count",
        "bandwidth_mib_s_mean",
        "bandwidth_mib_s_cv",
        "iops_mean",
        "iops_cv",
        "clat_p99_us_mean",
        "clat_p99_us_cv",
        "clat_p999_us_mean",
        "clat_p999_us_cv",
        "clat_max_us_mean",
        "clat_max_us_cv",
        "candidate_spike_count_mean",
    ]
    print(
        repeatability.to_string(
            index=False,
            columns=display_cols,
            formatters={
                "bandwidth_mib_s_mean": "{:.2f}".format,
                "bandwidth_mib_s_cv": lambda value: "" if pd.isna(value) else f"{value:.3f}",
                "iops_mean": "{:.2f}".format,
                "iops_cv": lambda value: "" if pd.isna(value) else f"{value:.3f}",
                "clat_p99_us_mean": "{:.2f}".format,
                "clat_p99_us_cv": lambda value: "" if pd.isna(value) else f"{value:.3f}",
                "clat_p999_us_mean": "{:.2f}".format,
                "clat_p999_us_cv": lambda value: "" if pd.isna(value) else f"{value:.3f}",
                "clat_max_us_mean": "{:.2f}".format,
                "clat_max_us_cv": lambda value: "" if pd.isna(value) else f"{value:.3f}",
                "candidate_spike_count_mean": "{:.2f}".format,
            },
        )
    )

    if not result_set_comparison.empty:
        print()
        print("=== Result Set Comparison ===")
        display_cols = [
            "workload",
            "base_result_set",
            "compare_result_set",
            "bandwidth_mib_s_mean_ratio",
            "iops_mean_ratio",
            "clat_p99_us_mean_ratio",
            "clat_p999_us_mean_ratio",
            "clat_max_us_mean_ratio",
        ]
        print(
            result_set_comparison.to_string(
                index=False,
                columns=display_cols,
                formatters={
                    "bandwidth_mib_s_mean_ratio": lambda value: ""
                    if pd.isna(value)
                    else f"{value:.3f}",
                    "iops_mean_ratio": lambda value: "" if pd.isna(value) else f"{value:.3f}",
                    "clat_p99_us_mean_ratio": lambda value: ""
                    if pd.isna(value)
                    else f"{value:.3f}",
                    "clat_p999_us_mean_ratio": lambda value: ""
                    if pd.isna(value)
                    else f"{value:.3f}",
                    "clat_max_us_mean_ratio": lambda value: ""
                    if pd.isna(value)
                    else f"{value:.3f}",
                },
            )
        )

    if not workload_comparison.empty:
        print()
        print("=== Workload Comparison ===")
        display_cols = [
            "base_workload",
            "compare_workload",
            "runtime_sec_mean",
            "iops_mean_ratio",
            "clat_p99_us_mean_ratio",
            "clat_p999_us_mean_ratio",
            "clat_max_us_mean_ratio",
        ]
        print(
            workload_comparison.to_string(
                index=False,
                columns=display_cols,
                formatters={
                    "runtime_sec_mean": "{:.0f}".format,
                    "iops_mean_ratio": lambda value: "" if pd.isna(value) else f"{value:.3f}",
                    "clat_p99_us_mean_ratio": lambda value: ""
                    if pd.isna(value)
                    else f"{value:.3f}",
                    "clat_p999_us_mean_ratio": lambda value: ""
                    if pd.isna(value)
                    else f"{value:.3f}",
                    "clat_max_us_mean_ratio": lambda value: ""
                    if pd.isna(value)
                    else f"{value:.3f}",
                },
            )
        )


def main() -> None:
    summary = load_json_summary()
    timeseries = load_timeseries()
    window_summary = make_window_summary(timeseries)
    latency_spikes = make_latency_spikes(timeseries)
    repeatability = make_repeatability_summary(summary, window_summary, latency_spikes)
    result_set_comparison = make_result_set_comparison(repeatability)
    workload_comparison = make_workload_comparison(repeatability)

    SUMMARY_CSV.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(SUMMARY_CSV, index=False, encoding="utf-8-sig")
    timeseries.to_csv(TIMESERIES_CSV, index=False, encoding="utf-8-sig")
    window_summary.to_csv(WINDOW_CSV, index=False, encoding="utf-8-sig")
    latency_spikes.to_csv(SPIKES_CSV, index=False, encoding="utf-8-sig")
    repeatability.to_csv(REPEATABILITY_CSV, index=False, encoding="utf-8-sig")
    result_set_comparison.to_csv(
        RESULT_SET_COMPARISON_CSV, index=False, encoding="utf-8-sig"
    )
    workload_comparison.to_csv(WORKLOAD_COMPARISON_CSV, index=False, encoding="utf-8-sig")

    print(f"[OK] Saved summary: {SUMMARY_CSV}")
    print(f"[OK] Saved timeseries: {TIMESERIES_CSV}")
    print(f"[OK] Saved window summary: {WINDOW_CSV}")
    print(f"[OK] Saved latency spike candidates: {SPIKES_CSV}")
    print(f"[OK] Saved repeatability summary: {REPEATABILITY_CSV}")
    print(f"[OK] Saved result-set comparison: {RESULT_SET_COMPARISON_CSV}")
    print(f"[OK] Saved workload comparison: {WORKLOAD_COMPARISON_CSV}")

    plot_timeseries(
        timeseries,
        y_col="iops",
        ylabel="IOPS",
        title="Sustained Smoke - IOPS Over Time",
        output=BASE_DIR / "results" / "sustained_smoke_plots" / "sustained_iops_over_time.png",
    )
    plot_timeseries(
        timeseries,
        y_col="bandwidth_mib_s",
        ylabel="Bandwidth (MiB/s)",
        title="Sustained Smoke - Bandwidth Over Time",
        output=BASE_DIR
        / "results"
        / "sustained_smoke_plots"
        / "sustained_bandwidth_over_time.png",
    )
    plot_timeseries(
        timeseries,
        y_col="clat_avg_us",
        ylabel="Average completion latency per interval (us)",
        title="Sustained Smoke - Average clat Over Time",
        output=BASE_DIR
        / "results"
        / "sustained_smoke_plots"
        / "sustained_clat_avg_over_time.png",
    )

    print_summary(
        summary,
        window_summary,
        latency_spikes,
        repeatability,
        result_set_comparison,
        workload_comparison,
    )


if __name__ == "__main__":
    main()
