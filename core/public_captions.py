"""Bounded experimental retrieval of public English captions; no bypass or retries."""
import math
import re
import time
from datetime import datetime, timezone
import requests


def collect_public_captions(video_ids, *, fetch=None, clock=time.monotonic):
    if not 1 <= len(video_ids) <= 12 or len(set(video_ids)) != len(video_ids) or any(not re.fullmatch(r'[A-Za-z0-9_-]{11}', v) for v in video_ids):
        raise ValueError('Use up to twelve unique YouTube video IDs.')
    started = clock()
    results = []
    stopped = False
    session = None
    try:
        if fetch is None:
            from youtube_transcript_api import YouTubeTranscriptApi
            class BoundedSession(requests.Session):
                def request(self, method, url, **kwargs):
                    remaining = 30 - (clock() - started)
                    if remaining <= 0:
                        raise requests.Timeout()
                    kwargs['timeout'] = min(4, remaining)
                    return super().request(method, url, **kwargs)
            session = BoundedSession()
            fetch = YouTubeTranscriptApi(http_client=session).fetch
        for video_id in video_ids:
            record = {'video_id': video_id, 'source_url': f'https://www.youtube.com/watch?v={video_id}', 'status': 'not_attempted', 'text': None, 'segments': [], 'language_code': None, 'is_generated': None, 'source': 'public_caption_unverified'}
            if stopped or clock() - started >= 30:
                results.append(record)
                continue
            try:
                transcript = fetch(video_id, languages=['en'])
                if transcript.video_id != video_id or transcript.language_code != 'en':
                    raise ValueError('Unexpected transcript identity or language.')
                segments = []
                size = 0
                for item in transcript:
                    if not isinstance(item.text, str) or not math.isfinite(item.start) or not math.isfinite(item.duration) or item.start < 0 or item.duration < 0:
                        raise ValueError('Invalid caption segment.')
                    size += len(item.text) + 1
                    if size > 200000 or len(segments) >= 10000:
                        record['status'] = 'too_large'
                        break
                    segments.append({'text': item.text, 'start': item.start, 'duration': item.duration})
                else:
                    text = '\n'.join(s['text'] for s in segments)
                    record.update(status='available' if text.strip() else 'empty', text=text if text.strip() else None, segments=segments, language_code=transcript.language_code, is_generated=bool(transcript.is_generated))
            except Exception as error:
                name = type(error).__name__
                if name in {'RequestBlocked', 'IpBlocked'}:
                    record['status'] = 'blocked'
                    stopped = True
                elif name in {'TranscriptsDisabled', 'NoTranscriptFound', 'VideoUnavailable'}:
                    record['status'] = 'unavailable'
                elif isinstance(error, requests.Timeout):
                    record['status'] = 'timeout'
                else:
                    record['status'] = 'retrieval_failed'
            results.append(record)
    finally:
        if session is not None:
            session.close()
    return {'fetched_at': datetime.now(timezone.utc).isoformat(), 'provider': 'youtube-transcript-api', 'language_requested': 'en', 'results': results, 'limitations': ['Experimental public-caption retrieval can fail or be blocked. No retries or block bypass are used.', 'Only English captions are requested; missing captions are not evidence of missing speech.', 'Caption accuracy, video format and footage independence are unverified.']}
