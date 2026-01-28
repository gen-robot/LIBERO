#!/usr/bin/env python3
"""
Render LIBERO / ER BDDL files into an image + segmentation dataset.

For each sampled initial state (seed), this script saves 3 files (similar to eval/eval.py):
  1) `<stem>.png`                 : RGB image from `--primary-camera`
  2) `<stem>.segmentation.npz`    : segmentation mask(s) from obs keys containing "seg"
  3) `<stem>.json`                : metadata + segmentation id↔name mapping

Typical usage:
  MUJOCO_GL=egl python er_extension/generate_er_dataset.py \
    --input-dir libero/libero/bddl_files \
    --output-dir data/er_dataset \
    --num-seed 5
"""

from __future__ import annotations

import argparse
import gc
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np


LIBERO_DUMMY_ACTION = [0.0] * 6 + [-1.0]

# Allow running as a script without installing the package.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def _safe_close_env(env) -> None:
    if env is not None:
        try:
            env.close()
        except Exception:
            pass
        del env
    gc.collect()
    time.sleep(0.1)


def _swap_left_right(instruction: str) -> str:
    instruction = instruction.replace(" left ", " __LEFT__ ")
    instruction = instruction.replace(" right ", " __RIGHT__ ")
    instruction = instruction.replace(" __LEFT__ ", " right ")
    instruction = instruction.replace(" __RIGHT__ ", " left ")
    return instruction


def _collect_bddl_files(input_path: Path) -> List[Path]:
    if input_path.is_file():
        if input_path.suffix != ".bddl":
            raise ValueError(f"Expected a .bddl file, got: {input_path}")
        return [input_path]
    return sorted(p for p in input_path.rglob("*.bddl") if p.is_file())


def _resolve_input_root(input_path: Path, bddl_file: Path) -> Path:
    if input_path.is_file():
        return input_path.parent
    return input_path


def _sanitize_rel_stem(rel_path_no_suffix: Path) -> str:
    # Keep deterministic, filesystem-friendly filenames.
    # Example: "er_object/er_object_01" -> "er_object__er_object_01"
    rel = str(rel_path_no_suffix).replace("\\", "/")
    rel = rel.replace("/", "__")
    rel = rel.replace(" ", "_")
    return rel


def _rotate180(arr: np.ndarray) -> np.ndarray:
    return np.ascontiguousarray(arr[::-1, ::-1])


def _extract_segmentation_items(
    obs: Dict[str, Any],
    *,
    primary_camera: str,
    include_all_cameras: bool,
) -> Dict[str, np.ndarray]:
    seg_items = {k: v for k, v in obs.items() if "seg" in k.lower()}
    if not seg_items:
        return {}

    if include_all_cameras:
        keep = seg_items
    else:
        cam_lower = primary_camera.lower()
        keep = {k: v for k, v in seg_items.items() if cam_lower in k.lower()}
        if not keep:
            # Fallback to a deterministic key, similar to eval/eval.py.
            k0 = sorted(seg_items.keys())[0]
            keep = {k0: seg_items[k0]}

    out: Dict[str, np.ndarray] = {}
    for k, v in keep.items():
        seg = np.asarray(v)
        if seg.ndim == 3 and seg.shape[-1] == 1:
            seg = seg[..., 0]
        if seg.ndim != 2:
            raise ValueError(f"Expected 2D segmentation mask for {k}, got shape {seg.shape}")
        out[k] = seg.astype(np.int32, copy=False)
    return out


def _build_segmentation_name_mappings(env) -> Tuple[Dict[str, int], Dict[str, str]]:
    seg_name_to_id: Dict[str, int] = {}
    seg_id_to_name: Dict[str, str] = {}

    if hasattr(env, "instance_to_id"):
        for name, seg_id in env.instance_to_id.items():
            seg_id_int = int(seg_id)
            seg_name_to_id[str(name)] = seg_id_int
            seg_id_to_name[str(seg_id_int)] = str(name)

    if hasattr(env, "segmentation_robot_id") and env.segmentation_robot_id is not None:
        robot_base_id = int(env.segmentation_robot_id)
        # In SegmentationRenderEnv, robot pixels are typically encoded as robot_id + 1.
        seg_id_to_name[str(robot_base_id + 1)] = "robot"

    return seg_name_to_id, seg_id_to_name


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Render BDDL files into an image+segmentation dataset")
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Directory containing BDDL files (recursively searched) or a single .bddl file",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Output directory (flat; each sample produces .png + .segmentation.npz + .json)",
    )
    parser.add_argument(
        "--num-seed",
        type=int,
        default=1,
        help="Number of initial states (seeds) to render per BDDL file",
    )
    parser.add_argument(
        "--base-seed",
        type=int,
        default=42,
        help="Base seed; actual seed = base_seed + idx * seed-stride",
    )
    parser.add_argument(
        "--seed-stride",
        type=int,
        default=100,
        help="Seed stride between consecutive samples for the same BDDL file",
    )
    parser.add_argument(
        "--resolution",
        type=int,
        default=256,
        help="Camera resolution for rendered images / segmentation",
    )
    parser.add_argument(
        "--primary-camera",
        type=str,
        default="agentview",
        help="Camera name whose RGB image is saved as .png (e.g. agentview)",
    )
    parser.add_argument(
        "--camera-names",
        type=str,
        nargs="*",
        default=["agentview", "robot0_eye_in_hand"],
        help="Camera names to enable in the environment",
    )
    parser.add_argument(
        "--stabilize-steps",
        type=int,
        default=10,
        help="Number of zero-action steps after reset before capturing the frame",
    )
    # Keep compatibility with older Python versions that don't have argparse.BooleanOptionalAction.
    parser.add_argument(
        "--rotate180",
        dest="rotate180",
        action="store_true",
        default=True,
        help="Rotate images/segmentations by 180° (default: enabled; matches eval/eval.py behavior)",
    )
    parser.add_argument(
        "--no-rotate180",
        dest="rotate180",
        action="store_false",
        help="Disable 180° rotation",
    )
    parser.add_argument(
        "--include-all-segmentation-cameras",
        dest="include_all_segmentation_cameras",
        action="store_true",
        default=False,
        help="Store all segmentation-related obs keys (default: primary camera only)",
    )
    parser.add_argument(
        "--primary-only-segmentation",
        dest="include_all_segmentation_cameras",
        action="store_false",
        help="Store segmentation keys for the primary camera only (default)",
    )
    parser.add_argument(
        "--overwrite",
        dest="overwrite",
        action="store_true",
        default=False,
        help="Overwrite existing outputs (default: skip existing samples)",
    )
    parser.add_argument(
        "--no-overwrite",
        dest="overwrite",
        action="store_false",
        help="Skip existing outputs (default)",
    )
    args = parser.parse_args()

    from libero.libero.envs import SegmentationRenderEnv

    bddl_files = _collect_bddl_files(args.input_dir)
    if not bddl_files:
        raise FileNotFoundError(f"No .bddl files found under: {args.input_dir}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Found {len(bddl_files)} BDDL files under {args.input_dir}")
    print(f"Writing outputs to {args.output_dir} (3 files per sample)")

    for bddl_idx, bddl_path in enumerate(bddl_files):
        input_root = _resolve_input_root(args.input_dir, bddl_path)
        try:
            rel_no_suffix = bddl_path.relative_to(input_root)
        except ValueError:
            rel_no_suffix = Path(bddl_path.name)
        rel_no_suffix = Path(str(rel_no_suffix)).with_suffix("")
        safe_task = _sanitize_rel_stem(rel_no_suffix)

        env = None
        try:
            env = SegmentationRenderEnv(
                bddl_file_name=str(bddl_path),
                camera_heights=args.resolution,
                camera_widths=args.resolution,
                camera_names=args.camera_names,
            )

            for sample_idx in range(args.num_seed):
                seed = args.base_seed + sample_idx * args.seed_stride
                out_stem = f"init_{safe_task}_seed{seed:06d}"
                img_path = args.output_dir / f"{out_stem}.png"
                seg_path = args.output_dir / f"{out_stem}.segmentation.npz"
                meta_path = args.output_dir / f"{out_stem}.json"

                if not args.overwrite and img_path.exists() and seg_path.exists() and meta_path.exists():
                    continue

                env.seed(seed)
                obs = env.reset()
                for _ in range(max(0, int(args.stabilize_steps))):
                    obs, _, _, _ = env.step(LIBERO_DUMMY_ACTION)

                rgb_key = f"{args.primary_camera}_image"
                if rgb_key not in obs:
                    raise KeyError(
                        f"Missing RGB obs key {rgb_key!r}. Available keys include: "
                        f"{sorted([k for k in obs.keys() if 'image' in k.lower()])[:10]} ..."
                    )
                img = np.asarray(obs[rgb_key])
                if args.rotate180:
                    img = _rotate180(img)
                img = img.astype(np.uint8, copy=False)

                seg_items = _extract_segmentation_items(
                    obs,
                    primary_camera=args.primary_camera,
                    include_all_cameras=args.include_all_segmentation_cameras,
                )
                if args.rotate180:
                    seg_items = {k: _rotate180(v) for k, v in seg_items.items()}

                seg_arrays = {k: v[None, ...] for k, v in seg_items.items()}

                seg_name_to_id, seg_id_to_name = _build_segmentation_name_mappings(env)
                present_ids: Optional[List[int]] = None
                if seg_items:
                    combined = next(iter(seg_items.values()))
                    present_ids = sorted({int(x) for x in np.unique(combined).tolist()})

                instruction: Optional[str] = None
                if hasattr(env, "language_instruction"):
                    instruction = str(env.language_instruction)
                    if args.rotate180:
                        instruction = _swap_left_right(instruction)

                _ensure_parent(img_path)
                _ensure_parent(seg_path)
                _ensure_parent(meta_path)

                import imageio.v2 as imageio  # local import to keep import surface small

                imageio.imwrite(img_path, img)
                np.savez_compressed(seg_path, **seg_arrays)
                with meta_path.open("w", encoding="utf-8") as f:
                    json.dump(
                        {
                            "bddl_index": int(bddl_idx),
                            "sample_idx": int(sample_idx),
                            "seed": int(seed),
                            "bddl_file": str(bddl_path),
                            "bddl_relative": str(rel_no_suffix.with_suffix(".bddl")),
                            "problem_name": getattr(env, "problem_name", None),
                            "domain_name": getattr(env, "domain_name", None),
                            "language_instruction": instruction,
                            "primary_camera": args.primary_camera,
                            "camera_names": list(args.camera_names),
                            "resolution": int(args.resolution),
                            "rotate180": bool(args.rotate180),
                            "stabilize_steps": int(args.stabilize_steps),
                            "image_file": str(img_path.name),
                            "segmentation_file": str(seg_path.name),
                            "segmentation_keys": list(seg_items.keys()),
                            "segmentation_instance_to_id": seg_name_to_id,
                            "segmentation_id_to_instance": seg_id_to_name,
                            "segmentation_ids_present": present_ids,
                        },
                        f,
                        ensure_ascii=False,
                        indent=2,
                    )

            print(f"[{bddl_idx + 1:04d}/{len(bddl_files):04d}] OK: {bddl_path}")
        except Exception as e:
            print(f"[{bddl_idx + 1:04d}/{len(bddl_files):04d}] FAILED: {bddl_path} ({type(e).__name__}: {e})")
        finally:
            _safe_close_env(env)


if __name__ == "__main__":
    main()
