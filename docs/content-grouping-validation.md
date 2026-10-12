# Content grouping evaluation — 2026-10-12

## Result and rollout decision

No new matcher is promoted. The evaluation now covers six complete transcripts across MKBHD and 3Blue1Brown, two topical ranking cases, ten unchanged synthetic semantic diagnostics, a real Hindi language-coverage probe, and the wider YouTube collection failure. A ranking experiment is not the browser's production group-selection function and cannot establish fair performance comparisons.

| Evidence | MiniLM | BGE-small | Meaning |
| --- | --- | --- | --- |
| MKBHD user-reviewed headphone pair vs laptop | Intended pair ranked first | Intended pair ranked first | One user topical judgment, not whole-channel validation |
| 3Blue1Brown vector/span vs network lesson | Intended pair ranked first | Intended pair ranked first | Assistant transcript review; not independent ground truth |
| Ten unchanged illustrative diagnostics | 5 intended rankings | 6 intended rankings | Synthetic failures remain; no threshold tuning |
| Hindi creator-published text | Unsupported language; abstains | English-only adapter restriction | Multilingual grouping remains unvalidated |

The vocabulary baseline also ranks both real cases as expected. Therefore these two successful examples do not establish that semantic embeddings improve accuracy. BGE gives approximately 0.85 similarity to the MKBHD headphone-versus-laptop pair despite the intended topic distinction; high cosine scores are not calibrated probabilities or safe grouping thresholds. Negation, format, shared-material wording and equal-time reasoning remain failed diagnostics. These tasks should remain separately checked, rather than assumed from topic similarity.

All fifteen real transcript pairs received separate eight-word overlap and declaration checks. No large exact overlap was flagged. Formats remain unknown and fair comparisons are not established. No exact overlap is not proof of independent footage.

## Sources and review provenance

MKBHD's three public caption tracks were retrieved on 2026-10-12. Rahul's topical judgment predates the successful retrieval. Two tracks report manual captions and one generated captions; these metadata do not independently verify accuracy. The report includes text hashes and source IDs, but omits full third-party transcript text.

The broader YouTube batch was blocked at its first video and all seven remaining requests were stopped. Its statuses are recorded in `content-retrieval-coverage.json`; they are neither missing-content judgments nor model mistakes.

3Blue1Brown publishes transcripts in https://github.com/3b1b/captions . The evaluation retrieved `2016/vectors/english/transcript.txt`, `2016/span/english/transcript.txt` and `2017/neural-networks/english/transcript.txt` at commit `9aef876b0ed62ce4f099c0a2f0e7a52e8d1058c9`. The repository's corresponding `video_url.txt` files were checked against all three video IDs. This creator-published source is separate from blocked YouTube retrieval; no proxy, cookies, login or block bypass was used. Full English transcripts were reviewed before model comparisons. The neural-network lesson also uses linear algebra; its label means less direct topical overlap, not unrelated content.

A Hindi `sentence_translations.json` from the same pinned repository was used only to confirm the adapter's unsupported-language abstention. Translation review quality and multilingual accuracy are not established.

## Reproduction

Use a separate environment with `requirements-semantic-eval.txt`. Raw downloaded captions stay local, outside Git. Each caption input JSON has `results`, with complete `text`, `video_id`, `language_code`, source provenance and retrieval status. Source JSON from a published transcript repository can use the same schema while preserving its URL and commit. Do not combine different snapshots or languages under the same video ID in one run.

```sh
python tools/evaluate_content_triplets.py --cases tests/fixtures/reviewed-content-triplets.json --captions-json /path/mkbhd.json --captions-json /path/3b1b.json --cache-dir /path/model-cache --output /path/results.json
```

Add `--model BAAI/bge-small-en-v1.5` for the second candidate. The reports preserve source metadata, transcript hashes, package versions, model asset hashes, case-file hash, complete-text chunk coverage, ranking margins, declaration/overlap checks and reviewer-source counts. Models and captions are not web-runtime dependencies. The runner never converts ranking agreement into validated production groups. Blocked or unsupported evidence remains pending; no model is loaded when no transcripts are available.

## Required before promotion

A separately reviewed held-out corpus across more channels, source material, languages and audience intents is still absent. Assistant labels must not be counted as independent human labels. The next corpus needs related but differently worded examples, misleading shared vocabulary, negation, multipart or reused dialogue, mixed formats and caption failures. Split source material and channels between development and evaluation. Calibrate precision, missed matches and abstention separately from retrieval coverage. No automatic production semantic route, threshold change, merge or deployment occurred in this phase.

Validation: the focused ranking/semantic/overlap/frozen-review suite passes locally. Model experiments ran with recorded assets; browser testing is not applicable because no product UI behavior changed.
