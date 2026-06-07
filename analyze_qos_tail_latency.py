"""
analyze_qos_tail_latency.py

Purpose:
    Combine Stage 1 and WSL path comparison results into one QoS/tail-latency
    review table and a few focused plots.

Outputs:
    results/qos_tail_latency_summary.csv
    results/qos_tail_latency_plots/top_p99_latency.png
    results/qos_tail_latency_plots/top_p99_cv.png
    results/qos_tail_latency_plots/iops_vs_p99_latency.png

Usage:
    cd D:\\ssd_lab
    python .\\analyze_qos_tail_latency.py
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_CSV = BASE_DIR / "results" / "qos_tail_latency_summary.csv"
PLOT_DIR = BASE_DIR / "results" / "qos_tail_latency_plots"

BASELINE_CV = BASE_DIR / "results" / "plots" / "cv_summary.csv"
QD_REPRO = BASE_DIR / "results" / "qd_sweep_reproducibility.csv"
DIRECT_GROUPED = BASE_DIR / "results" / "direct_buffered_grouped.csv"
WSL_GROUPED = BASE_DIR / "results" / "wsl_path_compare_grouped.csv"


def as_float(value: Any) -> float | None:
    """Convert a value to float, returning None for missing/non-numeric values."""
    if pd.isna(value):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def add_row(
    rows: list[dict[str, Any]],
    *,
    experiment: str,
    condition: str,
    workload: str,
    run_count: int | None,
    bandwidth_mib_s_mean: Any,
    bandwidth_mib_s_cv: Any,
    iops_mean: Any,
    iops_cv: Any,
    clat_p99_us_mean: Any,
    clat_p99_us_cv: Any,
    clat_p999_us_mean: Any = None,
    clat_p999_us_cv: Any = None,
) -> None:
    """Append one normalized QoS summary row."""
    rows.append(
        {
            "experiment": experiment,
            "condition": condition,
            "workload": workload,
            "run_count": run_count,
            "bandwidth_mib_s_mean": as_float(bandwidth_mib_s_mean),
            "bandwidth_mib_s_cv": as_float(bandwidth_mib_s_cv),
            "iops_mean": as_float(iops_mean),
            "iops_cv": as_float(iops_cv),
            "clat_p99_us_mean": as_float(clat_p99_us_mean),
            "clat_p99_us_cv": as_float(clat_p99_us_cv),
            "clat_p999_us_mean": as_float(clat_p999_us_mean),
            "clat_p999_us_cv": as_float(clat_p999_us_cv),
        }
    )


def load_baseline(rows: list[dict[str, Any]]) -> None:
    """Load baseline CV summary."""
    if not BASELINE_CV.exists():
        print(f"[WARN] Missing baseline CV file: {BASELINE_CV}")
        return

    df = pd.read_csv(BASELINE_CV)
    for _, row in df.iterrows():
        add_row(
            rows,
            experiment="baseline",
            condition="baseline",
            workload=row["workload"],
            run_count=3,
            bandwidth_mib_s_mean=row.get("bandwidth_mib_s_mean"),
            bandwidth_mib_s_cv=row.get("bandwidth_mib_s_cv"),
            iops_mean=row.get("iops_mean"),
            iops_cv=row.get("iops_cv"),
            clat_p99_us_mean=row.get("clat_p99_us_mean"),
            clat_p99_us_cv=row.get("clat_p99_us_cv"),
        )


def load_qd_repro(rows: list[dict[str, Any]]) -> None:
    """Load QD sweep reproducibility summary."""
    if not QD_REPRO.exists():
        print(f"[WARN] Missing QD reproducibility file: {QD_REPRO}")
        return

    df = pd.read_csv(QD_REPRO)
    for _, row in df.iterrows():
        qd = int(row["qd_from_filename"])
        add_row(
            rows,
            experiment="qd_sweep",
            condition=f"QD{qd}",
            workload=row["workload"],
            run_count=int(row["run_count"]),
            bandwidth_mib_s_mean=row.get("bandwidth_mib_s_mean"),
            bandwidth_mib_s_cv=row.get("bandwidth_mib_s_cv"),
            iops_mean=row.get("iops_mean"),
            iops_cv=row.get("iops_cv"),
            clat_p99_us_mean=row.get("clat_p99_us_mean"),
            clat_p99_us_cv=row.get("clat_p99_us_cv"),
            clat_p999_us_mean=row.get("clat_p999_us_mean"),
            clat_p999_us_cv=row.get("clat_p999_us_cv"),
        )


def load_direct_buffered(rows: list[dict[str, Any]]) -> None:
    """Load direct/buffered grouped summary."""
    if not DIRECT_GROUPED.exists():
        print(f"[WARN] Missing direct/buffered grouped file: {DIRECT_GROUPED}")
        return

    df = pd.read_csv(DIRECT_GROUPED)
    for _, row in df.iterrows():
        add_row(
            rows,
            experiment="direct_buffered",
            condition=row["mode_label"],
            workload=row["workload"],
            run_count=int(row["run_count"]),
            bandwidth_mib_s_mean=row.get("bandwidth_mib_s_mean"),
            bandwidth_mib_s_cv=row.get("bandwidth_mib_s_cv"),
            iops_mean=row.get("iops_mean"),
            iops_cv=row.get("iops_cv"),
            clat_p99_us_mean=row.get("clat_p99_us_mean"),
            clat_p99_us_cv=row.get("clat_p99_us_cv"),
            clat_p999_us_mean=row.get("clat_p999_us_mean"),
            clat_p999_us_cv=row.get("clat_p999_us_cv"),
        )


def load_wsl_path(rows: list[dict[str, Any]]) -> None:
    """Load WSL path comparison grouped summary."""
    if not WSL_GROUPED.exists():
        print(f"[WARN] Missing WSL path grouped file: {WSL_GROUPED}")
        return

    df = pd.read_csv(WSL_GROUPED)
    for _, row in df.iterrows():
        add_row(
            rows,
            experiment="wsl_path_compare",
            condition=row["path_label"],
            workload=row["workload"],
            run_count=int(row["run_count"]),
            bandwidth_mib_s_mean=row.get("bandwidth_mib_s_mean"),
            bandwidth_mib_s_cv=row.get("bandwidth_mib_s_cv"),
            iops_mean=row.get("iops_mean"),
            iops_cv=row.get("iops_cv"),
            clat_p99_us_mean=row.get("clat_p99_us_mean"),
            clat_p99_us_cv=row.get("clat_p99_us_cv"),
            clat_p999_us_mean=row.get("clat_p999_us_mean"),
            clat_p999_us_cv=row.get("clat_p999_us_cv"),
        )


def make_label(row: pd.Series) -> str:
    """Build a compact plot label."""
    return f"{row['experiment']} | {row['workload']} | {row['condition']}"


def plot_top_bar(
    df: pd.DataFrame,
    metric: str,
    title: str,
    xlabel: str,
    output_path: Path,
    top_n: int = 12,
) -> None:
    """Plot top-N rows by a metric as horizontal bars."""
    part = df.dropna(subset=[metric]).sort_values(metric, ascending=False).head(top_n)
    part = part.iloc[::-1].copy()

    fig, ax = plt.subplots(figsize=(10, 7))
    labels = [make_label(row) for _, row in part.iterrows()]
    ax.barh(labels, part[metric], color="#345995")
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.grid(True, axis="x", alpha=0.3)
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    print(f"[OK] Saved plot: {output_path}")


def plot_iops_vs_p99(df: pd.DataFrame, output_path: Path) -> None:
    """Plot IOPS mean vs p99 latency mean."""
    part = df.dropna(subset=["iops_mean", "clat_p99_us_mean"]).copy()

    fig, ax = plt.subplots(figsize=(9, 6))
    for experiment, group in part.groupby("experiment"):
        ax.scatter(group["iops_mean"], group["clat_p99_us_mean"], label=experiment, s=60)

    ax.set_title("IOPS vs p99 Completion Latency")
    ax.set_xlabel("Mean IOPS")
    ax.set_ylabel("Mean p99 Completion Latency (us)")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    print(f"[OK] Saved plot: {output_path}")


def print_summary(df: pd.DataFrame) -> None:
    """Print compact terminal summary."""
    print()
    print("=== Highest p99 latency ===")
    cols = ["experiment", "condition", "workload", "clat_p99_us_mean", "clat_p99_us_cv"]
    print(
        df.dropna(subset=["clat_p99_us_mean"])
        .sort_values("clat_p99_us_mean", ascending=False)
        .head(8)[cols]
        .to_string(index=False, formatters={
            "clat_p99_us_mean": "{:.2f}".format,
            "clat_p99_us_cv": "{:.3f}".format,
        })
    )

    print()
    print("=== Highest p99 CV ===")
    print(
        df.dropna(subset=["clat_p99_us_cv"])
        .sort_values("clat_p99_us_cv", ascending=False)
        .head(8)[cols]
        .to_string(index=False, formatters={
            "clat_p99_us_mean": "{:.2f}".format,
            "clat_p99_us_cv": "{:.3f}".format,
        })
    )


def main() -> None:
    rows: list[dict[str, Any]] = []

    load_baseline(rows)
    load_qd_repro(rows)
    load_direct_buffered(rows)
    load_wsl_path(rows)

    if not rows:
        raise ValueError("No QoS rows were loaded.")

    df = pd.DataFrame(rows)
    df = df.sort_values(["experiment", "workload", "condition"]).reset_index(drop=True)

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print(f"[OK] Saved summary: {OUTPUT_CSV}")

    plot_top_bar(
        df,
        metric="clat_p99_us_mean",
        title="Top p99 Completion Latency Conditions",
        xlabel="Mean p99 Completion Latency (us)",
        output_path=PLOT_DIR / "top_p99_latency.png",
    )
    plot_top_bar(
        df,
        metric="clat_p99_us_cv",
        title="Top p99 Latency CV Conditions",
        xlabel="p99 Latency CV",
        output_path=PLOT_DIR / "top_p99_cv.png",
    )
    plot_iops_vs_p99(df, PLOT_DIR / "iops_vs_p99_latency.png")

    print_summary(df)


if __name__ == "__main__":
    main()
