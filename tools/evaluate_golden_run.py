"""Evaluate Observation Accuracy V1 from a saved golden run without analysis."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.beta.observation_accuracy import (
    console_summary, evaluate_saved_run, latest_completed_run,
)


def parser():
    value = argparse.ArgumentParser()
    selection = value.add_mutually_exclusive_group(required=True)
    selection.add_argument("--run-id")
    selection.add_argument("--latest", action="store_true")
    value.add_argument("--runs-dir", default="validation/golden_dataset/runs")
    value.add_argument("--manifest", default="validation/golden_dataset/manifest.json")
    return value


def main(argv=None):
    args = parser().parse_args(argv)
    run_dir = (
        latest_completed_run(args.runs_dir)
        if args.latest else Path(args.runs_dir) / args.run_id
    )
    if run_dir is None or not (run_dir / "summary.json").is_file():
        raise SystemExit("No completed golden run was found.")
    summary, accuracy_path = evaluate_saved_run(run_dir, args.manifest)
    print(f"Golden dataset run: {summary.run_id}")
    print(console_summary(summary, accuracy_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
