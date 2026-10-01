'use client';
import {FormEvent, useEffect, useRef, useState} from 'react';
import {investigateWindow, type investigateViews, type WindowEvidence} from '../lib/views-investigation';
const number=(value:number)=>value.toLocaleString(undefined,{maximumFractionDigits:1});
export default function MatchedViews({comparison}: {comparison:ReturnType<typeof investigateViews>}) {
  const [days,setDays]=useState(7);
  const [metric,setMetric]=useState<WindowEvidence['metric']>('engaged_views');
  const [counts,setCounts]=useState<Record<string,string>>({});
  const [confirmed,setConfirmed]=useState(false);
  const [error,setError]=useState('');
  const [answer,setAnswer]=useState<ReturnType<typeof investigateWindow>|null>(null);
  const heading=useRef<HTMLHeadingElement>(null);
  useEffect(()=>{if(answer) heading.current?.focus();},[answer]);
  function invalidate(){setAnswer(null);setError('');setConfirmed(false);}
  function submit(event:FormEvent){event.preventDefault();setAnswer(null);setError('');try{setAnswer(investigateWindow(comparison,{days,metric,counts,confirmed}));}catch(failure){setError(failure instanceof Error?failure.message:'Review the entered counts.');}}
  return <section className="report-section" aria-labelledby="matched-title">
    <h3 id="matched-title">Add analytics for the same viewing window</h3>
    <p className="muted">Optional: enter counts from your channel analytics for these selected videos. These figures stay in this page and are cleared on reload or when the comparison changes. Stratify does not connect to your YouTube account or verify the numbers.</p>
    <p className="muted"><a className="source" href="https://support.google.com/youtube/answer/16766491" target="_blank" rel="noopener noreferrer">YouTube’s guide to lifespan comparisons ↗</a></p>
    <form onSubmit={submit}>
      <label htmlFor="matched-window">Time after each video was published</label><select id="matched-window" value={days} onChange={event=>{setDays(Number(event.target.value));setCounts({});invalidate();}}><option value={1}>First 24 hours</option><option value={7}>First 7 days</option><option value={28}>First 28 days</option></select>
      <label className="concern-label" htmlFor="matched-metric">Metric used for every selected video</label><select id="matched-metric" value={metric} onChange={event=>{setMetric(event.target.value as WindowEvidence['metric']);setCounts({});invalidate();}}><option value="engaged_views">Engaged views</option><option value="views">Views</option></select>
      <p className="helper">Use the same metric and completed lifespan window for every video—not a shared calendar period. Public view definitions have changed; do not mix counts with different definitions. <a className="source" href="https://support.google.com/youtube/answer/2991785" target="_blank" rel="noopener noreferrer">How YouTube counts engagement ↗</a></p>
      <div className="video-selection" role="region" aria-label="Matched viewing-window counts" tabIndex={0}>{[{name:'Recent',group:comparison.recent},{name:'Earlier',group:comparison.earlier}].map(({name,group})=><div key={name}><h4>{name} group</h4>{group.rows.map(video=><div key={video.video_id} className="video-selection-row"><label htmlFor={`matched-${video.video_id}`}>{video.title || video.video_id}<span className="muted"> — {name.toLowerCase()} group</span></label><input id={`matched-${video.video_id}`} aria-label={`Window count for ${video.title || video.video_id}`} type="text" inputMode="numeric" pattern="[0-9]+" required maxLength={16} value={counts[video.video_id]||''} onChange={event=>{setCounts({...counts,[video.video_id]:event.target.value});invalidate();}} placeholder="Unavailable? Don’t enter 0"/></div>)}</div>)}</div>
      <label className="consent"><input type="checkbox" checked={confirmed} onChange={event=>{setConfirmed(event.target.checked);setAnswer(null);setError('');}}/>I checked that every count uses this completed window and the same metric definition.</label>
      <button className="channel-submit">Review matched-window evidence</button>
    </form>
    {error && <p role="alert" className="error">{error}</p>}
    {answer && <div className="evidence-note" aria-labelledby="matched-result-title">
      <h3 id="matched-result-title" ref={heading} tabIndex={-1}>Your views investigation</h3>
      <p><strong>Based on the figures you entered:</strong> the selected recent group has {answer.difference===0?'the same':answer.difference<0?'a lower':'a higher'} median {answer.metric==='views'?'views':'engaged views'} count over the first {answer.days===1?'24 hours':`${answer.days} days`}.</p>
      <dl className="measurement-list"><div><dt>Recent group</dt><dd>{answer.recentCount} videos · median {number(answer.recentMedian)}</dd></div><div><dt>Earlier group</dt><dd>{answer.earlierCount} videos · median {number(answer.earlierMedian)}</dd></div><div><dt>Difference in medians</dt><dd>{number(answer.difference)}{answer.percent===null?' · percentage unavailable (zero baseline)':` (${number(answer.percent)}%)`}</dd></div></dl>
      <p>{answer.recentAtOrAboveEarlierMedian} of {answer.recentCount} selected recent videos are at or above the earlier group’s median. The group median does not mean every video changed in the same way.</p>
      <h3>What that tells us—and what it doesn’t</h3>
      <ul className="limits"><li>These are creator-entered figures. Stratify has not verified their source, accuracy, window or metric definition.</li>{answer.smallSample && <li>At least one group has fewer than three videos. Treat this as a small sample, not a channel-wide trend.</li>}<li>{answer.comparableByCreator?'You described the topics and formats as similar; that remains your assessment.':'Topics or formats are different or unknown. The numbers describe the selection, but do not establish a like-for-like content comparison.'}</li><li>This describes only the selected videos and metric. It does not establish statistical significance, future performance or the cause of a difference.</li></ul>
      <h3>What to investigate next</h3><p>{answer.difference===0?'The medians do not show a decrease in this selection. Revisit which videos, metric or period prompted your concern.':answer.difference>0?'The medians do not show a decrease in this selection. Check whether your concern relates to different videos, a different metric or a later part of their lifespan.':'Check impressions and traffic sources for these videos over matching windows. Those could help distinguish changes in exposure from changes in how viewers responded; they have not been measured here.'}</p><p className="muted">No evidence here justifies blaming an opening, thumbnail or topic, or prescribing a content change.</p>
    </div>}
  </section>;
}
