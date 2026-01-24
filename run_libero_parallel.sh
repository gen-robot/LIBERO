source eval/.venv/bin/activate

env -u LD_LIBRARY_PATH -u PYTHONPATH PYTHONNOUSERSITE=1 \
    PYTHONPATH="$PWD/eval:$PYTHONPATH" \
    LD_LIBRARY_PATH=/usr/local/nvidia/lib64:/usr/local/nvidia/lib:/usr/lib/x86_64-linux-gnu \
    MUJOCO_GL=osmesa \
	    python eval/eval_parallel.py \
	        --args.task-suite-name libero_90 \
	        --args.host 127.0.0.1 \
	        --args.port 8000 \
	        --args.num-trials-per-task 20 \
	        --args.video-out-path outputs/pi05_libero_vla_subtask_cot_20260122_153122/checkpoint-15000/libero-90-2 \
			--args.num-workers 50
	        # --args.enable_gt_segmentation \
	        # --args.replan-steps 2 \