"""
Compute CoT grounding accuracy (bbox + pointing) for LIBERO evaluation outputs.

This script reads the per-episode JSON logs produced by `eval.py` / `eval_parallel.py`
and the matching segmentation files:

  - `<episode>.json`
  - `<episode>.segmentation.npz`

It parses `generated_text` for CoT annotations like:
  - `bbox: "orange juice": "[[29, 123], [63, 159]]"`
  - `bounding box: "basket": "[[...], [...]]"`
  - `pointing: "orange juice": "[204, 156]"`

Then it validates:
  - bbox: IoU(pred_bbox, gt_bbox_from_segmentation) > threshold (default 0.8)
  - pointing: (x, y) falls inside the GT mask for that object

Object name resolution follows the requested rules:
  - Reverse-map the simplified names (after ':') back to LIBERO names (before ':')
    using the provided replacements table.
  - If the model outputs only `bowl`, treat it as `black bowl`.
  - If the model outputs `drawer`, map it to the cabinet present in the scene.
  - If multiple instances exist, always use the `_1` instance.

Outputs:
  - Per-episode detailed JSON: `<out_dir>/<episode>.cot_grounding_eval.json`
  - Folder summary JSON: `<out_dir>/cot_grounding_summary.json`
"""

from __future__ import annotations

import dataclasses
import json
import logging
import pathlib
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
import tqdm
import tyro

LOGGER = logging.getLogger(__name__)


def _extract_slow_text(full_text: str) -> str:
    """Return the part of generated text before the 'FAST:' / 'Fast:' marker, if present."""
    if not full_text:
        return ""
    text = str(full_text)
    lower = text.lower()
    for marker in ("fast:",):
        idx = lower.find(marker)
        if idx != -1:
            return text[:idx].strip()
    return text.strip()


def normalize_seg_name(name: str) -> str:
    """Normalize an object name for fuzzy matching (letters only, lowercase)."""
    name = str(name).lower()
    name = re.sub(r"\d+", "", name)  # remove digits
    name = re.sub(r"[^a-z]+", " ", name)  # non-alpha -> space
    return " ".join(name.split())


def _build_reverse_replacements() -> Dict[str, List[str]]:
    """
    Build reverse mapping: normalized(simplified_name) -> list[original_name].

    Requested behavior: map the string after ':' back to the string before ':'.
    """
    replacements = {
        "akita black bowl": "black bowl",
        "porcelain mug": "white mug",
        "white cabinet": "cabinet",
        "wine rank": "rank",
        "wooden cabinet": "cabinet",
        "wooden two layer shelf": "shelf",
        "chefmate 8 frypan": "frying pan",
        "new salad dressing": "salad dressing",
        "red coffee mug": "red mug",
        "wooden tray": "tray",
        "black book": "book",
        "yellow book": "book",
        "desk caddy": "caddy",
        "flat stove": "stove",
    }

    rev: Dict[str, List[str]] = {}
    for original, simplified in replacements.items():
        key = normalize_seg_name(simplified)
        if not key:
            continue
        rev.setdefault(key, []).append(original)
    return rev


def _split_instance_key(name: str) -> Tuple[str, Optional[int]]:
    """Split a segmentation instance name like `orange_juice_1` into (`orange_juice`, 1)."""
    m = re.match(r"^(.*)_(\d+)$", str(name))
    if not m:
        return str(name), None
    return m.group(1), int(m.group(2))


@dataclasses.dataclass(frozen=True)
class _ResolvedInstance:
    base_name: str
    instance_key: str
    seg_id: int
    reason: Optional[str] = None


def _choose_instance_key(keys: Iterable[str]) -> Optional[str]:
    """Choose instance `_1` if present; otherwise the smallest numeric suffix."""
    keys_list = [str(k) for k in keys if isinstance(k, str) and k]
    if not keys_list:
        return None
    for k in keys_list:
        _base, num = _split_instance_key(k)
        if num == 1:
            return k
    keyed: List[Tuple[int, str]] = []
    for k in keys_list:
        _base, num = _split_instance_key(k)
        keyed.append(((num if num is not None else 10**9), k))
    keyed.sort()
    return keyed[0][1]


def _resolve_predicted_object_to_seg_instance(
    predicted_obj_name: str,
    seg_name_to_id: Dict[str, Any],
    *,
    reverse_replacements: Dict[str, List[str]],
) -> Optional[_ResolvedInstance]:
    """Resolve a predicted object name to a segmentation instance id in the scene."""
    if not predicted_obj_name or not isinstance(seg_name_to_id, dict) or not seg_name_to_id:
        return None

    norm_pred = normalize_seg_name(predicted_obj_name)
    if not norm_pred:
        return None

    # Special-case rules from the request.
    if norm_pred == "bowl":
        norm_pred = normalize_seg_name("black bowl")

    is_drawer = norm_pred == "drawer"
    if is_drawer:
        norm_pred = normalize_seg_name("cabinet")

    # Build scene indices.
    base_to_keys: Dict[str, List[str]] = {}
    norm_base_to_bases: Dict[str, List[str]] = {}
    for inst_key in seg_name_to_id.keys():
        if not isinstance(inst_key, str) or not inst_key:
            continue
        base, _num = _split_instance_key(inst_key)
        base_to_keys.setdefault(base, []).append(inst_key)
        norm_base = normalize_seg_name(base.replace("_", " "))
        if norm_base:
            norm_base_to_bases.setdefault(norm_base, []).append(base)

    def _pick_base(bases: List[str]) -> Optional[str]:
        if not bases:
            return None
        # Prefer bases that have an `_1` instance.
        scored: List[Tuple[int, str]] = []
        for b in sorted(set(bases)):
            keys = base_to_keys.get(b, [])
            has_1 = any(_split_instance_key(k)[1] == 1 for k in keys)
            scored.append(((0 if has_1 else 1), b))
        scored.sort()
        return scored[0][1]

    chosen_base: Optional[str] = None

    # 1) Direct match to a scene base name.
    if norm_pred in norm_base_to_bases:
        chosen_base = _pick_base(norm_base_to_bases[norm_pred])

    # 2) Reverse mapping: simplified -> original, then match original to scene.
    if chosen_base is None and norm_pred in reverse_replacements:
        for original in reverse_replacements[norm_pred]:
            norm_original = normalize_seg_name(original)
            if not norm_original:
                continue
            if norm_original in norm_base_to_bases:
                chosen_base = _pick_base(norm_base_to_bases[norm_original])
                if chosen_base is not None:
                    break

    # 3) Drawer/cabinet heuristic: pick any cabinet in the scene.
    if chosen_base is None and norm_pred == "cabinet":
        cabinet_candidates = [
            base
            for norm_base, bases in norm_base_to_bases.items()
            for base in bases
            if "cabinet" in norm_base.split()
        ]
        chosen_base = _pick_base(cabinet_candidates)

    # 4) Fuzzy containment match.
    if chosen_base is None:
        candidates: List[str] = []
        for norm_base, bases in norm_base_to_bases.items():
            if norm_pred in norm_base or norm_base in norm_pred:
                candidates.extend(bases)
        chosen_base = _pick_base(candidates)

    if chosen_base is None:
        return None

    chosen_instance_key = _choose_instance_key(base_to_keys.get(chosen_base, []))
    if chosen_instance_key is None:
        return None

    seg_id_raw = seg_name_to_id.get(chosen_instance_key)
    try:
        seg_id = int(seg_id_raw)
    except Exception:  # pylint: disable=broad-except
        return None

    reason = "drawer->cabinet" if is_drawer else None
    return _ResolvedInstance(
        base_name=chosen_base,
        instance_key=chosen_instance_key,
        seg_id=seg_id,
        reason=reason,
    )


def _parse_ints(text: str) -> List[int]:
    nums = re.findall(r"-?\d+(?:\.\d+)?", str(text))
    out: List[int] = []
    for n in nums:
        try:
            out.append(int(float(n)))
        except Exception:  # pylint: disable=broad-except
            continue
    return out


def _parse_bbox_annotations(text: str) -> List[Dict[str, Any]]:
    """Return a list of bbox annotations with `obj` and `bbox`."""
    slow = _extract_slow_text(text)
    if not slow:
        return []

    patterns = [
        re.compile(
            r'(?P<prefix>bbox|bounding box(?:es)?)\s*:\s*"(?P<obj>[^"]+)"\s*:\s*"(?P<coords>[^"]+)"',
            flags=re.IGNORECASE,
        ),
        re.compile(
            r'(?P<prefix>bbox|bounding box(?:es)?)\s*:\s*"(?P<obj>[^"]+)"\s*:\s*(?P<coords>\[\[.*?\]\])',
            flags=re.IGNORECASE,
        ),
        re.compile(
            r"(?P<prefix>bbox|bounding box(?:es)?)\s*:\s*(?P<obj>[a-zA-Z0-9 _-]+?)\s*:\s*(?P<coords>\[\[.*?\]\])",
            flags=re.IGNORECASE,
        ),
    ]

    out: List[Dict[str, Any]] = []
    for pat in patterns:
        for m in pat.finditer(slow):
            obj = (m.group("obj") or "").strip()
            coords_str = (m.group("coords") or "").strip()
            nums = _parse_ints(coords_str)
            record: Dict[str, Any] = {
                "raw_obj": obj,
                "raw_coords": coords_str,
                "pred_bbox_xyxy": None,
                "parse_ok": False,
            }
            if len(nums) >= 4:
                x1, y1, x2, y2 = nums[:4]
                record["pred_bbox_xyxy"] = [x1, y1, x2, y2]
                record["parse_ok"] = True
            out.append(record)
        if out:
            break  # first matching pattern wins to avoid duplicates
    return out


def _parse_pointing_annotations(text: str) -> List[Dict[str, Any]]:
    """Return a list of pointing annotations with `obj` and `point`."""
    slow = _extract_slow_text(text)
    if not slow:
        return []

    patterns = [
        re.compile(
            r'pointing\s*:\s*"(?P<obj>[^"]+)"\s*:\s*"(?P<coords>[^"]+)"',
            flags=re.IGNORECASE,
        ),
        re.compile(
            r'pointing\s*:\s*"(?P<obj>[^"]+)"\s*:\s*(?P<coords>\[[^\]]*\])',
            flags=re.IGNORECASE,
        ),
    ]

    out: List[Dict[str, Any]] = []
    for pat in patterns:
        for m in pat.finditer(slow):
            obj = (m.group("obj") or "").strip()
            coords_str = (m.group("coords") or "").strip()
            nums = _parse_ints(coords_str)
            record: Dict[str, Any] = {
                "raw_obj": obj,
                "raw_coords": coords_str,
                "pred_point_xy": None,
                "parse_ok": False,
            }
            if len(nums) >= 2:
                x, y = nums[:2]
                record["pred_point_xy"] = [x, y]
                record["parse_ok"] = True
            out.append(record)
        if out:
            break
    return out


def _compute_bbox_from_segmentation(seg_frame: np.ndarray, seg_id: int) -> Optional[List[int]]:
    """Compute bbox [x1,y1,x2,y2] from a single-frame segmentation mask."""
    if seg_frame.ndim == 3 and seg_frame.shape[-1] == 1:
        seg_frame = seg_frame[..., 0]
    seg = np.asarray(seg_frame)
    ys, xs = np.where(seg == int(seg_id))
    if ys.size == 0:
        return None
    x1, x2 = int(xs.min()), int(xs.max())
    y1, y2 = int(ys.min()), int(ys.max())
    return [x1, y1, x2, y2]


def _iou_xyxy(a: List[int], b: List[int]) -> float:
    """IoU for integer xyxy boxes using inclusive pixel bounds."""
    ax1, ay1, ax2, ay2 = [int(v) for v in a]
    bx1, by1, bx2, by2 = [int(v) for v in b]
    ax1, ax2 = (ax1, ax2) if ax1 <= ax2 else (ax2, ax1)
    ay1, ay2 = (ay1, ay2) if ay1 <= ay2 else (ay2, ay1)
    bx1, bx2 = (bx1, bx2) if bx1 <= bx2 else (bx2, bx1)
    by1, by2 = (by1, by2) if by1 <= by2 else (by2, by1)

    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw = max(0, ix2 - ix1 + 1)
    ih = max(0, iy2 - iy1 + 1)
    inter = float(iw * ih)
    area_a = float(max(0, ax2 - ax1 + 1) * max(0, ay2 - ay1 + 1))
    area_b = float(max(0, bx2 - bx1 + 1) * max(0, by2 - by1 + 1))
    denom = area_a + area_b - inter
    if denom <= 0:
        return 0.0
    return inter / denom


def _point_in_mask(seg_frame: np.ndarray, seg_id: int, x: int, y: int) -> bool:
    if seg_frame.ndim == 3 and seg_frame.shape[-1] == 1:
        seg_frame = seg_frame[..., 0]
    seg = np.asarray(seg_frame)
    h, w = seg.shape[:2]
    x_i, y_i = int(x), int(y)
    if x_i < 0 or y_i < 0 or x_i >= w or y_i >= h:
        return False
    return int(seg[y_i, x_i]) == int(seg_id)


@dataclasses.dataclass
class Args:
    """Arguments for CoT grounding accuracy computation."""

    input_dir: str
    output_dir: Optional[str] = None
    out_dir_name: str = "cot_grounding_eval"
    seg_key: str = "agentview_segmentation_instance"
    bbox_iou_threshold: float = 0.8


def _evaluate_episode(
    json_path: pathlib.Path,
    *,
    args: Args,
    reverse_replacements: Dict[str, List[str]],
) -> Optional[Dict[str, Any]]:
    seg_path = json_path.with_suffix(".segmentation.npz")
    if not seg_path.exists():
        LOGGER.warning("Missing segmentation for %s", json_path.name)
        return None

    try:
        meta = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception as exc:  # pylint: disable=broad-except
        LOGGER.warning("Failed to read %s: %s", json_path, exc)
        return None

    steps = meta.get("steps", [])
    if not isinstance(steps, list) or not steps:
        LOGGER.warning("No steps found in %s", json_path.name)
        return None

    seg_name_to_id = meta.get("segmentation_instance_to_id") or {}
    if not isinstance(seg_name_to_id, dict) or not seg_name_to_id:
        LOGGER.warning("No segmentation_instance_to_id in %s", json_path.name)
        return None

    try:
        npz = np.load(seg_path)
    except Exception as exc:  # pylint: disable=broad-except
        LOGGER.warning("Failed to load %s: %s", seg_path.name, exc)
        return None

    try:
        if args.seg_key not in npz.files:
            LOGGER.warning(
                "Seg key %s not found in %s (available=%s)",
                args.seg_key,
                seg_path.name,
                npz.files,
            )
            return None

        seg_arr = npz[args.seg_key]
        if seg_arr.ndim == 4 and seg_arr.shape[-1] == 1:
            seg_arr = seg_arr[..., 0]
        if seg_arr.ndim != 3:
            LOGGER.warning("Unexpected seg shape %s in %s", seg_arr.shape, seg_path.name)
            return None

        T = int(seg_arr.shape[0])

        bbox_total = 0
        bbox_correct = 0
        point_total = 0
        point_correct = 0

        step_results: List[Dict[str, Any]] = []
        for i, step in enumerate(steps):
            if not isinstance(step, dict):
                continue
            t = step.get("t", i)
            try:
                t_i = int(t)
            except Exception:  # pylint: disable=broad-except
                t_i = i
            if t_i < 0 or t_i >= T:
                t_i = min(max(i, 0), T - 1)

            seg_frame = seg_arr[t_i]
            gen_text = step.get("generated_text", "")

            bboxes = _parse_bbox_annotations(gen_text)
            points = _parse_pointing_annotations(gen_text)

            bbox_eval: List[Dict[str, Any]] = []
            for bb in bboxes:
                bbox_total += 1
                record = dict(bb)
                record.update(
                    {
                        "t": t_i,
                        "mapped_instance_key": None,
                        "mapped_seg_id": None,
                        "gt_bbox_xyxy": None,
                        "iou": None,
                        "correct": False,
                        "error": None,
                    }
                )

                if not record.get("parse_ok"):
                    record["error"] = "bbox_parse_failed"
                    bbox_eval.append(record)
                    continue

                resolved = _resolve_predicted_object_to_seg_instance(
                    record.get("raw_obj", ""),
                    seg_name_to_id,
                    reverse_replacements=reverse_replacements,
                )
                if resolved is None:
                    record["error"] = "object_mapping_failed"
                    bbox_eval.append(record)
                    continue

                record["mapped_instance_key"] = resolved.instance_key
                record["mapped_seg_id"] = resolved.seg_id
                record["mapping_reason"] = resolved.reason

                gt_bbox = _compute_bbox_from_segmentation(seg_frame, resolved.seg_id)
                if gt_bbox is None:
                    record["error"] = "gt_mask_empty"
                    bbox_eval.append(record)
                    continue

                record["gt_bbox_xyxy"] = gt_bbox
                iou = _iou_xyxy(record["pred_bbox_xyxy"], gt_bbox)
                record["iou"] = float(iou)
                is_correct = iou > float(args.bbox_iou_threshold)
                record["correct"] = bool(is_correct)
                if is_correct:
                    bbox_correct += 1
                bbox_eval.append(record)

            point_eval: List[Dict[str, Any]] = []
            for pt in points:
                point_total += 1
                record = dict(pt)
                record.update(
                    {
                        "t": t_i,
                        "mapped_instance_key": None,
                        "mapped_seg_id": None,
                        "inside_mask": None,
                        "correct": False,
                        "error": None,
                    }
                )

                if not record.get("parse_ok"):
                    record["error"] = "point_parse_failed"
                    point_eval.append(record)
                    continue

                resolved = _resolve_predicted_object_to_seg_instance(
                    record.get("raw_obj", ""),
                    seg_name_to_id,
                    reverse_replacements=reverse_replacements,
                )
                if resolved is None:
                    record["error"] = "object_mapping_failed"
                    point_eval.append(record)
                    continue

                record["mapped_instance_key"] = resolved.instance_key
                record["mapped_seg_id"] = resolved.seg_id
                record["mapping_reason"] = resolved.reason

                x, y = record["pred_point_xy"]
                inside = _point_in_mask(seg_frame, resolved.seg_id, x, y)
                record["inside_mask"] = bool(inside)
                record["correct"] = bool(inside)
                if inside:
                    point_correct += 1
                point_eval.append(record)

            step_results.append(
                {
                    "t": t_i,
                    "has_bbox": bool(bbox_eval),
                    "has_pointing": bool(point_eval),
                    "bbox": bbox_eval,
                    "pointing": point_eval,
                }
            )

        def _acc(correct: int, total: int) -> Optional[float]:
            if total <= 0:
                return None
            return float(correct) / float(total)

        summary = {
            "episode": json_path.stem,
            "json_path": str(json_path),
            "segmentation_path": str(seg_path),
            "num_steps": len(step_results),
            "bbox": {
                "correct": bbox_correct,
                "total": bbox_total,
                "acc": _acc(bbox_correct, bbox_total),
                "iou_threshold": float(args.bbox_iou_threshold),
            },
            "pointing": {
                "correct": point_correct,
                "total": point_total,
                "acc": _acc(point_correct, point_total),
            },
            "combined": {
                "correct": bbox_correct + point_correct,
                "total": bbox_total + point_total,
                "acc": _acc(bbox_correct + point_correct, bbox_total + point_total),
            },
        }

        return {
            "meta": {
                "task_id": meta.get("task_id"),
                "episode_idx": meta.get("episode_idx"),
                "task_description": meta.get("task_description"),
            },
            "summary": summary,
            "steps": step_results,
        }
    finally:
        try:
            npz.close()
        except Exception:  # pylint: disable=broad-except
            pass


def main(args: Args) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    input_dir = pathlib.Path(args.input_dir)
    if not input_dir.exists():
        raise FileNotFoundError(f"input_dir not found: {input_dir}")

    if args.output_dir:
        out_dir = pathlib.Path(args.output_dir)
    else:
        out_dir = input_dir / args.out_dir_name
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        # Some evaluation output folders can be read-only (e.g., shared checkpoints).
        fallback = pathlib.Path.cwd() / args.out_dir_name / input_dir.name
        fallback.mkdir(parents=True, exist_ok=True)
        LOGGER.warning("Cannot write to %s; writing outputs to %s instead", out_dir, fallback)
        out_dir = fallback

    reverse_replacements = _build_reverse_replacements()

    json_paths = sorted(p for p in input_dir.glob("*.json") if p.is_file())
    if not json_paths:
        raise FileNotFoundError(f"No *.json files found in: {input_dir}")

    overall_bbox_total = 0
    overall_bbox_correct = 0
    overall_point_total = 0
    overall_point_correct = 0

    per_episode_summaries: List[Dict[str, Any]] = []

    for json_path in tqdm.tqdm(json_paths, desc="Evaluating episodes"):
        episode_result = _evaluate_episode(
            json_path,
            args=args,
            reverse_replacements=reverse_replacements,
        )
        if episode_result is None:
            continue

        ep_summary = episode_result["summary"]
        per_episode_summaries.append(ep_summary)

        overall_bbox_total += int(ep_summary["bbox"]["total"])
        overall_bbox_correct += int(ep_summary["bbox"]["correct"])
        overall_point_total += int(ep_summary["pointing"]["total"])
        overall_point_correct += int(ep_summary["pointing"]["correct"])

        out_path = out_dir / f"{json_path.stem}.cot_grounding_eval.json"
        out_path.write_text(
            json.dumps(episode_result, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _acc(correct: int, total: int) -> Optional[float]:
        if total <= 0:
            return None
        return float(correct) / float(total)

    summary = {
        "input_dir": str(input_dir),
        "output_dir": str(out_dir),
        "seg_key": args.seg_key,
        "bbox_iou_threshold": float(args.bbox_iou_threshold),
        "episodes_evaluated": len(per_episode_summaries),
        "overall": {
            "bbox": {
                "correct": overall_bbox_correct,
                "total": overall_bbox_total,
                "acc": _acc(overall_bbox_correct, overall_bbox_total),
            },
            "pointing": {
                "correct": overall_point_correct,
                "total": overall_point_total,
                "acc": _acc(overall_point_correct, overall_point_total),
            },
            "combined": {
                "correct": overall_bbox_correct + overall_point_correct,
                "total": overall_bbox_total + overall_point_total,
                "acc": _acc(
                    overall_bbox_correct + overall_point_correct,
                    overall_bbox_total + overall_point_total,
                ),
            },
        },
        "per_episode": per_episode_summaries,
    }

    (out_dir / "cot_grounding_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    LOGGER.info("Wrote per-episode results to: %s", out_dir)
    LOGGER.info("Wrote summary to: %s", out_dir / "cot_grounding_summary.json")


if __name__ == "__main__":
    tyro.cli(main)
