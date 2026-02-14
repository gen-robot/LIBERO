#!/usr/bin/env python3
"""
Visualize LIBERO benchmark suites (libero_90, libero_10, libero_object, libero_goal, libero_spatial).

Creates visualization grids showing init AND goal states for each task.
Goal states are rendered using:
1. Pre-generated goal BDDL files and goal init files (if available)
2. Fallback: Move objects to goal positions via qpos manipulation

Prerequisites (optional but recommended):
    python scripts/generate_goal_bddl_files.py --suite all
    python scripts/generate_goal_init_files.py --suite all

Usage:
    python scripts/visualize_libero_suites.py --suite libero_10
    python scripts/visualize_libero_suites.py --suite all
    python scripts/visualize_libero_suites.py --suite libero_10 --skip-render
"""

from __future__ import annotations
import argparse
import gc
import os
import re
import textwrap
import time
import traceback
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFont

SCRIPT_DIR = Path(__file__).parent
LIBERO_ROOT = SCRIPT_DIR.parent / "libero" / "libero"
BDDL_DIR = LIBERO_ROOT / "bddl_files"
INIT_DIR = LIBERO_ROOT / "init_files"
GOAL_BDDL_DIR = LIBERO_ROOT / "goal_bddl_files"
GOAL_INIT_DIR = GOAL_BDDL_DIR / "goal_files"

OUTPUT_DIR = SCRIPT_DIR.parent / "visualizations"
RENDERED_DIR = OUTPUT_DIR / "rendered_images"

LIBERO_SUITES = ["libero_10", "libero_90", "libero_spatial", "libero_object", "libero_goal"]
ER_SUITES = ["er_object", "er_goal", "er_spatial", "er_sequential", "er_object_simple"]
SUITES = LIBERO_SUITES + ER_SUITES


def torch_load_any(path: str):
    """
    Load torch-saved objects (e.g. lists of dict sim states).

    Note: For PyTorch >= 2.6, `torch.load` defaults to `weights_only=True`, which
    can reject non-weight pickles such as LIBERO init-state files. We fall back
    to `weights_only=False` for local benchmark artifacts.
    """
    try:
        return torch.load(path)
    except Exception:
        try:
            return torch.load(path, weights_only=False)
        except TypeError:
            raise


def get_font(size: int) -> ImageFont.FreeTypeFont:
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
    ]
    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def wrap_text(text: str, max_chars: int = 50) -> List[str]:
    return textwrap.wrap(text, width=max_chars)


def render_image(env, resolution: int) -> np.ndarray:
    img = env.sim.render(
        camera_name="agentview",
        width=resolution,
        height=resolution,
    )
    return np.flipud(img)


def safe_close_env(env) -> None:
    """Close environment and force garbage collection to release GPU resources."""
    if env is not None:
        env.close()
        del env
    gc.collect()
    time.sleep(0.1)


def parse_goal_predicates(bddl_path: str) -> List[Tuple[str, List[str]]]:
    """Parse goal predicates from BDDL file."""
    with open(bddl_path, 'r') as f:
        content = f.read()
    
    predicates = []
    
    # Find goal section using balanced parens
    goal_start = content.find('(:goal')
    if goal_start == -1:
        return predicates
    
    depth = 0
    goal_end = goal_start
    for i in range(goal_start, len(content)):
        if content[i] == '(':
            depth += 1
        elif content[i] == ')':
            depth -= 1
            if depth == 0:
                goal_end = i + 1
                break
    
    goal_section = content[goal_start:goal_end]
    
    pred_pattern = r'\((\w+)\s+([^()]+)\)'
    for match in re.finditer(pred_pattern, goal_section):
        pred_name = match.group(1)
        if pred_name == 'And':
            continue
        args = match.group(2).strip().split()
        predicates.append((pred_name, args))
    
    return predicates


def get_target_position(env, target_name: str) -> Optional[np.ndarray]:
    """Get target position for goal object placement.
    
    Handles various region naming patterns:
    - desk_caddy_1_front_region -> desk_caddy_1_main
    - basket_1_contain_region -> basket_1_main
    - wooden_cabinet_1_top_side -> wooden_cabinet_1_main
    - flat_stove_1_cook_region -> flat_stove_1_main
    """
    # Build list of candidate body names to try
    patterns = [target_name, f"{target_name}_main", f"{target_name}_base"]
    
    # Extract fixture base name from region name patterns
    # Pattern: fixture_name_1_region_type -> fixture_name_1
    region_suffixes = [
        '_front_region', '_back_region', '_left_region', '_right_region',
        '_contain_region', '_top_side', '_top_region', '_bottom_region',
        '_cook_region', '_shelf_region', '_drawer_region',
    ]
    
    base_fixture = None
    for suffix in region_suffixes:
        if suffix in target_name:
            base_fixture = target_name.replace(suffix, '')
            break
    
    # Also try splitting on common patterns
    if base_fixture is None:
        for sep in ['_region', '_side']:
            if sep in target_name:
                parts = target_name.rsplit(sep, 1)
                # Get everything up to the last qualifier (front, back, left, right, top, etc.)
                candidate = parts[0]
                for qual in ['_front', '_back', '_left', '_right', '_top', '_bottom', '_cook', '_contain']:
                    if candidate.endswith(qual):
                        base_fixture = candidate.rsplit(qual, 1)[0]
                        break
                if base_fixture is None:
                    base_fixture = candidate
                break
    
    if base_fixture:
        patterns.extend([
            base_fixture,
            f"{base_fixture}_main",
            f"{base_fixture}_base",
            f"{base_fixture}_body",
        ])
    
    for name in patterns:
        try:
            body_id = env.sim.model.body_name2id(name)
            pos = env.sim.data.body_xpos[body_id].copy()
            pos[2] += 0.08
            return pos
        except Exception:
            continue
    
    return None


def move_object_to_position(env, obj_name: str, target_pos: np.ndarray) -> bool:
    """Move object to target position via qpos."""
    for i in range(env.sim.model.njnt):
        joint_name = env.sim.model.joint_id2name(i)
        if joint_name and obj_name in joint_name:
            qpos_addr = env.sim.model.jnt_qposadr[i]
            env.sim.data.qpos[qpos_addr:qpos_addr+3] = target_pos
            env.sim.forward()
            return True
    return False


def set_drawer_state(env, drawer_name: str, is_open: bool) -> bool:
    """Set drawer open/close state."""
    base_name = drawer_name.replace("_region", "")
    for i in range(env.sim.model.njnt):
        joint_name = env.sim.model.joint_id2name(i)
        if joint_name and base_name in joint_name:
            qpos_addr = env.sim.model.jnt_qposadr[i]
            env.sim.data.qpos[qpos_addr] = 0.15 if is_open else 0.0
            env.sim.forward()
            return True
    return False


def apply_goal_state_fallback(env, goal_predicates: List[Tuple[str, List[str]]]) -> None:
    """Apply goal state by moving objects to goal positions (fallback method)."""
    for pred_name, args in goal_predicates:
        if pred_name in ('On', 'In') and len(args) >= 2:
            obj_name = args[0]
            target_name = args[1]
            target_pos = get_target_position(env, target_name)
            if target_pos is not None:
                move_object_to_position(env, obj_name, target_pos)
        elif pred_name == 'Open' and args:
            set_drawer_state(env, args[0], is_open=True)
        elif pred_name == 'Close' and args:
            set_drawer_state(env, args[0], is_open=False)
        elif pred_name in ('TurnOn', 'Turnon') and args:
            for i in range(env.sim.model.njnt):
                joint_name = env.sim.model.joint_id2name(i)
                if joint_name and 'knob' in joint_name.lower():
                    qpos_addr = env.sim.model.jnt_qposadr[i]
                    env.sim.data.qpos[qpos_addr] = 0.5
                    break
    
    env.sim.forward()
    dummy_action = [0.0] * 7
    for _ in range(20):
        try:
            env.sim.step()
        except Exception:
            break


def render_er_suite_images(
    suite_name: str,
    output_dir: Path,
    num_seeds: int = 3,
    resolution: int = 256,
    task_ids: Optional[set[int]] = None,
) -> dict:
    """Render init and goal state images for ER suites (no benchmark registration)."""
    from libero.libero.envs import OffScreenRenderEnv
    
    suite_bddl_dir = BDDL_DIR / suite_name
    bddl_files = sorted(suite_bddl_dir.glob("*.bddl"))
    
    suite_output_dir = output_dir / suite_name
    suite_output_dir.mkdir(parents=True, exist_ok=True)
    
    goal_bddl_suite_dir = GOAL_BDDL_DIR / suite_name
    goal_init_suite_dir = GOAL_INIT_DIR / suite_name
    
    print(f"Rendering {suite_name}: {len(bddl_files)} tasks")
    
    all_task_data = {}
    
    for task_id, bddl_file in enumerate(bddl_files):
        if task_ids is not None and task_id not in task_ids:
            continue
        task_name = bddl_file.stem
        
        # Extract language from BDDL
        with open(bddl_file, 'r') as f:
            content = f.read()
        lang_match = re.search(r'\(:language\s+(.+?)\)\s*\n', content)
        task_description = lang_match.group(1).strip() if lang_match else task_name
        
        task_output_dir = suite_output_dir / f"task_{task_id:02d}"
        task_output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"  [{task_id:02d}] {task_description[:50]}...")
        
        init_images = []
        goal_images = []
        
        goal_predicates = parse_goal_predicates(str(bddl_file))
        goal_bddl_file = goal_bddl_suite_dir / bddl_file.name
        goal_init_file = goal_init_suite_dir / f"{task_name}.pruned_init"
        
        # Render INIT states (generate on the fly)
        env = None
        try:
            env_args = {
                "bddl_file_name": str(bddl_file),
                "camera_heights": resolution,
                "camera_widths": resolution,
            }
            env = OffScreenRenderEnv(**env_args)
            
            for seed_idx in range(num_seeds):
                env.seed(42 + seed_idx * 100)
                env.reset()
                
                dummy_action = [0.0] * 7
                for _ in range(5):
                    env.step(dummy_action)
                
                init_img = render_image(env, resolution)
                init_path = task_output_dir / f"init_seed{seed_idx}.png"
                Image.fromarray(init_img).save(str(init_path))
                init_images.append(str(init_path))
            
            safe_close_env(env)
            env = None
        except Exception as e:
            # Debug log: show full traceback and hint about which BDDL caused failure
            print(f"    [ERROR] Init: {e}")
            print(f"    [DEBUG] Init exception in {bddl_file}")
            print("    [DEBUG] Full traceback:")
            for line in traceback.format_exc().splitlines():
                print("      " + line)
            if env is not None:
                safe_close_env(env)
                env = None
        
        # Render GOAL states
        goal_rendered = False
        goal_env = None
        
        # Method 1: Use pre-generated goal files
        if goal_bddl_file.exists() and goal_init_file.exists():
            try:
                goal_states = torch_load_any(str(goal_init_file))
                
                goal_env_args = {
                    "bddl_file_name": str(goal_bddl_file),
                    "camera_heights": resolution,
                    "camera_widths": resolution,
                }
                goal_env = OffScreenRenderEnv(**goal_env_args)
                
                for seed_idx in range(min(num_seeds, len(goal_states))):
                    goal_env.reset()
                    goal_env.set_init_state(goal_states[seed_idx])
                    
                    dummy_action = [0.0] * 7
                    for _ in range(5):
                        goal_env.step(dummy_action)
                    
                    goal_img = render_image(goal_env, resolution)
                    goal_path = task_output_dir / f"goal_seed{seed_idx}.png"
                    Image.fromarray(goal_img).save(str(goal_path))
                    goal_images.append(str(goal_path))
                
                safe_close_env(goal_env)
                goal_env = None
                goal_rendered = True
            except Exception:
                if goal_env is not None:
                    safe_close_env(goal_env)
                    goal_env = None
        
        # Method 2: Fallback - move objects via qpos
        if not goal_rendered and goal_predicates and init_images:
            env = None
            try:
                env_args = {
                    "bddl_file_name": str(bddl_file),
                    "camera_heights": resolution,
                    "camera_widths": resolution,
                }
                env = OffScreenRenderEnv(**env_args)
                
                for seed_idx in range(num_seeds):
                    env.seed(42 + seed_idx * 100)
                    env.reset()
                    
                    apply_goal_state_fallback(env, goal_predicates)
                    
                    goal_img = render_image(env, resolution)
                    goal_path = task_output_dir / f"goal_seed{seed_idx}.png"
                    Image.fromarray(goal_img).save(str(goal_path))
                    goal_images.append(str(goal_path))
                
                safe_close_env(env)
                env = None
                goal_rendered = True
            except Exception as e:
                print(f"    [ERROR] Goal fallback: {e}")
                if env is not None:
                    safe_close_env(env)
                    env = None
        
        if not goal_images:
            goal_images = init_images.copy()
        
        all_task_data[task_id] = {
            "task_name": task_name,
            "task_description": task_description,
            "init_images": init_images,
            "goal_images": goal_images,
        }
    
    return all_task_data


def render_task_images(
    task_suite_name: str,
    output_dir: Path,
    num_seeds: int = 3,
    resolution: int = 256,
    task_ids: Optional[set[int]] = None,
) -> dict:
    """Render init and goal state images for all tasks in a suite."""
    # Handle ER suites separately (not registered in benchmark)
    if task_suite_name in ER_SUITES:
        return render_er_suite_images(task_suite_name, output_dir, num_seeds, resolution, task_ids=task_ids)
    
    from libero.libero import benchmark
    from libero.libero.envs import OffScreenRenderEnv
    
    benchmark_dict = benchmark.get_benchmark_dict()
    task_suite = benchmark_dict[task_suite_name]()
    num_tasks = task_suite.n_tasks
    
    suite_output_dir = output_dir / task_suite_name
    suite_output_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if goal files exist
    goal_bddl_suite_dir = GOAL_BDDL_DIR / task_suite_name
    goal_init_suite_dir = GOAL_INIT_DIR / task_suite_name
    
    print(f"Rendering {task_suite_name}: {num_tasks} tasks")
    
    all_task_data = {}
    
    for task_id in range(num_tasks):
        if task_ids is not None and task_id not in task_ids:
            continue
        task = task_suite.get_task(task_id)
        task_name = task.name
        task_description = task.language
        
        task_output_dir = suite_output_dir / f"task_{task_id:02d}"
        task_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Paths
        bddl_file = BDDL_DIR / task_suite_name / task.bddl_file
        init_file = INIT_DIR / task_suite_name / task.init_states_file
        goal_bddl_file = goal_bddl_suite_dir / task.bddl_file
        goal_init_file = goal_init_suite_dir / task.init_states_file
        
        print(f"  [{task_id:02d}] {task_description[:50]}...")
        
        init_images = []
        goal_images = []
        
        # Parse goal predicates for fallback
        goal_predicates = parse_goal_predicates(str(bddl_file))
        
        # Render INIT states
        env = None
        try:
            init_states = torch_load_any(str(init_file))
            
            env_args = {
                "bddl_file_name": str(bddl_file),
                "camera_heights": resolution,
                "camera_widths": resolution,
            }
            env = OffScreenRenderEnv(**env_args)
            
            for seed_idx in range(min(num_seeds, len(init_states))):
                env.reset()
                env.set_init_state(init_states[seed_idx])
                
                dummy_action = [0.0] * 7
                for _ in range(5):
                    env.step(dummy_action)
                
                init_img = render_image(env, resolution)
                init_path = task_output_dir / f"init_seed{seed_idx}.png"
                Image.fromarray(init_img).save(str(init_path))
                init_images.append(str(init_path))
            
            safe_close_env(env)
            env = None
        except Exception as e:
            print(f"    [ERROR] Init: {e}")
            if env is not None:
                safe_close_env(env)
                env = None
        
        # Render GOAL states - try goal files first, then fallback
        goal_rendered = False
        goal_env = None
        
        # Method 1: Use pre-generated goal files
        if goal_bddl_file.exists() and goal_init_file.exists():
            try:
                goal_states = torch_load_any(str(goal_init_file))
                
                goal_env_args = {
                    "bddl_file_name": str(goal_bddl_file),
                    "camera_heights": resolution,
                    "camera_widths": resolution,
                }
                goal_env = OffScreenRenderEnv(**goal_env_args)
                
                for seed_idx in range(min(num_seeds, len(goal_states))):
                    goal_env.reset()
                    goal_env.set_init_state(goal_states[seed_idx])
                    
                    dummy_action = [0.0] * 7
                    for _ in range(5):
                        goal_env.step(dummy_action)
                    
                    goal_img = render_image(goal_env, resolution)
                    goal_path = task_output_dir / f"goal_seed{seed_idx}.png"
                    Image.fromarray(goal_img).save(str(goal_path))
                    goal_images.append(str(goal_path))
                
                safe_close_env(goal_env)
                goal_env = None
                goal_rendered = True
            except Exception:
                if goal_env is not None:
                    safe_close_env(goal_env)
                    goal_env = None
        
        # Method 2: Fallback - move objects to goal via qpos
        if not goal_rendered and goal_predicates and init_images:
            env = None
            try:
                init_states = torch_load_any(str(init_file))
                
                env_args = {
                    "bddl_file_name": str(bddl_file),
                    "camera_heights": resolution,
                    "camera_widths": resolution,
                }
                env = OffScreenRenderEnv(**env_args)
                
                for seed_idx in range(min(num_seeds, len(init_states))):
                    env.reset()
                    env.set_init_state(init_states[seed_idx])
                    
                    # Apply goal state via qpos manipulation
                    apply_goal_state_fallback(env, goal_predicates)
                    
                    goal_img = render_image(env, resolution)
                    goal_path = task_output_dir / f"goal_seed{seed_idx}.png"
                    Image.fromarray(goal_img).save(str(goal_path))
                    goal_images.append(str(goal_path))
                
                safe_close_env(env)
                env = None
                goal_rendered = True
            except Exception as e:
                print(f"    [ERROR] Goal fallback: {e}")
                if env is not None:
                    safe_close_env(env)
                    env = None
        
        # If still no goal images, use init as placeholder
        if not goal_images:
            goal_images = init_images.copy()
        
        all_task_data[task_id] = {
            "task_name": task_name,
            "task_description": task_description,
            "init_images": init_images,
            "goal_images": goal_images,
        }
    
    return all_task_data


def create_task_panel(
    task_id: int,
    task_description: str,
    init_images: List[str],
    goal_images: List[str],
    max_seeds: int = 3,
    panel_width: int = 500,
    img_size: int = 100,
    header_height: int = 55,
) -> Image.Image:
    """Create a panel for a single task with init and goal images."""
    num_seeds = min(len(init_images), max_seeds) if init_images else max_seeds
    
    total_img_width = num_seeds * img_size + (num_seeds - 1) * 5
    total_img_height = 2 * img_size + 20
    panel_height = header_height + total_img_height + 15
    
    panel = Image.new('RGB', (panel_width, panel_height), color=(255, 255, 255))
    draw = ImageDraw.Draw(panel)
    
    title_font = get_font(11)
    text_font = get_font(9)
    label_font = get_font(8)
    
    draw.text((5, 2), f"Task {task_id}", fill=(0, 0, 128), font=title_font)
    
    wrapped = wrap_text(task_description, max_chars=55)
    y_offset = 16
    for line in wrapped[:2]:
        draw.text((5, y_offset), line, fill=(60, 60, 60), font=text_font)
        y_offset += 12
    
    x_start = (panel_width - total_img_width) // 2 + 20
    y_start = header_height
    
    draw.text((5, y_start + img_size // 2 - 5), "Init", fill=(0, 100, 0), font=label_font)
    draw.text((5, y_start + img_size + 8 + img_size // 2 - 5), "Goal", fill=(150, 0, 0), font=label_font)
    
    for seed_idx in range(num_seeds):
        x = x_start + seed_idx * (img_size + 5)
        
        if seed_idx < len(init_images):
            try:
                img = Image.open(init_images[seed_idx])
                img = img.resize((img_size, img_size), Image.Resampling.LANCZOS)
                panel.paste(img, (x, y_start))
                draw.rectangle([x, y_start, x + img_size - 1, y_start + img_size - 1], outline=(0, 150, 0), width=2)
            except Exception:
                draw.rectangle([x, y_start, x + img_size - 1, y_start + img_size - 1], fill=(240, 240, 240), outline=(200, 200, 200))
        else:
            draw.rectangle([x, y_start, x + img_size - 1, y_start + img_size - 1], fill=(240, 240, 240), outline=(200, 200, 200))
        
        y_goal = y_start + img_size + 5
        if seed_idx < len(goal_images):
            try:
                img = Image.open(goal_images[seed_idx])
                img = img.resize((img_size, img_size), Image.Resampling.LANCZOS)
                panel.paste(img, (x, y_goal))
                draw.rectangle([x, y_goal, x + img_size - 1, y_goal + img_size - 1], outline=(200, 0, 0), width=2)
            except Exception:
                draw.rectangle([x, y_goal, x + img_size - 1, y_goal + img_size - 1], fill=(240, 240, 240), outline=(200, 200, 200))
        else:
            draw.rectangle([x, y_goal, x + img_size - 1, y_goal + img_size - 1], fill=(240, 240, 240), outline=(200, 200, 200))
        
        draw.text((x + img_size // 2 - 8, y_start - 11), f"s{seed_idx}", fill=(100, 100, 100), font=label_font)
    
    return panel


def create_visualization_grid(
    task_data: dict,
    output_path: Path,
    suite_name: str,
    cols: int = 4,
    max_seeds: int = 3,
    panel_width: int = 500,
    img_size: int = 100,
) -> str:
    """Create a grid visualization of all tasks with init and goal states."""
    num_tasks = len(task_data)
    rows = (num_tasks + cols - 1) // cols
    
    panel_height = 55 + 2 * img_size + 30
    
    grid_width = cols * panel_width + (cols + 1) * 8
    grid_height = rows * panel_height + (rows + 1) * 8 + 70
    
    grid = Image.new('RGB', (grid_width, grid_height), color=(240, 240, 245))
    draw = ImageDraw.Draw(grid)
    
    title_font = get_font(22)
    subtitle_font = get_font(12)
    legend_font = get_font(10)
    
    title = suite_name.upper().replace("_", "-")
    title_width = len(title) * 10
    draw.text((grid_width // 2 - title_width // 2, 10), title, fill=(0, 0, 100), font=title_font)
    
    subtitle = f"{num_tasks} tasks | {max_seeds} seeds | Init (green) vs Goal (red)"
    draw.text((grid_width // 2 - 130, 38), subtitle, fill=(80, 80, 80), font=subtitle_font)
    
    draw.rectangle([grid_width - 200, 15, grid_width - 180, 30], outline=(0, 150, 0), width=2)
    draw.text((grid_width - 175, 17), "Initial State", fill=(0, 100, 0), font=legend_font)
    draw.rectangle([grid_width - 200, 35, grid_width - 180, 50], outline=(200, 0, 0), width=2)
    draw.text((grid_width - 175, 37), "Goal State", fill=(150, 0, 0), font=legend_font)
    
    y_offset = 70
    
    for idx, (task_id, data) in enumerate(sorted(task_data.items())):
        row = idx // cols
        col = idx % cols
        
        x = 8 + col * (panel_width + 8)
        y = y_offset + row * (panel_height + 8)
        
        panel = create_task_panel(
            task_id=task_id,
            task_description=data["task_description"],
            init_images=data.get("init_images", []),
            goal_images=data.get("goal_images", []),
            max_seeds=max_seeds,
            panel_width=panel_width,
            img_size=img_size,
        )
        grid.paste(panel, (x, y))
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    grid.save(str(output_path), quality=95)
    return str(output_path)


def load_existing_task_data(suite_dir: Path) -> dict:
    """Load task data from existing rendered images."""
    suite_name = suite_dir.name
    
    task_data = {}
    
    # For ER suites, read task info from BDDL files
    if suite_name in ER_SUITES:
        bddl_dir = BDDL_DIR / suite_name
        bddl_files = sorted(bddl_dir.glob("*.bddl"))
        bddl_map = {i: f for i, f in enumerate(bddl_files)}
        
        for task_dir in sorted(suite_dir.iterdir()):
            if not task_dir.is_dir():
                continue
            
            try:
                task_id = int(task_dir.name.split("_")[1])
            except (ValueError, IndexError):
                continue
            
            if task_id not in bddl_map:
                continue
            
            bddl_file = bddl_map[task_id]
            with open(bddl_file, 'r') as f:
                content = f.read()
            lang_match = re.search(r'\(:language\s+(.+?)\)\s*\n', content)
            task_description = lang_match.group(1).strip() if lang_match else bddl_file.stem
            
            init_images = sorted(task_dir.glob("init_seed*.png"))
            goal_images = sorted(task_dir.glob("goal_seed*.png"))
            
            task_data[task_id] = {
                "task_name": bddl_file.stem,
                "task_description": task_description,
                "init_images": [str(img) for img in init_images],
                "goal_images": [str(img) for img in goal_images],
            }
    else:
        # For official LIBERO suites, use benchmark
        from libero.libero import benchmark
        
        benchmark_dict = benchmark.get_benchmark_dict()
        task_suite = benchmark_dict[suite_name]()
        
        for task_dir in sorted(suite_dir.iterdir()):
            if not task_dir.is_dir():
                continue
            
            try:
                task_id = int(task_dir.name.split("_")[1])
            except (ValueError, IndexError):
                continue
            
            task = task_suite.get_task(task_id)
            
            init_images = sorted(task_dir.glob("init_seed*.png"))
            goal_images = sorted(task_dir.glob("goal_seed*.png"))
            
            task_data[task_id] = {
                "task_name": task.name,
                "task_description": task.language,
                "init_images": [str(img) for img in init_images],
                "goal_images": [str(img) for img in goal_images],
            }
    
    return task_data


def visualize_suite(
    suite_name: str,
    skip_render: bool = False,
    num_seeds: int = 3,
    task_ids: Optional[set[int]] = None,
):
    """Visualize a single suite."""
    print(f"\n{'='*60}")
    print(f"Processing: {suite_name}")
    print(f"{'='*60}")
    
    suite_rendered_dir = RENDERED_DIR / suite_name
    
    if skip_render and suite_rendered_dir.exists():
        print("Loading existing rendered images...")
        task_data = load_existing_task_data(suite_rendered_dir)
    else:
        print("Rendering task images (init + goal)...")
        task_data = render_task_images(
            task_suite_name=suite_name,
            output_dir=RENDERED_DIR,
            num_seeds=num_seeds,
            task_ids=task_ids,
        )
    
    if task_ids is not None:
        task_data = {k: v for k, v in task_data.items() if k in task_ids}

    if not task_data:
        print(f"No tasks found for {suite_name}")
        return
    
    print(f"\nCreating visualization grid ({len(task_data)} tasks)...")
    
    cols = min(5, max(1, len(task_data)))
    img_size = 100
    total_img_width = num_seeds * img_size + (num_seeds - 1) * 5
    panel_width = max(500, total_img_width + 80)
    
    if task_ids is None:
        output_path = OUTPUT_DIR / f"{suite_name}_grid.png"
    elif len(task_ids) == 1:
        (only_id,) = tuple(task_ids)
        output_path = OUTPUT_DIR / f"{suite_name}_task{only_id:02d}_grid.png"
    else:
        output_path = OUTPUT_DIR / f"{suite_name}_subset_grid.png"
    
    create_visualization_grid(
        task_data=task_data,
        output_path=output_path,
        suite_name=suite_name,
        cols=cols,
        max_seeds=num_seeds,
        panel_width=panel_width,
        img_size=img_size,
    )
    
    file_size = output_path.stat().st_size / (1024 * 1024)
    print(f"Saved: {output_path} ({file_size:.2f} MB)")


def main():
    parser = argparse.ArgumentParser(description="Visualize LIBERO benchmark suites")
    parser.add_argument(
        "--suite",
        type=str,
        default="libero_10",
        choices=SUITES + ["all"],
        help="Suite to visualize (or 'all' for all suites)"
    )
    parser.add_argument(
        "--skip-render",
        action="store_true",
        help="Skip rendering, use existing images"
    )
    parser.add_argument(
        "--num-seeds",
        type=int,
        default=3,
        help="Number of scenes (seeds) to render + show per task"
    )
    parser.add_argument(
        "--task-id",
        type=int,
        action="append",
        default=None,
        help="Only visualize specific task id(s); pass multiple times, e.g. --task-id 0 --task-id 12",
    )
    args = parser.parse_args()
    task_ids = set(args.task_id) if args.task_id else None
    
    if args.suite == "all":
        suites_to_process = SUITES
    else:
        suites_to_process = [args.suite]
    
    for suite_name in suites_to_process:
        visualize_suite(
            suite_name=suite_name,
            skip_render=args.skip_render,
            num_seeds=args.num_seeds,
            task_ids=task_ids,
        )
    
    print(f"\n{'='*60}")
    print("Done!")
    print(f"Visualizations saved to: {OUTPUT_DIR}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
