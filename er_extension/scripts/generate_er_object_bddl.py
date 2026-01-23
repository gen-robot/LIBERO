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


def get_occupied_boxes(existing_regions: Dict[str, Region]) -> List[Tuple[float, float, float, float, str]]:
    """Get list of occupied bounding boxes using actual object sizes.
    
    Considers both *_init_region patterns and fixture regions (cabinet_region, stove_region).
    """
    fixture_regions = {'cabinet_region', 'stove_region', 'wine_rack_region', 'desk_caddy_region'}
    fixture_types = {'cabinet_region': 'wooden_cabinet', 'stove_region': 'flat_stove',
                     'wine_rack_region': 'wine_rack', 'desk_caddy_region': 'desk_caddy'}
    
    occupied = []
    for name, region in existing_regions.items():
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
        occupied.append((cx - obj_w/2, cy - obj_d/2, cx + obj_w/2, cy + obj_d/2, name))
    return occupied


def boxes_overlap(box1, box2, margin: float = 0.03) -> bool:
    """Check if two bounding boxes overlap."""
    x1_min, y1_min, x1_max, y1_max = box1[:4]
    x2_min, y2_min, x2_max, y2_max = box2[:4]
    x1_min -= margin
    y1_min -= margin
    x1_max += margin
    y1_max += margin
    return not (x1_max < x2_min or x2_max < x1_min or y1_max < y2_min or y2_max < y1_min)


def check_collision(new_box, occupied, margin: float = 0.04) -> bool:
    """Check if new_box collides with any occupied boxes."""
    for obox in occupied:
        if boxes_overlap(new_box, obox[:4], margin):
            return True
    return False


def allocate_object_region(
    table_name: str,
    obj_type: str,
    existing_regions: Dict[str, Region],
    is_target: bool = False,
) -> Tuple[Region, str]:
    """Allocate a region for a new object."""
    # Use expanded size (1.5x) for collision detection
    collision_w, collision_d = get_object_size(obj_type, for_collision=True)
    half_cw, half_cd = collision_w / 2, collision_d / 2
    # Use actual size for region bounds
    actual_w, actual_d = get_object_size(obj_type, for_collision=False)
    half_w, half_d = actual_w / 2, actual_d / 2
    occupied = get_occupied_boxes(existing_regions)
    
    # Use predefined positions from er_constants for consistent, spread-out placement
    if is_target:
        candidate_centers = list(TARGET_PLACEMENT_POSITIONS)
    else:
        candidate_centers = list(OBJECT_PLACEMENT_POSITIONS)

    selected_center = None
    for cx, cy in candidate_centers:
        new_box = (cx - half_cw, cy - half_cd, cx + half_cw, cy + half_cd)
        if not check_collision(new_box, occupied, margin=COLLISION_MARGIN):
            selected_center = (cx, cy)
            break

    if selected_center is None:
        for x_offset in [0.0, -0.12, 0.12, -0.22, 0.22]:
            for y_offset in [-0.15, -0.05, 0.05, 0.15]:
                cx, cy = x_offset, y_offset
                new_box = (cx - half_cw, cy - half_cd, cx + half_cw, cy + half_cd)
                if not check_collision(new_box, occupied, margin=COLLISION_MARGIN):
                    selected_center = (cx, cy)
                    break
            if selected_center:
                break

    if selected_center is None:
        idx = len(existing_regions)
        selected_center = (-0.20 + (idx % 5) * 0.10, -0.15 + (idx // 5) * 0.12)

    # Region bounds use object size for proper collision detection in LIBERO
    # Add small tolerance for spawning variation
    coords = (
        selected_center[0] - half_w - PLACEMENT_TOLERANCE,
        selected_center[1] - half_d - PLACEMENT_TOLERANCE,
        selected_center[0] + half_w + PLACEMENT_TOLERANCE,
        selected_center[1] + half_d + PLACEMENT_TOLERANCE,
    )

    region_name = f"{obj_type}_init_region"
    counter = 1
    while region_name in existing_regions:
        region_name = f"{obj_type}_init_region_{counter}"
        counter += 1

    region = Region(name=region_name, target=table_name, ranges=[coords], yaw_rotation=(0.0, 0.0))
    return region, region_name


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

    output.fixtures = dict(scene_bddl.fixtures)
    output.goal = extract_goal_from_source(manip_bddl)

    fixture_names = set(scene_bddl.fixtures.keys()) - {table_name}
    for region_name, region in scene_bddl.regions.items():
        if region.target == table_name and region.ranges:
            for fix_name in fixture_names:
                if fix_name.replace('_1', '') in region_name:
                    output.regions[region_name] = region
                    break
        if region.target in fixture_names:
            output.regions[region_name] = region

    for init_stmt in scene_bddl.init:
        for fix_instance in fixture_names:
            if fix_instance in init_stmt and "(On" in init_stmt:
                if init_stmt not in output.init:
                    output.init.append(init_stmt)
                break

    take_list_a = source_a.get('take', [])
    manip_objects = extract_objects_from_source(manip_bddl, take_list_a)
    target_types = ['basket', 'wooden_tray', 'plate']
    target_objs = {k: v for k, v in manip_objects.items() if v in target_types}
    other_objs = {k: v for k, v in manip_objects.items() if v not in target_types}

    for instance, obj_type in list(target_objs.items()) + list(other_objs.items()):
        output.objects[instance] = obj_type
        is_target = obj_type in target_types
        region, region_name = allocate_object_region(table_name, obj_type, output.regions, is_target=is_target)
        output.regions[region_name] = region

        if obj_type in ['basket', 'wooden_tray']:
            contain_region = Region(name="contain_region", target=instance)
            output.regions["contain_region"] = contain_region

        output.init.append(f"(On {instance} {table_name}_{region_name})")

    output.obj_of_interest = list(other_objs.keys())[:2]
    if target_objs:
        output.obj_of_interest.append(list(target_objs.keys())[0])

    if source_c:
        distractor_items = source_c.get('take', [])
        for item in distractor_items:
            if isinstance(item, str) and item.endswith('_1'):
                obj_type = item.rsplit('_', 1)[0]
                if item not in output.objects:
                    output.objects[item] = obj_type
                region, region_name = allocate_object_region(table_name, obj_type, output.regions, is_target=False)
                output.regions[region_name] = region
                output.init.append(f"(On {item} {table_name}_{region_name})")

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
