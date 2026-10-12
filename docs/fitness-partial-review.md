# Fitness partial-view follow-up — 2026-10-12

Rahul selected C as closer to A because both concern bench press, while B concerns building muscle. He reported fast-forwarding through the videos. The review therefore remains `partial_videos`, not a complete-video label. Language understanding was not separately confirmed and is recorded as null rather than invented. The review's exact wording and viewing method are preserved in `fitness-partial-human-review.json`.

Both complete-transcript semantic observations agreed with this narrow feedback:

| Candidate | A to B | A to C | Observation |
| --- | --- | --- | --- |
| MiniLM | 0.3521 | 0.8555 | C ranks closer |
| BGE-small | 0.7798 | 0.8801 | C ranks closer |

These values are cosine text similarities, not confidence percentages. All available transcript chunks were processed. Human partial viewing and model whole-text processing are different coverage bases. The exploratory result is explicitly excluded from full-video validation; the review intake returns no strict ranking case. No unknown language assertion, partial view or agreement is promoted into complete human ground truth.

The underlying observations can be reproduced with the existing `tools/evaluate_semantic_captions.py` runner using a local caption JSON containing only these three available fitness transcripts, the model-specific cache, and `--captions-json`. The script emits all pair observations alongside its unchanged diagnostics. The exploratory report preserves transcript hashes, chunk counts and model asset hashes; it omits full third-party transcript text. Inputs with changed hashes are a new snapshot and must not be treated as an exact reproduction.

## Development decision

The positive fitness example is encouraging but does not justify a production semantic threshold. Existing diagnostic failures, uncertain formats/footage, sparse human labels and unreliable retrieval remain. Continue the general evaluation path with strict and exploratory evidence kept separate; do not add a bench-press-specific product rule. The Hindi candidate set remains awaiting human review and supported caption evidence. No additional viewing is required from Rahul right now.
