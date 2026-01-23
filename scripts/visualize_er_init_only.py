#!/usr/bin/env python3
"""
Visualize ER suites - init states only (no goal states).

Usage:
    python scripts/visualize_er_init_only.py
"""

from __future__ import annotations
import re
import textwrap
import os
from pathlib import Path
from typing import List

from PIL import Image, ImageDraw, ImageFont

SCRIPT_DIR = Path(__file__).parent
LIBERO_ROOT = SCRIPT_DIR.parent / "libero" / "libero"
BDDL_DIR = LIBERO_ROOT / "bddl_files"

OUTPUT_DIR = SCRIPT_DIR.parent / "visualizations"
RENDERED_DIR = OUTPUT_DIR / "rendered_images"

ER_SUITES = ["er_object", "er_goal", "er_spatial", "er_sequential"]


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


def create_init_only_panel(
    task_id: int,
    task_description: str,
    init_images: List[str],
    panel_width: int = 400,
    img_size: int = 100,
    header_height: int = 55,
) -> Image.Image:
    """Create a panel for a single task with init images only."""
    num_seeds = min(len(init_images), 3) if init_images else 3
    
    total_img_width = num_seeds * img_size + (num_seeds - 1) * 5
    panel_height = header_height + img_size + 15
    
    panel = Image.new('RGB', (panel_width, panel_height), color=(255, 255, 255))
    draw = ImageDraw.Draw(panel)
    
    title_font = get_font(11)
    text_font = get_font(9)
    label_font = get_font(8)
    
    draw.text((5, 2), f"Task {task_id}", fill=(0, 0, 128), font=title_font)
    
    wrapped = wrap_text(task_description, max_chars=50)
    y_offset = 16
    for line in wrapped[:2]:
        draw.text((5, y_offset), line, fill=(60, 60, 60), font=text_font)
        y_offset += 12
    
    x_start = (panel_width - total_img_width) // 2
    y_start = header_height
    
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
        
        draw.text((x + img_size // 2 - 8, y_start - 11), f"s{seed_idx}", fill=(100, 100, 100), font=label_font)
    
    return panel


def create_init_only_grid(
    task_data: dict,
    output_path: Path,
    suite_name: str,
    cols: int = 5,
    panel_width: int = 400,
    img_size: int = 100,
) -> str:
    """Create a grid visualization of all tasks with init states only."""
    num_tasks = len(task_data)
    rows = (num_tasks + cols - 1) // cols
    
    panel_height = 55 + img_size + 20
    
    grid_width = cols * panel_width + (cols + 1) * 8
    grid_height = rows * panel_height + (rows + 1) * 8 + 60
    
    grid = Image.new('RGB', (grid_width, grid_height), color=(240, 240, 245))
    draw = ImageDraw.Draw(grid)
    
    title_font = get_font(22)
    subtitle_font = get_font(12)
    
    title = suite_name.upper().replace("_", "-")
    title_width = len(title) * 10
    draw.text((grid_width // 2 - title_width // 2, 10), title, fill=(0, 0, 100), font=title_font)
    
    subtitle = f"{num_tasks} tasks | 3 seeds | Initial States"
    draw.text((grid_width // 2 - 100, 38), subtitle, fill=(80, 80, 80), font=subtitle_font)
    
    y_offset = 60
    
    for idx, (task_id, data) in enumerate(sorted(task_data.items())):
        row = idx // cols
        col = idx % cols
        
        x = 8 + col * (panel_width + 8)
        y = y_offset + row * (panel_height + 8)
        
        panel = create_init_only_panel(
            task_id=task_id,
            task_description=data["task_description"],
            init_images=data.get("init_images", []),
            panel_width=panel_width,
            img_size=img_size,
        )
        grid.paste(panel, (x, y))
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    grid.save(str(output_path), quality=95)
    return str(output_path)


def load_er_task_data(suite_name: str) -> dict:
    """Load task data from existing rendered images for ER suites."""
    suite_dir = RENDERED_DIR / suite_name
    bddl_dir = BDDL_DIR / suite_name
    
    bddl_files = sorted(bddl_dir.glob("*.bddl"))
    bddl_map = {i: f for i, f in enumerate(bddl_files)}
    
    task_data = {}
    
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
        
        task_data[task_id] = {
            "task_name": bddl_file.stem,
            "task_description": task_description,
            "init_images": [str(img) for img in init_images],
        }
    
    return task_data


def main():
    print("Generating init-only visualizations for ER suites")
    print("=" * 60)
    
    for suite_name in ER_SUITES:
        print(f"\nProcessing: {suite_name}")
        
        suite_dir = RENDERED_DIR / suite_name
        if not suite_dir.exists():
            print(f"  Skipping: rendered images not found at {suite_dir}")
            continue
        
        task_data = load_er_task_data(suite_name)
        
        if not task_data:
            print(f"  No tasks found for {suite_name}")
            continue
        
        print(f"  Found {len(task_data)} tasks")
        
        output_path = OUTPUT_DIR / f"{suite_name}_init_grid.png"
        
        create_init_only_grid(
            task_data=task_data,
            output_path=output_path,
            suite_name=suite_name,
            cols=5,
        )
        
        file_size = output_path.stat().st_size / (1024 * 1024)
        print(f"  Saved: {output_path} ({file_size:.2f} MB)")
    
    print("\n" + "=" * 60)
    print(f"Done! Visualizations saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()





