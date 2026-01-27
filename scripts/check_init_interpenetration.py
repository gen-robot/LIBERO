#!/usr/bin/env python3
"""
Check whether a specific task/init-state has initial interpenetration (penetration contacts).

This is intended for debugging "touch-and-fly" / physics explosion issues:
- Load a task BDDL and (optionally) a saved *.pruned_init state
- Set the state into the env (or sample by seed + reset)
- Inspect MuJoCo contacts; negative `contact.dist` indicates penetration

Examples
--------
# Check a saved benchmark init state (recommended: matches online eval artifacts)
python scripts/check_init_interpenetration.py --suite er_object --task-id 0 --init-idx 0

# Check a reset-sampled state (useful before generating init files)
python scripts/check_init_interpenetration.py --suite er_object --task-id 0 --seed 42 --settle-steps 10
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, Optional

import numpy as np
import torch

LIBERO_DUMMY_ACTION = [0.0] * 6 + [-1.0]


def torch_load_any(path: Path):
    try:
        return torch.load(str(path))
    except Exception:
        return torch.load(str(path), weights_only=False)


def _as_numpy_state(x) -> np.ndarray:
    if isinstance(x, np.ndarray):
        return x
    if torch.is_tensor(x):
        return x.detach().cpu().numpy()
    return np.asarray(x)


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


def _geom_label(sim, geom_id: int) -> str:
    name = sim.model.geom_id2name(geom_id)
    if name is None:
        name = f"geom{geom_id}"
    body_id = int(sim.model.geom_bodyid[geom_id])
    body_name = sim.model.body_id2name(body_id) or f"body{body_id}"
    return f"{body_name}/{name}"


def _looks_like_robot(label: str) -> bool:
    # Heuristic filter; adjust for your robot naming if needed.
    s = label.lower()
    return ("panda" in s) or ("robot0" in s) or ("gripper" in s) or ("mount" in s)


def summarize_contacts(sim, *, penetration_eps: float, max_rows: int, ignore_robot: bool) -> dict:
    ncon = int(sim.data.ncon)
    if ncon == 0:
        return {
            "ncon": 0,
            "min_dist": None,
            "penetration_count": 0,
            "strong_penetration_count": 0,
            "rows": [],
        }

    rows = []
    min_dist = float("inf")
    penetration_count = 0
    strong_penetration_count = 0

    for i in range(ncon):
        c = sim.data.contact[i]
        dist = float(c.dist)
        min_dist = min(min_dist, dist)

        g1 = int(c.geom1)
        g2 = int(c.geom2)
        l1 = _geom_label(sim, g1)
        l2 = _geom_label(sim, g2)

        if ignore_robot and (_looks_like_robot(l1) or _looks_like_robot(l2)):
            continue

        if dist < 0.0:
            penetration_count += 1
        if dist < -penetration_eps:
            strong_penetration_count += 1

        rows.append(
            {
                "i": i,
                "dist": dist,
                "geom1": l1,
                "geom2": l2,
            }
        )

    rows.sort(key=lambda r: r["dist"])  # most negative first
    return {
        "ncon": ncon,
        "min_dist": None if min_dist == float("inf") else min_dist,
        "penetration_count": penetration_count,
        "strong_penetration_count": strong_penetration_count,
        "rows": rows[:max_rows],
    }


def _print_report(title: str, report: dict) -> None:
    print(f"\n== {title} ==")
    print(
        f"ncon={report['ncon']} min_dist={report['min_dist']} "
        f"penetrations={report['penetration_count']} strong(<-eps)={report['strong_penetration_count']}"
    )
    if not report["rows"]:
        return
    print("worst contacts (most negative dist first):")
    for r in report["rows"]:
        print(f"  [{r['i']:03d}] dist={r['dist']:+.6f}  {r['geom1']}  <->  {r['geom2']}")


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Check initial interpenetration for a task/init-state.")
    parser.add_argument("--suite", type=str, required=True, help="Suite name (e.g., er_object, libero_10).")
    parser.add_argument(
        "--task-order-index",
        type=int,
        default=0,
        help="Benchmark task order index (should match evaluation). Default: 0",
    )
    parser.add_argument("--task-id", type=int, required=True, help="Task index within the suite (0-based).")
    parser.add_argument(
        "--init-idx",
        type=int,
        default=None,
        help="Index into the saved *.pruned_init states. If omitted, uses --seed path (reset-sampled state).",
    )
    parser.add_argument("--seed", type=int, default=42, help="Seed for reset-sampled state (when --init-idx is None).")
    parser.add_argument("--settle-steps", type=int, default=10, help="Dummy steps after reset / set_state. Default: 10")
    parser.add_argument(
        "--penetration-eps",
        type=float,
        default=1e-3,
        help="Penetration threshold for 'strong' penetration (meters). Default: 1e-3",
    )
    parser.add_argument("--max-rows", type=int, default=30, help="Max contact rows to print. Default: 30")
    parser.add_argument(
        "--ignore-robot",
        action="store_true",
        help="Ignore contacts involving robot geoms (focus on object-object / object-fixture).",
    )
    parser.add_argument(
        "--bddl-root",
        type=str,
        default=None,
        help="Override BDDL root directory (default: get_libero_path('bddl_files')).",
    )
    parser.add_argument(
        "--init-root",
        type=str,
        default=None,
        help="Override init root directory (default: get_libero_path('init_states')).",
    )
    parser.add_argument(
        "--camera-resolution",
        type=int,
        default=64,
        help="Offscreen render resolution (not critical for contact check). Default: 64",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.suite not in _iter_suite_names():
        raise SystemExit(f"[error] unknown suite '{args.suite}'. Available: {', '.join(_iter_suite_names())}")

    bddl_root_default, init_root_default = _default_paths()
    bddl_root = Path(args.bddl_root) if args.bddl_root is not None else bddl_root_default
    init_root = Path(args.init_root) if args.init_root is not None else init_root_default

    suite = _get_benchmark_instance(args.suite, task_order_index=args.task_order_index)
    if not (0 <= args.task_id < suite.get_num_tasks()):
        raise SystemExit(f"[error] task-id {args.task_id} out of range (0..{suite.get_num_tasks()-1})")
    task = suite.get_task(args.task_id)

    bddl_path = bddl_root / task.problem_folder / task.bddl_file
    if not bddl_path.exists():
        raise SystemExit(f"[error] BDDL not found: {bddl_path}")

    init_path = init_root / task.problem_folder / task.init_states_file

    from libero.libero.envs import OffScreenRenderEnv

    env = OffScreenRenderEnv(
        bddl_file_name=str(bddl_path),
        camera_heights=args.camera_resolution,
        camera_widths=args.camera_resolution,
    )
    try:
        print(f"[info] suite={args.suite} task_id={args.task_id:02d} task_name={task.name}")
        print(f"[info] bddl={bddl_path}")
        print(f"[info] init_file={init_path}")

        if args.init_idx is not None:
            if not init_path.exists():
                raise SystemExit(f"[error] init file not found: {init_path}")
            init_states = torch_load_any(init_path)
            init_states = _as_numpy_state(init_states)
            if init_states.ndim != 2:
                raise SystemExit(f"[error] expected init states shaped (N, state_dim), got {init_states.shape}")
            if not (0 <= args.init_idx < init_states.shape[0]):
                raise SystemExit(f"[error] init-idx {args.init_idx} out of range (0..{init_states.shape[0]-1})")

            env.reset()
            env.set_init_state(init_states[args.init_idx])
        else:
            env.seed(int(args.seed))
            env.reset()

        env.sim.forward()
        before = summarize_contacts(
            env.sim,
            penetration_eps=float(args.penetration_eps),
            max_rows=int(args.max_rows),
            ignore_robot=bool(args.ignore_robot),
        )
        _print_report("contacts right after reset/set_state", before)

        for _ in range(int(args.settle_steps)):
            env.step(LIBERO_DUMMY_ACTION)
        env.sim.forward()

        after = summarize_contacts(
            env.sim,
            penetration_eps=float(args.penetration_eps),
            max_rows=int(args.max_rows),
            ignore_robot=bool(args.ignore_robot),
        )
        _print_report(f"contacts after settle_steps={args.settle_steps}", after)

        return 0
    finally:
        env.close()


if __name__ == "__main__":
    raise SystemExit(main())

