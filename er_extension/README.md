# Libero-ER Benchmark Extension

This extension adds four new test suites to evaluate **compositional generalization** in robotic manipulation. Each suite tests a different dimension of generalization by composing elements from the training set (libero_90 + libero_object + libero_goal + libero_spatial) in novel ways.

## ER Dimensions

| Suite | Description | Example |
|-------|-------------|---------|
| **ER-OBJECT** | Novel object in familiar manipulation | Training: "put soup in basket" + scene with butter → Test: "put butter in basket" |
| **ER-GOAL** | Novel goal destination for familiar object | Training: "cheese on plate" + cabinet scene → Test: "cheese on cabinet" |
| **ER-SPATIAL** | Novel spatial landmark in familiar pattern | Training: "bowl next to ramekin" + cream cheese → Test: "bowl next to cream cheese" |
| **ER-SEQUENTIAL** | Novel temporal composition of actions | Training: "open drawer" + "bowl on plate" → Test: "open drawer and put bowl on plate" |

## Directory Structure

```
er_extension/
├── README.md                    # This file
├── bddl_combination_spec.md     # Detailed BDDL generation specifications
├── grouping_rules.md            # ER dimension definitions and rules
├── task_specs/                  # YAML task definitions
│   ├── er_object_tasks.yaml     # 20 ER-OBJECT task definitions
│   ├── er_goal_tasks.yaml       # 20 ER-GOAL task definitions
│   ├── er_spatial_tasks.yaml    # 20 ER-SPATIAL task definitions
│   └── er_sequential_tasks.yaml # 20 ER-SEQUENTIAL task definitions
├── scripts/                     # Generation and visualization scripts
│   ├── generate_er_object_bddl.py
│   ├── generate_er_goal_bddl.py
│   ├── generate_er_spatial_bddl.py
│   ├── generate_er_sequential_bddl.py
│   ├── validate_er_tasks.py
│   ├── render_er_tasks.py
│   └── create_visualization.py
├── rendered_images/             # Rendered task images
│   ├── er_object/
│   ├── er_goal/
│   ├── er_spatial/
│   └── er_sequential/
└── visualizations/              # Grid visualizations for review
    ├── er_object_grid.png
    ├── er_goal_grid.png
    ├── er_spatial_grid.png
    └── er_sequential_grid.png
```

## Generated BDDL Files

BDDL files are generated into the main libero directory:
```
libero/libero/bddl_files/
├── er_object/      # 20 BDDL files
├── er_goal/        # 20 BDDL files
├── er_spatial/     # 20 BDDL files
└── er_sequential/  # 20 BDDL files
```

## Pipeline Usage

### Prerequisites

```bash
cd /path/to/LIBERO
source .venv/bin/activate
```

### Step 1: Generate BDDL Files

Each ER group has its own generator script:

```bash
# Generate all ER-OBJECT tasks
python er_extension/scripts/generate_er_object_bddl.py

# Generate all ER-GOAL tasks
python er_extension/scripts/generate_er_goal_bddl.py

# Generate all ER-SPATIAL tasks
python er_extension/scripts/generate_er_spatial_bddl.py

# Generate all ER-SEQUENTIAL tasks
python er_extension/scripts/generate_er_sequential_bddl.py
```

### Step 2: Validate Generated Tasks

Validate that tasks are complete and novel:

```bash
python er_extension/scripts/validate_er_tasks.py \
    --er-dir libero/libero/bddl_files/er_object \
    --training-dirs libero/libero/bddl_files/libero_90 \
                    libero/libero/bddl_files/libero_object \
                    libero/libero/bddl_files/libero_goal \
                    libero/libero/bddl_files/libero_spatial
```

### Step 3: Render Task Images

Render initial and goal state images for visual verification:

```bash
# Render ER-OBJECT
python er_extension/scripts/render_er_tasks.py \
    --er-dir libero/libero/bddl_files/er_object \
    --output-dir er_extension/rendered_images/er_object

# Render ER-GOAL
python er_extension/scripts/render_er_tasks.py \
    --er-dir libero/libero/bddl_files/er_goal \
    --output-dir er_extension/rendered_images/er_goal

# Render ER-SPATIAL
python er_extension/scripts/render_er_tasks.py \
    --er-dir libero/libero/bddl_files/er_spatial \
    --output-dir er_extension/rendered_images/er_spatial

# Render ER-SEQUENTIAL
python er_extension/scripts/render_er_tasks.py \
    --er-dir libero/libero/bddl_files/er_sequential \
    --output-dir er_extension/rendered_images/er_sequential
```

### Step 4: Create Visualization Grids

Create overview grids for easy visual inspection:

```bash
# ER-OBJECT grid
python er_extension/scripts/create_visualization.py \
    --rendered-dir er_extension/rendered_images/er_object \
    --bddl-dir libero/libero/bddl_files/er_object \
    --output er_extension/visualizations/er_object_grid.png

# ER-GOAL grid
python er_extension/scripts/create_visualization.py \
    --rendered-dir er_extension/rendered_images/er_goal \
    --bddl-dir libero/libero/bddl_files/er_goal \
    --output er_extension/visualizations/er_goal_grid.png

# ER-SPATIAL grid
python er_extension/scripts/create_visualization.py \
    --rendered-dir er_extension/rendered_images/er_spatial \
    --bddl-dir libero/libero/bddl_files/er_spatial \
    --output er_extension/visualizations/er_spatial_grid.png

# ER-SEQUENTIAL grid
python er_extension/scripts/create_visualization.py \
    --rendered-dir er_extension/rendered_images/er_sequential \
    --bddl-dir libero/libero/bddl_files/er_sequential \
    --output er_extension/visualizations/er_sequential_grid.png
```

## Full Pipeline (All Groups)

Run all steps for all groups:

```bash
cd /path/to/LIBERO
source .venv/bin/activate

for group in object goal spatial sequential; do
    echo "=== Processing ER-${group^^} ==="
    
    # Generate
    python er_extension/scripts/generate_er_${group}_bddl.py
    
    # Render
    python er_extension/scripts/render_er_tasks.py \
        --er-dir libero/libero/bddl_files/er_${group} \
        --output-dir er_extension/rendered_images/er_${group}
    
    # Visualize
    python er_extension/scripts/create_visualization.py \
        --rendered-dir er_extension/rendered_images/er_${group} \
        --bddl-dir libero/libero/bddl_files/er_${group} \
        --output er_extension/visualizations/er_${group}_grid.png
done
```

## Task Counts

| Suite | Two-Source Tasks | Three-Source Tasks | Total |
|-------|------------------|-------------------|-------|
| ER-OBJECT | 10 | 10 | 20 |
| ER-GOAL | 10 | 10 | 20 |
| ER-SPATIAL | 10 | 10 | 20 |
| ER-SEQUENTIAL | 10 (2-step) | 10 (3-step) | 20 |
| **Total** | | | **80** |

## Adding New Tasks

1. Edit the corresponding YAML file in `task_specs/`
2. Run the generation script for that group
3. Render and visualize to verify

Example for adding a new ER-OBJECT task:

```yaml
# In task_specs/er_object_tasks.yaml
- id: er_object_21
  name: new_task_name
  language: "put the X in the Y"
  manipulation_source: libero_90/...
  scene_source: libero_90/...
  objects:
    - name: X
      type: x_type
  goal: "(On X_1 Y_1)"
```

## Notes

- Each task renders 3 random initial states + 3 goal states
- Visualization grids show init/goal pairs for each seed
- Object placement uses collision detection to avoid overlaps
- Problem names must match scene type (e.g., `LIBERO_Kitchen_Tabletop_Manipulation` for kitchen scenes)

