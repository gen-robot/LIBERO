import argparse
import json
import re
from pathlib import Path
from typing import Any, Optional


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compute success rate from JSON files in a directory, "
            "based on 'success' / 'failure' in filenames."
        )
    )
    parser.add_argument(
        "--input-dir",
        "-i",
        type=str,
        required=True,
        help="Directory containing JSON result files.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Do not print per-file success/failure lists (faster in terminals).",
    )
    parser.add_argument(
        "--output-json",
        type=str,
        default="success_rate_summary.json",
        help="Output JSON filename to write inside --input-dir.",
    )
    parser.add_argument(
        "--max-list",
        type=int,
        default=200,
        help=(
            "Max files to print for success/failure lists (0 = no limit). "
            "Ignored when --quiet is set."
        ),
    )
    return parser.parse_args()


_TASK_RE = re.compile(r"^task\d+$", flags=re.IGNORECASE)
_EP_RE = re.compile(r"^ep\d+$", flags=re.IGNORECASE)


def _parse_episode_filename(stem: str) -> dict[str, Any]:
    """
    Parse filename stem like:
      task00_ep07_pick_up_the_black_bowl_..._failure
    Returns:
      - result: "success" | "failure" | None
      - task: "task00" | None
      - episode: int | None
      - task_desc: str | None
    """
    parts = [p for p in str(stem).split("_") if p]
    if not parts:
        return {"result": None, "task": None, "episode": None, "task_desc": None}

    result: Optional[str] = None
    last = parts[-1].lower()
    if last in {"success", "failure"}:
        result = last
    else:
        lower_stem = str(stem).lower()
        if "success" in lower_stem:
            result = "success"
        elif "failure" in lower_stem:
            result = "failure"

    task: Optional[str] = None
    if _TASK_RE.match(parts[0]):
        task = parts[0].lower()

    episode: Optional[int] = None
    if len(parts) >= 2 and _EP_RE.match(parts[1]):
        try:
            episode = int(parts[1][2:])
        except ValueError:
            episode = None

    task_desc: Optional[str] = None
    if result is not None:
        if task is not None and episode is not None:
            if len(parts) >= 4:
                task_desc = "_".join(parts[2:-1]) or None
        elif task is not None:
            if len(parts) >= 3:
                task_desc = "_".join(parts[1:-1]) or None

    return {"result": result, "task": task, "episode": episode, "task_desc": task_desc}


def main() -> None:
    args = parse_args()
    input_dir = Path(args.input_dir)

    if not input_dir.exists() or not input_dir.is_dir():
        raise ValueError(f"Input dir does not exist or is not a directory: {input_dir}")

    # Collect all json files under input_dir (non-recursive).
    json_files = sorted(p for p in input_dir.glob("*.json") if p.is_file())

    total_json = len(json_files)
    print(f"Input dir: {input_dir}")
    print(f"Total JSON files: {total_json}")

    if total_json == 0:
        return

    parsed = [(p, _parse_episode_filename(p.stem)) for p in json_files]
    used = [(p, info) for p, info in parsed if info.get("result") in {"success", "failure"}]
    ignored_files = [p for p, info in parsed if info.get("result") not in {"success", "failure"}]

    success_files = [p for p, info in used if info.get("result") == "success"]
    failure_files = [p for p, info in used if info.get("result") == "failure"]

    num_success = len(success_files)
    num_failure = len(failure_files)
    used_total = num_success + num_failure

    per_task: dict[str, dict[str, Any]] = {}
    unknown_task_files: list[Path] = []
    for p, info in used:
        task = info.get("task")
        if not task:
            unknown_task_files.append(p)
            continue
        if task not in per_task:
            per_task[task] = {
                "task": task,
                "task_desc": info.get("task_desc"),
                "success": 0,
                "failure": 0,
                "total": 0,
            }
        if per_task[task].get("task_desc") is None and info.get("task_desc"):
            per_task[task]["task_desc"] = info.get("task_desc")
        per_task[task][info["result"]] += 1
        per_task[task]["total"] += 1

    if not args.quiet:
        max_list = args.max_list

        def _print_list(title: str, files: list[Path]) -> None:
            print(f"\n{title}:")
            if max_list == 0 or len(files) <= max_list:
                for p in files:
                    print(f"  {p.name}")
                return
            for p in files[:max_list]:
                print(f"  {p.name}")
            print(f"  ... ({len(files) - max_list} more)")

        _print_list("Success files", success_files)
        _print_list("Failure files", failure_files)
        if ignored_files:
            _print_list("Ignored files (no success/failure)", ignored_files)
        if unknown_task_files:
            _print_list("Used files with unknown task prefix", unknown_task_files)

    if used_total == 0:
        print("\nNo files with 'success' or 'failure' in filename. Success rate undefined.")
        return

    success_rate = num_success / used_total
    print(
        f"\nSuccess (from filenames with 'success'/'failure'): "
        f"{num_success}/{used_total} ({success_rate * 100:.2f}%)"
    )

    def _task_sort_key(task: str) -> tuple[int, str]:
        m = re.match(r"^task(\d+)$", task, flags=re.IGNORECASE)
        if not m:
            return (10**9, task)
        return (int(m.group(1)), task)

    for task_stats in per_task.values():
        s = int(task_stats.get("success", 0))
        t = int(task_stats.get("total", 0))
        task_stats["success_rate"] = (float(s) / float(t)) if t > 0 else None

    per_task_list = [per_task[k] for k in sorted(per_task.keys(), key=_task_sort_key)]

    if not args.quiet and per_task_list:
        print("\nPer-task success rates:")
        for t in per_task_list:
            s = int(t["success"])
            tot = int(t["total"])
            rate = t["success_rate"]
            desc = t.get("task_desc")
            desc_str = f" ({desc})" if desc else ""
            print(f"  {t['task']}: {s}/{tot} ({(rate or 0.0) * 100:.2f}%){desc_str}")

    out_payload = {
        "input_dir": str(input_dir),
        "total_json_files": total_json,
        "used_total": used_total,
        "ignored_total": len(ignored_files),
        "unknown_task_used_total": len(unknown_task_files),
        "overall": {
            "success": num_success,
            "failure": num_failure,
            "total": used_total,
            "success_rate": success_rate,
        },
        "per_task": per_task_list,
    }

    out_path = input_dir / str(args.output_json)
    try:
        out_path.write_text(json.dumps(out_payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nWrote JSON summary: {out_path}")
    except PermissionError:
        fallback = Path.cwd() / str(args.output_json)
        fallback.write_text(json.dumps(out_payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nCannot write to input dir; wrote JSON summary to: {fallback}")


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        pass
