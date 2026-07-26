# Creator Memory V1

Creator Memory is a downstream, local-only layer:

`analysis pipeline → Creator report → normalized record → SQLite history → deterministic aggregation/comparison`

It does not change current observations, Creative Structure, Creative Understanding, reasoning, qualification, or experiments. The default database is `.stratify_data/creator_memory.db`, configurable with `STRATIFY_MEMORY_DB`. Schema version 1 is initialized idempotently; a newer unknown version fails without mutation.

Creator, channel, video/project, analysis revision, and experiment records are accessed only through `MemoryRepository` and `CreatorMemoryService`. SQLite foreign keys are enabled. Videos are deduplicated by normalized external ID when present or a deterministic local-source fingerprint; titles never identify projects. Reanalysis creates a new analysis revision.

Aggregation uses named thresholds in `core/memory/aggregator.py`. One report is history, two matches are only an emerging tendency, and stable language requires at least four observations with a 70% share. Unknown and limited evidence is excluded. Contradiction lowers confidence. No pattern is described as successful or preferred without outcome evidence.

The database stores normalized reports and creator-entered notes, not videos, frames, cache data, secrets, or API keys. It is not claimed to be encrypted or cloud-synchronized. JSON export is portable and deterministic in ordering; validation exists, but V1 does not blindly import or replace a database. Project deletion and full reset rely on foreign-key cascades and explicit UI confirmation.

Feature availability is centralized through `ProductAccess.creator_memory` (`enabled`, `preview`, or `disabled`; local beta defaults to enabled). SQLite is isolated behind repository/service boundaries so a future cloud repository can implement the same product operations without changing analysis logic.

Saved analysis revisions reopen through `core.memory.reconstruction`, which adapts the normalized record back to the existing Creator report contract without acquisition or analysis. The adapter preserves saved snapshots, confidence, limitations, opportunities, abstentions, and experiments. Fields not retained by V1 normalization, such as the original strength list and raw diagnostic evidence, remain unavailable rather than being inferred. Older partial or malformed records are isolated and shown through a normalized-summary fallback; technical reconstruction diagnostics remain Builder-only.
