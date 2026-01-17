#!/usr/bin/env python3
"""
Generate ER-SPATIAL BDDL files from task specifications.
Redesigned for diversity with different objects, landmarks, and scenes.
"""

import os
import re
import yaml
import argparse
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional

from er_constants import OBJECT_SIZES, COLLISION_MARGIN, get_object_size

SPATIAL_OFFSETS = {
    'next_to': (-0.10, 0.0),
    'left_of': (-0.12, 0.0),
    'right_of': (0.12, 0.0),
    'in_front_of': (0.0, 0.10),
    'behind': (0.0, -0.10),
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
    goal_match = re.search(r'\(:goal\s+\(And ([^)]+\))\s*\)', content)
    if goal_match:
        goal = goal_match.group(1)

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
    occupied = []
    for region in regions.values():
        if region.ranges:
            occupied.append(region.ranges[0])
    return occupied


def allocate_region_at_offset(table_name: str, obj_type: str, landmark_center: Tuple[float, float],
                              offset: Tuple[float, float], regions: Dict[str, Region]) -> Tuple[Region, str]:
    """Allocate a region at a spatial offset from a landmark."""
    size = OBJECT_SIZES.get(obj_type, OBJECT_SIZES['default'])
    half_w, half_d = size[0] / 2, size[1] / 2
    
    cx = landmark_center[0] + offset[0]
    cy = landmark_center[1] + offset[1]
    
    # Check for collision and adjust if needed
    occupied = get_occupied_boxes(regions)
    new_box = (cx - half_w, cy - half_d, cx + half_w, cy + half_d)
    
    # Try nearby positions if collision
    for dx in [0, 0.05, -0.05, 0.10, -0.10]:
        for dy in [0, 0.05, -0.05, 0.10, -0.10]:
            test_box = (cx + dx - half_w, cy + dy - half_d, cx + dx + half_w, cy + dy + half_d)
            if not any(boxes_overlap(test_box, obox, 0.04) for obox in occupied):
                new_box = test_box
                break
        else:
            continue
        break
    
    region_name = f"{obj_type}_init_region"
    counter = 1
    while region_name in regions:
        region_name = f"{obj_type}_init_region_{counter}"
        counter += 1
    
    region = Region(name=region_name, target=table_name, ranges=[new_box])
    return region, region_name


def allocate_region(table_name: str, obj_type: str, regions: Dict[str, Region]) -> Tuple[Region, str]:
    """Allocate a non-overlapping region for an object."""
    size = OBJECT_SIZES.get(obj_type, OBJECT_SIZES['default'])
    half_w, half_d = size[0] / 2, size[1] / 2
    occupied = get_occupied_boxes(regions)
    
    candidates = []
    for x in [-0.15, -0.08, 0.0, 0.08, 0.15]:
        for y in [-0.12, -0.04, 0.04, 0.12, 0.20]:
            candidates.append((x, y))
    
    for cx, cy in candidates:
        new_box = (cx - half_w, cy - half_d, cx + half_w, cy + half_d)
        if not any(boxes_overlap(new_box, obox, 0.05) for obox in occupied):
            region_name = f"{obj_type}_init_region"
            counter = 1
            while region_name in regions:
                region_name = f"{obj_type}_init_region_{counter}"
                counter += 1
            return Region(name=region_name, target=table_name, ranges=[new_box]), region_name
    
    new_box = (0.1, 0.15, 0.1 + size[0], 0.15 + size[1])
    return Region(name=f"{obj_type}_init_region", target=table_name, ranges=[new_box]), f"{obj_type}_init_region"


def generate_er_spatial_bddl(task_spec: dict, yaml_config: dict, bddl_base: str) -> BDDLFile:
    """Generate a single ER-SPATIAL BDDL file."""
    scene_key = task_spec['scene']
    scene_config = yaml_config['scenes'][scene_key]
    
    source_file = os.path.join(bddl_base, scene_config['source'])
    source = parse_bddl_file(source_file)
    
    output = BDDLFile(
        problem_name=scene_config['problem'],
        language=task_spec['language'],
    )
    
    table_name = scene_config['table']
    
    # Copy fixtures from source
    output.fixtures = dict(source.fixtures)
    
    # Copy regions from source (we'll add new ones)
    output.regions = dict(source.regions)
    
    # Copy objects from source
    output.objects = dict(source.objects)
    
    # Get task objects
    manip_obj = task_spec['manipulated_object']
    landmark = task_spec['landmark']
    relation = task_spec['relation']
    
    # Add objects
    output.objects[manip_obj['instance']] = manip_obj['type']
    output.objects[landmark['instance']] = landmark['type']
    
    # Add distractor objects
    add_objects = task_spec.get('add_objects', [])
    for obj in add_objects:
        output.objects[obj['instance']] = obj['type']
    
    # Set obj of interest
    output.obj_of_interest = [manip_obj['instance'], task_spec['goal_target']]
    
    # First allocate landmark region
    landmark_region, landmark_region_name = allocate_region(table_name, landmark['type'], output.regions)
    output.regions[landmark_region_name] = landmark_region
    
    # Get landmark center for spatial offset calculation
    lr = landmark_region.ranges[0]
    landmark_center = ((lr[0] + lr[2]) / 2, (lr[1] + lr[3]) / 2)
    
    # Allocate manipulated object region at spatial offset from landmark
    offset = SPATIAL_OFFSETS.get(relation, (-0.10, 0.0))
    manip_region, manip_region_name = allocate_region_at_offset(
        table_name, manip_obj['type'], landmark_center, offset, output.regions
    )
    output.regions[manip_region_name] = manip_region
    
    # Allocate regions for additional objects
    for obj in add_objects:
        region, region_name = allocate_region(table_name, obj['type'], output.regions)
        output.regions[region_name] = region
    
    # Build init statements from source
    output.init = list(source.init)
    
    # Add placements for new objects
    initialized = {stmt.split()[1] for stmt in output.init if stmt.startswith('(On')}
    
    if manip_obj['instance'] not in initialized:
        output.init.append(f"(On {manip_obj['instance']} {table_name}_{manip_region_name})")
    
    if landmark['instance'] not in initialized:
        output.init.append(f"(On {landmark['instance']} {table_name}_{landmark_region_name})")
    
    for obj in add_objects:
        if obj['instance'] not in initialized:
            for rname in output.regions:
                if obj['type'] in rname:
                    output.init.append(f"(On {obj['instance']} {table_name}_{rname})")
                    break
    
    output.goal = task_spec['goal']
    
    return output


def main():
    parser = argparse.ArgumentParser(description="Generate ER-SPATIAL BDDL files")
    parser.add_argument("--yaml-file", type=str, default="er_extension/task_specs/er_spatial_tasks.yaml")
    parser.add_argument("--bddl-base", type=str, default="libero/libero/bddl_files")
    parser.add_argument("--output-dir", type=str, default="libero/libero/bddl_files/er_spatial")
    args = parser.parse_args()
    
    os.makedirs(args.output_dir, exist_ok=True)
    
    with open(args.yaml_file, 'r') as f:
        yaml_config = yaml.safe_load(f)
    
    success_count = 0
    for task_spec in yaml_config['tasks']:
        task_id = task_spec['id']
        task_name = task_spec['name']
        
        print(f"Generating: {task_id}_{task_name}")
        
        try:
            output = generate_er_spatial_bddl(task_spec, yaml_config, args.bddl_base)
            output_file = os.path.join(args.output_dir, f"{task_id}_{task_name}.bddl")
            with open(output_file, 'w') as f:
                f.write(output.to_bddl())
            print(f"  -> {output_file}")
            success_count += 1
        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\nGenerated {success_count}/{len(yaml_config['tasks'])} BDDL files")


if __name__ == "__main__":
    main()
