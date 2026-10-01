# Creator Memory PostgreSQL storage

This private development slice adds PostgreSQL beneath the recovered Creator Memory service. Report composition, normalization, aggregation, experiment states and reconstruction remain unchanged. SQLite remains the default. No existing database is automatically copied, switched or deleted.

## Configure and initialize

Install `requirements-web.txt`. Set `STRATIFY_MEMORY_DATABASE_URL` in the FastAPI environment to a PostgreSQL connection URL; keep it server-side and out of source control. Use a dedicated empty database/schema and an appropriately restricted database role. Bootstrap requires schema creation privileges; runtime requires access to the created tables. Remote connections should use the deployment's certificate-verified TLS configuration.

Run `python -m tools.migrate_memory_postgres` to explicitly initialize schema version 1. API requests do not run DDL. Then restart FastAPI with the URL configured. When the URL is absent, the existing `STRATIFY_MEMORY_DB` SQLite path remains in use. Explicit Python `database_path` arguments continue to select SQLite for compatibility and isolated tests. A configured but unavailable/unsupported PostgreSQL backend fails rather than silently saving somewhere else. Service diagnostics omit the connection URL.

## Copy existing SQLite memory

Back up the SQLite store and stop writes while copying/cutting over. Initialize the empty PostgreSQL target, then run:

```bash
python -m tools.migrate_memory_postgres --source /absolute/path/creator_memory.db
```

The source opens read-only with a consistent snapshot. The target copy holds table locks and runs in one transaction, refuses a populated target, preserves IDs and serialized report payloads, and compares all copied rows to the source before commit. Failure rolls back the copied records. The source is never modified. Copy does not enable PostgreSQL by itself: configure the API URL and restart only after checking reports/history/experiment states. To return to SQLite, unset the URL; PostgreSQL changes made after cutover are not automatically copied back. Do not alternate stores while writes are active.

## Boundaries and validation

PostgreSQL uses the same version-1 relational layout and JSON-as-text contracts as SQLite, with double precision duration values. Atomic upsert handles concurrent content-identity saves without creating duplicate video projects. Analyses and experiments are committed together. PostgreSQL revisions use `(created_at, id)`, matching the existing history list; this deliberately avoids SQLite-only `rowid`.

The dedicated `postgres` CI job uses a disposable PostgreSQL 16 database. Tests cover profile/save/reopen, revisions with identical timestamps, explicit experiment results/notes, project-delete cascades, read-only SQLite copy and overwrite refusal, fail-closed configuration/schema behavior and concurrent identity saves. Local test runs skip these checks unless `STRATIFY_TEST_POSTGRES_URL` is set. That variable must point only to a disposable test database: the fixtures truncate Creator Memory tables.

This remains service-token-protected, single-profile private development. It does not add user authentication/tenant isolation, connection pooling, a migration framework for future schema versions, public media workers, deployment or a production cutover. PostgreSQL and SQLite have not been automatically switched for any existing user data.
