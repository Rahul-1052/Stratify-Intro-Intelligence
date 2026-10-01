'use client';
import MatchedViews from './matched-views';
import {FormEvent, useEffect, useRef, useState} from 'react';
import {investigateViews, type PublicVideo, type Comparability} from '../lib/views-investigation';
const number = (value: number | null) => value === null ? 'Unavailable' : value.toLocaleString(undefined,{maximumFractionDigits:1});
export default function ViewsInvestigation({videos, fetchedAt}: {videos: PublicVideo[]; fetchedAt: string}) {
  const [selection,setSelection] = useState<Record<string,string>>({});
  const [topics,setTopics] = useState<Comparability>('unknown');
  const [formats,setFormats] = useState<Comparability>('unknown');
  const [result,setResult] = useState<ReturnType<typeof investigateViews> | null>(null);
  const [error,setError] = useState('');
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(()=>{if (result) heading.current?.focus();},[result]);
  function invalidate() {setResult(null);setError('');}
  function investigate(event: FormEvent) {
    event.preventDefault();setError('');setResult(null);
    try {
      setResult(investigateViews(videos, videos.filter(v=>selection[v.video_id]==='recent').map(v=>v.video_id), videos.filter(v=>selection[v.video_id]==='earlier').map(v=>v.video_id), fetchedAt, topics, formats));
    } catch (failure) {setError(failure instanceof Error ? failure.message : 'Review your selection.');}
  }
  return <section className="report-section" aria-labelledby="views-investigation-title">
    <h3 id="views-investigation-title">Investigate a change in views</h3>
    <p className="muted">Choose the videos you mean. Compare a recent group with an earlier group; leave other videos out. Start with similar topics and formats where possible.</p>
    {!videos.length ? <p>No public videos are available to select. A comparison cannot be made.</p> : <form onSubmit={investigate}>
      <details className="sample-details" open><summary>Select videos for the comparison</summary>
        <div className="video-selection" role="region" aria-label="Videos available for comparison" tabIndex={0}>{videos.map(video=><div key={video.video_id} className="video-selection-row">
          <div><a className="source" href={video.source_url} target="_blank" rel="noopener noreferrer">{video.title || 'Untitled video'} ↗</a><p className="muted">Published: {video.published_at?.slice(0,10) || 'Unavailable'} · Public views: {number(video.views)}</p></div>
          <label><span className="sr-only">Comparison group for {video.title || video.video_id}</span><select value={selection[video.video_id] || ''} onChange={event=>{setSelection({...selection,[video.video_id]:event.target.value});invalidate();}}><option value="">Leave out</option><option value="recent">Recent group</option><option value="earlier">Earlier group</option></select></label>
        </div>)}</div>
      </details>
      <p className="helper">Selected: {Object.values(selection).filter(v=>v==='recent').length} recent, {Object.values(selection).filter(v=>v==='earlier').length} earlier. Each video belongs to one group.</p>
      <label htmlFor="view-topics">Are the selected groups about similar topics?</label><select id="view-topics" value={topics} onChange={event=>{setTopics(event.target.value as Comparability);invalidate();}}><option value="unknown">I’m not sure</option><option value="same">Yes, similar topics</option><option value="different">No, different topics</option></select>
      <label className="concern-label" htmlFor="view-formats">Do the groups use similar formats?</label><select id="view-formats" value={formats} onChange={event=>{setFormats(event.target.value as Comparability);invalidate();}}><option value="unknown">I’m not sure</option><option value="same">Yes, similar formats</option><option value="different">No, different formats</option></select>
      <button className="channel-submit">Compare selected public facts</button>
    </form>}
    {error && <p className="error" role="alert">{error}</p>}
    {result && <div className="evidence-note" aria-labelledby="views-result-title">
      <h3 id="views-result-title" tabIndex={-1} ref={heading}>What the selected videos show</h3>
      <p className="muted">Source: this channel’s public facts collected on {fetchedAt.slice(0,10)} (UTC). This selection does not represent every video on the channel.</p>
      <dl className="measurement-list">{[{label:'Recent',value:result.recent},{label:'Earlier',value:result.earlier}].map(({label,value})=>{
        return <div key={label}><dt>{label} group</dt><dd>{value.count} videos; {value.available} available view counts</dd><dd>Median lifetime views: {number(value.medianViews)}</dd><dd>Age at collection: {value.newestDays === null ? 'Unavailable' : `${number(value.newestDays)}–${number(value.oldestDays)} days`}</dd></div>;
      })}</dl>
      <p>{result.difference === null ? 'The difference between groups is withheld because counts or publication order do not support it.' : `Recent median lifetime views are ${result.difference === 0 ? 'equal to' : result.difference < 0 ? 'lower than' : 'higher than'} the earlier median. Difference: ${number(result.difference)} views${result.percent === null ? ' (percentage unavailable because the earlier median is zero)' : ` (${number(result.percent)}%)`}.`}</p>
      <h3>Limits of this comparison</h3><ul className="limits">{result.checks.map(check=><li key={check}>{check}</li>)}</ul>
      <p><strong>{result.conclusion}</strong></p><h3>Next evidence to check</h3><p>{result.nextStep}</p><p className="muted">Stratify has not retrieved those private analytics. No content change or experiment is justified by this comparison alone.</p>
      <MatchedViews comparison={result}/>
    </div>}
  </section>;
}
