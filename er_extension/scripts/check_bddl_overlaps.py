#!/usr/bin/env python3
"""
Analyze BDDL files for overlapping regions that could cause object collisions.

This script checks every pair of objects' init regions in each BDDL file
to find potential collision issues.
"""

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import defaultdict

# Import from er_constants
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from er_constants import OBJECT_SIZES, COLLISION_MARGIN, get_object_size


@dataclass
class Region:
    name: str
    target: str
    ranges: Optional[Tuple[float, float, float, float]] = None
    
    @property
    def center(self) -> Optional[Tuple[float, float]]:
        if self.ranges:
            return ((self.ranges[0] + self.ranges[2]) / 2, (self.ranges[1] + self.ranges[3]) / 2)
        return None


def parse_bddl_regions(filepath: str) -> Dict[str, Region]:
    """Parse regions from a BDDL file."""
    with open(filepath, 'r') as f:
        content = f.read()

    regions = {}
    regions_block = re.search(r'\(:regions(.*?)\)\s*\n\s*\(:fixtures', content, re.DOTALL)
    if not regions_block:
        return regions

    region_text = regions_block.group(1)
    
    # Match regions with ranges
    range_pattern = r'\((\w+)\s+\(:target\s+(\w+)\)(?:.*?\(:ranges\s*\(\s*\(([-\d.\s]+)\)\s*\))?'
    for match in re.finditer(range_pattern, region_text, re.DOTALL):
        name = match.group(1)
        target = match.group(2)
        coords_str = match.group(3)
        
        ranges = None
        if coords_str:
            coords = [float(x) for x in coords_str.split()]
            if len(coords) == 4:
                ranges = (coords[0], coords[1], coords[2], coords[3])
        
        regions[name] = Region(name=name, target=target, ranges=ranges)

    return regions


def extract_object_type(region_name: str) -> str:
    """Extract object type from region name like butter_init_region -> butter."""
    if '_init_region' in region_name:
        base = region_name.replace('_init_region', '')
        return base.rstrip('_0123456789')
    # Handle fixture regions
    fixture_map = {
        'cabinet_region': 'wooden_cabinet',
        'stove_region': 'flat_stove',
        'wine_rack_region': 'wine_rack',
        'desk_caddy_init_region': 'desk_caddy',
        'wooden_cabinet_init_region': 'wooden_cabinet',
        'wooden_tray_init_region': 'wooden_tray',
    }
    for key, val in fixture_map.items():
        if key in region_name:
            return val
    return region_name.replace('_region', '').replace('_init', '').rstrip('_0123456789')


def get_expanded_box(region: Region, margin: float = 0.0) -> Optional[Tuple[float, float, float, float]]:
    """Get the expanded bounding box for a region based on object size."""
    if not region.ranges:
        return None
    
    obj_type = extract_object_type(region.name)
    obj_w, obj_d = get_object_size(obj_type, for_collision=False)
    
    center = region.center
    half_w, half_d = obj_w / 2 + margin, obj_d / 2 + margin
    
    return (center[0] - half_w, center[1] - half_d, center[0] + half_w, center[1] + half_d)


def boxes_overlap(box1: Tuple[float, float, float, float], 
                  box2: Tuple[float, float, float, float]) -> bool:
    """Check if two bounding boxes overlap."""
    x1_min, y1_min, x1_max, y1_max = box1
    x2_min, y2_min, x2_max, y2_max = box2
    
    return not (x1_max <= x2_min or x2_max <= x1_min or 
                y1_max <= y2_min or y2_max <= y1_min)


def calculate_overlap_area(box1: Tuple[float, float, float, float], 
                           box2: Tuple[float, float, float, float]) -> float:
    """Calculate the overlap area between two boxes."""
    x1_min, y1_min, x1_max, y1_max = box1
    x2_min, y2_min, x2_max, y2_max = box2
    
    x_overlap = max(0, min(x1_max, x2_max) - max(x1_min, x2_min))
    y_overlap = max(0, min(y1_max, y2_max) - max(y1_min, y2_min))
    
    return x_overlap * y_overlap


def is_spurious_region(name: str) -> bool:
    """Check if a region is spurious and should be skipped."""
    # Skip containment regions that incorrectly have ranges on table
    if 'contain' in name and '_init_region' not in name:
        return True
    return False


def is_intentional_adjacency(name1: str, name2: str) -> bool:
    """Check if two regions are intentionally adjacent."""
    # Patterns like "next_to_X" and "X" are intentional
    obj1 = name1.replace('_init_region', '').replace('_region', '')
    obj2 = name2.replace('_init_region', '').replace('_region', '')
    if obj1.startswith('next_to_') and obj1.replace('next_to_', '') == obj2:
        return True
    if obj2.startswith('next_to_') and obj2.replace('next_to_', '') == obj1:
        return True
    if obj1.startswith('between_') or obj2.startswith('between_'):
        return True
    return False


def analyze_bddl_file(filepath: str, margin: float = 0.02) -> List[dict]:
    """Analyze a single BDDL file for overlapping regions."""
    regions = parse_bddl_regions(filepath)
    
    # Filter to only valid placement regions
    placement_regions = {
        name: r for name, r in regions.items() 
        if r.ranges and not is_spurious_region(name)
    }
    
    overlaps = []
    region_names = list(placement_regions.keys())
    
    for i, name1 in enumerate(region_names):
        for name2 in region_names[i+1:]:
            region1 = placement_regions[name1]
            region2 = placement_regions[name2]
            
            # Skip if on different targets (different surfaces)
            if region1.target != region2.target:
                continue
            
            # Skip intentionally adjacent regions
            if is_intentional_adjacency(name1, name2):
                continue
            
            box1 = get_expanded_box(region1, margin)
            box2 = get_expanded_box(region2, margin)
            
            if box1 and box2 and boxes_overlap(box1, box2):
                overlap_area = calculate_overlap_area(box1, box2)
                obj1 = extract_object_type(name1)
                obj2 = extract_object_type(name2)
                
                # Calculate distance between centers
                c1, c2 = region1.center, region2.center
                distance = ((c1[0] - c2[0])**2 + (c1[1] - c2[1])**2)**0.5
                
                overlaps.append({
                    'region1': name1,
                    'region2': name2,
                    'obj1': obj1,
                    'obj2': obj2,
                    'box1': box1,
                    'box2': box2,
                    'raw_range1': region1.ranges,
                    'raw_range2': region2.ranges,
                    'overlap_area': overlap_area,
                    'distance': distance,
                    'target': region1.target,
                })
    
    return overlaps


def analyze_clustering(filepath: str) -> dict:
    """Analyze whether objects are clustered together with large empty spaces."""
    regions = parse_bddl_regions(filepath)
    placement_regions = {name: r for name, r in regions.items() if r.ranges}
    
    if len(placement_regions) < 2:
        return {'clustered': False, 'objects': [], 'spread': 0}
    
    centers = []
    for name, region in placement_regions.items():
        if region.center:
            centers.append((region.center, extract_object_type(name)))
    
    if len(centers) < 2:
        return {'clustered': False, 'objects': [], 'spread': 0}
    
    # Calculate pairwise distances
    distances = []
    for i, (c1, _) in enumerate(centers):
        for j, (c2, _) in enumerate(centers):
            if i < j:
                dist = ((c1[0] - c2[0])**2 + (c1[1] - c2[1])**2)**0.5
                distances.append(dist)
    
    avg_distance = sum(distances) / len(distances)
    max_distance = max(distances)
    min_distance = min(distances)
    
    # Calculate bounding box of all centers
    xs = [c[0] for c, _ in centers]
    ys = [c[1] for c, _ in centers]
    spread_x = max(xs) - min(xs)
    spread_y = max(ys) - min(ys)
    
    # Define "clustered" as: min distance < 0.08 and spread < 0.25
    is_clustered = min_distance < 0.08 and max(spread_x, spread_y) < 0.25
    
    return {
        'clustered': is_clustered,
        'avg_distance': avg_distance,
        'min_distance': min_distance,
        'max_distance': max_distance,
        'spread_x': spread_x,
        'spread_y': spread_y,
        'num_objects': len(centers),
        'objects': [obj for _, obj in centers],
    }


def main():
    script_dir = Path(__file__).parent.parent.parent
    bddl_base = script_dir / "libero" / "libero" / "bddl_files"
    
    suites = ['er_goal', 'er_object', 'er_sequential', 'er_spatial']
    
    all_issues = []
    clustering_issues = []
    
    print("=" * 80)
    print("BDDL Region Overlap Analysis")
    print("=" * 80)
    
    for suite in suites:
        suite_dir = bddl_base / suite
        if not suite_dir.exists():
            print(f"Directory not found: {suite_dir}")
            continue
        
        print(f"\n{'='*60}")
        print(f"Analyzing: {suite}")
        print(f"{'='*60}")
        
        bddl_files = sorted(suite_dir.glob("*.bddl"))
        suite_overlaps = 0
        suite_clustered = 0
        
        for bddl_file in bddl_files:
            overlaps = analyze_bddl_file(str(bddl_file), margin=0.02)
            clustering = analyze_clustering(str(bddl_file))
            
            if overlaps:
                suite_overlaps += 1
                print(f"\n{bddl_file.name}: {len(overlaps)} potential overlap(s)")
                for ovl in overlaps:
                    print(f"  - {ovl['obj1']} <-> {ovl['obj2']}")
                    print(f"    Distance: {ovl['distance']:.3f}m, Overlap area: {ovl['overlap_area']*10000:.1f}cm²")
                    print(f"    Range1: ({ovl['raw_range1'][0]:.3f}, {ovl['raw_range1'][1]:.3f}, {ovl['raw_range1'][2]:.3f}, {ovl['raw_range1'][3]:.3f})")
                    print(f"    Range2: ({ovl['raw_range2'][0]:.3f}, {ovl['raw_range2'][1]:.3f}, {ovl['raw_range2'][2]:.3f}, {ovl['raw_range2'][3]:.3f})")
                    all_issues.append({
                        'file': bddl_file.name,
                        'suite': suite,
                        **ovl
                    })
            
            if clustering['clustered']:
                suite_clustered += 1
                clustering_issues.append({
                    'file': bddl_file.name,
                    'suite': suite,
                    **clustering
                })
        
        print(f"\n{suite} Summary: {suite_overlaps}/{len(bddl_files)} files with overlaps, "
              f"{suite_clustered} clustered")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    print(f"\nTotal files with overlaps: {len(set(i['file'] for i in all_issues))}")
    print(f"Total overlap pairs: {len(all_issues)}")
    
    # Group by object type pairs
    pair_counts = defaultdict(int)
    for issue in all_issues:
        pair = tuple(sorted([issue['obj1'], issue['obj2']]))
        pair_counts[pair] += 1
    
    print("\nMost common overlapping object pairs:")
    for pair, count in sorted(pair_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"  {pair[0]} <-> {pair[1]}: {count} occurrences")
    
    # Severe overlaps (high overlap area)
    severe = [i for i in all_issues if i['overlap_area'] > 0.002]
    if severe:
        print(f"\nSevere overlaps (>20cm² overlap area): {len(severe)}")
        for s in sorted(severe, key=lambda x: -x['overlap_area'])[:10]:
            print(f"  {s['suite']}/{s['file']}: {s['obj1']} <-> {s['obj2']} "
                  f"({s['overlap_area']*10000:.1f}cm²)")
    
    if clustering_issues:
        print(f"\nClustered scenes (objects too close together): {len(clustering_issues)}")
        for c in clustering_issues[:5]:
            print(f"  {c['suite']}/{c['file']}: {c['num_objects']} objects, "
                  f"min_dist={c['min_distance']:.3f}m, spread=({c['spread_x']:.3f}, {c['spread_y']:.3f})")
    
    # Return issue count for CI/CD
    return len(all_issues)


if __name__ == "__main__":
    issue_count = main()
    sys.exit(0 if issue_count == 0 else 1)

