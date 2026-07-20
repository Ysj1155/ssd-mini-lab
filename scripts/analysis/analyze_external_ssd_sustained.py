r"""
scripts/analysis/analyze_external_ssd_sustained.py

Purpose:
    Analyze external SSD sustained fio result sets without generating plots.

Inputs:
    results/external_ssd/sustained_*/*_run*.json
    matching *_bw.1.log, *_iops.1.log, *_clat.1.log files

Outputs:
    results/external_ssd_sustained_summary.csv
    results/external_ssd_sustained_timeseries.csv
    results/external_ssd_sustained_window_summary.csv
    results/external_ssd_sustained_repeatability.csv

Usage:
    cd D:\ssd_lab
    python .\scripts\analysis\analyze_external_ssd_sustained.py
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

from parse_fio_results import get_percentile, ns_to_us


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_DIR = REPO_ROOT / "results" / "external_ssd"
DEFAULT_OUTPUT_PREFIX = REPO_ROOT / "results" / "external_ssd_sustained"


def read_fio_json(path: Path) -> dict[str, Any]:
    """Read fio JSON that may include warning text before the JSON object."""
    text = path.read_text(encoding="utf-8-sig")
    start = text.find("{")
    if start == -1:
        raise ValueError(f"No JSON object found in {path}")
    return json.loads(text[start:])


def extract_run(path: Path) -> int | None:
    match = re.search(r"run(\d+)", path.stem, re.IGNORECASE)
    return int(match.group(1)) if match else None


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


def sustained_json_files(input_dir: Path) -> list[Path]:
    files = [
        path
        for path in input_dir.rglob("*.json")
        if path.parent.name.startswith("sustained_") and re.search(r"run\d+", path.stem)
    ]
    return sorted(files)


def load_json_summary(input_dir: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    for path in sustained_json_files(input_dir):
        data = read_fio_json(path)
        jobs = data.get("jobs", [])
        if not jobs:
            continue

        job = jobs[0]
        opts = job.get("job options", {})
        rw = opts.get("rw")
        operation, io_section = select_io_section(job, rw)
        clat_ns = io_section.get("clat_ns", {})
        percentiles = clat_ns.get("percentile", {})

        rows.append(
            {
                "file": path.name,
                "result_set": path.parent.name,
                "workload": job.get("jobname"),
                "run": extract_run(path),
                "operation": operation,
                "rw": rw,
                "bs": opts.get("bs"),
                "iodepth": opts.get("iodepth"),
                "size": opts.get("size"),
                "direct": opts.get("direct"),
                "runtime_sec": float(io_section.get("runtime", 0)) / 1000.0,
                "bandwidth_mib_s": float(io_section.get("bw_bytes", 0)) / (1024 * 1024),
                "iops": io_section.get("iops"),
                "clat_mean_us": ns_to_us(clat_ns.get("mean")),
                "clat_p99_us": ns_to_us(get_percentile(percentiles, "99.000000")),
                "clat_p999_us": ns_to_us(get_percentile(percentiles, "99.900000")),
                "clat_max_us": ns_to_us(clat_ns.get("max")),
                "fio_version": data.get("fio version"),
                "timestamp": data.get("timestamp"),
                "timestamp_ms": data.get("timestamp_ms"),
                "relative_path": str(path.relative_to(REPO_ROOT)),
            }
        )

    if not rows:
        raise FileNotFoundError(f"No external SSD sustained JSON files found in {input_dir}")

    return pd.DataFrame(rows).sort_values(["result_set", "run"]).reset_index(drop=True)


def read_fio_log(path: Path, value_name: str, scale: float) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as f:
        for line in f:
            parts = [part.strip() for part in line.strip().split(",")]
            if len(parts) < 2:
                continue
            try:
                rows.append(
                    {
                        "msec": float(parts[0]),
                        "sec": float(parts[0]) / 1000.0,
                        value_name: float(parts[1]) / scale,
                    }
                )
            except ValueError:
                continue
    return pd.DataFrame(rows)


def load_timeseries(input_dir: Path) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []

    for json_path in sustained_json_files(input_dir):
        stem = json_path.stem
        bw_path = json_path.parent / f"{stem}_bw.1.log"
        iops_path = json_path.parent / f"{stem}_iops.1.log"
        clat_path = json_path.parent / f"{stem}_clat.1.log"

        if not bw_path.exists() or not iops_path.exists() or not clat_path.exists():
            print(f"[WARN] Missing one or more time-series logs for {json_path.name}")
            continue

        data = read_fio_json(json_path)
        job = data["jobs"][0]

        bw = read_fio_log(bw_path, "bandwidth_mib_s", scale=1024.0)
        iops = read_fio_log(iops_path, "iops", scale=1.0)
        clat = read_fio_log(clat_path, "clat_avg_us", scale=1000.0)

        merged = bw.merge(iops, on=["msec", "sec"], how="outer").merge(
            clat, on=["msec", "sec"], how="outer"
        )
        merged["result_set"] = json_path.parent.name
        merged["workload"] = job.get("jobname")
        merged["run"] = extract_run(json_path)
        merged["source_file"] = str(json_path.relative_to(REPO_ROOT))
        frames.append(merged)

    if not frames:
        return pd.DataFrame()

    return pd.concat(frames, ignore_index=True).sort_values(
        ["result_set", "run", "sec"]
    )


def window_label(index: int, count: int) -> str:
    third = count / 3.0
    if index < third:
        return "first_third"
    if index >= 2 * third:
        return "last_third"
    return "middle"


def make_window_summary(timeseries: pd.DataFrame) -> pd.DataFrame:
    if timeseries.empty:
        return pd.DataFrame()

    rows: list[dict[str, Any]] = []
    for (result_set, workload, run), group in timeseries.groupby(
        ["result_set", "workload", "run"], dropna=False
    ):
        group = group.sort_values("sec").reset_index(drop=True)
        labeled = group.copy()
        labeled["window"] = [window_label(i, len(group)) for i in range(len(group))]
        first = labeled[labeled["window"] == "first_third"]
        last = labeled[labeled["window"] == "last_third"]
        first_iops = first["iops"].mean()
        last_iops = last["iops"].mean()
        first_clat = first["clat_avg_us"].mean()
        last_clat = last["clat_avg_us"].mean()

        for window, window_group in labeled.groupby("window"):
            rows.append(
                {
                    "result_set": result_set,
                    "workload": workload,
                    "run": run,
                    "window": window,
                    "sample_count": len(window_group),
                    "bandwidth_mib_s_mean": window_group["bandwidth_mib_s"].mean(),
                    "iops_mean": window_group["iops"].mean(),
                    "clat_avg_us_mean": window_group["clat_avg_us"].mean(),
                    "clat_avg_us_max": window_group["clat_avg_us"].max(),
                    "first_iops_mean": first_iops,
                    "last_iops_mean": last_iops,
                    "iops_last_over_first": last_iops / first_iops if first_iops else None,
                    "first_clat_avg_us_mean": first_clat,
                    "last_clat_avg_us_mean": last_clat,
                    "clat_last_over_first": last_clat / first_clat if first_clat else None,
                }
            )

    return pd.DataFrame(rows).sort_values(["result_set", "run", "window"])


def coefficient_of_variation(series: pd.Series) -> float | None:
    mean = series.mean()
    if pd.isna(mean) or mean == 0:
        return None
    return series.std(ddof=1) / mean if len(series.dropna()) > 1 else 0.0


def make_repeatability(summary: pd.DataFrame, window_summary: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    for keys, group in summary.groupby(
        ["result_set", "workload", "operation", "rw", "bs", "iodepth", "size", "direct"],
        dropna=False,
    ):
        result_set, workload, operation, rw, bs, iodepth, size, direct = keys
        windows = window_summary[window_summary["result_set"] == result_set]
        per_run_windows = windows.drop_duplicates(["result_set", "run"])

        rows.append(
            {
                "result_set": result_set,
                "workload": workload,
                "operation": operation,
                "rw": rw,
                "bs": bs,
                "iodepth": iodepth,
                "size": size,
                "direct": direct,
                "run_count": len(group),
                "bandwidth_mib_s_mean": group["bandwidth_mib_s"].mean(),
                "bandwidth_mib_s_std": group["bandwidth_mib_s"].std(ddof=1),
                "iops_mean": group["iops"].mean(),
                "iops_std": group["iops"].std(ddof=1),
                "clat_p99_us_mean": group["clat_p99_us"].mean(),
                "clat_p99_us_std": group["clat_p99_us"].std(ddof=1),
                "clat_p999_us_mean": group["clat_p999_us"].mean(),
                "clat_p999_us_std": group["clat_p999_us"].std(ddof=1),
                "clat_max_us_mean": group["clat_max_us"].mean(),
                "clat_max_us_std": group["clat_max_us"].std(ddof=1),
                "bandwidth_mib_s_cv": coefficient_of_variation(group["bandwidth_mib_s"]),
                "iops_cv": coefficient_of_variation(group["iops"]),
                "clat_p99_us_cv": coefficient_of_variation(group["clat_p99_us"]),
                "clat_p999_us_cv": coefficient_of_variation(group["clat_p999_us"]),
                "clat_max_us_cv": coefficient_of_variation(group["clat_max_us"]),
                "iops_last_over_first_mean": per_run_windows[
                    "iops_last_over_first"
                ].mean()
                if not per_run_windows.empty
                else None,
                "clat_last_over_first_mean": per_run_windows[
                    "clat_last_over_first"
                ].mean()
                if not per_run_windows.empty
                else None,
            }
        )

    return pd.DataFrame(rows).sort_values(["result_set", "workload"])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze external SSD sustained fio JSON and time-series logs."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help=f"Input directory. Default: {DEFAULT_INPUT_DIR}",
    )
    parser.add_argument(
        "--output-prefix",
        type=Path,
        default=DEFAULT_OUTPUT_PREFIX,
        help=f"Output CSV prefix. Default: {DEFAULT_OUTPUT_PREFIX}",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = load_json_summary(args.input_dir)
    timeseries = load_timeseries(args.input_dir)
    window_summary = make_window_summary(timeseries)
    repeatability = make_repeatability(summary, window_summary)

    args.output_prefix.parent.mkdir(parents=True, exist_ok=True)
    summary_path = args.output_prefix.with_name(args.output_prefix.name + "_summary.csv")
    timeseries_path = args.output_prefix.with_name(args.output_prefix.name + "_timeseries.csv")
    window_path = args.output_prefix.with_name(args.output_prefix.name + "_window_summary.csv")
    repeatability_path = args.output_prefix.with_name(
        args.output_prefix.name + "_repeatability.csv"
    )

    summary.to_csv(summary_path, index=False, encoding="utf-8-sig")
    timeseries.to_csv(timeseries_path, index=False, encoding="utf-8-sig")
    window_summary.to_csv(window_path, index=False, encoding="utf-8-sig")
    repeatability.to_csv(repeatability_path, index=False, encoding="utf-8-sig")

    print(f"[OK] Saved summary: {summary_path}")
    print(f"[OK] Saved timeseries: {timeseries_path}")
    print(f"[OK] Saved window summary: {window_path}")
    print(f"[OK] Saved repeatability: {repeatability_path}")
    print()
    print(repeatability.to_string(index=False))


if __name__ == "__main__":
    main()