#!/usr/bin/env python3
"""
Generate ER-GOAL BDDL files from task specifications.
Updated to work with v3.0 YAML format (source_a, source_b, source_c).
"""

import os
import re
import yaml
import argparse
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Set

from er_constants import (
    OBJECT_SIZES, COLLISION_MARGIN, PLACEMENT_TOLERANCE, get_object_size,
    OBJECT_PLACEMENT_POSITIONS
)

# === Additional placement constraints for ER-GOAL ===
# 1) Object init regions must not overlap
# 2) Min gap between region boundaries >= 0.05
# 3) For manipulated object + its goal placement region: max extent <= 0.2
# 4) For manipulated object + placement region (table-frame): all |coord| <= 0.25
# 5) If multiple same-type objects, the manipulated object should be *_1
# 6) Manipulated object should be far from fixtures: min gap >= 0.1
MIN_REGION_GAP = 0.08
MIN_MANIP_FIXTURE_GAP = 0.02
MAX_MANIP_REGION_EXTENT = 0.20
REACH_BOUND = 0.25
# Placement bounds (table frame) for all table-spawned movable objects.
# Constraint request:
# - x_max must be <= 0.15
# - y_min must be >= -0.12
MAX_REGION_XMAX = 0.15
MIN_REGION_YMIN = -0.12

EXTRA_OBJ_REGION_GAP = 0.01
EXTRA_OBJ_COLLISION_MARGIN = 0.01
LARGE_OBJECT_GAP = 0.13


@dataclass
class Region:
    name: str
    target: str
    ranges: Optional[List[Tuple[float, float, float, float]]] = None
    yaw_rotation: Optional[Tuple[float, float]] = None

    def to_bddl(self) -> str:
        lines = [f"      ({self.name}"]
        lines.append(f"          (:target {self.target})")
        if self.ranges:
            r = self.ranges[0]
            lines.append(f"          (:ranges (")
            lines.append(f"              ({r[0]:.4f} {r[1]:.4f} {r[2]:.4f} {r[3]:.4f})")
            lines.append(f"            )")
            lines.append(f"          )")
        if self.yaw_rotation:
            lines.append(f"          (:yaw_rotation (")
            lines.append(f"              ({self.yaw_rotation[0]} {self.yaw_rotation[1]})")
            lines.append(f"            )")
            lines.append(f"          )")
        lines.append("      )")
        return "\n".join(lines)


@dataclass
class BDDLFile:
    problem_name: str
    domain: str = "robosuite"
    language: str = ""
    regions: Dict[str, Region] = field(default_factory=dict)
    fixtures: Dict[str, str] = field(default_factory=dict)
    objects: Dict[str, str] = field(default_factory=dict)
    obj_of_interest: List[str] = field(default_factory=list)
    init: List[str] = field(default_factory=list)
    goal: str = ""

    def to_bddl(self) -> str:
        lines = [f"(define (problem {self.problem_name})"]
        lines.append(f"  (:domain {self.domain})")
        lines.append(f"  (:language {self.language})")
        
        lines.append("    (:regions")
        for region in self.regions.values():
            lines.append(region.to_bddl())
        lines.append("    )")
        lines.append("")
        
        lines.append("  (:fixtures")
        for instance, ftype in self.fixtures.items():
            lines.append(f"    {instance} - {ftype}")
        lines.append("  )")
        lines.append("")
        
        lines.append("  (:objects")
        type_to_instances = {}
        for instance, otype in self.objects.items():
            if otype not in type_to_instances:
                type_to_instances[otype] = []
            type_to_instances[otype].append(instance)
        for otype, instances in type_to_instances.items():
            lines.append(f"    {' '.join(sorted(instances))} - {otype}")
        lines.append("  )")
        lines.append("")
        
        lines.append("  (:obj_of_interest")
        for obj in self.obj_of_interest:
            lines.append(f"    {obj}")
        lines.append("  )")
        lines.append("")
        
        lines.append("  (:init")
        for stmt in self.init:
            lines.append(f"    {stmt}")
        lines.append("  )")
        lines.append("")
        
        lines.append("  (:goal")
        lines.append(f"    (And {self.goal})")
        lines.append("  )")
        lines.append(")")
        
        return "\n".join(lines)


def parse_bddl_file(filepath: str) -> BDDLFile:
    """Parse a BDDL file into structured components."""
    with open(filepath, 'r') as f:
        content = f.read()

    problem_match = re.search(r'\(define \(problem ([^)]+)\)', content)
    problem_name = problem_match.group(1) if problem_match else "UNKNOWN"

    lang_match = re.search(r'\(:language ([^)]+)\)', content)
    language = lang_match.group(1).strip() if lang_match else ""

    regions = {}
    regions_block = re.search(r'\(:regions(.*?)\)\s*\n\s*\(:fixtures', content, re.DOTALL)
    if regions_block:
        region_text = regions_block.group(1)
        range_pattern = r'\((\w+)\s+\(:target (\w+)\)\s+\(:ranges \(\s+\(([-\d. ]+)\)\s+\)\s+\)(?:\s+\(:yaw_rotation \(\s+\(([-\d. ]+)\)\s+\)\s+\))?\s*\)'
        for match in re.finditer(range_pattern, region_text):
            name, target, coords_str = match.group(1), match.group(2), match.group(3)
            coords = tuple(float(x) for x in coords_str.split())
            yaw = None
            if match.group(4):
                yaw_vals = [float(x) for x in match.group(4).split()]
                yaw = (yaw_vals[0], yaw_vals[1])
            regions[name] = Region(name=name, target=target, ranges=[coords], yaw_rotation=yaw)
        
        simple_pattern = r'\((\w+)\s+\(:target (\w+)\)\s*\)'
        for match in re.finditer(simple_pattern, region_text):
            name, target = match.group(1), match.group(2)
            if name not in regions:
                regions[name] = Region(name=name, target=target)

    fixtures = {}
    fixtures_match = re.search(r'\(:fixtures(.*?)\)', content, re.DOTALL)
    if fixtures_match:
        for line in fixtures_match.group(1).strip().split('\n'):
            line = line.strip()
            if ' - ' in line:
                parts = line.split(' - ')
                fixtures[parts[0].strip()] = parts[1].strip()

    objects = {}
    objects_match = re.search(r'\(:objects(.*?)\)', content, re.DOTALL)
    if objects_match:
        for line in objects_match.group(1).strip().split('\n'):
            line = line.strip()
            if ' - ' in line:
                parts = line.split(' - ')
                instances = parts[0].strip().split()
                otype = parts[1].strip()
                for inst in instances:
                    objects[inst] = otype

    obj_of_interest = []
    interest_match = re.search(r'\(:obj_of_interest(.*?)\)', content, re.DOTALL)
    if interest_match:
        for line in interest_match.group(1).strip().split('\n'):
            obj = line.strip()
            if obj:
                obj_of_interest.append(obj)

    init = []
    init_match = re.search(r'\(:init\s*(.*?)\s*\)\s*\n\s*\(:goal', content, re.DOTALL)
    if init_match:
        for match in re.finditer(r'\([^()]+\)', init_match.group(1)):
            init.append(match.group(0))

    goal = ""
    goal_match = re.search(r'\(:goal\s+\(And\s+(\([^)]+\))\s*\)\s*\)', content, re.DOTALL)
    if goal_match:
        goal = goal_match.group(1).strip()
    else:
        goal_match = re.search(r'\(:goal\s+(\([^)]+\))\s*\)', content, re.DOTALL)
        if goal_match:
            goal = goal_match.group(1).strip()

    return BDDLFile(
        problem_name=problem_name,
        domain="robosuite",
        language=language,
        regions=regions,
        fixtures=fixtures,
        objects=objects,
        obj_of_interest=obj_of_interest,
        init=init,
        goal=goal
    )


def boxes_overlap(box1, box2, margin=0.04) -> bool:
    x1_min, y1_min, x1_max, y1_max = box1[:4]
    x2_min, y2_min, x2_max, y2_max = box2[:4]
    x1_min -= margin
    y1_min -= margin
    x1_max += margin
    y1_max += margin
    return not (x1_max < x2_min or x2_max < x1_min or y1_max < y2_min or y2_max < y1_min)

def _parse_on_stmt(stmt: str) -> Optional[Tuple[str, str]]:
    # Returns (instance, region_key)
    s = stmt.strip()
    if not s.startswith("(On "):
        return None
    parts = s.replace("(", "").replace(")", "").split()
    if len(parts) < 3:
        return None
    return parts[1], parts[2]


def _occupied_table_boxes_from_init(init: List[str], regions: Dict[str, Region], table_name: str) -> List[Tuple[float, float, float, float]]:
    """
    Return the set of table-frame region boxes that are actually used by `(On ...)` init predicates.

    This avoids treating unrelated helper regions (e.g. stove_front_region) as occupied, which can
    make placement impossible in some base BDDLs.
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
        region_name = region_key[len(prefix):]
        region = regions.get(region_name)
        if region is None or region.target != table_name or not region.ranges:
            continue
        r = region.ranges[0]
        boxes.append((r[0], r[1], r[2], r[3]))
    return boxes


def _enforce_non_overlapping_table_placements(
    output: BDDLFile,
    table_name: str,
    *,
    fixed_instances: Set[str],
    min_gap: float = MIN_REGION_GAP,
) -> None:
    """
    Ensure all placements onto table-frame regions have non-overlapping ranges (with margin=min_gap).

    We treat fixtures (and any explicit fixed_instances) as immovable and re-place all other instances
    by re-sampling their table-targeted regions with `allocate_region(...)`.
    """
    placements: List[Tuple[int, str, str]] = []  # (init_idx, instance, region_name)
    prefix = f"{table_name}_"
    for i, stmt in enumerate(output.init):
        parsed = _parse_on_stmt(stmt)
        if parsed is None:
            continue
        instance, region_key = parsed
        if not region_key.startswith(prefix):
            continue
        region_name = region_key[len(prefix):]
        region = output.regions.get(region_name)
        if region is None or region.target != table_name or not region.ranges:
            continue
        placements.append((i, instance, region_name))

    # Remove non-fixed placement regions to allow clean re-placement.
    to_reallocate: List[Tuple[int, str, str]] = []
    for init_idx, instance, region_name in placements:
        if instance in fixed_instances:
            continue
        to_reallocate.append((init_idx, instance, region_name))
        output.regions.pop(region_name, None)

    # Greedily re-place all non-fixed instances.
    for init_idx, instance, region_name in to_reallocate:
        obj_type = extract_object_type(instance)
        avoid_boxes = _avoid_boxes_for_large_items(
            output,
            table_name=table_name,
            exclude_instance=instance,
            include_large_movable=(obj_type not in {"basket", "wooden_tray"}),
        )
        new_region, _ = allocate_region(
            table_name,
            obj_type,
            output.regions,
            min_gap=min_gap,
            collision_margin=EXTRA_OBJ_COLLISION_MARGIN,
            avoid_boxes=avoid_boxes,
            avoid_gap=LARGE_OBJECT_GAP,
            occupied_region_boxes=_occupied_table_boxes_from_init(output.init, output.regions, table_name),
        )
        # Keep the original region name so other references (if any) remain valid.
        existing = output.regions.get(region_name)
        if existing is None:
            output.regions[region_name] = Region(name=region_name, target=table_name, ranges=new_region.ranges)
        else:
            existing.target = table_name
            existing.ranges = new_region.ranges
        output.init[init_idx] = f"(On {instance} {table_name}_{region_name})"

    # Verify final non-overlap among all table-targeted regions used in init placements.
    final_boxes: List[Tuple[str, Tuple[float, float, float, float]]] = []
    for _, instance, region_name in placements:
        region = output.regions.get(region_name)
        if region is None or region.target != table_name or not region.ranges:
            continue
        r = region.ranges[0]
        final_boxes.append((f"{instance}:{region_name}", (r[0], r[1], r[2], r[3])))

    for i in range(len(final_boxes)):
        key_i, box_i = final_boxes[i]
        for j in range(i + 1, len(final_boxes)):
            key_j, box_j = final_boxes[j]
            if boxes_overlap(box_i, box_j, margin=min_gap):
                raise RuntimeError(
                    f"Table placement regions overlap (margin={min_gap}): {key_i} vs {key_j}"
                )


def get_occupied_boxes(regions: Dict[str, Region]) -> List[Tuple[float, float, float, float]]:
    """Get occupied boxes using actual object sizes from OBJECT_SIZES.
    
    Considers both *_init_region patterns and fixture regions (cabinet_region, stove_region).
    """
    # Fixture region names that should be considered for collision
    fixture_regions = {'cabinet_region', 'stove_region', 'wine_rack_region', 'desk_caddy_region'}
    fixture_types = {'cabinet_region': 'wooden_cabinet', 'stove_region': 'flat_stove',
                     'wine_rack_region': 'wine_rack', 'desk_caddy_region': 'desk_caddy'}
    
    occupied = []
    for name, region in regions.items():
        if not region.ranges:
            continue
        r = region.ranges[0]
        cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
        
        if '_init_region' in name:
            obj_type = name.replace('_init_region', '').rstrip('_0123456789')
        elif name in fixture_regions:
            obj_type = fixture_types[name]
        else:
            continue
            
        # Use actual footprint sizes; non-overlap constraints are enforced separately on region ranges.
        obj_w, obj_d = get_object_size(obj_type, for_collision=False)
        occupied.append((cx - obj_w/2, cy - obj_d/2, cx + obj_w/2, cy + obj_d/2))
    return occupied


def _extract_instance_base(name: str) -> Optional[str]:
    m = re.match(r"^(.+)_\d+$", name)
    if not m:
        return None
    return m.group(1)


def _token_replace(s: str, old: str, new: str) -> str:
    # Replace whole tokens (names consist of [A-Za-z0-9_]).
    pattern = r"(?<![A-Za-z0-9_])" + re.escape(old) + r"(?![A-Za-z0-9_])"
    return re.sub(pattern, new, s)


def _clamp_box_extent(box: Tuple[float, float, float, float], max_extent: float) -> Tuple[float, float, float, float]:
    x_min, y_min, x_max, y_max = box
    cx, cy = (x_min + x_max) / 2, (y_min + y_max) / 2
    half_x = min((x_max - x_min) / 2, max_extent / 2)
    half_y = min((y_max - y_min) / 2, max_extent / 2)
    return (cx - half_x, cy - half_y, cx + half_x, cy + half_y)


def _within_abs_bound(box: Tuple[float, float, float, float], bound: float) -> bool:
    x_min, y_min, x_max, y_max = box
    return max(abs(x_min), abs(y_min), abs(x_max), abs(y_max)) <= bound


def _table_object_init_region_boxes(table_name: str, regions: Dict[str, Region]) -> List[Tuple[float, float, float, float]]:
    # Backward-compatible helper: by default only consider explicit init regions and fixture placement regions.
    fixture_regions = {"cabinet_region", "stove_region", "wine_rack_region", "desk_caddy_region"}
    boxes: List[Tuple[float, float, float, float]] = []
    for name, region in regions.items():
        if region.target != table_name or not region.ranges:
            continue
        if "_init_region" not in name and name not in fixture_regions:
            continue
        r = region.ranges[0]
        boxes.append((r[0], r[1], r[2], r[3]))
    return boxes


def _fixture_region_boxes(table_name: str, regions: Dict[str, Region]) -> List[Tuple[float, float, float, float]]:
    """
    Approximate fixed-object footprints (in table frame) from their placement init regions.

    Many scene BDDLs place fixtures via regions like `flat_stove_init_region` (often tiny),
    so we infer the fixture footprint by taking the region center and expanding by the
    fixture's object-size footprint from `er_constants`.
    """
    fixture_types: Set[str] = {"wooden_cabinet", "white_cabinet", "flat_stove", "wine_rack", "desk_caddy"}
    boxes: List[Tuple[float, float, float, float]] = []

    for name, region in regions.items():
        if region.target != table_name or not region.ranges:
            continue
        if "_init_region" not in name:
            continue

        # Infer type from region name like `flat_stove_init_region` or `flat_stove_init_region_1`.
        inferred = name.replace("_init_region", "").rstrip("_0123456789")
        if inferred not in fixture_types:
            continue

        r = region.ranges[0]
        cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
        w, d = get_object_size(inferred, for_collision=False)
        boxes.append((cx - w / 2, cy - d / 2, cx + w / 2, cy + d / 2))

    return boxes


def _fixture_region_boxes_for_types(
    table_name: str,
    regions: Dict[str, Region],
    *,
    fixture_types: Set[str],
) -> List[Tuple[float, float, float, float]]:
    """
    Like `_fixture_region_boxes` but limited to an explicit set of inferred fixture types.
    """
    boxes: List[Tuple[float, float, float, float]] = []
    for name, region in regions.items():
        if region.target != table_name or not region.ranges:
            continue
        if "_init_region" not in name:
            continue
        inferred = name.replace("_init_region", "").rstrip("_0123456789")
        if inferred not in fixture_types:
            continue
        r = region.ranges[0]
        cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
        w, d = get_object_size(inferred, for_collision=False)
        boxes.append((cx - w / 2, cy - d / 2, cx + w / 2, cy + d / 2))
    return boxes


def _table_on_region_box(
    *,
    table_name: str,
    init_stmts: List[str],
    regions: Dict[str, Region],
    instance: str,
) -> Optional[Tuple[float, float, float, float]]:
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
        region_name = region_key[len(table_prefix):]
        region = regions.get(region_name)
        if region is None or region.target != table_name or not region.ranges:
            return None
        r = region.ranges[0]
        return (r[0], r[1], r[2], r[3])
    return None


def _avoid_boxes_for_large_items(
    output: BDDLFile,
    *,
    table_name: str,
    exclude_instance: Optional[str] = None,
    include_large_movable: bool = True,
) -> List[Tuple[float, float, float, float]]:
    """
    Return table-frame boxes that other objects should keep away from:
    - Cabinets (wooden/white) treated as fixed obstacles
    - Large movable containers (basket/wooden_tray) if requested
    """
    boxes: List[Tuple[float, float, float, float]] = []

    # Cabinets (fixtures) are effectively immovable obstacles.
    boxes.extend(
        _fixture_region_boxes_for_types(
            table_name,
            output.regions,
            fixture_types={"wooden_cabinet", "white_cabinet"},
        )
    )

    if not include_large_movable:
        return boxes

    large_types = {"basket", "wooden_tray"}
    for inst, otype in output.objects.items():
        if inst == exclude_instance:
            continue
        if otype not in large_types:
            continue
        b = _table_on_region_box(table_name=table_name, init_stmts=output.init, regions=output.regions, instance=inst)
        if b is not None:
            boxes.append(b)

    return boxes


def allocate_region(
    table_name: str,
    obj_type: str,
    regions: Dict[str, Region],
    *,
    min_gap: float = MIN_REGION_GAP,
    max_extent: Optional[float] = None,
    require_within_bound: Optional[float] = None,
    min_ymin: Optional[float] = MIN_REGION_YMIN,
    max_xmax: Optional[float] = MAX_REGION_XMAX,
    min_gap_to_fixtures: Optional[float] = None,
    collision_margin: float = COLLISION_MARGIN,
    avoid_boxes: Optional[List[Tuple[float, float, float, float]]] = None,
    avoid_gap: float = LARGE_OBJECT_GAP,
    occupied_region_boxes: Optional[List[Tuple[float, float, float, float]]] = None,
) -> Tuple[Region, str]:
    """Allocate a non-overlapping region for an object."""
    # Use actual size for collision detection (gap is enforced via region-range checks).
    collision_w, collision_d = get_object_size(obj_type, for_collision=False)
    half_cw, half_cd = collision_w / 2, collision_d / 2
    # Use actual size for region bounds
    actual_w, actual_d = get_object_size(obj_type, for_collision=False)
    half_w, half_d = actual_w / 2, actual_d / 2
    occupied = get_occupied_boxes(regions)
    
    # Candidate centers:
    # - Start with the curated spread from `er_constants`
    # - Add a denser grid to guarantee feasibility under strict non-overlap constraints
    candidates: List[Tuple[float, float]] = list(OBJECT_PLACEMENT_POSITIONS)
    # Wider/denser grid so crowded three-source scenes can still be placed feasibly.
    grid_xs = [-0.30, -0.24, -0.18, -0.12, -0.06, 0.0, 0.06, 0.12, 0.18, 0.24, 0.30]
    grid_ys = [0.24, 0.18, 0.12, 0.06, 0.0, -0.06, -0.12, -0.18, -0.24, -0.30]
    grid = [(x, y) for y in grid_ys for x in grid_xs]
    grid.sort(key=lambda p: (-p[1], abs(p[0]), abs(p[1])))
    for p in grid:
        if p not in candidates:
            candidates.append(p)
    occupied_init_regions = (
        occupied_region_boxes
        if occupied_region_boxes is not None
        else _table_object_init_region_boxes(table_name, regions)
    )
    fixture_boxes = _fixture_region_boxes(table_name, regions) if min_gap_to_fixtures is not None else []
    
    for cx, cy in candidates:
        # Use expanded size for collision detection
        collision_box = (cx - half_cw, cy - half_cd, cx + half_cw, cy + half_cd)
        collision = any(boxes_overlap(collision_box, obox, collision_margin) for obox in occupied)
        if not collision:
            # Region bounds use object size for proper physics spawning
            region_name = f"{obj_type}_init_region"
            counter = 1
            while region_name in regions:
                region_name = f"{obj_type}_init_region_{counter}"
                counter += 1

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

            # Enforce non-overlap + min gap between table-frame object init regions.
            if any(boxes_overlap(region_box, obox, margin=min_gap) for obox in occupied_init_regions):
                continue

            # Extra constraint: keep away from selected large obstacles (e.g. cabinets, basket, tray).
            if avoid_boxes is not None:
                if any(boxes_overlap(region_box, abox, margin=avoid_gap) for abox in avoid_boxes):
                    continue

            # Extra constraint: manipulated object far from fixtures.
            if min_gap_to_fixtures is not None:
                if any(boxes_overlap(region_box, fbox, margin=min_gap_to_fixtures) for fbox in fixture_boxes):
                    continue

            region = Region(name=region_name, target=table_name, ranges=[region_box])
            return region, region_name
    
    # Fallback: try a slightly shifted grid (helps if everything aligns unfavorably with min-gap margins).
    fallback_centers: List[Tuple[float, float]] = []
    for x in [-0.33, -0.27, -0.21, -0.15, -0.09, -0.03, 0.03, 0.09, 0.15, 0.21, 0.27, 0.33]:
        for y in [0.27, 0.21, 0.15, 0.09, 0.03, -0.03, -0.09, -0.15, -0.21, -0.27]:
            fallback_centers.append((x, y))

    for cx, cy in fallback_centers:
        collision_box = (cx - half_cw, cy - half_cd, cx + half_cw, cy + half_cd)
        collision = any(boxes_overlap(collision_box, obox, collision_margin) for obox in occupied)
        if collision:
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
        if avoid_boxes is not None:
            if any(boxes_overlap(region_box, abox, margin=avoid_gap) for abox in avoid_boxes):
                continue
        if min_gap_to_fixtures is not None:
            if any(boxes_overlap(region_box, fbox, margin=min_gap_to_fixtures) for fbox in fixture_boxes):
                continue

        region_name = f"{obj_type}_init_region"
        counter = 1
        while region_name in regions:
            region_name = f"{obj_type}_init_region_{counter}"
            counter += 1
        return Region(name=region_name, target=table_name, ranges=[region_box]), region_name

    raise RuntimeError(f"Failed to allocate non-overlapping region for {obj_type} on {table_name}")


def get_table_name(fixtures: Dict[str, str]) -> str:
    """Get the main table name from fixtures."""
    priority = ['kitchen_table', 'living_room_table', 'study_table', 'main_table', 'floor']
    for table in priority:
        if table in fixtures:
            return table
    for inst, ftype in fixtures.items():
        if 'table' in ftype.lower() or 'floor' in ftype.lower():
            return inst
    return list(fixtures.keys())[0] if fixtures else "main_table"


def extract_object_type(instance: str) -> str:
    """Extract object type from instance name like butter_1 -> butter."""
    if instance.endswith('_1') or instance.endswith('_2'):
        return instance.rsplit('_', 1)[0]
    return instance


def _initialized_instances(init_stmts: List[str]) -> Set[str]:
    return {stmt.split()[1] for stmt in init_stmts if stmt.startswith("(On ")}


def _add_object_if_missing(output: BDDLFile, instance: str, obj_type: str) -> None:
    _add_object_unique(output, instance, obj_type, prefer_name=instance)


def _alloc_unique_region_name(existing: Set[str], base: str) -> str:
    if base not in existing:
        return base
    i = 1
    while f"{base}_{i}" in existing:
        i += 1
    return f"{base}_{i}"


def _next_available_instance_name(existing: Set[str], instance: str) -> str:
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


def _add_object_unique(output: BDDLFile, instance: str, obj_type: str, *, prefer_name: str) -> str:
    """
    Add a movable object to output, renaming if needed to avoid instance-name collisions.
    Returns the final instance name used.
    """
    existing = set(output.objects) | set(output.fixtures)
    desired = prefer_name
    if desired in existing:
        # If same type already exists under this name, do nothing.
        if output.objects.get(desired) == obj_type:
            return desired
        desired = _next_available_instance_name(existing, desired)

    output.objects[desired] = obj_type

    if obj_type in ['basket', 'wooden_tray']:
        region_name = _alloc_unique_region_name(set(output.regions), "contain_region")
        output.regions[region_name] = Region(name=region_name, target=desired)

    return desired


def _ensure_object_is_initialized_on_table(
    output: BDDLFile,
    *,
    table_name: str,
    instance: str,
    obj_type: str,
    is_manip: bool = False,
    min_gap: float = MIN_REGION_GAP,
    collision_margin: float = COLLISION_MARGIN,
) -> None:
    initialized = _initialized_instances(output.init)
    if instance in initialized:
        return

    avoid_boxes = _avoid_boxes_for_large_items(
        output,
        table_name=table_name,
        exclude_instance=instance,
        include_large_movable=(obj_type not in {"basket", "wooden_tray"}),
    )
    region, region_name = allocate_region(
        table_name,
        obj_type,
        output.regions,
        min_gap=min_gap,
        max_extent=MAX_MANIP_REGION_EXTENT if is_manip else None,
        require_within_bound=REACH_BOUND if is_manip else None,
        min_gap_to_fixtures=MIN_MANIP_FIXTURE_GAP if is_manip else None,
        collision_margin=collision_margin,
        avoid_boxes=avoid_boxes,
        avoid_gap=LARGE_OBJECT_GAP,
        occupied_region_boxes=_occupied_table_boxes_from_init(output.init, output.regions, table_name),
    )
    output.regions[region_name] = region
    output.init.append(f"(On {instance} {table_name}_{region_name})")


def _parse_goal_atoms(goal: str) -> List[List[str]]:
    # goal is usually a single atom like "(On butter_1 plate_1)".
    atoms = re.findall(r"\(([^()]+)\)", goal)
    return [a.strip().split() for a in atoms if a.strip()]


def _infer_manip_and_target_from_goal(goal: str) -> Tuple[Optional[str], Optional[str]]:
    for tokens in _parse_goal_atoms(goal):
        if not tokens:
            continue
        pred = tokens[0]
        if pred == "On" and len(tokens) >= 3:
            return tokens[1], tokens[2]
    return None, None


def _support_object_for_target(target: str, regions: Dict[str, Region]) -> Optional[str]:
    if target in regions:
        return regions[target].target
    m = re.match(r"^(.+_\d+)_.+$", target)
    if m:
        return m.group(1)
    return None


def _filter_scene_by_take(
    scene_bddl: BDDLFile,
    *,
    table_name: str,
    take: List[str],
    goal: str,
) -> Tuple[Dict[str, str], Dict[str, str], Dict[str, Region], List[str]]:
    """
    Filter a source scene to only keep the explicitly requested fixtures/objects/regions.

    This is important for ER-GOAL because many LIBERO-90 scenes contain additional clutter objects;
    carrying all of them over can make it impossible to place the new manipulated object without
    region overlaps.
    """
    keep_instances: Set[str] = {table_name}
    keep_region_names: Set[str] = set()

    # Map "instance_regionName" -> regionName (for regions that target a fixture/object instance).
    prefixed_region_to_name: Dict[str, str] = {}
    for region_name, region in scene_bddl.regions.items():
        if region.target == table_name:
            continue
        prefixed_region_to_name[f"{region.target}_{region_name}"] = region_name

    for token in take:
        if token in {"scene_layout"}:
            continue
        if token in scene_bddl.fixtures or token in scene_bddl.objects:
            keep_instances.add(token)
            continue
        # If token references a fixture-internal region via "<instance>_<regionName>".
        region_name = prefixed_region_to_name.get(token)
        if region_name is not None:
            keep_region_names.add(region_name)
            keep_instances.add(scene_bddl.regions[region_name].target)

    fixtures: Dict[str, str] = {k: v for k, v in scene_bddl.fixtures.items() if k in keep_instances}
    objects: Dict[str, str] = {k: v for k, v in scene_bddl.objects.items() if k in keep_instances}

    # Filter init predicates to only keep those that reference kept instances.
    filtered_init: List[str] = []
    for stmt in scene_bddl.init:
        s = stmt.strip()
        if s.startswith("(On "):
            parsed = _parse_on_stmt(stmt)
            if parsed is None:
                continue
            inst, _ = parsed
            if inst in fixtures or inst in objects:
                filtered_init.append(stmt)
            continue
        for prefix in ("(Open ", "(Close ", "(Turnon ", "(Turnoff "):
            if s.startswith(prefix):
                subj = s.replace("(", "").replace(")", "").split()[1]
                if subj in fixtures or subj in objects:
                    filtered_init.append(stmt)
                break
        else:
            # Keep unknown predicates only if they mention kept instances (conservative).
            if any(f" {inst} " in s or s.endswith(f" {inst})") for inst in (set(fixtures) | set(objects))):
                filtered_init.append(stmt)

    # Keep regions required by the kept init placements onto the table.
    prefix = f"{table_name}_"
    for stmt in filtered_init:
        parsed = _parse_on_stmt(stmt)
        if parsed is None:
            continue
        _, region_key = parsed
        if not region_key.startswith(prefix):
            continue
        keep_region_names.add(region_key[len(prefix):])

    regions: Dict[str, Region] = {}
    for name, region in scene_bddl.regions.items():
        if name in keep_region_names:
            regions[name] = region
            continue
        # Keep fixture/object-internal regions (e.g. cook_region, drawer regions), but do NOT keep
        # unrelated table-targeted regions unless explicitly referenced by `take` or by kept init.
        if region.target == table_name:
            continue
        if region.target in fixtures or region.target in objects:
            regions[name] = region

    return fixtures, objects, regions, filtered_init


def _clamp_region_in_place(region: Region, max_extent: float) -> None:
    if not region.ranges:
        return
    x_min, y_min, x_max, y_max = region.ranges[0]
    region.ranges = [_clamp_box_extent((x_min, y_min, x_max, y_max), max_extent=max_extent)]


def _rename_instance_everywhere(output: BDDLFile, old: str, new: str) -> None:
    if old == new:
        return
    if old in output.objects:
        output.objects[new] = output.objects.pop(old)
    if old in output.fixtures:
        output.fixtures[new] = output.fixtures.pop(old)
    for region in output.regions.values():
        if region.target == old:
            region.target = new
    output.init = [_token_replace(stmt, old, new) for stmt in output.init]
    output.goal = _token_replace(output.goal, old, new)
    output.obj_of_interest = [new if x == old else x for x in output.obj_of_interest]


def _ensure_manip_is_instance_one(output: BDDLFile, manip_obj: str) -> str:
    base = _extract_instance_base(manip_obj)
    if base is None or manip_obj.endswith("_1"):
        return manip_obj
    desired = f"{base}_1"
    if desired == manip_obj:
        return manip_obj
    if desired not in output.objects and desired not in output.fixtures:
        _rename_instance_everywhere(output, manip_obj, desired)
        return desired
    # Swap if desired already exists.
    swap_tmp = f"{base}__tmp_swap__"
    _rename_instance_everywhere(output, desired, swap_tmp)
    _rename_instance_everywhere(output, manip_obj, desired)
    _rename_instance_everywhere(output, swap_tmp, manip_obj)
    return desired


def _find_on_init_stmt(output: BDDLFile, instance: str) -> Optional[Tuple[int, str]]:
    prefix = f"(On {instance} "
    for i, stmt in enumerate(output.init):
        if stmt.strip().startswith(prefix):
            return i, stmt
    return None


def _extract_table_region_name(table_name: str, on_stmt: str) -> Optional[str]:
    parsed = _parse_on_stmt(on_stmt)
    if parsed is None:
        return None
    _, region_key = parsed
    prefix = f"{table_name}_"
    if not region_key.startswith(prefix):
        return None
    return region_key[len(prefix):]


def _reposition_support_object_if_needed(
    output: BDDLFile,
    table_name: str,
    support_instance: str,
) -> None:
    """
    Ensure the support object/fixture that defines the placement target is reachable in table frame.
    Only applies if the support object is placed on the table via a table-targeted region.
    """
    found = _find_on_init_stmt(output, support_instance)
    if not found:
        return
    idx, stmt = found
    region_name = _extract_table_region_name(table_name, stmt)
    if region_name is None:
        return
    region = output.regions.get(region_name)
    if region is None or not region.ranges or region.target != table_name:
        return
    r = region.ranges[0]
    current_box = (r[0], r[1], r[2], r[3])
    if _within_abs_bound(current_box, REACH_BOUND):
        return

    obj_type = extract_object_type(support_instance)
    regions_view = dict(output.regions)
    regions_view.pop(region_name, None)
    try:
        new_region, new_region_name = allocate_region(
            table_name,
            obj_type,
            regions_view,
            require_within_bound=REACH_BOUND,
            min_gap=MIN_REGION_GAP,
            occupied_region_boxes=_occupied_table_boxes_from_init(output.init, regions_view, table_name),
        )
    except RuntimeError as e:
        print(f"  [warn] could not reposition support object '{support_instance}' for reachability: {e}")
        return

    output.regions[new_region_name] = new_region
    output.init[idx] = f"(On {support_instance} {table_name}_{new_region_name})"


def generate_er_goal_bddl(task_spec: dict, bddl_base: str) -> BDDLFile:
    """Generate a single ER-GOAL BDDL file using v3.0 format."""
    source_b = task_spec['source_b']
    source_a = task_spec['source_a']
    source_c = task_spec.get('source_c')
    
    scene_file = os.path.join(bddl_base, source_b['file'])
    scene_bddl = parse_bddl_file(scene_file)
    
    table_name = get_table_name(scene_bddl.fixtures)
    
    problem_name_map = {
        'kitchen_table': 'LIBERO_Kitchen_Tabletop_Manipulation',
        'living_room_table': 'LIBERO_Living_Room_Tabletop_Manipulation',
        'study_table': 'LIBERO_Study_Tabletop_Manipulation',
    }
    problem_name = problem_name_map.get(table_name, 'LIBERO_Tabletop_Manipulation')
    
    output = BDDLFile(
        problem_name=problem_name,
        language=task_spec['instruction'],
    )

    # Filter the base scene to essentials so we can reliably place additional objects.
    source_b_take = source_b.get("take", [])
    filtered_fixtures, filtered_objects, filtered_regions, filtered_init = _filter_scene_by_take(
        scene_bddl,
        table_name=table_name,
        take=source_b_take,
        goal=task_spec["goal"],
    )
    output.fixtures = filtered_fixtures
    output.objects = dict(filtered_objects)
    output.regions = dict(filtered_regions)
    output.init = list(filtered_init)
    base_initialized: Set[str] = _initialized_instances(output.init)

    # Determine manipulated object and placement target from the goal early so we can enforce constraints.
    raw_goal = task_spec["goal"]
    manip_obj, placement_target = _infer_manip_and_target_from_goal(raw_goal)

    take_items = source_a.get('take', [])
    for item in take_items:
        if item.endswith('_1') or item.endswith('_2'):
            obj_type = extract_object_type(item)
            _add_object_if_missing(output, item, obj_type)

    # For the last 10 tasks (three-source), enrich the scene by importing *all movable objects*
    # from the distractor scene (source_c). Fixed fixtures are excluded.
    extra_instances: List[Tuple[str, str]] = []
    if source_c is not None:
        source_c_file = os.path.join(bddl_base, source_c["file"])
        source_c_bddl = parse_bddl_file(source_c_file)
        for inst, otype in source_c_bddl.objects.items():
            final_name = _add_object_unique(output, inst, otype, prefer_name=inst)
            extra_instances.append((final_name, otype))
    
    # (Scene objects already populated via filtering above.)
    
    # Fix goal by replacing invalid fixture/region references
    goal = raw_goal
    fixture_names = set(output.fixtures.keys())
    
    # Auto-fix cabinet mismatches
    if 'wooden_cabinet_1' in goal and 'wooden_cabinet_1' not in fixture_names:
        if 'white_cabinet_1' in fixture_names:
            goal = goal.replace('wooden_cabinet_1', 'white_cabinet_1')
    if 'white_cabinet_1' in goal and 'white_cabinet_1' not in fixture_names:
        if 'wooden_cabinet_1' in fixture_names:
            goal = goal.replace('white_cabinet_1', 'wooden_cabinet_1')
    
    output.goal = goal

    # Constraint 5: if multiple same-type objects exist, ensure manipulated object is *_1.
    if manip_obj is not None:
        output.obj_of_interest = [manip_obj]
        old_manip = manip_obj
        manip_obj = _ensure_manip_is_instance_one(output, manip_obj)
        output.obj_of_interest = [manip_obj]
        if manip_obj != old_manip:
            take_items = [manip_obj if x == old_manip else x for x in take_items]
        # Keep goal in sync if it referenced e.g. *_2.
        manip_obj, placement_target = _infer_manip_and_target_from_goal(output.goal)

    # Constraint 3: clamp goal placement region size (if target is an explicit region with ranges).
    if placement_target is not None and placement_target in output.regions:
        _clamp_region_in_place(output.regions[placement_target], max_extent=MAX_MANIP_REGION_EXTENT)

    # Note: We intentionally do NOT reposition the placement target's support object here.
    # In some base scenes (e.g., cabinet-at-front layouts), moving large fixtures to satisfy
    # reachability can make it impossible to place the manipulated object with strict
    # non-overlap + min-gap constraints.
    
    for item in take_items:
        if item.endswith('_1') or item.endswith('_2'):
            obj_type = extract_object_type(item)
            is_manip = manip_obj is not None and item == manip_obj
            _ensure_object_is_initialized_on_table(
                output,
                table_name=table_name,
                instance=item,
                obj_type=obj_type,
                is_manip=is_manip,
                min_gap=EXTRA_OBJ_REGION_GAP if not is_manip else EXTRA_OBJ_REGION_GAP,
                collision_margin=EXTRA_OBJ_COLLISION_MARGIN if not is_manip else EXTRA_OBJ_COLLISION_MARGIN,
            )
    
    if source_c is not None:
        # Place all imported movable objects (from source_a/source_c scene BDDLs).
        for item, obj_type in extra_instances:
            if not (item.endswith("_1") or item.endswith("_2")):
                continue
            is_manip = manip_obj is not None and item == manip_obj
            _ensure_object_is_initialized_on_table(
                output,
                table_name=table_name,
                instance=item,
                obj_type=obj_type,
                is_manip=is_manip,
                min_gap=EXTRA_OBJ_REGION_GAP if not is_manip else EXTRA_OBJ_REGION_GAP,
                collision_margin=EXTRA_OBJ_COLLISION_MARGIN if not is_manip else EXTRA_OBJ_COLLISION_MARGIN,
            )

    # Final pass: enforce that *all* table placements in init have non-overlapping region ranges.
    fixed_instances: Set[str] = {k for k in output.fixtures.keys() if k != table_name}
    # Keep original scene placements fixed; only re-place newly added objects.
    fixed_instances |= base_initialized
    if manip_obj is not None:
        fixed_instances.add(manip_obj)
    _enforce_non_overlapping_table_placements(
        output,
        table_name,
        fixed_instances=fixed_instances,
        min_gap=EXTRA_OBJ_REGION_GAP,
    )

    return output


def main():
    parser = argparse.ArgumentParser(description="Generate ER-GOAL BDDL files")
    parser.add_argument("--yaml-file", type=str, default="er_extension/task_specs/er_goal_tasks.yaml")
    parser.add_argument("--bddl-base", type=str, default="libero/libero/bddl_files")
    parser.add_argument("--output-dir", type=str, default="libero/libero/bddl_files/er_goal")
    parser.add_argument("--task-id", type=str, help="Generate only specific task ID")
    args = parser.parse_args()
    
    os.makedirs(args.output_dir, exist_ok=True)
    
    with open(args.yaml_file, 'r') as f:
        yaml_config = yaml.safe_load(f)
    
    tasks = yaml_config['tasks']
    if args.task_id:
        tasks = [t for t in tasks if args.task_id in t['id']]
    
    success_count = 0
    for task_spec in tasks:
        task_id = task_spec['id']
        
        print(f"Generating: {task_id}")
        
        try:
            output = generate_er_goal_bddl(task_spec, args.bddl_base)
            output_file = os.path.join(args.output_dir, f"{task_id}.bddl")
            with open(output_file, 'w') as f:
                f.write(output.to_bddl())
            print(f"  -> {output_file}")
            success_count += 1
        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\nGenerated {success_count}/{len(tasks)} BDDL files")


if __name__ == "__main__":
    main()
