"""Preserve human uncertainty; never manufacture independent review labels."""
import copy
from datetime import datetime, timezone


def record_content_review(packet, case_id, *, reviewer, reviewer_kind, choice, reason, review_basis, understands_language):
    if not isinstance(reviewer,str) or not reviewer.strip() or reviewer_kind not in {'user','independent_human'}:
        raise ValueError('Name the human reviewer and their declared review source.')
    if choice not in {'b','c','both','neither','unsure'} or not isinstance(reason,str) or not reason.strip():
        raise ValueError('Record a choice and the reviewer’s own reason.')
    if review_basis not in {'whole_videos','partial_videos','titles_only'} or (understands_language is not None and not isinstance(understands_language,bool)):
        raise ValueError('Record review coverage and language understanding explicitly.')
    matches=[c for c in packet['cases'] if c['id']==case_id]
    if len(matches)!=1: raise ValueError('Select one uniquely identified review case.')
    if matches[0].get('review') is not None: raise ValueError('This review already exists; preserve it rather than overwrite it.')
    if matches[0].get('model_result') is not None: raise ValueError('Model predictions must remain hidden until review is recorded.')
    result=copy.deepcopy(packet)
    case=next(c for c in result['cases'] if c['id']==case_id)
    eligible=choice in {'b','c'} and review_basis=='whole_videos' and understands_language is True
    case['review']={'reviewer':reviewer.strip(),'reviewer_kind':reviewer_kind,'choice':choice,'reason':reason.strip(),'review_basis':review_basis,'understands_language':understands_language,'recorded_at':datetime.now(timezone.utc).isoformat(),'provenance':'Human-reported, not independently authenticated by this tool.'}
    case['status']='review_recorded' if eligible else 'review_recorded_no_strict_ranking'
    ranking=None
    if eligible:
        closer,different=(case['candidate_b'],case['candidate_c']) if choice=='b' else (case['candidate_c'],case['candidate_b'])
        ranking={'id':case['id'],'channel':case['channel'],'anchor':case['anchor']['video_id'],'closer':closer['video_id'],'different':different['video_id'],'reviewer_kind':reviewer_kind,'reason':reason.strip()}
    return {'packet':result,'ranking_case':ranking,'limitations':['A human label is a topical judgment, not verified format, independent footage or performance comparability.','Both/neither/unsure, partial coverage and unsupported reviewer language do not become forced rankings.','A small reviewed packet is not a calibrated held-out accuracy benchmark.']}
