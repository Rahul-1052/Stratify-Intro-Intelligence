"""Bounded public channel facts. No performance diagnosis or generated advice."""
import re
from datetime import datetime, timezone
from urllib.parse import urlparse, unquote

from core.youtube_client import youtube_get, clean_text


class ChannelInputError(ValueError):
    pass


def channel_selector(value):
    value = value.strip()
    if re.fullmatch(r'UC[A-Za-z0-9_-]{22}', value):
        return {'id': value}
    if value.startswith('@') and re.fullmatch(r'@[\w.\-]{3,30}', value):
        return {'forHandle': value}
    try:
        parsed = urlparse(value)
        if (parsed.scheme != 'https' or parsed.hostname not in
                {'youtube.com', 'www.youtube.com', 'm.youtube.com'} or
                parsed.username or parsed.password or parsed.port):
            raise ChannelInputError()
        path = unquote(parsed.path).strip('/').split('/')
        if len(path) == 2 and path[1] in {'videos', 'shorts', 'streams', 'featured'} and path[0].startswith('@'):
            path = path[:1]
        if len(path) == 1 and path[0].startswith('@'):
            return channel_selector(path[0])
        if len(path) == 2 and path[0] == 'channel' and re.fullmatch(r'UC[A-Za-z0-9_-]{22}', path[1]):
            return {'id': path[1]}
        if len(path) == 2 and path[0] == 'user' and re.fullmatch(r'[\w.\-]{1,100}', path[1]):
            return {'forUsername': path[1]}
    except ValueError:
        pass
    raise ChannelInputError('Use a YouTube @handle, channel ID, or HTTPS channel link. For a /c/ link, use the channel’s @handle instead.')


def optional_count(value):
    try:
        count = int(value)
        return count if count >= 0 else None
    except (ValueError, TypeError):
        return None


def collect_channel_workspace(identifier, concern, *, get=None):
    get = get or youtube_get
    fetched_at = datetime.now(timezone.utc).isoformat()
    data = get('channels', {'part': 'snippet,statistics,contentDetails', **channel_selector(identifier)})
    if not data.get('items'):
        return None
    item = data['items'][0]
    channel_id = item['id']
    snippet, stats = item.get('snippet', {}), item.get('statistics', {})
    channel = {
        'channel_id': channel_id, 'title': clean_text(snippet.get('title')),
        'created_at': snippet.get('publishedAt'),
        'source_url': f'https://www.youtube.com/channel/{channel_id}',
        'subscribers': None if stats.get('hiddenSubscriberCount') else optional_count(stats.get('subscriberCount')),
        'total_views': optional_count(stats.get('viewCount')),
        'video_count': optional_count(stats.get('videoCount')),
    }
    playlist = item.get('contentDetails', {}).get('relatedPlaylists', {}).get('uploads')
    ids, tokens, next_token, pages = [], set(), None, 0
    if playlist:
        # At most two playlist pages and 100 unique entries, including unavailable entries.
        for _ in range(2):
            params = {'part': 'contentDetails', 'playlistId': playlist, 'maxResults': 50}
            if next_token:
                params['pageToken'] = next_token
            page = get('playlistItems', params)
            pages += 1
            for entry in page.get('items', [])[:50]:
                video_id = entry.get('contentDetails', {}).get('videoId')
                if video_id and video_id not in ids:
                    ids.append(video_id)
            next_token = page.get('nextPageToken')
            if not next_token or next_token in tokens:
                break
            tokens.add(next_token)
    records = {}
    for start in range(0, len(ids), 50):
        details = get('videos', {'part': 'snippet,statistics,contentDetails', 'id': ','.join(ids[start:start+50])})
        for video in details.get('items', []):
            s, st = video.get('snippet', {}), video.get('statistics', {})
            if video.get('id') not in ids or s.get('channelId') != channel_id:
                continue
            video_id = video['id']
            records[video_id] = {
                'video_id': video_id, 'title': clean_text(s.get('title')),
                'published_at': s.get('publishedAt'),
                'duration': video.get('contentDetails', {}).get('duration'),
                'views': optional_count(st.get('viewCount')),
                'likes': optional_count(st.get('likeCount')),
                'comments': optional_count(st.get('commentCount')),
                'source_url': f'https://www.youtube.com/watch?v={video_id}',
            }
    videos = [records[key] for key in ids if key in records]
    dates = sorted(v['published_at'] for v in videos if v['published_at'])
    return {
        'status': 'facts_only', 'concern': concern.strip(), 'fetched_at': fetched_at,
        'channel': channel, 'videos': videos,
        'coverage': {'limit': 100, 'playlist_pages': pages, 'entries_checked': len(ids),
                     'videos_available': len(videos), 'unavailable_entries': len(ids)-len(videos),
                     'more_uploads_available': bool(next_token), 'uploads_playlist_available': bool(playlist),
                     'oldest_published_at': dates[0] if dates else None,
                     'newest_published_at': dates[-1] if dates else None},
        'limitations': [
            'This is a bounded sample of public uploads, not a complete channel diagnosis.',
            'The concern is recorded in your words; it has not yet been interpreted or answered.',
            'Views are cumulative. Different publication dates, topics and formats prevent a fair ranking from these counts alone.',
            'Retention, impressions, click-through rates, subscriber conversion and returning viewers are not available here.',
            'Titles and counts were retrieved. Thumbnail meaning, video content and audience reactions were not analyzed.',
            'Channel creation date does not establish when regular publishing began or how loyal viewers are.',
        ], 'recommendation': None,
    }
