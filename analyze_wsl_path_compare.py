"""
analyze_wsl_path_compare.py

Purpose:
    Analyze fio results comparing WSL native ext4 path vs /mnt/d path.

Input:
    D:\\ssd_lab\\results\\wsl_path_compare_summary.csv

Outputs:
    D:\\ssd_lab\\results\\wsl_path_compare_grouped.csv
    D:\\ssd_lab\\results\\wsl_path_compare_comparison.csv
    D:\\ssd_lab\\results\\wsl_path_compare_plots\\*.png

Usage:
    cd D:\\ssd_lab
    python .\\parse_fio_results.py `
      --input-dir D:\\ssd_lab\\results\\wsl_path_compare `
      --output D:\\ssd_lab\\results\\wsl_path_compare_summary.csv

    python .\\analyze_wsl_path_compare.py
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


DEFAULT_INPUT = r"D:\ssd_lab\results\wsl_path_compare_summary.csv"
DEFAULT_GROUPED_OUTPUT = r"D:\ssd_lab\results\wsl_path_compare_grouped.csv"
DEFAULT_COMPARISON_OUTPUT = r"D:\ssd_lab\results\wsl_path_compare_comparison.csv"
DEFAULT_PLOT_DIR = r"D:\ssd_lab\results\wsl_path_compare_plots"

GROUP_COLS = ["workload", "path_mode_from_filename"]

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
    "path_mode_from_filename",
] + METRICS

PATH_ORDER = ["wsl_ext4", "mnt_d"]
PATH_LABELS = {
    "wsl_ext4": "WSL ext4",
    "mnt_d": "/mnt/d",
}


def load_summary(input_path: Path) -> pd.DataFrame:
    """Load parser output and keep only path-comparison rows."""
    if not input_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_path}")

    df = pd.read_csv(input_path)

    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    numeric_cols = ["run"] + METRICS
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    before = len(df)
    df = df.dropna(subset=["run", "path_mode_from_filename"] + METRICS).copy()
    after = len(df)

    if before != after:
        print(f"[INFO] Ignored {before - after} non-comparison rows, usually prefill.")

    if df.empty:
        raise ValueError("No WSL path comparison rows found.")

    df["run"] = df["run"].astype(int)
    df["path_mode_from_filename"] = df["path_mode_from_filename"].astype(str)
    df["path_label"] = df["path_mode_from_filename"].map(PATH_LABELS).fillna(
        df["path_mode_from_filename"]
    )

    return df.sort_values(["workload", "path_mode_from_filename", "run"]).reset_index(
        drop=True
    )


def coefficient_of_variation(series: pd.Series) -> float | None:
    """Return std / mean for repeated runs."""
    mean_value = series.mean()
    std_value = series.std()

    if pd.isna(mean_value) or mean_value == 0:
        return None

    return std_value / mean_value


def make_grouped_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate repeated runs by workload and path mode."""
    rows = []

    for (workload, path_mode), part in df.groupby(GROUP_COLS):
        row = {
            "workload": workload,
            "path_mode": path_mode,
            "path_label": PATH_LABELS.get(path_mode, path_mode),
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
    grouped["path_sort"] = grouped["path_mode"].apply(
        lambda value: PATH_ORDER.index(value) if value in PATH_ORDER else len(PATH_ORDER)
    )
    grouped = grouped.sort_values(["workload", "path_sort"]).drop(columns="path_sort")

    return grouped.reset_index(drop=True)


def make_comparison_summary(grouped: pd.DataFrame) -> pd.DataFrame:
    """Compare /mnt/d against WSL ext4 for each workload."""
    rows = []

    for workload, part in grouped.groupby("workload"):
        ext4 = part[part["path_mode"] == "wsl_ext4"]
        mnt_d = part[part["path_mode"] == "mnt_d"]

        if ext4.empty or mnt_d.empty:
            continue

        ext4_row = ext4.iloc[0]
        mnt_d_row = mnt_d.iloc[0]

        row = {
            "workload": workload,
            "wsl_ext4_run_count": int(ext4_row["run_count"]),
            "mnt_d_run_count": int(mnt_d_row["run_count"]),
        }

        for metric in METRICS:
            ext4_mean = ext4_row[f"{metric}_mean"]
            mnt_d_mean = mnt_d_row[f"{metric}_mean"]

            row[f"wsl_ext4_{metric}_mean"] = ext4_mean
            row[f"mnt_d_{metric}_mean"] = mnt_d_mean
            row[f"mnt_d_over_wsl_ext4_{metric}"] = (
                mnt_d_mean / ext4_mean if ext4_mean else None
            )
            row[f"mnt_d_minus_wsl_ext4_{metric}"] = mnt_d_mean - ext4_mean

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
    """Plot WSL ext4 vs /mnt/d bars for each workload."""
    workloads = sorted(grouped["workload"].unique())
    x_positions = range(len(workloads))
    width = 0.35
    modes = [("wsl_ext4", "WSL ext4"), ("mnt_d", "/mnt/d")]
    offsets = {"wsl_ext4": -width / 2, "mnt_d": width / 2}
    colors = {"wsl_ext4": "#345995", "mnt_d": "#E07A5F"}

    fig, ax = plt.subplots(figsize=(8, 5))

    for path_mode, label in modes:
        values = []
        errors = []

        for workload in workloads:
            row = grouped[
                (grouped["workload"] == workload)
                & (grouped["path_mode"] == path_mode)
            ]

            if row.empty:
                values.append(0)
                errors.append(0)
            else:
                values.append(row.iloc[0][metric_mean_col])
                errors.append(row.iloc[0][metric_std_col])

        xs = [x + offsets[path_mode] for x in x_positions]
        ax.bar(
            xs,
            values,
            width=width,
            yerr=errors,
            capsize=4,
            label=label,
            color=colors[path_mode],
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
    """Print compact path comparison summary."""
    display_cols = [
        "workload",
        "path_label",
        "run_count",
        "bandwidth_mib_s_mean",
        "iops_mean",
        "clat_p99_us_mean",
    ]

    print()
    print("=== WSL Path Compare Grouped Summary ===")
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

    ratio_cols = [
        "workload",
        "mnt_d_over_wsl_ext4_bandwidth_mib_s",
        "mnt_d_over_wsl_ext4_iops",
        "mnt_d_over_wsl_ext4_clat_p99_us",
    ]

    print()
    print("=== /mnt/d over WSL ext4 Ratios ===")
    print(
        comparison[ratio_cols].to_string(
            index=False,
            formatters={
                "mnt_d_over_wsl_ext4_bandwidth_mib_s": "{:.3f}".format,
                "mnt_d_over_wsl_ext4_iops": "{:.3f}".format,
                "mnt_d_over_wsl_ext4_clat_p99_us": "{:.3f}".format,
            },
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze WSL path comparison results.")
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

    print("=== analyze_wsl_path_compare.py ===")
    print(f"Input CSV       : {input_path}")
    print(f"Grouped output  : {grouped_output}")
    print(f"Comparison CSV  : {comparison_output}")
    print(f"Plot dir        : {plot_dir}")

    df = load_summary(input_path)
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
        title="WSL Path Compare - IOPS",
        output_path=plot_dir / "wsl_path_compare_iops.png",
    )
    plot_grouped_bars(
        grouped=grouped,
        metric_mean_col="bandwidth_mib_s_mean",
        metric_std_col="bandwidth_mib_s_std",
        ylabel="Bandwidth (MiB/s)",
        title="WSL Path Compare - Bandwidth",
        output_path=plot_dir / "wsl_path_compare_bandwidth.png",
    )
    plot_grouped_bars(
        grouped=grouped,
        metric_mean_col="clat_p99_us_mean",
        metric_std_col="clat_p99_us_std",
        ylabel="p99 Completion Latency (us)",
        title="WSL Path Compare - p99 Latency",
        output_path=plot_dir / "wsl_path_compare_p99_latency.png",
    )
    plot_grouped_bars(
        grouped=grouped,
        metric_mean_col="clat_mean_us_mean",
        metric_std_col="clat_mean_us_std",
        ylabel="Mean Completion Latency (us)",
        title="WSL Path Compare - Mean Latency",
        output_path=plot_dir / "wsl_path_compare_mean_latency.png",
    )

    print_console_summary(grouped, comparison)

    print()
    print("[DONE] WSL path comparison analysis completed.")


if __name__ == "__main__":
    main()
