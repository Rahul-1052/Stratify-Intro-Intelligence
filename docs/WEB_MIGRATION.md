# Stratify web migration — first slice

## What works in this change

Next.js/TypeScript workspace → same-origin development bridge → token-protected FastAPI → existing `core.youtube_client.get_video_details` → typed public metadata evidence record. No Streamlit dependency is required for this workflow. The original application remains a reference.

No synthetic report is substituted when YouTube is unavailable. Metadata-only results contain no intro recommendation. Invalid hosts, credentials, HTTP URLs and malformed video IDs are rejected before provider calls. Provider error text is not sent to browsers. The service token stays server-side.

## Run locally

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-web.txt
export YOUTUBE_API_KEY=your_key
export STRATIFY_SERVICE_TOKEN=your_random_secret_at_least_32_characters
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

Source snapshot: `6116aaaccb214b4f7be9afc7d521feb83db986c8`.

The committed `core/intro_acquisition.py` is empty although `stratify_report.py` imports `acquire_intro_evidence`. Therefore the full legacy report cannot currently import. `intro_intelligence.py` returns fixed prose; `growth_snapshot.py` contains heuristics that do not demonstrate causal effects. These are not exposed by the new API. Creator Memory, the larger beta evaluation suite and report V4 described in conversation were not found in this snapshot. Recover those local changes before migrating them.

## Next work, in order

1. Locate and reconcile the newer local Stratify implementation. Freeze a reproducible engine baseline with dependencies and fixture data.
2. Implement evidence acquisition and provenance independently from UI; use creator-supplied owned assets for the first visual path. Do not assume OAuth supplies raw YouTube videos or that an embedded player allows canvas frame extraction.
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

## Validation of this change

13 API tests passed, including host validation, authentication, metadata abstention, missing-video handling and sanitized provider failures. Next.js production build and strict TypeScript checks passed. `npm audit --omit=dev` reported zero known vulnerabilities at validation time. CI runs API tests and web build/type checks separately. Live YouTube integration was not exercised because no API key was supplied. Browser screenshot checks were blocked by an unavailable Chromium executable and unsuccessful browser download; visual/accessibility verification remains open.
