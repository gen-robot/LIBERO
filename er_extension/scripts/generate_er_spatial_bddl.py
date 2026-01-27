#!/usr/bin/env python3
"""
Generate ER-SPATIAL BDDL files from task specifications.
Updated to work with v3.0 YAML format (source_a, source_b, source_c).
"""

import os
import re
import random
import yaml
import argparse
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Set

from er_constants import (
    OBJECT_SIZES, COLLISION_MARGIN, PLACEMENT_TOLERANCE, get_object_size,
    OBJECT_PLACEMENT_POSITIONS
)
from er_sim_constraints import (
    MIN_REGION_GAP,
    MIN_MANIP_FIXTURE_GAP,
    MAX_MANIP_REGION_EXTENT,
    REACH_BOUND,
    add_object_unique,
    alloc_unique_region_name,
    allocate_region as allocate_region_constrained,
    allocate_region_near_center,
    ensure_instance_one,
    infer_manip_and_target_from_goal,
    occupied_table_region_boxes_from_init,
    remove_instance_table_placement,
    table_on_region_box,
    box_center,
)

SPATIAL_OFFSETS = {
    'next_to': (-0.12, 0.0),   # Place to the left of landmark
    'left_of': (-0.14, 0.0),   # Place to the left
    'right_of': (0.14, 0.0),   # Place to the right
    'in_front_of': (0.0, 0.12), # Place in front (toward camera)
    'behind': (0.0, -0.12),    # Place behind (away from camera)
    'on': (0.0, 0.0),          # Place on top of (same position, for stacking)
    'between': (0.0, 0.0),     # For 'between' we need special handling with two landmarks
}

# Occupancy-heavy items to prune and space out.
LARGE_FOOTPRINT_TYPES = {
    "wooden_cabinet",
    "white_cabinet",
    "basket",
    "frypan",
    "wooden_tray",
    "wooden_two_layer_shelf",  # cabinet shelf
    "wine_rack",
}

# Some assets use long names; treat substring matches as large footprint too.
def _is_large_footprint_type(obj_type: str) -> bool:
    if obj_type in LARGE_FOOTPRINT_TYPES:
        return True
    t = obj_type.lower()
    return any(k in t for k in ["cabinet", "basket", "frypan", "wooden_tray", "wine_rack", "shelf"])

# Spatial rule constants requested by the user.
MIN_NEXT_TO_GAP = 0.08
MAX_NEXT_TO_DISTANCE = 0.22
MIN_DISTRACTOR_DISTANCE = 0.33
MAX_LARGE_ITEMS = 3
MIN_LARGE_ITEM_GAP = 0.18


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


def get_occupied_boxes(regions: Dict[str, Region]) -> List[Tuple[float, float, float, float]]:
    """Get occupied boxes using actual object sizes from OBJECT_SIZES.
    
    Considers both *_init_region patterns and fixture regions (cabinet_region, stove_region).
    """
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
            
        obj_w, obj_d = get_object_size(obj_type)
        occupied.append((cx - obj_w/2, cy - obj_d/2, cx + obj_w/2, cy + obj_d/2))
    return occupied


def _allocate_region_on_table(output: BDDLFile, table_name: str, obj_type: str) -> Tuple[Region, str]:
    occupied_boxes = occupied_table_region_boxes_from_init(output.init, output.regions, table_name)
    return allocate_region_constrained(
        table_name,
        obj_type,
        output.regions,
        region_cls=Region,
        min_gap=MIN_REGION_GAP,
        occupied_region_boxes=occupied_boxes,
    )


def _allocate_region_at_offset(
    output: BDDLFile,
    table_name: str,
    obj_type: str,
    *,
    desired_center: Tuple[float, float],
    is_manip: bool,
) -> Tuple[Region, str]:
    occupied_boxes = occupied_table_region_boxes_from_init(output.init, output.regions, table_name)
    return allocate_region_near_center(
        table_name,
        obj_type,
        output.regions,
        region_cls=Region,
        desired_center=desired_center,
        min_gap=MIN_REGION_GAP,
        max_extent=MAX_MANIP_REGION_EXTENT if is_manip else None,
        require_within_bound=REACH_BOUND if is_manip else None,
        min_gap_to_fixtures=MIN_MANIP_FIXTURE_GAP if is_manip else None,
        occupied_region_boxes=occupied_boxes,
    )


def _instance_base(name: str) -> str:
    m = re.match(r"^(.+)_\d+$", name)
    return m.group(1) if m else name


def _region_center(region: Region) -> Optional[Tuple[float, float]]:
    if not region.ranges:
        return None
    x1, y1, x2, y2 = region.ranges[0]
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

def _euclidean(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    return (dx * dx + dy * dy) ** 0.5


def _get_instance_table_region_name(init_stmts: List[str], table_name: str, instance: str) -> Optional[str]:
    prefix = f"{table_name}_"
    for stmt in init_stmts:
        stmt = stmt.strip()
        if not stmt.startswith("(On "):
            continue
        parts = stmt.replace("(", "").replace(")", "").split()
        if len(parts) < 3:
            continue
        if parts[1] != instance:
            continue
        key = parts[2]
        if not key.startswith(prefix):
            return None
        return key[len(prefix):]
    return None


def _ensure_two_instances_for_manip(output: BDDLFile, *, manip_obj: str) -> Tuple[str, str]:
    """
    Ensure the manipulated object type has at least 2 instances in the environment.
    Returns (manip_instance, distractor_instance).
    """
    base = _instance_base(manip_obj)
    manip = f"{base}_1"
    distractor = f"{base}_2"

    if manip_obj != manip:
        manip = ensure_instance_one(output, manip_obj)
        base = _instance_base(manip)
        manip = f"{base}_1"
        distractor = f"{base}_2"

    if manip not in output.objects:
        output.objects[manip] = base
    if distractor not in output.objects and distractor not in output.fixtures:
        output.objects[distractor] = base
    return manip, distractor


def _delete_instance_everywhere(output: BDDLFile, instance: str) -> None:
    output.objects.pop(instance, None)
    output.fixtures.pop(instance, None)
    output.regions = {k: v for k, v in output.regions.items() if v.target != instance}
    filtered_init: List[str] = []
    for stmt in output.init:
        s = stmt.strip()
        if s.startswith("(On "):
            parts = s.replace("(", "").replace(")", "").split()
            if len(parts) >= 2 and parts[1] == instance:
                continue
        filtered_init.append(stmt)
    output.init = filtered_init


def _filter_invalid_on_statements(output: BDDLFile) -> None:
    """
    Drop `(On <instance> <placement>)` statements that reference deleted/missing entities.

    This keeps downstream tools (e.g. visualization) from crashing when scene pruning
    removes a fixture/object that was used as a placement target.
    """
    valid_instances: Set[str] = set(output.objects.keys()) | set(output.fixtures.keys())
    valid_region_names: Set[str] = set(output.regions.keys())
    valid_fixture_prefixes: Set[str] = set(output.fixtures.keys())

    filtered_init: List[str] = []
    for init_stmt in output.init:
        stmt = init_stmt.strip()
        if not stmt.startswith("(On "):
            filtered_init.append(init_stmt)
            continue
        parts = stmt.replace("(", "").replace(")", "").split()
        if len(parts) < 3:
            continue
        subj = parts[1]
        placement_key = parts[2]

        if subj not in valid_instances:
            continue

        # Case 1: placing on a fixture directly: `(On obj fixture)`
        if placement_key in valid_instances:
            filtered_init.append(init_stmt)
            continue

        # Case 2: placing on a fixture-scoped region: `<fixture>_<region>`
        if "_" not in placement_key:
            continue
        fixture, region = placement_key.split("_", 1)
        if fixture not in valid_fixture_prefixes:
            continue
        if region not in valid_region_names:
            continue

        filtered_init.append(init_stmt)

    output.init = filtered_init


def _keep_only_instances(output: BDDLFile, *, keep_instances: Set[str], keep_table: bool = True) -> None:
    """
    Remove all non-kept objects/fixtures (and their regions/init placements) from the scene.
    Always keeps the main table fixture by default.
    """
    table_name = get_table_name(output.fixtures) if keep_table else None
    if table_name is not None:
        keep_instances = set(keep_instances) | {table_name}

    for inst in list(output.objects.keys()):
        if inst not in keep_instances:
            _delete_instance_everywhere(output, inst)
    for inst in list(output.fixtures.keys()):
        if inst not in keep_instances:
            _delete_instance_everywhere(output, inst)
    _filter_invalid_on_statements(output)


def _prune_large_items(output: BDDLFile, *, keep_instances: Set[str]) -> None:
    return _prune_large_items_with_limit(output, keep_instances=keep_instances, max_large=MAX_LARGE_ITEMS)


def _prune_large_items_with_limit(output: BDDLFile, *, keep_instances: Set[str], max_large: int) -> None:
    large_present = [inst for inst, typ in {**output.fixtures, **output.objects}.items() if _is_large_footprint_type(typ)]
    if len(large_present) <= max_large:
        return

    candidates: List[str] = []
    for inst, typ in output.objects.items():
        if inst in keep_instances:
            continue
        if _is_large_footprint_type(typ):
            candidates.append(inst)
    for inst, typ in output.fixtures.items():
        if inst in keep_instances:
            continue
        if _is_large_footprint_type(typ):
            candidates.append(inst)

    for inst in candidates:
        if len(large_present) <= max_large:
            break
        if inst in output.objects or inst in output.fixtures:
            _delete_instance_everywhere(output, inst)
            large_present = [x for x in large_present if x != inst]


def _instances_referenced_in_goal(goal: str) -> Set[str]:
    # Conservative: pull all tokens that look like instance names (contain '_' or end with digits).
    atoms = re.findall(r"\(([^()]+)\)", goal or "")
    out: Set[str] = set()
    for atom in atoms:
        toks = atom.strip().split()
        for t in toks[1:]:
            if "_" in t or re.search(r"\d$", t):
                out.add(t)
    return out


def _support_instance_from_target(target: Optional[str]) -> Optional[str]:
    """
    For goals like:
      - (On A plate_1) => support instance is plate_1
      - (In A basket_1_contain_region) => support instance is basket_1
    """
    if not target:
        return None
    if target.endswith("_contain_region"):
        return target[: -len("_contain_region")]
    return target


def _rand_centers(count: int, *, bound: float = 0.22) -> List[Tuple[float, float]]:
    # Table-frame sampling; bound is kept within REACH_BOUND for safety.
    out: List[Tuple[float, float]] = []
    for _ in range(count):
        out.append((random.uniform(-bound, bound), random.uniform(-bound, bound)))
    return out


def _set_point_region(
    output: BDDLFile,
    *,
    table_name: str,
    instance: str,
    center: Tuple[float, float],
    region_base: str,
    eps: float = 1e-4,
) -> None:
    """
    Force an instance's table placement to a degenerate (point) region centered at `center`.
    This is used to satisfy strict geometric constraints defined on region centers.
    """
    # Remove any existing table placement(s) for this instance to avoid multiple
    # `(On instance ...)` statements, which can confuse downstream samplers.
    remove_instance_table_placement(output, table_name, instance)
    output.init = [
        stmt for stmt in output.init
        if not (stmt.startswith("(On ") and stmt.split()[1] == instance)
    ]
    region_name = alloc_unique_region_name(set(output.regions.keys()), region_base)
    cx, cy = center
    box = (cx - eps, cy - eps, cx + eps, cy + eps)
    output.regions[region_name] = Region(name=region_name, target=table_name, ranges=[box])
    output.init.append(f"(On {instance} {table_name}_{region_name})")


def _pick_point_layout(
    *,
    b_center: Tuple[float, float],
) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    """
    Given landmark center, choose (a1_center, a2_center) such that:
      - dist(a1,b) in [MIN_NEXT_TO_GAP, MAX_NEXT_TO_DISTANCE]
      - dist(a2,b) >= MIN_DISTRACTOR_DISTANCE
    All points must remain within a conservative table bound.
    """
    bx, by = b_center
    bound = min(0.22, REACH_BOUND)

    def _within(p: Tuple[float, float]) -> bool:
        return abs(p[0]) <= bound and abs(p[1]) <= bound

    # A1: fixed offset 0.10 on x axis (guarantees >=0.08 and <=0.15).
    a1 = (bx + 0.10, by)
    if not _within(a1):
        a1 = (bx - 0.10, by)
    if not _within(a1):
        # Last resort: clamp into bounds.
        a1 = (max(-bound, min(bound, a1[0])), max(-bound, min(bound, a1[1])))

    # A2: choose from candidate offsets that yield >=0.25 distance.
    candidates = [
        (-0.18, -0.18),
        (-0.18, 0.18),
        (0.18, -0.18),
        (0.18, 0.18),
        (-0.20, -0.15),
        (-0.15, -0.20),
        (0.20, -0.15),
        (0.15, -0.20),
    ]
    for dx, dy in candidates:
        a2 = (bx + dx, by + dy)
        if _within(a2) and _euclidean(a2, b_center) >= MIN_DISTRACTOR_DISTANCE:
            return a1, a2

    # Fallback: push to a corner farthest from b.
    corners = [(-bound, -bound), (-bound, bound), (bound, -bound), (bound, bound)]
    corners.sort(key=lambda p: -_euclidean(p, b_center))
    for a2 in corners:
        if _euclidean(a2, b_center) >= MIN_DISTRACTOR_DISTANCE:
            return a1, a2

    # As a last resort (should not happen), return best-effort.
    return a1, corners[0]


def _guess_fixture_landmark_box(
    *,
    landmark_obj: str,
    table_name: str,
    regions: Dict[str, Region],
) -> Optional[Tuple[float, float, float, float]]:
    """
    Heuristic to recover a reasonable table-frame box for fixture landmarks
    (e.g., wine_rack_1, flat_stove_1, desk_caddy_1) when there is no explicit
    `(On landmark table_region)` placement in init.

    We look for a region whose target is the table and whose name contains a
    substring of the landmark's type (e.g., `wine_rack_region` for wine_rack_1).
    """
    landmark_type = extract_object_type(landmark_obj)
    candidates: List[Region] = []
    for name, reg in regions.items():
        if reg.target != table_name or not reg.ranges:
            continue
        lname = name.lower()
        ltype = landmark_type.lower()
        if ltype in lname or lname.startswith(ltype) or lname.endswith(f"{ltype}_region"):
            candidates.append(reg)
    if not candidates:
        return None
    # Prefer the first match; all candidates are table-frame regions with ranges.
    r = candidates[0].ranges[0]
    return (r[0], r[1], r[2], r[3])


def _ensure_all_objects_placed(output: BDDLFile, table_name: str) -> None:
    """
    Post-condition: every non-fixture object in `output.objects` must have at least
    one `(On obj table_region)` placement in init. If missing, allocate a fresh
    region on the main table and place it there.
    """
    placed = {
        stmt.split()[1]
        for stmt in output.init
        if stmt.strip().startswith("(On ")
    }
    for inst, otype in list(output.objects.items()):
        # Skip fixtures and any already placed instances.
        if inst in output.fixtures or inst in placed:
            continue
        try:
            region, region_name = _allocate_region_on_table(output, table_name, otype)
        except RuntimeError:
            # Best-effort: if even a generic placement fails, leave unplaced;
            # downstream tools may choose to ignore or handle these.
            continue
        output.regions[region_name] = region
        output.init.append(f"(On {inst} {table_name}_{region_name})")
        placed.add(inst)


def _ensure_minimum_distractors(
    output: BDDLFile,
    *,
    table_name: str,
    task_relevant: Set[str],
    min_distractors: int = 2,
    max_total: int = 4,
) -> None:
    """
    Ensure there are at least `min_distractors` non-task distractor objects in the
    scene, counting only objects whose type differs from the manipulated object
    type. If necessary, spawn additional generic distractors (from a small, safe
    library of known assets) up to `max_total` total distractors.

    This is used for sparse scenes (e.g., when A/B/C sources contribute very few
    non-task objects), so that ER-SPATIAL tasks always have some clutter.
    """
    # Determine manipulated object type from obj_of_interest[0] when available.
    manip_type: Optional[str] = None
    if output.obj_of_interest:
        manip_type = extract_object_type(output.obj_of_interest[0])

    # Count current distractors (non-task objects and non-table fixtures), but do
    # NOT count same-type instances as the manipulated object as distractors.
    # Same-type objects are considered within-class references instead.
    distractors: Set[str] = set()
    for inst in output.objects.keys():
        if inst in task_relevant:
            continue
        if manip_type is not None and extract_object_type(inst) == manip_type:
            continue
        distractors.add(inst)
    for inst, ftype in output.fixtures.items():
        if inst == table_name:
            continue
        if inst not in task_relevant:
            distractors.add(inst)

    if len(distractors) >= min_distractors:
        return

    # Generic movable distractor types that are known to exist in LIBERO assets.
    # These should be small-to-medium footprint items that rarely cause placement failures.
    GENERIC_DISTRACTOR_TYPES = [
        "black_book",
        "white_yellow_mug",
        "cookies",
        "plate",
        "wine_bottle",
    ]

    # Try to add new distractors until we reach min_distractors or hit max_total.
    for obj_type in GENERIC_DISTRACTOR_TYPES:
        if len(distractors) >= max_total:
            break
        # Skip if we already have some instance of this type that is task-relevant.
        existing_same_type = [
            inst for inst, typ in output.objects.items()
            if extract_object_type(inst) == obj_type
        ]
        # Create a fresh instance name regardless of existing ones, to avoid
        # interfering with task-relevant instances of the same type.
        base_name = f"{obj_type}_distractor"
        prefer_name = base_name if base_name not in output.objects else None
        inst_name = add_object_unique(
            output,
            prefer_name or base_name,
            obj_type,
            prefer_name=prefer_name,
        )
        try:
            region, region_name = _allocate_region_on_table(output, table_name, obj_type)
        except RuntimeError:
            # Placement failed; remove and try next candidate type.
            _delete_instance_everywhere(output, inst_name)
            continue
        output.regions[region_name] = region
        output.init.append(f"(On {inst_name} {table_name}_{region_name})")
        distractors.add(inst_name)
        if len(distractors) >= min_distractors:
            break


def _enforce_large_item_spacing(output: BDDLFile, *, table_name: str, keep_instances: Set[str]) -> None:
    def _table_center_for(inst: str) -> Optional[Tuple[float, float]]:
        region_name = _get_instance_table_region_name(output.init, table_name, inst)
        if region_name is None:
            return None
        reg = output.regions.get(region_name)
        if reg is None or reg.target != table_name:
            return None
        return _region_center(reg)

    large_instances: List[str] = []
    for inst, typ in output.objects.items():
        if _is_large_footprint_type(typ) and inst != table_name:
            if _get_instance_table_region_name(output.init, table_name, inst) is not None:
                large_instances.append(inst)

    for _ in range(6):
        centers = {inst: _table_center_for(inst) for inst in large_instances}
        bad_pair = None
        for i in range(len(large_instances)):
            for j in range(i + 1, len(large_instances)):
                a, b = large_instances[i], large_instances[j]
                ca, cb = centers.get(a), centers.get(b)
                if ca is None or cb is None:
                    continue
                if abs(ca[0] - cb[0]) < MIN_LARGE_ITEM_GAP and abs(ca[1] - cb[1]) < MIN_LARGE_ITEM_GAP:
                    bad_pair = (a, b)
                    break
            if bad_pair:
                break
        if not bad_pair:
            return
        a, b = bad_pair
        to_move = a if a not in keep_instances else (b if b not in keep_instances else None)
        if to_move is None:
            return
        remove_instance_table_placement(output, table_name, to_move)
        obj_type = extract_object_type(to_move)
        region, region_name = _allocate_region_on_table(output, table_name, obj_type)
        output.regions[region_name] = region
        output.init.append(f"(On {to_move} {table_name}_{region_name})")


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
    """Extract object type from instance name."""
    if instance.endswith('_1') or instance.endswith('_2'):
        return instance.rsplit('_', 1)[0]
    return instance


def has_real_table(bddl: BDDLFile) -> bool:
    """Check if BDDL has a real table (not floor)."""
    table = get_table_name(bddl.fixtures)
    return table != 'floor'


def _ensure_container_contain_region(output: BDDLFile, instance: str, obj_type: str) -> None:
    """
    Ensure a per-container contain region exists with a stable, non-conflicting name.

    Goal-init generation and many downstream tools expect basket to use the canonical
    region key `basket_1_contain_region`. To avoid accidental renaming (e.g. contain_region_1)
    when multiple containers exist, we:
      - reserve `contain_region` for baskets
      - use `<obj_type>_contain_region` for other containers (e.g. wooden_tray_contain_region)
    """
    if obj_type not in ["basket", "wooden_tray"]:
        return
    def _rename_region(old_name: str, new_name: str) -> None:
        if old_name == new_name:
            return
        region = output.regions.pop(old_name)
        region.name = new_name
        output.regions[new_name] = region
        old_key = f"{region.target}_{old_name}"
        new_key = f"{region.target}_{new_name}"
        # Update any existing references to the region key in init/goal.
        output.init = [stmt.replace(old_key, new_key) for stmt in output.init]
        output.goal = (output.goal or "").replace(old_key, new_key)

    if obj_type == "basket":
        # Reserve the canonical `contain_region` for basket to keep the goal key stable:
        # `basket_1_contain_region`.
        existing = output.regions.get("contain_region")
        if existing is not None and existing.target != instance:
            # Move the other container's region out of the way.
            other_type = extract_object_type(existing.target)
            _rename_region("contain_region", f"{other_type}_contain_region")
        region_name = "contain_region"
    else:
        region_name = f"{obj_type}_contain_region"

    # If desired name is taken by a different target, fall back to a unique suffix.
    existing = output.regions.get(region_name)
    if existing is not None and existing.target != instance:
        suffix = 1
        candidate = f"{region_name}_{suffix}"
        while candidate in output.regions and output.regions[candidate].target != instance:
            suffix += 1
            candidate = f"{region_name}_{suffix}"
        region_name = candidate

    output.regions[region_name] = Region(name=region_name, target=instance)


def sanitize_unplaceable_fixtures(output: BDDLFile, table_name: str) -> None:
    """
    Guard against fixture-fixture interpenetration caused by missing / invalid fixture placement regions.

    If a fixture is kept but its placement statement references a non-existent or non-ranged region
    (e.g. `(On flat_stove_1 main_table_stove_region)` but `stove_region` is missing in `(:regions ...)`),
    downstream env implementations may place the fixture at a fallback pose, often leading to overlaps.

    This function removes such fixtures and any regions / init statements directly tied to them.
    """
    fixture_instances = [k for k in output.fixtures.keys() if k != table_name]
    if not fixture_instances:
        return

    table_prefix = f"{table_name}_"
    fixtures_to_remove: Set[str] = set()

    for fix_instance in fixture_instances:
        placement_stmt = None
        placement_region_key = None
        for init_stmt in output.init:
            stmt = init_stmt.strip()
            if not stmt.startswith(f"(On {fix_instance} "):
                continue
            parts = stmt.replace("(", "").replace(")", "").split()
            if len(parts) >= 3:
                placement_stmt = init_stmt
                placement_region_key = parts[2]
            break

        if placement_stmt is None or placement_region_key is None:
            fixtures_to_remove.add(fix_instance)
            continue

        if not placement_region_key.startswith(table_prefix):
            fixtures_to_remove.add(fix_instance)
            continue

        placement_region_name = placement_region_key[len(table_prefix):]
        placement_region = output.regions.get(placement_region_name)
        if placement_region is None or not placement_region.ranges or placement_region.target != table_name:
            fixtures_to_remove.add(fix_instance)

    if not fixtures_to_remove:
        return

    for fix_instance in sorted(fixtures_to_remove):
        print(f"  [warn] removing unplaceable fixture '{fix_instance}' (missing/invalid table placement region)")
        output.fixtures.pop(fix_instance, None)

    output.regions = {k: v for k, v in output.regions.items() if v.target not in fixtures_to_remove}

    filtered_init: List[str] = []
    for init_stmt in output.init:
        stmt = init_stmt.strip()
        if not stmt.startswith("(On "):
            filtered_init.append(init_stmt)
            continue
        parts = stmt.replace("(", "").replace(")", "").split()
        if len(parts) < 3:
            filtered_init.append(init_stmt)
            continue
        subj = parts[1]
        region_key = parts[2]
        if subj in fixtures_to_remove:
            continue
        if any(region_key.startswith(f"{fix}_") for fix in fixtures_to_remove):
            continue
        filtered_init.append(init_stmt)
    output.init = filtered_init


def generate_er_spatial_bddl(task_spec: dict, bddl_base: str) -> BDDLFile:
    """Generate a single ER-SPATIAL BDDL file using v3.0 format."""
    source_a = task_spec['source_a']
    source_b = task_spec['source_b']
    source_c = task_spec.get('source_c')
    
    # Parse both sources to find which has the real scene
    bddl_a = parse_bddl_file(os.path.join(bddl_base, source_a['file']))
    bddl_b = parse_bddl_file(os.path.join(bddl_base, source_b['file']))
    
    # Use the source with the real table as the scene base
    if has_real_table(bddl_a):
        scene_bddl = bddl_a
        object_bddl = bddl_b
        object_source = source_b
    else:
        scene_bddl = bddl_b
        object_bddl = bddl_a
        object_source = source_a
    
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
    
    output.fixtures = dict(scene_bddl.fixtures)
    output.regions = dict(scene_bddl.regions)
    output.init = list(scene_bddl.init)
    
    for inst, otype in scene_bddl.objects.items():
        output.objects[inst] = otype

    # Robustness: drop fixtures whose placement regions are missing/invalid to avoid
    # fallback fixture poses that can cause immediate interpenetration.
    sanitize_unplaceable_fixtures(output, table_name=table_name)
    
    # Add objects from the object source (whichever has floor)
    take_items = object_source.get('take', [])
    added_objs = []
    initialized = {stmt.split()[1] for stmt in output.init if stmt.startswith('(On')}
    
    for item in take_items:
        if item.endswith('_1') or item.endswith('_2'):
            obj_type = extract_object_type(item)
            if item not in output.objects:
                final_name = add_object_unique(output, item, obj_type, prefer_name=item)
                added_objs.append(final_name)
                if obj_type in ['basket', 'wooden_tray']:
                    _ensure_container_contain_region(output, final_name, obj_type)
                if final_name not in initialized:
                    region, region_name = _allocate_region_on_table(output, table_name, obj_type)
                    output.regions[region_name] = region
                    output.init.append(f"(On {final_name} {table_name}_{region_name})")
                    initialized.add(final_name)
    
    # Determine manipulation and landmark objects from spatial_relation
    manip_obj = None
    landmark_raw = task_spec.get('landmark')
    relation = task_spec.get('spatial_relation', 'next_to')
    
    # Handle both single landmark and list of landmarks (for 'between')
    if isinstance(landmark_raw, list):
        landmark_obj = landmark_raw[0]
        landmark_obj2 = landmark_raw[1] if len(landmark_raw) > 1 else None
    else:
        landmark_obj = landmark_raw
        landmark_obj2 = None
    
    # Find the main manipulation object (first from source_a take list)
    for item in source_a.get('take', []):
        if (item.endswith('_1') or item.endswith('_2')) and item != landmark_obj and item != landmark_obj2:
            manip_obj = item
            break
    
    # Fix goal by replacing invalid fixture/region references
    goal = task_spec['goal']
    fixture_names = set(output.fixtures.keys())
    
    # Auto-fix cabinet mismatches
    if 'wooden_cabinet_1' in goal and 'wooden_cabinet_1' not in fixture_names:
        if 'white_cabinet_1' in fixture_names:
            goal = goal.replace('wooden_cabinet_1', 'white_cabinet_1')
    if 'white_cabinet_1' in goal and 'white_cabinet_1' not in fixture_names:
        if 'wooden_cabinet_1' in fixture_names:
            goal = goal.replace('white_cabinet_1', 'wooden_cabinet_1')
    
    output.goal = goal

    # Constraint: if multiple same-type objects exist, ensure manipulated object is *_1.
    goal_manip, _ = infer_manip_and_target_from_goal(output.goal)
    if goal_manip is not None and goal_manip in output.objects:
        manip_obj = ensure_instance_one(output, goal_manip)
    else:
        manip_obj = goal_manip or manip_obj

    if manip_obj is None:
        raise RuntimeError("No manipulated object inferred for this spatial task")

    # Rule 1: manipulated object type must have at least 2 instances; *_1 is the manipulated one.
    manip_obj, distractor_obj = _ensure_two_instances_for_manip(output, manip_obj=manip_obj)
    manip_type = extract_object_type(manip_obj)
    distractor_type = extract_object_type(distractor_obj)
    
    initialized = {stmt.split()[1] for stmt in output.init if stmt.startswith('(On')}
    # Note: do not place distractor yet; it can block tight spatial placements.
    
    # Place first landmark
    landmark_center = (0.0, 0.05)
    if landmark_obj and landmark_obj in initialized:
        b = table_on_region_box(table_name=table_name, init_stmts=output.init, regions=output.regions, instance=landmark_obj)
        if b is not None:
            landmark_center = box_center(b)
    if landmark_obj and landmark_obj not in initialized:
        landmark_type = extract_object_type(landmark_obj)
        try:
            landmark_region, landmark_region_name = _allocate_region_on_table(output, table_name, landmark_type)
            output.regions[landmark_region_name] = landmark_region
            output.init.append(f"(On {landmark_obj} {table_name}_{landmark_region_name})")
            lr = landmark_region.ranges[0]
            landmark_center = ((lr[0] + lr[2]) / 2, (lr[1] + lr[3]) / 2)
            initialized.add(landmark_obj)
        except RuntimeError:
            # Late-task fallback: if we can't allocate a region (e.g. very large tray),
            # pin the landmark to a point region to keep the task feasible.
            if task_spec.get("max_large_items") is None or landmark_obj in output.fixtures:
                raise
            _set_point_region(
                output,
                table_name=table_name,
                instance=landmark_obj,
                center=(0.0, 0.05),
                region_base=f"{landmark_type}_landmark_point",
            )
            landmark_center = (0.0, 0.05)
            initialized.add(landmark_obj)

    # Rule 4: prune occupancy-heavy items and enforce spacing.
    keep_instances: Set[str] = {manip_obj, distractor_obj} | ({landmark_obj, landmark_obj2} - {None})
    keep_instances |= _instances_referenced_in_goal(output.goal)
    # Optional: YAML-driven hard filtering for debugging feasibility.
    keep_only = task_spec.get("keep_only")
    if keep_only:
        keep_instances |= set(keep_only)
        _keep_only_instances(output, keep_instances=keep_instances)

    max_large = task_spec.get("max_large_items")
    if max_large is None:
        _prune_large_items(output, keep_instances=keep_instances)
    else:
        # For late tasks, aggressively de-clutter the scene to improve feasibility while
        # preserving all task-relevant instances (manip/distractor/landmark/goal targets).
        _keep_only_instances(output, keep_instances=keep_instances)
        _prune_large_items_with_limit(output, keep_instances=keep_instances, max_large=int(max_large))
    _filter_invalid_on_statements(output)
    _enforce_large_item_spacing(output, table_name=table_name, keep_instances=keep_instances)
    
    # Place second landmark (for 'between' relation)
    landmark_center2 = None
    if landmark_obj2 and landmark_obj2 not in initialized:
        landmark_type2 = extract_object_type(landmark_obj2)
        landmark_region2, landmark_region_name2 = _allocate_region_on_table(output, table_name, landmark_type2)
        output.regions[landmark_region_name2] = landmark_region2
        output.init.append(f"(On {landmark_obj2} {table_name}_{landmark_region_name2})")
        lr2 = landmark_region2.ranges[0]
        landmark_center2 = ((lr2[0] + lr2[2]) / 2, (lr2[1] + lr2[3]) / 2)
        initialized.add(landmark_obj2)
    if landmark_obj2 and landmark_obj2 in initialized and landmark_center2 is None:
        b2 = table_on_region_box(table_name=table_name, init_stmts=output.init, regions=output.regions, instance=landmark_obj2)
        if b2 is not None:
            landmark_center2 = box_center(b2)
    
    # Place manipulation object relative to landmark(s)
    # ALWAYS re-place manip_obj to ensure correct spatial relation (remove old placement first)
    if manip_obj:
        remove_instance_table_placement(output, table_name, manip_obj)
        # Use the ensured types/instances above.

        # If placing the manipulation object relative to a novel landmark becomes infeasible
        # (crowded templates), re-place the landmark to a different table region and retry.
        forbidden_landmark_boxes: List[Tuple[float, float, float, float]] = []
        max_retries = 8

        for attempt in range(max_retries):
            try:
                if relation == "on":
                    # Rule 3: skip min-distance constraints and force A and B to have identical sampled points.
                    if landmark_obj is None:
                        raise RuntimeError("Relation 'on' requires a landmark")
                    if landmark_obj in output.fixtures:
                        raise RuntimeError("Relation 'on' does not support fixture landmarks")
                    landmark_region_name = _get_instance_table_region_name(output.init, table_name, landmark_obj)
                    if landmark_region_name is None or landmark_region_name not in output.regions:
                        landmark_type = extract_object_type(landmark_obj)
                        landmark_region, landmark_region_name = _allocate_region_on_table(output, table_name, landmark_type)
                        output.regions[landmark_region_name] = landmark_region
                        output.init.append(f"(On {landmark_obj} {table_name}_{landmark_region_name})")
                        initialized.add(landmark_obj)
                    landmark_region = output.regions[landmark_region_name]
                    lc = _region_center(landmark_region)
                    if lc is None:
                        raise RuntimeError("Landmark region has no ranges for relation 'on'")
                    cx, cy = lc
                    eps = 1e-4
                    point_box = (cx - eps, cy - eps, cx + eps, cy + eps)
                    # Keep the landmark's original footprint to avoid shrinking large
                    # support objects (e.g., frypans, trays) into a point region,
                    # which can cause severe interpenetration artifacts. Instead,
                    # only force the manipulated object to use a degenerate region
                    # centered on the landmark.
                    manip_region_name = alloc_unique_region_name(set(output.regions.keys()), f"{manip_type}_on_region")
                    output.regions[manip_region_name] = Region(
                        name=manip_region_name,
                        target=table_name,
                        ranges=[point_box],
                    )
                    output.init.append(f"(On {manip_obj} {table_name}_{manip_region_name})")
                    break

                if relation == "next_to":
                    # Rule 2: A1 close to B (axis deltas <= 0.13), A2 far (axis deltas >= 0.25).
                    if landmark_obj is None:
                        raise RuntimeError("Relation 'next_to' requires a landmark")
                    # Determine goal support object C (plate/basket/etc.) so we can re-place it to avoid blocking.
                    _g_manip, _g_target = infer_manip_and_target_from_goal(output.goal)
                    support_instance = _support_instance_from_target(_g_target)

                    # If the YAML specifies `keep_only` (tasks 1–10), use point-regions for the
                    # involved instances. This makes the strict center-distance constraints
                    # feasible regardless of object footprint sizes.
                    if task_spec.get("keep_only"):
                        # Choose a compact layout in table frame.
                        b_center = (0.00, 0.05)
                        a1_center = (0.10, 0.05)  # dist=0.10 (>=0.08 and <=0.15)
                        a2_center = (-0.18, -0.18)  # dist~=0.254 (>=0.25)
                        # Place C away from B while staying within table bounds.
                        c_center = (0.18, -0.18)

                        # Ensure B is placed (movable landmarks only).
                        if landmark_obj not in output.fixtures:
                            _set_point_region(
                                output,
                                table_name=table_name,
                                instance=landmark_obj,
                                center=b_center,
                                region_base=f"{extract_object_type(landmark_obj)}_landmark_point",
                            )
                        # Place goal support object if it's movable and on the table.
                        if support_instance and support_instance in output.objects and support_instance not in output.fixtures:
                            _set_point_region(
                                output,
                                table_name=table_name,
                                instance=support_instance,
                                center=c_center,
                                region_base=f"{extract_object_type(support_instance)}_support_point",
                            )

                        _set_point_region(
                            output,
                            table_name=table_name,
                            instance=manip_obj,
                            center=a1_center,
                            region_base=f"{manip_type}_a1_point",
                        )
                        _set_point_region(
                            output,
                            table_name=table_name,
                            instance=distractor_obj,
                            center=a2_center,
                            region_base=f"{distractor_type}_a2_point",
                        )
                        break

                    def _place_instance_anywhere(instance: str, obj_type: str, *, centers: List[Tuple[float, float]]) -> None:
                        # Fast placement: use unconstrained allocation on the table.
                        remove_instance_table_placement(output, table_name, instance)
                        reg, rname = _allocate_region_on_table(output, table_name, obj_type)
                        output.regions[rname] = reg
                        output.init.append(f"(On {instance} {table_name}_{rname})")

                    def _place_close(instance: str, obj_type: str) -> None:
                        best = None
                        # Dense grid around the landmark; choose closest feasible.
                        step = 0.02
                        span = MAX_NEXT_TO_DISTANCE
                        candidates = []
                        dx = -span
                        while dx <= span + 1e-9:
                            dy = -span
                            while dy <= span + 1e-9:
                                candidates.append((bx + dx, by + dy))
                                dy += step
                            dx += step
                        # Try the closest points first (approx by sorting).
                        candidates.sort(key=lambda p: max(abs(p[0] - bx), abs(p[1] - by)))
                        for cx, cy in candidates:
                            try:
                                reg, rname = _allocate_region_at_offset(
                                    output,
                                    table_name,
                                    obj_type,
                                    desired_center=(cx, cy),
                                    is_manip=True,
                                )
                            except RuntimeError:
                                continue
                            cc = _region_center(reg)
                            if cc is None:
                                continue
                            dist = _euclidean(cc, (bx, by))
                            if dist <= MAX_NEXT_TO_DISTANCE:
                                score = dist
                                if best is None or score < best[0]:
                                    best = (score, reg, rname)
                        if best is None:
                            raise RuntimeError("Failed to place manipulated object close enough to landmark")
                        _, reg, rname = best
                        output.regions[rname] = reg
                        output.init.append(f"(On {instance} {table_name}_{rname})")

                    def _place_far(instance: str, obj_type: str) -> None:
                        # Coarse grid over a broad reachable workspace; pick any point satisfying axis deltas.
                        candidates = []
                        for cx in [x / 100.0 for x in range(-22, 23, 4)]:
                            for cy in [y / 100.0 for y in range(-22, 23, 4)]:
                                if _euclidean((cx, cy), (bx, by)) >= MIN_DISTRACTOR_DISTANCE:
                                    candidates.append((cx, cy))
                        # Prefer points that are farthest (greedy separation).
                        candidates.sort(key=lambda p: -(abs(p[0] - bx) + abs(p[1] - by)))
                        for cx, cy in candidates:
                            try:
                                reg, rname = _allocate_region_at_offset(
                                    output,
                                    table_name,
                                    obj_type,
                                    desired_center=(cx, cy),
                                    is_manip=False,
                                )
                            except RuntimeError:
                                continue
                            cc = _region_center(reg)
                            if cc is None:
                                continue
                            if _euclidean(cc, (bx, by)) >= MIN_DISTRACTOR_DISTANCE:
                                output.regions[rname] = reg
                                output.init.append(f"(On {instance} {table_name}_{rname})")
                                return
                        raise RuntimeError("Failed to place distractor far enough from landmark")

                    # Strong search: repeatedly re-place B (landmark) and C (goal support), then place A1/A2.
                    # This avoids being stuck with the template's initial clutter while keeping strict distances.
                    extra_keep = {x for x in [landmark_obj, support_instance] if x}
                    movable_to_reseed = {x for x in extra_keep if x not in output.fixtures}

                    solved = False
                    for _ in range(120):
                        # Freshly re-place B and C to new non-overlapping table regions.
                        try:
                            if landmark_obj in movable_to_reseed:
                                _place_instance_anywhere(landmark_obj, extract_object_type(landmark_obj), centers=[])
                            if support_instance and support_instance in movable_to_reseed:
                                _place_instance_anywhere(support_instance, extract_object_type(support_instance), centers=[])
                        except RuntimeError:
                            continue

                        landmark_box = table_on_region_box(
                            table_name=table_name,
                            init_stmts=output.init,
                            regions=output.regions,
                            instance=landmark_obj,
                        )
                        if landmark_box is None:
                            continue
                        bx, by = box_center(landmark_box)

                        remove_instance_table_placement(output, table_name, manip_obj)
                        remove_instance_table_placement(output, table_name, distractor_obj)
                        try:
                            _place_close(manip_obj, manip_type)
                            _place_far(distractor_obj, distractor_type)
                        except RuntimeError:
                            continue
                        solved = True
                        break
                    if not solved:
                        # Fallback for late tasks: if the scene still cannot satisfy the strict
                        # next_to constraints, enforce them by collapsing to point regions at
                        # carefully chosen centers (still respecting the required distances).
                        if task_spec.get("max_large_items") is not None:
                            # For movable landmarks, recover placement from init.
                            # For fixture landmarks (e.g. wine_rack_1, flat_stove_1),
                            # infer a suitable table-frame box directly from regions.
                            if landmark_obj in output.fixtures:
                                lbox = _guess_fixture_landmark_box(
                                    landmark_obj=landmark_obj,
                                    table_name=table_name,
                                    regions=output.regions,
                                )
                            else:
                                lbox = table_on_region_box(
                                    table_name=table_name,
                                    init_stmts=output.init,
                                    regions=output.regions,
                                    instance=landmark_obj,
                                )
                            if lbox is None:
                                raise RuntimeError("Failed to locate landmark placement for point-layout fallback")
                            b_center = box_center(lbox)
                            a1_center, a2_center = _pick_point_layout(b_center=b_center)
                            if support_instance and support_instance in output.objects and support_instance not in output.fixtures:
                                _set_point_region(
                                    output,
                                    table_name=table_name,
                                    instance=support_instance,
                                    center=(b_center[0] + 0.18, b_center[1] - 0.18),
                                    region_base=f"{extract_object_type(support_instance)}_support_point",
                                )
                            _set_point_region(
                                output,
                                table_name=table_name,
                                instance=manip_obj,
                                center=a1_center,
                                region_base=f"{manip_type}_a1_point",
                            )
                            _set_point_region(
                                output,
                                table_name=table_name,
                                instance=distractor_obj,
                                center=a2_center,
                                region_base=f"{distractor_type}_a2_point",
                            )
                            solved = True
                        else:
                            raise RuntimeError("Failed to satisfy strict next_to constraints after many re-seeding attempts")

                    break

                if relation == 'between' and landmark_center2:
                    between_center = ((landmark_center[0] + landmark_center2[0]) / 2,
                                      (landmark_center[1] + landmark_center2[1]) / 2)
                    manip_region, manip_region_name = _allocate_region_at_offset(
                        output,
                        table_name,
                        manip_type,
                        desired_center=between_center,
                        is_manip=True,
                    )
                else:
                    offset = SPATIAL_OFFSETS.get(relation, (-0.12, 0.0))
                    desired = (landmark_center[0] + offset[0], landmark_center[1] + offset[1])
                    manip_region, manip_region_name = _allocate_region_at_offset(
                        output,
                        table_name,
                        manip_type,
                        desired_center=desired,
                        is_manip=True,
                    )
                output.regions[manip_region_name] = manip_region
                output.init.append(f"(On {manip_obj} {table_name}_{manip_region_name})")
                break
            except RuntimeError:
                # Only retry by moving the (single) landmark if:
                # - not a between-relation, and
                # - landmark exists and is not a fixed fixture.
                if relation == "between":
                    raise
                if not landmark_obj or landmark_obj in output.fixtures:
                    raise
                # Record current landmark placement so we don't pick it again.
                current_box = table_on_region_box(
                    table_name=table_name,
                    init_stmts=output.init,
                    regions=output.regions,
                    instance=landmark_obj,
                )
                if current_box is not None:
                    forbidden_landmark_boxes.append(current_box)

                # Re-place landmark to a different region on the table.
                remove_instance_table_placement(output, table_name, landmark_obj)
                occ = occupied_table_region_boxes_from_init(output.init, output.regions, table_name)
                # Prevent returning to previously tried landmark placements.
                occ = list(occ) + forbidden_landmark_boxes
                landmark_type = extract_object_type(landmark_obj)
                new_region, new_region_name = allocate_region_constrained(
                    table_name,
                    landmark_type,
                    output.regions,
                    region_cls=Region,
                    min_gap=MIN_REGION_GAP,
                    occupied_region_boxes=occ,
                )
                output.regions[new_region_name] = new_region
                output.init.append(f"(On {landmark_obj} {table_name}_{new_region_name})")
                lr = new_region.ranges[0]
                landmark_center = ((lr[0] + lr[2]) / 2, (lr[1] + lr[3]) / 2)
        else:
            raise RuntimeError(f"Failed to place {manip_obj} relative to {landmark_obj} after {max_retries} retries")

        # Place the distractor instance after successful placement (unless already handled).
        initialized = {stmt.split()[1] for stmt in output.init if stmt.startswith('(On')}
        if distractor_obj not in initialized:
            region, region_name = _allocate_region_on_table(output, table_name, distractor_type)
            output.regions[region_name] = region
            output.init.append(f"(On {distractor_obj} {table_name}_{region_name})")
            initialized.add(distractor_obj)
    
    if source_c:
        # Distractor logic for 3-source tasks:
        # - treat ALL objects from source_c.take as potential distractors (no _1/_2 restriction)
        # - allow large-footprint objects as candidates
        # - aim for at least 2 and at most 3 distractors overall
        # - if possible, ensure at least one large-footprint distractor
        # - if placement of a chosen distractor repeatedly fails, skip it.
        raw_items = [x for x in source_c.get("take", []) if isinstance(x, str)]

        # Identify objects that are already required by the task (goal, keep_only, etc.).
        task_relevant: Set[str] = {
            x
            for x in [
                manip_obj,
                distractor_obj,
                landmark_obj,
                landmark_obj2,
            ]
            if x
        }
        task_relevant |= _instances_referenced_in_goal(output.goal)
        keep_only = task_spec.get("keep_only")
        if keep_only:
            task_relevant |= set(keep_only)

        # Ensure task-relevant instances from source_c are present.
        for item in raw_items:
            if item not in task_relevant:
                continue
            if item in output.objects or item in output.fixtures:
                continue
            obj_type = extract_object_type(item)
            final_name = add_object_unique(output, item, obj_type, prefer_name=item)
            if obj_type in ["basket", "wooden_tray"]:
                _ensure_container_contain_region(output, final_name, obj_type)
            try:
                region, region_name = _allocate_region_on_table(output, table_name, obj_type)
            except RuntimeError:
                # If even task-relevant instances cannot be placed, skip them;
                # do not fail the entire task generation.
                continue
            output.regions[region_name] = region
            output.init.append(f"(On {final_name} {table_name}_{region_name})")

        # Now build candidate pool for *additional* distractors.
        distractor_candidates: List[str] = []
        for item in raw_items:
            # Skip any that are task-relevant (already handled above) or already present.
            if item in task_relevant:
                continue
            if item in output.objects or item in output.fixtures:
                continue
            distractor_candidates.append(item)

        # We aim to add between 2 and 3 distractors from source_c in total.
        # Count currently-added source_c objects that are present in the scene.
        existing_from_c = 0
        for item in raw_items:
            if item in output.objects or item in output.fixtures:
                existing_from_c += 1

        target_total = 3  # prefer up to 3 if possible
        min_total = 2     # but at least 2 if feasible
        remaining_to_add = max(min_total - existing_from_c, 0)
        remaining_to_add = min(remaining_to_add, target_total - existing_from_c)
        if remaining_to_add <= 0:
            # Already have enough source_c objects in the scene.
            pass
        else:
            # Prefer to include at least one large-footprint object if any exist.
            large_candidates = [
                itm for itm in distractor_candidates
                if _is_large_footprint_type(extract_object_type(itm))
            ]
            small_candidates = [
                itm for itm in distractor_candidates
                if itm not in large_candidates
            ]
            random.shuffle(large_candidates)
            random.shuffle(small_candidates)

            chosen: List[str] = []
            if large_candidates:
                chosen.append(large_candidates.pop(0))

            # Fill the rest from both pools until we reach remaining_to_add.
            pools = [large_candidates, small_candidates]
            while len(chosen) < remaining_to_add and any(pools):
                for pool in pools:
                    if pool and len(chosen) < remaining_to_add:
                        chosen.append(pool.pop(0))

            # Best-effort placement of chosen distractors.
            for item in chosen:
                obj_type = extract_object_type(item)
                final_name = add_object_unique(output, item, obj_type, prefer_name=item)
                if obj_type in ["basket", "wooden_tray"]:
                    _ensure_container_contain_region(output, final_name, obj_type)
                try:
                    region, region_name = _allocate_region_on_table(output, table_name, obj_type)
                except RuntimeError:
                    # If placement fails for this distractor, drop it.
                    # We do not attempt repeated re-seeding to keep generation robust.
                    # Remove from objects if it was just inserted.
                    _delete_instance_everywhere(output, final_name)
                    continue
                output.regions[region_name] = region
                output.init.append(f"(On {final_name} {table_name}_{region_name})")
    # Ensure a consistent distractor budget:
    # - prefer to keep existing fixed (fixture) distractors if available
    # - keep at most three movable distractors unrelated to the task
    # Task-relevant instances (manip/landmark/goal/keep_only) are never pruned.
    task_relevant: Set[str] = {
        x for x in [manip_obj, distractor_obj, landmark_obj, landmark_obj2] if x
    }
    task_relevant |= _instances_referenced_in_goal(output.goal)
    keep_only = task_spec.get("keep_only")
    if keep_only:
        task_relevant |= set(keep_only)

    # Fixed distractors: fixtures on the main table that are not task-relevant and
    # not the table itself.
    fixed_distractors = [
        inst
        for inst, ftype in output.fixtures.items()
        if inst not in task_relevant and inst != table_name
    ]
    # We do not forcibly add new fixtures; we only require that if any exist,
    # at least one survives (which is already true unless later logic prunes it).
    # Movable distractors: non-task objects, excluding same-type as the manipulated
    # object (same-type instances are treated as "same-class references", not true
    # distractors).
    movable_distractors = [
        inst
        for inst, otype in output.objects.items()
        if inst not in task_relevant
        and extract_object_type(inst) != extract_object_type(manip_obj)
    ]
    # Select up to 3 movable distractors.
    random.shuffle(movable_distractors)
    max_mov = 3
    if movable_distractors:
        chosen_mov = movable_distractors[:max_mov]
        to_drop = set(movable_distractors[max_mov:])
        # Remove unneeded movable objects completely from the scene.
        for inst in to_drop:
            _delete_instance_everywhere(output, inst)
    else:
        chosen_mov = []

    output.obj_of_interest = []
    if manip_obj:
        output.obj_of_interest.append(manip_obj)
    if landmark_obj:
        output.obj_of_interest.append(landmark_obj)
    if landmark_obj2:
        output.obj_of_interest.append(landmark_obj2)

    # Final safety pass 1: ensure every non-fixture object has a table placement.
    table_name = get_table_name(output.fixtures)
    _ensure_all_objects_placed(output, table_name)

    # Final safety pass 2: ensure at least 2 distractors exist in sparse scenes.
    task_relevant: Set[str] = set(output.obj_of_interest)
    task_relevant |= _instances_referenced_in_goal(output.goal)
    keep_only = task_spec.get("keep_only")
    if keep_only:
        task_relevant |= set(keep_only)
    _ensure_minimum_distractors(
        output,
        table_name=table_name,
        task_relevant=task_relevant,
        min_distractors=2,
        max_total=4,
    )

    return output


def main():
    parser = argparse.ArgumentParser(description="Generate ER-SPATIAL BDDL files")
    parser.add_argument("--yaml-file", type=str, default="er_extension/task_specs/er_spatial_tasks.yaml")
    parser.add_argument("--bddl-base", type=str, default="libero/libero/bddl_files")
    parser.add_argument("--output-dir", type=str, default="libero/libero/bddl_files/er_spatial")
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
            output = generate_er_spatial_bddl(task_spec, args.bddl_base)
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
