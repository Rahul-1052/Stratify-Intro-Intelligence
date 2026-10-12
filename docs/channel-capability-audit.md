# Stratify channel capability audit

Audited 2026-10-01 against migration head ff4d996. Static code inspection; no live YouTube collection or new model evaluation was performed.

## Product scope

Stratify is channel-level content intelligence. Start with the creator's concern; individual videos are evidence units. Intro analysis is one module, not the product boundary. Slow pacing/branding is not inherently a defect. Plain-language answers must distinguish observations, interpretations, missing information and justified next steps. PostgreSQL stays optional. A creative assistant remains a proposal.

## Capability inventory

| Capability | Code evidence | Actual boundary / disposition |
|---|---|---|
| Channel public metadata | core/youtube_client.py:get_channel_details | Retrieves creation date, description, thumbnail URL, counts and uploads playlist. Reuse retrieval; preserve missing/hidden metrics rather than silently treating them as zero. Creation date is not proof of loyalty. |
| Recent uploads | core/youtube_client.py:get_recent_videos | Default sample is 12; single playlist page, no pagination. Not a complete channel inventory. Reuse and extend bounded collection with explicit coverage. |
| Channel context from a video | core/youtube_client.py:get_full_youtube_context; core/stratify_report.py | Video-first entrypoint obtains channel and recent uploads; active runner remains intro-oriented. Channel URL/handle intake is not demonstrated here. |
| Titles, descriptions, duration and thumbnail links | core/youtube_client.py | Metadata exists. Thumbnail URLs are not image interpretation; descriptions are not full-video transcripts. |
| Benchmark collection/qualification | core/benchmark_collector.py; core/benchmark_signature.py; core/benchmark_qualification.py | Reusable candidate/relevance/compatibility machinery. Retrieved benchmark videos are not necessarily the creator's uploads. _performance_evidence explicitly calls raw views limited and unnormalized for publish age/impressions/audience size. Do not interpret ranking as causal success. |
| Cross-analysis memory | core/memory/service.py; core/memory/aggregator.py; core/memory/comparison.py | Conservative patterns over saved opening fields; not complete-channel analytics. Multiple revisions can contribute analysis records; channel-level reporting must separate unique videos from revisions. |
| Intro findings and report | core/intelligence_v3.py; core/creator_report.py; api/local_evidence.py | Working narrow observer/report foundation. Current web path samples first 10 seconds, no audio/retention measurement. Do not infer full-video quality from it. |
| Content DNA | core/content_dna.py | Keyword rules over metadata plus repeated canned claims about audience motives/emotional repackaging. Not measured channel/audience understanding; do not migrate as factual output. |
| Growth snapshot | core/growth_snapshot.py | Views/subscriber thresholds and generic stronger-opening advice; recent_videos parameter unused. No defensible diagnosis of growth or audience familiarity. Quarantine from channel recommendations. |
| Context intelligence | core/context_intelligence.py | Returns the same audience-psychology/emotional-payoff claims regardless of input. Not evidence-backed; exclude. |
| Audience observer | core/observers/audience_observer.py | Heuristic first-time-viewer interpretation from normalized opening observations. Does not measure audience reactions. |
| Competitor intelligence | core/competitor_intelligence.py | File inspected is empty; not an implemented capability. |
| Packaging, full story/editing, audience intelligence | stratify_platform/module_registry.py | Explicitly PLANNED; only intro_intelligence has an available runner. |
| Public comment text / owner retention / traffic / click-through data | Current retrieved client and active web adapters | Not implemented in this audited path. Comment counts are not comment sentiment; public metadata cannot substitute for owner analytics. |

## Recommended first channel workflow

Creator supplies a channel identifier and one concern (plus optional goal/intent). Collect a bounded public upload sample. Show which uploads/time span were covered, which formats were included and what is unavailable. Let the creator narrow a comparable set before drawing conclusions.

First output: an evidence inventory and a direct answer to whether the available evidence can address the concern. Show sourced channel facts and sampled video records. Separate data collection failures, absent metrics and low sample coverage. Do not add generic strengths/weaknesses or assume that every question deserves an experiment.

Example concern: “Should I keep my branding?” Public metadata alone cannot settle it. Ask for intended purpose and relevant viewing evidence; observed repeated branding can be described only after actually examining those videos. Never translate channel age into audience loyalty.

## Evidence requirements

- Counts: preserve availability and collection timestamp; calculations use code.
- Packaging interpretation: inspect the actual thumbnail/title, label interpretations, allow correction.
- Channel pattern: cite unique video IDs, timestamps/fields, sample denominator and counterexamples; deduplicate saved revisions.
- Performance comparison: distinguish format/topic/duration/upload age and available exposure/traffic data. Raw views alone support a descriptive ordering, not “why it worked.”
- Audience reactions: quoted/comment-linked evidence with explicit sampling; no universal audience claim.
- Recommendations: identify the creator's concern, plausible alternatives, supporting evidence and missing evidence; “keep it” and “cannot conclude” are valid outcomes.

## Next implementation scope

1. Channel identifier resolution and bounded upload inventory, preserving missing values and collection coverage.
2. Creator concern/intent capture and a channel workspace showing facts rather than invented diagnosis.
3. Deterministic validation fixtures for hidden counts, unavailable data, small/mixed samples, pagination limits and repeated revisions.
4. Only then add the acquisition/analysis needed for the selected concern, such as packaging inspection or authorized audience evidence.

No new infrastructure, model training, creative assistant, automatic research crawling, or blanket migration of legacy prose is included in this milestone. Existing recovered engines remain intact. This audit does not claim complete-channel analysis has been implemented.
