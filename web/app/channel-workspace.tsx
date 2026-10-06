'use client';
import ViewsInvestigation from './views-investigation';
import {FormEvent, useRef, useState} from 'react';
type Workspace = {
  inquiry: {question: string; focus: string; period: string; evidence_needed: string[]};
  concern: string; fetched_at: string; limitations: string[];
  channel: {title: string; source_url: string; created_at: string | null; subscribers: number | null; video_count: number | null};
  coverage: {entries_checked: number; videos_available: number; unavailable_entries: number; more_uploads_available: boolean; uploads_playlist_available: boolean; oldest_published_at: string | null; newest_published_at: string | null};
  videos: {video_id: string; title: string; source_url: string; published_at: string | null; duration: string | null; views: number | null; likes: number | null; comments: number | null}[];
};
const count = (value: number | null) => value === null ? 'Unavailable' : value.toLocaleString();
const date = (value: string | null) => value ? value.slice(0, 10) : 'Unavailable';
function readableDuration(value: string | null) {
  const match = value?.match(/^P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?$/);
  if (!match) return 'Unavailable';
  const seconds = Number(match[1] || 0)*86400 + Number(match[2] || 0)*3600 + Number(match[3] || 0)*60 + Number(match[4] || 0);
  if (!seconds) return 'Unavailable';
  return [Math.floor(seconds/3600) ? `${Math.floor(seconds/3600)} hr` : '', Math.floor(seconds%3600/60) ? `${Math.floor(seconds%3600/60)} min` : '', seconds%60 ? `${seconds%60} sec` : ''].filter(Boolean).join(' ');
}
const focuses = [
  ['reach', 'Views — compare recent and earlier videos'], ['returning_viewers', 'Returning viewers — who comes back'],
  ['subscriptions', 'Subscribers — who subscribes after watching'], ['content_direction', 'Choosing what to create'],
  ['packaging', 'Titles and thumbnails'], ['watching', 'Understanding the viewing experience'],
  ['open_question', 'Something else / help me explore'],
];
export default function ChannelWorkspace() {
  const [channel, setChannel] = useState('');
  const [concern, setConcern] = useState('');
  const [reviewing, setReviewing] = useState(false);
  const [focus, setFocus] = useState('');
  const [question, setQuestion] = useState('');
  const [period, setPeriod] = useState('');
  const reviewHeading = useRef<HTMLHeadingElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const channelInput = useRef<HTMLInputElement>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  async function collect(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(''); setWorkspace(null);
    try {
      const response = await fetch('/api/channel-workspace', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({channel, concern, inquiry: {focus, question, period, confirmed: true}})});
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Channel facts could not be collected. Try again.');
      setWorkspace(data);
      requestAnimationFrame(() => heading.current?.focus());
    } catch (failure) {setError(failure instanceof Error ? failure.message : 'Try again.');}
    finally {setBusy(false);}
  }
  function review(event: FormEvent) {
    event.preventDefault(); setWorkspace(null); setError(''); setQuestion(concern.trim()); setFocus(''); setPeriod(''); setReviewing(true);
    requestAnimationFrame(() => reviewHeading.current?.focus());
  }
  function editIntake() {setReviewing(false); setWorkspace(null); setError(''); requestAnimationFrame(() => channelInput.current?.focus());}
  return <>
    <details className="input-card workflow-step" open={!reviewing}><summary>1. Channel and original concern</summary>
      <div className="section-title"><span className="number">01</span><div><h2 id="channel-intake-title">Start with your channel</h2><p>Tell us what you want to understand. You don’t need technical terms.</p></div></div>
      <form onSubmit={review}>
        <label htmlFor="channel-link">YouTube channel link or @handle</label>
        <input ref={channelInput} id="channel-link" required maxLength={2048} placeholder="https://www.youtube.com/@yourchannel" value={channel} onChange={event => setChannel(event.target.value)} disabled={busy || reviewing}/>
        <label className="concern-label" htmlFor="channel-concern">What would you like help understanding about your channel?</label>
        <textarea id="channel-concern" required maxLength={2000} rows={3} aria-describedby="concern-help" placeholder="My recent videos are getting fewer views. What should I investigate?" value={concern} onChange={event => setConcern(event.target.value)} disabled={busy || reviewing}/>
        <p id="concern-help" className="helper">You can ask about a problem, a new direction, or what’s working. Up to 2,000 characters.</p>
        <button className="channel-submit" disabled={busy || reviewing}>Review my question</button>
      </form>
      <p className="helper">First confirm what you want investigated. Then collect public facts for up to 100 upload entries.</p>
    </details>
    {error && <p role="alert" className="error">{error}</p>}
    <div role="status">{busy && <p className="loading">Retrieving channel and upload facts from YouTube…</p>}</div>
    {reviewing && <details className="report workflow-step" open={!workspace}><summary>2. Review or edit your investigation</summary>
      <h2 id="inquiry-title" tabIndex={-1} ref={reviewHeading}>Let’s make sure we understand your question</h2>
      <p className="muted">What matters most here? Choose a starting point. You can include other concerns in your question.</p>
      <form onSubmit={collect}>
        <label htmlFor="inquiry-focus">What would you like to investigate first?</label>
        <select id="inquiry-focus" required value={focus} onChange={event => {setFocus(event.target.value); setWorkspace(null);}} disabled={busy}>
          <option value="" disabled>Choose what you want to understand</option>{focuses.map(([value,label]) => <option key={value} value={value}>{label}</option>)}
        </select>
        <p className="helper">Asking whether views changed? Choose “Views — compare recent and earlier videos.” Returning viewers and subscribers are different questions.</p>{focus && focus !== 'reach' && <p className="evidence-note">This starting point currently collects public facts and lists the evidence needed. It does not yet generate an answer for this question.</p>}
        <label className="concern-label" htmlFor="inquiry-question">The question you want Stratify to investigate</label>
        <textarea id="inquiry-question" required maxLength={2000} rows={3} value={question} onChange={event => {setQuestion(event.target.value); setWorkspace(null);}} disabled={busy} aria-describedby="inquiry-help"/>
        <p id="inquiry-help" className="helper">Keep or edit your original words. Include examples or a decision you need help making. Selecting a focus doesn’t establish the cause of a problem.</p>
        <label className="concern-label" htmlFor="inquiry-period">Which period or videos do you mean? (optional)</label>
        <input id="inquiry-period" maxLength={200} value={period} onChange={event => {setPeriod(event.target.value); setWorkspace(null);}} disabled={busy} placeholder="For example: my last six uploads, compared with earlier tutorials"/>
        <p className="helper">This describes your intended scope. The public upload sample may not cover it, and has not yet been filtered to match it.</p>
        <div className="inquiry-actions"><button disabled={busy}>{busy ? 'Collecting channel facts…' : 'Confirm question and collect facts'}</button>{!workspace && <button type="button" className="secondary" onClick={editIntake} disabled={busy}>Edit channel or original concern</button>}</div>
      </form>
    </details>}
    {workspace && <section className="report" aria-labelledby="channel-result-title">
      <p className="eyebrow">CHANNEL EVIDENCE RECORD</p><button type="button" className="secondary" onClick={editIntake}>Edit channel or original concern</button>
      <h2 id="channel-result-title" tabIndex={-1} ref={heading}>{workspace.channel.title}</h2>
      <a className="source" href={workspace.channel.source_url} target="_blank" rel="noopener noreferrer">View channel on YouTube ↗</a>
      <div className="report-section"><h3>Your confirmed investigation</h3><p>{workspace.inquiry.question}</p>
      <details className="sample-details"><summary>Original concern, scope and evidence requirements</summary><p>Original concern: {workspace.concern}</p><p className="muted">Starting point: {focuses.find(([value]) => value === workspace.inquiry.focus)?.[1]}.</p><p className="muted">Requested scope: {workspace.inquiry.period || 'Not specified yet'}.</p><ul className="limits">{workspace.inquiry.evidence_needed.map(item => <li key={item}>{item === 'The concern is recorded in your words; it has not yet been interpreted or answered.' ? 'Collecting public facts alone does not answer your question. Any comparison is limited to its selected videos and available evidence.' : item}</li>)}</ul><p className="muted">These are evidence requirements, not findings. The public facts do not provide all of them.</p></details></div>
      <p className="helper">Sample: {workspace.coverage.videos_available} available videos from {workspace.coverage.entries_checked} upload entries. {workspace.coverage.more_uploads_available ? 'More uploads exist beyond this sample.' : 'Private or unavailable videos are not included.'}</p>
      <details className="sample-details"><summary>Channel facts and collection coverage</summary>
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
      </details>
      <details className="sample-details"><summary>Inspect the public video facts ({workspace.videos.length})</summary>
        <p className="muted">Upload order. Formats have not been classified; counts are not a performance ranking. Durations are reported by YouTube. A missing or zero duration is shown as unavailable; it does not identify the video’s format.</p>
        <div className="table-scroll" role="region" aria-label="Channel video facts" tabIndex={0}>
          <table><caption className="sr-only">Public upload sample with source links and available counts</caption><thead><tr>{['Video', 'Published', 'Duration', 'Views', 'Likes', 'Comments'].map(label => <th key={label} scope="col">{label}</th>)}</tr></thead>
            <tbody>{workspace.videos.map(video => <tr key={video.video_id}><td><a className="source" href={video.source_url} target="_blank" rel="noopener noreferrer">{video.title || 'Untitled video'} ↗</a></td><td>{date(video.published_at)}</td><td>{readableDuration(video.duration)}</td><td>{count(video.views)}</td><td>{count(video.likes)}</td><td>{count(video.comments)}</td></tr>)}</tbody>
          </table>
        </div>
      </details>
      {workspace.inquiry.focus === 'reach' && <ViewsInvestigation key={workspace.fetched_at} videos={workspace.videos} fetchedAt={workspace.fetched_at}/>}
      <details className="sample-details"><summary>Channel evidence limits</summary><ul>{workspace.limitations.map(item => <li key={item}>{item === 'The concern is recorded in your words; it has not yet been interpreted or answered.' ? 'Collecting public facts alone does not answer your question. Any comparison is limited to its selected videos and available evidence.' : item}</li>)}</ul></details>
    </section>}
  </>;
}
