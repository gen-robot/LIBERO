source eval/.venv/bin/activate

is_er_suite() {
  case "$1" in
    er_spatial|er_sequential|er_goal|er_object) return 0 ;;
    *) return 1 ;;
  esac
}

SUITE="${SUITE:-libero_goal}"
extra_env=()
if is_er_suite "$SUITE"; then
  # Use a repo-local LIBERO config so `get_libero_path("init_states")` points to this checkout.
  # This avoids accidentally reading paths from ~/.libero that may reference a different checkout.
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
    PYTHONPATH="$PWD/eval:$PYTHONPATH" \
    LD_LIBRARY_PATH=/usr/local/nvidia/lib64:/usr/local/nvidia/lib:/usr/lib/x86_64-linux-gnu \
    MUJOCO_GL=osmesa \
	    python eval/eval_parallel.py \
	        --args.task-suite-name "$SUITE" \
	        --args.host 127.0.0.1 \
	        --args.port 8000 \
	        --args.num-trials-per-task 20 \
	        --args.video-out-path data/libero/videos-debug \
			--args.num-workers 50 \
	        # --args.enable_gt_segmentation \
	        # --args.replan-steps 2 \
