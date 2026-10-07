"""Real PostgreSQL contract checks. Run only against the disposable CI test database."""
import os
from concurrent.futures import ThreadPoolExecutor

import pytest

from core.memory.postgres import initialize_postgres, open_database, PostgresMemoryRepository
from core.memory.schema import UnsupportedSchemaVersion
from core.memory.service import CreatorMemoryService, utc_now
from stratify_platform.projects import create_project
from tests.test_creator_memory import report
from tools.migrate_memory_postgres import copy_sqlite

URL = os.getenv('STRATIFY_TEST_POSTGRES_URL')
pytestmark = pytest.mark.skipif(not URL, reason='Requires a dedicated PostgreSQL test database')


@pytest.fixture(autouse=True)
def database(monkeypatch):
    initialize_postgres(URL, utc_now())
    with open_database(URL) as connection:
        connection.execute('TRUNCATE creators CASCADE')
    monkeypatch.setenv('STRATIFY_MEMORY_DATABASE_URL', URL)
    yield
    with open_database(URL) as connection:
        connection.execute('TRUNCATE creators CASCADE')
        connection.execute('UPDATE memory_metadata SET schema_version=1 WHERE singleton=1')


def test_service_save_reopen_revision_and_experiment():
    service = CreatorMemoryService(now=lambda: '2026-01-01T00:00:00+00:00')
    assert isinstance(service.repository, PostgresMemoryRepository)
    assert 'database_path' not in service.diagnostics
    service.save_profile('Creator', 'Channel')
    project = create_project(upload_name='clip.mp4', title='clip')
    first = service.save_report(report(), project, content_digest='a' * 64)
    second = service.save_report(report(), project, content_digest='a' * 64)
    assert first['video_id'] == second['video_id']
    assert second['decision'] == 'existing_project_new_revision'
    dashboard = service.dashboard()
    assert dashboard['counts'] == {'videos': 1, 'analyses': 2}
    for revision in dashboard['history'][0]['revisions']:
        opened = service.reopen_analysis(revision['id'])
        assert opened['status'] == 'reconstructed'
        assert opened['diagnostics']['analysis_pipeline_rerun'] is False
        assert opened['report']['saved_history']['revision'] == revision['revision']
    experiment = dashboard['experiments'][0]
    service.update_experiment(experiment.id, status='completed', result_summary='Creator-entered result')
    updated = next(item for item in service.dashboard()['experiments'] if item.id == experiment.id)
    assert updated.result_summary == 'Creator-entered result'
    assert updated.status == 'completed'
    service.repository.delete_project(first['video_id'])
    assert service.dashboard()['counts'] == {'videos': 0, 'analyses': 0}
    assert service.dashboard()['experiments'] == []


def test_copy_preserves_ids_payloads_states_and_refuses_overwrite(tmp_path):
    source = tmp_path / 'memory.db'
    local = CreatorMemoryService(source)
    local.save_profile('Creator', 'Channel')
    saved = local.save_report(report(), create_project(upload_name='clip.mp4'), content_digest='b' * 64)
    experiment = local.dashboard()['experiments'][0]
    local.update_experiment(experiment.id, status='running', creator_notes='Preserve this note')
    before = source.read_bytes()
    counts = copy_sqlite(source, URL)
    assert counts['analyses'] == 1
    pg = CreatorMemoryService()
    assert pg.repository.export(pg.profile()['id']) == local.repository.export(local.profile()['id'])
    assert pg.reopen_analysis(saved['analysis_id'])['status'] == 'reconstructed'
    with pytest.raises(ValueError, match='empty target'):
        copy_sqlite(source, URL)
    assert source.read_bytes() == before


def test_unavailable_database_does_not_fall_back(monkeypatch):
    monkeypatch.setenv('STRATIFY_MEMORY_DATABASE_URL', 'invalid-url')
    with pytest.raises(ValueError):
        CreatorMemoryService()


def test_future_schema_rejected():
    with open_database(URL) as connection:
        connection.execute('UPDATE memory_metadata SET schema_version=999 WHERE singleton=1')
    with pytest.raises(UnsupportedSchemaVersion):
        CreatorMemoryService()


def test_concurrent_content_identity_keeps_one_project():
    CreatorMemoryService().save_profile('Creator', 'Channel')
    def save(_):
        return CreatorMemoryService().save_report(report(), create_project(upload_name='clip.mp4'), content_digest='c' * 64)
    with ThreadPoolExecutor(max_workers=4) as pool:
        saved = list(pool.map(save, range(4)))
    assert len({item['video_id'] for item in saved}) == 1
    assert CreatorMemoryService().dashboard()['counts'] == {'videos': 1, 'analyses': 4}
