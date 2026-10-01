# Stratify web migration — recovered beta engine

## What works in this change

Next.js/TypeScript workspace → same-origin development bridge → token-protected FastAPI → existing `core.youtube_client.get_video_details` → typed public metadata evidence record. No Streamlit dependency is required for this workflow. The original application remains a reference.

No synthetic report is substituted when YouTube is unavailable. Metadata-only results contain no intro recommendation. Invalid hosts, credentials, HTTP URLs and malformed video IDs are rejected before provider calls. Provider error text is not sent to browsers. The service token stays server-side.

Owned-video uploads now feed the recovered beta's `analyze_intro_frames`, `build_temporal_evidence` and `build_intelligence_v3` functions. The private adapter samples at most 20 frames from the first 10 seconds, records timestamps, and returns measured brightness, contrast and appearance differences. It makes no AI/provider calls, guesses no creator metadata, and recommends no experiment. Temporary video/frame files are deleted after processing; paths are never returned. A 20 MB upload limit, permission confirmation and explicit backend opt-in apply.

## Run locally

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-web.txt
export YOUTUBE_API_KEY=your_key
export STRATIFY_SERVICE_TOKEN=your_random_secret_at_least_32_characters
export STRATIFY_LOCAL_MEDIA_ENABLED=1
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

In a second terminal, put the same token in `web/.env.local` using `web/.env.example`, then:

```bash
cd web
npm ci
npm run dev
```

Open http://127.0.0.1:3000. The API defaults to localhost. Do not publish the development service. Production analysis explicitly returns 503 until real user authentication, authorization, quotas and abuse protection are implemented.

```bash
python -m pytest tests/test_web_api.py
cd web
npm run build
npm run typecheck
```

## Verified repository baseline

Recovered source: `external-beta-v1` at `9721883370b5761767f519837a90af62e4122cd8`. This integration branch starts from that snapshot and adds the web foundation. It does not merge or rewrite main or the beta source branch.

The original main snapshot (`6116aaac`) had an empty acquisition module. The newer code was subsequently found on the beta branch: Creator Memory, report V4, qualification, observers, intelligence V3, golden fixtures and validation tooling are present. The earlier statement that those features were missing applied only to main; they were not lost. Existing FFmpeg helpers hard-code a Windows executable. The new private adapter decodes with OpenCV instead and leaves those legacy helpers unchanged. OpenCV 5 lacks the legacy cascade API required by the recovered observer; the web environment pins the verified 4.x release.

## Next work, in order

1. Review this integration against the recovered beta, then establish the eventual main migration base. Creator Memory and report V4 exist but are not yet exposed on the web.
2. Extend the owned-asset evidence contract to the qualified semantic and creative report. Do not assume OAuth supplies raw YouTube videos or that an embedded player allows canvas frame extraction.
3. Add normalized observations and comparable cohorts, qualification rules and tests showing unsupported claims abstain.
4. Add Postgres users, workspaces, ownership checks, migrations and report persistence. Integrate real authentication; do not expose a shared token as user authentication.
5. Move expensive work into a durable queue with cancellation, limits, timeouts and worker isolation. Add a shared rate limiter, monitoring and safe audit events.
6. Ship the first evidence-backed experiment with a measurement window and explicit uncertainty. Evaluate on a golden dataset before inviting creators.

## Sprint across the three products

Thursday October 1: Stratify web vertical slice and engine reconciliation. Friday October 2: no scheduled work. Saturday October 3: NEXOR synthetic access event model and one traceable delay workflow. Sunday October 4: Cleargrain semantic-review-to-financial-result migration and shared hardening.

NEXOR repo snapshot inspected: Flask templates and demo CSVs exist; it is not solely Streamlit. Do not replace its working routes without migration tests. Prior authorization events and policy requirements need a separate explicit synthetic schema; existing claims cannot be treated as PA decisions. Keep drug and non-drug PA rules separate and verify current primary sources before encoding requirements.

Cleargrain repo snapshot inspected: FastAPI contracts, Postgres repository, migrations, governance and tests exist. Reuse them. Inspect current readiness behavior before fixing the previously reported payment/revenue issue; do not infer that a prior local fix is present upstream.

## Launch gates still outstanding

Real authentication and tenant isolation; persistent jobs and data; end-to-end provider validation with configured credentials; golden evidence evaluation; deployment/HTTPS; CSP appropriate to the deployed frontend; secrets rotation; monitoring and backups; account deletion and data retention; truthful privacy/terms; accessibility and mobile checks; dependency/security review. This change is a migration foundation, not a public SaaS launch or a Google Workspace Marketplace submission. Distribution route and OAuth scopes remain decisions to settle.

Upload handling is private development only. Before public deployment, enforce request-body limits before multipart parsing at the gateway, isolate media decoding in resource-limited workers with hard timeouts, and add concurrency limits. Current file limits apply after framework multipart parsing; they do not substitute for gateway limits. Production frontend routes remain closed.

## Validation of this change

The verification command covers metadata API tests, upload/real pixel-processing tests, and recovered Creator Memory, temporal evidence, intelligence V3 and observation calibration tests. The upload tests encode real synthetic MP4s, assert dark-to-bright measurements and frame differences, verify cleanup, reject corrupt/empty/oversize files and check permissions. Next.js production build and strict TypeScript checks are also required. Legacy UI/report V4 tests import Streamlit and were not included in the web environment. Live YouTube integration still requires a key; visual/accessibility verification remains open.

Result: **95 tests passed**. Frontend build and strict type checks passed. `python tools/verify_web_bridge.py` also passed: an actual MP4 traversed Next.js → FastAPI → the recovered observer and returned six measurements; an untrusted origin was rejected. The web bridge uses a configured `STRATIFY_WEB_ORIGIN` rather than Next.js's normalized internal origin. The default matches http://127.0.0.1:3000.
