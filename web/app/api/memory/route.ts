import {NextRequest, NextResponse} from 'next/server';

const api = () => process.env.STRATIFY_API_URL || 'http://127.0.0.1:8000';
const token = () => process.env.STRATIFY_SERVICE_TOKEN || '';
const headers = () => ({'Content-Type': 'application/json', Authorization: `Bearer ${token()}`});

function available() {
  return process.env.NODE_ENV !== 'production' && token().length >= 32;
}

export async function GET(request: NextRequest) {
  if (!available()) return NextResponse.json({detail: 'Creator Memory is not enabled here.'}, {status: 503});
  try {
    const analysisId = request.nextUrl.searchParams.get('analysis_id');
    const path = analysisId ? `/v1/memory/analyses/${encodeURIComponent(analysisId)}` : '/v1/memory';
    const upstream = await fetch(`${api()}${path}`, {headers: {Authorization: `Bearer ${token()}`}, cache: 'no-store', signal: AbortSignal.timeout(10000)});
    const data = await upstream.json();
    return NextResponse.json(upstream.ok ? data : {detail: data.detail || 'Creator Memory is unavailable.'}, {status: upstream.status, headers: {'Cache-Control': 'no-store'}});
  } catch {
    return NextResponse.json({detail: 'Creator Memory is unavailable.'}, {status: 502});
  }
}

export async function POST(request: NextRequest) {
  if (!available()) return NextResponse.json({detail: 'Creator Memory is not enabled here.'}, {status: 503});
  if (request.headers.get('origin') !== (process.env.STRATIFY_WEB_ORIGIN || 'http://127.0.0.1:3000'))
    return NextResponse.json({detail: 'Request origin rejected.'}, {status: 403});
  try {
    const body = await request.json();
    let path = '';
    let payload: unknown = {};
    let method = 'POST';
    if (body.action === 'profile') {
      path = '/v1/memory/profile';
      payload = {display_name: body.display_name, channel_name: body.channel_name, niche: body.niche || null};
    } else if (body.action === 'save') {
      path = '/v1/memory/analyses';
      payload = {report: body.report, upload_name: body.upload_name, content_digest: body.content_digest};
    } else if (body.action === 'experiment') {
      path = `/v1/memory/experiments/${encodeURIComponent(String(body.experiment_id || ''))}`;
      payload = {status: body.status ?? null, creator_notes: body.creator_notes ?? null, result_summary: body.result_summary ?? null};
      method = 'PATCH';
    } else {
      return NextResponse.json({detail: 'Unsupported Creator Memory action.'}, {status: 400});
    }
    const upstream = await fetch(`${api()}${path}`, {method, headers: headers(), body: JSON.stringify(payload), cache: 'no-store', signal: AbortSignal.timeout(10000)});
    const data = await upstream.json();
    return NextResponse.json(upstream.ok ? data : {detail: data.detail || 'Creator Memory request failed.'}, {status: upstream.status, headers: {'Cache-Control': 'no-store'}});
  } catch {
    return NextResponse.json({detail: 'Creator Memory request failed.'}, {status: 502});
  }
}
