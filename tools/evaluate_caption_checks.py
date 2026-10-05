"""Evaluate independent checks on retrieved captions without publishing raw text."""
import argparse
import hashlib
import json
import sys
from itertools import combinations
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.caption_comparison_checks import compare_caption_evidence, ordered_passage_alignment

parser = argparse.ArgumentParser()
parser.add_argument('--captions-json', required=True)
parser.add_argument('--output', required=True)
args = parser.parse_args()
raw = json.loads(Path(args.captions_json).read_text())
records = [r for r in raw['results'] if r['status'] == 'available']
pairs = [{**compare_caption_evidence(a, b), 'ordered_alignment': ordered_passage_alignment(a['text'], b['text'])} for a, b in combinations(records, 2)]
report = {
    'provenance': 'Automatically retrieved public captions; unverified transcription. No independent video or footage annotation.',
    'available_captions': len(records),
    'collection_statuses': [{'video_id': r['video_id'], 'status': r['status']} for r in raw['results']],
    'text_hashes': {r['video_id']: hashlib.sha256(r['text'].encode()).hexdigest() for r in records},
    'pair_count': len(pairs),
    'possible_shared_text_pairs': sum(p['overlap']['status'] == 'possible_shared_text' for p in pairs),
    'possible_shared_dialogue_pairs': sum(p['ordered_alignment']['status'] == 'possible_shared_dialogue' for p in pairs),
    'unknown_format_pairs': sum(p['format']['status'] == 'unknown' for p in pairs),
    'pairs': pairs,
    'rollout_decision': 'not_promoted',
    'limitations': ['Real caption observations are not independent ground-truth validation.', 'Exact-overlap threshold is an uncalibrated review heuristic.', 'No pair has established fair performance comparability.'],
}
Path(args.output).write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: report[k] for k in ('available_captions', 'pair_count', 'possible_shared_text_pairs', 'possible_shared_dialogue_pairs', 'unknown_format_pairs', 'rollout_decision')}))
