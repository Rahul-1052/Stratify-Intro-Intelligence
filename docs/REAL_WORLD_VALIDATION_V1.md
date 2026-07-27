# Real-World Validation V1

## Purpose

Real-World Validation V1 measures Stratify's structured visual observations
against annotations created before analysis. It supplements, but does not alter
or replace, the synthetic golden dataset. It makes no product or outcome claims.

## Manifest

`validation/real_world/manifest.json` contains `schema_version`,
`validation_version`, and `cases`. Every case contains:

- `case_id`, `title`, and `category`
- `clip_path`, `source_type`, and measured `duration_seconds`
- `enabled` and `notes`
- `expectations`, `annotation_status`, and `annotator`
- `created_at`, `expectations_created_at`, and `analysis_started_at`
- `expectations_hash`

Each expectation follows Observation Accuracy V1:

```json
{
  "metric": "subject_initially_present",
  "expected_value": true,
  "comparison": "boolean",
  "tolerance": 0,
  "weight": 1,
  "required": false,
  "description": "A person is visible in the first sample."
}
```

Supported comparisons are `numeric_min`, `numeric_max`, `numeric_range`,
`exact`, `ordered`, `boolean`, `temporal_before`, `temporal_after`, and
`presence` (plus the existing `relative` mode). Use `exact` for categorical
values. Presence accepts `present` or `absent`.

## Blind locking

Annotations are entered manually, then locked:

```powershell
python tools/create_real_world_case.py --lock-case rw-001 --annotator "YOUR NAME"
```

Locking records the annotation timestamp and a SHA-256 hash of canonical JSON.
The runner verifies the hash before setting `analysis_started_at`. A changed,
unlocked, or unstamped expectation set stops the run. Re-running a previously
started case is allowed only while its hash still matches.

The observation pipeline receives only the resolved clip path and the network
policy. Expectations are loaded only by the evaluation layer after the raw
report returns.

## Commands

Create and copy a clip:

```powershell
python tools/create_real_world_case.py --case-id rw-001 --title "Static talking-head intro" --category education --clip "C:\path\intro.mp4"
```

Reference a clip without copying:

```powershell
python tools/create_real_world_case.py --case-id rw-002 --title "Podcast intro" --category podcast --clip "C:\path\podcast.mp4" --reference
```

Run one case, up to ten enabled cases, or explicitly request evaluation:

```powershell
python tools/run_real_world_validation.py --case rw-001
python tools/run_real_world_validation.py --limit 10
python tools/run_real_world_validation.py --evaluate
```

Evaluation is always included; `--evaluate` is accepted as an explicit,
self-documenting request. Network access is disabled unless
`--allow-network` is provided.

## Outputs

Each run is stored under `validation/real_world/runs/<run-id>/`:

- `run.json`: run provenance, timestamps, network policy, clip checks, coverage
- `cases/<case-id>.json`: untouched pipeline output
- `accuracy/summary.json` and `accuracy/summary.md`
- `accuracy/cases/<case-id>.json` and `.md`

Manual annotation coverage is the number of supplied expectations divided by
the 14 recommended metric slots across selected cases. Evaluability coverage
reports how many supplied expectations had a structured observation. These are
separate so absent annotations are never presented as pipeline failures and
unavailable observations are never counted as matches.

## Recommended first 10 clips

Supply one lawful local intro clip in each category:

1. Static talking head
2. Podcast
3. Educational explainer
4. Finance commentary
5. Vlog
6. Gaming
7. Documentary montage
8. Technology review
9. Screen recording
10. Product demonstration

Prefer short clips with known provenance and permission for local analysis.
Do not download copyrighted videos automatically. Record ambiguity and unusual
editing in `notes`; omit expectations that a human annotator cannot support.

## Limitations

- Accuracy is limited by manual annotation quality and sample diversity.
- The workflow evaluates observations, not retention, causality, or performance.
- Frame sampling can make boundary timestamps approximate.
- Referenced clips can become unavailable if moved.
- The default runner uses the first 15 seconds and one-frame-per-second sampling,
  matching the current intro pipeline invocation.
- `--allow-network` only removes this workflow's offline guard; it does not
  guarantee that external services are configured or available.
