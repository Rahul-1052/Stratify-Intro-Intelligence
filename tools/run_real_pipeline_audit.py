"""Discover safe cached clips and run a bounded no-network pipeline pilot."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2

from core.product_validation.evidence_audit import aggregate_evidence, audit_exports
from core.product_validation.runner import ProductValidationRunner
from core.product_validation.storage import ValidationStore


def inspect_clip(path):
    capture = cv2.VideoCapture(str(path))
    readable = capture.isOpened()
    frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0)
    duration = round(frames / fps, 3) if fps > 0 else 0
    capture.release()
    return {"path": path.as_posix(), "format": path.suffix.lower().lstrip("."),
            "duration_seconds": duration, "size_bytes": path.stat().st_size,
            "readable": readable and frames > 0, "provenance_known": False,
            "suitable_for_reproducible_validation": readable and frames > 0 and duration > 0}


def discover(root, limit):
    inspected = [inspect_clip(path) for path in sorted(Path(root).glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)]
    usable = [item for item in inspected if item["suitable_for_reproducible_validation"]]
    # Avoid obvious duplicate derivative names and exact duplicate sizes in this bounded pilot.
    selected, sizes = [], set()
    for item in usable:
        if item["size_bytes"] in sizes:
            continue
        selected.append(item)
        sizes.add(item["size_bytes"])
        if len(selected) >= limit:
            break
    return inspected, selected


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", default="temp_clips")
    parser.add_argument("--input", action="append", default=[],
                        help="Explicit local clip path; repeat for a reproducible cohort.")
    parser.add_argument("--output", default=".stratify_validation")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--case")
    parser.add_argument("--resume", nargs="?", const="latest")
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--no-network", action="store_true")
    parser.add_argument("--trace-export", action="store_true")
    args = parser.parse_args(argv)
    if args.input:
        inspected = [inspect_clip(Path(value)) for value in args.input]
        selected = [item for item in inspected if item["suitable_for_reproducible_validation"]][
            :max(0, min(args.limit, 5))
        ]
    else:
        inspected, selected = discover(args.input_dir, max(0, min(args.limit, 5)))
    entries = [{"case_id": f"local-{index + 1:02d}", "local_source": item["path"],
                "url": "", "creator": "", "title": "", "niche": "unknown",
                "source_type": "cached local intro clip", "validation_kind": "real-video pipeline validation"}
               for index, item in enumerate(selected)]
    if args.case:
        entries = [item for item in entries if item["case_id"] == args.case]
    store = ValidationStore(args.output)
    run_id = None
    if args.resume:
        runs = store.list_runs()
        run_id = runs[0]["run_id"] if args.resume == "latest" and runs else args.resume
    run = ProductValidationRunner(store).run(entries, run_id=run_id, mode="real-video pipeline validation",
        resume=bool(args.resume), skip_existing=args.skip_existing, no_network=True,
        environment_notes="Bounded cached-clip pilot; network disabled.")
    for case in run["cases"]:
        if case.get("pipeline_trace_reference"):
            case["pipeline_trace"] = json.loads((store.root / case["pipeline_trace_reference"]).read_text(encoding="utf-8"))
    store.save_run(run)
    aggregate = aggregate_evidence(run, store.load_report)
    export_dir = store.root / "exports" / run["run_id"]
    export_dir.mkdir(parents=True, exist_ok=True)
    (export_dir / "inputs_discovered.json").write_text(json.dumps({"inspected": inspected, "selected": selected}, indent=2), encoding="utf-8")
    for name, content in audit_exports(run, selected, aggregate).items():
        (export_dir / name).write_text(content, encoding="utf-8", newline="")
    print(json.dumps({"run_id": run["run_id"], "inspected": len(inspected), "attempted": len(entries),
                      "completed": sum(c["analysis_status"] == "completed" for c in run["cases"]),
                      "failed": sum(c["analysis_status"] == "failed" for c in run["cases"]),
                      "output": str(export_dir)}, indent=2))


if __name__ == "__main__":
    main()
