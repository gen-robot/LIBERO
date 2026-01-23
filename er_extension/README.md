# Libero-ER Benchmark Extension

This extension adds four new test suites to evaluate **compositional generalization** in robotic manipulation. Each suite tests a different dimension of generalization by composing elements from the training set (libero_90 + libero_object + libero_goal + libero_spatial) in novel ways.

## ER Dimensions

| Suite | Description | Example |
|-------|-------------|---------|
| **ER-OBJECT** | Novel object in familiar manipulation | Training: "put soup in basket" + scene with butter → Test: "put butter in basket" |
| **ER-GOAL** | Novel goal destination for familiar object | Training: "cheese on plate" + cabinet scene → Test: "cheese on cabinet" |
| **ER-SPATIAL** | Novel spatial landmark in familiar pattern | Training: "bowl next to ramekin" + cream cheese → Test: "bowl next to cream cheese" |
| **ER-SEQUENTIAL** | Novel temporal composition of actions | Training: "open drawer" + "bowl on plate" → Test: "open drawer and put bowl on plate" |

## Pipeline Overview

The ER task generation pipeline has **4 stages**:

```
┌─────────────────────┐    ┌───────────────────┐    ┌──────────────────────────────────────────┐    ┌─────────────────────┐
│ 1. Task Spec YAML   │ -> │ 2. BDDL Generation │ -> │ 3. Goal Files Gen (optional to check)   │ -> │ 4. Visualization    │
│ (Human Design)      │    │ (Python Scripts)   │    │ (Sim State Saving)                      │    │ (Grid Images)       │
└─────────────────────┘    └───────────────────┘    └──────────────────────────────────────────┘    └─────────────────────┘
```

## Quick Start: Regenerate All Suites

Use the automation script to regenerate all ER suites:

```bash
cd /path/to/LIBERO-ER

# Regenerate all 4 ER suites (er_object, er_goal, er_spatial, er_sequential)
./er_extension/regenerate_er_suites.sh

# Regenerate only a specific suite
./er_extension/regenerate_er_suites.sh er_goal
```

This script runs all 4 pipeline stages automatically.

## Directory Structure

```
er_extension/
├── README.md                    # This file
├── regenerate_er_suites.sh      # Full pipeline automation script
├── bddl_combination_spec.md     # Detailed BDDL generation specifications
├── grouping_rules.md            # ER dimension definitions and rules
├── task_specs/                  # YAML task definitions (v3.0 format)
│   ├── er_object_tasks.yaml     # ER-OBJECT task definitions
│   ├── er_goal_tasks.yaml       # ER-GOAL task definitions
│   ├── er_spatial_tasks.yaml    # ER-SPATIAL task definitions
│   └── er_sequential_tasks.yaml # ER-SEQUENTIAL task definitions
├── scripts/                     # Generation and validation scripts
│   ├── er_constants.py          # Shared placement/collision parameters
│   ├── generate_er_object_bddl.py
│   ├── generate_er_goal_bddl.py
│   ├── generate_er_spatial_bddl.py
│   ├── generate_er_sequential_bddl.py
│   ├── validate_er_tasks.py
│   ├── render_er_tasks.py
│   ├── check_bddl_overlaps.py
│   └── create_visualization.py
└── visualizations/              # Grid visualizations for review
```

## Generated Files

BDDL files are generated into the main libero directory:
```
libero/libero/bddl_files/
├── er_object/      # BDDL files
├── er_goal/        # BDDL files
├── er_spatial/     # BDDL files
└── er_sequential/  # BDDL files

libero/libero/goal_bddl_files/
├── er_object/      # Goal BDDL files (objects at goal positions)
├── er_goal/
├── er_spatial/
├── er_sequential/
└── goal_files/     # Saved MuJoCo states for goal visualization
    ├── er_object/
    ├── er_goal/
    ├── er_spatial/
    └── er_sequential/
```

---

## Stage 1: Task Specification Design (YAML)

Task definitions use the **v3.0 YAML format** with explicit source specifications:

```yaml
version: "3.0"
group: ER-GOAL
task_count: 10  # Documentation only; actual count = number of task entries

tasks:
  - id: er_goal_01                                    # Unique task identifier
    instruction: "put the butter on the plate"        # Natural language instruction
    source_a:                                         # Primary source (manipulation/object)
      file: libero_object/pick_up_the_butter...bddl
      suite: libero_object
      take: [butter_1]                                # What to extract from this source
    source_b:                                         # Secondary source (scene/target)
      file: libero_90/KITCHEN_SCENE1_put_the...bddl
      suite: libero_90
      take: [plate_1, kitchen_table, scene_layout]
    source_c:                                         # Optional: distractors
      file: libero_90/STUDY_SCENE1_pick_up_the...bddl
      take: [black_book_1]
    goal: "(On butter_1 plate_1)"                     # Goal predicate
    novelty: "Butter on plate (never trained)"        # Documentation
```

### Controlling the Number of Tasks

**To add/remove tasks**: Edit the YAML file and add/remove task entries. The number of tasks equals the number of entries in the `tasks` list.

### Source Types

| Source | Purpose | Common `take` items |
|--------|---------|---------------------|
| `source_a` | Primary manipulation/object | `[butter_1, milk_1, ...]` |
| `source_b` | Scene context/target | `[kitchen_table, wooden_cabinet_1, scene_layout]` |
| `source_c` | Distractors (optional) | `[black_book_1, mug_1]` |

---

## Stage 2: BDDL Generation Scripts

Each ER suite has its own generation script with different merging logic:

| Suite | Script | Merging Logic |
|-------|--------|---------------|
| **er_object** | `generate_er_object_bddl.py` | Take manipulation from A, scene from B |
| **er_goal** | `generate_er_goal_bddl.py` | Take object from A, target destination from B |
| **er_spatial** | `generate_er_spatial_bddl.py` | Apply spatial offsets (left_of, between, etc.) |
| **er_sequential** | `generate_er_sequential_bddl.py` | Merge multi-step goals |

### CLI Arguments

```bash
python er_extension/scripts/generate_er_goal_bddl.py \
    --yaml-file er_extension/task_specs/er_goal_tasks.yaml \
    --bddl-base libero/libero/bddl_files \
    --output-dir libero/libero/bddl_files/er_goal \
    --task-id er_goal_01  # Optional: generate single task only
```

---

## Stage 3: Goal File Generation

Two sub-steps convert BDDL goals into renderable states:

```bash
# 3a. Create goal BDDL files (goal predicates -> init predicates)
python scripts/generate_goal_bddl_files.py --suite er_goal

# 3b. Run simulator to save MuJoCo states
python scripts/generate_goal_init_files.py --suite er_goal --num-states 5
```

---

## Stage 4: Visualization

```bash
python scripts/visualize_libero_suites.py --suite er_goal
```

Output: `visualizations/er_goal_grid.png`

---

## Tunable Parameters

### In `er_constants.py`

| Parameter | Default | Description |
|-----------|---------|-------------|
| `COLLISION_MARGIN` | 0.05m | Safety gap between objects |
| `COLLISION_SIZE_MULTIPLIER` | 1.5 | Object hitbox expansion factor |
| `PLACEMENT_TOLERANCE` | 0.005m | Random spawn variation (5mm) |

### Object Placement Positions

Priority-ordered spawn locations (front row has best visibility):

```python
OBJECT_PLACEMENT_POSITIONS = [
    # Front row - best visibility
    (0.0, 0.15), (-0.12, 0.15), (0.12, 0.15),
    # Mid-front row
    (0.0, 0.08), (-0.15, 0.08), (0.15, 0.08),
    # Center row
    (-0.08, 0.0), (0.08, 0.0), (0.0, 0.0),
    # ...
]
```

### Object Sizes (footprints)

```python
OBJECT_SIZES = {
    'butter': (0.10, 0.06),      # (width_x, depth_y) in meters
    'basket': (0.32, 0.3),
    'wooden_cabinet': (0.25, 0.22),
    # ...
}
```

### Spatial Offsets (for er_spatial)

```python
SPATIAL_OFFSETS = {
    'next_to': (-0.12, 0.0),
    'left_of': (-0.14, 0.0),
    'right_of': (0.14, 0.0),
    'in_front_of': (0.0, 0.12),
    'behind': (0.0, -0.12),
    'between': (0.0, 0.0),  # Special handling: midpoint of two landmarks
}
```

### Goal State Generation

| Parameter | Location | Default |
|-----------|----------|---------|
| `--num-states` | `generate_goal_init_files.py` | 50 (regenerate script uses 5) |

---

## Manual Pipeline Steps

### Step 1: Generate BDDL Files

```bash
python er_extension/scripts/generate_er_object_bddl.py
python er_extension/scripts/generate_er_goal_bddl.py
python er_extension/scripts/generate_er_spatial_bddl.py
python er_extension/scripts/generate_er_sequential_bddl.py
```

### Step 2: Validate Generated Tasks

```bash
python er_extension/scripts/validate_er_tasks.py \
    --er-dir libero/libero/bddl_files/er_object \
    --training-dirs libero/libero/bddl_files/libero_90 \
                    libero/libero/bddl_files/libero_object \
                    libero/libero/bddl_files/libero_goal \
                    libero/libero/bddl_files/libero_spatial
```

### Step 3: Generate Goal Files

```bash
python scripts/generate_goal_bddl_files.py --suite er_goal
python scripts/generate_goal_init_files.py --suite er_goal --num-states 5
```

### Step 4: Visualize

```bash
python scripts/visualize_libero_suites.py --suite er_goal
```

---

## Adding New Tasks

1. Edit the corresponding YAML file in `task_specs/`
2. Follow the v3.0 format:

```yaml
- id: er_goal_21
  instruction: "put the X on the Y"
  source_a:
    file: libero_object/pick_up_the_X...bddl
    suite: libero_object
    take: [X_1]
  source_b:
    file: libero_90/SCENE_with_Y.bddl
    suite: libero_90
    take: [Y_1, kitchen_table, scene_layout]
  goal: "(On X_1 Y_1)"
  novelty: "X on Y (never trained)"
```

3. Run the regeneration script:

```bash
./er_extension/regenerate_er_suites.sh er_goal
```

---

## Task Counts (at least 10 tasks per suite, perferred 20 tasks per suite)

| Suite | Two-Source Tasks | Three-Source Tasks | Total |
|-------|------------------|-------------------|-------|
| ER-OBJECT | 5 | 5 | 10 |
| ER-GOAL | 5 | 5 | 10 |
| ER-SPATIAL | 5 | 5 | 10 |
| ER-SEQUENTIAL | 5 (2-step) | 5 (3-step) | 10 |
| **Total** | | | **40** |

---

## Notes

- Visualization grids show init/goal pairs for verification
- Object placement uses collision detection to avoid overlaps
- Problem names auto-match scene type (e.g., `LIBERO_Kitchen_Tabletop_Manipulation`)
- Cabinet type mismatches (`wooden_cabinet` ↔ `white_cabinet`) are auto-fixed
