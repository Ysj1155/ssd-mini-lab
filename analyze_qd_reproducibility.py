"""
analyze_qd_reproducibility.py

Purpose:
    Analyze run-to-run reproducibility of fio QD sweep results.

Input:
    D:\\ssd_lab\\results\\qd_sweep_summary.csv

Outputs:
    D:\\ssd_lab\\results\\qd_sweep_reproducibility.csv
    D:\\ssd_lab\\results\\qd_sweep_plots\\qd_sweep_iops_cv.png
    D:\\ssd_lab\\results\\qd_sweep_plots\\qd_sweep_bandwidth_cv.png
    D:\\ssd_lab\\results\\qd_sweep_plots\\qd_sweep_p99_cv.png
    D:\\ssd_lab\\results\\qd_sweep_plots\\qd_sweep_p99_run_to_run.png

Usage:
    PowerShell:
        cd D:\\ssd_lab
        python .\\analyze_qd_reproducibility.py

Notes:
    CV = standard deviation / mean

    Lower CV means better run-to-run stability.
    Higher CV means the metric fluctuates more across repeated runs.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


DEFAULT_INPUT = r"D:\ssd_lab\results\qd_sweep_summary.csv"
DEFAULT_OUTPUT = r"D:\ssd_lab\results\qd_sweep_reproducibility.csv"
DEFAULT_PLOT_DIR = r"D:\ssd_lab\results\qd_sweep_plots"

GROUP_COLS = ["workload", "qd_from_filename"]

METRICS = [
    "bandwidth_mib_s",
    "iops",
    "clat_mean_us",
    "clat_p95_us",
    "clat_p99_us",
    "clat_p999_us",
]

REQUIRED_COLUMNS = GROUP_COLS + ["run"] + METRICS


def load_qd_summary(input_path: Path) -> pd.DataFrame:
    """
    Load qd_sweep_summary.csv and normalize numeric columns.
    """
    if not input_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_path}")

    df = pd.read_csv(input_path)

    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    numeric_cols = ["run", "qd_from_filename"] + METRICS

    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    before = len(df)
    df = df.dropna(subset=REQUIRED_COLUMNS).copy()
    after = len(df)

    if before != after:
        print(f"[WARN] Dropped {before - after} rows with invalid values.")

    df["qd_from_filename"] = df["qd_from_filename"].astype(int)
    df["run"] = df["run"].astype(int)

    return df.sort_values(["workload", "qd_from_filename", "run"]).reset_index(drop=True)


def cv(series: pd.Series) -> float | None:
    """
    Coefficient of variation.

    CV = std / mean
    """
    mean_value = series.mean()
    std_value = series.std()

    if pd.isna(mean_value) or mean_value == 0:
        return None

    return std_value / mean_value


def make_reproducibility_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Make reproducibility summary by workload and QD.
    """
    rows = []

    for (workload, qd), part in df.groupby(GROUP_COLS):
        row = {
            "workload": workload,
            "qd_from_filename": int(qd),
            "run_count": len(part),
        }

        for metric in METRICS:
            values = part[metric].dropna()

            row[f"{metric}_mean"] = values.mean()
            row[f"{metric}_std"] = values.std()
            row[f"{metric}_min"] = values.min()
            row[f"{metric}_max"] = values.max()
            row[f"{metric}_range"] = values.max() - values.min()
            row[f"{metric}_cv"] = cv(values)

        rows.append(row)

    result = pd.DataFrame(rows)
    result = result.sort_values(["workload", "qd_from_filename"]).reset_index(drop=True)

    return result


def save_reproducibility_summary(summary: pd.DataFrame, output_path: Path) -> None:
    """
    Save reproducibility summary CSV.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"[OK] Saved reproducibility CSV: {output_path}")


def plot_cv(
    summary: pd.DataFrame,
    metric_cv_col: str,
    ylabel: str,
    title: str,
    output_path: Path,
) -> None:
    """
    Plot CV by QD for each workload.
    """
    plt.figure(figsize=(8, 5))

    for workload, part in summary.groupby("workload"):
        part = part.sort_values("qd_from_filename")
        plt.plot(
            part["qd_from_filename"],
            part[metric_cv_col],
            marker="o",
            label=workload,
        )

    plt.xlabel("Queue Depth / iodepth")
    plt.ylabel(ylabel)
    plt.title(title)
    plt.xticks(sorted(summary["qd_from_filename"].unique()))
    plt.grid(True, linestyle="--", alpha=0.4)
    plt.legend()
    plt.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150)
    plt.close()

    print(f"[OK] Saved plot: {output_path}")


def plot_run_to_run(
    df: pd.DataFrame,
    metric: str,
    ylabel: str,
    title: str,
    output_path: Path,
) -> None:
    """
    Plot run-to-run values for each workload/QD pair.
    """
    plt.figure(figsize=(10, 6))

    for (workload, qd), part in df.groupby(["workload", "qd_from_filename"]):
        part = part.sort_values("run")
        label = f"{workload} QD{int(qd)}"

        plt.plot(
            part["run"],
            part[metric],
            marker="o",
            label=label,
        )

    plt.xlabel("Run")
    plt.ylabel(ylabel)
    plt.title(title)

    runs = sorted(df["run"].dropna().unique())
    if runs:
        plt.xticks(runs)

    plt.grid(True, linestyle="--", alpha=0.4)
    plt.legend(fontsize=8, ncol=2)
    plt.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150)
    plt.close()

    print(f"[OK] Saved plot: {output_path}")


def print_summary(summary: pd.DataFrame) -> None:
    """
    Print compact terminal summary.
    """
    cols = [
        "workload",
        "qd_from_filename",
        "run_count",
        "bandwidth_mib_s_cv",
        "iops_cv",
        "clat_p99_us_cv",
    ]

    print()
    print("=== QD Sweep Reproducibility Summary ===")
    print(summary[cols].to_string(index=False, formatters={
        "bandwidth_mib_s_cv": "{:.4f}".format,
        "iops_cv": "{:.4f}".format,
        "clat_p99_us_cv": "{:.4f}".format,
    }))

    print()
    print("=== Highest CV by metric ===")

    for metric_cv_col in ["bandwidth_mib_s_cv", "iops_cv", "clat_p99_us_cv"]:
        idx = summary[metric_cv_col].idxmax()
        row = summary.loc[idx]

        print(
            f"- {metric_cv_col}: "
            f"{row['workload']} QD{int(row['qd_from_filename'])} "
            f"CV={row[metric_cv_col]:.4f}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze run-to-run reproducibility of QD sweep results."
    )

    parser.add_argument(
        "--input",
        type=str,
        default=DEFAULT_INPUT,
        help=f"Input qd_sweep_summary.csv path. Default: {DEFAULT_INPUT}",
    )

    parser.add_argument(
        "--output",
        type=str,
        default=DEFAULT_OUTPUT,
        help=f"Output reproducibility CSV path. Default: {DEFAULT_OUTPUT}",
    )

    parser.add_argument(
        "--plot-dir",
        type=str,
        default=DEFAULT_PLOT_DIR,
        help=f"Output plot directory. Default: {DEFAULT_PLOT_DIR}",
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    plot_dir = Path(args.plot_dir)

    print("=== analyze_qd_reproducibility.py ===")
    print(f"Input CSV : {input_path}")
    print(f"Output CSV: {output_path}")
    print(f"Plot dir  : {plot_dir}")

    df = load_qd_summary(input_path)
    print(f"[OK] Loaded rows: {len(df)}")

    summary = make_reproducibility_summary(df)
    save_reproducibility_summary(summary, output_path)

    plot_cv(
        summary=summary,
        metric_cv_col="iops_cv",
        ylabel="IOPS CV",
        title="QD Sweep Reproducibility - IOPS CV",
        output_path=plot_dir / "qd_sweep_iops_cv.png",
    )

    plot_cv(
        summary=summary,
        metric_cv_col="bandwidth_mib_s_cv",
        ylabel="Bandwidth CV",
        title="QD Sweep Reproducibility - Bandwidth CV",
        output_path=plot_dir / "qd_sweep_bandwidth_cv.png",
    )

    plot_cv(
        summary=summary,
        metric_cv_col="clat_p99_us_cv",
        ylabel="p99 Latency CV",
        title="QD Sweep Reproducibility - p99 Latency CV",
        output_path=plot_dir / "qd_sweep_p99_cv.png",
    )

    plot_run_to_run(
        df=df,
        metric="clat_p99_us",
        ylabel="p99 Completion Latency (us)",
        title="QD Sweep Run-to-Run Variation - p99 Latency",
        output_path=plot_dir / "qd_sweep_p99_run_to_run.png",
    )

    print_summary(summary)

    print()
    print("[DONE] QD sweep reproducibility analysis completed.")


if __name__ == "__main__":
    main()