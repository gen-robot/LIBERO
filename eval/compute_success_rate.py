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

    print("\nSuccess files:")
    for p in success_files:
        print(f"  {p.name}")

    print("\nFailure files:")
    for p in failure_files:
        print(f"  {p.name}")

    if used_total == 0:
        print("\nNo files with 'success' or 'failure' in filename. Success rate undefined.")
        return

    success_rate = num_success / used_total
    print(
        f"\nSuccess (from filenames with 'success'/'failure'): "
        f"{num_success}/{used_total} ({success_rate * 100:.2f}%)"
    )


if __name__ == "__main__":
    main()
