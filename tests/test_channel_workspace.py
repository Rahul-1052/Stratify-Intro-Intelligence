import pytest
import requests
from fastapi.testclient import TestClient
from api import main
from core.channel_workspace import channel_selector, collect_channel_workspace, optional_count

CHANNEL = 'UC' + 'a' * 22
TOKEN = 'test-service-token-that-is-long-enough'
INQUIRY = {'focus': 'open_question', 'question': 'Which direction fits?', 'period': '', 'confirmed': True}


@pytest.mark.parametrize('value,selector', [
    ('@creator', {'forHandle': '@creator'}),
    ('https://www.youtube.com/@creator/videos', {'forHandle': '@creator'}),
    (CHANNEL, {'id': CHANNEL}),
    ('https://youtube.com/channel/' + CHANNEL, {'id': CHANNEL}),
    ('https://youtube.com/user/creator', {'forUsername': 'creator'}),
])
def test_resolver(value, selector):
    assert channel_selector(value) == selector


@pytest.mark.parametrize('value', ['https://youtube.com.evil.test/@creator', 'https://youtube.com@evil.test/@creator',
    'http://youtube.com/@creator', 'https://youtube.com:444/@creator', 'https://127.0.0.1/@creator',
    'https://youtube.com/watch?v=abcdefghijk', 'https://youtube.com/c/creator', 'https://youtube.com/@creator/anything'])
def test_resolver_rejects(value):
    with pytest.raises(ValueError):
        channel_selector(value)


def test_pagination_missing_counts_unavailable_and_order():
    calls = []
    def get(endpoint, params):
        calls.append((endpoint, params))
        if endpoint == 'channels':
            return {'items': [{'id': CHANNEL, 'snippet': {'title': 'Creator'}, 'statistics': {'hiddenSubscriberCount': True, 'subscriberCount': '45', 'videoCount': '3'}, 'contentDetails': {'relatedPlaylists': {'uploads': 'uploads'}}}]}
        if endpoint == 'playlistItems':
            ids = ['one', 'two'] if 'pageToken' not in params else ['one', 'three']
            return {'items': [{'contentDetails': {'videoId': value}} for value in ids], 'nextPageToken': 'next'}
        return {'items': [{'id': value, 'snippet': {'channelId': CHANNEL, 'title': value, 'publishedAt': '2026-01-01'}, 'statistics': {'viewCount': '0'}} for value in ['three', 'one']]}
    report = collect_channel_workspace('@creator', 'Why are views down?', get=get)
    assert report['concern'] == 'Why are views down?'
    assert report['channel']['subscribers'] is None
    assert [v['video_id'] for v in report['videos']] == ['one', 'three']
    assert report['videos'][0]['views'] == 0
    assert report['videos'][0]['likes'] is None
    assert report['coverage']['entries_checked'] == 3
    assert report['coverage']['unavailable_entries'] == 1
    assert report['coverage']['more_uploads_available']
    assert sum(endpoint == 'playlistItems' for endpoint, _ in calls) == 2
    assert report['recommendation'] is None


def test_empty_channel_is_not_zero():
    def get(endpoint, params):
        return {'items': [{'id': CHANNEL}]}
    report = collect_channel_workspace('@creator', 'Help', get=get)
    assert report['videos'] == []
    assert report['channel']['video_count'] is None
    assert not report['coverage']['uploads_playlist_available']
    assert optional_count('-1') is None
    assert optional_count('bad') is None
    assert collect_channel_workspace('@creator', 'Help', get=lambda *_: {'items': []}) is None


def test_api_validation_auth_and_sanitized_errors(monkeypatch):
    monkeypatch.setenv('STRATIFY_SERVICE_TOKEN', TOKEN)
    client = TestClient(main.app)
    payload = {'channel': '@creator', 'concern': 'Help me understand', 'inquiry': INQUIRY}
    headers = {'Authorization': 'Bearer ' + TOKEN}
    assert client.post('/v1/channel-workspace', json=payload).status_code == 401
    for invalid in [dict(payload, concern='   '), dict(payload, concern='x'*2001), dict(payload, channel='https://evil.test'), dict(payload, extra=True)]:
        assert client.post('/v1/channel-workspace', json=invalid, headers=headers).status_code == 422
    import core.channel_workspace as module
    for error, status in [(requests.Timeout('secret'), 504), (RuntimeError('secret'), 502), (ValueError('secret'), 503)]:
        def fail(*_, failure=error):
            raise failure
        monkeypatch.setattr(module, 'collect_channel_workspace', fail)
        response = client.post('/v1/channel-workspace', json=payload, headers=headers)
        assert response.status_code == status
        assert 'secret' not in response.text
    monkeypatch.setattr(module, 'collect_channel_workspace', lambda *_: None)
    assert client.post('/v1/channel-workspace', json=payload, headers=headers).status_code == 404


def test_hundred_entry_bound_and_batching():
    calls = []
    def get(endpoint, params):
        calls.append((endpoint, params))
        if endpoint == 'channels':
            return {'items': [{'id': CHANNEL, 'contentDetails': {'relatedPlaylists': {'uploads': 'uploads'}}}]}
        if endpoint == 'playlistItems':
            start = 50 if 'pageToken' in params else 0
            return {'items': [{'contentDetails': {'videoId': str(i)}} for i in range(start, start+50)], 'nextPageToken': str(start+50)}
        return {'items': []}
    report = collect_channel_workspace('@creator', 'New direction?', get=get)
    assert report['coverage']['entries_checked'] == 100
    assert report['coverage']['unavailable_entries'] == 100
    assert len(calls) == 5
    assert all(len(params['id'].split(',')) == 50 for endpoint, params in calls if endpoint == 'videos')


def test_api_records_concern_without_answer(monkeypatch):
    monkeypatch.setenv('STRATIFY_SERVICE_TOKEN', TOKEN)
    import core.channel_workspace as module
    monkeypatch.setattr(module, 'youtube_get', lambda *_: {'items': [{'id': CHANNEL}]})
    response = TestClient(main.app).post('/v1/channel-workspace', json={'channel': '@creator', 'concern': '  Which direction fits?  ', 'inquiry': INQUIRY}, headers={'Authorization': 'Bearer ' + TOKEN})
    assert response.status_code == 200
    assert response.json()['concern'] == 'Which direction fits?'
    assert response.json()['recommendation'] is None
    assert response.json()['status'] == 'facts_only'


@pytest.mark.parametrize('inquiry', [None, {}, dict(INQUIRY, confirmed=False), dict(INQUIRY, confirmed='true'), dict(INQUIRY, focus='made_up'), dict(INQUIRY, question='   '), dict(INQUIRY, period='x'*201), dict(INQUIRY, question='x'*2001), dict(INQUIRY, invented=True)])
def test_invalid_inquiry_never_reaches_provider(monkeypatch, inquiry):
    monkeypatch.setenv('STRATIFY_SERVICE_TOKEN', TOKEN)
    import core.channel_workspace as module
    monkeypatch.setattr(module, 'collect_channel_workspace', lambda *_: pytest.fail('Invalid inquiry reached provider'))
    payload = {'channel': '@creator', 'concern': 'Help', 'inquiry': inquiry}
    assert TestClient(main.app).post('/v1/channel-workspace', json=payload, headers={'Authorization': 'Bearer ' + TOKEN}).status_code == 422


def test_inquiry_preserves_creator_words_and_does_not_diagnose(monkeypatch):
    monkeypatch.setenv('STRATIFY_SERVICE_TOKEN', TOKEN)
    import core.channel_workspace as module
    monkeypatch.setattr(module, 'youtube_get', lambda *_: {'items': [{'id': CHANNEL}]})
    inquiry = dict(INQUIRY, focus='watching', question='Is my deliberate slow branding working?', period='My last six tutorials')
    result = TestClient(main.app).post('/v1/channel-workspace', json={'channel': '@creator', 'concern': 'Not sure', 'inquiry': inquiry}, headers={'Authorization': 'Bearer ' + TOKEN}).json()
    assert result['inquiry']['question'] == inquiry['question']
    assert result['inquiry']['period'] == inquiry['period']
    assert result['inquiry']['source'] == 'creator_confirmed'
    assert result['inquiry']['status'] == 'scope_confirmed_not_answered'
    assert any('deliberate pacing' in item for item in result['inquiry']['evidence_needed'])
    assert result['recommendation'] is None
