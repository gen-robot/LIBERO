#!/usr/bin/env python3
"""
Create visualization grid of all ER tasks with annotations.

Creates a large image with:
- All tasks arranged in a grid
- Each task shows 3 random initializations AND their goal states
- Annotations showing task language and goal
- Proper font sizing to avoid overflow
"""

from __future__ import annotations
import argparse
import os
import re
import textwrap
from pathlib import Path
from typing import Dict, List, Tuple

from PIL import Image, ImageDraw, ImageFont


def get_font(size: int) -> ImageFont.FreeTypeFont:
    """Get a font at the specified size, with fallbacks."""
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


def wrap_text(text: str, max_chars: int = 40) -> List[str]:
    """Wrap text to fit within max characters per line."""
    return textwrap.wrap(text, width=max_chars)


def extract_task_info_from_bddl(bddl_path: str) -> dict:
    """Extract task info from BDDL file."""
    info = {'language': '', 'goal': '', 'id': Path(bddl_path).stem}

    try:
        with open(bddl_path, 'r') as f:
            content = f.read()

        lang_match = re.search(r'\(:language\s+(.+?)\)\s*\n', content)
        if lang_match:
            info['language'] = lang_match.group(1).strip()

        goal_match = re.search(r'\(:goal\s*\n\s*(.*?)\s*\)\s*\)', content, re.DOTALL)
        if goal_match:
            info['goal'] = goal_match.group(1).strip()
    except Exception:
        pass

    return info


def create_task_panel(
    task_info: dict,
    init_images: List[str],
    goal_images: List[str],
    panel_width: int = 800,
    img_size: int = 120,
    header_height: int = 50,
) -> Image.Image:
    """Create a panel for a single task with init and goal images."""
    num_seeds = min(len(init_images), len(goal_images), 3)

    # Layout: 2 rows (init, goal) x num_seeds columns
    total_img_width = num_seeds * img_size + (num_seeds - 1) * 5
    total_img_height = 2 * img_size + 25  # 2 rows + label space
    panel_height = header_height + total_img_height + 15

    panel = Image.new('RGB', (panel_width, panel_height), color=(255, 255, 255))
    draw = ImageDraw.Draw(panel)

    title_font = get_font(11)
    text_font = get_font(9)
    label_font = get_font(8)

    # Task ID (shortened)
    task_id = task_info.get('id', 'Unknown')
    short_id = task_id.replace('er_object_', '').replace('_', ' ')[:35]
    draw.text((5, 3), short_id, fill=(0, 0, 128), font=title_font)

    # Language instruction
    language = task_info.get('language', 'No description')
    wrapped_lang = wrap_text(language, max_chars=55)
    y_offset = 18
    for line in wrapped_lang[:2]:
        draw.text((5, y_offset), line, fill=(60, 60, 60), font=text_font)
        y_offset += 12

    # Images layout
    x_start = (panel_width - total_img_width) // 2
    y_start = header_height

    # Row labels
    draw.text((5, y_start + img_size // 2 - 5), "Init", fill=(0, 100, 0), font=label_font)
    draw.text((5, y_start + img_size + 10 + img_size // 2 - 5), "Goal", fill=(150, 0, 0), font=label_font)

    for seed_idx in range(num_seeds):
        x = x_start + seed_idx * (img_size + 5)

        # Init image
        if seed_idx < len(init_images):
            try:
                img = Image.open(init_images[seed_idx])
                img = img.resize((img_size, img_size), Image.Resampling.LANCZOS)
                panel.paste(img, (x, y_start))
                draw.rectangle([x, y_start, x + img_size - 1, y_start + img_size - 1], outline=(0, 150, 0), width=2)
            except Exception:
                draw.rectangle([x, y_start, x + img_size - 1, y_start + img_size - 1], fill=(240, 240, 240), outline=(200, 200, 200))

        # Goal image
        y_goal = y_start + img_size + 5
        if seed_idx < len(goal_images):
            try:
                img = Image.open(goal_images[seed_idx])
                img = img.resize((img_size, img_size), Image.Resampling.LANCZOS)
                panel.paste(img, (x, y_goal))
                draw.rectangle([x, y_goal, x + img_size - 1, y_goal + img_size - 1], outline=(200, 0, 0), width=2)
            except Exception:
                draw.rectangle([x, y_goal, x + img_size - 1, y_goal + img_size - 1], fill=(240, 240, 240), outline=(200, 200, 200))

        # Seed label
        draw.text((x + img_size // 2 - 10, y_start - 12), f"s{seed_idx}", fill=(100, 100, 100), font=label_font)

    return panel


def create_visualization_grid(
    tasks_data: List[dict],
    output_path: str,
    group_name: str = "ER",
    cols: int = 4,
    panel_width: int = 500,
    img_size: int = 120,
) -> str:
    """Create a grid visualization of all tasks with init and goal states."""
    num_tasks = len(tasks_data)
    rows = (num_tasks + cols - 1) // cols

    panel_height = 50 + 2 * img_size + 30  # header + 2 rows of images + spacing

    grid_width = cols * panel_width + (cols + 1) * 8
    grid_height = rows * panel_height + (rows + 1) * 8 + 70

    grid = Image.new('RGB', (grid_width, grid_height), color=(240, 240, 245))
    draw = ImageDraw.Draw(grid)

    title_font = get_font(22)
    subtitle_font = get_font(12)
    legend_font = get_font(10)

    # Title
    title = f"{group_name} Task Visualization"
    title_width = len(title) * 10
    draw.text((grid_width // 2 - title_width // 2, 10), title, fill=(0, 0, 100), font=title_font)

    # Subtitle
    subtitle = f"{num_tasks} tasks | 3 seeds | Init (green) vs Goal (red)"
    draw.text((grid_width // 2 - 130, 38), subtitle, fill=(80, 80, 80), font=subtitle_font)

    # Legend
    draw.rectangle([grid_width - 200, 15, grid_width - 180, 30], outline=(0, 150, 0), width=2)
    draw.text((grid_width - 175, 17), "Initial State", fill=(0, 100, 0), font=legend_font)
    draw.rectangle([grid_width - 200, 35, grid_width - 180, 50], outline=(200, 0, 0), width=2)
    draw.text((grid_width - 175, 37), "Goal State", fill=(150, 0, 0), font=legend_font)

    y_offset = 70

    for idx, task_data in enumerate(tasks_data):
        row = idx // cols
        col = idx % cols

        x = 8 + col * (panel_width + 8)
        y = y_offset + row * (panel_height + 8)

        panel = create_task_panel(
            task_info=task_data['info'],
            init_images=task_data.get('init_images', []),
            goal_images=task_data.get('goal_images', []),
            panel_width=panel_width,
            img_size=img_size,
        )
        grid.paste(panel, (x, y))

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    grid.save(output_path, quality=95)
    return output_path


def collect_task_data(rendered_dir: str, bddl_dir: str) -> List[dict]:
    """Collect task data from rendered images and BDDL files."""
    tasks_data = []
    rendered_path = Path(rendered_dir)
    bddl_path = Path(bddl_dir)

    if not rendered_path.exists():
        print(f"Rendered directory not found: {rendered_dir}")
        return tasks_data

    for task_dir in sorted(rendered_path.iterdir()):
        if not task_dir.is_dir():
            continue

        task_id = task_dir.name
        bddl_file = bddl_path / f"{task_id}.bddl"

        if bddl_file.exists():
            info = extract_task_info_from_bddl(str(bddl_file))
        else:
            info = {'id': task_id, 'language': 'No BDDL found', 'goal': ''}

        init_images = sorted(task_dir.glob("init_seed*.png"))
        goal_images = sorted(task_dir.glob("goal_seed*.png"))

        if init_images:
            tasks_data.append({
                'info': info,
                'init_images': [str(img) for img in init_images[:3]],
                'goal_images': [str(img) for img in goal_images[:3]],
            })

    return tasks_data


def main():
    parser = argparse.ArgumentParser(description="Create visualization grid of ER tasks")
    parser.add_argument(
        "--rendered-dir",
        type=str,
        default="er_extension/rendered_images/er_object",
        help="Directory containing rendered task images"
    )
    parser.add_argument(
        "--bddl-dir",
        type=str,
        default="libero/libero/bddl_files/er_object",
        help="Directory containing BDDL files"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="er_extension/visualizations/er_object_grid.png",
        help="Output image path"
    )
    parser.add_argument("--cols", type=int, default=4, help="Number of columns in grid")
    parser.add_argument("--panel-width", type=int, default=500, help="Width of each task panel")
    parser.add_argument("--img-size", type=int, default=120, help="Size of each rendered image")
    args = parser.parse_args()

    print("Collecting task data...")
    tasks_data = collect_task_data(args.rendered_dir, args.bddl_dir)

    if not tasks_data:
        print("No tasks found to visualize")
        return

    print(f"Found {len(tasks_data)} tasks with images")
    print("Creating visualization grid...")

    # Extract group name from bddl_dir (e.g., "er_object" -> "ER-OBJECT")
    bddl_dir_name = Path(args.bddl_dir).name
    group_name = bddl_dir_name.upper().replace("_", "-")

    output_path = create_visualization_grid(
        tasks_data=tasks_data,
        output_path=args.output,
        group_name=group_name,
        cols=args.cols,
        panel_width=args.panel_width,
        img_size=args.img_size,
    )

    print(f"Visualization saved to: {output_path}")

    file_size = os.path.getsize(output_path) / (1024 * 1024)
    print(f"File size: {file_size:.2f} MB")


if __name__ == "__main__":
    main()
