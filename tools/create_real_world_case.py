"""Create or lock a manually supplied real-world validation case."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.beta.real_world_validation import create_case, lock_expectations


def parser():
    value = argparse.ArgumentParser()
    value.add_argument("--manifest", default="validation/real_world/manifest.json")
    value.add_argument("--case-id")
    value.add_argument("--title")
    value.add_argument("--category")
    value.add_argument("--clip")
    value.add_argument("--source-type", default="local_file")
    value.add_argument("--notes", default="")
    value.add_argument(
        "--reference", action="store_true",
        help="Reference the original absolute clip path instead of copying it.",
    )
    value.add_argument(
        "--lock-case",
        help="Lock expectations already entered in the manifest for this case.",
    )
    value.add_argument("--annotator", default="")
    return value


def main(argv=None):
    args = parser().parse_args(argv)
    if args.lock_case:
        case = lock_expectations(args.manifest, args.lock_case, args.annotator)
        print(f"Locked expectations: {case['case_id']}")
        print(f"Hash: {case['expectations_hash']}")
        return 0
    missing = [
        name for name, current in (
            ("--case-id", args.case_id), ("--title", args.title),
            ("--category", args.category), ("--clip", args.clip),
        ) if not current
    ]
    if missing:
        parser().error(f"creation requires: {', '.join(missing)}")
    case = create_case(
        args.manifest, args.case_id, args.title, args.category, args.clip,
        copy_clip=not args.reference, source_type=args.source_type,
        notes=args.notes,
    )
    print(f"Created real-world case: {case['case_id']}")
    print(f"Clip: {case['clip_path']}")
    print("Next: add expectations to the manifest, then lock them with:")
    print(
        f"python tools/create_real_world_case.py --lock-case {case['case_id']} "
        f"--annotator \"YOUR NAME\""
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
