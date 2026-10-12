# Human content review packet — 2026-10-12

Two new channel sets are reserved for human review: fitness videos in English and cooking videos with Hindi metadata. No expected labels or model scores have been recorded for these cases. Three fitness captions were retrieved; the cooking request was blocked at its first video, so remaining requests stopped. Caption availability and reviewer confidence are separate fields.

Start with just one set. Watch the videos, not only their titles. If you have only watched excerpts, record that. You may answer “both”, “neither”, or “not sure”; do not force a winner. These are topical judgments, not claims about matching formats, shared footage or performance.

## Set 1

Which video, B or C, is closer to A in its main topic and what the viewer comes to learn?

| Video | Link |
| --- | --- |
| A | [Watch A](https://www.youtube.com/watch?v=vcBig73ojpE) |
| B | [Watch B](https://www.youtube.com/watch?v=Pok0Jg2JAkE) |
| C | [Watch C](https://www.youtube.com/watch?v=hWbUlkb5Ms4) |

Reply with your choice and a sentence explaining why. Also say whether you watched all three fully and understood their language. Viewing titles alone is not a complete content review. You can stop after this set.

## Set 2

Only review this set if you understand its spoken language. It has Hindi title/channel metadata; actual language understanding remains reviewer-reported.

| Video | Link |
| --- | --- |
| A | [Watch A](https://www.youtube.com/watch?v=B3H2RDSW9V8) |
| B | [Watch B](https://www.youtube.com/watch?v=bCTFtG_gG5s) |
| C | [Watch C](https://www.youtube.com/watch?v=NwUNbuFK2Ro) |

Use the same question and response format. “I cannot judge the language” is a valid answer. We will not translate that into a negative content match.

## Capture and evaluation boundaries

`docs/evaluations/independent-review-candidates.json` stores original IDs, source links, metadata provenance, caption status and text hashes when available. Metadata came from first-party YouTube results and oEmbed where available. Full third-party transcripts are omitted. Neither source titles nor descriptions establish content labels. The candidate video IDs do not overlap the six-video real-caption development cases; the two channel sets were not scored by the current candidate models. This does not prove absence from model pretraining or absence of related source material.

Record actual human responses through `core/content_review_intake.py` or `tools/record_content_review.py`. Reviewer identity and coverage are self-reported, not authenticated. The helper rejects assistant review provenance and refuses to overwrite an existing review or accept a case whose model result has already been exposed. Only a strict B/C preference, whole-video review and understood language creates a ranking case. Both/neither/unsure and incomplete review remain recorded without a fabricated ranking. Returned packets are copies; the original review manifest remains intact.

The helper records one review; it does not resolve disagreements between reviewers or establish consensus. A separate reviewer can use their own copy of the untouched packet. Once human reviews exist, retain them unchanged while computing model observations with the tested triplet evaluator. Pending or unsupported transcripts remain pending even when a human label exists. English-only model restrictions still apply.

This is a small reserved review packet, not a statistically sufficient validation corpus. More categories, languages, difficult paraphrases and repeated-material cases remain necessary. No channel-specific product rule, score threshold, UI behavior, merge or deployment was introduced.
