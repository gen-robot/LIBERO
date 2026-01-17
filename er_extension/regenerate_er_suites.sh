#!/bin/bash
# Regenerate all ER suites and visualize them
# Usage: ./regenerate_er_suites.sh [suite_name]
# Examples:
#   ./regenerate_er_suites.sh           # Regenerate all ER suites
#   ./regenerate_er_suites.sh er_goal   # Regenerate only er_goal

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Activate virtual environment
if [ -f "eval/.venv/bin/activate" ]; then
    source eval/.venv/bin/activate
else
    echo "Error: Virtual environment not found at eval/.venv"
    exit 1
fi

# Set environment
export PYTHONPATH="$PROJECT_ROOT:$PROJECT_ROOT/er_extension/scripts:$PYTHONPATH"
export MUJOCO_GL=egl

# Define suites to process
if [ -n "$1" ]; then
    SUITES=("$1")
else
    SUITES=("er_goal" "er_spatial" "er_sequential")
fi

echo "============================================================"
echo "ER Suite Regeneration Pipeline"
echo "Project root: $PROJECT_ROOT"
echo "Suites to process: ${SUITES[*]}"
echo "============================================================"

for suite in "${SUITES[@]}"; do
    echo ""
    echo "============================================================"
    echo "Processing: $suite"
    echo "============================================================"
    
    # Step 1: Regenerate BDDL files (only for ER suites)
    case "$suite" in
        er_object)
            echo "[1/4] Regenerating BDDL files..."
            python er_extension/scripts/generate_er_object_bddl.py
            ;;
        er_goal)
            echo "[1/4] Regenerating BDDL files..."
            python er_extension/scripts/generate_er_goal_bddl.py
            ;;
        er_spatial)
            echo "[1/4] Regenerating BDDL files..."
            python er_extension/scripts/generate_er_spatial_bddl.py
            ;;
        er_sequential)
            echo "[1/4] Regenerating BDDL files..."
            python er_extension/scripts/generate_er_sequential_bddl.py
            ;;
        *)
            echo "[1/4] Skipping BDDL regeneration for non-ER suite: $suite"
            ;;
    esac
    
    # Step 2: Generate goal BDDL files
    echo "[2/4] Generating goal BDDL files..."
    python scripts/generate_goal_bddl_files.py --suite "$suite"
    
    # Step 3: Generate goal init files
    echo "[3/4] Generating goal init files..."
    python scripts/generate_goal_init_files.py --suite "$suite" --num-states 5
    
    # Step 4: Visualize
    echo "[4/4] Generating visualization..."
    python scripts/visualize_libero_suites.py --suite "$suite"
    
    echo "Completed: $suite"
done

echo ""
echo "============================================================"
echo "All done!"
echo "Visualizations saved to: $PROJECT_ROOT/visualizations/"
echo "============================================================"
ls -la "$PROJECT_ROOT/visualizations/"*_grid.png 2>/dev/null || echo "No grid images found"

