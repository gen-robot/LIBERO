#!/usr/bin/env python3
"""
Generate ER-GOAL BDDL files from task specifications.
Redesigned for diversity across KITCHEN, LIVING_ROOM, and STUDY scenes.
"""

import os
import re
import yaml
import argparse
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from pathlib import Path


OBJECT_SIZES = {
    'akita_black_bowl': (0.12, 0.12),
    'plate': (0.14, 0.14),
    'butter': (0.06, 0.05),
    'cream_cheese': (0.07, 0.06),
    'ketchup': (0.05, 0.05),
    'milk': (0.07, 0.07),
    'tomato_sauce': (0.06, 0.06),
    'chocolate_pudding': (0.07, 0.07),
    'alphabet_soup': (0.07, 0.07),
    'orange_juice': (0.07, 0.07),
    'moka_pot': (0.10, 0.10),
    'wine_bottle': (0.07, 0.07),
    'frying_pan': (0.18, 0.18),
    'basket': (0.15, 0.15),
    'wooden_tray': (0.18, 0.12),
    'desk_caddy': (0.15, 0.12),
    'wooden_cabinet': (0.22, 0.22),
    'flat_stove': (0.28, 0.22),
    'wine_rack': (0.18, 0.15),
    'default': (0.08, 0.08),
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
    goal_match = re.search(r'\(:goal\s+\(And ([^)]+\))\s*\)', content)
    if goal_match:
        goal = goal_match.group(1)

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


def get_occupied_boxes(regions: Dict[str, Region]) -> List[Tuple[float, float, float, float]]:
    occupied = []
    for region in regions.values():
        if region.ranges:
            occupied.append(region.ranges[0])
    return occupied


def allocate_region(table_name: str, obj_type: str, regions: Dict[str, Region],
                    margin: float = 0.05) -> Tuple[Region, str]:
    """Allocate a non-overlapping region for an object."""
    size = OBJECT_SIZES.get(obj_type, OBJECT_SIZES['default'])
    half_w, half_d = size[0] / 2, size[1] / 2
    occupied = get_occupied_boxes(regions)
    
    # Grid search for free position
    candidates = []
    for x in [-0.15, -0.08, 0.0, 0.08, 0.15]:
        for y in [-0.12, -0.04, 0.04, 0.12, 0.20]:
            candidates.append((x, y))
    
    for cx, cy in candidates:
        new_box = (cx - half_w, cy - half_d, cx + half_w, cy + half_d)
        collision = any(boxes_overlap(new_box, obox, margin) for obox in occupied)
        if not collision:
            region_name = f"{obj_type}_init_region"
            counter = 1
            while region_name in regions:
                region_name = f"{obj_type}_init_region_{counter}"
                counter += 1
            region = Region(name=region_name, target=table_name, ranges=[new_box])
            return region, region_name
    
    # Fallback
    cx, cy = 0.12, 0.15
    new_box = (cx - half_w, cy - half_d, cx + half_w, cy + half_d)
    region_name = f"{obj_type}_init_region"
    return Region(name=region_name, target=table_name, ranges=[new_box]), region_name


def generate_er_goal_bddl(task_spec: dict, yaml_config: dict, bddl_base: str) -> BDDLFile:
    """Generate a single ER-GOAL BDDL file."""
    scene_key = task_spec['scene']
    scene_config = yaml_config['scenes'][scene_key]
    
    source_file = os.path.join(bddl_base, scene_config['source'])
    source = parse_bddl_file(source_file)
    
    output = BDDLFile(
        problem_name=scene_config['problem'],
        language=task_spec['language'],
    )
    
    table_name = scene_config['table']
    
    # Copy fixtures and regions from source
    output.fixtures = dict(source.fixtures)
    output.regions = dict(source.regions)
    
    # Copy objects from source
    output.objects = dict(source.objects)
    
    # Add manipulated object
    manip_obj = task_spec['manipulated_object']
    output.objects[manip_obj['instance']] = manip_obj['type']
    
    # Add distractor objects if specified
    add_objects = task_spec.get('add_objects', [])
    for obj in add_objects:
        output.objects[obj['instance']] = obj['type']
    
    # Set obj of interest
    output.obj_of_interest = [manip_obj['instance']]
    if task_spec['goal_target'] not in [r.target for r in output.regions.values()]:
        output.obj_of_interest.append(task_spec['goal_target'].split('_')[0] + '_1')
    
    # Allocate regions for new objects
    if manip_obj['instance'] not in [stmt.split()[1] for stmt in source.init if stmt.startswith('(On')]:
        region, region_name = allocate_region(table_name, manip_obj['type'], output.regions)
        output.regions[region_name] = region
    
    for obj in add_objects:
        region, region_name = allocate_region(table_name, obj['type'], output.regions)
        output.regions[region_name] = region
    
    # Build init statements
    output.init = list(source.init)
    
    # Add placements for new objects
    initialized = {stmt.split()[1] for stmt in output.init if stmt.startswith('(On')}
    
    if manip_obj['instance'] not in initialized:
        for rname, region in output.regions.items():
            if manip_obj['type'] in rname and region.target == table_name:
                output.init.append(f"(On {manip_obj['instance']} {table_name}_{rname})")
                break
    
    for obj in add_objects:
        if obj['instance'] not in initialized:
            for rname, region in output.regions.items():
                if obj['type'] in rname and region.target == table_name:
                    output.init.append(f"(On {obj['instance']} {table_name}_{rname})")
                    break
    
    output.goal = task_spec['goal']
    
    return output


def main():
    parser = argparse.ArgumentParser(description="Generate ER-GOAL BDDL files")
    parser.add_argument("--yaml-file", type=str, default="er_extension/task_specs/er_goal_tasks.yaml")
    parser.add_argument("--bddl-base", type=str, default="libero/libero/bddl_files")
    parser.add_argument("--output-dir", type=str, default="libero/libero/bddl_files/er_goal")
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
            output = generate_er_goal_bddl(task_spec, yaml_config, args.bddl_base)
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
