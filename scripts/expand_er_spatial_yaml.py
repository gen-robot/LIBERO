#!/usr/bin/env python3
"""
Expand ER-SPATIAL task YAML by enriching `take` lists for tasks 11–20 with
all object / fixture instances declared in the underlying BDDL files.

Usage:
  python scripts/expand_er_spatial_yaml.py \
      --yaml er_extension/task_specs/er_spatial_tasks.yaml \
      --output er_extension/task_specs/er_spatial_tasks_expanded.yaml

Only tasks with ids `er_spatial_11`–`er_spatial_20` are modified.
"""

import argparse
import os
import re
from typing import Dict, List, Set

import yaml


SUITE_DIRS = {
    "libero_90": "libero/libero/bddl_files/libero_90",
    "libero_10": "libero/libero/bddl_files/libero_10",
    "libero_goal": "libero/libero/bddl_files/libero_goal",
    "libero_object": "libero/libero/bddl_files/libero_object",
    "libero_spatial": "libero/libero/bddl_files/libero_spatial",
}


def _read_file(path: str) -> str:
    with open(path, "r") as f:
        return f.read()


def _parse_instances_block(block: str) -> Dict[str, str]:
    """
    Parse a (:objects ...) or (:fixtures ...) block into a mapping
    instance -> type. The block is the inner text between parentheses.
    """
    inst_to_type: Dict[str, str] = {}
    for line in block.strip().splitlines():
        line = line.strip()
        if not line or line.startswith(";"):
            continue
        if " - " not in line:
            continue
        left, right = line.split(" - ", 1)
        otype = right.strip().strip(")")
        # Left side can contain multiple instances separated by spaces.
        for inst in left.strip().split():
            # Strip any trailing ')' from instance names due to formatting.
            inst = inst.strip(")")
            if not inst:
                continue
            inst_to_type[inst] = otype
    return inst_to_type


def _parse_bddl_instances(bddl_path: str) -> Dict[str, Set[str]]:
    """
    Return all object and fixture instances from a BDDL file.

    Keys:
      "objects": set of object instance names
      "fixtures": set of fixture instance names
    """
    content = _read_file(bddl_path)

    objects: Set[str] = set()
    fixtures: Set[str] = set()

    # Objects block
    m_obj = re.search(r"\(:objects(.*?)\)\s*\n", content, re.DOTALL)
    if m_obj:
        block = m_obj.group(1)
        inst_map = _parse_instances_block(block)
        objects.update(inst_map.keys())

    # Fixtures block
    m_fix = re.search(r"\(:fixtures(.*?)\)\s*\n", content, re.DOTALL)
    if m_fix:
        block = m_fix.group(1)
        inst_map = _parse_instances_block(block)
        fixtures.update(inst_map.keys())

    return {"objects": objects, "fixtures": fixtures}


def _suite_file_path(suite: str, rel_file: str) -> str:
    if suite not in SUITE_DIRS:
        raise ValueError(f"Unknown suite '{suite}'")
    return os.path.join(SUITE_DIRS[suite], rel_file)


def expand_er_spatial_yaml(input_yaml: str, output_yaml: str) -> None:
    with open(input_yaml, "r") as f:
        config = yaml.safe_load(f)

    tasks: List[Dict] = config.get("tasks", [])

    # Only expand tasks 11–20 (ids er_spatial_11 .. er_spatial_20).
    target_ids = {f"er_spatial_{i:02d}" for i in range(11, 21)}

    for task in tasks:
        tid = task.get("id")
        if tid not in target_ids:
            continue

        for key in ("source_a", "source_b", "source_c"):
            src = task.get(key)
            if not src:
                continue
            suite = src.get("suite")
            rel_file = src.get("file")
            if not suite or not rel_file:
                continue
            try:
                bddl_path = _suite_file_path(suite, rel_file)
            except ValueError:
                # Unknown suite; skip.
                continue
            if not os.path.exists(bddl_path):
                # Missing BDDL file; skip.
                continue

            instances = _parse_bddl_instances(bddl_path)
            # Always include all objects; optionally include fixtures except
            # for tables / floors, which are environment supports not distractors.
            objects = instances["objects"]
            fixtures = {
                fx
                for fx in instances["fixtures"]
                if not any(k in fx.lower() for k in ["table", "floor"])
            }

            original_take = src.get("take", [])
            merged: List[str] = []
            seen: Set[str] = set()

            # Preserve original entries' ordering.
            for name in original_take:
                if isinstance(name, str) and name not in seen:
                    merged.append(name)
                    seen.add(name)

            # Then add all discovered object / fixture instances.
            for name in sorted(objects | fixtures):
                if name not in seen:
                    merged.append(name)
                    seen.add(name)

            src["take"] = merged

    with open(output_yaml, "w") as f:
        yaml.safe_dump(config, f, sort_keys=False)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Expand ER-SPATIAL YAML by enriching `take` lists for tasks 11–20."
    )
    parser.add_argument(
        "--yaml",
        type=str,
        required=True,
        help="Path to er_spatial_tasks.yaml",
    )
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="Output path for expanded YAML",
    )
    args = parser.parse_args()

    expand_er_spatial_yaml(args.yaml, args.output)
    print(f"Expanded YAML written to: {args.output}")


if __name__ == "__main__":
    main()

