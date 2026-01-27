#!/usr/bin/env python3
"""
Generate ER-SEQUENTIAL BDDL files from task specifications.
Updated to work with v3.0 YAML format (source_a, source_b, source_c).
"""

import os
import re
import yaml
import argparse
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional

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
    allocate_region,
    enforce_non_overlapping_table_placements,
    ensure_instance_one,
    infer_manip_and_target_from_goal,
    occupied_table_region_boxes_from_init,
    remove_instance_table_placement,
)


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
        lines.append(f"    {self.goal}")
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


def _allocate_region_on_table(output: BDDLFile, table_name: str, obj_type: str, *, is_manip: bool) -> Tuple[Region, str]:
    occupied_boxes = occupied_table_region_boxes_from_init(output.init, output.regions, table_name)
    return allocate_region(
        table_name,
        obj_type,
        output.regions,
        region_cls=Region,
        min_gap=MIN_REGION_GAP,
        max_extent=MAX_MANIP_REGION_EXTENT if is_manip else None,
        require_within_bound=REACH_BOUND if is_manip else None,
        min_gap_to_fixtures=MIN_MANIP_FIXTURE_GAP if is_manip else None,
        occupied_region_boxes=occupied_boxes,
    )


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


def has_real_table(bddl: BDDLFile) -> bool:
    """Check if BDDL has a real table (not floor)."""
    table = get_table_name(bddl.fixtures)
    return table != 'floor'


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
    fixtures_to_remove: set[str] = set()

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

        # If we can't even locate a placement statement, it's safer to drop the fixture.
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

    # Remove regions that target removed fixtures (fixture-internal regions).
    output.regions = {k: v for k, v in output.regions.items() if v.target not in fixtures_to_remove}

    # Remove init statements that place removed fixtures, or place objects onto removed fixtures' regions.
    filtered_init: list[str] = []
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


def generate_er_sequential_bddl(task_spec: dict, bddl_base: str) -> BDDLFile:
    """Generate a single ER-SEQUENTIAL BDDL file using v3.0 format.
    
    Automatically detects which source has the real scene (not floor)
    and uses that as the base.
    """
    source_a = task_spec['source_a']
    source_b = task_spec['source_b']
    source_c = task_spec.get('source_c')
    
    # Parse both sources to find which has the real scene
    bddl_a = parse_bddl_file(os.path.join(bddl_base, source_a['file']))
    bddl_b = parse_bddl_file(os.path.join(bddl_base, source_b['file']))
    
    # Use the source with the real table as the scene base
    if has_real_table(bddl_a):
        scene_bddl = bddl_a
        object_source = source_b
    else:
        scene_bddl = bddl_b
        object_source = source_a
    
    table_name = get_table_name(scene_bddl.fixtures)
    inferred_manip, _ = infer_manip_and_target_from_goal(task_spec.get("goal", ""))
    
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
    base_initialized = {stmt.split()[1] for stmt in scene_bddl.init if stmt.strip().startswith("(On ")}
    
    for inst, otype in scene_bddl.objects.items():
        output.objects[inst] = otype

    # Robustness: drop fixtures whose placement regions are missing/invalid to avoid
    # fallback fixture poses that can cause immediate interpenetration.
    sanitize_unplaceable_fixtures(output, table_name=table_name)
    
    # Add objects from the object source (whichever has floor)
    take_items = object_source.get('take', [])
    manip_objects = []
    
    for item in take_items:
        if item.endswith('_1') or item.endswith('_2'):
            obj_type = extract_object_type(item)
            final_name = add_object_unique(output, item, obj_type, prefer_name=item)
            if final_name not in manip_objects:
                manip_objects.append(final_name)
            if obj_type in ['basket', 'wooden_tray']:
                contain_region_name = alloc_unique_region_name(set(output.regions), "contain_region")
                output.regions[contain_region_name] = Region(name=contain_region_name, target=final_name)
    
    initialized = {stmt.split()[1] for stmt in output.init if stmt.startswith('(On')}
    
    for item in manip_objects:
        if item not in initialized:
            obj_type = extract_object_type(item)
            region, region_name = _allocate_region_on_table(
                output,
                table_name,
                obj_type,
                is_manip=(inferred_manip is not None and item == inferred_manip),
            )
            output.regions[region_name] = region
            output.init.append(f"(On {item} {table_name}_{region_name})")
            initialized.add(item)
    
    if source_c:
        initialized = {stmt.split()[1] for stmt in output.init if stmt.startswith('(On')}
        distractor_items = source_c.get('take', [])
        for item in distractor_items:
            if item.endswith('_1') or item.endswith('_2'):
                obj_type = extract_object_type(item)
                final_name = add_object_unique(output, item, obj_type, prefer_name=item)
                if final_name not in initialized:
                    region, region_name = _allocate_region_on_table(
                        output,
                        table_name,
                        obj_type,
                        is_manip=(inferred_manip is not None and final_name == inferred_manip),
                    )
                    output.regions[region_name] = region
                    output.init.append(f"(On {final_name} {table_name}_{region_name})")
                    initialized.add(final_name)
    
    # Fix goal by replacing invalid fixture/region references
    goal = task_spec['goal']
    
    fixture_names = set(output.fixtures.keys())
    region_names = set(output.regions.keys())
    object_names = set(output.objects.keys())
    
    import re
    
    # Auto-fix wooden_cabinet <-> white_cabinet mismatches
    if 'wooden_cabinet_1' in goal and 'wooden_cabinet_1' not in fixture_names:
        if 'white_cabinet_1' in fixture_names:
            goal = goal.replace('wooden_cabinet_1', 'white_cabinet_1')
    if 'white_cabinet_1' in goal and 'white_cabinet_1' not in fixture_names:
        if 'wooden_cabinet_1' in fixture_names:
            goal = goal.replace('white_cabinet_1', 'wooden_cabinet_1')
    
    # Fix invalid region references
    goal = goal.replace('desk_caddy_1_right_side', 'desk_caddy_1_front_contain_region')
    goal = goal.replace('desk_caddy_1_front_region', 'desk_caddy_1_front_contain_region')

    # Fix In -> On for non-containers (AkitaBlackBowl doesn't support In)
    goal = re.sub(r'\(In (\w+) (akita_black_bowl_\d+)\)', r'(On \1 \2)', goal)

    # Basket containment should use the basket's contain-region site object (e.g. basket_1_contain_region)
    # rather than the basket body itself, because Basket (a scanned MujocoXMLObject) doesn't implement
    # an `in_box()` API used by ObjectState.check_contain().
    goal = re.sub(r"\(In (\w+) (basket_\d+)\)", r"(In \1 \2_contain_region)", goal)
    
    # Fix bare table references - table names need region suffix
    for tbl in ['study_table', 'living_room_table', 'kitchen_table', 'main_table']:
        pattern = rf'\(On (\w+) {tbl}\)'
        if re.search(pattern, goal):
            center_region_name = "center_region"
            if center_region_name not in output.regions:
                target_table = tbl if tbl in fixture_names else table_name
                center_region = Region(name=center_region_name, target=target_table, ranges=[(0.0, 0.0, 0.02, 0.02)])
                output.regions[center_region_name] = center_region
            target_table = tbl if tbl in fixture_names else table_name
            goal = re.sub(pattern, rf'(On \1 {target_table}_center_region)', goal)
    
    # Fix table name mismatches in goal (when table doesn't exist)
    for wrong_table in ['study_table', 'living_room_table', 'main_table', 'floor']:
        if wrong_table in goal and wrong_table not in fixture_names:
            goal = goal.replace(wrong_table, table_name)
    
    # Ensure basket contain_region exists if referenced
    if re.search(r"\bbasket_\d+_contain_region\b", goal) and "contain_region" not in output.regions:
        # In our ER suites we only use a single basket instance; `contain_region` must match the
        # site name baked into the basket asset XML.
        basket_instances = sorted([n for n in object_names if re.fullmatch(r"basket_\d+", n)])
        if basket_instances:
            output.regions["contain_region"] = Region(name="contain_region", target=basket_instances[0])
    
    output.goal = goal

    # Ensure any goal-referenced movable instances exist in the scene.
    # Some sources (e.g. object suite providers) don't include target props
    # like `plate_1`, but LIBERO's predicate evaluator expects them to exist.
    goal_instances: set[str] = set()
    for atom in re.findall(r"\(([^()]+)\)", output.goal or ""):
        toks = atom.strip().split()
        if not toks:
            continue
        pred = toks[0]
        if pred == "On" and len(toks) >= 3:
            goal_instances.update([toks[1], toks[2]])
        elif pred == "In" and len(toks) >= 3:
            goal_instances.update([toks[1], toks[2]])
        elif pred in {"Open", "Close", "Turnon"} and len(toks) >= 2:
            goal_instances.add(toks[1])

    for inst in sorted(goal_instances):
        if inst in output.objects or inst in output.fixtures:
            continue
        if inst == table_name:
            continue
        # Only auto-add movable-looking instances like `plate_1`.
        if not re.match(r".+_\d+$", inst):
            continue
        obj_type = extract_object_type(inst)
        add_object_unique(output, inst, obj_type, prefer_name=inst)
        new_region, region_name = allocate_region(
            table_name,
            obj_type,
            output.regions,
            region_cls=Region,
            min_gap=MIN_REGION_GAP,
            collision_margin=COLLISION_MARGIN,
            occupied_region_boxes=occupied_table_region_boxes_from_init(output.init, output.regions, table_name),
        )
        output.regions[region_name] = new_region
        output.init.append(f"(On {inst} {table_name}_{region_name})")

    # Constraint: if multiple same-type objects exist, ensure manipulated object is *_1.
    manip_obj, _ = infer_manip_and_target_from_goal(output.goal)
    if manip_obj is not None and manip_obj in output.objects:
        ensure_instance_one(output, manip_obj)
        manip_obj, _ = infer_manip_and_target_from_goal(output.goal)

    output.obj_of_interest = manip_objects[:3] if manip_objects else []

    # Final pass: ensure table placements have non-overlapping region ranges.
    fixed_instances: set[str] = {k for k in output.fixtures.keys() if k != table_name}
    # NOTE: Do not freeze all base-scene `(On ...)` objects. Some upstream BDDL
    # files define overlapping *_init_region ranges; we rely on the constraint
    # pass to re-sample non-critical table placements to be collision-free.
    # Keep large containers fixed; re-sampling them can fail on crowded tables.
    fixed_instances |= {inst for inst, typ in output.objects.items() if typ in {"basket", "wooden_tray"}}
    # Keep goal-referenced props fixed so they won't be dropped as "distractors".
    fixed_instances |= {inst for inst in goal_instances if inst in output.objects}
    if manip_obj is not None:
        fixed_instances.add(manip_obj)
    # If we still fail due to overlapping upstream init regions, drop one
    # overlapping distractor placement and retry once. This keeps generation
    # robust while preserving fixed instances (fixtures / containers / manip).
    # First try: re-sample non-fixed placements.
    # Fallback: if overlaps persist due to an extremely crowded scene template,
    # drop a few non-fixed table distractors.
    for _attempt in range(6):
        try:
            enforce_non_overlapping_table_placements(
                output,
                table_name,
                fixed_instances=fixed_instances,
                min_gap=MIN_REGION_GAP,
            )
            break
        except RuntimeError as e:
            msg = str(e)
            m = re.search(r"Table placement regions overlap .*?: ([^ ]+) vs ([^ ]+)$", msg)
            if not m:
                raise
            key_i, key_j = m.group(1), m.group(2)
            inst_i = key_i.split(":", 1)[0]
            inst_j = key_j.split(":", 1)[0]

            victim = None
            if inst_j not in fixed_instances:
                victim = inst_j
            elif inst_i not in fixed_instances:
                victim = inst_i
            if victim is None:
                raise

            remove_instance_table_placement(output, table_name, victim)
            output.objects.pop(victim, None)
    else:
        # Should be unreachable because the loop either breaks or raises.
        raise RuntimeError("Failed to enforce non-overlapping placements after retries")
    
    return output


def main():
    parser = argparse.ArgumentParser(description="Generate ER-SEQUENTIAL BDDL files")
    parser.add_argument("--yaml-file", type=str, default="er_extension/task_specs/er_sequential_tasks.yaml")
    parser.add_argument("--bddl-base", type=str, default="libero/libero/bddl_files")
    parser.add_argument("--output-dir", type=str, default="libero/libero/bddl_files/er_sequential")
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
            output = generate_er_sequential_bddl(task_spec, args.bddl_base)
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
