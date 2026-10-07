import pytest
from core.caption_comparison_checks import compare_caption_evidence


def row(video_id, text, fmt=None):
    r = dict(video_id=video_id, text=text, source='public_caption_unverified')
    if fmt:
        r['format_declaration'] = dict(value=fmt, source='creator_unverified')
    return r


def test_renamed_excerpt_is_flagged_without_titles():
    excerpt = ' '.join(f'word{i}' for i in range(80))
    result = compare_caption_evidence(row('abcdefghijk', excerpt), row('bcdefghijkl', 'extra beginning ' + excerpt + ' different ending'))
    assert result['overlap']['status'] == 'possible_shared_text'
    assert result['fair_comparison'] == 'not_established'
    assert result['format']['status'] == 'unknown'


def test_format_mismatch_survives_identical_topic_text():
    text = ' '.join(f'word{i}' for i in range(50))
    result = compare_caption_evidence(row('abcdefghijk', text, 'short'), row('bcdefghijkl', text, 'regular_video'))
    assert result['format']['status'] == 'declared_format_mismatch'
    assert result['review_required']


def test_distinct_words_do_not_prove_independent_footage():
    a = ' '.join(f'alpha{i}' for i in range(50))
    b = ' '.join(f'beta{i}' for i in range(50))
    result = compare_caption_evidence(row('abcdefghijk', a, 'regular_video'), row('bcdefghijkl', b, 'regular_video'))
    assert result['overlap']['status'] == 'no_large_exact_overlap_observed'
    assert result['fair_comparison'] == 'not_established'
    assert result['format']['status'] == 'declared_same_format_unverified'
    assert result['review_required']


def test_short_shared_slogan_is_insufficient():
    result = compare_caption_evidence(row('abcdefghijk', 'subscribe and watch our next video'), row('bcdefghijkl', 'subscribe and watch our next video'))
    assert result['overlap']['status'] == 'insufficient_text'
    assert result['overlap']['fraction_of_smaller_set'] is None


@pytest.mark.parametrize('change', [{'source': 'verified'}, {'video_id': 'bad'}, {'format_declaration': {'value': 'short', 'source': 'title'}}, {'text': 'a' * 100001}])
def test_invalid_evidence_fails(change):
    a = row('abcdefghijk', 'caption')
    a.update(change)
    with pytest.raises(ValueError):
        compare_caption_evidence(a, row('bcdefghijkl', 'caption'))


def test_alignment_tolerates_cue_annotations_and_intervening_edits():
    from core.caption_comparison_checks import ordered_passage_alignment
    words = [f'word{i}' for i in range(90)]
    changed = ' '.join(words[:30] + ['different', 'transcription'] + words[30:60] + ['[laughter]'] + words[60:])
    result = ordered_passage_alignment(' '.join(words), 'new opening ' + changed)
    assert result['status'] == 'possible_shared_dialogue'
    assert result['matched_tokens'] == 90


def test_alignment_does_not_promote_shared_script_to_recording_verification():
    from core.caption_comparison_checks import ordered_passage_alignment
    script = ' '.join(f'word{i}' for i in range(90))
    result = ordered_passage_alignment(script, script)
    assert result['status'] == 'possible_shared_dialogue'
    assert any('without shared recordings' in s for s in result['limitations'])


def test_alignment_abstains_on_complete_oversized_documents():
    from core.caption_comparison_checks import ordered_passage_alignment
    result = ordered_passage_alignment('word ' * 1100, 'word ' * 1100)
    assert result['status'] == 'insufficient_or_oversized_text'
    assert result['matched_tokens'] is None


def test_unrelated_dialogue_is_not_flagged():
    from core.caption_comparison_checks import ordered_passage_alignment
    result = ordered_passage_alignment(' '.join(f'alpha{i}' for i in range(90)), ' '.join(f'beta{i}' for i in range(90)))
    assert result['status'] == 'no_large_ordered_alignment_observed'
