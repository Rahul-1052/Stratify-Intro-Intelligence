"""Frozen real-caption regressions: do not mistake ranking for verified groups."""
import json
import subprocess
import sys
from pathlib import Path


def test_frozen_review_retains_known_misses_and_unknowns(tmp_path):
    root = Path(__file__).resolve().parents[1]
    out = tmp_path / 'review.json'
    subprocess.run([sys.executable, str(root / 'tools/evaluate_reviewed_caption_pairs.py'), '--output', str(out)], check=True, capture_output=True)
    report = json.loads(out.read_text())
    assert report['shared_dialogue_cases'] == 2
    assert report['shared_dialogue_cases_flagged_by_exact_overlap'] == 0
    assert all(p['format'] == 'unknown' and p['shared_footage'] == 'unknown' and p['fair_comparison'] == 'not_established' for p in report['reviewed_pairs'])
    assert all(m['passes'] == 2 for m in report['models'])
    assert report['rollout_decision'] == 'not_promoted'
