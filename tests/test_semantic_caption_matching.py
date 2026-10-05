import pytest
from core.semantic_caption_matching import caption_chunks, cosine, semantic_text_observations


def record(video_id='abcdefghijk', **updates):
    return dict(video_id=video_id, source='public_caption_unverified', language_code='en', text='full caption text', **updates)


def test_chunks_preserve_late_content():
    text = ' '.join(str(i) for i in range(500))
    chunks = caption_chunks(text, lambda s: len(s.split()), max_tokens=100)
    assert len(chunks) == 5
    assert ' '.join(chunks) == text
    with pytest.raises(ValueError):
        caption_chunks(text, lambda s: len(s.split()), max_tokens=100, max_chunks=4)


@pytest.mark.parametrize('a,b', [([], []), ([0], [1]), ([float('nan')], [1]), ([1], [1, 2])])
def test_invalid_embeddings_fail(a, b):
    with pytest.raises(ValueError):
        cosine(a, b)


def test_observations_keep_provenance_and_abstain_on_unsupported_text():
    rows = [record(), record('bcdefghijkl'), dict(record('cdefghijklm'), language_code='fr'), dict(record('defghijklmn'), text='')]
    result = semantic_text_observations(rows, lambda texts: [[1, 2] for _ in texts], lambda s: len(s.split()))
    assert len(result['pairs']) == 1
    assert result['pairs'][0]['left'] == 'abcdefghijk'
    assert [r['status'] for r in result['coverage']] == ['encoded', 'encoded', 'unsupported_language', 'insufficient_or_oversized_text']
    assert result['coverage'][0]['source'] == 'public_caption_unverified'


def test_incomplete_encoder_output_is_rejected():
    with pytest.raises(ValueError):
        semantic_text_observations([record()], lambda texts: [], len)


def test_unverified_provenance_is_required():
    with pytest.raises(ValueError):
        semantic_text_observations([dict(record(), source='verified')], lambda texts: [[1]], len)
