"""
Offline visualization script for LIBERO evaluation outputs.

Given an input directory containing per-episode video and JSON logs produced by
eval.py / eval_parallel.py, this script:
  - loads each <episode>.mp4 and matching <episode>.json
  - for each frame, overlays:
      * the generated text on the right side of the frame
      * any bounding box / pointing annotations embedded in the text
  - writes a new video to <input_dir>/generated_text_visualization with the same
    base filename as the original episode video.

Usage:
    python eval/visualize_evaluation_output.py --args.input-dir data/libero/videos
"""

from __future__ import annotations

import dataclasses
import json
import logging
import pathlib
import re
from typing import Dict, List, Tuple

import cv2
import imageio
import numpy as np
import tqdm
import tyro


LOGGER = logging.getLogger(__name__)


def _wrap_text_to_width(
    text: str,
    font_scale: float,
    line_thickness: int,
    max_width_px: int,
) -> List[str]:
    """Word-wrap text so that each line fits within max_width_px (in pixels).

    Uses cv2.getTextSize to measure rendered width, so text stays inside the panel.
    """
    if not text:
        return []

    words = text.split()
    if not words:
        return []

    lines: List[str] = []
    current = words[0]
    for w in words[1:]:
        candidate = current + " " + w
        (size, _) = cv2.getTextSize(
            candidate, cv2.FONT_HERSHEY_SIMPLEX, font_scale, line_thickness
        )
        if size[0] <= max_width_px:
            current = candidate
        else:
            lines.append(current)
            current = w
    if current:
        lines.append(current)
    return lines


def _extract_slow_text(full_text: str) -> str:
    """Return the part of generated text before the 'FAST:' / 'Fast:' marker, if present."""
    if not full_text:
        return ""
    text = str(full_text)
    for marker in ("FAST:", "Fast:"):
        idx = text.find(marker)
        if idx != -1:
            return text[:idx].strip()
    return text.strip()


def _parse_annotations(full_text: str) -> Tuple[List[Tuple[Tuple[int, int], Tuple[int, int]]], List[Tuple[int, int]]]:
    """Parse bounding box and pointing annotations from generated text.

    Supports patterns like:
      - 'bounding box: "basket": "[[14, 106], [75, 163]]"'
      - 'Bounding box: ...'
      - 'pointing: 295 440 291 322 299 439 323 444'

    Returns:
      bboxes: list of ((x1, y1), (x2, y2))
      points: list of (x, y)
    """
    if not full_text:
        return [], []

    text = str(full_text)
    lower = text.lower()
    bboxes: List[Tuple[Tuple[int, int], Tuple[int, int]]] = []
    points: List[Tuple[int, int]] = []

    # --------- Parse bounding boxes ----------
    bbox_markers = ["bounding box:", "bounding boxes:", "bbox:"]
    for marker in bbox_markers:
        idx = lower.find(marker)
        if idx == -1:
            continue
        sub = text[idx + len(marker) :]
        pattern = r"\[\s*\[\s*(\d+)\s*,\s*(\d+)\s*],\s*\[\s*(\d+)\s*,\s*(\d+)\s*]]"
        for m in re.finditer(pattern, sub):
            x1, y1, x2, y2 = map(int, m.groups())
            bboxes.append(((x1, y1), (x2, y2)))
        break

    # --------- Parse pointing coordinates ----------
    point_markers = ["pointing:", "Pointing:"]
    for marker in point_markers:
        idx = lower.find(marker.lower())
        if idx == -1:
            continue
        end_idx = len(text)
        for end_marker in ("FAST:", "Fast:"):
            j = lower.find(end_marker.lower(), idx)
            if j != -1:
                end_idx = j
                break
        sub = text[idx + len(marker) : end_idx]
        nums = [int(m.group(0)) for m in re.finditer(r"\d+", sub)]
        for i in range(0, len(nums) - 1, 2):
            points.append((nums[i], nums[i + 1]))
        break

    return bboxes, points


def _render_text_panel(
    text: str,
    height: int,
    width: int,
    *,
    font_scale: float = 0.5,
    line_thickness: int = 1,
) -> np.ndarray:
    """Render a simple white text panel of shape [H, W, 3] using OpenCV."""
    panel = np.full((height, width, 3), 255, dtype=np.uint8)
    if not text:
        return panel

    left_margin = 10
    right_margin = 10
    max_text_width = max(10, width - left_margin - right_margin)

    lines = _wrap_text_to_width(
        text=text,
        font_scale=font_scale,
        line_thickness=line_thickness,
        max_width_px=max_text_width,
    )

    (text_size, _) = cv2.getTextSize(
        "Ag", cv2.FONT_HERSHEY_SIMPLEX, font_scale, line_thickness
    )
    text_height = text_size[1]
    line_spacing = int(0.4 * text_height)
    line_height = text_height + line_spacing

    top_margin = 20
    bottom_margin = 10
    y = top_margin

    max_lines = max(
        1, (height - top_margin - bottom_margin) // max(line_height, 1)
    )
    lines = lines[:max_lines]

    for line in lines:
        cv2.putText(
            panel,
            line,
            (left_margin, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            (0, 0, 0),
            line_thickness,
            cv2.LINE_AA,
        )
        y += line_height

    return panel


def _draw_annotations_on_image(
    img: np.ndarray,
    bboxes: List[Tuple[Tuple[int, int], Tuple[int, int]]],
    points: List[Tuple[int, int]],
    bbox_color=(0, 255, 0),
    point_color=(0, 0, 255),
) -> np.ndarray:
    """Draw bounding boxes and pointing points on a copy of the image."""
    if img is None:
        return img
    annotated = img.copy()
    h, w = annotated.shape[:2]

    for (x1, y1), (x2, y2) in bboxes:
        x1 = max(0, min(w - 1, int(x1)))
        x2 = max(0, min(w - 1, int(x2)))
        y1 = max(0, min(h - 1, int(y1)))
        y2 = max(0, min(h - 1, int(y2)))
        cv2.rectangle(annotated, (x1, y1), (x2, y2), bbox_color, 2)

    if points:
        pts = []
        for x, y in points:
            x = max(0, min(w - 1, int(x)))
            y = max(0, min(h - 1, int(y)))
            pts.append((x, y))
            cv2.circle(annotated, (x, y), 3, point_color, -1)
        if len(pts) >= 2:
            cv2.polylines(
                annotated,
                [np.array(pts, dtype=np.int32)],
                isClosed=False,
                color=point_color,
                thickness=1,
            )

    return annotated


def _compose_image_with_text(img: np.ndarray, text: str) -> np.ndarray:
    """Compose a side-by-side frame: left=image, right=text panel."""
    h, w = img.shape[:2]
    text_panel = _render_text_panel(text, h, w)
    return np.concatenate([img, text_panel], axis=1)


@dataclasses.dataclass
class Args:
    """Arguments for offline visualization."""

    input_dir: str = "data/libero/videos"
    fps: int = 60


def visualize_episode(json_path: pathlib.Path, args: Args, out_dir: pathlib.Path) -> None:
    """Visualize a single episode given its JSON log and corresponding video."""
    with json_path.open("r", encoding="utf-8") as f:
        meta = json.load(f)

    steps = meta.get("steps", [])
    if not steps:
        LOGGER.warning("No steps found in %s, skipping", json_path)
        return

    video_path = json_path.with_suffix(".mp4")
    if not video_path.exists():
        LOGGER.warning("Video file %s not found for JSON %s, skipping", video_path, json_path)
        return

    out_dir.mkdir(parents=True, exist_ok=True)
    out_video_path = out_dir / video_path.name

    reader = imageio.get_reader(str(video_path))
    writer = imageio.get_writer(str(out_video_path), fps=args.fps)

    try:
        for idx, frame in enumerate(reader):
            if idx >= len(steps):
                break
            entry = steps[idx]
            full_text = entry.get("generated_text")
            slow_text = _extract_slow_text(full_text) if full_text else ""
            bboxes, points = _parse_annotations(full_text) if full_text else ([], [])

            frame_rgb = np.asarray(frame)
            frame_annotated = _draw_annotations_on_image(frame_rgb, bboxes, points)
            composed = _compose_image_with_text(frame_annotated, slow_text)
            writer.append_data(composed)
    finally:
        writer.close()
        reader.close()

    LOGGER.info("Wrote visualization: %s", out_video_path)


def main(args: Args) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    input_dir = pathlib.Path(args.input_dir)
    out_dir = input_dir / "generated_text_visualization"

    json_files = sorted(input_dir.glob("*.json"))
    if not json_files:
        LOGGER.warning("No JSON files found in %s", input_dir)
        return

    for json_path in tqdm.tqdm(json_files, desc="Episodes"):
        visualize_episode(json_path, args, out_dir)


if __name__ == "__main__":
    tyro.cli(main)

