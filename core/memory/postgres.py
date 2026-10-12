"""Opt-in PostgreSQL storage adapter; recovered memory contracts remain unchanged."""
import json
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

from core.memory.repository import MemoryRepository
from core.memory.schema import DDL, SCHEMA_VERSION, UnsupportedSchemaVersion


class PostgresConnection:
    """Adapt repository-owned parameterized SQL and transaction contexts only."""
    def __init__(self, connection):
        self.raw = connection
        self.transaction = None

    def execute(self, sql, values=()):
        return self.raw.execute(sql.replace('?', '%s'), values)

    def __enter__(self):
        self.transaction = self.raw.transaction()
        self.transaction.__enter__()
        return self

    def __exit__(self, *args):
        return self.transaction.__exit__(*args)


def open_database(url):
    if not url.startswith(('postgresql://', 'postgres://')):
        raise ValueError('Creator Memory requires a PostgreSQL URL.')
    return psycopg.connect(url, autocommit=True, row_factory=dict_row,
                           connect_timeout=5, options='-c statement_timeout=10000 -c lock_timeout=5000')


def initialize_postgres(url, now):
    """Explicit schema setup, never implicitly run by an API request."""
    with open_database(url) as connection, connection.transaction():
        # Serialize initial schema creation across bootstrap processes.
        connection.execute('SELECT pg_advisory_xact_lock(74183001)')
        existing = connection.execute("SELECT to_regclass('memory_metadata') present").fetchone()
        if existing['present']:
            validate_schema(connection)
        for statement in DDL.replace('duration_seconds REAL', 'duration_seconds DOUBLE PRECISION').split(';'):
            if statement.strip():
                connection.execute(statement)
        connection.execute('''INSERT INTO memory_metadata(singleton,schema_version,created_at,updated_at)
            VALUES(1,%s,%s,%s) ON CONFLICT(singleton) DO NOTHING''', (SCHEMA_VERSION, now, now))


def validate_schema(connection):
    exists = connection.execute("SELECT to_regclass('memory_metadata') present").fetchone()
    if not exists['present']:
        raise UnsupportedSchemaVersion('Initialize the PostgreSQL Creator Memory schema before use.')
    version = connection.execute('SELECT schema_version FROM memory_metadata WHERE singleton=1').fetchone()
    if not version or version['schema_version'] != SCHEMA_VERSION:
        raise UnsupportedSchemaVersion('PostgreSQL Creator Memory schema version is not supported.')


class PostgresMemoryRepository(MemoryRepository):
    def __init__(self, url, now):
        self.url, self.now = url, now
        with open_database(url) as connection:
            validate_schema(connection)

    @contextmanager
    def connection(self):
        with open_database(self.url) as connection:
            yield PostgresConnection(connection)

    def analysis_for_reopen(self, analysis_id):
        with self.connection() as connection:
            row = connection.execute('''SELECT ranked.*,v.title video_title,v.source_type video_source_type
                FROM (SELECT a.*,ROW_NUMBER() OVER (PARTITION BY video_id ORDER BY created_at,id) revision
                      FROM analyses a) ranked JOIN videos v ON v.id=ranked.video_id WHERE ranked.id=?''',
                (analysis_id,)).fetchone()
        if not row:
            return None, {'analysis_id': analysis_id, 'error': 'missing_analysis'}
        metadata = {'title': row.pop('video_title'), 'source_type': row.pop('video_source_type'),
                    'revision': row.pop('revision')}
        try:
            return self._analysis_from_row(row), metadata
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            return None, {**metadata, 'analysis_id': analysis_id, 'error': str(exc)}

    def resolve_video(self, item):
        names = ('id','channel_id','external_video_id','source_url','title','created_at','analyzed_at',
                 'source_type','analysis_status','published_at','thumbnail_url','duration_seconds','source_fingerprint')
        if item.external_video_id:
            conflict = '(channel_id,external_video_id) WHERE external_video_id IS NOT NULL'
        elif item.source_fingerprint:
            conflict = '(channel_id,source_fingerprint) WHERE source_fingerprint IS NOT NULL'
        else:
            conflict = '(id)'
        with self.connection() as connection, connection:
            row = connection.execute(f'''INSERT INTO videos({','.join(names)})
                VALUES({','.join('?' for _ in names)}) ON CONFLICT {conflict} DO UPDATE
                SET title=COALESCE(excluded.title,videos.title),source_url=COALESCE(excluded.source_url,videos.source_url),
                    analyzed_at=excluded.analyzed_at,analysis_status=excluded.analysis_status RETURNING id''',
                tuple(getattr(item, name) for name in names)).fetchone()
        return row['id'], 'new_project' if row['id'] == item.id else 'existing_project_new_revision'
