#!/usr/bin/env python3
"""
Generate goal BDDL files for LIBERO suites.

For each task, creates a modified BDDL file where goal predicates become init predicates.
This allows rendering goal states by initializing the environment with the goal BDDL.

Usage:
    python scripts/generate_goal_bddl_files.py --suite libero_10
    python scripts/generate_goal_bddl_files.py --suite all
"""

from __future__ import annotations
import argparse
import os
import re
from pathlib import Path
from typing import List, Tuple

SCRIPT_DIR = Path(__file__).parent
LIBERO_ROOT = SCRIPT_DIR.parent / "libero" / "libero"
BDDL_DIR = LIBERO_ROOT / "bddl_files"
GOAL_BDDL_DIR = LIBERO_ROOT / "goal_bddl_files"

LIBERO_SUITES = ["libero_10", "libero_90", "libero_spatial", "libero_object", "libero_goal"]
ER_SUITES = ["er_object", "er_goal", "er_spatial", "er_sequential"]
SUITES = LIBERO_SUITES + ER_SUITES


def extract_goal_section(bddl_content: str) -> str:
    """Extract the goal section from BDDL content using balanced parens."""
    goal_start = bddl_content.find('(:goal')
    if goal_start == -1:
        return ""
    
    # Find matching closing paren
    depth = 0
    for i in range(goal_start, len(bddl_content)):
        if bddl_content[i] == '(':
            depth += 1
        elif bddl_content[i] == ')':
            depth -= 1
            if depth == 0:
                return bddl_content[goal_start:i+1]
    
    return ""


def parse_goal_predicates(bddl_content: str) -> List[Tuple[str, List[str]]]:
    """Parse goal predicates from BDDL content."""
    predicates = []
    
    goal_section = extract_goal_section(bddl_content)
    if not goal_section:
        return predicates
    
    # Parse all predicates: (PredicateName arg1 arg2 ...)
    # Find all predicates that are NOT 'And'
    pred_pattern = r'\((\w+)\s+([^()]+)\)'
    for match in re.finditer(pred_pattern, goal_section):
        pred_name = match.group(1)
        if pred_name == 'And':
            continue
        args = match.group(2).strip().split()
        predicates.append((pred_name, args))
    
    return predicates


def parse_init_predicates(bddl_content: str) -> List[str]:
    """Parse init predicates from BDDL content."""
    init_start = bddl_content.find('(:init')
    if init_start == -1:
        return []
    
    # Find matching closing paren
    depth = 0
    init_end = init_start
    for i in range(init_start, len(bddl_content)):
        if bddl_content[i] == '(':
            depth += 1
        elif bddl_content[i] == ')':
            depth -= 1
            if depth == 0:
                init_end = i + 1
                break
    
    init_section = bddl_content[init_start:init_end]
    
    # Parse individual predicates
    predicates = []
    pred_pattern = r'\((\w+)\s+[^()]+\)'
    for match in re.finditer(pred_pattern, init_section):
        predicates.append(match.group(0))
    
    return predicates


def convert_goal_predicate_to_init(pred_name: str, args: List[str]) -> str:
    """Convert a goal predicate to an init statement.
    
    Note: (In obj container) goals become (On obj container) for init,
    since LIBERO uses (On ...) for all object placements in init section.
    LIBERO predicates: Turnon, Turnoff, Open, Close (not Turnedon/Closed)
    """
    if pred_name == 'On':
        return f"(On {args[0]} {args[1]})"
    elif pred_name == 'In':
        return f"(On {args[0]} {args[1]})"
    elif pred_name == 'Open':
        return f"(Open {args[0]})"
    elif pred_name == 'Close':
        return f"(Close {args[0]})"
    elif pred_name == 'Turnon':
        return f"(Turnon {args[0]})"
    elif pred_name == 'Turnoff':
        return f"(Turnoff {args[0]})"
    return ""


def create_goal_bddl(original_bddl_path: str, output_path: str) -> bool:
    """Create a goal BDDL file where goal predicates become init predicates."""
    with open(original_bddl_path, 'r') as f:
        content = f.read()
    
    # Parse goal predicates
    goal_predicates = parse_goal_predicates(content)
    
    if not goal_predicates:
        # No changes needed, just copy
        with open(output_path, 'w') as f:
            f.write(content)
        return True
    
    # Parse existing init predicates
    existing_init = parse_init_predicates(content)
    
    if not existing_init:
        with open(output_path, 'w') as f:
            f.write(content)
        return True
    
    # Track objects that will be moved to goal positions
    goal_placement_objects = set()
    # Track state predicates (Open/Close, Turnon/Turnoff) that conflict
    goal_state_subjects = {}
    for pred_name, args in goal_predicates:
        if pred_name in ('On', 'In') and args:
            goal_placement_objects.add(args[0])
        elif pred_name in ('Open', 'Close') and args:
            goal_state_subjects[args[0]] = 'door_state'
        elif pred_name in ('Turnon', 'Turnoff') and args:
            goal_state_subjects[args[0]] = 'power_state'
    
    # Build new init - remove old placements for goal objects, add goal placements
    new_init_predicates = []
    
    for pred in existing_init:
        skip = False
        # Skip placements for objects that will be placed at goal
        for obj in goal_placement_objects:
            if f' {obj} ' in pred or pred.endswith(f' {obj})'):
                if '(On ' in pred or '(In ' in pred:
                    skip = True
                    break
        # Skip conflicting state predicates
        if not skip:
            for subj, state_type in goal_state_subjects.items():
                if subj in pred:
                    if state_type == 'door_state' and ('(Open ' in pred or '(Close ' in pred):
                        skip = True
                        break
                    if state_type == 'power_state' and ('(Turnon ' in pred or '(Turnoff ' in pred):
                        skip = True
                        break
        if not skip:
            new_init_predicates.append(pred)
    
    # Add ALL goal predicates as init
    for pred_name, args in goal_predicates:
        init_stmt = convert_goal_predicate_to_init(pred_name, args)
        if init_stmt and init_stmt not in new_init_predicates:
            new_init_predicates.append(init_stmt)
    
    # Build new init section string
    new_init_section = "  (:init\n"
    for pred in new_init_predicates:
        new_init_section += f"    {pred}\n"
    new_init_section += "  )"
    
    # Find and replace the init section
    init_start = content.find('(:init')
    if init_start == -1:
        with open(output_path, 'w') as f:
            f.write(content)
        return True
    
    # Find matching closing parenthesis for (:init ...)
    depth = 0
    init_end = init_start
    for i in range(init_start, len(content)):
        if content[i] == '(':
            depth += 1
        elif content[i] == ')':
            depth -= 1
            if depth == 0:
                init_end = i + 1
                break
    
    # Replace the init section
    new_content = content[:init_start] + new_init_section + content[init_end:]
    
    # Write output
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(new_content)
    
    return True


def generate_suite_goal_bddls(suite_name: str) -> int:
    """Generate goal BDDL files for a suite."""
    suite_bddl_dir = BDDL_DIR / suite_name
    suite_goal_dir = GOAL_BDDL_DIR / suite_name
    suite_goal_dir.mkdir(parents=True, exist_ok=True)
    
    bddl_files = sorted(suite_bddl_dir.glob("*.bddl"))
    
    print(f"\nGenerating goal BDDLs for {suite_name}: {len(bddl_files)} tasks")
    
    success_count = 0
    for bddl_file in bddl_files:
        output_path = suite_goal_dir / bddl_file.name
        
        if create_goal_bddl(str(bddl_file), str(output_path)):
            success_count += 1
        else:
            print(f"  [WARN] Failed to process: {bddl_file.name}")
    
    print(f"  Created {success_count}/{len(bddl_files)} goal BDDL files")
    return success_count


def main():
    parser = argparse.ArgumentParser(description="Generate goal BDDL files for LIBERO suites")
    parser.add_argument(
        "--suite",
        type=str,
        default="libero_10",
        choices=SUITES + ["all"],
        help="Suite to process (or 'all')"
    )
    args = parser.parse_args()
    
    GOAL_BDDL_DIR.mkdir(parents=True, exist_ok=True)
    
    if args.suite == "all":
        suites = SUITES
    else:
        suites = [args.suite]
    
    total = 0
    for suite in suites:
        total += generate_suite_goal_bddls(suite)
    
    print(f"\nDone! Generated {total} goal BDDL files in {GOAL_BDDL_DIR}")


if __name__ == "__main__":
    main()
