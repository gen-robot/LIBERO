source eval/.venv/bin/activate

env -u LD_LIBRARY_PATH -u PYTHONPATH PYTHONNOUSERSITE=1 \
    PYTHONPATH="$PWD/eval:$PYTHONPATH" \
    LD_LIBRARY_PATH=/usr/local/nvidia/lib64:/usr/local/nvidia/lib:/usr/lib/x86_64-linux-gnu \
    MUJOCO_GL=osmesa \
    python eval/eval_parallel.py \
        --args.task-suite-name libero_goal \
        --args.host localhost \
        --args.port 7005 \
        --args.num-workers 10 \
        --args.video-out-path pi05_libero_vla_subtask_bbox_cot_ki_20260118_020941/checkpoint-30000/libero_goal/no_reasoning \
        --args.num-trials-per-task 10