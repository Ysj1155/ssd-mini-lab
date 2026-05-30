"""
parse_fio_results.py

Purpose:
    Parse fio JSON result files and summarize key validation-oriented metrics into CSV.

Supported filename patterns:
    Baseline:
        seq_read_run1.json
        seq_write_run2.json
        rand_read_run3.json
        rand_write_run1.json

    QD sweep:
        rand_read_qd1_run1.json
        rand_read_qd4_run2.json
        rand_write_qd16_run3.json
        rand_write_qd32_run1.json

    Direct vs buffered:
        rand_read_direct1_run1.json
        rand_read_direct0_run2.json
        rand_write_direct1_run3.json
        rand_write_direct0_run1.json

    WSL path comparison:
        rand_read_path_wsl_ext4_run1.json
        rand_write_path_mnt_d_run2.json

Default input:
    D:\\ssd_lab\\results\\*.json

Default output:
    D:\\ssd_lab\\results\\fio_summary.csv

Usage:
    Baseline:
        cd D:\\ssd_lab
        python .\\parse_fio_results.py

    QD sweep:
        python .\\parse_fio_results.py `
          --input-dir D:\\ssd_lab\\results\\qd_sweep `
          --output D:\\ssd_lab\\results\\qd_sweep_summary.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


# -----------------------------
# Small conversion/helper funcs
# -----------------------------

def safe_get(data: Dict[str, Any], keys: List[str], default: Any = None) -> Any:
    """
    Safely access nested dictionary values.

    Example:
        safe_get(job, ["read", "iops"], 0)
    """
    current: Any = data

    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]

    return current


def ns_to_us(value_ns: Optional[float]) -> Optional[float]:
    """
    Convert nanoseconds to microseconds.

    fio clat_ns values are usually stored in ns.
    """
    if value_ns is None:
        return None

    try:
        return float(value_ns) / 1000.0
    except (TypeError, ValueError):
        return None


def bytes_per_sec_to_mib_per_sec(value_bps: Optional[float]) -> Optional[float]:
    """
    Convert bytes/s to MiB/s.

    fio JSON generally stores bw_bytes in bytes/s.
    """
    if value_bps is None:
        return None

    try:
        return float(value_bps) / (1024 * 1024)
    except (TypeError, ValueError):
        return None


def get_percentile(percentile_dict: Dict[str, Any], target: str) -> Optional[float]:
    """
    fio percentile keys may be strings like:
        "95.000000"
        "99.000000"

    This function finds the matching percentile robustly.
    """
    if not isinstance(percentile_dict, dict):
        return None

    target_float = float(target)

    for key, value in percentile_dict.items():
        try:
            if abs(float(key) - target_float) < 0.0001:
                return value
        except (TypeError, ValueError):
            continue

    return None


# -----------------------------
# Filename metadata extraction
# -----------------------------

def extract_run_number(filename: str) -> Optional[int]:
    """
    Extract run number from filenames like:
        seq_read_run1.json
        rand_write_qd32_run3.json

    Returns None if no run number is found.
    """
    match = re.search(r"(?:^|[_-])run[_-]?(\d+)(?:$|[_-])", Path(filename).stem, re.IGNORECASE)

    if match:
        return int(match.group(1))

    # Fallback for simple patterns like "...run1"
    match = re.search(r"run[_-]?(\d+)", filename, re.IGNORECASE)
    if match:
        return int(match.group(1))

    return None


def extract_qd_from_filename(filename: str) -> Optional[int]:
    """
    Extract queue depth from filenames like:
        rand_read_qd1_run1.json
        rand_write_qd32_run3.json

    Returns None for baseline files without qd metadata.
    """
    stem = Path(filename).stem

    match = re.search(r"(?:^|[_-])qd[_-]?(\d+)(?:$|[_-])", stem, re.IGNORECASE)
    if match:
        return int(match.group(1))

    return None


def extract_direct_from_filename(filename: str) -> Optional[int]:
    """
    Extract direct I/O flag from filenames like:
        rand_read_direct1_run1.json
        rand_write_direct0_run3.json

    Returns None for files without direct metadata.
    """
    stem = Path(filename).stem

    match = re.search(r"(?:^|[_-])direct[_-]?([01])(?:$|[_-])", stem, re.IGNORECASE)
    if match:
        return int(match.group(1))

    return None


def extract_path_mode_from_filename(filename: str) -> Optional[str]:
    """
    Extract path mode from filenames like:
        rand_read_path_wsl_ext4_run1.json
        rand_write_path_mnt_d_run3.json

    Returns None for files without path metadata.
    """
    stem = Path(filename).stem

    match = re.search(r"(?:^|[_-])path[_-](.*?)(?:[_-]run[_-]?\d+|$)", stem, re.IGNORECASE)
    if match:
        return match.group(1).replace("-", "_").lower()

    return None


def infer_workload_from_filename(filename: str) -> str:
    """
    Infer workload name from filename.

    Examples:
        seq_read_run1.json -> seq_read
        rand_write_run2.json -> rand_write
        rand_read_qd16_run3.json -> rand_read
        rand_write_qd32_run1.json -> rand_write
        rand_read_direct1_run1.json -> rand_read
        rand_write_direct0_run2.json -> rand_write
        rand_read_path_wsl_ext4_run1.json -> rand_read
        rand_write_path_mnt_d_run2.json -> rand_write
    """
    stem = Path(filename).stem

    # Remove run metadata.
    name = re.sub(r"[_-]?run[_-]?\d+", "", stem, flags=re.IGNORECASE)

    # Remove qd metadata.
    name = re.sub(r"[_-]?qd[_-]?\d+", "", name, flags=re.IGNORECASE)

    # Remove direct/buffered metadata.
    name = re.sub(r"[_-]?direct[_-]?[01]", "", name, flags=re.IGNORECASE)

    # Remove path metadata.
    name = re.sub(
        r"[_-]?path[_-][a-z0-9]+(?:[_-][a-z0-9]+)*",
        "",
        name,
        flags=re.IGNORECASE,
    )

    # Normalize leftover separators.
    name = re.sub(r"[-]+", "_", name)
    name = re.sub(r"__+", "_", name)
    name = name.strip("_")

    return name


# -----------------------------
# fio JSON parsing
# -----------------------------

def choose_active_direction(job: Dict[str, Any]) -> str:
    """
    Decide whether this job is read or write focused.

    fio JSON has both 'read' and 'write' sections.
    The inactive side usually has zero IOPS / bandwidth.
    """
    read_iops = safe_get(job, ["read", "iops"], 0) or 0
    write_iops = safe_get(job, ["write", "iops"], 0) or 0

    try:
        read_iops = float(read_iops)
        write_iops = float(write_iops)
    except (TypeError, ValueError):
        return "unknown"

    if read_iops > 0 and write_iops == 0:
        return "read"

    if write_iops > 0 and read_iops == 0:
        return "write"

    if read_iops > 0 and write_iops > 0:
        return "mixed"

    return "unknown"


def parse_one_json(json_path: Path) -> List[Dict[str, Any]]:
    """
    Parse one fio JSON file.

    Returns a list because fio JSON can contain multiple jobs.
    In this mini-lab, normally each file has one job.
    """
    text = json_path.read_text(encoding="utf-8-sig")
    json_start = text.find("{")

    if json_start == -1:
        raise ValueError("No JSON object found in fio output")

    data = json.loads(text[json_start:])

    jobs = data.get("jobs", [])

    if not jobs:
        raise ValueError(f"No jobs found in {json_path}")

    rows: List[Dict[str, Any]] = []

    for job in jobs:
        direction = choose_active_direction(job)

        if direction == "read":
            active = job.get("read", {})
            rows.append(build_row(json_path, data, job, active, direction))

        elif direction == "write":
            active = job.get("write", {})
            rows.append(build_row(json_path, data, job, active, direction))

        elif direction == "mixed":
            # For mixed workload, record read and write as separate rows.
            for mixed_direction in ["read", "write"]:
                active_mixed = job.get(mixed_direction, {})
                rows.append(build_row(json_path, data, job, active_mixed, mixed_direction))

        else:
            rows.append(build_row(json_path, data, job, {}, direction))

    return rows


def build_row(
    json_path: Path,
    fio_root: Dict[str, Any],
    job: Dict[str, Any],
    active: Dict[str, Any],
    direction: str,
) -> Dict[str, Any]:
    """
    Build one CSV row from one fio job result.
    """
    job_options = job.get("job options", {})

    clat_ns = active.get("clat_ns", {})
    clat_mean_ns = clat_ns.get("mean")
    clat_percentiles = clat_ns.get("percentile", {})

    p95_ns = get_percentile(clat_percentiles, "95.000000")
    p99_ns = get_percentile(clat_percentiles, "99.000000")
    p999_ns = get_percentile(clat_percentiles, "99.900000")

    bw_bytes = active.get("bw_bytes")
    iops = active.get("iops")

    runtime_ms = active.get("runtime")
    runtime_sec = None

    if runtime_ms is not None:
        try:
            runtime_sec = float(runtime_ms) / 1000.0
        except (TypeError, ValueError):
            runtime_sec = None

    filename = json_path.name
    filename_qd = extract_qd_from_filename(filename)
    filename_direct = extract_direct_from_filename(filename)
    filename_path_mode = extract_path_mode_from_filename(filename)

    # Prefer fio job option iodepth for the actual runtime setting.
    # The filename qd is kept separately as metadata.
    iodepth = job_options.get("iodepth")

    return {
        "file": filename,
        "source_dir": str(json_path.parent),
        "workload": infer_workload_from_filename(filename),
        "run": extract_run_number(filename),
        "qd_from_filename": filename_qd,
        "direct_from_filename": filename_direct,
        "path_mode_from_filename": filename_path_mode,
        "job_name": job.get("jobname"),
        "rw": job_options.get("rw", direction),
        "active_direction": direction,
        "bs": job_options.get("bs"),
        "iodepth": iodepth,
        "numjobs": job_options.get("numjobs"),
        "size": job_options.get("size"),
        "direct": job_options.get("direct"),
        "runtime_sec": runtime_sec,
        "bandwidth_mib_s": bytes_per_sec_to_mib_per_sec(bw_bytes),
        "iops": iops,
        "clat_mean_us": ns_to_us(clat_mean_ns),
        "clat_p95_us": ns_to_us(p95_ns),
        "clat_p99_us": ns_to_us(p99_ns),
        "clat_p999_us": ns_to_us(p999_ns),
        "fio_version": fio_root.get("fio version"),
        "timestamp": fio_root.get("timestamp"),
        "timestamp_ms": fio_root.get("timestamp_ms"),
    }


def parse_all(input_dir: Path) -> List[Dict[str, Any]]:
    """
    Parse all JSON files in input_dir.
    """
    json_files = sorted(input_dir.glob("*.json"))

    if not json_files:
        raise FileNotFoundError(f"No JSON files found in {input_dir}")

    all_rows: List[Dict[str, Any]] = []

    for json_path in json_files:
        try:
            rows = parse_one_json(json_path)
            all_rows.extend(rows)
        except Exception as exc:
            print(f"[WARN] Failed to parse {json_path.name}: {exc}")

    return all_rows


# -----------------------------
# CSV output / terminal summary
# -----------------------------

def write_csv(rows: List[Dict[str, Any]], output_path: Path) -> None:
    """
    Write parsed rows to CSV.
    """
    if not rows:
        raise ValueError("No rows to write.")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "file",
        "source_dir",
        "workload",
        "run",
        "qd_from_filename",
        "direct_from_filename",
        "path_mode_from_filename",
        "job_name",
        "rw",
        "active_direction",
        "bs",
        "iodepth",
        "numjobs",
        "size",
        "direct",
        "runtime_sec",
        "bandwidth_mib_s",
        "iops",
        "clat_mean_us",
        "clat_p95_us",
        "clat_p99_us",
        "clat_p999_us",
        "fio_version",
        "timestamp",
        "timestamp_ms",
    ]

    with output_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def fmt_num(value: Any, digits: int = 2) -> str:
    """
    Format numeric value for terminal printing.
    """
    if value is None:
        return "NA"

    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def print_summary(rows: List[Dict[str, Any]], output_path: Path) -> None:
    """
    Print simple parsing summary.
    """
    print()
    print("=== fio JSON parse summary ===")
    print(f"Parsed rows : {len(rows)}")
    print(f"Output CSV  : {output_path}")

    workloads = sorted(set(str(row.get("workload")) for row in rows))
    qds = sorted(
        {
            int(row["qd_from_filename"])
            for row in rows
            if row.get("qd_from_filename") is not None
        }
    )

    print(f"Workloads   : {', '.join(workloads)}")

    if qds:
        print(f"QD values   : {', '.join(str(qd) for qd in qds)}")
    else:
        print("QD values   : none in filename")

    print()
    print("Rows:")

    for row in rows:
        print(
            f"- {row['file']} | "
            f"workload={row['workload']} | "
            f"run={row['run']} | "
            f"qd_file={row['qd_from_filename']} | "
            f"direct_file={row['direct_from_filename']} | "
            f"path_mode={row['path_mode_from_filename']} | "
            f"iodepth={row['iodepth']} | "
            f"rw={row['rw']} | "
            f"bw={fmt_num(row['bandwidth_mib_s'])} MiB/s | "
            f"iops={fmt_num(row['iops'])} | "
            f"p99={fmt_num(row['clat_p99_us'])} us"
        )


# -----------------------------
# Main
# -----------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parse fio JSON results into a validation-oriented CSV summary."
    )

    parser.add_argument(
        "--input-dir",
        type=str,
        default=r"D:\ssd_lab\results",
        help=r"Directory containing fio JSON files. Default: D:\ssd_lab\results",
    )

    parser.add_argument(
        "--output",
        type=str,
        default=r"D:\ssd_lab\results\fio_summary.csv",
        help=r"Output CSV path. Default: D:\ssd_lab\results\fio_summary.csv",
    )

    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_path = Path(args.output)

    rows = parse_all(input_dir)
    write_csv(rows, output_path)
    print_summary(rows, output_path)


if __name__ == "__main__":
    main()
