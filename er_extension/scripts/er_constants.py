"""
Common constants for ER suite generation.

This file centralizes object sizes, collision margins, and other shared parameters
used by all ER suite generation scripts.

Object sizes are extracted from MuJoCo XML asset files in:
  libero/libero/assets/{turbosquid_objects,stable_scanned_objects,stable_hope_objects,articulated_objects}/

Size format: (width_x, depth_y) in meters - represents the actual collision footprint.
A COLLISION_MARGIN is added during placement to prevent overlaps.

IMPORTANT: When placing objects, consider visibility - avoid placing small manipulation
objects behind large fixtures that would occlude them from the camera view.
"""

# Safety margin added to object footprints during collision detection (meters)
COLLISION_MARGIN = 0.05

# Object size multiplier for collision detection
# Objects/fixtures are expanded by this factor to prevent physics instability
COLLISION_SIZE_MULTIPLIER = 1.5

# Random placement tolerance - how much variation around center point
# Smaller = more deterministic placement, more stable evaluations
# The region will be: center ± PLACEMENT_TOLERANCE
PLACEMENT_TOLERANCE = 0.005  # 5mm random range for very stable eval

# Placement zones for objects (front/center of table, away from fixtures)
# Format: list of (x, y) centers, ordered by priority
# Positive y = front of table (toward camera), negative y = back of table
OBJECT_PLACEMENT_POSITIONS = [
    # Front row - best visibility, away from fixtures
    (0.0, 0.15), (-0.12, 0.15), (0.12, 0.15),
    # Mid-front row
    (0.0, 0.08), (-0.15, 0.08), (0.15, 0.08),
    # Center row
    (-0.08, 0.0), (0.08, 0.0), (0.0, 0.0),
    # Mid-back row (still visible)
    (-0.12, -0.08), (0.12, -0.08), (0.0, -0.08),
]

# Placement zones for target objects (where robot needs to place)
# Slightly more centered for reachability
TARGET_PLACEMENT_POSITIONS = [
    (0.0, 0.12), (-0.10, 0.12), (0.10, 0.12),
    (0.0, 0.05), (-0.12, 0.05), (0.12, 0.05),
]

# Placement zones for fixtures (back/sides of table)
FIXTURE_PLACEMENT_POSITIONS = [
    (0.0, -0.20), (-0.25, -0.15), (0.25, -0.15),  # Back row
    (-0.30, 0.0), (0.30, 0.0),  # Sides
]

# Object footprint sizes (width_x, depth_y) in meters
# Extracted from XML collision geom extents
OBJECT_SIZES = {
    # === Large fixtures (place first, avoid occluding small objects) ===
    # wooden_cabinet.xml: base extends ±0.119 x, ±0.109 y
    'wooden_cabinet': (0.25, 0.22),
    # white_cabinet.xml: same dimensions as wooden
    'white_cabinet': (0.25, 0.22),
    # flat_stove.xml: burner at (0.15,0) with size 0.095, button section
    'flat_stove': (0.33, 0.23),
    # wine_rack.xml: extends ±0.093 x, ±0.069 y, plus tilted planes
    'wine_rack': (0.24, 0.2),
    # desk_caddy.xml: extends ±0.067 x, ±0.209 y
    'desk_caddy': (0.2, 0.44),

    # === Medium containers (may contain objects, wide footprints) ===
    # basket.xml: walls at ±0.076 x, ±0.069 y, contain_region ±0.061
    # INCREASED significantly to avoid collision with tray/bowl
    'basket': (0.32, 0.3),
    # wooden_tray.xml: extends ±0.147 x, ±0.085 y
    # INCREASED to avoid collision with basket
    'wooden_tray': (0.4, 0.3),
    # chefmate_8_frypan.xml: pan ±0.055, handle to x=0.193
    'chefmate_8_frypan': (0.28, 0.15),

    # === Dishes and bowls ===
    # plate.xml: circular, extends ±0.048 radius
    'plate': (0.12, 0.12),
    # akita_black_bowl.xml: extends ±0.047 (scaled 0.7)
    # INCREASED: to avoid collision with basket
    'akita_black_bowl': (0.14, 0.14),
    # glazed_rim_porcelain_ramekin: small bowl
    'glazed_rim_porcelain_ramekin': (0.10, 0.10),

    # === Mugs (include handle width) ===
    # white_yellow_mug.xml: body ±0.060 x (with handle), ±0.042 y
    # INCREASED: to avoid collision with basket
    'white_yellow_mug': (0.16, 0.12),
    # porcelain_mug.xml: similar dimensions
    'porcelain_mug': (0.16, 0.12),
    # red_coffee_mug.xml: similar dimensions
    'red_coffee_mug': (0.16, 0.12),

    # === Bottles and tall objects ===
    # moka_pot.xml: body ±0.025, handle extends to y=0.075
    'moka_pot': (0.06, 0.13),
    # wine_bottle.xml: body ±0.015 (narrow)
    'wine_bottle': (0.04, 0.04),

    # === Books (when laying flat) ===
    # black_book.xml: size 0.014 x 0.055 x 0.067
    'black_book': (0.12, 0.04),
    # yellow_book.xml: similar
    'yellow_book': (0.12, 0.04),

    # === Small food items (HOPE dataset, scaled) ===
    # INCREASED all sizes to prevent collisions in crowded scenes
    # butter.xml: size 0.009 x 0.020 x 0.038 (scaled 0.0075)
    'butter': (0.10, 0.06),
    # milk.xml: size 0.026 x 0.026 x 0.055 (with handle)
    'milk': (0.08, 0.12),
    # ketchup.xml: small bottle
    'ketchup': (0.06, 0.10),
    # cream_cheese.xml: box shape
    'cream_cheese': (0.09, 0.07),
    # alphabet_soup.xml: can shape
    'alphabet_soup': (0.08, 0.08),
    # orange_juice.xml: carton (similar to milk)
    'orange_juice': (0.08, 0.12),
    # tomato_sauce.xml: can shape
    'tomato_sauce': (0.08, 0.08),
    # salad_dressing.xml: bottle
    'salad_dressing': (0.07, 0.10),
    # chocolate_pudding.xml: cup shape
    'chocolate_pudding': (0.08, 0.08),
    # bbq_sauce.xml: bottle
    'bbq_sauce': (0.07, 0.10),
    # cookies.xml: box shape
    'cookies': (0.10, 0.10),

    # Default for unknown objects (conservative)
    'default': (0.10, 0.10),
}

# Object height categories for visibility checks
# Objects should not be placed behind taller objects
OBJECT_HEIGHTS = {
    # Tall fixtures (>0.15m) - place at back or sides
    'wooden_cabinet': 0.22,
    'white_cabinet': 0.22,
    'wine_rack': 0.25,
    'desk_caddy': 0.14,
    
    # Medium height (0.08-0.15m)
    'basket': 0.14,
    'moka_pot': 0.09,
    'wine_bottle': 0.16,
    'milk': 0.11,
    'orange_juice': 0.11,
    
    # Low objects (<0.08m)
    'plate': 0.03,
    'akita_black_bowl': 0.05,
    'butter': 0.04,
    'flat_stove': 0.04,
    'wooden_tray': 0.08,
}


def get_object_size(obj_type: str, for_collision: bool = True) -> tuple:
    """Get the (width, depth) footprint size for an object type.
    
    Args:
        obj_type: Object type name
        for_collision: If True, apply COLLISION_SIZE_MULTIPLIER for collision detection
    """
    # Try exact match first
    if obj_type in OBJECT_SIZES:
        size = OBJECT_SIZES[obj_type]
    elif obj_type.rstrip('_0123456789') in OBJECT_SIZES:
        size = OBJECT_SIZES[obj_type.rstrip('_0123456789')]
    else:
        # Try to find a partial match in the object name
        size = OBJECT_SIZES['default']
        for key in OBJECT_SIZES:
            if key in obj_type.lower():
                size = OBJECT_SIZES[key]
                break
    
    if for_collision:
        return (size[0] * COLLISION_SIZE_MULTIPLIER, size[1] * COLLISION_SIZE_MULTIPLIER)
    return size


def get_object_height(obj_type: str) -> float:
    """Get object height for visibility ordering."""
    if obj_type in OBJECT_HEIGHTS:
        return OBJECT_HEIGHTS[obj_type]
    base_type = obj_type.rstrip('_0123456789')
    return OBJECT_HEIGHTS.get(base_type, 0.10)


def is_large_fixture(obj_type: str) -> bool:
    """Check if object is a large fixture that should be placed carefully."""
    large_fixtures = {
        'wooden_cabinet', 'white_cabinet', 'wine_rack', 
        'desk_caddy', 'flat_stove', 'wooden_tray', 'basket'
    }
    base_type = obj_type.rstrip('_0123456789')
    return base_type in large_fixtures or obj_type in large_fixtures
