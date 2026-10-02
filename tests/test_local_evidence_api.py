import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from api import main
from api.local_evidence import analyze_owned_intro

TOKEN = "private-test-token-that-is-long-enough"
client = TestClient(main.app)
headers = {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture(autouse=True)
def private_configuration(monkeypatch):
    monkeypatch.setenv("STRATIFY_SERVICE_TOKEN", TOKEN)
    monkeypatch.setenv("STRATIFY_LOCAL_MEDIA_ENABLED", "1")


@pytest.fixture
def clip(tmp_path):
    path = tmp_path / "owned.mp4"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 10, (160, 120))
    assert writer.isOpened()
    for index in range(120):
        writer.write(np.full((120, 160, 3), 25 if index < 20 else 220, dtype=np.uint8))
    writer.release()
    return path


def test_real_pixel_pipeline(clip, tmp_path, monkeypatch):
    import requests
    monkeypatch.setattr(requests, "post", lambda *a, **k: pytest.fail("Unexpected provider call"))
    evidence = analyze_owned_intro(clip, tmp_path / "frames")
    assert evidence["sample_count"] == 20
    assert evidence["intro_seconds"] == 10
    assert evidence["samples"][0]["brightness_score"] < 40
    assert evidence["samples"][4]["brightness_score"] > 190
    assert evidence["samples"][4]["motion_score"] > 150
    assert evidence["recommendation"] is None
    assert evidence["asset_sha256"] == hashlib.sha256(clip.read_bytes()).hexdigest()
    assert "frame_path" not in json.dumps(evidence)


def test_upload_runs_engine_and_cleans_files(clip, monkeypatch):
    import api.local_evidence as adapter
    original = adapter.analyze_owned_intro
    paths = []
    def tracked(path, frame_directory):
        paths.extend([path, frame_directory])
        return original(path, frame_directory)
    monkeypatch.setattr(adapter, "analyze_owned_intro", tracked)
    response = client.post("/v1/intro-evidence", headers=headers,
                           files={"file": ("../../escaped.mp4", clip.read_bytes(), "video/mp4")}, data={"owned": "true"})
    assert response.status_code == 200
    assert response.json()["sample_count"] == 20
    assert all(not path.exists() for path in paths)


def test_permission_required():
    response = client.post("/v1/intro-evidence", headers=headers, files={"file": ("x.mp4", b"x")})
    assert response.status_code == 422


def test_disabled_by_default(monkeypatch):
    monkeypatch.delenv("STRATIFY_LOCAL_MEDIA_ENABLED")
    assert client.post("/v1/intro-evidence", headers=headers, files={"file": ("x.mp4", b"x")}, data={"owned": "true"}).status_code == 503


@pytest.mark.parametrize("content", [b"", b"not a video"])
def test_corrupt_or_empty_input(content):
    response = client.post("/v1/intro-evidence", headers=headers,
                           files={"file": ("x.mp4", content)}, data={"owned": "true"})
    assert response.status_code == 422
    assert "stratify-intro-" not in response.text


def test_size_limit():
    response = client.post("/v1/intro-evidence", headers=headers,
                           files={"file": ("x.mp4", b"x" * (20 * 1024 * 1024 + 1))}, data={"owned": "true"})
    assert response.status_code == 413


def test_authentication_required():
    assert client.post("/v1/intro-evidence", files={"file": ("x.mp4", b"x")}, data={"owned": "true"}).status_code == 401
