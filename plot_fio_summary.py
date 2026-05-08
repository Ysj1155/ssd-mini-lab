"""
plot_fio_summary.py

Purpose:
    Read fio_summary.csv and generate validation-oriented baseline plots.

Default input:
    D:\\ssd_lab\\results\\fio_summary.csv

Default output directory:
    D:\\ssd_lab\\results\\plots

Behavior:
    Existing plot files with the same names are overwritten.

Usage:
    PowerShell:
        cd D:\\ssd_lab
        python .\\plot_fio_summary.py
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


WORKLOAD_ORDER = ["seq_read", "seq_write", "rand_read", "rand_write"]
RANDOM_WORKLOADS = ["rand_read", "rand_write"]
SEQUENTIAL_WORKLOADS = ["seq_read", "seq_write"]


def load_summary(csv_path: Path) -> pd.DataFrame:
    """
    Load fio summary CSV and normalize numeric columns.
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    df = pd.read_csv(csv_path)

    required_columns = [
        "workload",
        "run",
        "bandwidth_mib_s",
        "iops",
        "clat_mean_us",
        "clat_p99_us",
    ]

    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns in CSV: {missing}")

    numeric_columns = [
        "run",
        "bandwidth_mib_s",
        "iops",
        "clat_mean_us",
        "clat_p95_us",
        "clat_p99_us",
        "runtime_sec",
    ]

    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["workload"] = pd.Categorical(
        df["workload"],
        categories=WORKLOAD_ORDER,
        ordered=True,
    )

    df = df.sort_values(["workload", "run"]).reset_index(drop=True)
    return df


def make_output_dir(output_dir: Path) -> None:
    """
    Create output directory if it does not exist.
    """
    output_dir.mkdir(parents=True, exist_ok=True)


def filter_workloads(df: pd.DataFrame, workloads: list[str]) -> pd.DataFrame:
    """
    Return rows for selected workloads while preserving order.
    """
    filtered = df[df["workload"].astype(str).isin(workloads)].copy()
    filtered["workload"] = pd.Categorical(
        filtered["workload"].astype(str),
        categories=workloads,
        ordered=True,
    )
    return filtered.sort_values(["workload", "run"]).reset_index(drop=True)


def save_bar_with_points(
    df: pd.DataFrame,
    metric: str,
    ylabel: str,
    title: str,
    output_path: Path,
    workload_order: list[str],
    log_y: bool = False,
) -> None:
    """
    Draw average bar chart with individual run points.

    Bar:
        Mean value across repeated runs.

    Dots:
        Individual run values.

    Error bar:
        Standard deviation across repeated runs.
    """
    grouped = df.groupby("workload", observed=False)[metric]
    mean_values = grouped.mean().reindex(workload_order)
    std_values = grouped.std().reindex(workload_order)

    x_positions = list(range(len(workload_order)))

    plt.figure(figsize=(10, 6))
    plt.bar(x_positions, mean_values, yerr=std_values, capsize=5)

    for idx, workload in enumerate(workload_order):
        values = df.loc[df["workload"].astype(str) == workload, metric].dropna().tolist()
        x_jitter = [idx] * len(values)
        plt.scatter(x_jitter, values, marker="o")

    if log_y:
        plt.yscale("log")

    plt.xticks(x_positions, workload_order, rotation=20)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.grid(axis="y", linestyle="--", alpha=0.4)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def save_grouped_latency_mean_vs_p99(
    df: pd.DataFrame,
    output_path: Path,
    workload_order: list[str],
    title: str,
    log_y: bool = False,
) -> None:
    """
    Draw mean latency vs p99 latency comparison by workload.

    log_y=True is recommended when sequential and random workloads
    are shown together because their block sizes are different.
    """
    grouped = (
        df.groupby("workload", observed=False)[["clat_mean_us", "clat_p99_us"]]
        .mean()
        .reindex(workload_order)
    )

    x_positions = list(range(len(workload_order)))
    width = 0.35

    mean_x = [x - width / 2 for x in x_positions]
    p99_x = [x + width / 2 for x in x_positions]

    plt.figure(figsize=(10, 6))
    plt.bar(mean_x, grouped["clat_mean_us"], width=width, label="mean latency")
    plt.bar(p99_x, grouped["clat_p99_us"], width=width, label="p99 latency")

    if log_y:
        plt.yscale("log")

    plt.xticks(x_positions, workload_order, rotation=20)
    plt.ylabel("Latency (us)")
    plt.title(title)
    plt.legend()
    plt.grid(axis="y", linestyle="--", alpha=0.4)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def save_run_to_run_variation(
    df: pd.DataFrame,
    metric: str,
    ylabel: str,
    title: str,
    output_path: Path,
    workload_order: list[str],
    log_y: bool = False,
) -> None:
    """
    Draw run-to-run variation for a selected metric.
    """
    plt.figure(figsize=(10, 6))

    for workload in workload_order:
        subset = df[df["workload"].astype(str) == workload].sort_values("run")
        if subset.empty:
            continue

        plt.plot(
            subset["run"],
            subset[metric],
            marker="o",
            label=workload,
        )

    if log_y:
        plt.yscale("log")

    plt.xlabel("Run")
    plt.ylabel(ylabel)
    plt.title(title)

    runs = sorted(df["run"].dropna().unique())
    if runs:
        plt.xticks(runs)

    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.4)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def save_scatter_iops_vs_p99(
    df: pd.DataFrame,
    output_path: Path,
) -> None:
    """
    Draw IOPS vs p99 latency scatter.

    This plot is useful for random workloads because IOPS and latency
    are both meaningful under 4K random access.
    """
    random_df = filter_workloads(df, RANDOM_WORKLOADS)

    plt.figure(figsize=(10, 6))

    for workload in RANDOM_WORKLOADS:
        subset = random_df[random_df["workload"].astype(str) == workload]
        if subset.empty:
            continue

        plt.scatter(
            subset["iops"],
            subset["clat_p99_us"],
            label=workload,
        )

        for _, row in subset.iterrows():
            plt.annotate(
                f"run{int(row['run'])}",
                (row["iops"], row["clat_p99_us"]),
                textcoords="offset points",
                xytext=(5, 5),
                fontsize=8,
            )

    plt.xlabel("IOPS")
    plt.ylabel("p99 Latency (us)")
    plt.title("Random Workload: IOPS vs p99 Latency")
    plt.grid(True, linestyle="--", alpha=0.4)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def save_cv_summary(df: pd.DataFrame, output_path: Path) -> pd.DataFrame:
    """
    Calculate coefficient of variation for key metrics and save as CSV.

    CV = standard deviation / mean

    Lower CV means repeated measurements are more stable.
    """
    metrics = ["bandwidth_mib_s", "iops", "clat_mean_us", "clat_p99_us"]

    rows = []

    for workload in WORKLOAD_ORDER:
        subset = df[df["workload"].astype(str) == workload]

        row = {"workload": workload}

        for metric in metrics:
            mean_value = subset[metric].mean()
            std_value = subset[metric].std()

            row[f"{metric}_mean"] = mean_value
            row[f"{metric}_std"] = std_value

            if pd.notna(mean_value) and mean_value != 0:
                row[f"{metric}_cv"] = std_value / mean_value
            else:
                row[f"{metric}_cv"] = None

        rows.append(row)

    cv_df = pd.DataFrame(rows)
    cv_df.to_csv(output_path, index=False, encoding="utf-8-sig")
    return cv_df


def save_readme_note(output_path: Path) -> None:
    """
    Save a short note explaining how to interpret the generated plots.
    """
    note = """# Plot Interpretation Notes

## Important interpretation rule

The baseline contains two different block-size families:

- Sequential workload: 1M block size
- Random workload: 4K block size

Therefore, IOPS and latency should not be interpreted as direct apples-to-apples comparisons across all workloads.

## Recommended reading

### Bandwidth
Use `bandwidth_by_workload.png` to compare overall throughput tendency.

### IOPS
Use `random_iops_only.png` for the random 4K workload comparison.
The full IOPS plot is useful only as a rough overview because sequential 1M I/O naturally has much lower IOPS.

### Latency
Use log-scale latency plots when comparing all workloads together.
For detailed interpretation, prefer separate sequential/random latency plots.

### Repeatability
Use `cv_summary.csv` and run-to-run variation plots to discuss repeatability.
Lower CV means lower run-to-run variation.

## Validation-oriented caution

Do not overclaim root cause from this baseline alone.
This baseline can support observations such as:

- write workload showed higher tail latency than read workload
- repeated runs were stable or unstable under fixed conditions
- sequential and random workloads require different primary metrics

It cannot directly prove internal SSD causes such as garbage collection, SLC cache behavior, or thermal throttling without additional experiments.
"""
    output_path.write_text(note, encoding="utf-8")


def print_basic_summary(df: pd.DataFrame, cv_df: pd.DataFrame, output_dir: Path) -> None:
    """
    Print a terminal summary after plot generation.
    """
    print()
    print("=== fio plot summary ===")
    print(f"Rows loaded : {len(df)}")
    print(f"Output dir  : {output_dir}")
    print("Overwrite   : enabled by fixed output filenames")

    print()
    print("Average by workload:")
    avg = (
        df.groupby("workload", observed=False)[
            ["bandwidth_mib_s", "iops", "clat_mean_us", "clat_p99_us"]
        ]
        .mean()
        .reindex(WORKLOAD_ORDER)
    )
    print(avg.round(2).to_string())

    print()
    print("Coefficient of variation:")
    cv_cols = [
        "workload",
        "bandwidth_mib_s_cv",
        "iops_cv",
        "clat_mean_us_cv",
        "clat_p99_us_cv",
    ]
    print(cv_df[cv_cols].round(4).to_string(index=False))

    print()
    print("Generated or overwritten files:")
    for path in sorted(output_dir.glob("*")):
        print(f"- {path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate validation-oriented plots from fio_summary.csv."
    )

    parser.add_argument(
        "--input",
        type=str,
        default=r"D:\ssd_lab\results\fio_summary.csv",
        help=r"Input CSV path. Default: D:\ssd_lab\results\fio_summary.csv",
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default=r"D:\ssd_lab\results\plots",
        help=r"Output plot directory. Default: D:\ssd_lab\results\plots",
    )

    args = parser.parse_args()

    csv_path = Path(args.input)
    output_dir = Path(args.output_dir)

    make_output_dir(output_dir)

    df = load_summary(csv_path)

    random_df = filter_workloads(df, RANDOM_WORKLOADS)
    sequential_df = filter_workloads(df, SEQUENTIAL_WORKLOADS)

    # 1. Bandwidth plots
    save_bar_with_points(
        df=df,
        metric="bandwidth_mib_s",
        ylabel="Bandwidth (MiB/s)",
        title="Average Bandwidth by Workload",
        output_path=output_dir / "bandwidth_by_workload.png",
        workload_order=WORKLOAD_ORDER,
        log_y=False,
    )

    # 2. IOPS plots
    save_bar_with_points(
        df=df,
        metric="iops",
        ylabel="IOPS",
        title="Average IOPS by Workload",
        output_path=output_dir / "iops_by_workload.png",
        workload_order=WORKLOAD_ORDER,
        log_y=False,
    )

    save_bar_with_points(
        df=df,
        metric="iops",
        ylabel="IOPS - log scale",
        title="Average IOPS by Workload - Log Scale",
        output_path=output_dir / "iops_by_workload_log.png",
        workload_order=WORKLOAD_ORDER,
        log_y=True,
    )

    save_bar_with_points(
        df=random_df,
        metric="iops",
        ylabel="IOPS",
        title="Random 4K IOPS by Workload",
        output_path=output_dir / "random_iops_only.png",
        workload_order=RANDOM_WORKLOADS,
        log_y=False,
    )

    # 3. p99 latency plots
    save_bar_with_points(
        df=df,
        metric="clat_p99_us",
        ylabel="p99 Latency (us)",
        title="p99 Completion Latency by Workload",
        output_path=output_dir / "p99_latency_by_workload.png",
        workload_order=WORKLOAD_ORDER,
        log_y=False,
    )

    save_bar_with_points(
        df=df,
        metric="clat_p99_us",
        ylabel="p99 Latency (us) - log scale",
        title="p99 Completion Latency by Workload - Log Scale",
        output_path=output_dir / "p99_latency_by_workload_log.png",
        workload_order=WORKLOAD_ORDER,
        log_y=True,
    )

    save_bar_with_points(
        df=random_df,
        metric="clat_p99_us",
        ylabel="p99 Latency (us)",
        title="Random 4K p99 Completion Latency",
        output_path=output_dir / "random_p99_latency_only.png",
        workload_order=RANDOM_WORKLOADS,
        log_y=False,
    )

    save_bar_with_points(
        df=sequential_df,
        metric="clat_p99_us",
        ylabel="p99 Latency (us)",
        title="Sequential 1M p99 Completion Latency",
        output_path=output_dir / "sequential_p99_latency_only.png",
        workload_order=SEQUENTIAL_WORKLOADS,
        log_y=False,
    )

    # 4. Mean vs p99 latency plots
    save_grouped_latency_mean_vs_p99(
        df=df,
        output_path=output_dir / "mean_vs_p99_latency.png",
        workload_order=WORKLOAD_ORDER,
        title="Mean vs p99 Completion Latency by Workload",
        log_y=False,
    )

    save_grouped_latency_mean_vs_p99(
        df=df,
        output_path=output_dir / "mean_vs_p99_latency_log.png",
        workload_order=WORKLOAD_ORDER,
        title="Mean vs p99 Completion Latency by Workload - Log Scale",
        log_y=True,
    )

    save_grouped_latency_mean_vs_p99(
        df=random_df,
        output_path=output_dir / "random_mean_vs_p99_latency_only.png",
        workload_order=RANDOM_WORKLOADS,
        title="Random 4K Mean vs p99 Completion Latency",
        log_y=False,
    )

    save_grouped_latency_mean_vs_p99(
        df=sequential_df,
        output_path=output_dir / "sequential_mean_vs_p99_latency_only.png",
        workload_order=SEQUENTIAL_WORKLOADS,
        title="Sequential 1M Mean vs p99 Completion Latency",
        log_y=False,
    )

    # 5. Run-to-run variation plots
    save_run_to_run_variation(
        df=df,
        metric="clat_p99_us",
        ylabel="p99 Latency (us)",
        title="Run-to-Run p99 Latency Variation",
        output_path=output_dir / "p99_run_to_run_variation.png",
        workload_order=WORKLOAD_ORDER,
        log_y=False,
    )

    save_run_to_run_variation(
        df=df,
        metric="clat_p99_us",
        ylabel="p99 Latency (us) - log scale",
        title="Run-to-Run p99 Latency Variation - Log Scale",
        output_path=output_dir / "p99_run_to_run_variation_log.png",
        workload_order=WORKLOAD_ORDER,
        log_y=True,
    )

    save_run_to_run_variation(
        df=random_df,
        metric="clat_p99_us",
        ylabel="p99 Latency (us)",
        title="Random 4K Run-to-Run p99 Latency Variation",
        output_path=output_dir / "random_p99_run_to_run_variation_only.png",
        workload_order=RANDOM_WORKLOADS,
        log_y=False,
    )

    save_run_to_run_variation(
        df=sequential_df,
        metric="clat_p99_us",
        ylabel="p99 Latency (us)",
        title="Sequential 1M Run-to-Run p99 Latency Variation",
        output_path=output_dir / "sequential_p99_run_to_run_variation_only.png",
        workload_order=SEQUENTIAL_WORKLOADS,
        log_y=False,
    )

    # 6. Random workload relationship plot
    save_scatter_iops_vs_p99(
        df=df,
        output_path=output_dir / "random_iops_vs_p99_latency.png",
    )

    # 7. CV summary and plot interpretation note
    cv_df = save_cv_summary(
        df=df,
        output_path=output_dir / "cv_summary.csv",
    )

    save_readme_note(
        output_path=output_dir / "plot_interpretation_notes.md",
    )

    print_basic_summary(df, cv_df, output_dir)


if __name__ == "__main__":
    main()