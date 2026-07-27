# Observation Accuracy V1

## Purpose

Observation Accuracy V1 measures whether Stratify's structured observations match
machine-readable expectations for synthetic golden-dataset clips. It evaluates
saved reports after analysis and never supplies expectations to the observation
pipeline.

> Synthetic benchmark accuracy does not prove real-world creator-video accuracy.

## Architecture

The golden manifest defines expectations. Existing Stratify reports provide
timestamped frame observations and Intelligence V3 measurements. A post-analysis
adapter normalizes those fields, a comparison engine scores each expectation,
and deterministic JSON and Markdown exports are written beneath the saved run.
Creator-facing report prose is never parsed.

## Manifest expectation schema

Each synthetic case may include `expected_observations`:

```json
{
  "metric": "scene_change_count",
  "expected_value": 5,
  "comparison": "numeric_min",
  "tolerance": 0,
  "weight": 1.5,
  "required": true,
  "description": "Frequent hard scene changes should be observed."
}
```

Cases without expectations remain compatible and are marked unevaluable.

## Normalized metrics

Supported structured metrics cover visual energy, mean/maximum motion, meaningful
and scene-change counts, scene continuity, cadence, novelty, subject introduction
and persistence, text introduction and persistence, information introduction,
visual density, visible-element count, and focal stability. Every value records
its structured source, confidence, timestamp where applicable, and evidence.

## Comparison modes

- `exact`: categorical equality
- `ordered`: ordered category distance with optional half-credit tolerance
- `numeric_min` / `numeric_max`: inclusive numeric thresholds
- `numeric_range`: inclusive two-value range
- `boolean`: boolean equality
- `temporal_before` / `temporal_after`: inclusive timestamp thresholds
- `relative`: explicit `gt`, `gte`, `lt`, or `lte` operator
- `presence`: structured value must be present or absent

Unsupported modes fail explicitly. Missing observations are unavailable, not
incorrect.

## Scoring and confidence

Exact matches score 1.0, accepted ordered deviations score 0.5, and mismatches
score 0.0. Unavailable observations are excluded from accuracy but counted in
evaluability and required-metric coverage. Confidence is reported separately and
never multiplied into correctness.

Case statuses use centralized thresholds: excellent requires at least 90%
accuracy and 90% coverage; good requires 75% accuracy; needs-review requires 50%;
lower scores are poor; no evaluated metrics is unevaluable.

## Commands

Evaluate without rerunning analysis:

```powershell
.\.venv\Scripts\python.exe tools\evaluate_golden_run.py --run-id <run-id>
.\.venv\Scripts\python.exe tools\evaluate_golden_run.py --latest
```

Run and immediately evaluate selected clips:

```powershell
.\.venv\Scripts\python.exe tools\run_golden_dataset.py --no-network --limit 3 --evaluate
```

## Output files

Each run receives:

```text
accuracy/
  summary.json
  summary.md
  cases/
    <case-id>.json
```

The summary reports accuracy, confidence, coverage, case results, metric rankings,
and detailed mismatches with structured evidence sources.

## Interpretation and limitations

Accuracy measures agreement with explicitly encoded synthetic behavior. Coverage
shows how much could be evaluated. A high score with low coverage is not strong
validation. Synthetic shapes may exercise detectors differently from real people,
natural scenes, typography, camera motion, and compression.

## Adding future cases

Add only expectations supported by normalized structured fields. State comparison,
weight, and whether the metric is required. If a concept is unavailable, extend
the adapter transparently from existing structured observations or leave it
unevaluable. Do not parse Creator report prose.

## Avoiding benchmark leakage

Expected labels are loaded only after a report has been saved. Never pass case
expectations, filenames, case IDs, or expected values into video analysis,
benchmark discovery, evidence qualification, or report generation.
