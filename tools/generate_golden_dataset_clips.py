"""Generate deterministic synthetic MP4s for the local golden dataset."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.beta.synthetic_clips import generate_golden_clips


def parser():
    value = argparse.ArgumentParser()
    value.add_argument(
        "--manifest", default="validation/golden_dataset/manifest.json"
    )
    value.add_argument("--clips-dir")
    value.add_argument("--force", action="store_true")
    return value


def main(argv=None):
    args = parser().parse_args(argv)
    outcome = generate_golden_clips(
        args.manifest, clips_dir=args.clips_dir, force=args.force
    )
    results = outcome["results"]
    generated = sum(item["status"] == "generated" for item in results.values())
    skipped = sum(item["status"] == "skipped" for item in results.values())
    validated = sum(item.get("valid") is True for item in results.values())
    failed = len(results) - validated
    print(f"Golden dataset clips generated: {generated}")
    print(f"Existing valid clips skipped: {skipped}")
    print(f"Manifest cases updated: {outcome['manifest_updated']}")
    print(f"Validated videos: {validated}")
    print(f"Failed: {failed}")
    print(f"Clips directory: {outcome['clips_dir']}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
