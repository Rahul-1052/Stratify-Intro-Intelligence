"""Compare frozen derived observations with caption-only development labels."""
import argparse
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--output', required=True)
args = parser.parse_args()
fixture = root / 'tests/fixtures/reviewed-caption-pairs.json'
labels = json.loads(fixture.read_text())
checks = json.loads((root / 'docs/evaluations/caption-independent-checks.json').read_text())
key = lambda a, b: tuple(sorted((a, b)))
observed = {key(p['left'], p['right']): p for p in checks['pairs']}
results = []
for case in labels['cases']:
    actual = observed[key(case['left'], case['right'])]
    results.append({**case, 'exact_overlap_flag': actual['overlap']['status'], 'fair_comparison': actual['fair_comparison'], 'ordered_alignment_flag': actual.get('ordered_alignment', {}).get('status', 'not_evaluated')})
models = []
expected_inventory = set(checks['text_hashes'])
for filename in ('semantic-caption-minilm.json', 'semantic-caption-bge-small.json'):
    report = json.loads((root / 'docs/evaluations' / filename).read_text())
    coverage = report['live_text_observations']['coverage']
    if {r['video_id'] for r in coverage if r['status'] == 'encoded'} != expected_inventory:
        raise ValueError('Model and independent-check inventories differ.')
    scores = {key(p['left'], p['right']): p['cosine_similarity'] for p in report['live_text_observations']['pairs']}
    probes = []
    for probe in labels['ranking_probes']:
        closer = scores[key(probe['anchor'], probe['closer_dialogue'])]
        different = scores[key(probe['anchor'], probe['different_dialogue'])]
        probes.append({**probe, 'closer_score': closer, 'different_score': different, 'closer_ranks_first': closer > different})
    models.append({'model': report['model'], 'probes': probes, 'passes': sum(p['closer_ranks_first'] for p in probes)})
positives = [r for r in results if r['shared_dialogue'] == 'observed']
output = {
    'provenance': labels['provenance'], 'review_scope': labels['review_scope'],
    'fixture_sha256': hashlib.sha256(fixture.read_bytes()).hexdigest(),
    'reviewed_pairs': results, 'shared_dialogue_cases': len(positives),
    'shared_dialogue_cases_flagged_by_exact_overlap': sum(r['exact_overlap_flag'] == 'possible_shared_text' for r in positives),
    'shared_dialogue_cases_flagged_by_ordered_alignment': sum(r['ordered_alignment_flag'] == 'possible_shared_dialogue' for r in positives),
    'models': models, 'rollout_decision': 'not_promoted',
    'limitations': ['Seven development pairs from one channel are not independent held-out validation.', 'No verified video-format or shared-footage labels are available.', 'Ranking success is not a calibrated grouping decision. High scores occur for different dialogue.', 'Reports share the checked video inventory and original retrieval session. Semantic reports did not preserve caption hashes, so hash identity cannot be independently confirmed; no fresh retrieval is performed.'],
}
Path(args.output).write_text(json.dumps(output, indent=2) + '\n')
print(json.dumps({'reviewed_pairs': len(results), 'shared_dialogue_cases': len(positives), 'exact_overlap_flags': output['shared_dialogue_cases_flagged_by_exact_overlap'], 'model_ranking_passes': [m['passes'] for m in models], 'rollout_decision': output['rollout_decision']}))
