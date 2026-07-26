"""Run bounded product validation without changing production behavior."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.product_validation.exports import export_bundle
from core.product_validation.fixtures import fixture_cases
from core.product_validation.runner import ProductValidationRunner, load_manifest
from core.product_validation.storage import ValidationStore


def parser():
    value = argparse.ArgumentParser()
    value.add_argument("--manifest", default="validation/video_manifest.example.json")
    value.add_argument("--limit", type=int)
    value.add_argument("--output", default=".stratify_validation")
    value.add_argument("--resume", nargs="?", const="latest")
    value.add_argument("--fixture-only", action="store_true")
    value.add_argument("--real-only", action="store_true")
    value.add_argument("--skip-existing", action="store_true")
    value.add_argument("--builder-diagnostics", action="store_true")
    value.add_argument("--no-network", action="store_true")
    value.add_argument("--case")
    return value


def main(argv=None):
    args = parser().parse_args(argv)
    if args.fixture_only and args.real_only:
        raise SystemExit("--fixture-only and --real-only cannot be combined.")
    entries = fixture_cases() if args.fixture_only else load_manifest(args.manifest)
    if args.case:
        entries = [entry for entry in entries if entry["case_id"] == args.case]
    if args.limit is not None:
        entries = entries[:max(args.limit, 0)]
    store = ValidationStore(args.output)
    run_id = None
    if args.resume:
        runs = store.list_runs()
        run_id = runs[0]["run_id"] if args.resume == "latest" and runs else args.resume
    run = ProductValidationRunner(store).run(entries, run_id=run_id,
        mode="fixture UI validation" if args.fixture_only else "real-video pipeline validation",
        resume=bool(args.resume), skip_existing=args.skip_existing, no_network=args.no_network,
        environment_notes="Builder diagnostics requested." if args.builder_diagnostics else "")
    export_dir = store.root / "exports" / run["run_id"]
    export_dir.mkdir(parents=True, exist_ok=True)
    for name, content in export_bundle(run).items():
        (export_dir / name).write_text(content, encoding="utf-8", newline="")
    print(json.dumps({"run_id": run["run_id"], "cases": len(run["cases"]), "mode": run["validation_mode"],
                      "output": str(store.root)}, indent=2))


if __name__ == "__main__":
    main()
