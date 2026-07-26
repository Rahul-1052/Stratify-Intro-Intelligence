# Stratify Product Validation V1

## Purpose

Product Validation is a Builder-only, local workflow for examining whether existing Creator reports are accurate, specific, trustworthy, and actionable. It does not add intelligence or tune production behavior.

## Architecture and storage

`tools/run_product_validation.py` wraps the existing Intro Intelligence module and Creator report payload. Typed contracts, objective checks, storage, fixtures, and exports live in `core/product_validation`. The review board lives in `ui/product_validation.py` and reuses `ui.report.render_report`.

Artifacts default to `.stratify_validation/` with separate `runs`, `reports`, `reviews`, and `exports` directories. Writes are atomic. This directory is ignored by Git and never shares Creator Memory’s database.

## Manifest

Copy `validation/video_manifest.example.json` to a local ignored manifest. Supply real URLs or local-source metadata, enable only intended cases, and keep niches as review metadata—not analysis instructions. The checked-in example deliberately contains no fabricated URLs.

## Commands

```powershell
.\.venv\Scripts\python.exe tools\run_product_validation.py --fixture-only --no-network --limit 10
.\.venv\Scripts\python.exe tools\run_product_validation.py --manifest .stratify_validation\first-ten.json --limit 10 --skip-existing
.\.venv\Scripts\python.exe tools\run_product_validation.py --manifest .stratify_validation\first-ten.json --resume latest
.\.venv\Scripts\python.exe tools\run_product_validation.py --manifest .stratify_validation\first-ten.json --case food-01 --no-network
```

Use `--real-only` to make intent explicit, `--builder-diagnostics` to record that diagnostics were requested, and `--output` for another isolated local directory. Runs are bounded by the manifest and `--limit`; failures are recorded per case.

## Automated versus human review

Automated checks produce conservative warnings for confidence inconsistencies, repeated text, unsupported text advice, padded experiments, missing limitations or sections, unsupported performance/retention/psychology claims, generic advice, abstention conflicts, malformed experiments, and leakage-related report shape concerns. Warnings are heuristic and never confirmed defects.

All eight one-to-five scores, the usefulness decision, issue classification, notes, and “If you could change only one thing…” are human review. Blank scores mean awaiting human review. Creator interviews are not implied.

## Scoring rubric

Use 1 for unusable or misleading, 3 for mixed but usable with important caveats, and 5 for precise, well-supported, immediately useful work. Score snapshot accuracy, opportunity specificity, experiment actionability, confidence believability, clarity, novelty, creator usefulness, and likelihood of acting independently.

Issue categories are observation, interpretation, recommendation, trust, UX, product, acquisition, evidence limitation, and infrastructure. Severity expresses review priority, not confirmed defect status.

## Hall of Failures and exports

Builder Mode groups reviewed issues only when normalized category, section, and short description match. It does not merge merely similar wording. Exports include the complete run JSON, human-review CSV, issue CSV, summary JSON, and Markdown report with provenance and limitations.

## Safe resume, privacy, and limitations

Each case is checkpointed. `--resume` or `--skip-existing` reuses completed records and avoids repeated acquisition. No retry loop exists. Payloads may contain video metadata and report evidence, so keep `.stratify_validation` local and review it before sharing.

Fixtures validate the system, not creators or real videos. Automated checks cannot establish factual report accuracy. Local cached clips may lack trustworthy title, creator, niche, or source provenance.

## First ten-video sprint

1. Create `.stratify_validation\first-ten.json` from the example.
2. Add ten diverse, consented or otherwise appropriate sources and metadata.
3. Run the bounded command above.
4. Open Stratify in Builder Mode and review every case.
5. Save the required one-change answer, scores, decision, notes, and any issues.
6. Export the Markdown report and inspect recurring issues before considering engine changes.

Creator interview feedback can later be added as a separate provenance field and export section. Do not mix interview feedback with automated or internal human review.
