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

