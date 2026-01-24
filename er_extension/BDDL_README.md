# BDDL Files Documentation

BDDL (Behavior Domain Definition Language) files define robotic manipulation tasks for the LIBERO benchmark. Each file specifies a complete task including the scene layout, objects, initial conditions, and goal conditions.

## Directory Structure

| Directory | Description | # Tasks |
|-----------|-------------|---------|
| `er_spatial/` | LIBERO-ER Spatial tasks - varying spatial relationships between objects | 40 |
| `er_sequential/` | LIBERO-ER Sequential tasks - multi-step manipulation sequences | 40 |
| `er_goal/` | LIBERO-ER Goal tasks - varying goal conditions | 40 |
| `er_object/` | LIBERO-ER Object tasks - varying target objects | 40 |
| `libero_spatial/` | Original LIBERO Spatial benchmark | 10 |
| `libero_object/` | Original LIBERO Object benchmark | 10 |
| `libero_goal/` | Original LIBERO Goal benchmark | 10 |
| `libero_90/` | LIBERO-90 diverse task set | 90 |
| `libero_10/` | LIBERO-10 long-horizon tasks | 10 |

## Coordinate System

All coordinates are in **meters** and relative to the workspace center (typically the table center).

### Image Orientation

In the rendered images:
- **Robot** is at the **TOP** of the image
- **Image's LEFT** = Robot's **RIGHT**
- Camera looks down from behind/above the robot

### BDDL to Image Coordinate Mapping

```
                    Image TOP (-X, near robot)
                    ┌─────────────────────────┐
                    │      ┌─────────┐        │
                    │      │  ROBOT  │        │
                    │      └─────────┘        │
    Image LEFT      │                         │      Image RIGHT
    (-Y direction)  │     ┌───────────┐       │      (+Y direction)
    (robot's right) │     │   TABLE   │       │      (robot's left)
                    │     │  CENTER   │       │
                    │     │  (0, 0)   │       │
                    │     └───────────┘       │
                    │                         │
                    └─────────────────────────┘
                    Image BOTTOM (+X, away from robot)
```

| BDDL Axis | Image Direction | Description |
|-----------|-----------------|-------------|
| **+X** | Image **BOTTOM** (↓) | Away from robot, front of table |
| **-X** | Image **TOP** (↑) | Closer to robot arm |
| **+Y** | Image **RIGHT** (→) | Robot's left side |
| **-Y** | Image **LEFT** (←) | Robot's right side |
| **Z** | Out of screen | Height (handled automatically) |

### Visual Example: `er_goal_01.bddl`

```
                         -X (Image TOP, near robot)
                              ↑
                    ┌─────────┼─────────┐
                    │     [ROBOT]       │
                    │         │         │
                    │   CABINET        │
                    │  (-0.01,-0.30)    │
   -Y (Image LEFT)  │         │         │  +Y (Image RIGHT)
         ←──────────┼────BOWL─┼─────────┼──────────→
                    │   (0,0) │  PLATE  │
                    │         │ (0,+0.25)│
                    │         │         │
                    │      BUTTER       │
                    │   (+0.12,+0.15)   │
                    └─────────┼─────────┘
                              │
                              ↓
                         +X (Image BOTTOM, away from robot)
```

Objects in `er_goal_01.bddl`:
| Object | X range | Y range | Image Position |
|--------|---------|---------|----------------|
| Cabinet | -0.01 to 0.01 | -0.31 to -0.29 | Near robot (top), far LEFT |
| Bowl | -0.025 to 0.025 | -0.025 to 0.025 | TABLE CENTER |
| Plate | -0.025 to 0.025 | 0.225 to 0.275 | Near robot (top), far RIGHT |
| Butter | 0.065 to 0.175 | 0.115 to 0.185 | Away from robot (bottom), RIGHT of center |

### Workspace Offsets by Scene Type

These offsets translate table-relative coordinates to world coordinates:

| Scene Type | Offset (X, Y, Z) | Z = Table Height |
|------------|------------------|------------------|
| Kitchen table | `(0, 0, 0.90)` | 0.90m |
| Study table | `(-0.2, 0, 0.867)` | 0.867m |
| Living room table | `(0, 0, 0.41)` | 0.41m |
| Coffee table | `(0, 0, 0.41)` | 0.41m |
| Floor | `(0, 0, -0.035)` | Ground level |

---

## BDDL File Structure

### Basic Syntax

```lisp
(define (problem PROBLEM_NAME)
  (:domain robosuite)
  (:language TASK_DESCRIPTION)
  (:regions ...)
  (:fixtures ...)
  (:objects ...)
  (:obj_of_interest ...)
  (:init ...)
  (:goal ...)
)
```

---

## Line-by-Line Examples

### Example 1: er_object - Kitchen Pick-and-Place

**File:** `er_object/er_object_01.bddl`

```lisp
(define (problem LIBERO_Kitchen_Tabletop_Manipulation)      ; Line 1: Problem name determines environment class
  (:domain robosuite)                                        ; Line 2: Physics simulator domain
  (:language pick up the alphabet soup and place it in the basket)  ; Line 3: Natural language task description
```

**Regions Section** - Defines placement areas on surfaces:

```lisp
    (:regions
      (wooden_cabinet_init_region                            ; Region name
          (:target kitchen_table)                            ; Parent surface this region is on
          (:ranges (
              (-0.01 -0.31 0.01 -0.29)                        ; Bounding box: (x_min, y_min, x_max, y_max)
            )                                                 ; This is a 2cm x 2cm area
          )
          (:yaw_rotation (
              (3.141592653589793 3.141592653589793)          ; Rotation range in radians (min, max)
            )                                                 ; 3.14 = 180 degrees (fixed rotation)
          )
      )
      (contain_region                                         ; Predefined region (no ranges needed)
          (:target basket_1)                                  ; Uses basket's built-in containment zone
      )
      (alphabet_soup_init_region
          (:target kitchen_table)
          (:ranges (
              (-0.045 -0.075 0.045 0.015)                     ; 9cm x 9cm placement area
            )
          )
          (:yaw_rotation (
              (0.0 0.0)                                       ; No rotation (0 radians)
            )
          )
      )
    )
```

**Fixtures Section** - Static scene elements:

```lisp
  (:fixtures
    kitchen_table - kitchen_table                             ; instance_name - object_type
    wooden_cabinet_1 - wooden_cabinet                         ; The cabinet is a fixture (static)
  )
```

**Objects Section** - Manipulable items:

```lisp
  (:objects
    basket_1 - basket                                         ; Container object
    alphabet_soup_1 - alphabet_soup                           ; Target object to pick up
  )
```

**Objects of Interest** - Task-relevant objects for tracking:

```lisp
  (:obj_of_interest
    alphabet_soup_1                                           ; The object to manipulate
    basket_1                                                  ; The destination
  )
```

**Initial State** - Object placements at episode start:

```lisp
  (:init
    (On wooden_cabinet_1 kitchen_table_wooden_cabinet_init_region)  ; Cabinet on its region
    (On basket_1 kitchen_table_basket_init_region)                   ; Basket on its region
    (On alphabet_soup_1 kitchen_table_alphabet_soup_init_region)     ; Soup on its region
  )
```
> **Note:** Region names are formed as `{target}_{region_name}`, e.g., `kitchen_table` + `basket_init_region` = `kitchen_table_basket_init_region`

**Goal Condition** - Success criteria:

```lisp
  (:goal
    (And (In alphabet_soup_1 basket_1_contain_region))        ; Soup must be IN the basket's contain region
  )
```

---

### Example 2: er_sequential - Multi-Step Task

**File:** `er_sequential/er_seq_01.bddl`

```lisp
(define (problem LIBERO_Kitchen_Tabletop_Manipulation)
  (:domain robosuite)
  (:language put the bowl on the plate and then put the butter on the cabinet)  ; Multi-step task
```

**Goal with Multiple Conditions:**

```lisp
  (:goal
    (And (On akita_black_bowl_1 plate_1)                     ; First: bowl on plate
         (On butter_1 wooden_cabinet_1_top_region))          ; Then: butter on cabinet top
  )
```

---

### Example 3: er_spatial - Spatial Relationship Task

**File:** `er_spatial/er_spatial_01.bddl`

```lisp
(define (problem LIBERO_Tabletop_Manipulation)
  (:domain robosuite)
  (:language pick up the black bowl next to the butter and place it on the plate)  ; Spatial reference
```

**Multiple Regions for Spatial Layout:**

```lisp
    (:regions
      (plate_region
          (:target main_table)
          (:ranges (
              (0.0500 0.1900 0.0700 0.2100)                   ; Front-left area
            )
          )
      )
      (butter_init_region
          (:target main_table)
          (:ranges (
              (-0.0550 0.1150 0.0550 0.1850)                  ; Center-left area
            )
          )
      )
      (akita_black_bowl_init_region
          (:target main_table)
          (:ranges (
              (-0.1950 -0.0250 -0.0450 0.1250)                ; Back-center, next to butter
            )
          )
      )
```

**Initial State with Stacking:**

```lisp
  (:init
    (On akita_black_bowl_1 cookies_1)                        ; Bowl stacked ON cookies box
    (On akita_black_bowl_2 wooden_cabinet_1_top_side)        ; Distractor bowl on cabinet
    (On plate_1 main_table_plate_region)
    ...
  )
```

---

### Example 4: libero_object - Floor Manipulation

**File:** `libero_object/pick_up_the_butter_and_place_it_in_the_basket.bddl`

```lisp
(define (problem LIBERO_Floor_Manipulation)                  ; Floor-based task (no table)
  (:domain robosuite)
  (:language Pick the butter and place it in the basket)
```

**Floor as Target Surface:**

```lisp
    (:regions
      (bin_region
          (:target floor)                                     ; Objects placed on floor
          (:ranges (
              (-0.01 0.25 0.01 0.27)
            )
          )
      )
```

**Fixtures for Floor Scene:**

```lisp
  (:fixtures
    floor - floor                                             ; Floor is the only fixture
  )
```

---

### Example 5: libero_goal - Articulated Object Interaction

**File:** `libero_goal/open_the_top_drawer_and_put_the_bowl_inside.bddl`

```lisp
(define (problem LIBERO_Tabletop_Manipulation)
  (:domain robosuite)
  (:language Open the top layer of the drawer and put the bowl inside)
```

**Predefined Regions on Articulated Objects:**

```lisp
      (top_region                                             ; Drawer's top compartment
          (:target wooden_cabinet_1)                          ; No ranges - uses object's built-in region
      )
      (middle_region
          (:target wooden_cabinet_1)
      )
      (bottom_region
          (:target wooden_cabinet_1)
      )
```

**Goal with Container Placement:**

```lisp
  (:goal
    (And (In akita_black_bowl_1 wooden_cabinet_1_top_region)) ; Bowl inside drawer
  )
```

---

### Example 6: libero_10 - Long-Horizon Task with State Change

**File:** `libero_10/KITCHEN_SCENE3_turn_on_the_stove_and_put_the_moka_pot_on_it.bddl`

```lisp
(define (problem LIBERO_Kitchen_Tabletop_Manipulation)
  (:domain robosuite)
  (:language turn on the stove and put the moka pot on it)   ; Two-part task
```

**Predefined Cook Region:**

```lisp
      (cook_region
          (:target flat_stove_1)                              ; Stove's cooking surface
      )
```

**Goal with State Change Predicate:**

```lisp
  (:goal
    (And (Turnon flat_stove_1)                                ; State change: turn on stove
         (On moka_pot_1 flat_stove_1_cook_region))            ; Placement: pot on stove
  )
```

---

## Predicate Reference

### Placement Predicates

| Predicate | Usage | Description |
|-----------|-------|-------------|
| `On` | `(On obj1 region)` | Object is on top of a surface/region |
| `In` | `(In obj1 region)` | Object is inside a container region |

### State Predicates

| Predicate | Usage | Description |
|-----------|-------|-------------|
| `Turnon` | `(Turnon obj)` | Articulated object is turned on (e.g., stove) |
| `Turnoff` | `(Turnoff obj)` | Articulated object is turned off |
| `Open` | `(Open obj)` | Drawer/door is open |
| `Close` | `(Close obj)` | Drawer/door is closed |

---

## Range Format Details

The `:ranges` field defines a rectangular bounding box:

```
(:ranges (
    (x_min y_min x_max y_max)
))
```

**Example:**
```lisp
(:ranges (
    (-0.165 -0.005 0.165 0.305)    ; Width: 0.33m, Depth: 0.31m
))
```

- **X range:** -0.165 to 0.165 (33cm wide, centered)
- **Y range:** -0.005 to 0.305 (31cm deep, slightly left of center)

Objects are randomly sampled within this region at episode reset.

---

## Yaw Rotation Format

The `:yaw_rotation` field specifies rotation around the Z-axis (in radians):

```lisp
(:yaw_rotation (
    (min_angle max_angle)
))
```

| Value | Meaning |
|-------|---------|
| `(0.0 0.0)` | No rotation (0°) |
| `(3.14 3.14)` | Fixed 180° rotation |
| `(0.0 6.28)` | Random rotation 0° to 360° |
| `(2.66 2.72)` | Small random rotation around ~153° |

---

## Region Naming Convention

Full region names are constructed as: `{target_name}_{region_name}`

**Examples:**
- `kitchen_table` + `basket_init_region` → `kitchen_table_basket_init_region`
- `wooden_cabinet_1` + `top_region` → `wooden_cabinet_1_top_region`
- `basket_1` + `contain_region` → `basket_1_contain_region`

---

## Common Object Types

### Fixtures (Static)
- `kitchen_table`, `main_table`, `floor`
- `wooden_cabinet`, `wine_rack`
- `flat_stove`, `microwave`

### Manipulable Objects
- Foods: `alphabet_soup`, `butter`, `cream_cheese`, `ketchup`, `tomato_sauce`
- Containers: `basket`, `akita_black_bowl`, `plate`, `glazed_rim_porcelain_ramekin`
- Kitchenware: `moka_pot`, `chefmate_8_frypan`, `wine_bottle`

