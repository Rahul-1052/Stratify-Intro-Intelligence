import { NextRequest, NextResponse } from 'next/server';
export async function POST(request: NextRequest) {
  if (process.env.NODE_ENV === 'production')
    return NextResponse.json({detail: 'Public analysis is not enabled yet.'}, {status: 503});
  if (request.headers.get('origin') !== (process.env.STRATIFY_WEB_ORIGIN || 'http://127.0.0.1:3000'))
    return NextResponse.json({detail: 'Request origin rejected.'}, {status: 403});
  const token = process.env.STRATIFY_SERVICE_TOKEN;
  if (!token || token.length < 32)
    return NextResponse.json({detail: 'Analysis service is not configured.'}, {status: 503});
  try {
    const form = await request.formData();
    const file = form.get('file');
    if (!(file instanceof File) || file.size > 20 * 1024 * 1024)
      return NextResponse.json({detail: 'Upload a video smaller than 20 MB.'}, {status: 413});
    if (form.get('owned') !== 'true')
      return NextResponse.json({detail: 'Confirm permission to analyze this video.'}, {status: 422});
    const upstream = await fetch(`${process.env.STRATIFY_API_URL || 'http://127.0.0.1:8000'}/v1/intro-evidence`, {
      method: 'POST', headers: {Authorization: `Bearer ${token}`}, body: form,
      signal: AbortSignal.timeout(60000), cache: 'no-store',
    });
    const data = await upstream.json();
    if (!upstream.ok)
      return NextResponse.json({detail: typeof data.detail === 'string' ? data.detail : 'Check your video upload.'}, {status: upstream.status});
    return NextResponse.json(data, {headers: {'Cache-Control': 'no-store'}});
  } catch {
    return NextResponse.json({detail: 'Intro analysis is unavailable. Try again.'}, {status: 502});
  }
}
