\# Stratify Failure Log



\## Entry 1



\### Video URL

https://www.youtube.com/watch?v=XlcK4VYSWZk\&t=1s



\### Content Type

TV/movie scene compilation



\### What Failed

Video download and benchmark intro extraction failed.



\### Current Output

Benchmark discovery worked, but intro evidence was unavailable. Stratify returned low confidence and no recommendation.



\### Root Cause

YouTube blocked yt-dlp on Render with bot-confirmation requirement.



\### Product Impact

The core intro intelligence cannot run when server-side video download is blocked.



\### Future Fix

Build a fallback path that uses metadata, transcript, thumbnail, and/or a more reliable extraction method. Keep YouTube URL as the main user experience; do not require users to manually upload 15-second clips.



\## Entry 2



\### Video URL

https://www.youtube.com/watch?v=dVs9CWrp4Dc



\### Content Type

Food / recipe short



\### What Worked

The full intro pipeline ran successfully. User intro, top benchmarks, and lower benchmarks were all analyzed.



\### What Failed

Top and lower benchmark intros had very similar dominant patterns, so Stratify could not generate a useful recommendation.



\### Root Cause

Benchmark selection is based mostly on relevance and view difference, but the selected top/lower videos are not behaviorally distinct enough.



\### Product Impact

The report is technically correct but not useful enough for creators.



\### Future Fix

Benchmark Discovery V2 should select lower performers that are both relevant and meaningfully different from top performers in format/intro behavior, not only lower-view videos.

