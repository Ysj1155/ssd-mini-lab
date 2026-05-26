"""
analyze_direct_buffered.py

Purpose:
    Analyze fio direct I/O vs buffered I/O experiment results.

Input:
    D:\\ssd_lab\\results\\direct_buffered_summary.csv

Outputs:
    D:\\ssd_lab\\results\\direct_buffered_grouped.csv
    D:\\ssd_lab\\results\\direct_buffered_comparison.csv
    D:\\ssd_lab\\results\\direct_buffered_plots\\direct_buffered_iops.png
    D:\\ssd_lab\\results\\direct_buffered_plots\\direct_buffered_bandwidth.png
    D:\\ssd_lab\\results\\direct_buffered_plots\\direct_buffered_p99_latency.png
    D:\\ssd_lab\\results\\direct_buffered_plots\\direct_buffered_mean_latency.png

Usage:
    cd D:\\ssd_lab
    python .\\analyze_direct_buffered.py
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


DEFAULT_INPUT = r"D:\ssd_lab\results\direct_buffered_summary.csv"
DEFAULT_GROUPED_OUTPUT = r"D:\ssd_lab\results\direct_buffered_grouped.csv"
DEFAULT_COMPARISON_OUTPUT = r"D:\ssd_lab\results\direct_buffered_comparison.csv"
DEFAULT_PLOT_DIR = r"D:\ssd_lab\results\direct_buffered_plots"

GROUP_COLS = ["workload", "direct_mode"]

METRICS = [
    "bandwidth_mib_s",
    "iops",
    "clat_mean_us",
    "clat_p95_us",
    "clat_p99_us",
    "clat_p999_us",
]

REQUIRED_COLUMNS = [
    "file",
    "workload",
    "run",
    "direct",
    "direct_from_filename",
] + METRICS


def load_direct_buffered_summary(input_path: Path) -> pd.DataFrame:
    """Load parser output and keep only direct/buffered experiment rows."""
    if not input_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_path}")

    df = pd.read_csv(input_path)

    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    numeric_cols = ["run", "direct", "direct_from_filename"] + METRICS
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    before = len(df)
    df = df.dropna(subset=["run", "direct_from_filename"] + METRICS).copy()
    after = len(df)

    if before != after:
        print(f"[INFO] Ignored {before - after} non-comparison rows, usually prefill.")

    if df.empty:
        raise ValueError("No direct/buffered comparison rows found.")

    df["run"] = df["run"].astype(int)
    df["direct_from_filename"] = df["direct_from_filename"].astype(int)
    df["direct"] = df["direct"].astype(int)
    df["direct_mode"] = df["direct_from_filename"]
    df["mode_label"] = df["direct_mode"].map({1: "direct=1", 0: "direct=0"})

    mismatches = df[df["direct"] != df["direct_from_filename"]]
    if not mismatches.empty:
        mismatch_files = ", ".join(mismatches["file"].astype(str).tolist())
        print(f"[WARN] direct option and filename disagree for: {mismatch_files}")

    return df.sort_values(["workload", "direct_mode", "run"]).reset_index(drop=True)


def coefficient_of_variation(series: pd.Series) -> float | None:
    """Return std / mean for repeated runs."""
    mean_value = series.mean()
    std_value = series.std()

    if pd.isna(mean_value) or mean_value == 0:
        return None

    return std_value / mean_value


def make_grouped_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate repeated runs by workload and direct mode."""
    rows = []

    for (workload, direct_mode), part in df.groupby(GROUP_COLS):
        row = {
            "workload": workload,
            "direct_mode": int(direct_mode),
            "mode_label": "direct=1" if int(direct_mode) == 1 else "direct=0",
            "run_count": len(part),
        }

        for metric in METRICS:
            values = part[metric].dropna()
            row[f"{metric}_mean"] = values.mean()
            row[f"{metric}_std"] = values.std()
            row[f"{metric}_min"] = values.min()
            row[f"{metric}_max"] = values.max()
            row[f"{metric}_cv"] = coefficient_of_variation(values)

        rows.append(row)

    grouped = pd.DataFrame(rows)
    return grouped.sort_values(["workload", "direct_mode"]).reset_index(drop=True)


def make_comparison_summary(grouped: pd.DataFrame) -> pd.DataFrame:
    """Compare buffered mode against direct mode for each workload."""
    rows = []

    for workload, part in grouped.groupby("workload"):
        direct = part[part["direct_mode"] == 1]
        buffered = part[part["direct_mode"] == 0]

        if direct.empty or buffered.empty:
            continue

        direct_row = direct.iloc[0]
        buffered_row = buffered.iloc[0]

        row = {
            "workload": workload,
            "direct_run_count": int(direct_row["run_count"]),
            "buffered_run_count": int(buffered_row["run_count"]),
        }

        for metric in METRICS:
            direct_mean = direct_row[f"{metric}_mean"]
            buffered_mean = buffered_row[f"{metric}_mean"]
            row[f"direct_{metric}_mean"] = direct_mean
            row[f"buffered_{metric}_mean"] = buffered_mean
            row[f"buffered_over_direct_{metric}"] = (
                buffered_mean / direct_mean if direct_mean else None
            )
            row[f"buffered_minus_direct_{metric}"] = buffered_mean - direct_mean

        rows.append(row)

    return pd.DataFrame(rows).sort_values("workload").reset_index(drop=True)


def save_csv(df: pd.DataFrame, path: Path, label: str) -> None:
    """Save a DataFrame as UTF-8-sig CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"[OK] Saved {label}: {path}")


def plot_grouped_bars(
    grouped: pd.DataFrame,
    metric_mean_col: str,
    metric_std_col: str,
    ylabel: str,
    title: str,
    output_path: Path,
) -> None:
    """Plot direct=1 vs direct=0 bars for each workload."""
    workloads = sorted(grouped["workload"].unique())
    x_positions = range(len(workloads))
    width = 0.35
    modes = [(1, "direct=1"), (0, "direct=0")]
    offsets = {1: -width / 2, 0: width / 2}
    colors = {1: "#345995", 0: "#E07A5F"}

    fig, ax = plt.subplots(figsize=(8, 5))

    for direct_mode, label in modes:
        values = []
        errors = []

        for workload in workloads:
            row = grouped[
                (grouped["workload"] == workload)
                & (grouped["direct_mode"] == direct_mode)
            ]

            if row.empty:
                values.append(0)
                errors.append(0)
            else:
                values.append(row.iloc[0][metric_mean_col])
                errors.append(row.iloc[0][metric_std_col])

        xs = [x + offsets[direct_mode] for x in x_positions]
        ax.bar(
            xs,
            values,
            width=width,
            yerr=errors,
            capsize=4,
            label=label,
            color=colors[direct_mode],
        )

    ax.set_title(title)
    ax.set_xlabel("Workload")
    ax.set_ylabel(ylabel)
    ax.set_xticks(list(x_positions))
    ax.set_xticklabels(workloads)
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend()
    fig.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)

    print(f"[OK] Saved plot: {output_path}")


def print_console_summary(grouped: pd.DataFrame, comparison: pd.DataFrame) -> None:
    """Print compact direct/buffered interpretation."""
    display_cols = [
        "workload",
        "mode_label",
        "run_count",
        "bandwidth_mib_s_mean",
        "iops_mean",
        "clat_p99_us_mean",
    ]

    print()
    print("=== Direct vs Buffered Grouped Summary ===")
    print(
        grouped[display_cols].to_string(
            index=False,
            formatters={
                "bandwidth_mib_s_mean": "{:.2f}".format,
                "iops_mean": "{:.2f}".format,
                "clat_p99_us_mean": "{:.2f}".format,
            },
        )
    )

    if comparison.empty:
        return

    print()
    print("=== Buffered / Direct Ratios ===")
    ratio_cols = [
        "workload",
        "buffered_over_direct_bandwidth_mib_s",
        "buffered_over_direct_iops",
        "buffered_over_direct_clat_p99_us",
    ]
    print(
        comparison[ratio_cols].to_string(
            index=False,
            formatters={
                "buffered_over_direct_bandwidth_mib_s": "{:.3f}".format,
                "buffered_over_direct_iops": "{:.3f}".format,
                "buffered_over_direct_clat_p99_us": "{:.3f}".format,
            },
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze fio direct I/O vs buffered I/O results."
    )
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Input parser CSV path.")
    parser.add_argument(
        "--grouped-output",
        default=DEFAULT_GROUPED_OUTPUT,
        help="Output grouped CSV path.",
    )
    parser.add_argument(
        "--comparison-output",
        default=DEFAULT_COMPARISON_OUTPUT,
        help="Output comparison CSV path.",
    )
    parser.add_argument("--plot-dir", default=DEFAULT_PLOT_DIR, help="Output plot dir.")

    args = parser.parse_args()

    input_path = Path(args.input)
    grouped_output = Path(args.grouped_output)
    comparison_output = Path(args.comparison_output)
    plot_dir = Path(args.plot_dir)

    print("=== analyze_direct_buffered.py ===")
    print(f"Input CSV       : {input_path}")
    print(f"Grouped output  : {grouped_output}")
    print(f"Comparison CSV  : {comparison_output}")
    print(f"Plot dir        : {plot_dir}")

    df = load_direct_buffered_summary(input_path)
    print(f"[OK] Loaded comparison rows: {len(df)}")

    grouped = make_grouped_summary(df)
    comparison = make_comparison_summary(grouped)

    save_csv(grouped, grouped_output, "grouped summary")
    save_csv(comparison, comparison_output, "comparison summary")

    plot_grouped_bars(
        grouped=grouped,
        metric_mean_col="iops_mean",
        metric_std_col="iops_std",
        ylabel="IOPS",
        title="Direct vs Buffered - IOPS",
        output_path=plot_dir / "direct_buffered_iops.png",
    )
    plot_grouped_bars(
        grouped=grouped,
        metric_mean_col="bandwidth_mib_s_mean",
        metric_std_col="bandwidth_mib_s_std",
        ylabel="Bandwidth (MiB/s)",
        title="Direct vs Buffered - Bandwidth",
        output_path=plot_dir / "direct_buffered_bandwidth.png",
    )
    plot_grouped_bars(
        grouped=grouped,
        metric_mean_col="clat_p99_us_mean",
        metric_std_col="clat_p99_us_std",
        ylabel="p99 Completion Latency (us)",
        title="Direct vs Buffered - p99 Latency",
        output_path=plot_dir / "direct_buffered_p99_latency.png",
    )
    plot_grouped_bars(
        grouped=grouped,
        metric_mean_col="clat_mean_us_mean",
        metric_std_col="clat_mean_us_std",
        ylabel="Mean Completion Latency (us)",
        title="Direct vs Buffered - Mean Latency",
        output_path=plot_dir / "direct_buffered_mean_latency.png",
    )

    print_console_summary(grouped, comparison)

    print()
    print("[DONE] Direct vs buffered analysis completed.")


if __name__ == "__main__":
    main()
