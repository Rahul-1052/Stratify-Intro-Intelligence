import pytest
from core.content_review_intake import record_content_review


def packet():
    return {'cases':[{'id':'case','channel':'fixture','anchor':{'video_id':'abcdefghijk'},'candidate_b':{'video_id':'bcdefghijkl'},'candidate_c':{'video_id':'cdefghijklm'},'review':None,'model_result':None}]}


def record(p=None,**updates):
    args={'reviewer':'Human','reviewer_kind':'user','choice':'c','reason':'I watched the content and compared the intended topic.','review_basis':'whole_videos','understands_language':True}
    args.update(updates)
    return record_content_review(p or packet(),'case',**args)


def test_human_choice_is_preserved_without_mutating_packet():
    p=packet();r=record(p)
    assert p['cases'][0]['review'] is None
    assert r['ranking_case']['closer']=='cdefghijklm'
    assert r['ranking_case']['different']=='bcdefghijkl'


@pytest.mark.parametrize('choice',['both','neither','unsure'])
def test_uncertainty_does_not_become_a_forced_ranking(choice):
    assert record(choice=choice)['ranking_case'] is None


def test_title_only_partial_and_unfamiliar_language_cannot_supply_strict_labels():
    for basis in ['titles_only','partial_videos']:assert record(review_basis=basis)['ranking_case'] is None
    assert record(understands_language=False)['ranking_case'] is None


def test_assistant_labels_blank_reasons_and_existing_or_exposed_reviews_are_rejected():
    with pytest.raises(ValueError):record(reviewer_kind='assistant')
    with pytest.raises(ValueError):record(reason=' ')
    p=record()['packet']
    with pytest.raises(ValueError):record(p)
    p=packet();p['cases'][0]['model_result']={'prediction':'c'}
    with pytest.raises(ValueError):record(p)
