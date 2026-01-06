#!/usr/bin/env python3
"""
Validate ER task BDDL files:
1. Check all required BDDL components are present
2. Check task is not in training set (novel)
3. Check all referenced entities exist
"""

from __future__ import annotations
import argparse
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set, Tuple


@dataclass
class BDDLValidation:
    task_id: str
    has_language: bool = False
    has_regions: bool = False
    has_fixtures: bool = False
    has_objects: bool = False
    has_obj_of_interest: bool = False
    has_init: bool = False
    has_goal: bool = False
    is_novel: bool = True
    similar_training_tasks: List[str] = None
    missing_refs: List[str] = None
    errors: List[str] = None

    def __post_init__(self):
        if self.similar_training_tasks is None:
            self.similar_training_tasks = []
        if self.missing_refs is None:
            self.missing_refs = []
        if self.errors is None:
            self.errors = []

    @property
    def is_valid(self) -> bool:
        return (
            self.has_language and self.has_regions and self.has_fixtures and
            self.has_objects and self.has_obj_of_interest and self.has_init and
            self.has_goal and self.is_novel and not self.errors
        )


def extract_language(content: str) -> str:
    """Extract language instruction from BDDL content."""
    match = re.search(r'\(:language\s+(.+?)\)\s*\n', content)
    return match.group(1).strip().lower() if match else ""


def extract_goal(content: str) -> str:
    """Extract goal from BDDL content."""
    match = re.search(r'\(:goal\s*\n\s*(.*?)\s*\)\s*\)', content, re.DOTALL)
    return match.group(1).strip() if match else ""


def extract_objects(content: str) -> Set[str]:
    """Extract object instances from BDDL content."""
    objects = set()
    match = re.search(r'\(:objects\s*\n(.*?)\s*\)', content, re.DOTALL)
    if match:
        for line in match.group(1).strip().split('\n'):
            line = line.strip()
            if ' - ' in line:
                instances = line.split(' - ')[0].strip().split()
                objects.update(instances)
    return objects


def extract_fixtures(content: str) -> Set[str]:
    """Extract fixture instances from BDDL content."""
    fixtures = set()
    match = re.search(r'\(:fixtures\s*\n(.*?)\s*\)', content, re.DOTALL)
    if match:
        for line in match.group(1).strip().split('\n'):
            line = line.strip()
            if ' - ' in line:
                instances = line.split(' - ')[0].strip().split()
                fixtures.update(instances)
    return fixtures


def normalize_language(lang: str) -> str:
    """Normalize language for comparison."""
    lang = lang.lower().strip()
    lang = re.sub(r'\s+', ' ', lang)
    lang = re.sub(r'[^\w\s]', '', lang)
    return lang


def load_training_tasks(bddl_base: str) -> Dict[str, Tuple[str, str, Set[str]]]:
    """Load all training tasks (language, goal, objects) for novelty checking."""
    training_suites = ['libero_10', 'libero_90', 'libero_object', 'libero_goal', 'libero_spatial']
    tasks = {}

    for suite in training_suites:
        suite_dir = os.path.join(bddl_base, suite)
        if not os.path.exists(suite_dir):
            continue
        for bddl_file in Path(suite_dir).glob("*.bddl"):
            try:
                with open(bddl_file, 'r') as f:
                    content = f.read()
                language = extract_language(content)
                goal = extract_goal(content)
                objects = extract_objects(content)
                task_key = f"{suite}/{bddl_file.name}"
                tasks[task_key] = (normalize_language(language), goal, objects)
            except Exception:
                continue

    return tasks


def check_novelty(
    language: str,
    goal: str,
    objects: Set[str],
    training_tasks: Dict[str, Tuple[str, str, Set[str]]]
) -> Tuple[bool, List[str]]:
    """Check if a task is novel compared to training set."""
    normalized_lang = normalize_language(language)
    similar_tasks = []

    for task_key, (train_lang, train_goal, train_objects) in training_tasks.items():
        if normalized_lang == train_lang:
            similar_tasks.append(f"{task_key} (exact language match)")
            continue
        lang_similarity = len(set(normalized_lang.split()) & set(train_lang.split()))
        lang_total = max(len(normalized_lang.split()), len(train_lang.split()))
        if lang_total > 0 and lang_similarity / lang_total > 0.9:
            obj_overlap = len(objects & train_objects)
            if obj_overlap >= len(objects) - 1:
                similar_tasks.append(f"{task_key} (high similarity)")

    is_novel = len(similar_tasks) == 0
    return is_novel, similar_tasks


def validate_bddl_file(
    bddl_path: str,
    training_tasks: Dict[str, Tuple[str, str, Set[str]]]
) -> BDDLValidation:
    """Validate a single BDDL file."""
    task_id = Path(bddl_path).stem
    validation = BDDLValidation(task_id=task_id)

    try:
        with open(bddl_path, 'r') as f:
            content = f.read()
    except Exception as e:
        validation.errors.append(f"Failed to read file: {e}")
        return validation

    validation.has_language = bool(re.search(r'\(:language\s+.+?\)', content))
    validation.has_regions = bool(re.search(r'\(:regions', content))
    validation.has_fixtures = bool(re.search(r'\(:fixtures', content))
    validation.has_objects = bool(re.search(r'\(:objects', content))
    validation.has_obj_of_interest = bool(re.search(r'\(:obj_of_interest', content))
    validation.has_init = bool(re.search(r'\(:init', content))
    validation.has_goal = bool(re.search(r'\(:goal', content))

    language = extract_language(content)
    goal = extract_goal(content)
    objects = extract_objects(content)
    fixtures = extract_fixtures(content)

    all_entities = objects | fixtures
    region_targets = set(re.findall(r'\(:target\s+(\w+)\)', content))
    for target in region_targets:
        if target not in all_entities:
            validation.missing_refs.append(f"Region target '{target}' not in fixtures/objects")

    init_refs = set(re.findall(r'\(On\s+(\w+)\s+', content))
    for ref in init_refs:
        if ref not in all_entities:
            validation.missing_refs.append(f"Init reference '{ref}' not in objects/fixtures")

    goal_refs = set(re.findall(r'\((?:On|In)\s+(\w+)\s+', goal))
    for ref in goal_refs:
        if ref not in all_entities:
            validation.missing_refs.append(f"Goal reference '{ref}' not in objects")

    is_novel, similar = check_novelty(language, goal, objects, training_tasks)
    validation.is_novel = is_novel
    validation.similar_training_tasks = similar

    if validation.missing_refs:
        validation.errors.extend(validation.missing_refs)

    return validation


def main():
    parser = argparse.ArgumentParser(description="Validate ER task BDDL files")
    parser.add_argument(
        "--er-dir",
        type=str,
        default="libero/libero/bddl_files/er_object",
        help="Directory containing ER BDDL files to validate"
    )
    parser.add_argument(
        "--bddl-base",
        type=str,
        default="libero/libero/bddl_files",
        help="Base directory for training BDDL files"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    print("Loading training tasks...")
    training_tasks = load_training_tasks(args.bddl_base)
    print(f"Loaded {len(training_tasks)} training tasks")

    er_dir = Path(args.er_dir)
    if not er_dir.exists():
        print(f"Error: Directory not found: {er_dir}")
        return

    bddl_files = sorted(er_dir.glob("*.bddl"))
    if not bddl_files:
        print(f"No BDDL files found in {er_dir}")
        return

    print(f"\nValidating {len(bddl_files)} tasks in {er_dir.name}")
    print("=" * 70)

    valid_count = 0
    novel_count = 0
    results = []

    for bddl_file in bddl_files:
        validation = validate_bddl_file(str(bddl_file), training_tasks)
        results.append(validation)

        status = "VALID" if validation.is_valid else "INVALID"
        novel_status = "NOVEL" if validation.is_novel else "DUPLICATE"

        if validation.is_valid:
            valid_count += 1
        if validation.is_novel:
            novel_count += 1

        print(f"\n{validation.task_id}")
        print(f"  Status: {status} | Novelty: {novel_status}")

        if args.verbose or not validation.is_valid:
            print(f"  Components: L={validation.has_language} R={validation.has_regions} "
                  f"F={validation.has_fixtures} O={validation.has_objects} "
                  f"I={validation.has_obj_of_interest} N={validation.has_init} G={validation.has_goal}")

        if validation.errors:
            print(f"  Errors: {validation.errors[:3]}")

        if validation.similar_training_tasks:
            print(f"  Similar to: {validation.similar_training_tasks[:2]}")

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Total tasks:  {len(bddl_files)}")
    print(f"  Valid tasks:  {valid_count}/{len(bddl_files)}")
    print(f"  Novel tasks:  {novel_count}/{len(bddl_files)}")

    invalid_tasks = [r for r in results if not r.is_valid]
    if invalid_tasks:
        print(f"\nInvalid tasks ({len(invalid_tasks)}):")
        for r in invalid_tasks:
            print(f"  - {r.task_id}: {r.errors[:1] if r.errors else 'missing components'}")

    duplicate_tasks = [r for r in results if not r.is_novel]
    if duplicate_tasks:
        print(f"\nPotentially duplicate tasks ({len(duplicate_tasks)}):")
        for r in duplicate_tasks:
            print(f"  - {r.task_id}")


if __name__ == "__main__":
    main()

