#!/usr/bin/env python3
"""
BDDL validation utilities for checking and fixing region overlaps.

This module provides functions to:
1. Validate BDDL files for overlapping placement regions
2. Re-allocate overlapping regions to non-overlapping positions
3. Filter out unused template regions

IMPORTANT: All placements must stay within table bounds and camera view.
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Set
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from er_constants import (
    OBJECT_SIZES, COLLISION_MARGIN, COLLISION_SIZE_MULTIPLIER,
    PLACEMENT_TOLERANCE, get_object_size, OBJECT_PLACEMENT_POSITIONS
)

# Workspace bounds - objects must stay within these limits
# These are conservative bounds to ensure objects stay on table and in camera view
WORKSPACE_BOUNDS = {
    'x_min': -0.22,  # Back of table (toward robot)
    'x_max': 0.22,   # Front of table (away from robot)
    'y_min': -0.28,  # Right side (robot's right)
    'y_max': 0.28,   # Left side (robot's left)
}


@dataclass
class OverlapInfo:
    """Information about an overlap between two regions."""
    region1: str
    region2: str
    obj_type1: str
    obj_type2: str
    overlap_area: float
    distance: float


def extract_object_type_from_region(region_name: str) -> str:
    """Extract object type from region name."""
    if '_init_region' in region_name:
        base = region_name.replace('_init_region', '')
        return base.rstrip('_0123456789')
    
    fixture_map = {
        'cabinet_region': 'wooden_cabinet',
        'wooden_cabinet_init_region': 'wooden_cabinet',
        'stove_region': 'flat_stove',
        'wine_rack_region': 'wine_rack',
        'desk_caddy_init_region': 'desk_caddy',
        'desk_caddy_region': 'desk_caddy',
        'desk_caddy_right_region': 'desk_caddy',
        'basket_init_region': 'basket',
        'wooden_tray_init_region': 'wooden_tray',
        'plate_region': 'plate',
        'plate_left': 'plate',
        'plate_right': 'plate',
        'ramekin_region': 'glazed_rim_porcelain_ramekin',
        'box_region': 'cookies',
    }
    
    for key, val in fixture_map.items():
        if key in region_name:
            return val
    
    return region_name.replace('_region', '').replace('_init', '').rstrip('_0123456789')


def is_within_workspace(cx: float, cy: float, obj_type: str) -> bool:
    """Check if an object centered at (cx, cy) stays within workspace bounds."""
    obj_w, obj_d = get_object_size(obj_type, for_collision=False)
    half_w, half_d = obj_w / 2, obj_d / 2
    
    return (cx - half_w >= WORKSPACE_BOUNDS['x_min'] and
            cx + half_w <= WORKSPACE_BOUNDS['x_max'] and
            cy - half_d >= WORKSPACE_BOUNDS['y_min'] and
            cy + half_d <= WORKSPACE_BOUNDS['y_max'])


def get_region_box(region_ranges: Tuple[float, float, float, float], 
                   obj_type: str, use_collision_size: bool = True) -> Tuple[float, float, float, float]:
    """Get the bounding box for a region based on its center and object size."""
    cx = (region_ranges[0] + region_ranges[2]) / 2
    cy = (region_ranges[1] + region_ranges[3]) / 2
    
    obj_w, obj_d = get_object_size(obj_type, for_collision=use_collision_size)
    half_w, half_d = obj_w / 2, obj_d / 2
    
    return (cx - half_w, cy - half_d, cx + half_w, cy + half_d)


def boxes_overlap(box1: Tuple[float, float, float, float], 
                  box2: Tuple[float, float, float, float],
                  margin: float = 0.0) -> bool:
    """Check if two bounding boxes overlap with optional margin."""
    x1_min, y1_min, x1_max, y1_max = box1
    x2_min, y2_min, x2_max, y2_max = box2
    
    x1_min -= margin
    y1_min -= margin
    x1_max += margin
    y1_max += margin
    
    return not (x1_max <= x2_min or x2_max <= x1_min or 
                y1_max <= y2_min or y2_max <= y1_min)


def calculate_overlap_area(box1: Tuple[float, float, float, float], 
                           box2: Tuple[float, float, float, float]) -> float:
    """Calculate the overlap area between two boxes in m²."""
    x_overlap = max(0, min(box1[2], box2[2]) - max(box1[0], box2[0]))
    y_overlap = max(0, min(box1[3], box2[3]) - max(box1[1], box2[1]))
    return x_overlap * y_overlap


def find_overlaps(regions: Dict, init_statements: List[str], 
                  margin: float = COLLISION_MARGIN) -> List[OverlapInfo]:
    """Find all overlapping region pairs in a BDDL file."""
    used_regions = set()
    for stmt in init_statements:
        if stmt.startswith('(On'):
            parts = stmt.replace('(', '').replace(')', '').split()
            if len(parts) >= 3:
                region_ref = parts[2]
                for region_name in regions.keys():
                    if region_name in region_ref:
                        used_regions.add(region_name)
                        break
    
    placement_regions = {}
    for name, region in regions.items():
        if hasattr(region, 'ranges') and region.ranges:
            if name in used_regions or '_init_region' in name or name.endswith('_region'):
                placement_regions[name] = region
    
    overlaps = []
    region_names = list(placement_regions.keys())
    
    for i, name1 in enumerate(region_names):
        for name2 in region_names[i+1:]:
            region1 = placement_regions[name1]
            region2 = placement_regions[name2]
            
            if region1.target != region2.target:
                continue
            
            obj_type1 = extract_object_type_from_region(name1)
            obj_type2 = extract_object_type_from_region(name2)
            
            box1 = get_region_box(region1.ranges[0], obj_type1)
            box2 = get_region_box(region2.ranges[0], obj_type2)
            
            if boxes_overlap(box1, box2, margin):
                c1 = ((box1[0] + box1[2]) / 2, (box1[1] + box1[3]) / 2)
                c2 = ((box2[0] + box2[2]) / 2, (box2[1] + box2[3]) / 2)
                distance = ((c1[0] - c2[0])**2 + (c1[1] - c2[1])**2)**0.5
                overlap_area = calculate_overlap_area(box1, box2)
                
                overlaps.append(OverlapInfo(
                    region1=name1,
                    region2=name2,
                    obj_type1=obj_type1,
                    obj_type2=obj_type2,
                    overlap_area=overlap_area,
                    distance=distance,
                ))
    
    return overlaps


def get_occupied_boxes_from_regions(regions: Dict, exclude_region: str = None) -> List[Tuple[float, float, float, float]]:
    """Get list of occupied bounding boxes from regions."""
    occupied = []
    for name, region in regions.items():
        if name == exclude_region:
            continue
        if not hasattr(region, 'ranges') or not region.ranges:
            continue
        obj_type = extract_object_type_from_region(name)
        box = get_region_box(region.ranges[0], obj_type, use_collision_size=True)
        occupied.append(box)
    return occupied


def find_non_overlapping_position(obj_type: str, 
                                   existing_regions: Dict,
                                   exclude_region: str = None) -> Optional[Tuple[float, float]]:
    """
    Find a non-overlapping position for an object within workspace bounds.
    
    Returns (cx, cy) center position or None if no position found.
    """
    collision_w, collision_d = get_object_size(obj_type, for_collision=True)
    half_cw, half_cd = collision_w / 2, collision_d / 2
    
    occupied = get_occupied_boxes_from_regions(existing_regions, exclude_region)
    
    # Placement positions within workspace bounds
    # Prioritize center and spread outward
    valid_positions = []
    for cx, cy in OBJECT_PLACEMENT_POSITIONS:
        if is_within_workspace(cx, cy, obj_type):
            valid_positions.append((cx, cy))
    
    for cx, cy in valid_positions:
        new_box = (cx - half_cw, cy - half_cd, cx + half_cw, cy + half_cd)
        collision = any(boxes_overlap(new_box, obox, COLLISION_MARGIN) for obox in occupied)
        if not collision:
            return (cx, cy)
    
    # Grid search within workspace bounds
    for x_offset in [i * 0.05 for i in range(-4, 5)]:  # -0.20 to 0.20
        for y_offset in [i * 0.05 for i in range(-5, 6)]:  # -0.25 to 0.25
            cx, cy = x_offset, y_offset
            if not is_within_workspace(cx, cy, obj_type):
                continue
            new_box = (cx - half_cw, cy - half_cd, cx + half_cw, cy + half_cd)
            collision = any(boxes_overlap(new_box, obox, COLLISION_MARGIN) for obox in occupied)
            if not collision:
                return (cx, cy)
    
    return None


def relocate_region(region, obj_type: str, new_center: Tuple[float, float]):
    """Update a region's ranges to be centered at new_center."""
    actual_w, actual_d = get_object_size(obj_type, for_collision=False)
    half_w, half_d = actual_w / 2, actual_d / 2
    
    new_ranges = (
        new_center[0] - half_w - PLACEMENT_TOLERANCE,
        new_center[1] - half_d - PLACEMENT_TOLERANCE,
        new_center[0] + half_w + PLACEMENT_TOLERANCE,
        new_center[1] + half_d + PLACEMENT_TOLERANCE,
    )
    region.ranges = [new_ranges]


def fix_overlaps(regions: Dict, init_statements: List[str], 
                 max_iterations: int = 10, verbose: bool = False) -> int:
    """Fix overlapping regions by relocating them to non-overlapping positions."""
    immovable_fixtures = {'wooden_cabinet', 'white_cabinet', 'flat_stove', 'desk_caddy', 'wine_rack'}
    template_regions = {'cabinet_region', 'stove_region', 'wine_rack_region'}
    
    total_relocated = 0
    
    for iteration in range(max_iterations):
        overlaps = find_overlaps(regions, init_statements)
        if not overlaps:
            break
        
        if verbose:
            print(f"  Iteration {iteration + 1}: {len(overlaps)} overlaps found")
        
        def get_size_score(overlap):
            size1 = get_object_size(overlap.obj_type1)[0] * get_object_size(overlap.obj_type1)[1]
            size2 = get_object_size(overlap.obj_type2)[0] * get_object_size(overlap.obj_type2)[1]
            return min(size1, size2)
        
        relocated_this_iter = False
        for overlap in sorted(overlaps, key=get_size_score):
            obj_type1, obj_type2 = overlap.obj_type1, overlap.obj_type2
            region1, region2 = overlap.region1, overlap.region2
            
            can_move_1 = (obj_type1 not in immovable_fixtures and 
                         region1 not in template_regions and
                         region1 in regions)
            can_move_2 = (obj_type2 not in immovable_fixtures and 
                         region2 not in template_regions and
                         region2 in regions)
            
            if not can_move_1 and not can_move_2:
                continue
            
            size1 = get_object_size(obj_type1)[0] * get_object_size(obj_type1)[1]
            size2 = get_object_size(obj_type2)[0] * get_object_size(obj_type2)[1]
            
            if can_move_1 and can_move_2:
                if size1 <= size2:
                    region_to_fix, obj_type = region1, obj_type1
                else:
                    region_to_fix, obj_type = region2, obj_type2
            elif can_move_1:
                region_to_fix, obj_type = region1, obj_type1
            else:
                region_to_fix, obj_type = region2, obj_type2
            
            new_pos = find_non_overlapping_position(obj_type, regions, exclude_region=region_to_fix)
            if new_pos:
                relocate_region(regions[region_to_fix], obj_type, new_pos)
                total_relocated += 1
                relocated_this_iter = True
                if verbose:
                    print(f"    Relocated {region_to_fix} to ({new_pos[0]:.3f}, {new_pos[1]:.3f})")
                break
        
        if not relocated_this_iter:
            break
    
    return total_relocated


def filter_unused_template_regions(regions: Dict, init_statements: List[str], 
                                    keep_patterns: Set[str] = None) -> Dict:
    """Remove template regions that aren't used by any object."""
    if keep_patterns is None:
        keep_patterns = {'contain_region', 'top_region', 'middle_region', 'bottom_region', 
                         'top_side', 'cook_region', 'front_contain_region', 'left_contain_region',
                         'right_contain_region', 'back_contain_region'}
    
    used_regions = set()
    for stmt in init_statements:
        if stmt.startswith('(On'):
            for region_name in regions.keys():
                if region_name in stmt:
                    used_regions.add(region_name)
    
    filtered = {}
    for name, region in regions.items():
        if name in used_regions:
            filtered[name] = region
            continue
        if any(pattern in name for pattern in keep_patterns):
            filtered[name] = region
            continue
        if '_init_region' in name:
            filtered[name] = region
            continue
        if not hasattr(region, 'ranges') or not region.ranges:
            filtered[name] = region
            continue
    
    return filtered


def validate_bddl(regions: Dict, init_statements: List[str], 
                  fix: bool = True, verbose: bool = False) -> Tuple[bool, List[OverlapInfo]]:
    """Validate a BDDL file for overlapping regions."""
    overlaps = find_overlaps(regions, init_statements)
    
    if not overlaps:
        return True, []
    
    if verbose:
        print(f"  Found {len(overlaps)} overlapping region pairs")
    
    if fix:
        relocated = fix_overlaps(regions, init_statements, verbose=verbose)
        if verbose:
            print(f"  Relocated {relocated} regions")
        overlaps = find_overlaps(regions, init_statements)
    
    return len(overlaps) == 0, overlaps

