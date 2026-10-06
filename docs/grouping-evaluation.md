# General grouping evaluation — 2026-10-06

The current product groups shared caption words. It does not provide general semantic understanding. The new evaluation runner exercises that actual browser-side grouping function, separately from the earlier experimental embedding reports. No live channels, provider requests, model downloads or threshold changes are introduced.

Run with Node 24:

```sh
node --experimental-strip-types tools/evaluate_grouping.cjs --output docs/evaluations/grouping-development.json
```

Use `--fixture path.json` to evaluate a separate reviewed corpus in the same input schema. Reports identify fixture and engine SHA-256 hashes and preserve case-level selections, abstentions and coverage. Development labels must be explicitly `allow` or `abstain`; invalid labels reject the run.

## Observed development results

Eight assistant-authored synthetic cases: two expected groups accepted, one expected group missed, one misleading group accepted, four expected abstentions. The English and Hindi vocabulary controls group; fitness paraphrases do not. Generic shared vocabulary causes an unwanted group across constructed different subjects. Language separation, copied scripts, sparse input and date ties abstain.

This is not an accuracy percentage or evidence of usefulness on real channels. The constructed vocabulary bags isolate word matching; they are not natural creator transcripts. The natural-language fitness passages are still synthetic. Negative expectations are authored test design, not independent human ground truth.

## Decision

Do not promote shared-word grouping as general content understanding. Keep existing preparation provisional. Do not relax thresholds to rescue the missed case: that risks increasing unwanted matches. The next candidate approach needs semantic content representation and explicit independent-material checks, evaluated against separate reviewed examples before integration. Existing semantic experiments remain experimental; ranking related passages does not validate whole-video grouping.

## Next evaluation corpus

Collect complete, lawfully available transcripts from multiple creator categories and languages, preserving source IDs, retrieval language, collection status and text hashes. Have reviewers independently identify topical relationships, different audience intent, related parts or repeated dialogue, and unknown cases. Review video format and footage separately; transcripts alone cannot verify them. Separate development and held-out cases by channel and source material, so parts of the same recording cannot leak across splits.

Measure incorrect grouping and missed grouping separately from retrieval coverage and abstention. For each retrieval failure, preserve its actual status; do not label unavailable content unrelated. Have the creator confirm the intended concern and scope. No universal threshold, perfect answer or verified decline follows from this eight-case suite.
