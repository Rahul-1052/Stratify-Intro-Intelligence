"""Lightweight repository scanner for brittle production hardcoding.

The scanner reports evidence; it does not reject controlled vocabulary,
documented thresholds, URL construction, or reusable language templates.
"""

import argparse
import ast
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path


PRODUCTION_ROOTS = ("core", "ui", "stratify_platform")
ROOT_FILES = ("app.py", "config.py", "version.py")
KNOWN_TEST_VIDEO_TERMS = (
    "catch me if you can", "impersonating a pilot", "lucy calls professor norman",
    "lucy: phone call", "professor norman",
)
KNOWN_CREATOR_TERMS = ("mrbeast", "pewdiepie", "markiplier", "casey neistat")
NAMED_MEDIA_TERMS = (
    "breaking bad", "blacklist", "spider-man", "ghostbusters", "karate kid",
    "the boys", "valorant", "fortnite",
)
FIXED_YOUTUBE_ID = re.compile(r"https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[A-Za-z0-9_-]{6,}", re.I)
TEST_IMPORT = re.compile(r"(?:from|import)\s+tests(?:\.|\s|$)")


@dataclass
class AuditFinding:
    file: str
    line: int
    rule: str
    classification: str
    risk: str
    excerpt: str


def production_files(root):
    root = Path(root)
    files = []
    for relative in PRODUCTION_ROOTS:
        path = root / relative
        if path.exists():
            files.extend(path.rglob("*.py"))
    files.extend(root / name for name in ROOT_FILES if (root / name).exists())
    return sorted(set(files))


def _add_matches(findings, path, text, terms, rule, classification, risk):
    for line_number, source_line in enumerate(text.splitlines(), 1):
        lowered = source_line.lower()
        if any(re.search(r"(?<![\w-])" + re.escape(term) + r"(?![\w-])", lowered) for term in terms):
            findings.append(AuditFinding(str(path), line_number, rule, classification, risk, source_line.strip()[:240]))


def scan_repository(root):
    root = Path(root).resolve()
    findings = []
    inspected = production_files(root)
    for path in inspected:
        text = path.read_text(encoding="utf-8", errors="replace")
        relative = path.relative_to(root)
        _add_matches(findings, relative, text, KNOWN_TEST_VIDEO_TERMS, "known_test_video", "F", "high")
        _add_matches(findings, relative, text, KNOWN_CREATOR_TERMS, "named_creator_special_case", "F", "high")
        _add_matches(findings, relative, text, NAMED_MEDIA_TERMS, "named_media_or_category_rule", "F", "high")
        for match in FIXED_YOUTUBE_ID.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            findings.append(AuditFinding(str(relative), line, "fixed_youtube_url", "F", "high", match.group(0)))
        for match in TEST_IMPORT.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            findings.append(AuditFinding(str(relative), line, "production_imports_tests", "F", "high", text.splitlines()[line - 1].strip()))
        try:
            tree = ast.parse(text)
        except SyntaxError:
            findings.append(AuditFinding(str(relative), 1, "syntax_error", "F", "high", "File could not be parsed."))
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and any(isinstance(value, ast.Constant) and isinstance(value.value, (int, float)) for value in [node.left, *node.comparators]):
                excerpt = ast.get_source_segment(text, node) or "numeric comparison"
                findings.append(AuditFinding(str(relative), node.lineno, "numeric_threshold", "D", "review", excerpt[:240]))
    return {"root": str(root), "files_inspected": len(inspected), "findings": [asdict(item) for item in findings]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = scan_repository(args.root)
    if args.json:
        print(json.dumps(result, indent=2))
        return
    print(f"Inspected {result['files_inspected']} production Python files.")
    counts = {}
    for finding in result["findings"]:
        counts[finding["rule"]] = counts.get(finding["rule"], 0) + 1
    for rule, count in sorted(counts.items()):
        print(f"{rule}: {count}")
    for finding in result["findings"]:
        if finding["classification"] == "F":
            print(f"{finding['file']}:{finding['line']} [{finding['rule']}] {finding['excerpt']}")


if __name__ == "__main__":
    main()
