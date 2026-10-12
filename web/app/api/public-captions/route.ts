import { NextRequest, NextResponse } from 'next/server';
export async function POST(request: NextRequest) {
  // This private development bridge is deliberately closed in production.
  // Enable only after real user auth, ownership checks and shared rate limits exist.
  if (process.env.NODE_ENV === 'production')
    return NextResponse.json({detail: 'Public analysis is not enabled yet.'}, {status: 503});
  if (request.headers.get('origin') !== (process.env.STRATIFY_WEB_ORIGIN || 'http://127.0.0.1:3000'))
    return NextResponse.json({detail: 'Request origin rejected.'}, {status: 403});
  const token = process.env.STRATIFY_SERVICE_TOKEN;
  if (!token || token.length < 32)
    return NextResponse.json({detail: 'Analysis service is not configured.'}, {status: 503});
  const body = await request.text();
  if (Buffer.byteLength(body) > 32768)
    return NextResponse.json({detail: 'Request too large.'}, {status: 413});
  try {
    const payload = JSON.parse(body);
    if (!Array.isArray(payload.video_ids) || Object.keys(payload).length !== 1 || payload.video_ids.length < 1 || payload.video_ids.length > 12 || new Set(payload.video_ids).size !== payload.video_ids.length || payload.video_ids.some((id: unknown)=>typeof id !== 'string' || !/^[A-Za-z0-9_-]{11}$/.test(id)))
      return NextResponse.json({detail: 'Use up to twelve unique YouTube video IDs.'}, {status: 400});
    const upstream = await fetch(`${process.env.STRATIFY_API_URL || 'http://127.0.0.1:8000'}/v1/public-captions`, {
      method: 'POST', headers: {'Content-Type': 'application/json', Authorization: `Bearer ${token}`},
      body: JSON.stringify({video_ids: payload.video_ids}), signal: AbortSignal.timeout(45000), cache: 'no-store',
    });
    const data = await upstream.json();
    if (!upstream.ok) {
      const detail = typeof data.detail === 'string' ? data.detail : 'Enter a supported channel link and a concern of up to 2,000 characters.';
      return NextResponse.json({detail}, {status: upstream.status});
    }
    return NextResponse.json(data, {headers: {'Cache-Control': 'no-store'}});
  } catch (error) {
    return NextResponse.json({detail: error instanceof SyntaxError ? 'Invalid request.' : 'Analysis service is unavailable. Try again.'}, {status: error instanceof SyntaxError ? 400 : 502});
  }
}
