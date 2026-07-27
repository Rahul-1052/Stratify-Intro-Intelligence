"""Run blind validation against lawful local real-world clips."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.beta.real_world_validation import RealWorldValidationRunner


def parser():
    value = argparse.ArgumentParser()
    value.add_argument("--manifest", default="validation/real_world/manifest.json")
    value.add_argument("--case", action="append", default=[])
    value.add_argument("--limit", type=int)
    value.add_argument(
        "--evaluate", action="store_true",
        help="Explicitly request evaluation (evaluation is always included).",
    )
    value.add_argument("--output-dir", default="validation/real_world/runs")
    value.add_argument(
        "--allow-network", action="store_true",
        help="Permit network-capable pipeline behavior; disabled by default.",
    )
    return value


def main(argv=None):
    args = parser().parse_args(argv)
    run, location = RealWorldValidationRunner().run(
        args.manifest, case_ids=args.case, limit=args.limit,
        output_dir=args.output_dir, allow_network=args.allow_network,
    )
    counts = {}
    for case in run["cases"]:
        counts[case["status"]] = counts.get(case["status"], 0) + 1
    print(f"Real-world validation run: {run['run_id']}")
    print(f"Results: {counts}")
    print(
        "Manual annotation coverage: "
        f"{run['coverage']['manual_annotation_coverage'] * 100:.1f}%"
    )
    print(f"Network access enabled: {run['network_access_enabled']}")
    print(f"Saved: {Path(location)}")
    return 0 if not counts.get("failed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
