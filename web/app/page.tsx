'use client';
import { FormEvent, useState } from 'react';
import IntroEvidence from './intro-evidence';
type Report = {
  source_url: string; evidence_level: string; limitations: string[]; recommendation: string | null;
  video: {title: string; channel_title: string; published_at: string; views: number; likes: number; comments: number};
};
export default function Home() {
  const [url, setUrl] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [report, setReport] = useState<Report | null>(null);
  async function analyze(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(''); setReport(null);
    try {
      const response = await fetch('/api/analyses', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({url})});
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Analysis failed. Try again.');
      setReport(data);
    } catch (e) {setError(e instanceof Error ? e.message : 'Something went wrong.');}
    finally {setBusy(false);}
  }
  return <div className="shell">
    <aside><a href="/" className="brand"><span className="mark">s</span>stratify<span className="dot">.</span></a>
      <p className="nav-label">YOUR WORKSPACE</p><a className="nav-item selected" href="#workspace">◈ <span>Content intelligence</span></a>
      <div className="aside-bottom"><span className="status-dot"/> Private development<br/><small>Evidence before advice.</small></div>
    </aside>
    <main id="workspace"><header><span>Workspace <span className="slash">/</span> Content intelligence</span><span className="badge">EARLY ACCESS BUILD</span></header>
      <section className="intro"><p className="eyebrow">A CLEARER NEXT MOVE</p><h1>Understand what<br/>makes your content work.</h1><p className="lede">Start with the evidence. Find the patterns.<br/>Build your next experiment with confidence.</p></section>
      <section className="input-card"><div className="section-title"><span className="number">01</span><div><h2>Start with a video</h2><p>Add a YouTube video to build its evidence record.</p></div></div>
        <form onSubmit={analyze}><label htmlFor="video-url">YouTube video URL</label><div className="input-row"><input id="video-url" type="url" required maxLength={2048} placeholder="https://www.youtube.com/watch?v=…" value={url} onChange={e=>setUrl(e.target.value)} disabled={busy}/><button disabled={busy}>{busy ? 'Collecting evidence…' : 'Analyze video ↗'}</button></div></form>
        <p className="helper">Public metadata first. Visual insights appear only when supported by observed evidence.</p>
        {error && <p className="error" role="alert">{error}</p>}
        <div role="status" aria-live="polite">{busy && <p className="loading">Retrieving video facts from YouTube…</p>}</div>
      </section>
      {report ? <section className="report" aria-live="polite"><div className="report-heading"><div><p className="eyebrow">EVIDENCE RECORD</p><h2>{report.video.title}</h2><p>{report.video.channel_title}</p></div><span className="badge amber">METADATA ONLY</span></div>
        <div className="stats">{[['Views',report.video.views],['Likes',report.video.likes],['Comments',report.video.comments]].map(([label,value])=><div key={label}><span>{label}</span><strong>{Number(value).toLocaleString()}</strong></div>)}</div>
        <a className="source" href={report.source_url} target="_blank" rel="noopener noreferrer">View source on YouTube ↗</a>
        <div className="evidence-note"><h3>More evidence needed before an experiment</h3><ul>{report.limitations.map(item=><li key={item}>{item}</li>)}</ul></div>
      </section> : <section className="empty"><span className="empty-icon">◎</span><h3>Your next insight starts here.</h3><p>Analyze a video to see its facts, sources,<br/>and exactly where more evidence is needed.</p></section>}
      <IntroEvidence />
      <footer><span>OBSERVE <b>→</b> COMPARE <b>→</b> EXPERIMENT <b>→</b> LEARN</span><span>Built on evidence.</span></footer>
    </main></div>;
}
