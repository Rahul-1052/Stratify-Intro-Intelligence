"""Experimental local semantic text observations; not a grouping or format verdict."""
import math
import re

MODEL_NAME = 'sentence-transformers/all-MiniLM-L6-v2'


def caption_chunks(text, token_count, *, max_tokens=240, max_chunks=128):
    if not isinstance(text, str) or not text.strip() or len(text) > 100000:
        raise ValueError('Use nonempty caption text up to 100,000 characters.')
    words = text.split()
    chunks, current = [], []
    for word in words:
        proposed = ' '.join(current + [word])
        if token_count(proposed) > max_tokens:
            if not current or token_count(word) > max_tokens:
                raise ValueError('A caption token exceeds the model window.')
            chunks.append(' '.join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        chunks.append(' '.join(current))
    if len(chunks) > max_chunks:
        raise ValueError('Caption exceeds the complete-text processing limit.')
    return chunks


def cosine(a, b):
    if len(a) != len(b) or not a or any(not math.isfinite(float(v)) for v in [*a, *b]):
        raise ValueError('Invalid embedding vectors.')
    denom = math.sqrt(sum(float(v)**2 for v in a) * sum(float(v)**2 for v in b))
    if not denom:
        raise ValueError('Empty embedding direction.')
    return max(-1.0, min(1.0, sum(float(x)*float(y) for x, y in zip(a, b))/denom))


def semantic_text_observations(records, encode, token_count):
    """encode is injectable; unsupported language and oversized text abstain."""
    if not 1 <= len(records) <= 12 or len({r['video_id'] for r in records}) != len(records):
        raise ValueError('Use up to twelve unique caption records.')
    vectors, coverage = {}, []
    for record in records:
        if not re.fullmatch(r'[A-Za-z0-9_-]{11}', record['video_id']):
            raise ValueError('Invalid video ID.')
        if record.get('source') not in {'public_caption_unverified', 'creator_caption_unverified'}:
            raise ValueError('Caption provenance is required.')
        if record.get('language_code') != 'en':
            coverage.append({'video_id': record['video_id'], 'status': 'unsupported_language'})
            continue
        try:
            chunks = caption_chunks(record.get('text'), token_count)
        except ValueError:
            coverage.append({'video_id': record['video_id'], 'status': 'insufficient_or_oversized_text'})
            continue
        embedded = [list(vector) for vector in encode(chunks)]
        if len(embedded) != len(chunks) or not embedded or any(len(v) != len(embedded[0]) for v in embedded):
            raise ValueError('Encoder returned incomplete evidence.')
        # Validate vectors before averaging; never silently drop bad chunks.
        for vector in embedded:
            cosine(vector, vector)
        vector = [sum(float(v[i]) for v in embedded)/len(embedded) for i in range(len(embedded[0]))]
        cosine(vector, vector)
        vectors[record['video_id']] = vector
        coverage.append({'video_id': record['video_id'], 'status': 'encoded', 'chunks': len(chunks), 'source': record['source']})
    pairs = []
    ids = list(vectors)
    for i, left in enumerate(ids):
        for right in ids[i+1:]:
            pairs.append({'left': left, 'right': right, 'cosine_similarity': cosine(vectors[left], vectors[right])})
    return {'status': 'experimental_text_observations', 'model': MODEL_NAME, 'coverage': coverage, 'pairs': sorted(pairs, key=lambda p: (-p['cosine_similarity'], p['left'], p['right'])), 'limitations': ['Scores are text-similarity observations, not calibrated probabilities or fair-comparison decisions.', 'Format, reused footage, creator intent and comparable viewing windows remain unverified.', 'All text chunks are processed; oversized text abstains rather than analyzing only the opening.']}


def local_encoder(cache_dir):
    from fastembed import TextEmbedding
    model = TextEmbedding(model_name=MODEL_NAME, cache_dir=cache_dir, threads=2)
    tokenizer = model.model.tokenizer
    tokenizer.no_truncation()
    return lambda texts: model.embed(texts, batch_size=16), lambda text: len(tokenizer.encode(text).ids)
