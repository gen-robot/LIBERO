#!/usr/bin/env python3
"""
Shared simulation-environment constraints for ER BDDL generators.

These utilities centralize placement and naming constraints that should be
consistent across ER-GOAL / ER-OBJECT / ER-SEQUENTIAL / ER-SPATIAL.
"""

from __future__ import annotations

import re
import random
from typing import Dict, List, Optional, Set, Tuple

from er_constants import COLLISION_MARGIN, PLACEMENT_TOLERANCE, get_object_size, OBJECT_PLACEMENT_POSITIONS

# === Placement constraints (table frame) ===
# 1) Object init regions must not overlap (with a minimum gap).
# 2) Placement region (table frame) bounds:
#    - x_max must be <= 0.15
#    - y_min must be >= -0.12
# 3) For manipulated object + its placement region: max extent <= 0.2
# 4) For manipulated object placement region: all |coord| <= 0.25
MIN_REGION_GAP = 0.08
MIN_MANIP_FIXTURE_GAP = 0.02
MAX_MANIP_REGION_EXTENT = 0.20
REACH_BOUND = 0.25
MAX_REGION_XMAX = 0.15
MIN_REGION_YMIN = -0.12
LARGE_OBJECT_GAP = 0.13


def boxes_overlap(box1, box2, margin: float = 0.04) -> bool:
    x1_min, y1_min, x1_max, y1_max = box1[:4]
    x2_min, y2_min, x2_max, y2_max = box2[:4]
    x1_min -= margin
    y1_min -= margin
    x1_max += margin
    y1_max += margin
    return not (x1_max < x2_min or x2_max < x1_min or y1_max < y2_min or y2_max < y1_min)


def _clamp_box_extent(box: Tuple[float, float, float, float], max_extent: float) -> Tuple[float, float, float, float]:
    x_min, y_min, x_max, y_max = box
    cx, cy = (x_min + x_max) / 2, (y_min + y_max) / 2
    half_x = min((x_max - x_min) / 2, max_extent / 2)
    half_y = min((y_max - y_min) / 2, max_extent / 2)
    return (cx - half_x, cy - half_y, cx + half_x, cy + half_y)


def _within_abs_bound(box: Tuple[float, float, float, float], bound: float) -> bool:
    x_min, y_min, x_max, y_max = box
    return max(abs(x_min), abs(y_min), abs(x_max), abs(y_max)) <= bound


def _parse_on_stmt(stmt: str) -> Optional[Tuple[str, str]]:
    s = stmt.strip()
    if not s.startswith("(On "):
        return None
    parts = s.replace("(", "").replace(")", "").split()
    if len(parts) < 3:
        return None
    return parts[1], parts[2]


def occupied_table_region_boxes_from_init(
    init: List[str],
    regions: Dict[str, object],
    table_name: str,
) -> List[Tuple[float, float, float, float]]:
    """
    Return table-frame region boxes that are actually used by `(On ...)` init predicates.

    This avoids treating unrelated helper regions (e.g., stove_front_region) as occupied.
    """
    boxes: List[Tuple[float, float, float, float]] = []
    prefix = f"{table_name}_"
    for stmt in init:
        parsed = _parse_on_stmt(stmt)
        if parsed is None:
            continue
        _, region_key = parsed
        if not region_key.startswith(prefix):
            continue
        region_name = region_key[len(prefix) :]
        region = regions.get(region_name)
        if region is None:
            continue
        if getattr(region, "target", None) != table_name:
            continue
        ranges = getattr(region, "ranges", None)
        if not ranges:
            continue
        r = ranges[0]
        boxes.append((r[0], r[1], r[2], r[3]))
    return boxes


def occupied_table_collision_boxes_from_init(
    init: List[str],
    regions: Dict[str, object],
    table_name: str,
) -> List[Tuple[float, float, float, float]]:
    """
    Return footprint boxes (in table frame) for objects actually placed onto table regions in init.

    Unlike `get_occupied_boxes(regions)`, this is driven by `(On ...)` statements so it won't
    treat unused helper regions as occupied.
    """
    boxes: List[Tuple[float, float, float, float]] = []
    prefix = f"{table_name}_"
    for stmt in init:
        parsed = _parse_on_stmt(stmt)
        if parsed is None:
            continue
        instance, region_key = parsed
        if not region_key.startswith(prefix):
            continue
        region_name = region_key[len(prefix) :]
        region = regions.get(region_name)
        if region is None or getattr(region, "target", None) != table_name:
            continue
        ranges = getattr(region, "ranges", None)
        if not ranges:
            continue
        r = ranges[0]
        cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
        obj_type = extract_object_type(instance)
        w, d = get_object_size(obj_type, for_collision=False)
        boxes.append((cx - w / 2, cy - d / 2, cx + w / 2, cy + d / 2))
    return boxes


def table_on_region_box(
    *,
    table_name: str,
    init_stmts: List[str],
    regions: Dict[str, object],
    instance: str,
) -> Optional[Tuple[float, float, float, float]]:
    """
    Return the table-frame region box for `(On instance <table>_<region>)` if present.
    """
    prefix = f"(On {instance} "
    for stmt in init_stmts:
        s = stmt.strip()
        if not s.startswith(prefix):
            continue
        parsed = _parse_on_stmt(stmt)
        if parsed is None:
            continue
        _, region_key = parsed
        table_prefix = f"{table_name}_"
        if not region_key.startswith(table_prefix):
            return None
        region_name = region_key[len(table_prefix) :]
        region = regions.get(region_name)
        if region is None or getattr(region, "target", None) != table_name:
            return None
        ranges = getattr(region, "ranges", None)
        if not ranges:
            return None
        r = ranges[0]
        return (r[0], r[1], r[2], r[3])
    return None


def box_center(box: Tuple[float, float, float, float]) -> Tuple[float, float]:
    return ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)


def get_occupied_boxes(regions: Dict[str, object]) -> List[Tuple[float, float, float, float]]:
    """
    Approximate occupied footprints from region centers and object-size footprints.

    Considers:
    - regions named like `*_init_region[_k]`
    - specific fixture regions (cabinet_region, stove_region, ...)
    """
    fixture_regions = {"cabinet_region", "stove_region", "wine_rack_region", "desk_caddy_region"}
    fixture_types = {
        "cabinet_region": "wooden_cabinet",
        "stove_region": "flat_stove",
        "wine_rack_region": "wine_rack",
        "desk_caddy_region": "desk_caddy",
    }
    occupied: List[Tuple[float, float, float, float]] = []
    for name, region in regions.items():
        ranges = getattr(region, "ranges", None)
        if not ranges:
            continue
        r = ranges[0]
        cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2

        if "_init_region" in name:
            obj_type = name.replace("_init_region", "").rstrip("_0123456789")
        elif name in fixture_regions:
            obj_type = fixture_types[name]
        else:
            continue

        obj_w, obj_d = get_object_size(obj_type, for_collision=False)
        occupied.append((cx - obj_w / 2, cy - obj_d / 2, cx + obj_w / 2, cy + obj_d / 2))
    return occupied


def fixture_region_boxes(table_name: str, regions: Dict[str, object]) -> List[Tuple[float, float, float, float]]:
    """
    Approximate fixed-object footprints (in table frame) from their init regions.
    """
    fixture_types: Set[str] = {"wooden_cabinet", "white_cabinet", "flat_stove", "wine_rack", "desk_caddy"}
    boxes: List[Tuple[float, float, float, float]] = []
    for name, region in regions.items():
        if getattr(region, "target", None) != table_name:
            continue
        ranges = getattr(region, "ranges", None)
        if not ranges:
            continue
        if "_init_region" not in name:
            continue
        inferred = name.replace("_init_region", "").rstrip("_0123456789")
        if inferred not in fixture_types:
            continue
        r = ranges[0]
        cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
        w, d = get_object_size(inferred, for_collision=False)
        boxes.append((cx - w / 2, cy - d / 2, cx + w / 2, cy + d / 2))
    return boxes


def _candidate_centers(
    *,
    initial: Optional[List[Tuple[float, float]]] = None,
) -> List[Tuple[float, float]]:
    candidates: List[Tuple[float, float]] = list(initial) if initial is not None else list(OBJECT_PLACEMENT_POSITIONS)

    # Denser grid to guarantee feasibility under strict non-overlap constraints.
    grid_xs = [-0.30, -0.24, -0.18, -0.12, -0.06, 0.0, 0.06, 0.12, 0.18, 0.24, 0.30]
    grid_ys = [0.24, 0.18, 0.12, 0.06, 0.0, -0.06, -0.12, -0.18, -0.24, -0.30]
    grid = [(x, y) for y in grid_ys for x in grid_xs]
    grid.sort(key=lambda p: (-p[1], abs(p[0]), abs(p[1])))
    for p in grid:
        if p not in candidates:
            candidates.append(p)
    return candidates


def allocate_region(
    table_name: str,
    obj_type: str,
    regions: Dict[str, object],
    *,
    region_cls: Optional[type] = None,
    candidates: Optional[List[Tuple[float, float]]] = None,
    min_gap: float = MIN_REGION_GAP,
    max_extent: Optional[float] = None,
    require_within_bound: Optional[float] = None,
    min_ymin: Optional[float] = MIN_REGION_YMIN,
    max_xmax: Optional[float] = MAX_REGION_XMAX,
    min_gap_to_fixtures: Optional[float] = None,
    collision_margin: float = COLLISION_MARGIN,
    occupied_region_boxes: Optional[List[Tuple[float, float, float, float]]] = None,
    occupied_collision_boxes: Optional[List[Tuple[float, float, float, float]]] = None,
    _allow_relax: bool = True,
) -> Tuple[object, str]:
    """
    Allocate a non-overlapping region for an object on `table_name`.
    Returns (Region, region_name).
    """
    collision_w, collision_d = get_object_size(obj_type, for_collision=False)
    half_cw, half_cd = collision_w / 2, collision_d / 2
    actual_w, actual_d = get_object_size(obj_type, for_collision=False)
    half_w, half_d = actual_w / 2, actual_d / 2

    occupied_init_regions = occupied_region_boxes if occupied_region_boxes is not None else []
    # Collision check can be overly sensitive depending on the representation.
    # Prefer init-referenced region ranges when provided (matches existing ER-GOAL behavior),
    # otherwise fall back to collision footprints when explicitly provided, else region-based scan.
    if occupied_region_boxes is not None:
        collision_obstacles = occupied_region_boxes
    elif occupied_collision_boxes is not None:
        collision_obstacles = occupied_collision_boxes
    else:
        collision_obstacles = get_occupied_boxes(regions)
    fixture_boxes = fixture_region_boxes(table_name, regions) if min_gap_to_fixtures is not None else []

    for cx, cy in _candidate_centers(initial=candidates):
        collision_box = (cx - half_cw, cy - half_cd, cx + half_cw, cy + half_cd)
        if any(boxes_overlap(collision_box, obox, collision_margin) for obox in collision_obstacles):
            continue

        region_box = (
            cx - half_w - PLACEMENT_TOLERANCE,
            cy - half_d - PLACEMENT_TOLERANCE,
            cx + half_w + PLACEMENT_TOLERANCE,
            cy + half_d + PLACEMENT_TOLERANCE,
        )
        if max_extent is not None:
            region_box = _clamp_box_extent(region_box, max_extent=max_extent)
        if min_ymin is not None and region_box[1] < min_ymin:
            continue
        if max_xmax is not None and region_box[2] > max_xmax:
            continue
        if require_within_bound is not None and not _within_abs_bound(region_box, require_within_bound):
            continue
        if any(boxes_overlap(region_box, obox, margin=min_gap) for obox in occupied_init_regions):
            continue
        if min_gap_to_fixtures is not None:
            if any(boxes_overlap(region_box, fbox, margin=min_gap_to_fixtures) for fbox in fixture_boxes):
                continue

        region_name = f"{obj_type}_init_region"
        counter = 1
        while region_name in regions:
            region_name = f"{obj_type}_init_region_{counter}"
            counter += 1

        # Construct a Region-like object. Callers typically define their own `Region` dataclass.
        region_cls = region_cls or (next(iter(regions.values())).__class__ if regions else None)
        if region_cls is None:
            raise RuntimeError("allocate_region requires `region_cls` when `regions` is empty")
        region = region_cls(name=region_name, target=table_name, ranges=[region_box])
        return region, region_name

    # Fallback: shifted grid
    fallback_centers: List[Tuple[float, float]] = []
    for x in [-0.33, -0.27, -0.21, -0.15, -0.09, -0.03, 0.03, 0.09, 0.15, 0.21, 0.27, 0.33]:
        for y in [0.27, 0.21, 0.15, 0.09, 0.03, -0.03, -0.09, -0.15, -0.21, -0.27]:
            fallback_centers.append((x, y))

    for cx, cy in fallback_centers:
        collision_box = (cx - half_cw, cy - half_cd, cx + half_cw, cy + half_cd)
        if any(boxes_overlap(collision_box, obox, collision_margin) for obox in collision_obstacles):
            continue
        region_box = (
            cx - half_w - PLACEMENT_TOLERANCE,
            cy - half_d - PLACEMENT_TOLERANCE,
            cx + half_w + PLACEMENT_TOLERANCE,
            cy + half_d + PLACEMENT_TOLERANCE,
        )
        if max_extent is not None:
            region_box = _clamp_box_extent(region_box, max_extent=max_extent)
        if min_ymin is not None and region_box[1] < min_ymin:
            continue
        if max_xmax is not None and region_box[2] > max_xmax:
            continue
        if require_within_bound is not None and not _within_abs_bound(region_box, require_within_bound):
            continue
        if any(boxes_overlap(region_box, obox, margin=min_gap) for obox in occupied_init_regions):
            continue
        if min_gap_to_fixtures is not None:
            if any(boxes_overlap(region_box, fbox, margin=min_gap_to_fixtures) for fbox in fixture_boxes):
                continue

        region_name = f"{obj_type}_init_region"
        counter = 1
        while region_name in regions:
            region_name = f"{obj_type}_init_region_{counter}"
            counter += 1
        region_cls = region_cls or (next(iter(regions.values())).__class__ if regions else None)
        if region_cls is None:
            raise RuntimeError("allocate_region requires `region_cls` when `regions` is empty")
        return region_cls(name=region_name, target=table_name, ranges=[region_box]), region_name

    if _allow_relax:
        # Some scene templates are extremely crowded under strict table-frame bounds
        # (e.g. `x_max <= 0.15`, `y_min >= -0.12`) and large objects (basket/tray)
        # can become impossible to place. As a last resort, retry with relaxed bounds
        # and a smaller min-gap while keeping other constraints (extent / reach).
        relaxed_min_gap = min(min_gap, 0.02)
        if min_ymin is not None or max_xmax is not None or relaxed_min_gap < min_gap:
            return allocate_region(
                table_name,
                obj_type,
                regions,
                region_cls=region_cls,
                candidates=candidates,
                min_gap=relaxed_min_gap,
                max_extent=max_extent,
                require_within_bound=require_within_bound,
                min_ymin=None,
                max_xmax=None,
                min_gap_to_fixtures=min_gap_to_fixtures,
                collision_margin=collision_margin,
                occupied_region_boxes=occupied_region_boxes,
                _allow_relax=False,
            )

    raise RuntimeError(f"Failed to allocate non-overlapping region for {obj_type} on {table_name}")


def allocate_region_near_center(
    table_name: str,
    obj_type: str,
    regions: Dict[str, object],
    *,
    region_cls: Optional[type] = None,
    desired_center: Tuple[float, float],
    search_offsets: Optional[List[Tuple[float, float]]] = None,
    min_gap: float = MIN_REGION_GAP,
    max_extent: Optional[float] = None,
    require_within_bound: Optional[float] = None,
    min_ymin: Optional[float] = MIN_REGION_YMIN,
    max_xmax: Optional[float] = MAX_REGION_XMAX,
    min_gap_to_fixtures: Optional[float] = None,
    collision_margin: float = COLLISION_MARGIN,
    occupied_region_boxes: Optional[List[Tuple[float, float, float, float]]] = None,
    occupied_collision_boxes: Optional[List[Tuple[float, float, float, float]]] = None,
) -> Tuple[object, str]:
    """
    Allocate a region close to `desired_center` by trying small offsets first.
    """
    if search_offsets is None:
        search_offsets = [
            (0.0, 0.0),
            (0.05, 0.0),
            (-0.05, 0.0),
            (0.0, 0.05),
            (0.0, -0.05),
            (0.10, 0.0),
            (-0.10, 0.0),
            (0.0, 0.10),
            (0.0, -0.10),
            (0.05, 0.05),
            (0.05, -0.05),
            (-0.05, 0.05),
            (-0.05, -0.05),
        ]
    cx0, cy0 = desired_center
    candidates = [(cx0 + dx, cy0 + dy) for dx, dy in search_offsets]
    return allocate_region(
        table_name,
        obj_type,
        regions,
        region_cls=region_cls,
        candidates=candidates,
        min_gap=min_gap,
        max_extent=max_extent,
        require_within_bound=require_within_bound,
        min_ymin=min_ymin,
        max_xmax=max_xmax,
        min_gap_to_fixtures=min_gap_to_fixtures,
        collision_margin=collision_margin,
        occupied_region_boxes=occupied_region_boxes,
        occupied_collision_boxes=occupied_collision_boxes,
    )


def extract_object_type(instance: str) -> str:
    if instance.endswith("_1") or instance.endswith("_2"):
        return instance.rsplit("_", 1)[0]
    return instance


def alloc_unique_region_name(existing: Set[str], base: str) -> str:
    if base not in existing:
        return base
    i = 1
    while f"{base}_{i}" in existing:
        i += 1
    return f"{base}_{i}"


def next_available_instance_name(existing: Set[str], instance: str) -> str:
    m = re.match(r"^(.+)_([0-9]+)$", instance)
    if m:
        base = m.group(1)
        start = int(m.group(2))
    else:
        base = instance
        start = 1
    i = max(1, start)
    cand = instance
    while cand in existing:
        i += 1
        cand = f"{base}_{i}"
    return cand


def add_object_unique(output: object, instance: str, obj_type: str, *, prefer_name: Optional[str] = None) -> str:
    """
    Add a movable object to `output.objects`, renaming if needed to avoid instance-name collisions.
    Returns the final instance name used.
    """
    prefer_name = prefer_name or instance
    objects = getattr(output, "objects", None)
    fixtures = getattr(output, "fixtures", None)
    if not isinstance(objects, dict) or not isinstance(fixtures, dict):
        raise TypeError("add_object_unique expects `output.objects` and `output.fixtures` dicts")

    existing = set(objects) | set(fixtures)
    desired = prefer_name
    if desired in existing:
        if objects.get(desired) == obj_type:
            return desired
        desired = next_available_instance_name(existing, desired)
    objects[desired] = obj_type
    return desired


def infer_manip_and_target_from_goal(goal: str) -> Tuple[Optional[str], Optional[str]]:
    atoms = re.findall(r"\(([^()]+)\)", goal or "")
    for a in atoms:
        tokens = a.strip().split()
        if not tokens:
            continue
        if tokens[0] == "On" and len(tokens) >= 3:
            return tokens[1], tokens[2]
    return None, None


def _extract_instance_base(name: str) -> Optional[str]:
    m = re.match(r"^(.+)_\d+$", name)
    if not m:
        return None
    return m.group(1)


def _token_replace(s: str, old: str, new: str) -> str:
    pattern = r"(?<![A-Za-z0-9_])" + re.escape(old) + r"(?![A-Za-z0-9_])"
    return re.sub(pattern, new, s)


def rename_instance_everywhere(output: object, old: str, new: str) -> None:
    if old == new:
        return
    objects = getattr(output, "objects", None)
    fixtures = getattr(output, "fixtures", None)
    regions = getattr(output, "regions", None)
    init = getattr(output, "init", None)
    goal = getattr(output, "goal", None)
    obj_of_interest = getattr(output, "obj_of_interest", None)

    if isinstance(objects, dict) and old in objects:
        objects[new] = objects.pop(old)
    if isinstance(fixtures, dict) and old in fixtures:
        fixtures[new] = fixtures.pop(old)
    if isinstance(regions, dict):
        for region in regions.values():
            if getattr(region, "target", None) == old:
                region.target = new
    if isinstance(init, list):
        setattr(output, "init", [_token_replace(stmt, old, new) for stmt in init])
    if isinstance(goal, str):
        setattr(output, "goal", _token_replace(goal, old, new))
    if isinstance(obj_of_interest, list):
        setattr(output, "obj_of_interest", [new if x == old else x for x in obj_of_interest])


def ensure_instance_one(output: object, instance: str) -> str:
    base = _extract_instance_base(instance)
    if base is None or instance.endswith("_1"):
        return instance
    desired = f"{base}_1"
    objects = getattr(output, "objects", {}) or {}
    fixtures = getattr(output, "fixtures", {}) or {}
    if desired not in objects and desired not in fixtures:
        rename_instance_everywhere(output, instance, desired)
        return desired
    swap_tmp = f"{base}__tmp_swap__"
    rename_instance_everywhere(output, desired, swap_tmp)
    rename_instance_everywhere(output, instance, desired)
    rename_instance_everywhere(output, swap_tmp, instance)
    return desired


def _extract_table_region_name(table_name: str, on_stmt: str) -> Optional[str]:
    parsed = _parse_on_stmt(on_stmt)
    if parsed is None:
        return None
    _, region_key = parsed
    prefix = f"{table_name}_"
    if not region_key.startswith(prefix):
        return None
    return region_key[len(prefix) :]


def enforce_non_overlapping_table_placements(
    output: object,
    table_name: str,
    *,
    fixed_instances: Set[str],
    min_gap: float = MIN_REGION_GAP,
) -> None:
    """
    Ensure all `(On <instance> <table>_<region>)` placements have non-overlapping region ranges.

    Re-samples placements for all non-fixed instances.
    """
    init = getattr(output, "init", [])
    regions = getattr(output, "regions", {})
    objects = getattr(output, "objects", {})

    # Some upstream BDDL sources may carry overlapping *_init_region ranges.
    # We try a few re-sampling attempts for all non-fixed table placements
    # before giving up.
    last_overlap: Optional[Tuple[str, str]] = None
    last_failure: Optional[str] = None
    for _attempt in range(25):
        init_try = list(init) if isinstance(init, list) else []
        regions_try = dict(regions) if isinstance(regions, dict) else {}

        placements = []
        prefix = f"{table_name}_"
        for i, stmt in enumerate(init_try):
            parsed = _parse_on_stmt(stmt)
            if parsed is None:
                continue
            instance, region_key = parsed
            if not region_key.startswith(prefix):
                continue
            region_name = region_key[len(prefix) :]
            region = regions_try.get(region_name)
            if region is None or getattr(region, "target", None) != table_name or not getattr(region, "ranges", None):
                continue
            placements.append((i, instance, region_name))

        to_reallocate = []
        for init_idx, instance, region_name in placements:
            if instance in fixed_instances:
                continue
            to_reallocate.append((init_idx, instance, region_name))
            regions_try.pop(region_name, None)

        # Randomize order to avoid deterministic dead-ends when space is tight.
        random.shuffle(to_reallocate)

        allocation_failed = False
        for init_idx, instance, region_name in to_reallocate:
            obj_type = objects.get(instance) or extract_object_type(instance)
            try:
                new_region, _ = allocate_region(
                    table_name,
                    obj_type,
                    regions_try,
                    min_gap=min_gap,
                    collision_margin=COLLISION_MARGIN,
                    occupied_region_boxes=occupied_table_region_boxes_from_init(init_try, regions_try, table_name),
                )
            except RuntimeError:
                allocation_failed = True
                last_failure = f"Failed to allocate non-overlapping region for {instance} ({obj_type}) on {table_name}"
                break

            regions_try[region_name] = new_region
            init_try[init_idx] = f"(On {instance} {table_name}_{region_name})"

        if allocation_failed:
            continue

        final_boxes: List[Tuple[str, Tuple[float, float, float, float]]] = []
        for _, instance, region_name in placements:
            region = regions_try.get(region_name)
            if region is None or getattr(region, "target", None) != table_name or not getattr(region, "ranges", None):
                continue
            r = getattr(region, "ranges")[0]
            final_boxes.append((f"{instance}:{region_name}", (r[0], r[1], r[2], r[3])))

        overlap_found = False
        for i in range(len(final_boxes)):
            key_i, box_i = final_boxes[i]
            for j in range(i + 1, len(final_boxes)):
                key_j, box_j = final_boxes[j]
                if boxes_overlap(box_i, box_j, margin=min_gap):
                    last_overlap = (key_i, key_j)
                    overlap_found = True
                    break
            if overlap_found:
                break

        if not overlap_found:
            setattr(output, "init", init_try)
            setattr(output, "regions", regions_try)
            return

    if last_overlap is None:
        if last_failure is not None:
            raise RuntimeError(last_failure)
        raise RuntimeError("Table placement regions overlap but no concrete overlap pair was found.")
    raise RuntimeError(f"Table placement regions overlap (margin={min_gap}): {last_overlap[0]} vs {last_overlap[1]}")


def remove_instance_table_placement(output: object, table_name: str, instance: str) -> None:
    """
    Remove `(On instance table_...)` statement and the corresponding table-targeted region.
    """
    init = getattr(output, "init", [])
    regions = getattr(output, "regions", {})
    removed_region_name: Optional[str] = None
    new_init: List[str] = []
    for stmt in init:
        parsed = _parse_on_stmt(stmt)
        if parsed is None:
            new_init.append(stmt)
            continue
        inst, region_key = parsed
        if inst != instance:
            new_init.append(stmt)
            continue
        region_name = _extract_table_region_name(table_name, stmt)
        if region_name is not None:
            removed_region_name = region_name
        # Skip this statement
    setattr(output, "init", new_init)
    if removed_region_name is not None:
        region = regions.get(removed_region_name)
        if region is not None and getattr(region, "target", None) == table_name:
            regions.pop(removed_region_name, None)
