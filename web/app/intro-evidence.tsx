'use client';
import {FormEvent, useState} from 'react';
import CreatorReportView from './creator-report';
export type Evidence = {asset_sha256: string; upload_name: string; sample_count: number; intro_seconds: number; samples: {timestamp: number; brightness_score: number; contrast_score: number; motion_score: number}[]; limitations: string[]; report: Parameters<typeof CreatorReportView>[0]['report']};
export default function IntroEvidence({onEvidence}: {onEvidence: (evidence: Evidence | null) => void}) {
  const [file, setFile] = useState<File | null>(null);
  const [owned, setOwned] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [evidence, setEvidence] = useState<Evidence | null>(null);
  async function submit(event: FormEvent) {
    event.preventDefault(); setError(''); setEvidence(null); onEvidence(null);
    if (!file || file.size > 20 * 1024 * 1024) {setError('Choose a video smaller than 20 MB.'); return;}
    setBusy(true);
    try {
      const form = new FormData(); form.append('file', file); form.append('owned', String(owned));
      const response = await fetch('/api/intro-evidence', {method: 'POST', body: form});
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Could not analyze this clip.');
      setEvidence(data); onEvidence(data);
    } catch (e) {setError(e instanceof Error ? e.message : 'Analysis failed.');}
    finally {setBusy(false);}
  }
  return <><section className="input-card local-evidence"><div className="section-title"><span className="number">02</span><div><h2>Observe your opening</h2><p>Use your own clip to inspect the first 10 seconds.</p></div></div>
    <form onSubmit={submit}><label htmlFor="intro-file">Video file · up to 20 MB</label><input id="intro-file" type="file" accept="video/*" required disabled={busy} onChange={e=>setFile(e.target.files?.[0] || null)}/>
      <label className="consent"><input type="checkbox" required checked={owned} disabled={busy} onChange={e=>setOwned(e.target.checked)}/>I own this video or have permission to analyze it.</label>
      <button disabled={busy || !owned}>{busy ? 'Observing frames…' : 'Observe intro ↗'}</button>
    </form><p className="helper">Video and frames are processed temporarily and deleted after the request. No video is sent to an AI provider.</p>
    {error && <p className="error" role="alert">{error}</p>}<div role="status" aria-live="polite">{busy && <p className="loading">Measuring sampled frames and assembling the evidence report…</p>}</div>
    {evidence && <div className="visual-result"><h3>{evidence.sample_count} observed frames · {evidence.intro_seconds.toFixed(1)} seconds</h3><p className="helper">Brightness and contrast use grayscale pixel values. Frame difference measures appearance change between samples.</p>
      <div className="table-scroll"><table><caption className="sr-only">Sampled intro frame measurements</caption><thead><tr><th scope="col">Time</th><th scope="col">Brightness</th><th scope="col">Contrast</th><th scope="col">Frame difference</th></tr></thead><tbody>{evidence.samples.map(sample=><tr key={sample.timestamp}><td>{sample.timestamp.toFixed(1)}s</td><td>{sample.brightness_score.toFixed(1)}</td><td>{sample.contrast_score.toFixed(1)}</td><td>{sample.motion_score.toFixed(1)}</td></tr>)}</tbody></table></div></div>}
  </section>{evidence?.report && <><CreatorReportView report={evidence.report}/></>}</>;
}
