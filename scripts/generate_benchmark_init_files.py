#!/usr/bin/env python3
"""
Generate benchmark-compatible init-state files (*.pruned_init) for LIBERO suites.

This script generates the same *type* of init-state artifacts that the benchmark
loader expects:

  get_libero_path("init_states")/<suite>/<task_name>.pruned_init

Each file is saved via `torch.save` as a NumPy array of shape (N, state_dim),
where each row is a flattened MuJoCo state returned by `env.get_sim_state()`.

Notes
-----
- This does NOT generate goal init files (those live under goal_bddl_files/goal_files).
- For "strict benchmark evaluation", your BDDL files must exist at:
    get_libero_path("bddl_files")/<suite>/<task_name>.bddl
  where <task_name> matches the benchmark suite task map.

Example
-------
  source eval/.venv/bin/activate
  export MUJOCO_GL=osmesa
  python scripts/generate_benchmark_init_files.py --suite libero_object --num-states 50
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Iterable, Optional

import numpy as np
import torch


LIBERO_DUMMY_ACTION = [0.0] * 6 + [-1.0]


def _iter_suite_names() -> list[str]:
    from libero.libero import benchmark

    return sorted(benchmark.get_benchmark_dict().keys())


def _get_benchmark_instance(suite_name: str, task_order_index: int):
    from libero.libero import benchmark

    benchmark_dict = benchmark.get_benchmark_dict()
    if suite_name not in benchmark_dict:
        raise SystemExit(
            f"[error] unknown suite '{suite_name}'. Available: {', '.join(sorted(benchmark_dict.keys()))}"
        )
    return benchmark_dict[suite_name](task_order_index=task_order_index)


def _default_paths() -> tuple[Path, Path]:
    from libero.libero import get_libero_path

    bddl_root = Path(get_libero_path("bddl_files"))
    init_root = Path(get_libero_path("init_states"))
    return bddl_root, init_root


def _ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _maybe_skip_existing(path: Path, overwrite: bool) -> bool:
    if not path.exists():
        return False
    if overwrite:
        return False
    return True


def _stack_states(states: list[np.ndarray]) -> np.ndarray:
    if not states:
        raise ValueError("no states generated")
    first_shape = states[0].shape
    for i, s in enumerate(states):
        if s.shape != first_shape:
            raise ValueError(f"inconsistent state shapes: states[0]={first_shape}, states[{i}]={s.shape}")
    return np.stack(states, axis=0)


def generate_init_states_for_bddl(
    bddl_file: Path,
    num_states: int,
    base_seed: int,
    seed_stride: int,
    settle_steps: int,
    camera_resolution: int,
) -> np.ndarray:
    from libero.libero.envs import OffScreenRenderEnv

    env = OffScreenRenderEnv(
        bddl_file_name=str(bddl_file),
        camera_heights=camera_resolution,
        camera_widths=camera_resolution,
    )
    try:
        states: list[np.ndarray] = []
        for i in range(num_states):
            seed = base_seed + i * seed_stride
            env.seed(seed)
            env.reset()
            for _ in range(settle_steps):
                env.step(LIBERO_DUMMY_ACTION)
            states.append(env.get_sim_state())
        return _stack_states(states)
    finally:
        env.close()


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate benchmark init-state files (*.pruned_init) under init_states/<suite>/"
    )
    parser.add_argument("--suite", type=str, required=True, help="Suite name (e.g., libero_10, er_object)")
    parser.add_argument(
        "--task-order-index",
        type=int,
        default=0,
        help="Benchmark task order index (should match evaluation). Default: 0",
    )
    parser.add_argument("--num-states", type=int, default=50, help="Number of init states per task")
    parser.add_argument(
        "--base-seed",
        type=int,
        default=42,
        help="Base seed used for env.seed() (per-task offset is added). Default: 42",
    )
    parser.add_argument(
        "--task-seed-stride",
        type=int,
        default=100_000,
        help="Seed offset between tasks (task_id * stride). Default: 100000",
    )
    parser.add_argument(
        "--seed-stride",
        type=int,
        default=100,
        help="Seed offset between states within a task. Default: 100",
    )
    parser.add_argument(
        "--settle-steps",
        type=int,
        default=10,
        help="Number of dummy env.step() calls after reset. Default: 10",
    )
    parser.add_argument(
        "--camera-resolution",
        type=int,
        default=64,
        help="Offscreen render resolution (not critical for state). Default: 64",
    )
    parser.add_argument(
        "--output-root",
        type=str,
        default=None,
        help="Override output root directory for init files (default: get_libero_path('init_states'))",
    )
    parser.add_argument(
        "--bddl-root",
        type=str,
        default=None,
        help="Override BDDL root directory (default: get_libero_path('bddl_files'))",
    )
    parser.add_argument(
        "--only-task-ids",
        type=str,
        nargs="*",
        default=None,
        help="Only generate for these benchmark task indices (0-based), e.g. --only-task-ids 0 3 7",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing *.pruned_init files instead of skipping",
    )
    parser.add_argument(
        "--skip-missing-bddl",
        action="store_true",
        help="Skip tasks whose BDDL file is missing (otherwise error)",
    )

    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.suite not in _iter_suite_names():
        raise SystemExit(
            f"[error] unknown suite '{args.suite}'. Available: {', '.join(_iter_suite_names())}"
        )

    bddl_root_default, init_root_default = _default_paths()
    bddl_root = Path(args.bddl_root) if args.bddl_root is not None else bddl_root_default
    init_root = Path(args.output_root) if args.output_root is not None else init_root_default

    suite = _get_benchmark_instance(args.suite, task_order_index=args.task_order_index)
    num_tasks = suite.get_num_tasks()

    only_task_ids: Optional[set[int]] = None
    if args.only_task_ids is not None and len(args.only_task_ids) > 0:
        try:
            only_task_ids = {int(x) for x in args.only_task_ids}
        except ValueError as e:
            raise SystemExit(f"[error] invalid --only-task-ids value: {e}")

    print(f"[info] suite={args.suite} task_order_index={args.task_order_index} num_tasks={num_tasks}")
    print(f"[info] bddl_root={bddl_root}")
    print(f"[info] init_output_root={init_root}")

    missing_bddl: list[Path] = []

    for task_id in range(num_tasks):
        if only_task_ids is not None and task_id not in only_task_ids:
            continue

        task = suite.get_task(task_id)
        bddl_path = bddl_root / task.problem_folder / task.bddl_file
        out_path = init_root / task.problem_folder / task.init_states_file

        if _maybe_skip_existing(out_path, overwrite=args.overwrite):
            print(f"[skip] task_id={task_id:02d} exists: {out_path}")
            continue

        if not bddl_path.exists():
            missing_bddl.append(bddl_path)
            msg = f"[missing] task_id={task_id:02d} bddl not found: {bddl_path}"
            if args.skip_missing_bddl:
                print(msg)
                continue
            raise SystemExit(
                msg
                + "\n"
                + "For strict benchmark evaluation, ensure BDDL files exist with names matching the benchmark task map."
            )

        print(f"[gen] task_id={task_id:02d} {task.name}")
        _ensure_parent_dir(out_path)

        task_base_seed = int(args.base_seed + task_id * args.task_seed_stride)
        init_states = generate_init_states_for_bddl(
            bddl_file=bddl_path,
            num_states=args.num_states,
            base_seed=task_base_seed,
            seed_stride=args.seed_stride,
            settle_steps=args.settle_steps,
            camera_resolution=args.camera_resolution,
        )
        torch.save(init_states, str(out_path))
        print(f"[ok] saved {init_states.shape} -> {out_path}")

    if missing_bddl and args.skip_missing_bddl:
        print(f"[warn] missing {len(missing_bddl)} BDDL files under: {bddl_root}")
        for p in missing_bddl[:20]:
            print(f"  - {p}")
        if len(missing_bddl) > 20:
            print(f"  ... and {len(missing_bddl) - 20} more")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

