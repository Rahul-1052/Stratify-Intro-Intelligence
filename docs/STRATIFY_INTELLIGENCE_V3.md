# Stratify Intelligence V3

## Intelligence architecture

The production path remains acquisition → sampled frames → deterministic visual
observations → temporal evidence → semantic observations → evidence qualification
→ creative reasoning → experiments → Creator report. V3 adds a typed,
timestamp-aware evidence layer after frame observation. It does not replace the
V2 semantic layer, benchmark system, Creator Memory, or report renderer.

The concrete production modules are:

- frame extraction: `utils/frame_extractor.py`
- visual measurements, motion, energy, human count, text-like regions, lighting,
  color-adjacent brightness and scene class: `core/vision_analyzer.py`
- V2 temporal windows: `core/observers/temporal_evidence.py`
- semantic states and beat calibration: `core/observers/semantic_observer.py`
- V3 temporal findings and qualification: `core/intelligence_v3.py`
- benchmark collection and qualification: `core/benchmark_collector.py`,
  `core/benchmark_qualification.py`, and `core/benchmark_intelligence_v2.py`
- creative reasoning and opportunity ranking:
  `core/reasoning/creative_reasoning.py`
- Creator serialization and rendering: `core/creator_report.py` and
  `ui/report.py`
- objective report warnings: `core/product_validation/checks.py`

## Observation taxonomy and meaningful change

V3 compares adjacent sampled states and records composition, scene, visible
subject count, dominant visible focus, text-like-region state, motion state,
focal region, energy, and sufficiently large measured lighting shifts.
Brightness noise alone is not a creative event. Each accepted event retains its
timestamp, previous and new states, supporting measurements, evidence strength,
warnings, and a non-evaluative novelty score.

Derived timing includes the first meaningful change, unique change timestamps,
the longest stable interval, and early/late counts. Cadence uses intervals
between unique meaningful-change timestamps. Progression labels are computed
from interval medians and spread. Novelty represents measured state difference,
never quality.

Information introduction includes observable new text-like regions, visible
subjects, scenes, compositions, and dominant visible focus. It excludes speech
unless separately qualified transcript evidence exists. Subject continuity does
not identify people. Density counts simultaneous supported elements and
distinguishes a stable focal anchor from variable focal regions.

## Evidence model

Every V3 finding contains a stable finding ID, observation type, time range,
measured and optional comparison values, evidence strength and source,
supporting and conflicting observations, availability, qualification,
limitations, and provenance.

Availability is one of `unavailable`, `available_but_weak`,
`available_and_qualified`, `conflicting`, or `not_applicable`. Sample coverage,
missing windows, reliability, agreement, and conflicts govern qualification.

## Confidence separation

Observation confidence describes measurement support. Interpretation confidence
describes whether those observations form a coherent pattern. Recommendation
confidence additionally requires an isolatable, actionable variable. A strong
observation therefore may still produce limited recommendation confidence.

## Reasoning and opportunity contract

Reasoning states observation, evidence, interpretation, opportunity, limitation,
and recommendation eligibility. Opportunities are ranked using evidence count,
strength, temporal importance, magnitude, actionability, isolation, novelty,
benchmark support, contradictions, missing evidence, and limitations.
Near-duplicate structural dimensions are suppressed.

## Experiment contract

Each V3 experiment identifies source finding IDs, one measurable variable,
controls, exact execution, target timing and applicability, acceptable examples,
the expected observable change, measurement plan, evidence basis, confidence,
limitations, and invalidation criteria. Outcomes are not predicted.

## Abstention policy

The system abstains when evidence is sparse, conflicting, unqualified, cannot
support one isolated variable, requires an audience assumption, or merely
restates an observation. Creator reports explain that no controlled alternative
is justified and identify stronger evidence as the next requirement.

## Benchmark and local-source behavior

Qualified YouTube benchmarks may enrich a direct finding with measured
comparison values, sample size, agreement, and limitations. Unqualified
benchmarks never support recommendations. Uploaded and cached local clips use
direct video evidence only and label benchmark context unavailable.

## Prohibited claims and limitations

V3 does not infer boredom, abandonment, retention improvement, engagement,
preference, creator intent, identity, spoken information, or aesthetic quality.
Sampled frames can miss events between timestamps. Text-like-region detection
does not establish readable text. Human detection does not establish identity.
No creative recommendation establishes causal performance impact.
