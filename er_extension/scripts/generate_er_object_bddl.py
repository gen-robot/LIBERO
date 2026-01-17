#!/usr/bin/env python3
"""
Generate ER-OBJECT BDDL files from YAML task specifications.

ER-OBJECT Principle:
- Keep manipulation (Language, Goal, manipulation objects) from Source A
- Replace scene context (Fixtures, Regions layout) from Source B
- Optionally add background objects from Source C
"""

from __future__ import annotations
import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
import yaml

from er_constants import OBJECT_SIZES, COLLISION_MARGIN, get_object_size


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

    def get_center(self) -> Optional[Tuple[float, float]]:
        if self.ranges:
            r = self.ranges[0]
            return ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)
        return None


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

    # Parse fixtures
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

    # Parse objects
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

    # Parse regions
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

    # Parse obj_of_interest
    oi_match = re.search(r'\(:obj_of_interest\s*\n(.*?)\s*\)', content, re.DOTALL)
    if oi_match:
        for line in oi_match.group(1).strip().split('\n'):
            line = line.strip()
            if line:
                bddl.obj_of_interest.append(line)

    # Parse init
    init_match = re.search(r'\(:init\s*\n(.*?)\s*\)\s*\n\s*\(:goal', content, re.DOTALL)
    if init_match:
        for stmt in re.findall(r'\([^()]+\)', init_match.group(1)):
            bddl.init.append(stmt)

    # Parse goal
    goal_match = re.search(r'\(:goal\s*\n\s*\(And\s*(.*?)\)\s*\)', content, re.DOTALL)
    if goal_match:
        bddl.goal = goal_match.group(1).strip()
    else:
        goal_match = re.search(r'\(:goal\s*\n\s*(\([^)]+\))\s*\)', content, re.DOTALL)
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


def extract_obj_type_from_region_name(region_name: str) -> str:
    """Extract object type from region name like 'butter_init_region' -> 'butter'."""
    name = region_name.lower()
    # Remove common suffixes
    for suffix in ['_init_region', '_region', '_1', '_2', '_3']:
        name = name.replace(suffix, '')
    return name


def get_occupied_boxes(existing_regions: Dict[str, Region]) -> List[Tuple[float, float, float, float, str]]:
    """Get list of (x_min, y_min, x_max, y_max, name) for occupied regions."""
    occupied = []
    for name, region in existing_regions.items():
        if region.ranges:
            r = region.ranges[0]
            cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
            
            # Extract potential object type from region name
            extracted_type = extract_obj_type_from_region_name(name)
            
            # Find matching object size
            matched_size = None
            for obj_type, size in OBJECT_SIZES.items():
                # Direct match
                if obj_type == extracted_type:
                    matched_size = size
                    break
                # Partial match (e.g., 'white_cabinet' matches 'whitecabinet')
                if obj_type.replace('_', '') == extracted_type.replace('_', ''):
                    matched_size = size
                    break
                # Substring match
                if obj_type in extracted_type or extracted_type in obj_type:
                    matched_size = size
                    break
            
            if matched_size:
                w, d = matched_size
                half_w, half_d = w / 2, d / 2
                occupied.append((cx - half_w, cy - half_d, cx + half_w, cy + half_d, name))
            else:
                # For unmatched regions, use region bounds or default
                region_w = r[2] - r[0]
                region_d = r[3] - r[1]
                # If region is very small (anchor point), assume medium fixture
                if region_w < 0.05 and region_d < 0.05:
                    w, d = 0.15, 0.15
                    occupied.append((cx - w/2, cy - d/2, cx + w/2, cy + d/2, name))
                else:
                    # Use the region bounds with padding
                    padding = 0.03
                    occupied.append((r[0] - padding, r[1] - padding, r[2] + padding, r[3] + padding, name))
    return occupied


def boxes_overlap(box1: Tuple[float, float, float, float], box2: Tuple[float, float, float, float], margin: float = 0.03) -> bool:
    """Check if two bounding boxes overlap with a safety margin."""
    x1_min, y1_min, x1_max, y1_max = box1
    x2_min, y2_min, x2_max, y2_max = box2
    # Add margin
    x1_min -= margin
    y1_min -= margin
    x1_max += margin
    y1_max += margin
    # Check overlap
    return not (x1_max < x2_min or x2_max < x1_min or y1_max < y2_min or y2_max < y1_min)


def check_collision(new_box: Tuple[float, float, float, float], occupied: List[Tuple[float, float, float, float, str]], margin: float = 0.04) -> bool:
    """Check if new_box would collide with any occupied boxes."""
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
    """Allocate a region for a new object, ensuring no bounding box collisions."""
    obj_w, obj_d = get_object_size(obj_type)
    half_w, half_d = obj_w / 2, obj_d / 2
    occupied = get_occupied_boxes(existing_regions)
    
    # Use larger margin for better separation
    collision_margin = COLLISION_MARGIN

    # Define well-spaced placement zones
    if is_target:
        # Target containers go in back/middle area, away from fixtures
        candidate_centers = [
            (0.0, 0.18),      # Back center
            (-0.15, 0.15),    # Back left
            (0.15, 0.15),     # Back right
            (0.0, 0.10),      # Mid center
            (-0.20, 0.10),    # Far left mid
            (0.20, 0.10),     # Far right mid
        ]
    else:
        # Manipulation objects: well-spread across front/mid area
        # Positions are designed to be far apart from each other
        candidate_centers = [
            (0.0, -0.10),      # Front center (closest to robot)
            (-0.18, -0.05),    # Far left front
            (0.18, -0.05),     # Far right front
            (-0.10, 0.05),     # Left mid
            (0.10, 0.05),      # Right mid
            (0.0, 0.02),       # Center
            (-0.20, 0.08),     # Far left mid
            (0.20, 0.08),      # Far right mid
            (-0.12, -0.12),    # Front left
            (0.12, -0.12),     # Front right
            (0.0, -0.18),      # Very front
            (-0.15, 0.12),     # Back left area
            (0.15, 0.12),      # Back right area
        ]

    # Find first non-colliding position using bounding box checks
    selected_center = None
    for cx, cy in candidate_centers:
        new_box = (cx - half_w, cy - half_d, cx + half_w, cy + half_d)
        if not check_collision(new_box, occupied, margin=collision_margin):
            selected_center = (cx, cy)
            break

    # Fallback: systematic grid search with larger spacing
    if selected_center is None:
        for x_offset in [0.0, -0.12, 0.12, -0.22, 0.22]:
            for y_offset in [-0.15, -0.05, 0.05, 0.15]:
                cx, cy = x_offset, y_offset
                new_box = (cx - half_w, cy - half_d, cx + half_w, cy + half_d)
                if not check_collision(new_box, occupied, margin=collision_margin):
                    selected_center = (cx, cy)
                    break
            if selected_center:
                break

    # Last resort fallback with unique offset per object
    if selected_center is None:
        idx = len(existing_regions)
        if is_target:
            selected_center = (-0.10 + (idx % 3) * 0.10, 0.20)
        else:
            # Spread fallback positions more
            selected_center = (-0.20 + (idx % 5) * 0.10, -0.15 + (idx // 5) * 0.12)

    # Create region bounds from center using actual object size
    coords = (
        selected_center[0] - half_w,
        selected_center[1] - half_d,
        selected_center[0] + half_w,
        selected_center[1] + half_d,
    )

    region_name = f"{obj_type}_init_region"
    counter = 1
    while region_name in existing_regions:
        region_name = f"{obj_type}_init_region_{counter}"
        counter += 1

    region = Region(name=region_name, target=table_name, ranges=[coords], yaw_rotation=(0.0, 0.0))
    return region, region_name


def generate_er_object_bddl(
    task_spec: dict,
    yaml_config: dict,
    bddl_base: str
) -> BDDLFile:
    """Generate a single ER-OBJECT BDDL file from task specification."""
    sources = {s['id']: s for s in task_spec['sources']}
    source_a = sources['A']
    source_b = sources['B']
    source_c = sources.get('C')

    manip_key = source_a['ref']
    scene_key = source_b['ref']
    manip_config = yaml_config['manipulation_sources'][manip_key]
    scene_config = yaml_config['scene_templates'][scene_key]

    scene_file = os.path.join(bddl_base, scene_config['file'])
    scene_bddl = parse_bddl_file(scene_file)
    table_name = scene_config['table']

    # Determine problem name based on scene type
    problem_name_map = {
        'kitchen_table': 'LIBERO_Kitchen_Tabletop_Manipulation',
        'living_room_table': 'LIBERO_Living_Room_Tabletop_Manipulation',
        'study_table': 'LIBERO_Study_Tabletop_Manipulation',
        'main_table': 'LIBERO_Tabletop_Manipulation',
        'floor': 'LIBERO_Floor_Manipulation',
    }
    problem_name = problem_name_map.get(table_name, 'LIBERO_Tabletop_Manipulation')

    output = BDDLFile(
        problem_name=problem_name,
        domain="robosuite",
        language=manip_config['language'],
    )

    output.fixtures = dict(scene_bddl.fixtures)
    output.goal = manip_config['goal']
    output.obj_of_interest = list(manip_config['obj_of_interest'])

    # Only copy fixture placement regions (not object regions from scene template)
    fixture_names = set(scene_bddl.fixtures.keys()) - {table_name}
    for region_name, region in scene_bddl.regions.items():
        # Copy fixture placement regions on table
        if region.target == table_name and region.ranges:
            for fix_name in fixture_names:
                if fix_name.replace('_1', '') in region_name or region_name.replace('_init_region', '') in fix_name:
                    output.regions[region_name] = region
                    break

        # Copy fixture's own regions (drawer regions, etc.)
        if region.target in fixture_names:
            output.regions[region_name] = region

    # Copy fixture init statements
    for init_stmt in scene_bddl.init:
        for fix_instance in fixture_names:
            if fix_instance in init_stmt and "(On" in init_stmt:
                if init_stmt not in output.init:
                    output.init.append(init_stmt)
                break

    # Add manipulation objects - target first (basket), then manipulation object
    manip_objects = manip_config['manipulation_objects']

    # Sort: target containers first, then manipulation objects
    target_objects = [o for o in manip_objects if o['type'] in ['basket', 'wooden_tray', 'plate']]
    other_objects = [o for o in manip_objects if o['type'] not in ['basket', 'wooden_tray', 'plate']]

    for obj_info in target_objects + other_objects:
        instance = obj_info['instance']
        obj_type = obj_info['type']
        output.objects[instance] = obj_type

        is_target = obj_type in ['basket', 'wooden_tray', 'plate']
        region, region_name = allocate_object_region(table_name, obj_type, output.regions, is_target=is_target)
        output.regions[region_name] = region

        if obj_type in ['basket', 'wooden_tray']:
            contain_region = Region(name="contain_region", target=instance)
            output.regions["contain_region"] = contain_region

        output.init.append(f"(On {instance} {table_name}_{region_name})")

    # Add background objects from source C (3-source tasks)
    if source_c and source_c.get('role') == 'background_objects':
        bg_objects = source_c.get('objects', [])
        for obj_info in bg_objects:
            instance = obj_info['instance']
            obj_type = obj_info['type']
            if instance not in output.objects:
                output.objects[instance] = obj_type
                region, region_name = allocate_object_region(table_name, obj_type, output.regions, is_target=False)
                output.regions[region_name] = region
                output.init.append(f"(On {instance} {table_name}_{region_name})")

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
            bddl = generate_er_object_bddl(task, config, args.bddl_base)
            output_path = os.path.join(args.output_dir, f"{task_id}.bddl")
            with open(output_path, 'w') as f:
                f.write(bddl.render())
            print(f"  -> {output_path}")
            success_count += 1
        except Exception as e:
            print(f"  [ERROR] {e}")
            failed_tasks.append((task_id, str(e)))

    print(f"\nGenerated {success_count}/{len(tasks)} BDDL files")
    if failed_tasks:
        print("Failed tasks:")
        for tid, err in failed_tasks:
            print(f"  - {tid}: {err}")


if __name__ == "__main__":
    main()
