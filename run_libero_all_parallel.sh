#!/usr/bin/env bash
set -euo pipefail

# Sequentially evaluate multiple LIBERO suites with eval/eval_parallel.py.
# Assumes the policy server is already running (host/port below).

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

is_er_suite() {
  case "$1" in
    er_spatial|er_sequential|er_goal|er_object) return 0 ;;
    *) return 1 ;;
  esac
}

# Keep defaults aligned with run_libero_parallel.sh (can be overridden via env).
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
NUM_TRIALS_PER_TASK="${NUM_TRIALS_PER_TASK:-20}"
NUM_WORKERS="${NUM_WORKERS:-50}"

# Base output directory; each suite writes to a separate subfolder.
VIDEO_OUT_BASE="${VIDEO_OUT_BASE:-outputs/pi05_libero_vla_only_mix120/pi05_libero_vla_only_mix120_20260115_180102/checkpoint-25500/attention_mask/}"
# Optional suffix appended to each suite folder (e.g., "-2" to match an existing run tag).
RUN_TAG="${RUN_TAG:--cot-reasoning}"

# Default suites (order matters).
# SUITES_DEFAULT=("libero_10" "libero_90" "libero_object" "libero_goal" "libero_spatial")
SUITES_DEFAULT=("er_spatial" "er_object" "er_goal" "er_sequential")

suite_to_dir() {
  local suite="$1"
  case "$suite" in
    libero_10) echo "libero-10" ;;
    libero_90) echo "libero-90" ;;
    libero_object) echo "libero-object" ;;
    libero_goal) echo "libero-goal" ;;
    libero_spatial) echo "libero-spatial" ;;
    er_spatial) echo "er-spatial" ;;
    er_object) echo "er-object" ;;
    er_goal) echo "er-goal" ;;
    er_sequential) echo "er-sequential" ;;
    *) echo "$suite" ;;
  esac
}

source eval/.venv/bin/activate

for suite in "${SUITES_DEFAULT[@]}"; do
  out_dir="${VIDEO_OUT_BASE}/$(suite_to_dir "$suite")${RUN_TAG}"
  mkdir -p "$out_dir"

  echo "==> Evaluating ${suite} -> ${out_dir}"
  extra_env=()
  if is_er_suite "$suite"; then
    cfg_dir="$PWD/.libero_cfg"
    mkdir -p "$cfg_dir"
    cat >"$cfg_dir/config.yaml" <<EOF
benchmark_root: $PWD/libero/libero
bddl_files: $PWD/libero/libero/bddl_files
init_states: $PWD/libero/libero/init_files
datasets: $PWD/libero/../datasets
assets: $PWD/libero/libero/assets
EOF
    extra_env=(LIBERO_CONFIG_PATH="$cfg_dir")
  fi

  env -u LD_LIBRARY_PATH -u PYTHONPATH PYTHONNOUSERSITE=1 \
    "${extra_env[@]}" \
    PYTHONPATH="$PWD/eval:${PYTHONPATH:-}" \
    LD_LIBRARY_PATH=/usr/local/nvidia/lib64:/usr/local/nvidia/lib:/usr/lib/x86_64-linux-gnu \
    MUJOCO_GL=osmesa \
      python eval/eval_parallel.py \
        --args.task-suite-name "$suite" \
        --args.host "$HOST" \
        --args.port "$PORT" \
        --args.num-trials-per-task "$NUM_TRIALS_PER_TASK" \
        --args.video-out-path "$out_dir" \
        --args.num-workers "$NUM_WORKERS"
done

echo "All suites finished."
