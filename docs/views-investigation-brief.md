# Question-aware views investigation

The confirmed creator question and requested period now reach the views comparison. Reports distinguish a measured public-count difference from an explanation of why it happened or a strategy for increasing views. Answers are deterministic wording-based statements of the evidence boundary; they do not constitute general semantic understanding. Unsupported question wording remains explicitly unanswered. Calculations continue to use the existing validated median and viewing-window functions.

## Scope handling

An empty period retains the existing provisional three-versus-three selection, at least seven days old. Exact paired requests such as `last 3 uploads vs previous 3 uploads` or `my last six uploads compared with the previous four videos` select those counts by publication date in the collected public inventory. Unlike the default, fresh uploads are retained to avoid silently changing the requested groups; their lifetime totals remain unequal exposure evidence. Explicit requests do not invoke caption matching to substitute a different cohort.

Other scope text, such as `September vs August`, `last six uploads` without a comparison group, or topic-qualified requests, disables automatic preparation and asks for manual selection. The creator can confirm that their selection matches the requested period; that confirmation is unverified. Adjustments invalidate it. Parsed paired requests are checked against the actual selected IDs and group counts, so manual changes cannot silently remain labeled as the requested comparison. Missing or future dates, date ties across the group boundary, insufficient inventory or duplicate IDs withhold automatic scoped groups. Private or unavailable uploads remain outside the inventory.

## Report evidence

The compact report states what it can answer, reports the measured comparison and retains one next step. `See details` includes the confirmed question, requested scope, source-linked selected videos and lifetime counts, collection date, median definition and limitations. Creator-entered equal-window analytics continue to be explicitly unverified and do not establish causal explanations. Scope uncertainty remains visible in that result as well.

Validation: 47 routing, scope, comparison and caption tests passed; strict TypeScript checks and production build passed. Browser script syntax and diff whitespace checks passed. Browser coverage was extended for unsupported scope, creator confirmation, automatic paired groups and causal abstention. Browser execution is pending because Chromium was unavailable after its download returned an invalid archive in the preceding milestone. No backend or private-analytics integration was added; general natural-language period parsing, content verification and channel-wide causal diagnosis remain unfinished.
