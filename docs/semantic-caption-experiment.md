# Semantic caption experiment

This offline experiment tests text matching by meaning. It does not change the website's comparison selection or add a production dependency.

The fixed, assistant-authored illustrative benchmark contains ten positive/negative triples. MiniLM ranked the intended positive first in only five cases. Failures included negation, distinguishing an interview from stand-up, related material, equal viewing windows, and a budgeting paraphrase. This is a small diagnostic, not a real-video accuracy estimate or an independently annotated benchmark. The model is not promoted to automatic grouping.

The evaluation also records pairwise observations on seven retrieved public captions from the Matt Rife pilot. These scores have no calibrated decision threshold and do not establish content independence, video format, or a fair performance comparison. Full caption texts are not committed. The report contains derived scores and model asset hashes.

The implementation processes complete English caption text in bounded chunks rather than just an opening, preserves unverified provenance, rejects invalid embeddings, and abstains on unsupported languages or oversized text. Equal averaging of chunks can obscure mixed topics. Text similarity cannot verify reused footage.

Use a separate virtual environment for `requirements-semantic-eval.txt`; FastEmbed's dependencies differ from the web environment. Run `python tools/evaluate_semantic_captions.py --output /tmp/semantic-evaluation.json`. The first run downloads the public model. No new API key is required.

Before production grouping, evaluate alternatives against independently reviewed real examples, including differently named related clips, multipart uploads, negation, and mixed formats. Keep chronology, format, shared material, and viewing-window checks separate from semantic scores. Do not tune thresholds to make this illustrative benchmark pass.

## Second candidate

`BAAI/bge-small-en-v1.5` ranked the intended positive first in six of the same ten unchanged illustrative triples. It still failed negation, the format trap, shared-material wording, and equal-window reasoning. Both reports contain observations from the same seven public captions. Neither model is promoted: these are similarity scores, not validated fair groups. The evaluator accepts `--model BAAI/bge-small-en-v1.5` with a separate cache directory, and the observation record identifies the model actually used.

## Independent checks and real-caption observations

`core/caption_comparison_checks.py` separates exact caption overlap from explicit creator format declarations. Eight-word sequences retain negation and other function words. A conservative, uncalibrated review flag requires at least ten shared unique sequences and 65% containment of the smaller set. No observed overlap does not establish independent recordings. Short shared slogans remain insufficient evidence. Titles and durations are not used to assign formats. Supported creator declarations are clearly unverified; mismatching declarations raise a separate format flag. Every pair still needs comparability review.

On the seven available public captions, all 21 pair formats remain unknown and no pair crosses the exact-overlap review threshold. This does not clear multipart videos as independent material: transcription differences and paraphrased reuse can evade exact matching. The eighth attempted caption timed out. `docs/evaluations/caption-independent-checks.json` preserves retrieval coverage, text hashes, derived observations and limitations, without caption text.

Reproduce with `python tools/evaluate_caption_checks.py --captions-json <retrieval.json> --output <report.json>`. The check evaluator needs no model or additional dependency. The web migration CI now runs the independent-check and semantic-contract tests.

### Remaining rollout gate

These experiments are not wired into the website. Production promotion requires reviewed examples with independently established format, topic and shared-recording relationships. Public caption scores cannot supply that ground truth. Include different titles for shared footage, matching titles for different recordings, transcript paraphrases, series excerpts, compilations and mixed formats. Record source, reviewer, evidence and disagreement for each label; split evaluation by recording/channel so related clips cannot leak across development and held-out examples. Report coverage, false matches and abstentions separately. Set acceptance criteria before tuning a decision threshold. Matched viewing-window analytics remain a separate requirement for performance claims.

## Caption-only reviewed development set

Seven pairs were reviewed against the complete available caption texts. Two show shared dialogue between an excerpt and the longer transcript, despite transcription variations. Five show no repeated passage in the available text; some have possible narrative continuity. Every format and shared-footage label remains unknown. These labels were authored by the assistant from captions, not by an independent reviewer watching videos.

The current exact-overlap screen flags neither of the two observed dialogue-containment cases. Both embedding models rank the two shared-dialogue cases above the chosen different-dialogue comparison, but BGE also gives that different exchange a similarity of about 0.85. Two ranking successes cannot establish a safe threshold. This frozen, caption-only development set therefore exposes a real false-negative gap in overlap screening without declaring any pair a fair performance comparison.

`tests/fixtures/reviewed-caption-pairs.json` records paraphrased review reasons without reproducing captions. Run `python tools/evaluate_reviewed_caption_pairs.py --output /tmp/reviewed-pairs.json`. Inventory consistency is checked. The older semantic reports lack caption-text hashes, so identical text provenance is based on the recorded retrieval session rather than independently rechecked hashes. The evaluator performs no network retrieval. The regression test preserves these known misses and unknown labels; it is not an accuracy certification.

Next implementation work should evaluate transcription-tolerant passage alignment independently of semantic topic similarity. Validate it on new, held-out examples before treating a lack of overlap as reassuring. Video viewing or explicit verified metadata is still required for actual format and recording ground truth. Until then, keep fair grouping unverified and the experimental layer disconnected from the website.
