# Plot Interpretation Notes

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
