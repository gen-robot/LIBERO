#!/usr/bin/env python3
"""
Render ER task initial and goal states for verification.

For each task:
1. Initialize simulation with 3 random seeds
2. Render initial state images
3. Render goal state by moving objects to goal positions
4. Save images for verification
"""

from __future__ import annotations
import argparse
import os
import sys
from pathlib import Path
from typing import List, Optional, Tuple, Dict
import re

import numpy as np


def setup_libero_path(libero_root: str):
    """Add LIBERO to Python path."""
    libero_package_path = os.path.dirname(os.path.dirname(libero_root))
    if libero_package_path not in sys.path:
        sys.path.insert(0, libero_package_path)


def extract_task_info(bddl_path: str) -> dict:
    """Extract task info from BDDL file for annotation."""
    with open(bddl_path, 'r') as f:
        content = f.read()

    info = {'language': '', 'goal': '', 'objects': [], 'fixtures': [], 'goal_object': '', 'goal_target': ''}

    lang_match = re.search(r'\(:language\s+(.+?)\)\s*\n', content)
    if lang_match:
        info['language'] = lang_match.group(1).strip()

    goal_match = re.search(r'\(:goal\s*\n\s*(.*?)\s*\)\s*\)', content, re.DOTALL)
    if goal_match:
        info['goal'] = goal_match.group(1).strip()
    
    # Parse goal predicate from full content: (In object_1 target_region) or (On object_1 target)
    in_match = re.search(r'\(In\s+(\w+)\s+(\w+)\)', content)
    on_match = re.search(r'\(On\s+(\w+)\s+(\w+)\)', content[content.find(':goal'):] if ':goal' in content else '')
    if in_match:
        info['goal_object'] = in_match.group(1)
        info['goal_target'] = in_match.group(2)
    elif on_match:
        info['goal_object'] = on_match.group(1)
        info['goal_target'] = on_match.group(2)

    obj_match = re.search(r'\(:objects\s*\n(.*?)\s*\)', content, re.DOTALL)
    if obj_match:
        for line in obj_match.group(1).strip().split('\n'):
            line = line.strip()
            if ' - ' in line:
                info['objects'].append(line)

    fix_match = re.search(r'\(:fixtures\s*\n(.*?)\s*\)', content, re.DOTALL)
    if fix_match:
        for line in fix_match.group(1).strip().split('\n'):
            line = line.strip()
            if ' - ' in line:
                info['fixtures'].append(line)

    return info


def get_object_body_id(env, obj_name: str) -> Optional[int]:
    """Get MuJoCo body ID for an object."""
    try:
        # Try different naming conventions
        for name_variant in [obj_name, f"{obj_name}_main", f"{obj_name}_base"]:
            try:
                body_id = env.sim.model.body_name2id(name_variant)
                return body_id
            except Exception:
                continue
        return None
    except Exception:
        return None


def get_target_position(env, target_name: str) -> Optional[np.ndarray]:
    """Get target position for goal state."""
    try:
        # For basket contain region, get basket position + offset
        if 'basket' in target_name and 'contain' in target_name:
            basket_name = target_name.split('_contain')[0]
            for name_variant in [basket_name, f"{basket_name}_main"]:
                try:
                    body_id = env.sim.model.body_name2id(name_variant)
                    pos = env.sim.data.body_xpos[body_id].copy()
                    pos[2] += 0.08  # Lift above basket
                    return pos
                except Exception:
                    continue

        # For other targets, try direct lookup
        for name_variant in [target_name, f"{target_name}_main"]:
            try:
                body_id = env.sim.model.body_name2id(name_variant)
                pos = env.sim.data.body_xpos[body_id].copy()
                pos[2] += 0.05
                return pos
            except Exception:
                continue

        return None
    except Exception:
        return None


def move_object_to_goal(env, obj_name: str, target_pos: np.ndarray) -> bool:
    """Move an object to the goal position."""
    try:
        # Find the object's joint
        obj_qpos_addr = None
        for i in range(env.sim.model.njnt):
            joint_name = env.sim.model.joint_id2name(i)
            if joint_name and obj_name in joint_name:
                obj_qpos_addr = env.sim.model.jnt_qposadr[i]
                break

        if obj_qpos_addr is not None:
            # Set position (assuming free joint with 7 DOF: x,y,z,qw,qx,qy,qz)
            env.sim.data.qpos[obj_qpos_addr:obj_qpos_addr+3] = target_pos
            env.sim.forward()
            return True

        return False
    except Exception:
        return False


def render_image(env, resolution: int) -> np.ndarray:
    """Render an image from the environment."""
    try:
        img = env.sim.render(
            camera_name="agentview",
            width=resolution,
            height=resolution,
        )
        return np.flipud(img)
    except Exception:
        return np.zeros((resolution, resolution, 3), dtype=np.uint8)


def render_task(
    bddl_file: str,
    output_dir: str,
    num_seeds: int = 3,
    resolution: int = 256,
    base_seed: int = 42,
) -> Tuple[bool, List[str], List[str], Optional[str]]:
    """Render a task with multiple random seeds, including goal states."""
    try:
        from libero.libero.envs import OffScreenRenderEnv
    except ImportError as e:
        return False, [], [], f"Import error: {e}"

    from PIL import Image

    task_name = Path(bddl_file).stem
    task_output_dir = os.path.join(output_dir, task_name)
    os.makedirs(task_output_dir, exist_ok=True)

    task_info = extract_task_info(bddl_file)
    init_images = []
    goal_images = []

    try:
        env_args = {
            "bddl_file_name": bddl_file,
            "camera_heights": resolution,
            "camera_widths": resolution,
        }
        env = OffScreenRenderEnv(**env_args)

        for seed_idx in range(num_seeds):
            seed = base_seed + seed_idx * 100
            env.seed(seed)
            env.reset()

            # Render initial state
            init_img = render_image(env, resolution)
            init_path = os.path.join(task_output_dir, f"init_seed{seed_idx}.png")
            Image.fromarray(init_img).save(init_path)
            init_images.append(init_path)

            # Render goal state by moving object to target
            goal_obj = task_info.get('goal_object', '')
            goal_target = task_info.get('goal_target', '')

            goal_moved = False
            if goal_obj and goal_target:
                target_pos = get_target_position(env, goal_target)
                if target_pos is not None:
                    goal_moved = move_object_to_goal(env, goal_obj, target_pos)
                    for _ in range(20):
                        env.sim.step()

            goal_img = render_image(env, resolution)
            goal_path = os.path.join(task_output_dir, f"goal_seed{seed_idx}.png")
            Image.fromarray(goal_img).save(goal_path)
            goal_images.append(goal_path)

        env.close()
        return True, init_images, goal_images, None

    except Exception as e:
        return False, init_images, goal_images, str(e)


def main():
    parser = argparse.ArgumentParser(description="Render ER tasks for verification")
    parser.add_argument(
        "--libero-root",
        type=str,
        default="libero/libero",
        help="Path to LIBERO libero/libero directory"
    )
    parser.add_argument(
        "--er-dir",
        type=str,
        default="libero/libero/bddl_files/er_object",
        help="Directory containing ER BDDL files"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="er_extension/rendered_images/er_object",
        help="Output directory for rendered images"
    )
    parser.add_argument("--num-seeds", type=int, default=3, help="Number of random seeds")
    parser.add_argument("--resolution", type=int, default=256, help="Image resolution")
    parser.add_argument("--base-seed", type=int, default=42, help="Base random seed")
    parser.add_argument("--task-id", type=str, help="Render only specific task ID")
    args = parser.parse_args()

    setup_libero_path(args.libero_root)

    er_dir = Path(args.er_dir)
    if not er_dir.exists():
        print(f"Error: Directory not found: {er_dir}")
        return

    bddl_files = sorted(er_dir.glob("*.bddl"))
    if args.task_id:
        bddl_files = [f for f in bddl_files if args.task_id in f.stem]

    if not bddl_files:
        print(f"No BDDL files found in {er_dir}")
        return

    os.makedirs(args.output_dir, exist_ok=True)

    print(f"Rendering {len(bddl_files)} tasks (init + goal states)")
    print("=" * 60)

    success_count = 0
    failed_tasks = []
    all_images = {}

    for bddl_file in bddl_files:
        task_name = bddl_file.stem
        print(f"\nRendering: {task_name}")

        task_info = extract_task_info(str(bddl_file))
        print(f"  Language: {task_info['language'][:50]}...")
        print(f"  Goal: {task_info['goal_object']} -> {task_info['goal_target']}")

        success, init_imgs, goal_imgs, error = render_task(
            bddl_file=str(bddl_file),
            output_dir=args.output_dir,
            num_seeds=args.num_seeds,
            resolution=args.resolution,
            base_seed=args.base_seed,
        )

        if success:
            print(f"  Saved {len(init_imgs)} init + {len(goal_imgs)} goal images")
            success_count += 1
            all_images[task_name] = {
                'init_images': init_imgs,
                'goal_images': goal_imgs,
                'info': task_info,
            }
        else:
            print(f"  [ERROR] {error}")
            failed_tasks.append((task_name, error))

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Success: {success_count}/{len(bddl_files)}")
    print(f"  Failed:  {len(failed_tasks)}/{len(bddl_files)}")

    if failed_tasks:
        print("\nFailed tasks:")
        for name, err in failed_tasks:
            print(f"  - {name}: {err[:50]}")

    # Save manifest
    manifest_path = os.path.join(args.output_dir, "manifest.txt")
    with open(manifest_path, 'w') as f:
        for task_name, data in all_images.items():
            f.write(f"{task_name}\n")
            f.write(f"  language: {data['info']['language']}\n")
            f.write(f"  goal: {data['info']['goal']}\n")
            for img_path in data['init_images']:
                f.write(f"  init: {img_path}\n")
            for img_path in data['goal_images']:
                f.write(f"  goal: {img_path}\n")
    print(f"\nManifest saved to: {manifest_path}")


if __name__ == "__main__":
    main()
