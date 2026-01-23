#!/usr/bin/env python3
"""
Generate ER-SPATIAL BDDL files from task specifications.
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

SPATIAL_OFFSETS = {
    'next_to': (-0.12, 0.0),   # Place to the left of landmark
    'left_of': (-0.14, 0.0),   # Place to the left
    'right_of': (0.14, 0.0),   # Place to the right
    'in_front_of': (0.0, 0.12), # Place in front (toward camera)
    'behind': (0.0, -0.12),    # Place behind (away from camera)
    'on': (0.0, 0.0),          # Place on top of (same position, for stacking)
    'between': (0.0, 0.0),     # For 'between' we need special handling with two landmarks
}


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


def allocate_region_at_offset(table_name: str, obj_type: str, landmark_center: Tuple[float, float],
                              offset: Tuple[float, float], regions: Dict[str, Region]) -> Tuple[Region, str]:
    """Allocate a region at a spatial offset from a landmark."""
    # Use expanded size (1.5x) for collision detection
    collision_w, collision_d = get_object_size(obj_type, for_collision=True)
    half_cw, half_cd = collision_w / 2, collision_d / 2
    # Use actual size for region bounds
    actual_w, actual_d = get_object_size(obj_type, for_collision=False)
    half_w, half_d = actual_w / 2, actual_d / 2
    
    cx = landmark_center[0] + offset[0]
    cy = landmark_center[1] + offset[1]
    
    occupied = get_occupied_boxes(regions)
    final_cx, final_cy = cx, cy
    
    for dx in [0, 0.05, -0.05, 0.10, -0.10]:
        for dy in [0, 0.05, -0.05, 0.10, -0.10]:
            test_box = (cx + dx - half_cw, cy + dy - half_cd, cx + dx + half_cw, cy + dy + half_cd)
            if not any(boxes_overlap(test_box, obox, COLLISION_MARGIN) for obox in occupied):
                final_cx, final_cy = cx + dx, cy + dy
                break
        else:
            continue
        break
    
    region_name = f"{obj_type}_init_region"
    counter = 1
    while region_name in regions:
        region_name = f"{obj_type}_init_region_{counter}"
        counter += 1
    
    # Region bounds use actual object size for proper physics spawning
    region_box = (final_cx - half_w - PLACEMENT_TOLERANCE, final_cy - half_d - PLACEMENT_TOLERANCE,
                  final_cx + half_w + PLACEMENT_TOLERANCE, final_cy + half_d + PLACEMENT_TOLERANCE)
    region = Region(name=region_name, target=table_name, ranges=[region_box])
    return region, region_name


def allocate_region(table_name: str, obj_type: str, regions: Dict[str, Region]) -> Tuple[Region, str]:
    """Allocate a non-overlapping region for an object."""
    # Use expanded size (1.5x) for collision detection
    collision_w, collision_d = get_object_size(obj_type, for_collision=True)
    half_cw, half_cd = collision_w / 2, collision_d / 2
    # Use actual size for region bounds
    actual_w, actual_d = get_object_size(obj_type, for_collision=False)
    half_w, half_d = actual_w / 2, actual_d / 2
    occupied = get_occupied_boxes(regions)
    
    # Use predefined positions from er_constants for consistent, spread-out placement
    candidates = list(OBJECT_PLACEMENT_POSITIONS)
    
    for cx, cy in candidates:
        collision_box = (cx - half_cw, cy - half_cd, cx + half_cw, cy + half_cd)
        if not any(boxes_overlap(collision_box, obox, COLLISION_MARGIN) for obox in occupied):
            region_name = f"{obj_type}_init_region"
            counter = 1
            while region_name in regions:
                region_name = f"{obj_type}_init_region_{counter}"
                counter += 1
            # Region bounds use actual object size for physics spawning
            region_box = (cx - half_w - PLACEMENT_TOLERANCE, cy - half_d - PLACEMENT_TOLERANCE,
                          cx + half_w + PLACEMENT_TOLERANCE, cy + half_d + PLACEMENT_TOLERANCE)
            return Region(name=region_name, target=table_name, ranges=[region_box]), region_name
    
    # Fallback position
    cx, cy = 0.1, 0.15
    region_box = (cx - half_w - PLACEMENT_TOLERANCE, cy - half_d - PLACEMENT_TOLERANCE,
                  cx + half_w + PLACEMENT_TOLERANCE, cy + half_d + PLACEMENT_TOLERANCE)
    return Region(name=f"{obj_type}_init_region", target=table_name, ranges=[region_box]), f"{obj_type}_init_region"


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
    
    # Add objects from the object source (whichever has floor)
    take_items = object_source.get('take', [])
    added_objs = []
    initialized = {stmt.split()[1] for stmt in output.init if stmt.startswith('(On')}
    
    for item in take_items:
        if item.endswith('_1') or item.endswith('_2'):
            obj_type = extract_object_type(item)
            if item not in output.objects:
                output.objects[item] = obj_type
                added_objs.append(item)
                # Add contain_region for containers
                if obj_type in ['basket', 'wooden_tray']:
                    contain_region = Region(name="contain_region", target=item)
                    output.regions["contain_region"] = contain_region
                # Add init placement for this object if not already placed
                if item not in initialized:
                    region, region_name = allocate_region(table_name, obj_type, output.regions)
                    output.regions[region_name] = region
                    output.init.append(f"(On {item} {table_name}_{region_name})")
    
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
    
    initialized = {stmt.split()[1] for stmt in output.init if stmt.startswith('(On')}
    
    # Place first landmark
    landmark_center = (0.0, 0.05)
    if landmark_obj and landmark_obj not in initialized:
        landmark_type = extract_object_type(landmark_obj)
        landmark_region, landmark_region_name = allocate_region(table_name, landmark_type, output.regions)
        output.regions[landmark_region_name] = landmark_region
        output.init.append(f"(On {landmark_obj} {table_name}_{landmark_region_name})")
        lr = landmark_region.ranges[0]
        landmark_center = ((lr[0] + lr[2]) / 2, (lr[1] + lr[3]) / 2)
    
    # Place second landmark (for 'between' relation)
    landmark_center2 = None
    if landmark_obj2 and landmark_obj2 not in initialized:
        landmark_type2 = extract_object_type(landmark_obj2)
        landmark_region2, landmark_region_name2 = allocate_region(table_name, landmark_type2, output.regions)
        output.regions[landmark_region_name2] = landmark_region2
        output.init.append(f"(On {landmark_obj2} {table_name}_{landmark_region_name2})")
        lr2 = landmark_region2.ranges[0]
        landmark_center2 = ((lr2[0] + lr2[2]) / 2, (lr2[1] + lr2[3]) / 2)
    
    # Place manipulation object relative to landmark(s)
    # ALWAYS re-place manip_obj to ensure correct spatial relation (remove old placement first)
    if manip_obj:
        # Remove old placement of manip_obj from init
        output.init = [stmt for stmt in output.init if f"(On {manip_obj} " not in stmt]
        
        manip_type = extract_object_type(manip_obj)
        
        if relation == 'between' and landmark_center2:
            # For 'between': place at midpoint of two landmarks
            between_center = ((landmark_center[0] + landmark_center2[0]) / 2,
                              (landmark_center[1] + landmark_center2[1]) / 2)
            manip_region, manip_region_name = allocate_region_at_offset(
                table_name, manip_type, between_center, (0.0, 0.0), output.regions
            )
        else:
            offset = SPATIAL_OFFSETS.get(relation, (-0.12, 0.0))
            manip_region, manip_region_name = allocate_region_at_offset(
                table_name, manip_type, landmark_center, offset, output.regions
            )
        output.regions[manip_region_name] = manip_region
        output.init.append(f"(On {manip_obj} {table_name}_{manip_region_name})")
    
    if source_c:
        distractor_items = source_c.get('take', [])
        # Get already placed objects (landmarks, manip_obj)
        already_placed = {landmark_obj, landmark_obj2, manip_obj} - {None}
        for item in distractor_items:
            if item.endswith('_1') or item.endswith('_2'):
                # Skip if already placed as landmark or manip object
                if item in already_placed:
                    continue
                if item not in output.objects:
                    obj_type = extract_object_type(item)
                    output.objects[item] = obj_type
                    region, region_name = allocate_region(table_name, obj_type, output.regions)
                    output.regions[region_name] = region
                    output.init.append(f"(On {item} {table_name}_{region_name})")
    
    output.obj_of_interest = []
    if manip_obj:
        output.obj_of_interest.append(manip_obj)
    if landmark_obj:
        output.obj_of_interest.append(landmark_obj)
    if landmark_obj2:
        output.obj_of_interest.append(landmark_obj2)
    
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
