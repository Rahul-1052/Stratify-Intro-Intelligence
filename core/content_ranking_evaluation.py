"""Reviewed topical ranking diagnostics, never a production grouping verdict."""
import math
import re


def evaluate_reviewed_triplets(cases, observations):
    if not cases or len(cases) > 100 or len({c.get('id') for c in cases}) != len(cases):
        raise ValueError('Use one to one hundred uniquely identified reviewed cases.')
    coverage_rows = observations.get('coverage', [])
    if len({r['video_id'] for r in coverage_rows}) != len(coverage_rows):
        raise ValueError('Coverage must use unique video IDs.')
    coverage = {r['video_id']: r['status'] for r in coverage_rows}
    pairs = {}
    for row in observations.get('pairs', []):
        key = tuple(sorted([row['left'], row['right']]))
        score = row['cosine_similarity']
        if len(set(key)) != 2 or key in pairs or isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score) or not -1 <= score <= 1:
            raise ValueError('Similarity evidence must have unique valid finite pairs.')
        pairs[key] = score
    results = []
    for case in cases:
        ids = [case.get(k) for k in ('anchor', 'closer', 'different')]
        if not case.get('id') or len(set(ids)) != 3 or any(not isinstance(v, str) or not re.fullmatch(r'[A-Za-z0-9_-]{11}', v) for v in ids):
            raise ValueError('Each case requires three different valid video IDs.')
        if case.get('reviewer_kind') not in {'user', 'assistant', 'independent_human'} or not isinstance(case.get('reason'), str) or not case['reason'].strip() or not isinstance(case.get('channel'), str) or not case['channel'].strip():
            raise ValueError('Explicit review provenance, channel and reason are required.')
        a = pairs.get(tuple(sorted([ids[0], ids[1]])))
        b = pairs.get(tuple(sorted([ids[0], ids[2]])))
        complete = all(coverage.get(v) == 'encoded' for v in ids) and a is not None and b is not None
        results.append({**case, 'status': 'ranked' if complete else 'pending_evidence',
                        'closer_score': a if complete else None, 'different_score': b if complete else None,
                        'margin': a-b if complete else None,
                        'closer_ranks_first': a > b if complete else None,
                        'fair_performance_comparison': 'not_established'})
    summary = {}
    for kind in ('user', 'assistant', 'independent_human'):
        rows = [r for r in results if r['reviewer_kind'] == kind]
        summary[kind] = {'cases': len(rows), 'ranked': sum(r['status'] == 'ranked' for r in rows),
                         'ranking_agreements': sum(r['closer_ranks_first'] is True for r in rows),
                         'pending': sum(r['status'] == 'pending_evidence' for r in rows)}
    return {'cases': results, 'summary_by_review_source': summary, 'rollout_decision': 'not_promoted',
            'limitations': ['Ranking agreement is not a calibrated grouping decision or an accuracy estimate.',
                           'Assistant reviews are development labels, not independent held-out labels.',
                           'Format, audience intent, reused footage and equal viewing time remain unverified.',
                           'Missing or unsupported evidence does not count as a ranking error or disagreement.']}
