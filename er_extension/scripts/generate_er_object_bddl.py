#!/usr/bin/env python3
"""
Generate ER-OBJECT BDDL files from YAML task specifications.

ER-OBJECT Principle:
- Keep manipulation (Language, Goal, manipulation objects) from Source A
- Replace scene context (Fixtures, Regions layout) from Source B
- Optionally add distractor objects from Source C

Updated to work with new explicit YAML format (v3.0).
"""

from __future__ import annotations
import argparse
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import yaml

from er_constants import (
    OBJECT_SIZES, COLLISION_MARGIN, PLACEMENT_TOLERANCE, get_object_size,
    OBJECT_PLACEMENT_POSITIONS, TARGET_PLACEMENT_POSITIONS, FIXTURE_PLACEMENT_POSITIONS
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
)


@dataclass
class Region:
    name: str
    target: str
    ranges: Optional[List[Tuple[float, float, float, float]]] = None
    yaw_rotation: Optional[Tuple[float, float]] = None

    def render(self) -> str:
        lines = [f"      ({self.name}"]
        lines.append(f"          (:target {self.target})")
        if self.ranges:
            lines.append("          (:ranges (")
            for r in self.ranges:
                lines.append(f"              ({r[0]} {r[1]} {r[2]} {r[3]})")
            lines.append("            )")
            lines.append("          )")
        if self.yaw_rotation:
            lines.append("          (:yaw_rotation (")
            lines.append(f"              ({self.yaw_rotation[0]} {self.yaw_rotation[1]})")
            lines.append("            )")
            lines.append("          )")
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

    def render(self) -> str:
        lines = [f"(define (problem {self.problem_name})"]
        lines.append(f"  (:domain {self.domain})")
        lines.append(f"  (:language {self.language})")

        lines.append("    (:regions")
        for region in self.regions.values():
            lines.append(region.render())
        lines.append("    )")
        lines.append("")

        lines.append("  (:fixtures")
        for instance, fix_type in self.fixtures.items():
            lines.append(f"    {instance} - {fix_type}")
        lines.append("  )")
        lines.append("")

        lines.append("  (:objects")
        for instance, obj_type in self.objects.items():
            lines.append(f"    {instance} - {obj_type}")
        lines.append("  )")
        lines.append("")

        lines.append("  (:obj_of_interest")
        for obj in self.obj_of_interest:
            lines.append(f"    {obj}")
        lines.append("  )")
        lines.append("")

        lines.append("  (:init")
        for init_stmt in self.init:
            lines.append(f"    {init_stmt}")
        lines.append("  )")
        lines.append("")

        lines.append("  (:goal")
        lines.append(f"    (And {self.goal})")
        lines.append("  )")
        lines.append("")
        lines.append(")")

        return "\n".join(lines)


def parse_bddl_file(filepath: str) -> BDDLFile:
    """Parse a BDDL file into structured format."""
    with open(filepath, 'r') as f:
        content = f.read()

    prob_match = re.search(r'\(define\s+\(problem\s+(\w+)\)', content)
    problem_name = prob_match.group(1) if prob_match else "LIBERO_ER_Manipulation"

    domain_match = re.search(r'\(:domain\s+(\w+)\)', content)
    domain = domain_match.group(1) if domain_match else "robosuite"

    lang_match = re.search(r'\(:language\s+(.+?)\)\s*\n', content)
    language = lang_match.group(1).strip() if lang_match else ""

    bddl = BDDLFile(problem_name=problem_name, domain=domain, language=language)

    fix_match = re.search(r'\(:fixtures\s*\n(.*?)\s*\)', content, re.DOTALL)
    if fix_match:
        for line in fix_match.group(1).strip().split('\n'):
            line = line.strip()
            if ' - ' in line:
                parts = line.split(' - ', 1)
                instances = parts[0].strip().split()
                fix_type = parts[1].strip()
                for inst in instances:
                    bddl.fixtures[inst] = fix_type

    obj_match = re.search(r'\(:objects\s*\n(.*?)\s*\)', content, re.DOTALL)
    if obj_match:
        for line in obj_match.group(1).strip().split('\n'):
            line = line.strip()
            if ' - ' in line:
                parts = line.split(' - ', 1)
                instances = parts[0].strip().split()
                obj_type = parts[1].strip()
                for inst in instances:
                    bddl.objects[inst] = obj_type

    regions_section = re.search(r'\(:regions\s*(.*?)\s*\)\s*\n\s*\(:fixtures', content, re.DOTALL)
    if regions_section:
        region_content = regions_section.group(1)
    else:
        region_content = content

    region_blocks = re.findall(
        r'\((\w+)\s*\n\s*\(:target\s+(\w+)\)(.*?)(?=\s*\(\w+\s*\n\s*\(:target|\s*\)\s*\n\s*\(:fixtures|\s*\)\s*$)',
        region_content, re.DOTALL
    )
    for region_name, target, rest in region_blocks:
        ranges = None
        yaw = None
        ranges_match = re.search(r'\(:ranges\s*\(\s*\(([-\d.\s]+)\)', rest)
        if ranges_match:
            coords = [float(x) for x in ranges_match.group(1).split()]
            if len(coords) == 4:
                ranges = [(coords[0], coords[1], coords[2], coords[3])]
        yaw_match = re.search(r'\(:yaw_rotation\s*\(\s*\(([-\d.\s]+)\)', rest)
        if yaw_match:
            yaw_coords = [float(x) for x in yaw_match.group(1).split()]
            if len(yaw_coords) == 2:
                yaw = (yaw_coords[0], yaw_coords[1])
        bddl.regions[region_name] = Region(
            name=region_name, target=target, ranges=ranges, yaw_rotation=yaw
        )

    oi_match = re.search(r'\(:obj_of_interest\s*\n(.*?)\s*\)', content, re.DOTALL)
    if oi_match:
        for line in oi_match.group(1).strip().split('\n'):
            line = line.strip()
            if line:
                bddl.obj_of_interest.append(line)

    init_match = re.search(r'\(:init\s*\n(.*?)\s*\)\s*\n\s*\(:goal', content, re.DOTALL)
    if init_match:
        for stmt in re.findall(r'\([^()]+\)', init_match.group(1)):
            bddl.init.append(stmt)

    goal_match = re.search(r'\(:goal\s+\(And\s+(\([^)]+\))\s*\)\s*\)', content, re.DOTALL)
    if goal_match:
        bddl.goal = goal_match.group(1).strip()
    else:
        goal_match = re.search(r'\(:goal\s+(\([^)]+\))\s*\)', content, re.DOTALL)
        if goal_match:
            bddl.goal = goal_match.group(1).strip()

    return bddl


def get_table_name(fixtures: Dict[str, str]) -> str:
    """Get the main table/floor name from fixtures."""
    priority = ['main_table', 'kitchen_table', 'living_room_table', 'study_table', 'floor']
    for table in priority:
        if table in fixtures:
            return table
    for instance, fix_type in fixtures.items():
        if 'table' in fix_type or fix_type == 'floor':
            return instance
    return list(fixtures.keys())[0] if fixtures else "main_table"


def _init_occupied_table_boxes(output: BDDLFile, table_name: str) -> List[Tuple[float, float, float, float]]:
    return occupied_table_region_boxes_from_init(output.init, output.regions, table_name)




def extract_goal_from_source(source_bddl: BDDLFile) -> str:
    """Extract goal predicate from source BDDL."""
    return source_bddl.goal


def extract_objects_from_source(source_bddl: BDDLFile, take_list: List[str] = None) -> Dict[str, str]:
    """Extract manipulation objects from source, filtered by take list if provided."""
    if take_list is None:
        return dict(source_bddl.objects)
    
    # Filter to only objects in the take list (ignore non-object items like 'goal', 'scene_layout')
    result = {}
    for inst, otype in source_bddl.objects.items():
        if inst in take_list:
            result[inst] = otype
    return result


def generate_er_object_bddl(task_spec: dict, bddl_base: str) -> BDDLFile:
    """Generate a single ER-OBJECT BDDL file from task specification (v3.0 format)."""
    source_a = task_spec['source_a']
    source_b = task_spec['source_b']
    source_c = task_spec.get('source_c')

    manip_file = os.path.join(bddl_base, source_a['file'])
    scene_file = os.path.join(bddl_base, source_b['file'])

    manip_bddl = parse_bddl_file(manip_file)
    scene_bddl = parse_bddl_file(scene_file)

    table_name = get_table_name(scene_bddl.fixtures)

    problem_name_map = {
        'main_table': 'LIBERO_Tabletop_Manipulation',
        'kitchen_table': 'LIBERO_Kitchen_Tabletop_Manipulation',
        'living_room_table': 'LIBERO_Living_Room_Tabletop_Manipulation',
        'study_table': 'LIBERO_Study_Tabletop_Manipulation',
        'floor': 'LIBERO_Floor_Manipulation',
    }
    problem_name = problem_name_map.get(table_name, 'LIBERO_Tabletop_Manipulation')

    output = BDDLFile(
        problem_name=problem_name,
        domain="robosuite",
        language=task_spec['instruction'],
    )

    output.goal = extract_goal_from_source(manip_bddl)
    manip_obj, _ = infer_manip_and_target_from_goal(output.goal)

    # Keep the table fixture, and only keep other fixtures that have a valid
    # table placement region (otherwise MuJoCo may place them at a fallback pose
    # and cause fixture-fixture interpenetration / physics explosions).
    output.fixtures = {table_name: scene_bddl.fixtures[table_name]}

    fixture_instances = [k for k in scene_bddl.fixtures.keys() if k != table_name]
    kept_fixtures: set[str] = set()

    # Copy fixture placement init statements from the scene template, but only
    # when the referenced table placement region is present (with ranges).
    #
    # Many scene templates include object placement statements like:
    #   (On akita_black_bowl_1 flat_stove_1_cook_region)
    # which reference objects we intentionally do NOT carry over for ER-OBJECT.
    #
    # To avoid dangling references, we only keep fixture-placement (On ...) and
    # validate the region before keeping the fixture.
    for fix_instance in fixture_instances:
        placement_stmt = None
        placement_region_key = None
        for init_stmt in scene_bddl.init:
            stmt = init_stmt.strip()
            if not stmt.startswith(f"(On {fix_instance} "):
                continue
            # Expected: (On <fixture> <table>_<region_name>)
            parts = stmt.replace("(", "").replace(")", "").split()
            if len(parts) >= 3:
                placement_stmt = init_stmt
                placement_region_key = parts[2]
            break

        if placement_stmt is None or placement_region_key is None:
            continue

        table_prefix = f"{table_name}_"
        if not placement_region_key.startswith(table_prefix):
            # Unrecognized format; skip to avoid keeping a fixture we can't place.
            continue

        placement_region_name = placement_region_key[len(table_prefix):]
        placement_region = scene_bddl.regions.get(placement_region_name)
        if placement_region is None or placement_region.target != table_name or not placement_region.ranges:
            print(
                f"  [warn] skipping fixture '{fix_instance}': missing placement region "
                f"'{placement_region_name}' on '{table_name}'"
            )
            continue

        output.fixtures[fix_instance] = scene_bddl.fixtures[fix_instance]
        kept_fixtures.add(fix_instance)

        # Ensure the table placement region exists in the output.
        output.regions[placement_region_name] = placement_region
        output.init.append(placement_stmt)

    # Copy fixture-internal regions for fixtures we kept (e.g. cook_region, shelf tiers).
    for region_name, region in scene_bddl.regions.items():
        if region.target in kept_fixtures:
            output.regions[region_name] = region

    take_list_a = source_a.get('take', [])
    manip_objects = extract_objects_from_source(manip_bddl, take_list_a)
    target_types = ['basket', 'wooden_tray', 'plate']
    target_objs = {k: v for k, v in manip_objects.items() if v in target_types}
    other_objs = {k: v for k, v in manip_objects.items() if v not in target_types}

    # Add objects first (handle instance-name collisions), then place with constrained allocator.
    name_map: Dict[str, str] = {}
    for instance, obj_type in list(target_objs.items()) + list(other_objs.items()):
        final_name = add_object_unique(output, instance, obj_type, prefer_name=instance)
        name_map[instance] = final_name
        if obj_type in ["basket", "wooden_tray"]:
            contain_region_name = alloc_unique_region_name(set(output.regions), "contain_region")
            output.regions[contain_region_name] = Region(name=contain_region_name, target=final_name)

    output.obj_of_interest = [name_map[k] for k in list(other_objs.keys())[:2] if k in name_map]
    if target_objs:
        first_target = list(target_objs.keys())[0]
        if first_target in name_map:
            output.obj_of_interest.append(name_map[first_target])

    if source_c:
        distractor_items = source_c.get('take', [])
        for item in distractor_items:
            if isinstance(item, str) and item.endswith('_1'):
                obj_type = item.rsplit('_', 1)[0]
                final_name = add_object_unique(output, item, obj_type, prefer_name=item)
                if obj_type in ["basket", "wooden_tray"]:
                    contain_region_name = alloc_unique_region_name(set(output.regions), "contain_region")
                    output.regions[contain_region_name] = Region(name=contain_region_name, target=final_name)

    # Constraint: if multiple same-type objects exist, ensure manipulated object is *_1.
    if manip_obj is not None and manip_obj in output.objects:
        ensure_instance_one(output, manip_obj)
        manip_obj, _ = infer_manip_and_target_from_goal(output.goal)

    ordered_instances: List[Tuple[str, str, bool]] = [
        (inst, otype, otype in target_types) for inst, otype in output.objects.items()
    ]

    # Place all movable objects onto table with shared constraints.
    initialized = {stmt.split()[1] for stmt in output.init if stmt.strip().startswith("(On ")}
    for instance, obj_type, is_target in ordered_instances:
        if instance in initialized:
            continue
        occ = _init_occupied_table_boxes(output, table_name)
        is_manip = manip_obj is not None and instance == manip_obj
        region, region_name = allocate_region(
            table_name,
            obj_type,
            output.regions,
            region_cls=Region,
            candidates=list(TARGET_PLACEMENT_POSITIONS) if is_target else list(OBJECT_PLACEMENT_POSITIONS),
            min_gap=MIN_REGION_GAP,
            max_extent=MAX_MANIP_REGION_EXTENT if is_manip else None,
            require_within_bound=REACH_BOUND if is_manip else None,
            min_gap_to_fixtures=MIN_MANIP_FIXTURE_GAP if is_manip else None,
            occupied_region_boxes=occ,
        )
        output.regions[region_name] = region
        output.init.append(f"(On {instance} {table_name}_{region_name})")

    # Final pass: ensure table placements have non-overlapping region ranges.
    fixed_instances: set[str] = {k for k in output.fixtures.keys() if k != table_name}
    if manip_obj is not None:
        fixed_instances.add(manip_obj)
    enforce_non_overlapping_table_placements(
        output,
        table_name,
        fixed_instances=fixed_instances,
        min_gap=MIN_REGION_GAP,
    )

    return output


def load_yaml_config(yaml_path: str) -> dict:
    """Load YAML configuration file."""
    with open(yaml_path, 'r') as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(description="Generate ER-OBJECT BDDL files")
    parser.add_argument(
        "--yaml-file",
        type=str,
        default="er_extension/task_specs/er_object_tasks.yaml",
        help="Path to task specification YAML"
    )
    parser.add_argument(
        "--bddl-base",
        type=str,
        default="libero/libero/bddl_files",
        help="Base directory for source BDDL files"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="libero/libero/bddl_files/er_object",
        help="Output directory for generated BDDL files"
    )
    parser.add_argument("--task-id", type=str, help="Generate only specific task ID")
    args = parser.parse_args()

    config = load_yaml_config(args.yaml_file)
    os.makedirs(args.output_dir, exist_ok=True)

    tasks = config['tasks']
    if args.task_id:
        tasks = [t for t in tasks if args.task_id in t['id']]

    success_count = 0
    failed_tasks = []

    for task in tasks:
        task_id = task['id']
        print(f"Generating: {task_id}")
        try:
            bddl = generate_er_object_bddl(task, args.bddl_base)
            output_path = os.path.join(args.output_dir, f"{task_id}.bddl")
            with open(output_path, 'w') as f:
                f.write(bddl.render())
            print(f"  -> {output_path}")
            success_count += 1
        except Exception as e:
            print(f"  [ERROR] {e}")
            import traceback
            traceback.print_exc()
            failed_tasks.append((task_id, str(e)))

    print(f"\nGenerated {success_count}/{len(tasks)} BDDL files")
    if failed_tasks:
        print("Failed tasks:")
        for tid, err in failed_tasks:
            print(f"  - {tid}: {err}")


if __name__ == "__main__":
    main()
