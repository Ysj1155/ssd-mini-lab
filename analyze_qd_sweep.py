# analyze_qd_sweep.py
"""
Analyze fio QD sweep results.

Input:
    results/qd_sweep_summary.csv

Outputs:
    results/qd_sweep_grouped.csv
    results/qd_sweep_plots/qd_sweep_iops.png
    results/qd_sweep_plots/qd_sweep_bandwidth.png
    results/qd_sweep_plots/qd_sweep_p99_latency.png
    results/qd_sweep_plots/qd_sweep_mean_latency.png

Purpose:
    - Summarize repeated fio runs by workload and queue depth.
    - Compute mean/std/min/max for key metrics.
    - Generate QD-vs-performance and QD-vs-latency plots.

Usage:
    python .\\analyze_qd_sweep.py
"""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import matplotlib.pyplot as plt


# ---------------------------------------------------------------------
# Fixed project paths
# ---------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
INPUT_CSV = BASE_DIR / "results" / "qd_sweep_summary.csv"
OUTPUT_CSV = BASE_DIR / "results" / "qd_sweep_grouped.csv"
PLOT_DIR = BASE_DIR / "results" / "qd_sweep_plots"


# ---------------------------------------------------------------------
# Columns expected from parse_fio_results.py
# ---------------------------------------------------------------------
GROUP_COLS = ["workload", "qd_from_filename"]

METRIC_COLS = [
    "bandwidth_mib_s",
    "iops",
    "clat_mean_us",
    "clat_p95_us",
    "clat_p99_us",
    "clat_p999_us",
]

REQUIRED_COLS = GROUP_COLS + METRIC_COLS


def fail(message: str) -> None:
    """Print an error message and stop execution."""
    print(f"[ERROR] {message}", file=sys.stderr)
    sys.exit(1)


def load_input_csv(path: Path) -> pd.DataFrame:
    """Load qd_sweep_summary.csv and validate required columns."""
    if not path.exists():
        fail(f"Input CSV not found: {path}")

    df = pd.read_csv(path)

    missing = [col for col in REQUIRED_COLS if col not in df.columns]
    if missing:
        fail(
            "Required columns are missing from input CSV: "
            + ", ".join(missing)
        )

    # Force numeric conversion.
    # If a value cannot be parsed, it becomes NaN.
    numeric_cols = ["qd_from_filename"] + METRIC_COLS
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Drop rows that cannot be analyzed.
    before = len(df)
    df = df.dropna(subset=REQUIRED_COLS)
    after = len(df)

    if after == 0:
        fail("No valid rows remain after dropping rows with missing values.")

    if before != after:
        print(f"[WARN] Dropped {before - after} rows due to missing/invalid values.")

    # QD should be integer-like.
    df["qd_from_filename"] = df["qd_from_filename"].astype(int)

    return df


def make_grouped_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Group by workload and QD.

    Output columns use flattened names such as:
        iops_mean
        iops_std
        iops_min
        iops_max
    """
    grouped = (
        df.groupby(GROUP_COLS, as_index=False)
        .agg(
            run_count=("file", "count") if "file" in df.columns else ("iops", "count"),
            bandwidth_mib_s_mean=("bandwidth_mib_s", "mean"),
            bandwidth_mib_s_std=("bandwidth_mib_s", "std"),
            bandwidth_mib_s_min=("bandwidth_mib_s", "min"),
            bandwidth_mib_s_max=("bandwidth_mib_s", "max"),
            iops_mean=("iops", "mean"),
            iops_std=("iops", "std"),
            iops_min=("iops", "min"),
            iops_max=("iops", "max"),
            clat_mean_us_mean=("clat_mean_us", "mean"),
            clat_mean_us_std=("clat_mean_us", "std"),
            clat_p95_us_mean=("clat_p95_us", "mean"),
            clat_p95_us_std=("clat_p95_us", "std"),
            clat_p99_us_mean=("clat_p99_us", "mean"),
            clat_p99_us_std=("clat_p99_us", "std"),
            clat_p999_us_mean=("clat_p999_us", "mean"),
            clat_p999_us_std=("clat_p999_us", "std"),
        )
        .sort_values(["workload", "qd_from_filename"])
        .reset_index(drop=True)
    )

    # Standard deviation is NaN when run_count == 1.
    # For this QD sweep, each group should usually have 3 runs.
    grouped = grouped.fillna({"bandwidth_mib_s_std": 0.0, "iops_std": 0.0})

    return grouped


def save_grouped_summary(grouped: pd.DataFrame, path: Path) -> None:
    """Save grouped summary CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    grouped.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"[OK] Saved grouped summary: {path}")


def plot_metric(
    grouped: pd.DataFrame,
    metric_mean_col: str,
    metric_std_col: str | None,
    ylabel: str,
    title: str,
    output_path: Path,
) -> None:
    """
    Plot QD vs metric.

    One line per workload.
    Error bars are included when std column is available.
    """
    fig, ax = plt.subplots(figsize=(8, 5))

    for workload, part in grouped.groupby("workload"):
        part = part.sort_values("qd_from_filename")

        x = part["qd_from_filename"]
        y = part[metric_mean_col]

        if metric_std_col and metric_std_col in part.columns:
            yerr = part[metric_std_col]
            ax.errorbar(x, y, yerr=yerr, marker="o", capsize=4, label=workload)
        else:
            ax.plot(x, y, marker="o", label=workload)

    ax.set_title(title)
    ax.set_xlabel("Queue Depth / iodepth")
    ax.set_ylabel(ylabel)
    ax.set_xticks(sorted(grouped["qd_from_filename"].unique()))
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)

    print(f"[OK] Saved plot: {output_path}")


def print_console_summary(grouped: pd.DataFrame) -> None:
    """Print compact summary for quick terminal inspection."""
    display_cols = [
        "workload",
        "qd_from_filename",
        "run_count",
        "bandwidth_mib_s_mean",
        "iops_mean",
        "clat_p99_us_mean",
    ]

    print()
    print("=== QD Sweep Grouped Summary ===")
    print(
        grouped[display_cols]
        .to_string(
            index=False,
            formatters={
                "bandwidth_mib_s_mean": "{:.2f}".format,
                "iops_mean": "{:.2f}".format,
                "clat_p99_us_mean": "{:.2f}".format,
            },
        )
    )

    print()
    print("=== Quick Interpretation Hints ===")
    for workload, part in grouped.groupby("workload"):
        part = part.sort_values("qd_from_filename")

        best_iops_row = part.loc[part["iops_mean"].idxmax()]
        best_bw_row = part.loc[part["bandwidth_mib_s_mean"].idxmax()]
        worst_p99_row = part.loc[part["clat_p99_us_mean"].idxmax()]

        print(f"- {workload}:")
        print(
            f"  best IOPS QD={int(best_iops_row['qd_from_filename'])}, "
            f"IOPS={best_iops_row['iops_mean']:.2f}"
        )
        print(
            f"  best bandwidth QD={int(best_bw_row['qd_from_filename'])}, "
            f"BW={best_bw_row['bandwidth_mib_s_mean']:.2f} MiB/s"
        )
        print(
            f"  highest p99 latency QD={int(worst_p99_row['qd_from_filename'])}, "
            f"p99={worst_p99_row['clat_p99_us_mean']:.2f} us"
        )


def main() -> None:
    print("=== analyze_qd_sweep.py ===")
    print(f"Input CSV : {INPUT_CSV}")
    print(f"Output CSV: {OUTPUT_CSV}")
    print(f"Plot dir  : {PLOT_DIR}")

    df = load_input_csv(INPUT_CSV)
    print(f"[OK] Loaded rows: {len(df)}")

    grouped = make_grouped_summary(df)
    save_grouped_summary(grouped, OUTPUT_CSV)

    plot_metric(
        grouped=grouped,
        metric_mean_col="iops_mean",
        metric_std_col="iops_std",
        ylabel="IOPS",
        title="QD Sweep - IOPS",
        output_path=PLOT_DIR / "qd_sweep_iops.png",
    )

    plot_metric(
        grouped=grouped,
        metric_mean_col="bandwidth_mib_s_mean",
        metric_std_col="bandwidth_mib_s_std",
        ylabel="Bandwidth (MiB/s)",
        title="QD Sweep - Bandwidth",
        output_path=PLOT_DIR / "qd_sweep_bandwidth.png",
    )

    plot_metric(
        grouped=grouped,
        metric_mean_col="clat_p99_us_mean",
        metric_std_col="clat_p99_us_std",
        ylabel="p99 Completion Latency (us)",
        title="QD Sweep - p99 Latency",
        output_path=PLOT_DIR / "qd_sweep_p99_latency.png",
    )

    plot_metric(
        grouped=grouped,
        metric_mean_col="clat_mean_us_mean",
        metric_std_col="clat_mean_us_std",
        ylabel="Mean Completion Latency (us)",
        title="QD Sweep - Mean Latency",
        output_path=PLOT_DIR / "qd_sweep_mean_latency.png",
    )

    print_console_summary(grouped)

    print()
    print("[DONE] QD sweep analysis completed.")


if __name__ == "__main__":
    main()