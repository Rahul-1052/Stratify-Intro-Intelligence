# Semantic caption experiment

This offline experiment tests text matching by meaning. It does not change the website's comparison selection or add a production dependency.

The fixed, assistant-authored illustrative benchmark contains ten positive/negative triples. MiniLM ranked the intended positive first in only five cases. Failures included negation, distinguishing an interview from stand-up, related material, equal viewing windows, and a budgeting paraphrase. This is a small diagnostic, not a real-video accuracy estimate or an independently annotated benchmark. The model is not promoted to automatic grouping.

The evaluation also records pairwise observations on seven retrieved public captions from the Matt Rife pilot. These scores have no calibrated decision threshold and do not establish content independence, video format, or a fair performance comparison. Full caption texts are not committed. The report contains derived scores and model asset hashes.

The implementation processes complete English caption text in bounded chunks rather than just an opening, preserves unverified provenance, rejects invalid embeddings, and abstains on unsupported languages or oversized text. Equal averaging of chunks can obscure mixed topics. Text similarity cannot verify reused footage.

Use a separate virtual environment for `requirements-semantic-eval.txt`; FastEmbed's dependencies differ from the web environment. Run `python tools/evaluate_semantic_captions.py --output /tmp/semantic-evaluation.json`. The first run downloads the public model. No new API key is required.

Before production grouping, evaluate alternatives against independently reviewed real examples, including differently named related clips, multipart uploads, negation, and mixed formats. Keep chronology, format, shared material, and viewing-window checks separate from semantic scores. Do not tune thresholds to make this illustrative benchmark pass.
