import pytest
from core.content_ranking_evaluation import evaluate_reviewed_triplets

IDS=['abcdefghijk','bcdefghijkl','cdefghijklm']
CASE={'id':'review','channel':'fixture','anchor':IDS[0],'closer':IDS[1],'different':IDS[2],'reviewer_kind':'user','reason':'User supplied a topical comparison.'}


def observations(a=.8,b=.4):
    return {'coverage':[{'video_id':v,'status':'encoded'} for v in IDS],
            'pairs':[{'left':IDS[0],'right':IDS[1],'cosine_similarity':a}, {'left':IDS[0],'right':IDS[2],'cosine_similarity':b}]}


def test_success_is_ranking_only_and_keeps_review_sources_separate():
    result=evaluate_reviewed_triplets([CASE],observations())
    assert result['cases'][0]['closer_ranks_first'] is True
    assert result['cases'][0]['fair_performance_comparison']=='not_established'
    assert result['summary_by_review_source']['independent_human']['cases']==0
    assert result['rollout_decision']=='not_promoted'


def test_missing_unsupported_and_incomplete_pairs_remain_pending():
    for status in ['unsupported_language','insufficient_or_oversized_text']:
        obs=observations();obs['coverage'][1]['status']=status
        row=evaluate_reviewed_triplets([CASE],obs)['cases'][0]
        assert row['status']=='pending_evidence' and row['closer_ranks_first'] is None
    obs=observations();obs['pairs'].pop()
    assert evaluate_reviewed_triplets([CASE],obs)['cases'][0]['margin'] is None


def test_ties_and_wrong_rank_do_not_count_as_agreement():
    for a,b in [(.4,.4),(.3,.8)]:
        result=evaluate_reviewed_triplets([CASE],observations(a,b))
        assert result['summary_by_review_source']['user']['ranking_agreements']==0


@pytest.mark.parametrize('score',[float('nan'),float('inf'),1.01,True])
def test_invalid_similarity_is_rejected(score):
    with pytest.raises(ValueError): evaluate_reviewed_triplets([CASE],observations(score,.4))


def test_invalid_labels_duplicate_pairs_and_duplicate_cases_are_rejected():
    with pytest.raises(ValueError): evaluate_reviewed_triplets([{**CASE,'reviewer_kind':'verified_ai'}],observations())
    with pytest.raises(ValueError): evaluate_reviewed_triplets([CASE,CASE],observations())
    with pytest.raises(ValueError): evaluate_reviewed_triplets([{**CASE,'different':CASE['closer']}],observations())
    obs=observations();obs['pairs'].append(obs['pairs'][0])
    with pytest.raises(ValueError): evaluate_reviewed_triplets([CASE],obs)


def test_duplicate_coverage_is_rejected_and_empty_evidence_remains_pending():
    obs=observations();obs['coverage'].append(obs['coverage'][0])
    with pytest.raises(ValueError): evaluate_reviewed_triplets([CASE],obs)
    result=evaluate_reviewed_triplets([CASE],{'coverage':[],'pairs':[]})
    assert result['summary_by_review_source']['user']['pending']==1
    assert result['cases'][0]['closer_ranks_first'] is None


def test_offline_runner_records_blocked_inputs_without_loading_a_model(tmp_path):
    import json
    import subprocess
    import sys
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    cases=tmp_path/'cases.json';captions=tmp_path/'captions.json';out=tmp_path/'report.json'
    cases.write_text(json.dumps({'cases':[CASE]}))
    captions.write_text(json.dumps({'provider':'fixture','results':[{'video_id':v,'status':'blocked'} for v in IDS]}))
    subprocess.run([sys.executable,str(root/'tools/evaluate_content_triplets.py'),'--cases',str(cases),'--captions-json',str(captions),'--cache-dir',str(tmp_path/'unused-model'),'--output',str(out)],check=True,capture_output=True)
    result=json.loads(out.read_text())
    assert result['semantic']['summary_by_review_source']['user']['pending']==1
    assert all(r['status']=='blocked' for r in result['retrieval_coverage'])
    assert not (tmp_path/'unused-model').exists()
    assert result['caption_evidence']==[]
