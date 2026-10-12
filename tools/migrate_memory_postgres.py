"""Initialize PostgreSQL and optionally copy an existing SQLite memory store safely.

Usage: STRATIFY_MEMORY_DATABASE_URL=... python -m tools.migrate_memory_postgres
       ... python -m tools.migrate_memory_postgres --source /path/to/creator_memory.db
"""
import argparse
import os
import sqlite3
from pathlib import Path

from psycopg import sql
from core.memory.postgres import initialize_postgres, open_database
from core.memory.schema import SCHEMA_VERSION
from core.memory.service import utc_now

TABLES = ('creators', 'channels', 'videos', 'analyses', 'experiments')


def copy_sqlite(source, url):
    source = Path(source).resolve(strict=True)
    # Read-only access, with a consistent snapshot; the original file is never changed.
    with sqlite3.connect(source.as_uri() + '?mode=ro', uri=True) as old:
        old.row_factory = sqlite3.Row
        old.execute('BEGIN')
        version = old.execute('SELECT schema_version FROM memory_metadata WHERE singleton=1').fetchone()
        if not version or version['schema_version'] != SCHEMA_VERSION:
            raise ValueError('Source Creator Memory schema is unsupported.')
        with open_database(url) as target, target.transaction():
            target.execute('LOCK TABLE creators,channels,videos,analyses,experiments IN ACCESS EXCLUSIVE MODE')
            for table in TABLES:
                if target.execute(sql.SQL('SELECT COUNT(*) count FROM {}').format(sql.Identifier(table))).fetchone()['count']:
                    raise ValueError('Copy requires an empty target. Existing PostgreSQL records were not changed.')
            counts = {}
            for table in TABLES:
                rows = old.execute(f'SELECT * FROM {table} ORDER BY id').fetchall()
                counts[table] = len(rows)
                for row in rows:
                    keys = row.keys()
                    target.execute(sql.SQL('INSERT INTO {} ({}) VALUES ({})').format(
                        sql.Identifier(table), sql.SQL(',').join(map(sql.Identifier, keys)),
                        sql.SQL(',').join(sql.Placeholder() for _ in keys)), tuple(row))
                copied = target.execute(sql.SQL('SELECT * FROM {} ORDER BY id').format(sql.Identifier(table))).fetchall()
                if copied != [dict(row) for row in rows]:
                    raise ValueError('Copied data did not match the source. Copy rolled back.')
            return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path)
    args = parser.parse_args()
    url = os.environ.get('STRATIFY_MEMORY_DATABASE_URL', '')
    try:
        initialize_postgres(url, utc_now())
        print(copy_sqlite(args.source, url) if args.source else 'PostgreSQL Creator Memory schema initialized.')
    except Exception:
        # Database errors can include connection credentials. Keep CLI output safe.
        raise SystemExit('Creator Memory setup/copy failed. Check configuration, schema and empty-target requirements.') from None


if __name__ == '__main__':
    main()
