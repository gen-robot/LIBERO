"""
Offline visualization script for LIBERO segmentation npz files.

Given an input directory containing per-episode
`*.segmentation.npz` files (as produced in `data/libero/videos`),
this script:
  - loads each `<episode>.segmentation.npz`
  - for every array inside the npz (e.g. `agentview_segmentation_instance`)
    it renders a colored mask video where each instance id gets a
    consistent color across the whole episode
  - reads the matching `<episode>.json` file (if present) to obtain
    id ↔ object-name mappings
  - writes visualization videos to:
        <input_dir>/seg_vis_output
    with filenames like:
        <episode>_<array_name_sanitized>.mp4

Each visualization frame contains:
  - left: colored segmentation mask
  - right: large white legend panel, listing the color → object-name mapping.

Notes:
  - Background (id == 0) is rendered as black.
  - Colors are deterministic per instance id (so the same id keeps
    the same color across frames).

Usage example:
    python eval/visualize_segmentation.py --args.input-dir data/libero/videos
"""

from __future__ import annotations

import dataclasses
import json
import logging
import pathlib
from typing import Dict, List

import cv2
import imageio
import numpy as np
import tqdm
import tyro


LOGGER = logging.getLogger(__name__)


@dataclasses.dataclass
class Args:
    """Arguments for segmentation visualization."""

    # Directory that contains *.segmentation.npz files.
    input_dir: str = "data/libero/videos"
    # FPS of the output videos.
    fps: int = 60


def _build_color_map(instance_ids: np.ndarray) -> np.ndarray:
    """Build a deterministic color map for the given instance ids.

    Returns:
        color_map: np.ndarray of shape [max_id + 1, 3], dtype uint8
                   where color_map[id] is the RGB color for that id.
                   Id 0 is reserved for background (black).
    """
    if instance_ids.size == 0:
        return np.zeros((1, 3), dtype=np.uint8)

    max_id = int(instance_ids.max())
    if max_id < 0:
        return np.zeros((1, 3), dtype=np.uint8)

    color_map = np.zeros((max_id + 1, 3), dtype=np.uint8)

    # Simple hash-based deterministic color mapping.
    for idx in range(1, max_id + 1):
        # Use different multipliers to spread values in RGB space.
        r = (37 * idx) % 256
        g = (17 * idx) % 256
        b = (97 * idx) % 256
        # Avoid very dark colors to keep them visible.
        if r < 32 and g < 32 and b < 32:
            r = (r + 64) % 256
            g = (g + 64) % 256
            b = (b + 64) % 256
        color_map[idx] = (r, g, b)

    # id == 0 stays as pure black background.
    return color_map


def _sanitize_key_name(key: str) -> str:
    """Sanitize npz key name for use in filenames."""
    name = key
    # Strip common suffix to shorten filenames.
    if name.endswith("_segmentation_instance"):
        name = name[: -len("_segmentation_instance")]
    # Replace any remaining problematic characters just in case.
    for ch in ("/", "\\", " ", ":"):
        name = name.replace(ch, "_")
    return name


def _render_legend_panel(
    unique_ids: np.ndarray,
    color_map: np.ndarray,
    id_to_name: Dict[int, str],
    height: int,
    width: int,
) -> np.ndarray:
    """Render a legend panel (white background) mapping colors to object names.

    Args:
        unique_ids: 1D array of instance ids present in the episode.
        color_map: [max_id+1, 3] color lookup table.
        id_to_name: Mapping from instance id to object name.
        height: Panel height (matches segmentation image height).
        width: Panel width (we use same as segmentation width to get large area).
    """
    panel = np.full((height, width, 3), 255, dtype=np.uint8)

    # Skip background id 0 in legend.
    ids = [i for i in unique_ids.tolist() if i != 0]
    if not ids:
        return panel

    # Legend layout: one column, each row has a color box + text.
    # If too many entries, they will be clipped at the bottom; but LIBERO
    # typically has only a handful of instances, so this is sufficient.
    left_margin = 20
    top_margin = 20
    box_size = 16

    # Estimate line height from font metrics.
    font_scale = 0.5
    line_thickness = 1
    (text_size, _) = cv2.getTextSize(
        "Ag", cv2.FONT_HERSHEY_SIMPLEX, font_scale, line_thickness
    )
    text_height = text_size[1]
    line_spacing = int(0.6 * text_height)
    line_height = max(box_size, text_height) + line_spacing

    y = top_margin
    for seg_id in ids:
        if y + line_height > height - 5:
            break  # avoid drawing off the panel
        color = tuple(int(c) for c in color_map[seg_id])
        name = id_to_name.get(seg_id, f"id={seg_id}")

        # Draw color box
        pt1 = (left_margin, y)
        pt2 = (left_margin + box_size, y + box_size)
        cv2.rectangle(panel, pt1, pt2, color, thickness=-1)
        cv2.rectangle(panel, pt1, pt2, (0, 0, 0), thickness=1)

        # Draw text to the right of the color box
        text_x = pt2[0] + 10
        text_y = y + box_size - 4
        cv2.putText(
            panel,
            name,
            (text_x, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            (0, 0, 0),
            line_thickness,
            cv2.LINE_AA,
        )

        y += line_height

    return panel


def _visualize_single_array(
    seg: np.ndarray,
    out_video_path: pathlib.Path,
    fps: int,
    id_to_name: Dict[int, str],
) -> None:
    """Render a single segmentation array into a colored mask video with legend."""
    # seg expected shape: [T, H, W] or [T, H, W, 1]
    if seg.ndim == 4 and seg.shape[-1] == 1:
        seg = seg[..., 0]
    if seg.ndim != 3:
        LOGGER.warning(
            "Unexpected segmentation array shape %s for %s, skipping",
            seg.shape,
            out_video_path,
        )
        return

    seg = seg.astype(np.int64)
    unique_ids = np.unique(seg)
    if unique_ids.size == 0:
        LOGGER.warning("Empty segmentation for %s, skipping", out_video_path)
        return

    color_map = _build_color_map(unique_ids)

    T, H, W = seg.shape

    # Precompute legend panel (same for all frames).
    legend_panel = _render_legend_panel(unique_ids, color_map, id_to_name, H, W)
    out_video_path.parent.mkdir(parents=True, exist_ok=True)
    writer = imageio.get_writer(str(out_video_path), fps=fps)

    try:
        for t in range(T):
            frame_ids = seg[t]
            # Map instance ids to colors with direct indexing.
            frame_rgb = color_map[frame_ids].astype(np.uint8)
            # Compose final frame: left = segmentation, right = legend.
            frame_out = np.concatenate([frame_rgb, legend_panel], axis=1)
            writer.append_data(frame_out)
    finally:
        writer.close()

    LOGGER.info("Wrote segmentation visualization: %s", out_video_path)


def visualize_segmentation_file(
    seg_path: pathlib.Path,
    args: Args,
    out_dir: pathlib.Path,
) -> None:
    """Visualize one *.segmentation.npz file."""
    try:
        npz: Dict[str, np.ndarray] = np.load(seg_path)
    except Exception as exc:  # pylint: disable=broad-except
        LOGGER.warning("Failed to load %s: %s", seg_path, exc)
        return

    if not npz.files:
        LOGGER.warning("No arrays found in %s, skipping", seg_path)
        return

    base_name = seg_path.name
    if base_name.endswith(".segmentation.npz"):
        base_name = base_name[: -len(".segmentation.npz")]
    else:
        base_name = seg_path.stem

    # Load corresponding JSON to get id ↔ instance-name mapping (if available).
    json_path = seg_path.with_name(base_name + ".json")
    id_to_name: Dict[int, str] = {}
    if json_path.exists():
        try:
            with json_path.open("r", encoding="utf-8") as f:
                meta = json.load(f)
            raw_map = meta.get("segmentation_id_to_instance", {}) or {}
            for k, v in raw_map.items():
                try:
                    seg_id = int(k)
                except (TypeError, ValueError):
                    continue
                id_to_name[seg_id] = str(v)
        except Exception as exc:  # pylint: disable=broad-except
            LOGGER.warning("Failed to load id mapping from %s: %s", json_path, exc)

    for key in npz.files:
        seg = npz[key]
        key_name = _sanitize_key_name(key)
        out_video_path = out_dir / f"{base_name}_{key_name}.mp4"
        _visualize_single_array(seg, out_video_path, fps=args.fps, id_to_name=id_to_name)


def main(args: Args) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    input_dir = pathlib.Path(args.input_dir)
    if not input_dir.exists():
        LOGGER.error("Input directory does not exist: %s", input_dir)
        return

    out_dir = input_dir / "seg_vis_output"

    seg_files = sorted(input_dir.glob("*.segmentation.npz"))
    if not seg_files:
        LOGGER.warning("No *.segmentation.npz files found in %s", input_dir)
        return

    for seg_path in tqdm.tqdm(seg_files, desc="Segmentation episodes"):
        visualize_segmentation_file(seg_path, args, out_dir)


if __name__ == "__main__":
    tyro.cli(main)
