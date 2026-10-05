"""Independent, unverified caption overlap and declared-format checks.

These checks can flag review needs. Passing them never verifies independent footage.
"""
import re


def _tokens(text):
    if not isinstance(text, str) or len(text) > 100000:
        raise ValueError('Caption text must be a string up to 100,000 characters.')
    return re.findall(r"\w+(?:['’]\w+)?", text.lower(), flags=re.UNICODE)


def _shingles(tokens, width=8):
    return {tuple(tokens[i:i + width]) for i in range(len(tokens) - width + 1)}


def compare_caption_evidence(left, right):
    """Exact overlap is a review clue, never a reused-footage determination.

    Format comes only from explicit creator declarations, not titles or duration.
    """
    for row in (left, right):
        if not re.fullmatch(r'[A-Za-z0-9_-]{11}', row.get('video_id', '')):
            raise ValueError('Valid video IDs are required.')
        if row.get('source') not in {'public_caption_unverified', 'creator_caption_unverified'}:
            raise ValueError('Caption provenance is required.')
        declaration = row.get('format_declaration')
        if declaration is not None and (not isinstance(declaration, dict) or declaration.get('source') != 'creator_unverified' or declaration.get('value') not in {'short', 'regular_video', 'livestream'}):
            raise ValueError('Format declarations must be explicit, supported, and unverified.')
    if left['video_id'] == right['video_id']:
        raise ValueError('Compare two different videos.')
    a, b = _tokens(left.get('text')), _tokens(right.get('text'))
    pa, pb = _shingles(a), _shingles(b)
    shared = len(pa & pb)
    enough = min(len(pa), len(pb)) >= 10
    fraction = shared / min(len(pa), len(pb)) if enough else None
    # Conservative review threshold, not calibrated probability or decision rule.
    overlap = 'possible_shared_text' if enough and shared >= 10 and fraction >= .65 else 'no_large_exact_overlap_observed' if enough else 'insufficient_text'
    declarations = [r.get('format_declaration') for r in (left, right)]
    if all(declarations):
        format_status = 'declared_same_format_unverified' if declarations[0]['value'] == declarations[1]['value'] else 'declared_format_mismatch'
    else:
        format_status = 'unknown'
    return {
        'left': left['video_id'], 'right': right['video_id'],
        'overlap': {'status': overlap, 'shared_unique_eight_word_sequences': shared, 'fraction_of_smaller_set': fraction},
        'format': {'status': format_status, 'source': 'creator_unverified' if all(declarations) else None},
        'fair_comparison': 'not_established',
        'review_required': True,
        'limitations': ['Exact matching can miss paraphrased or differently transcribed reused material.', 'Shared scripts, quotations, and branding can produce overlap without shared footage.', 'No observed overlap does not prove independent recordings.', 'Format declarations are not verified; titles and duration do not determine format.', 'Topics, creator intent, publication windows and performance comparability still need review.'],
    }
