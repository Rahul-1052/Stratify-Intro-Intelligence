# Channel workspace: public facts and creator concern

The main page now accepts a channel identifier and a concern in the creator’s own words. Supported identifiers are @handles, channel IDs, HTTPS /@handle or /channel/ links, and legacy /user/ links. Ambiguous /c/ links require a handle instead; the collector never follows user-supplied URLs.

The private API endpoint `/v1/channel-workspace` resolves the channel through YouTube Data API v3, checks at most two upload-playlist pages (100 entries), and retrieves video metadata in batches of at most 50 IDs. It preserves playlist order, deduplicates IDs, excludes mismatched-channel metadata, and reports unavailable entries, pagination limits, publication date coverage and collection time. Missing or hidden metrics remain null. Public cumulative counts are not used to rank videos or explain performance.

The UI displays the concern verbatim, linked channel facts, an expandable source-linked upload inventory, and explicit limitations. This is evidence intake, not a completed answer. Automatic concern interpretation, concern-specific comparisons, private analytics authorization, thumbnail/content interpretation and audience-reaction analysis are future work. Nothing is saved to Creator Memory by submitting this form.

Existing upload observations and Creator Memory remain accessible. The new bridge uses the existing service token and same-origin check and stays disabled in production. No schema changes, infrastructure additions, deployment or external AI calls are introduced. `YOUTUBE_API_KEY` is needed for real acquisition.

Validation includes fixture-driven provider pagination, bounds, missing counts, input validation and sanitized API failures. Browser coverage checks intake, failure/retry preservation, result focus, responsive overflow and axe accessibility with clearly synthetic channel fixtures. Existing upload and memory browser checks still exercise real local services. Live YouTube acquisition has not been verified without a configured API key.

## Creator clarification and confirmation

Intake now has a review step before any YouTube call. The creator explicitly chooses a starting point (reach, returning viewers, subscriptions, content direction, packaging, viewing experience or an open question), keeps or edits their original wording, and optionally describes the period or videos they mean. No keyword classifier or model silently infers intent. The confirm action submits both the original concern and a separate creator-confirmed inquiry. Editing the intake clears the previous result and starts a new review; changing inquiry fields also invalidates the displayed result. Failure/retry preserves the creator’s work.

The API requires a validated inquiry with a supported focus, nonblank bounded question, optional bounded period and strict boolean confirmation. The response echoes that scope and attaches general evidence requirements for the selected focus. These are requirements, not observations or a diagnosis. A slow or branded opening is not assumed to be a problem. The requested period remains creator context: acquisition is still bounded and does not silently filter or assert that it covers that period.

This implements explicit clarification and confirmation, not a conversational AI interpreter. Automatic paraphrasing, adaptive multi-turn questions, exact video/period selection, concern-specific measurement and conclusions remain future work. The form is not persisted across reloads.

## Views investigation

For the creator-selected reach focus, the workspace now offers explicit selection of recent and earlier video groups from the collected public inventory. Every video can be in at most one group. Creators state whether topics and formats are similar, different or unknown; these statements are labeled as creator context and never treated as independently verified observations.

The calculation runs locally on the current evidence snapshot. It does not acquire new data, call a model or persist a diagnosis. It reports selected-video denominators, available counts, median lifetime views and publication ages at collection. Each group’s median is withheld if any selected count is missing or invalid. Differences are withheld when dates are missing, future-dated or interleaved; percentages are withheld when the earlier median is zero. Small groups are explicitly flagged. The calculation rejects duplicated, overlapping, empty or foreign selections.

Even a valid descriptive lifetime-count difference cannot establish declining performance over equal time after publication or its cause. The result explains that limitation and identifies the next evidence to collect: matched post-publication view windows, impressions and traffic sources for the selected videos. No content-change recommendation or experiment is produced. Duration does not infer format. This does not yet retrieve or accept owner-authorized analytics.

Changing selections or comparability clears stale results. Recollecting or editing the inquiry resets the comparison. Nine Node tests cover meaningful calculation edge cases; the browser workflow checks group selection, missing selection, descriptive output, focus, invalidation and accessibility with synthetic public-video fixtures.
