source eval/.venv/bin/activate

# Use a repo-local LIBERO config so `get_libero_path("init_states")` points to this checkout.
# This avoids accidentally reading paths from ~/.libero that may reference a different checkout.

export LIBERO_CONFIG_PATH="$PWD/.libero_cfg"
mkdir -p "$LIBERO_CONFIG_PATH"
cat >"$LIBERO_CONFIG_PATH/config.yaml" <<EOF
benchmark_root: $PWD/libero/libero
bddl_files: $PWD/libero/libero/bddl_files
init_states: $PWD/libero/libero/init_files
datasets: $PWD/libero/../datasets
assets: $PWD/libero/libero/assets
EOF

env -u LD_LIBRARY_PATH -u PYTHONPATH PYTHONNOUSERSITE=1 \
    PYTHONPATH="$PWD/eval:$PYTHONPATH" \
    LD_LIBRARY_PATH=/usr/local/nvidia/lib64:/usr/local/nvidia/lib:/usr/lib/x86_64-linux-gnu \
    MUJOCO_GL=osmesa \
	    python eval/eval_parallel.py \
	        --args.task-suite-name libero_goal \
	        --args.host 127.0.0.1 \
	        --args.port 8000 \
	        --args.num-trials-per-task 20 \
	        --args.video-out-path data/libero/videos-debug \
			--args.num-workers 50 \
	        # --args.enable_gt_segmentation \
	        # --args.replan-steps 2 \
