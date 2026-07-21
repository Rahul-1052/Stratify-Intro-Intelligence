# Stratify Hardcoding Audit V1

## 1. Executive summary

The active Intro Intelligence Creator path is predominantly evidence-driven, but the repository is not free of harmful hardcoding.

The current path derives Creator output from frame observations, calibrated semantic aggregation, qualified benchmark evidence, and controlled language templates. No active rule checks for the audited Catch Me If You Can or Lucy clips, a fixed creator/channel, or a fixed YouTube video ID. Metadata is used for acquisition and benchmark discovery, but Semantic Observation V2 keeps it separate from direct visual evidence.

Two risk groups remain:

1. Several dormant legacy modules contain fixed emotional conclusions, named franchise/game keyword branches, and generic recommendations that would be harmful if reconnected to runtime.
2. Some active recommendation rules map one aggregated semantic condition to one editing principle without contradiction checks or confidence gates. These are reusable rather than video-specific, but remain suspicious shortcuts requiring evaluation data.

One clearly unsupported active shortcut was corrected: immediate focus clarity no longer manufactures an experiment to remove a secondary element that was never observed. One-frame evidence is also no longer sufficient to emit an experiment.

## 2. Overall hardcoding risk

**Overall repository risk: Moderate.**

- Active Creator path: **Low-to-moderate**. No video/title/category special cases were found. Primary risk is overgeneralized editing advice from aggregated semantics.
- Benchmark path: **Moderate**. Qualification gates are evidence-based, but many calibrated weights and thresholds remain distributed across modules.
- Dormant legacy code: **High if reactivated**. It contains named media/category keyword rules and unconditional emotional/retention-style outputs.
- UI, project restoration, caching, and evaluation framework: **Low**. These transport or render stored evidence and do not select conclusions from named content.

## 3. Scope and modules inspected

The automated scanner inspected **99 production Python files** under `core/`, `ui/`, `stratify_platform/`, plus application/configuration entry points. All **13 test modules** were searched for fixture leakage and production imports.

Manual review concentrated on:

- Acquisition and app entry points
- Frame, visual, story, and semantic observers
- Understanding and provider routing
- Creative reasoning and Creator report composition
- Benchmark collection, cleaning, relevance scoring, qualification, cohort formation, and pattern discovery
- Experiment and recommendation engines
- Category/query intelligence
- Confidence and threshold logic
- Project restoration and caches
- Evaluation datasets, metrics, comparison, exports, and dashboard
- Legacy content, emotion, scene, context, growth, and intro modules

## 4. Repository-wide search patterns

The audit used case-insensitive searches for:

- Named clips: `Catch Me If You Can`, `Impersonating a Pilot`, `Lucy`, `Professor Norman`
- Named creators/channels: `MrBeast`, `PewDiePie`, `Markiplier`, `Casey Neistat`
- Named media/games: `Breaking Bad`, `Blacklist`, `Spider-Man`, `Ghostbusters`, `Karate Kid`, `The Boys`, `Valorant`, `Fortnite`
- URLs: `youtube.com/watch`, `youtu.be`
- Metadata: `title`, `description`, `channel_title`, `video_title`, `creator_name`
- Category branches: `if category`, category equality/membership, movie/gaming/podcast/tutorial terms
- Fixture leakage: `from tests`, `import tests`, `fixture`, `synthetic`
- Advice branches: `recommend`, `experiment`, `if text`, `if motion`, `if person`, `if multiple`
- Thresholds and confidence assignments: numeric comparisons, shares, counts, scores, and confidence labels

The repeatable scanner is `tools/audit_hardcoding.py`.

## 5. Findings by file

| File | Line/function | Current behavior | Class | Risk | Evidence dependency | Recommended action |
|---|---|---|---|---|---|---|
| `core/vision_analyzer.py` | `_lighting_level`, `_clarity_level`, `_energy_level`, `_detect_text_like_regions` | Converts measured brightness, contrast, motion, and contours into controlled observations. | A/D | Medium | Pixel statistics | Centralize/calibrate thresholds when a labeled visual dataset exists. Do not replace with prose generation. |
| `core/observers/semantic_observer.py` | `BeatCalibrationConfig` | Centralizes persistence, interruption, alternating-state, and frequent-change thresholds. | A/D | Low | Multiple timestamped frames | Keep; evaluate thresholds through the evaluation framework. |
| `core/observers/semantic_observer.py` | `_focus`, `_purpose`, `_merge_candidate_states` | Maps structured signals into controlled focus/purpose states and merges temporally continuous states. | A/C | Low | Focus, text, motion, environment, composition, persistence | Keep; mappings are deterministic and diagnostics expose every decision. |
| `core/reasoning/creative_reasoning.py` | `_focus_insight` | Generates advice for competing, alternating, delayed, or developing focus. The former immediate-focus removal advice was unsupported and removed. | B/E | Medium | Aggregated focus, clarity, multiple samples | Keep corrected behavior; add agreement labels before changing remaining principles. |
| `core/reasoning/creative_reasoning.py` | `_text_insight` | Persistent/dominant text leads to a delayed-text experiment; intermittent text leads to a timing experiment. | B/E | Medium | Multi-frame text role and information mode | Evaluate whether visual hierarchy or legibility evidence should be an additional gate. |
| `core/reasoning/creative_reasoning.py` | `_progression_insight` | Stable single-state openings may receive a deliberate-development experiment; frequent semantic changes may receive consolidation advice. | B/E | Medium | Final beats plus candidate state count | Retain for evaluation, not as proven truth. Track agreement and experiment usefulness. |
| `core/reasoning/creative_reasoning.py` | `_subject_pattern_insight` | Multiple or late/inconsistent visible subjects produce framing/entrance experiments. | B/E | Medium | Sustained subject pattern | Add contradiction checks as labeled failures become available. |
| `core/creator_report.py` | `_benchmark_experiment`, `build_creator_report` | Adds benchmark language only when `eligible_for_directional_learning` is true; otherwise remains observation-only. | A/C | Low | Qualified benchmark quality and populated recommendation | Keep. Existing tests prevent unsupported benchmark claims. |
| `core/creator_report.py` | no-priority fallback | Reports insufficient evidence and requests a clearer sample instead of inventing an editing change. | C | Low | Absence of usable insights | Keep. |
| `core/content_understanding.py` | prompt and `_fallback_queries` | Uses title/description/channel as metadata context to generate benchmark queries, not direct visual claims. | A/C | Medium | Explicit metadata plus optional intro observation | Keep metadata labeling explicit. Provider output must remain outside direct observation. |
| `core/category_intelligence.py` | `WEAK_ANCHOR_WORDS`, query hypotheses | Removes packaging words and builds evidence-derived benchmark queries without assigning content categories. | A/D | Low | Supplied title/description | Keep; word lists affect search only, not Creator observations. |
| `core/benchmark_intelligence_v2.py` | scoring and `qualify_neighborhood` | Scores candidate relevance using metadata/query overlap and applies adaptive thresholds. | A/D | Medium | Candidate metadata and generated hypotheses | Centralize weights/floors after calibration. Current values are explainable but scattered. |
| `core/benchmark_intelligence_v2.py` | `select_performance_cohorts`, `assess_benchmark_quality` | Uses views only after relevance qualification and requires group size, diversity, separation, and quality before directional learning. | A/D | Medium | Qualified observed neighborhood plus performance | Keep causality disclaimer; views are a grouping signal, not proof of a creative cause. |
| `core/benchmark_qualification.py` | `_qualification_decision` | Requires observed intros, coverage, viewer-job agreement, dimension floors, and observed-intro compatibility. | A/D | Low-to-medium | Both intros observed and structured comparisons | Consolidate the remaining inline floors with benchmark configuration when calibrated. |
| `core/experiment_engine.py` | experiment-board templates | Converts qualified feature contrasts into generic “move toward stronger pattern” experiments. | C/E | Medium | Actionable benchmark contrast and evidence counts | Builder-only context is important. Do not promote directly to Creator without semantic/contradiction validation. |
| `core/brain/insight_engine.py` / `brain/experiment_engine.py` | grouped templates | Uses fixed editing principles populated from benchmark feature evidence. | B/C/E | Medium | Actionable stronger/lower comparison | Label as templated diagnostic reasoning; avoid claims of unique interpretation. |
| `core/evaluation/evaluation_metrics.py` | confidence/agreement maps | Converts existing labels into documented ordinal values and adjacent-class partial agreement. | A/D | Low | Stored reports and optional manual labels | Keep mappings explicit and version evaluation runs when they change. |
| `core/pipeline/intro_pipeline.py` | metadata context | Stores title, description, and channel separately inside semantic output. | A | Low | Source metadata | Keep separation; direct semantic fields never read metadata. |
| `ui/report.py` | Creator renderer | Renders structured Creator fields without title/category switches. | C | Low | Creator report schema | Keep. Templates should be described as controlled presentation, not novel prose. |
| `ui/advanced.py` | Builder diagnostics | Exposes raw observations, semantics, benchmark evidence, and evaluation output. | C | Low | Stored technical evidence | Keep Builder-only evaluation gating. |
| `stratify_platform/projects.py` | restoration | Serializes/restores reports and experiments without altering conclusions. | A | Low | Stored project schema | Keep compatibility tests. |
| `core/content_dna.py` | keyword tables and `generate_content_dna` | Named franchises/games and title keywords prescribe content world, emotion, audience desire, and title promise. Not imported by active runtime. | F | High if reactivated | Metadata substring only | Quarantine/deprecate before any future use; replace only after a separate product decision. |
| `core/emotional_center.py` | `detect_emotional_center` | Named-character, car, gaming, and food keywords prescribe emotional needs and growth advice. Not imported by active runtime. | F | High if reactivated | Title/description substring only | Do not reconnect. Retire or rebuild from supported evidence in a dedicated task. |
| `core/intro_intelligence.py` | `analyze_intro` | Returns the same emotional, attention, and growth conclusions for every path. Dormant. | F | High if reactivated | None | Deprecate/remove in a dedicated cleanup; current module registry does not call it. |
| `core/context_intelligence.py` | `get_context_intelligence` | Returns fixed audience psychology and emotional promise for all inputs. Dormant. | F | High if reactivated | None | Do not reconnect; retire separately. |
| `core/scene_understanding.py` | `understand_scene` | Wraps visual values in fixed emotional conclusions unsupported by the raw fields. Dormant. | F | High if reactivated | Shallow vision summary | Retire or require explicit emotion/story evidence before reuse. |
| `core/growth_snapshot.py` | title/engagement branches | Converts title keywords and engagement thresholds into emotional strengths and fixed growth advice. Dormant. | F/E | High if reactivated | Metadata and aggregate engagement | Keep out of Intro Intelligence; requires a separate analytics evidence model. |
| `core/stratify_brain.py` and related legacy meaning modules | fixed emotional language | Produces retention/emotional claims from passed labels without validating their origin. Dormant from current report runner. | F/E | High if reactivated | Caller-provided labels of uncertain provenance | Do not expose without evidence contracts and evaluation coverage. |

## 6. Findings by classification

### A. Deterministic algorithms

- Pixel-statistic observation bands
- Consecutive-state grouping and persistence-aware beat merging
- Evidence coverage and confidence calculations
- Benchmark deduplication, relevance scoring, diversity selection, and qualification gates
- Project serialization and evaluation-cache reuse

These are legitimate deterministic logic. Their risk comes from calibration quality, not hardcoding of particular videos.

### B. Domain principles

- Competing visual priority can justify a controlled simplification test
- Persistent text can justify testing information order
- Excessive semantic change can justify testing consolidation
- A delayed subject can justify testing earlier visual establishment

These are reusable editing principles, not guaranteed outcomes. They should remain framed as experiments and evaluated against manual labels.

### C. Evidence-driven templates

- Opening summaries populated from focus, clarity, progression, and text role
- Beat descriptions populated from beat purpose and timestamps
- Experiment cards populated from semantic observations or qualified comparisons
- Evidence-validation and insufficient-evidence messages

Templates are acceptable because they expose their evidence source and do not claim bespoke generative reasoning.

### D. Configuration or thresholds

The scanner reported **220 numeric-comparison candidates**. This is intentionally over-inclusive: it includes loop limits, safe bounds, counts, and UI limits as well as meaningful model thresholds.

Important threshold families are:

- Semantic persistence: centralized in `BeatCalibrationConfig`
- Evaluation confidence and partial agreement: centralized in module constants
- Benchmark minimum groups: partly centralized, with relevance/quality weights and several floors still inline
- Vision brightness, contrast, motion, and contour bands: inline in `vision_analyzer.py`
- Benchmark signature/viewer-job similarity: distributed across comparison modules

The inline vision and benchmark thresholds are audit findings, not automatically defects. Moving them without labeled calibration could create an unmeasured behavior change.

### E. Suspicious shortcuts

- Persistent text maps directly to delayed-text testing without checking actual legibility or occlusion.
- Mostly-held semantic purpose can map to adding development, although a stable opening may be intentional.
- Multiple-subject patterns map to isolating a figure without knowing the creator's intended hierarchy.
- Benchmark experiment templates can overstate that matching a stronger cohort's feature is creatively appropriate.
- Some low-confidence multi-frame findings still produce experiments; confidence is shown but is not a universal emission gate.
- Provider-generated content understanding may be semantically rich but is not direct visual evidence and must stay confined to benchmark context.

These require product judgment and labeled evaluation, so they were documented rather than silently rewritten.

### F. Harmful hardcoding

Confirmed in dormant legacy modules:

- Named franchise/game branches in `content_dna.py` and `emotional_center.py`
- Fixed report output in `intro_intelligence.py` and `context_intelligence.py`
- Unsupported emotional interpretation in `scene_understanding.py`
- Title-keyword growth advice in `growth_snapshot.py`
- Fixed emotional/retention language in legacy meaning/brain helpers

No harmful named-content rule was found in the active Creator pipeline.

## 7. Metadata leakage verdict

- Full titles, descriptions, and channel names are passed to content understanding and benchmark query generation as metadata.
- They are separately stored under `semantic_observation.metadata_context`.
- Direct semantic aggregation reads only frame observations.
- Creator reasoning consumes semantic fields and does not read `video.title`, description, channel, or category.
- The scanner found no audited test-video title in production.
- Regression tests confirm changing the full title while holding visual evidence constant does not change Creator reasoning.

Verdict: **No active metadata-to-direct-visual leakage found.** Metadata remains influential in benchmark discovery, where it is explicitly appropriate and labeled.

## 8. Experiment-generation audit

The active Creator chain is:

`multiple frame observations → semantic aggregation → semantic condition → editing principle → controlled experiment → optional benchmark enrichment`

| Rule | Required evidence | Semantic condition | Confidence handling | Contradiction/unavailable behavior |
|---|---|---|---|---|
| Focus priority | At least two samples | competing, alternating, delayed, or develops early | Confidence copied to experiment | Immediate clarity now produces no corrective experiment; unavailable omitted |
| Text timing | At least two samples | persistent/dominant or intermittent text plus information mode | Confidence copied | Absent/unavailable omitted; actual legibility is not checked |
| Progression | At least two samples and calibrated state diagnostics | mostly held with one candidate state, or frequent semantic change | Confidence copied | Multi-state continuity does not trigger “add a beat”; ordinary multi-beat structure omitted |
| Subject entrance | At least two samples | multiple, late, or inconsistent subject presence | Confidence copied | Present-immediately/unavailable omitted |
| Benchmark enrichment | Eligible qualified comparison set | Complete title/change/reason item | Inherits benchmark quality gate | No enrichment when qualification fails |

No experiment is emitted from one sampled frame after this audit. Missing evidence produces no insight or experiment.

## 9. Benchmark verdict

- No fixed creators, channels, video IDs, or benchmark result lists were found in runtime collection.
- Query hypotheses derive from metadata/provider understanding, not a fixed category table.
- Candidate relevance is scored, deduplicated, and thresholded.
- Both user and comparison intros require observed evidence for final qualification.
- Performance cohorts form only after viewer-job compatibility.
- Views create a limited performance contrast; they are not presented as causal proof.
- Creator benchmark labels require `eligible_for_directional_learning`.
- Insufficient evidence explicitly abstains.

Verdict: **Evidence-driven with moderate calibration risk, not manually prescribed.**

## 10. Tests versus production

- No production module imports `tests` or test fixtures.
- Named Sprint test clips do not appear in production.
- Cached validation artifacts are loaded only by validation/test tooling, not by the application report path.
- Synthetic fixtures do not enter runtime registries.
- Some tests assert section names and safety language, but do not require video-specific conclusions.

## 11. Corrections made

1. Removed the immediate-focus experiment that assumed an unobserved secondary element should be removed.
2. Required at least two supporting frame observations before any focus, text, progression, or subject-pattern experiment can be emitted.
3. Added a repository scanner with separate high-risk rules and review-only numeric-threshold reporting.
4. Added regression guardrails for titles, fixed URLs, creator names, test imports, benchmark gating, insufficient evidence, primitive-signal recommendations, active category branches, and centralized semantic thresholds.

Dormant harmful modules were not broadly rewritten because they are outside the active pipeline and require an explicit deprecation/migration decision.

## 12. Runtime impact

- Creator reports with immediate clear focus no longer receive a fabricated subtraction experiment.
- A single sampled frame cannot generate an editing experiment.
- Multi-frame observation-only and qualified benchmark reports remain compatible.
- Creator UI structure, Builder diagnostics, acquisition, project restoration, caching, and future-module status are unchanged.

## 13. Recommended remediation

Priority order:

1. Mark the identified legacy emotional/category modules deprecated and remove them after verifying no external consumers.
2. Populate manual evaluation labels for text timing, stable openings, and multi-subject sequences before changing those advice rules.
3. Introduce a versioned benchmark configuration object for relevance weights, qualification floors, quality weights, and group requirements.
4. Introduce a versioned vision-threshold configuration after collecting labeled brightness/motion/text-region examples.
5. Add CI execution of `tools/audit_hardcoding.py` and the hardcoding guardrail tests.

## 14. Final verdict

Stratify's active Creator-facing Intro Intelligence is not driven by named videos, creators, categories, or fixed benchmark lists. Its observations and timelines are deterministic transformations of sampled evidence, and its benchmark support is gated by observed compatibility and quality.

However, the repository cannot honestly be called free of harmful hardcoding. Dormant legacy modules contain exactly the title/category/emotional shortcuts prohibited by this audit, and several active editing principles remain hypotheses expressed through controlled templates rather than empirically proven recommendations.

The correct verdict is: **active pipeline substantially evidence-driven; repository-wide hardcoding risk remains moderate until legacy modules are retired and active advice rules are calibrated against manual evaluation data.**
