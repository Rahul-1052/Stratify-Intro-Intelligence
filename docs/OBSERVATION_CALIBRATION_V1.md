# Observation Calibration V1

## Baseline

The ten synthetic cases initially measured 68.1% weighted accuracy, 71.4%
unweighted accuracy, 92.1% evaluability coverage, 93.5% required-metric
coverage, three unavailable metrics, and 72.3% average confidence.

## Root causes

Scene changes depended on coarse semantic scene labels, novelty counted changed
labels rather than visual difference, the text detector did not group individual
glyph edges, and density lacked geometric focal evidence. The accuracy adapter's
continuity fallback also normalized only the longest reported stable interval.

## Scene-change method

Each sampled-frame transition now receives a deterministic cut score:

```text
0.38 × normalized frame difference
+ 0.32 × color-histogram distance
+ 0.20 × edge-layout difference
+ 0.10 × luminance shift
```

A centralized threshold of 0.18 marks a sampled hard cut. V3 merges this with
existing semantic change events and emits the score components as evidence.

## Continuity formula

Scene continuity is:

```text
0.55 × (1 − sampled cut ratio)
+ 0.45 × longest cut-free interval ratio
```

This distinguishes a stable clip from one with frequent sampled cuts without
assuming that an undetected semantic label change means continuity.

## Novelty method

Perceptual novelty is the cut score normalized against 0.42 and capped at 1.0.
V3 aggregates transition scores directly. Older structured fixtures without the
new field retain the existing categorical-event fallback.

## Text-presence method

The lightweight detector groups high-contrast horizontal edge components,
filters them by relative size, aspect ratio, and edge density, then scores region
size and character-like edge density. Temporal smoothing requires adjacent
support unless a frame has a strong detector margin. It detects presence and
timing, not the written words.

## Focal stability and competition

Frames are segmented by color distance from their median background. Prominent
connected regions expose normalized area and centroid evidence. The largest
region's share supplies dominance; the top-two area ratio combined with spatial
separation supplies competition. Aggregation reports visible-region count,
dominance, competition, centroid drift, focal stability, density level, and a
transparent classification.

Central thresholds are:

- sampled cut score: 0.18
- text-region score: 0.42
- prominent-region minimum area: 1.2%
- focal competition: 0.52
- stable centroid drift: 0.08 normalized frame units

## Confidence calibration

Text confidence reflects score margin and temporal support. Focal confidence
reflects whether prominent regions exist and how far competition lies from its
threshold. Accuracy remains independent of confidence, so confident errors stay
visible.

## Regression protection

Tests protect rapid and frequent cuts, static/no-scene behavior, near-duplicate
frames, text timing and smoothing, focal dominance and competition, subject
continuity, information timing, and the existing accuracy adapter.

## Limitations

Sampling can still miss cuts between timestamps. Color segmentation is not a
semantic object detector and may merge textured regions in natural footage.
Text-region detection does not read words and requires persistent, prominent
visual structure. Real typography and camera motion require further validation.

> Improvements on synthetic clips do not establish real-world creator-video accuracy.

## Offline benchmark after calibration

Run `20260727T014535Z-01e5c945` completed all ten cases:

- weighted accuracy: 100.0% (baseline 68.1%)
- unweighted accuracy: 100.0% (baseline 71.4%)
- evaluability coverage: 100.0% (baseline 92.1%)
- required metric coverage: 100.0% (baseline 93.5%)
- unavailable metrics: 0 (baseline 3)

All existing expectations were preserved. The strict results include twelve
detected sampled cuts and 0.05 continuity for the rapid montage, early text at
0.0 seconds, late text at 5.0 seconds, stable focal geometry for the anchor case,
and competing focal geometry with 2.08 average visible elements for the
competition case. This perfect synthetic score is evidence of fixture coverage,
not proof of general detector accuracy. Real-video validation remains required.
