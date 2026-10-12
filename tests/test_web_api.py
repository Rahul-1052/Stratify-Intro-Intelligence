import pytest
import requests
from fastapi.testclient import TestClient
from api import main

TOKEN = "test-service-token-that-is-long-enough"
client = TestClient(main.app)
headers = {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture(autouse=True)
def environment(monkeypatch):
    monkeypatch.setenv("STRATIFY_SERVICE_TOKEN", TOKEN)


def test_fail_closed_without_configuration(monkeypatch):
    monkeypatch.delenv("STRATIFY_SERVICE_TOKEN")
    assert client.post("/v1/analyses", json={"url": "https://youtu.be/abcdefghijk"}, headers=headers).status_code == 503


def test_auth_required():
    assert client.post("/v1/analyses", json={"url": "https://youtu.be/abcdefghijk"}).status_code == 401


@pytest.mark.parametrize("url", [
    "http://youtu.be/abcdefghijk", "https://youtube.com.evil.test/watch?v=abcdefghijk",
    "https://127.0.0.1/private", "https://youtube.com@evil.test/watch?v=abcdefghijk",
    "https://youtu.be/short", "https://youtube.com:444/watch?v=abcdefghijk",
])
def test_invalid_sources_rejected(url, monkeypatch):
    monkeypatch.setattr(main, "get_video_details", lambda _: pytest.fail("Invalid input reached provider"))
    assert client.post("/v1/analyses", json={"url": url}, headers=headers).status_code == 422


def test_real_adapter_contract_abstains(monkeypatch):
    urls = []
    def provider(url):
        urls.append(url)
        return {"video_id": "abcdefghijk", "title": "Example", "channel_title": "Creator",
                "published_at": "2026-01-01", "views": 100, "likes": 8, "comments": 2,
                "description": "Not part of the public response"}
    monkeypatch.setattr(main, "get_video_details", provider)
    response = client.post("/v1/analyses", json={"url": "https://youtu.be/abcdefghijk?t=3"}, headers=headers)
    assert response.status_code == 200
    report = response.json()
    assert urls == ["https://www.youtube.com/watch?v=abcdefghijk"]
    assert report["recommendation"] is None
    assert report["evidence_level"] == "metadata_only"
    assert report["status"] == "partial"
    assert "description" not in report["video"]


@pytest.mark.parametrize("failure,status", [(requests.Timeout("secret"),504), (RuntimeError("secret"),502), (ValueError("secret"),503)])
def test_provider_errors_sanitized(monkeypatch, failure, status):
    def provider(_):
        raise failure
    monkeypatch.setattr(main, "get_video_details", provider)
    response = client.post("/v1/analyses", json={"url": "https://youtu.be/abcdefghijk"}, headers=headers)
    assert response.status_code == status
    assert "secret" not in response.text


def test_missing_video(monkeypatch):
    monkeypatch.setattr(main, "get_video_details", lambda _: None)
    assert client.post("/v1/analyses", json={"url": "https://youtu.be/abcdefghijk"}, headers=headers).status_code == 404
