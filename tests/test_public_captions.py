from types import SimpleNamespace
import pytest
import requests
from core.public_captions import collect_public_captions

IDS=['abcdefghijk','bcdefghijkl','cdefghijklm']
def transcript(video_id, *, language='en', generated=False, text='Caption evidence'):
    class Transcript(list):
        pass
    result=Transcript([SimpleNamespace(text=text,start=0.5,duration=2.0)])
    result.video_id=video_id;result.language_code=language;result.is_generated=generated
    return result

def test_success_preserves_source_and_timestamps():
    result=collect_public_captions(IDS,fetch=lambda id,**_:transcript(id,generated=True))
    row=result['results'][0]
    assert row['status']=='available' and row['text']=='Caption evidence'
    assert row['segments'][0]['start']==0.5
    assert row['is_generated'] is True and row['source']=='public_caption_unverified'

@pytest.mark.parametrize('ids',[[],IDS*2,['bad'],IDS*5])
def test_invalid_input_does_not_call_provider(ids):
    with pytest.raises(ValueError):collect_public_captions(ids,fetch=lambda *_:pytest.fail('Called provider'))

def test_block_stops_further_calls_without_retries():
    class RequestBlocked(Exception):pass
    calls=[]
    def fetch(id,**_):
        calls.append(id);raise RequestBlocked('sensitive provider detail')
    result=collect_public_captions(IDS,fetch=fetch)
    assert calls==IDS[:1]
    assert [r['status'] for r in result['results']]==['blocked','not_attempted','not_attempted']
    assert 'sensitive' not in str(result)

def test_timeout_and_missing_do_not_invent_captions():
    class NoTranscriptFound(Exception):pass
    def fetch(id,**_):
        if id==IDS[0]:raise requests.Timeout('secret')
        if id==IDS[1]:raise NoTranscriptFound()
        return transcript(id,text='')
    result=collect_public_captions(IDS,fetch=fetch)
    assert [r['status'] for r in result['results']]==['timeout','unavailable','empty']
    assert all(r['text'] is None for r in result['results'])

def test_identity_language_and_size_are_checked():
    for fetch in [lambda id,**_:transcript('wrong'),lambda id,**_:transcript(id,language='de')]:
        assert collect_public_captions(IDS[:1],fetch=fetch)['results'][0]['status']=='retrieval_failed'
    row=collect_public_captions(IDS[:1],fetch=lambda id,**_:transcript(id,text='x'*200001))['results'][0]
    assert row['status']=='too_large' and row['text'] is None

def test_budget_does_not_start_more_work():
    ticks=iter([0,31,32,33])
    result=collect_public_captions(IDS,fetch=lambda *_:pytest.fail('Budget exceeded'),clock=lambda:next(ticks))
    assert all(r['status']=='not_attempted' for r in result['results'])

def test_private_endpoint_validation_and_missing_dependency(monkeypatch):
    from api.main import app
    from fastapi.testclient import TestClient
    import core.public_captions as module
    monkeypatch.setenv('STRATIFY_SERVICE_TOKEN','x'*32)
    client=TestClient(app);headers={'Authorization':'Bearer '+'x'*32}
    assert client.post('/v1/public-captions',json={'video_ids':IDS}).status_code==401
    for ids in [[],['bad'],IDS*2,IDS*5]:assert client.post('/v1/public-captions',json={'video_ids':ids},headers=headers).status_code==422
    monkeypatch.setattr(module,'collect_public_captions',lambda ids:{'results':[]})
    assert client.post('/v1/public-captions',json={'video_ids':IDS},headers=headers).status_code==200
    def missing(*_):raise ImportError('secret')
    monkeypatch.setattr(module,'collect_public_captions',missing)
    r=client.post('/v1/public-captions',json={'video_ids':IDS},headers=headers)
    assert r.status_code==503 and 'secret' not in r.text
