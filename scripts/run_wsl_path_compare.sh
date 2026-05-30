#!/usr/bin/env bash
#
# run_wsl_path_compare.sh
#
# Purpose:
#   Compare small file-based fio results between:
#     1. WSL native ext4 path under $HOME
#     2. Windows-mounted D: path under /mnt/d
#
# Safety:
#   This script uses regular files only.
#   It never targets raw block devices such as /dev/sdX or /dev/nvmeXnY.
#
# Usage from Windows PowerShell:
#   wsl -d Ubuntu -- bash /mnt/d/ssd_lab/scripts/run_wsl_path_compare.sh

set -euo pipefail

BASE_MOUNT="${SSD_LAB_BASE_MOUNT:-/mnt/d/ssd_lab}"
RESULT_DIR="${SSD_LAB_WSL_RESULT_DIR:-$BASE_MOUNT/results/wsl_path_compare}"
MNTD_WORK_DIR="${SSD_LAB_WSL_MNTD_WORK_DIR:-$BASE_MOUNT/results/wsl_path_compare_files}"
EXT4_WORK_DIR="${SSD_LAB_WSL_EXT4_WORK_DIR:-$HOME/ssd_lab_wsl_path_compare}"

SIZE="${SSD_LAB_WSL_TEST_SIZE:-512M}"
RUNTIME="${SSD_LAB_WSL_RUNTIME:-15}"
RUNS="${SSD_LAB_WSL_RUNS:-3}"
BS="${SSD_LAB_WSL_BS:-4k}"
IODEPTH="${SSD_LAB_WSL_IODEPTH:-16}"
DIRECT="${SSD_LAB_WSL_DIRECT:-0}"

mkdir -p "$RESULT_DIR" "$MNTD_WORK_DIR" "$EXT4_WORK_DIR"

echo "=== WSL path comparison fio run ==="
echo "BASE_MOUNT    : $BASE_MOUNT"
echo "RESULT_DIR    : $RESULT_DIR"
echo "EXT4_WORK_DIR : $EXT4_WORK_DIR"
echo "MNTD_WORK_DIR : $MNTD_WORK_DIR"
echo "SIZE          : $SIZE"
echo "RUNTIME       : $RUNTIME"
echo "RUNS          : $RUNS"
echo "BS            : $BS"
echo "IODEPTH       : $IODEPTH"
echo "DIRECT        : $DIRECT"
echo

command -v fio >/dev/null

run_fio() {
  local path_mode="$1"
  local work_dir="$2"
  local workload="$3"
  local rw="$4"
  local run="$5"
  local test_file="$work_dir/fio_testfile_wsl_path_compare"
  local out_file="$RESULT_DIR/${workload}_path_${path_mode}_run${run}.json"

  echo "Running: workload=$workload path_mode=$path_mode run=$run"
  echo "Output : $out_file"

  fio \
    --name="$workload" \
    --filename="$test_file" \
    --rw="$rw" \
    --bs="$BS" \
    --size="$SIZE" \
    --iodepth="$IODEPTH" \
    --numjobs=1 \
    --direct="$DIRECT" \
    --time_based \
    --runtime="$RUNTIME" \
    --group_reporting \
    --output-format=json \
    --output="$out_file"
}

prefill_path() {
  local path_mode="$1"
  local work_dir="$2"
  local test_file="$work_dir/fio_testfile_wsl_path_compare"
  local out_file="$RESULT_DIR/prefill_path_${path_mode}.json"

  echo "Prefill: path_mode=$path_mode"

  fio \
    --name="prefill_${path_mode}" \
    --filename="$test_file" \
    --rw=write \
    --bs=1M \
    --size="$SIZE" \
    --iodepth=1 \
    --numjobs=1 \
    --direct=0 \
    --output-format=json \
    --output="$out_file"
}

prefill_path "wsl_ext4" "$EXT4_WORK_DIR"
prefill_path "mnt_d" "$MNTD_WORK_DIR"

for path_entry in "wsl_ext4:$EXT4_WORK_DIR" "mnt_d:$MNTD_WORK_DIR"; do
  path_mode="${path_entry%%:*}"
  work_dir="${path_entry#*:}"

  for workload_entry in "rand_read:randread" "rand_write:randwrite"; do
    workload="${workload_entry%%:*}"
    rw="${workload_entry#*:}"

    for run in $(seq 1 "$RUNS"); do
      run_fio "$path_mode" "$work_dir" "$workload" "$rw" "$run"
      echo
    done
  done
done

echo "[DONE] WSL path comparison fio runs completed."
