source eval/.venv/bin/activate

env -u LD_LIBRARY_PATH -u PYTHONPATH PYTHONNOUSERSITE=1 \
    PYTHONPATH="$PWD/eval:$PYTHONPATH" \
    LD_LIBRARY_PATH=/usr/local/nvidia/lib64:/usr/local/nvidia/lib:/usr/lib/x86_64-linux-gnu \
    MUJOCO_GL=osmesa \
	    python eval/eval_parallel.py \
	        --args.task-suite-name libero_goal \
	        --args.host 127.0.0.1 \
	        --args.port 8001 \
	        --args.num-trials-per-task 10 \
	        --args.video-out-path output/pi05_libero_cotraining_ki_20260120_160333/checkpoint-23000/libero-goal/ \
			--args.num-workers 50 
	        # --args.enable_gt_segmentation \
	        # --args.replan-steps 2 \