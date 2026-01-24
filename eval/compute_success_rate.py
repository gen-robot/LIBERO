import argparse
from pathlib import Path


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
        "--max-list",
        type=int,
        default=200,
        help=(
            "Max files to print for success/failure lists (0 = no limit). "
            "Ignored when --quiet is set."
        ),
    )
    return parser.parse_args()


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

    success_files = [p for p in json_files if "success" in p.stem]
    failure_files = [p for p in json_files if "failure" in p.stem]

    num_success = len(success_files)
    num_failure = len(failure_files)
    used_total = num_success + num_failure

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

    if used_total == 0:
        print("\nNo files with 'success' or 'failure' in filename. Success rate undefined.")
        return

    success_rate = num_success / used_total
    print(
        f"\nSuccess (from filenames with 'success'/'failure'): "
        f"{num_success}/{used_total} ({success_rate * 100:.2f}%)"
    )


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        pass
