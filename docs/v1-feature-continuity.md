# V1 feature continuity plan

Reviewed 2026-10-06 UTC. Static source review, not a runtime certification.

Legacy source: Rahul-1052/Stratify main at eb382aa9d84da16a9927ce8f6d42e31ebfc288dc.
Current source: Rahul-1052/Stratify-Intro-Intelligence feat/web-beta-integration at a26535c49d72ed8f58cad4ff32d566506fb3a1a5.

## Product commitment

One whole-channel product. Creator concerns drive investigations; videos are evidence units. Opening analysis is optional. Preserve useful V1 capabilities, but rebuild unsupported conclusions instead of copying legacy answers. This checklist is a migration backlog, not a claim that all features are available.

## Feature checklist

| V1 capability and source | Current web status | Carry-forward decision / acceptance requirement |
| --- | --- | --- |
| Single Video Analysis: app.py get_video_details, get_video_ai_insights; utils/analyzer.py | Public video metadata and optional owned opening observations exist; full-video insights not migrated. | Preserve video drill-down within channel investigations. Cite inspected content and missing evidence; metadata cannot establish viewer experience or causal performance drivers. |
| Channel Intelligence: app.py get_recent_channel_videos and Channel Intelligence tab | Bounded public channel inventory up to 100 upload entries, dates, missing values and coverage; selected lifetime-view comparisons. | Preserve channel overview. Restore useful charts with sample scope and collection time. Do not call snapshot counts subscriber growth, returning-viewer behavior or complete channel health. |
| Creator Scorecard: app.py calculate_creator_scorecard | Legacy six-score grade not exposed in current channel workspace. | Redesign around measurable signals with definitions and limitations. No overall health grade until validated. Upload cadence is descriptive, not a universal three-uploads-per-week target. |
| Growth Diagnosis: app.py calculate_growth_diagnosis | No equivalent broad diagnosis implemented. | Preserve the goal of prioritizing concerns. Replace fixed-threshold causal labels with evidence-qualified hypotheses and justified next evidence/action. |
| Video Comparison: app.py Video Comparison tab | Manual groups, provisional date proposals, public median views; optional user-entered same-window analytics. | Preserve and extend. Comparable content, formats, shared material, time windows and metric definitions must be considered. Lifetime views remain descriptive. |
| Growth Strategy Generator: app.py get_growth_strategy, build_smart_growth_fallback | Not migrated as a channel strategy generator. | Preserve positioning, opportunities and planning. Recommendations cite supporting video evidence and alternatives. Ideas are proposals, never proof of future success. Failed AI calls must not turn generic fallback advice into findings. |
| Channel DNA: app.py get_channel_dna, build_smart_dna_fallback; utils/analyzer.py generate_channel_dna | No verified channel-content/audience synthesis in active web workspace. Experimental caption grouping is not Channel DNA. | Preserve channel identity and content-pattern exploration. Evidence from reviewed content with counterexamples and coverage; audience motives need audience evidence or explicit hypothesis labels. |
| Next-video ideas: app.py growth strategy output specific_video_ideas | Not implemented in current web workspace. | Restore as creative proposals connected to creator goals and supported patterns; keep distinction between creative suggestion and observed fact. |
| PDF exports: app.py make_pdf_report and build_video_report/build_channel_report/build_strategy_report/build_dna_report | V1 PDF exports not wired into the web UI. | Restore after report contract settles. Export the same findings, source links, collection dates, selection, limitations and version as the screen. |
| Transcript context: app.py get_transcript; utils/transcript_utils.py | Optional bounded English public-caption retrieval; unavailable captions explicitly fall back to date selection. | Preserve content evidence, expand languages deliberately. No transcript fabrication and no claim of full-video visual verification from captions. |
| Engagement/performance/viral scores: app.py calculate_engagement_rate, calculate_video_score, calculate_viral_score | Public likes/comments/views exposed; legacy scores not migrated. | Preserve transparent descriptive ratios where counts are available. Do not relabel arbitrary weighted formulas as validated quality, virality or future growth. |

## New capabilities beyond V1

- Starter questions and editable focus suggestions: implemented for specific recognized question wording; general question understanding remains unfinished.
- Creator Memory: profile, saved owned-video reports/revisions and experiment statuses exist. Channel investigation persistence is not implied by this.
- Qualified opening observations/report: optional narrow evidence tool, not whole-video diagnosis.
- Creative agent with image generation/video editing: proposed future feature, not recovered V1 implementation.

## Specific legacy weaknesses found

1. calculate_creator_scorecard scores packaging using title length, digits and selected words without inspecting thumbnails or CTR.
2. Its content_depth_score uses comment-to-like ratio; that does not measure content depth.
3. Its momentum compares newest/oldest lifetime totals without equal exposure windows.
4. calculate_growth_diagnosis infers subscribers not returning from average public views versus subscribers; those counts do not identify returning viewers.
5. Diagnosis confidence is computed from threshold severity rather than calibrated predictive evidence.
6. detect_video_formats uses title keywords, including “shorts”; titles cannot verify format and the declared Compilation category is never incremented in this function.
7. get_video_ai_insights/get_channel_dna prompts request audience motives and reasons for performance and instruct “Do not return N/A,” even when content/audience evidence is absent.
8. Growth/Channel DNA functions merge fallback prose into AI output. Provider failure must instead preserve unavailable evidence and distinguish proposed ideas from findings.

## Implementation order

1. General concern understanding and investigation contract: preserve original wording; suggest editable intent only when justified; ask one clarification for ambiguity. Define what is answerable from current evidence before generation.
2. Channel overview and content investigation: actual content evidence, sample-aware grouping, counterexamples, shared-material handling and creator correction.
3. Evidence-backed growth strategy / Channel DNA / next-video proposals using that contract; validate unsupported questions abstain and factual claims cite evidence.
4. Channel report persistence and exports; reconnect useful V1 visual comparisons to the same report contract.
5. Broader audience/packaging investigations with appropriately acquired evidence; creative-agent workspace as a separate module.

## Verification boundary

Reviewed README.md, app.py, utils/ai_utils.py and utils/analyzer.py in V1; current repository tree, channel-capability-audit.md, WEB_MIGRATION.md and creator-memory.tsx, alongside the current channel and comparison workflows inspected during implementation. README claims were checked against corresponding functions for the concerns above. No legacy or current application was executed for this audit. Current browser flows have user confirmation, but that is not certification of every legacy feature. No feature implementation, branch merge or deployment is part of this documentation change.
