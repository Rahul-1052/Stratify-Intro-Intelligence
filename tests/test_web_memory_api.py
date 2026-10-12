import pytest
from fastapi.testclient import TestClient

from api import main
from tests.test_creator_memory import report as memory_report

TOKEN = "test-service-token-that-is-long-enough"
client = TestClient(main.app)
headers = {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture(autouse=True)
def environment(monkeypatch, tmp_path):
    monkeypatch.setenv("STRATIFY_SERVICE_TOKEN", TOKEN)
    monkeypatch.setenv("STRATIFY_MEMORY_DB", str(tmp_path / "creator-memory.db"))


def test_memory_requires_profile_before_save():
    response = client.post("/v1/memory/analyses", headers=headers, json={
        "report": memory_report(), "upload_name": "clip.mp4", "content_digest": "a" * 64,
    })
    assert response.status_code == 409
    assert "profile" in response.json()["detail"].lower()


def test_memory_save_reopen_and_revision_without_pipeline_rerun():
    profile = client.post("/v1/memory/profile", headers=headers, json={
        "display_name": "Creator", "channel_name": "Channel",
    })
    assert profile.status_code == 200
    payload = {"report": memory_report(), "upload_name": "clip.mp4", "content_digest": "b" * 64}
    first = client.post("/v1/memory/analyses", headers=headers, json=payload)
    second = client.post("/v1/memory/analyses", headers=headers, json=payload)
    assert first.status_code == second.status_code == 200
    assert first.json()["video_id"] == second.json()["video_id"]
    assert second.json()["decision"] == "existing_project_new_revision"

    opened = client.get(f"/v1/memory/analyses/{first.json()['analysis_id']}", headers=headers)
    assert opened.status_code == 200
    assert opened.json()["status"] == "reconstructed"
    assert opened.json()["diagnostics"]["analysis_pipeline_rerun"] is False

    dashboard = client.get("/v1/memory", headers=headers).json()
    assert dashboard["counts"] == {"videos": 1, "analyses": 2}
    assert dashboard["history"][0]["revision_count"] == 2


def test_experiment_tracking_is_explicit_creator_state():
    client.post("/v1/memory/profile", headers=headers, json={"display_name": "Creator", "channel_name": "Channel"})
    saved = client.post("/v1/memory/analyses", headers=headers, json={
        "report": memory_report(experiments=1), "upload_name": "clip.mp4", "content_digest": "c" * 64,
    }).json()
    experiment = saved["dashboard"]["experiments"][0]
    assert experiment["status"] == "suggested"
    assert experiment["result_summary"] == ""

    updated = client.patch(f"/v1/memory/experiments/{experiment['id']}", headers=headers, json={
        "status": "completed", "result_summary": "Entered by creator after the test.",
    })
    assert updated.status_code == 200
    item = updated.json()["experiments"][0]
    assert item["status"] == "completed"
    assert item["result_summary"] == "Entered by creator after the test."


def test_memory_rejects_unapproved_experiment_status():
    response = client.patch("/v1/memory/experiments/not-found", headers=headers, json={"status": "won"})
    assert response.status_code == 422
