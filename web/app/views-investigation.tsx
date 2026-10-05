'use client';
import MatchedViews from './matched-views';
import {FormEvent, useEffect, useRef, useState} from 'react';
import {comparisonTitleWarnings, proposeComparison, investigateViews, type PublicVideo, type Comparability} from '../lib/views-investigation';
const number = (value: number | null) => value === null ? 'Unavailable' : value.toLocaleString(undefined,{maximumFractionDigits:1});
export default function ViewsInvestigation({videos, fetchedAt}: {videos: PublicVideo[]; fetchedAt: string}) {
  const [manual,setManual] = useState(false);
  const proposal = proposeComparison(videos,fetchedAt);
  const [prepared,setPrepared] = useState(false);
  const [search,setSearch] = useState('');
  const [page,setPage] = useState(0);
  const filtered = videos.filter(video => `${video.title} ${video.published_at || ''}`.toLowerCase().includes(search.toLowerCase()));
  const visible = filtered.slice(page * 10, page * 10 + 10);
  const [selection,setSelection] = useState<Record<string,string>>({});
  const warnings = comparisonTitleWarnings(videos.filter(v=>selection[v.video_id]==='recent' || selection[v.video_id]==='earlier'));
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
  function prepare() {
    if (!proposal) return;
    setSelection(Object.fromEntries([...proposal.recent.map(v=>[v.video_id,'recent']),...proposal.earlier.map(v=>[v.video_id,'earlier'])]));
    setTopics('unknown');setFormats('unknown');setPrepared(true);setManual(false);invalidate();
  }
  return <section className="report-section" aria-labelledby="views-investigation-title">
    <h3 id="views-investigation-title">Investigate a change in views</h3>
    <p className="muted">Let Stratify prepare a starting comparison, or choose the videos yourself.</p>
    <button type="button" onClick={prepare} disabled={!proposal}>Prepare a comparison for me</button>{' '}<button type="button" onClick={()=>{setManual(true);}}>Choose videos myself</button>
    {!proposal && <p className="helper">Not enough dated uploads for two groups of three at least 7 days old. You can choose videos manually.</p>}
    {prepared && <div className="evidence-note"><h4>Review the proposed groups</h4><p>We picked three recent uploads and three earlier uploads, all at least 7 days old. Check that these videos fit your question.</p><p className="helper">Topics and formats still need review.</p><details className="sample-details"><summary>Why these videos?</summary><p>{proposal?.reason}</p><p>Your question and requested period have not been interpreted or applied. {proposal?.excluded} other uploads are left out of this selection.</p></details><div className="measurement-list">{['recent','earlier'].map(group=><div key={group}><h4>{group==='recent'?'Recent group':'Earlier group'}</h4><ul>{videos.filter(v=>selection[v.video_id]===group).map(v=><li key={v.video_id}><a className="source" href={v.source_url} target="_blank" rel="noopener noreferrer">{v.title || 'Untitled video'}</a> — {v.published_at?.slice(0,10)}</li>)}</ul></div>)}</div><button type="button" onClick={()=>setManual(true)}>Adjust comparison</button></div>}
    {!videos.length ? <p>No public videos are available to select. A comparison cannot be made.</p> : <form onSubmit={investigate}>
      <details className="sample-details" open={manual} onToggle={event=>setManual(event.currentTarget.open)}><summary>Adjust comparison / select videos manually</summary>
        <label htmlFor="comparison-search">Find a video by title or date</label><input id="comparison-search" type="search" value={search} onChange={event=>{setSearch(event.target.value);setPage(0);}} placeholder="For example: Guardian or 2026-09"/><p className="helper">Showing {filtered.length ? page*10+1 : 0}–{Math.min(page*10+10,filtered.length)} of {filtered.length} matches. Selections stay selected across searches and pages.</p><div className="video-selection" role="region" aria-label="Videos available for comparison" tabIndex={0}>{visible.map(video=><div key={video.video_id} className="video-selection-row">
          <div><a className="source" href={video.source_url} target="_blank" rel="noopener noreferrer">{video.title || 'Untitled video'} ↗</a><p className="muted">Published: {video.published_at?.slice(0,10) || 'Unavailable'} · Public views: {number(video.views)}</p></div>
          <label><span className="sr-only">Comparison group for {video.title || video.video_id}</span><select value={selection[video.video_id] || ''} onChange={event=>{setSelection({...selection,[video.video_id]:event.target.value});setPrepared(false);invalidate();}}><option value="">Leave out</option><option value="recent">Recent group</option><option value="earlier">Earlier group</option></select></label>
        </div>)}</div>
        <button type="button" disabled={page===0} onClick={()=>setPage(page-1)}>Previous videos</button>{' '}<button type="button" disabled={(page+1)*10>=filtered.length} onClick={()=>setPage(page+1)}>Next videos</button>
      </details>
      {warnings.length > 0 && <div className="evidence-note" role="status"><h4>Possible content mismatch</h4><p>Selected titles use different labels. This is a clue to review, not verified video analysis. Adjust the groups if needed.</p><ul>{warnings.map(w=><li key={`${w.videoId}-${w.label}`}><a className="source" href={videos.find(v=>v.video_id===w.videoId)!.source_url} target="_blank" rel="noopener noreferrer">{w.title}</a>: title mentions “{w.label}”.</li>)}</ul></div>}
      <p className="helper">Selected: {Object.values(selection).filter(v=>v==='recent').length} recent, {Object.values(selection).filter(v=>v==='earlier').length} earlier. Each video belongs to one group.</p>
      <details className="sample-details"><summary>Check topics and formats (optional)</summary><p className="helper">If you haven’t checked, leave both as “I’m not sure.”</p><label htmlFor="view-topics">Are the selected groups about similar topics?</label><select id="view-topics" value={topics} onChange={event=>{setTopics(event.target.value as Comparability);invalidate();}}><option value="unknown">I’m not sure</option><option value="same">Yes, similar topics</option><option value="different">No, different topics</option></select>
      <label className="concern-label" htmlFor="view-formats">Do the groups use similar formats?</label><select id="view-formats" value={formats} onChange={event=>{setFormats(event.target.value as Comparability);invalidate();}}><option value="unknown">I’m not sure</option><option value="same">Yes, similar formats</option><option value="different">No, different formats</option></select>
      </details><button className="channel-submit">Compare selected public facts</button>
    </form>}
    {error && <p className="error" role="alert">{error}</p>}
    {result && <div className="evidence-note" aria-labelledby="views-result-title">
      <h3 id="views-result-title" tabIndex={-1} ref={heading}>What the selected videos show</h3>
      <p className="muted">Source: this channel’s public facts collected on {fetchedAt.slice(0,10)} (UTC). This selection does not represent every video on the channel.</p>
      <p><strong>{result.difference === null ? 'We can’t establish a difference from this selection.' : result.difference < 0 ? 'The selected recent videos have a lower middle lifetime view count. This alone does not prove a performance decline.' : result.difference > 0 ? 'The selected recent videos have a higher middle lifetime view count. This selection does not show fewer public views.' : 'The selected groups have the same middle lifetime view count.'}</strong></p>
      <p><strong>{result.difference === null ? "We don’t have enough consistent facts to compare these groups." : `The middle lifetime view count is ${number(result.recent.medianViews)} for your recent videos and ${number(result.earlier.medianViews)} for your earlier videos.`}</strong></p><p>Older videos have had more time to collect views. These totals alone don’t show whether recent videos performed worse over the same amount of time.</p><details className="sample-details"><summary>See the numbers and comparison limits</summary><dl className="measurement-list">{[{label:'Recent',value:result.recent},{label:'Earlier',value:result.earlier}].map(({label,value})=>{
        return <div key={label}><dt>{label} group</dt><dd>{value.count} videos; {value.available} available view counts</dd><dd>Median lifetime views: {number(value.medianViews)}</dd><dd>Age at collection: {value.newestDays === null ? 'Unavailable' : `${number(value.newestDays)}–${number(value.oldestDays)} days`}</dd></div>;
      })}</dl>
      <p>{result.difference === null ? 'The difference between groups is withheld because counts or publication order do not support it.' : `Recent median lifetime views are ${result.difference === 0 ? 'equal to' : result.difference < 0 ? 'lower than' : 'higher than'} the earlier median. Difference: ${number(result.difference)} views${result.percent === null ? ' (percentage unavailable because the earlier median is zero)' : ` (${number(result.percent)}%)`}.`}</p>
      <h3>Limits of this comparison</h3><ul className="limits">{result.checks.map(check=><li key={check}>{check}</li>)}</ul>
      </details><h3>What to do next</h3><p>{result.nextStep}</p><p className="muted">Stratify has not retrieved those private analytics. No content change or experiment is justified by this comparison alone.</p>
      <MatchedViews comparison={result}/>
    </div>}
  </section>;
}
