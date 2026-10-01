'use client';
import {FormEvent, useRef, useState} from 'react';
type Workspace = {
  concern: string; fetched_at: string; limitations: string[];
  channel: {title: string; source_url: string; created_at: string | null; subscribers: number | null; video_count: number | null};
  coverage: {entries_checked: number; videos_available: number; unavailable_entries: number; more_uploads_available: boolean; uploads_playlist_available: boolean; oldest_published_at: string | null; newest_published_at: string | null};
  videos: {video_id: string; title: string; source_url: string; published_at: string | null; duration: string | null; views: number | null; likes: number | null; comments: number | null}[];
};
const count = (value: number | null) => value === null ? 'Unavailable' : value.toLocaleString();
const date = (value: string | null) => value ? value.slice(0, 10) : 'Unavailable';
export default function ChannelWorkspace() {
  const [channel, setChannel] = useState('');
  const [concern, setConcern] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  async function collect(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(''); setWorkspace(null);
    try {
      const response = await fetch('/api/channel-workspace', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({channel, concern})});
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Channel facts could not be collected. Try again.');
      setWorkspace(data);
      requestAnimationFrame(() => heading.current?.focus());
    } catch (failure) {setError(failure instanceof Error ? failure.message : 'Try again.');}
    finally {setBusy(false);}
  }
  return <>
    <section className="input-card" aria-labelledby="channel-intake-title">
      <div className="section-title"><span className="number">01</span><div><h2 id="channel-intake-title">Start with your channel</h2><p>Tell us what you want to understand. You don’t need technical terms.</p></div></div>
      <form onSubmit={collect}>
        <label htmlFor="channel-link">YouTube channel link or @handle</label>
        <input id="channel-link" required maxLength={2048} placeholder="https://www.youtube.com/@yourchannel" value={channel} onChange={event => setChannel(event.target.value)} disabled={busy}/>
        <label className="concern-label" htmlFor="channel-concern">What would you like help understanding about your channel?</label>
        <textarea id="channel-concern" required maxLength={2000} rows={3} aria-describedby="concern-help" placeholder="My recent videos are getting fewer views. What should I investigate?" value={concern} onChange={event => setConcern(event.target.value)} disabled={busy}/>
        <p id="concern-help" className="helper">You can ask about a problem, a new direction, or what’s working. Up to 2,000 characters.</p>
        <button className="channel-submit" disabled={busy}>{busy ? 'Collecting channel facts…' : 'Build channel evidence record'}</button>
      </form>
      <p className="helper">This first step collects public facts for up to 100 upload entries. Understanding your concern and answering it comes next.</p>
      {error && <p role="alert" className="error">{error}</p>}
      <div role="status">{busy && <p className="loading">Retrieving channel and upload facts from YouTube…</p>}</div>
    </section>
    {workspace && <section className="report" aria-labelledby="channel-result-title">
      <p className="eyebrow">CHANNEL EVIDENCE RECORD</p>
      <h2 id="channel-result-title" tabIndex={-1} ref={heading}>{workspace.channel.title}</h2>
      <a className="source" href={workspace.channel.source_url} target="_blank" rel="noopener noreferrer">View channel on YouTube ↗</a>
      <div className="report-section"><h3>Your concern</h3><p>{workspace.concern}</p><p className="muted">Recorded in your words. These facts do not yet answer your concern.</p></div>
      <dl className="measurement-list">
        <div><dt>Subscribers reported by YouTube</dt><dd>{count(workspace.channel.subscribers)}</dd></div>
        <div><dt>Public video count reported by YouTube</dt><dd>{count(workspace.channel.video_count)}</dd></div>
        <div><dt>Channel created</dt><dd>{date(workspace.channel.created_at)}</dd></div>
        <div><dt>Facts collected</dt><dd>{date(workspace.fetched_at)} (UTC)</dd></div>
      </dl>
      <div className="evidence-note"><h3>What this sample covers</h3>
        <p>{workspace.coverage.videos_available} unique videos available from {workspace.coverage.entries_checked} upload entries checked. {workspace.coverage.unavailable_entries} entries unavailable.</p>
        <p>Publication dates: {date(workspace.coverage.oldest_published_at)} to {date(workspace.coverage.newest_published_at)}.</p>
        <p>{!workspace.coverage.uploads_playlist_available ? 'No uploads playlist was available.' : workspace.coverage.more_uploads_available ? 'More uploads exist beyond this sample.' : 'The uploads playlist returned no further page. This does not include private or unavailable videos.'}</p>
      </div>
      <details className="sample-details"><summary>Inspect the public video facts ({workspace.videos.length})</summary>
        <p className="muted">Upload order. Formats have not been classified; counts are not a performance ranking. Duration is the value reported by YouTube (for example, PT5M means five minutes).</p>
        <div className="table-scroll" role="region" aria-label="Channel video facts" tabIndex={0}>
          <table><caption className="sr-only">Public upload sample with source links and available counts</caption><thead><tr>{['Video', 'Published', 'Duration', 'Views', 'Likes', 'Comments'].map(label => <th key={label} scope="col">{label}</th>)}</tr></thead>
            <tbody>{workspace.videos.map(video => <tr key={video.video_id}><td><a className="source" href={video.source_url} target="_blank" rel="noopener noreferrer">{video.title || 'Untitled video'} ↗</a></td><td>{date(video.published_at)}</td><td>{video.duration || 'Unavailable'}</td><td>{count(video.views)}</td><td>{count(video.likes)}</td><td>{count(video.comments)}</td></tr>)}</tbody>
          </table>
        </div>
      </details>
      <div className="evidence-note"><h3>What we can’t conclude yet</h3><ul>{workspace.limitations.map(item => <li key={item}>{item}</li>)}</ul></div>
    </section>}
  </>;
}
