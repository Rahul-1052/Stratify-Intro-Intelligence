"""Run the local private-beta golden dataset."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.beta.golden import GoldenDatasetRunner, load_golden_manifest


def parser():
    value = argparse.ArgumentParser()
    value.add_argument("--manifest", default="validation/golden_dataset/manifest.json")
    value.add_argument("--case", action="append", default=[])
    value.add_argument("--category", action="append", default=[])
    value.add_argument("--style", action="append", default=[])
    value.add_argument("--limit", type=int)
    value.add_argument("--compare-run")
    value.add_argument("--output-dir", default="validation/golden_dataset/runs")
    value.add_argument("--no-network", action="store_true")
    value.add_argument("--evaluate", action="store_true")
    return value


def main(argv=None):
    args = parser().parse_args(argv)
    manifest = load_golden_manifest(args.manifest)
    cases = [
        item for item in manifest["cases"] if item.get("enabled", True)
        and (not args.case or item["case_id"] in args.case)
        and (not args.category or item["content_category"] in args.category)
        and (not args.style or item["creator_style"] in args.style)
    ]
    if args.limit is not None:
        cases = cases[:max(args.limit, 0)]
    run, location = GoldenDatasetRunner().run(
        cases, args.output_dir, no_network=args.no_network,
        compare_run=args.compare_run,
    )
    counts = {}
    for case in run["cases"]:
        counts[case["status"]] = counts.get(case["status"], 0) + 1
    print(f"Golden dataset run: {run['run_id']}")
    print(f"Cases selected: {len(cases)}")
    print(f"Results: {counts}")
    print(f"Saved: {Path(location)}")
    if args.evaluate:
        from core.beta.observation_accuracy import (
            console_summary, evaluate_saved_run,
        )
        accuracy, accuracy_path = evaluate_saved_run(location, args.manifest)
        print()
        print(console_summary(accuracy, accuracy_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
