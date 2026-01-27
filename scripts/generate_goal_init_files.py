#!/usr/bin/env python3
"""
Generate goal init state files for LIBERO suites.

Uses the goal BDDL files (where goal predicates are init predicates) to initialize
environments and save the simulation states as init files.

Prerequisites:
    python scripts/generate_goal_bddl_files.py --suite all

Usage:
    python scripts/generate_goal_init_files.py --suite libero_10
    python scripts/generate_goal_init_files.py --suite all
"""

from __future__ import annotations
import argparse
import gc
import os
import time
from pathlib import Path
from typing import List, Optional, Sequence

import numpy as np
import torch

SCRIPT_DIR = Path(__file__).parent
LIBERO_ROOT = SCRIPT_DIR.parent / "libero" / "libero"
GOAL_BDDL_DIR = LIBERO_ROOT / "goal_bddl_files"
GOAL_INIT_DIR = GOAL_BDDL_DIR / "goal_files"

LIBERO_SUITES = ["libero_10", "libero_90", "libero_spatial", "libero_object", "libero_goal"]
ER_SUITES = ["er_object", "er_goal", "er_spatial", "er_sequential"]
SUITES = LIBERO_SUITES + ER_SUITES


def safe_close_env(env) -> None:
    """Close environment and force garbage collection to release GPU resources."""
    if env is not None:
        env.close()
        del env
    gc.collect()
    time.sleep(0.1)


def generate_init_states(bddl_file: str, num_states: int = 50, base_seed: int = 42) -> List[dict]:
    """Generate init states for a BDDL file."""
    from libero.libero.envs import OffScreenRenderEnv
    
    init_states = []
    env = None
    
    env_args = {
        "bddl_file_name": bddl_file,
        "camera_heights": 128,
        "camera_widths": 128,
    }
    
    env = OffScreenRenderEnv(**env_args)
    
    for i in range(num_states):
        seed = base_seed + i * 100
        env.seed(seed)
        env.reset()
        
        # Step a few times to stabilize
        dummy_action = [0.0] * 7
        for _ in range(10):
            env.step(dummy_action)
        
        # Get simulation state
        state = env.get_sim_state()
        init_states.append(state)
    
    safe_close_env(env)
    
    return init_states


def generate_suite_goal_init_files(
    suite_name: str,
    num_states: int = 50,
    *,
    only_tasks: Optional[Sequence[str]] = None,
) -> int:
    """Generate goal init files for a suite."""
    suite_goal_bddl_dir = GOAL_BDDL_DIR / suite_name
    suite_goal_init_dir = GOAL_INIT_DIR / suite_name
    suite_goal_init_dir.mkdir(parents=True, exist_ok=True)
    
    if not suite_goal_bddl_dir.exists():
        print(f"  [ERROR] Goal BDDL directory not found: {suite_goal_bddl_dir}")
        print("  Run generate_goal_bddl_files.py first")
        return 0
    
    bddl_files = sorted(suite_goal_bddl_dir.glob("*.bddl"))
    if only_tasks:
        wanted = set()
        for t in only_tasks:
            stem = Path(t).stem
            wanted.add(stem)
        bddl_files = [p for p in bddl_files if p.stem in wanted]
        missing = sorted(wanted - {p.stem for p in bddl_files})
        if missing:
            print(f"  [ERROR] Requested task(s) not found under {suite_goal_bddl_dir}: {', '.join(missing)}")
            return 0
    
    print(f"\nGenerating goal init files for {suite_name}: {len(bddl_files)} tasks")
    
    success_count = 0
    for bddl_file in bddl_files:
        task_name = bddl_file.stem
        output_path = suite_goal_init_dir / f"{task_name}.pruned_init"
        
        print(f"  [{success_count + 1:02d}/{len(bddl_files)}] {task_name[:40]}...", end=" ", flush=True)
        
        try:
            init_states = generate_init_states(str(bddl_file), num_states=num_states)
            torch.save(init_states, str(output_path))
            print(f"OK ({len(init_states)} states)")
            success_count += 1
        except Exception as e:
            print(f"FAILED: {e}")
    
    print(f"  Generated {success_count}/{len(bddl_files)} goal init files")
    return success_count


def main():
    parser = argparse.ArgumentParser(description="Generate goal init state files for LIBERO suites")
    parser.add_argument(
        "--suite",
        type=str,
        default="libero_10",
        choices=SUITES + ["all"],
        help="Suite to process (or 'all')"
    )
    parser.add_argument(
        "--num-states",
        type=int,
        default=50,
        help="Number of init states per task"
    )
    parser.add_argument(
        "--task",
        type=str,
        nargs="*",
        default=None,
        help=(
            "Only generate for these task files (stem or filename). "
            "Example: --suite er_spatial --task er_spatial_16"
        ),
    )
    args = parser.parse_args()
    
    GOAL_INIT_DIR.mkdir(parents=True, exist_ok=True)
    
    if args.suite == "all":
        suites = SUITES
    else:
        suites = [args.suite]
    
    total = 0
    for suite in suites:
        total += generate_suite_goal_init_files(suite, num_states=args.num_states, only_tasks=args.task)
    
    print(f"\nDone! Generated {total} goal init files in {GOAL_INIT_DIR}")


if __name__ == "__main__":
    main()
