# Channel workspace: public facts and creator concern

The main page now accepts a channel identifier and a concern in the creator’s own words. Supported identifiers are @handles, channel IDs, HTTPS /@handle or /channel/ links, and legacy /user/ links. Ambiguous /c/ links require a handle instead; the collector never follows user-supplied URLs.

The private API endpoint `/v1/channel-workspace` resolves the channel through YouTube Data API v3, checks at most two upload-playlist pages (100 entries), and retrieves video metadata in batches of at most 50 IDs. It preserves playlist order, deduplicates IDs, excludes mismatched-channel metadata, and reports unavailable entries, pagination limits, publication date coverage and collection time. Missing or hidden metrics remain null. Public cumulative counts are not used to rank videos or explain performance.

The UI displays the concern verbatim, linked channel facts, an expandable source-linked upload inventory, and explicit limitations. This is evidence intake, not a completed answer. Concern interpretation, follow-up questions, confirmation, concern-specific comparisons, private analytics authorization, thumbnail/content interpretation and audience-reaction analysis are future work. Nothing is saved to Creator Memory by submitting this form.

Existing upload observations and Creator Memory remain accessible. The new bridge uses the existing service token and same-origin check and stays disabled in production. No schema changes, infrastructure additions, deployment or external AI calls are introduced. `YOUTUBE_API_KEY` is needed for real acquisition.

Validation includes fixture-driven provider pagination, bounds, missing counts, input validation and sanitized API failures. Browser coverage checks intake, failure/retry preservation, result focus, responsive overflow and axe accessibility with clearly synthetic channel fixtures. Existing upload and memory browser checks still exercise real local services. Live YouTube acquisition has not been verified without a configured API key.
