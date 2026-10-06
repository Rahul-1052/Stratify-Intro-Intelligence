'use client';
import {prepareCaptionComparison, type CaptionEvidence} from '../lib/caption-comparison';
import MatchedViews from './matched-views';
import {parseViewsScope, proposeScopedViews, scopeMatchesSelection, answerViewsConcern} from '../lib/views-brief';
import {FormEvent, useEffect, useRef, useState} from 'react';
import {relatedTitleGroups, comparisonTitleWarnings, proposeComparison, investigateViews, type PublicVideo, type Comparability} from '../lib/views-investigation';
const number = (value: number | null) => value === null ? 'Unavailable' : value.toLocaleString(undefined,{maximumFractionDigits:1});
export default function ViewsInvestigation({videos, fetchedAt, question = '', period = ''}: {videos: PublicVideo[]; fetchedAt: string; question?: string; period?: string}) {
  const [manual,setManual] = useState(false);
  const [selectedOnly,setSelectedOnly] = useState(false);
  const comparisonControls = useRef<HTMLDetailsElement>(null);
  const comparisonSearch = useRef<HTMLInputElement>(null);
  const [captions,setCaptions] = useState<CaptionEvidence[]>([]);
  const [captionError,setCaptionError] = useState('');
  const [retrievalNotice,setRetrievalNotice] = useState('');
  const [captionBusy,setCaptionBusy] = useState(false);
  const captionProposal = captions.length ? prepareCaptionComparison(videos,fetchedAt,captions) : null;
  const scope = parseViewsScope(period);
  const proposal = scope.kind === 'uploads' ? proposeScopedViews(videos,fetchedAt,scope) : scope.kind === 'manual' ? null : captionProposal ? captionProposal.proposal : proposeComparison(videos,fetchedAt);
  const [prepared,setPrepared] = useState(false);
  const [scopeConfirmed,setScopeConfirmed] = useState(false);
  const [search,setSearch] = useState('');
  const [page,setPage] = useState(0);
  const [selection,setSelection] = useState<Record<string,string>>({});
  const filtered = videos.filter(video => (!selectedOnly || selection[video.video_id] === 'recent' || selection[video.video_id] === 'earlier') && `${video.title} ${video.published_at || ''}`.toLowerCase().includes(search.toLowerCase()));
  const visible = filtered.slice(page * 10, page * 10 + 10);
  const warnings = comparisonTitleWarnings(videos.filter(v=>selection[v.video_id]==='recent' || selection[v.video_id]==='earlier'));
  const related = relatedTitleGroups(videos.filter(v=>selection[v.video_id]==='recent' || selection[v.video_id]==='earlier'));
  const relatedNote = related.length > 0 && <div className="evidence-note"><h4>Possible related parts</h4><p>These titles may refer to parts of the same material. Check before treating them as separate examples.</p>{related.map(group=><ul key={group[0].video_id}>{group.map(video=><li key={video.video_id}>{video.title}</li>)}</ul>)}<p className="helper">Names alone cannot confirm shared material. Different names can also refer to related videos.</p></div>;
  const [topics,setTopics] = useState<Comparability>('unknown');
  const [formats,setFormats] = useState<Comparability>('unknown');
  const [result,setResult] = useState<ReturnType<typeof investigateViews> | null>(null);
  const [error,setError] = useState('');
  const scopeMatch = result ? scope.kind === 'manual' && scopeConfirmed ? true : scopeMatchesSelection(scope,videos,fetchedAt,result) : null;
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(()=>{if (result) heading.current?.focus();},[result]);
  function invalidate() {setResult(null);setError('');setScopeConfirmed(false);}
  function reviewSelected() {
    setSelectedOnly(true);setSearch('');setPage(0);setManual(true);
    if (comparisonControls.current) comparisonControls.current.open = true;
    requestAnimationFrame(()=>comparisonSearch.current?.focus());
  }
  function investigate(event: FormEvent) {
    event.preventDefault();setError('');setResult(null);
    try {
      setResult(investigateViews(videos, videos.filter(v=>selection[v.video_id]==='recent').map(v=>v.video_id), videos.filter(v=>selection[v.video_id]==='earlier').map(v=>v.video_id), fetchedAt, topics, formats));
    } catch (failure) {setError(failure instanceof Error ? failure.message : 'Review your selection.');}
  }
  async function readCaptions(files: FileList | null) {
    if (!files?.length) return;
    setRetrievalNotice('');setCaptionBusy(true);setCaptionError('');setCaptions([]);setSelection({});setPrepared(false);invalidate();
    try {
      const batch=Array.from(files);
      if(batch.length>100 || batch.reduce((sum,file)=>sum+file.size,0)>2000000) throw new Error('Choose up to 100 caption files, with a combined size below 2 MB.');
      const evidence:CaptionEvidence[]=[];
      for(const file of batch) {
        if(!/\.(srt|vtt|txt)$/i.test(file.name)) throw new Error('Use SRT, VTT or TXT caption files.');
        const matches=videos.filter(v=>file.name.includes(v.video_id));
        if(matches.length!==1) throw new Error(`Could not match ${file.name}. Include its YouTube video ID in the filename.`);
        evidence.push({videoId:matches[0].video_id,text:await file.text(),source:'creator_caption_unverified'});
      }
      prepareCaptionComparison(videos,fetchedAt,evidence);
      setCaptions(evidence);
    } catch(failure) {setCaptionError(failure instanceof Error ? failure.message : 'Captions could not be read.');}
    finally {setCaptionBusy(false);}
  }
  async function prepare() {
    let chosen = proposal;
    if (!captions.length && scope.kind === 'default') {
      setCaptionBusy(true);setRetrievalNotice('Checking available English captions…');invalidate();
      const candidates = videos.filter(v=>v.published_at && Date.parse(fetchedAt)-Date.parse(v.published_at)>=7*86400000).sort((a,b)=>Date.parse(b.published_at!)-Date.parse(a.published_at!) || a.video_id.localeCompare(b.video_id)).slice(0,12);
      try {
        const response=await fetch('/api/public-captions',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({video_ids:candidates.map(v=>v.video_id)}),signal:AbortSignal.timeout(45000)});
        const data=await response.json();
        if(!response.ok) throw new Error(typeof data.detail==='string'?data.detail:'Captions could not be retrieved.');
        const evidence:CaptionEvidence[]=data.results.filter((r:{status:string})=>r.status==='available').map((r:{video_id:string;text:string})=>({videoId:r.video_id,text:r.text,source:'public_caption_unverified'}));
        const matched=prepareCaptionComparison(videos,fetchedAt,evidence);
        const blocked=data.results.some((r:{status:string})=>r.status==='blocked');
        setRetrievalNotice(`${evidence.length} of ${candidates.length} candidate uploads have retrieved English captions. ${blocked ? 'Retrieval was blocked; remaining requests were stopped. ' : ''}${evidence.length ? 'Caption accuracy remains unverified.' : 'This setup uses dates only; no content match was established.'}`);
        if(evidence.length) {setCaptions(evidence);chosen=matched.proposal;}
      } catch(failure) {
        setRetrievalNotice(`${failure instanceof Error ? failure.message : 'Caption retrieval failed.'} This setup uses dates only; no content match was established.`);
      } finally {setCaptionBusy(false);}
    }
    if (!chosen) {setSelection({});setPrepared(false);return;}
    setSelection(Object.fromEntries([...chosen.recent.map(v=>[v.video_id,'recent']),...chosen.earlier.map(v=>[v.video_id,'earlier'])]));
    setTopics('unknown');setFormats('unknown');setPrepared(true);setManual(false);invalidate();
  }
  const labelCounts = Object.fromEntries(warnings.map(w=>[w.label,warnings.filter(other=>other.label===w.label).length]));
  const rankedLabels = Object.keys(labelCounts).sort((a,b)=>labelCounts[b]-labelCounts[a]);
  const dominant = rankedLabels.length > 1 && labelCounts[rankedLabels[0]] > labelCounts[rankedLabels[1]] ? rankedLabels[0] : null;
  const unusual = dominant ? warnings.filter(w=>w.label!==dominant) : [];
  const mismatchNote = warnings.length > 0 && <div className="evidence-note" role="status"><h4>Possible content mismatch</h4>
    {warnings.every(w=>w.label==='full show') ? <><p>A selected title says “full show”; other selected titles do not. Check whether the groups mix full shows with other content.</p><ul>{warnings.filter(w=>w.label==='full show').map(w=><li key={w.videoId}><a className="source" href={videos.find(v=>v.video_id===w.videoId)!.source_url} target="_blank" rel="noopener noreferrer">{w.title}</a></li>)}</ul></> : dominant ? <><p>{unusual.length === 1 ? 'One selected title uses a different label:' : 'Some selected titles use different labels:'}</p><ul>{unusual.map(w=><li key={`${w.videoId}-${w.label}`}><a className="source" href={videos.find(v=>v.video_id===w.videoId)!.source_url} target="_blank" rel="noopener noreferrer">{w.title}</a> — “{w.label}”.</li>)}</ul><p className="helper">{labelCounts[dominant]} selected titles mention “{dominant}”.</p></> : <p>Selected titles use different content labels. Review whether these videos belong together.</p>}
    <p className="helper">Title clues only; formats are unverified. Use “Adjust comparison” to leave out a video if needed.</p>
    <details className="sample-details"><summary>See all title clues</summary><ul>{warnings.map(w=><li key={`${w.videoId}-${w.label}`}>{w.title} — “{w.label}”.</li>)}</ul></details></div>;
  return <section className="report-section" aria-labelledby="views-investigation-title">
    <details ref={comparisonControls} className="sample-details" open={!result}><summary>{result ? 'Adjust selected videos' : 'Choose comparison videos'}</summary>
    <h3 id="views-investigation-title">Investigate a change in views</h3>
    <p className="muted">Let Stratify prepare a starting comparison, or choose the videos yourself.</p>
    {scope.kind === 'manual' && <p className="helper">{scope.message}</p>}
    {scope.kind === 'default' && <details className="sample-details"><summary>Add captions for content-based grouping (optional)</summary><p>Supply caption files for several recent and earlier videos. Stratify can look for shared wording across different titles and screen for substantial text overlap. Supplied files are creator-provided and unverified. Neither supplied nor retrieved captions establish the video’s format.</p><label htmlFor="comparison-captions">Caption files (SRT, VTT or TXT)</label><input id="comparison-captions" type="file" multiple accept=".srt,.vtt,.txt" disabled={captionBusy} onChange={event=>{void readCaptions(event.currentTarget.files);event.currentTarget.value='';}}/><p className="helper">Include the YouTube video ID in each filename, for example 5ddEDYTFWTc.srt. Up to 100 files, 2 MB combined. Supplied files stay in this page and are cleared on reload; they are not uploaded or saved.</p>{captionError && <p role="alert" className="error">{captionError}</p>}{captionBusy && <p role="status">Reading captions…</p>}{captionProposal && <><p role="status">{captionProposal.coverage.supplied} captions available ({captions.filter(c=>c.source==='public_caption_unverified').length} retrieved automatically, {captions.filter(c=>c.source==='creator_caption_unverified').length} from supplied files); {captionProposal.coverage.usable} have enough text and meet the age cutoff. {captionProposal.coverage.overlapSkipped} screened out for substantial caption overlap.</p><button type="button" onClick={()=>{setCaptions([]);setRetrievalNotice('');setSelection({});setPrepared(false);invalidate();}}>Remove captions</button></>}</details>}
    <button type="button" onClick={()=>{void prepare();}} disabled={!proposal || captionBusy}>Prepare a comparison for me</button>{' '}<button type="button" disabled={captionBusy} onClick={()=>{setSelectedOnly(false);setManual(true);}}>Choose videos myself</button>
    {retrievalNotice && <p role="status" className="helper">{retrievalNotice}</p>}
    {captionProposal && !captionProposal.proposal && <details className="sample-details"><summary>Why no groups were prepared</summary><p>{captionProposal.diagnostics.distinct} uploads remained after text-overlap screening. The largest shared-word match set had {captionProposal.diagnostics.largestMatchSet} uploads; the best earlier group had {captionProposal.diagnostics.bestEarlierCount} strictly older matches after selecting three recent uploads.</p><p>Matching thresholds are provisional. Different wording, timing ties and unavailable captions can prevent a selection; no performance finding follows.</p></details>}
    {!proposal && scope.kind !== 'manual' && <p className="helper">{scope.kind === 'uploads' ? 'The available dates or upload coverage cannot establish your requested groups. Choose videos manually or collect a broader inventory.' : captionProposal ? 'No content-based groups were prepared. The current shared-word rules did not find three recent and three strictly older matches. This does not establish that your videos are unrelated.' : 'Not enough dated uploads for two groups of three at least 7 days old. You can choose videos manually.'}</p>}
    {prepared && <div className="evidence-note"><h4>Review the proposed groups</h4><p>{scope.kind === 'uploads' ? `We picked ${scope.recent} recent and ${scope.earlier} earlier available uploads from your requested scope. Fresh uploads are included.` : 'We picked three recent uploads and three earlier uploads, all at least 7 days old.'} Check that these videos fit your question.</p><p className="helper">{captionProposal ? 'Provisional selection using shared caption wording. Topic, format and footage independence are not verified.' : 'Provisional selection by date. Video content, formats and shared material have not been verified. Matching titles do not establish a fair comparison.'}</p>{mismatchNote}{relatedNote}<details className="sample-details"><summary>Why these videos?</summary><p>{proposal?.reason}</p>{captionProposal && <p>Caption reference: {videos.find(v=>v.video_id===captionProposal.diagnostics.referenceVideoId)?.title || 'Unavailable'}. Shared words below are measured against this reference, which may be an earlier upload.</p>}{captionProposal && <ul>{captionProposal.matches.map(match=><li key={match.videoId}>{videos.find(v=>v.video_id===match.videoId)?.title}: shared words — {match.terms.join(', ')}.</li>)}</ul>}{proposal?.cutoff && <p>Publication cutoff: {proposal.cutoff.replace('T',' ').replace(/Z$/, ' UTC')}. Uploads must be at least 168 hours old at collection; the displayed calendar date alone is not enough.</p>}<p>{scope.kind === 'uploads' ? 'The paired upload counts were applied to this public inventory. The question’s content requirements have not been interpreted.' : 'No specific period was requested. This is a default selection; the question’s content requirements have not been interpreted.'} {proposal?.excluded} other uploads are left out of this selection.</p></details><div className="measurement-list">{['recent','earlier'].map(group=><div key={group}><h4>{group==='recent'?'Recent group':'Earlier group'}</h4><ul>{videos.filter(v=>selection[v.video_id]===group).map(v=><li key={v.video_id}><a className="source" href={v.source_url} target="_blank" rel="noopener noreferrer">{v.title || 'Untitled video'}</a> — {v.published_at?.slice(0,10)}</li>)}</ul></div>)}</div><button type="button" onClick={()=>setManual(true)}>Adjust comparison</button></div>}
    {!prepared && <>{mismatchNote}{relatedNote}</>}
    {!videos.length ? <p>No public videos are available to select. A comparison cannot be made.</p> : <form onSubmit={investigate}>
      <details className="sample-details" open={manual} onToggle={event=>setManual(event.currentTarget.open)}><summary>Adjust comparison / select videos manually</summary>
        <label htmlFor="comparison-search">Find a video by title or date</label><input ref={comparisonSearch} id="comparison-search" type="search" value={search} onChange={event=>{setSearch(event.target.value);setPage(0);}} placeholder="For example: Guardian or 2026-09"/><label className="consent"><input type="checkbox" checked={selectedOnly} onChange={event=>{setSelectedOnly(event.target.checked);setPage(0);}}/>Show selected videos only</label><p className="helper">Showing {filtered.length ? page*10+1 : 0}–{Math.min(page*10+10,filtered.length)} of {filtered.length} matches. Selections stay selected across searches and pages.</p><div className="video-selection" role="region" aria-label="Videos available for comparison" tabIndex={0}>{visible.map(video=><div key={video.video_id} className="video-selection-row">
          <div><a className="source" href={video.source_url} target="_blank" rel="noopener noreferrer">{video.title || 'Untitled video'} ↗</a><p className="muted">Published: {video.published_at?.slice(0,10) || 'Unavailable'} · Public views: {number(video.views)}</p></div>
          <label><span className="sr-only">Comparison group for {video.title || video.video_id}</span><select value={selection[video.video_id] || ''} onChange={event=>{setSelection({...selection,[video.video_id]:event.target.value});setPrepared(false);invalidate();}}><option value="">Leave out</option><option value="recent">Recent group</option><option value="earlier">Earlier group</option></select></label>
        </div>)}</div>
        <button type="button" disabled={page===0} onClick={()=>setPage(page-1)}>Previous videos</button>{' '}<button type="button" disabled={(page+1)*10>=filtered.length} onClick={()=>setPage(page+1)}>Next videos</button>
      </details>
      <p className="helper">Selected: {Object.values(selection).filter(v=>v==='recent').length} recent, {Object.values(selection).filter(v=>v==='earlier').length} earlier. Each video belongs to one group.</p>
      <details className="sample-details"><summary>Check topics and formats (optional)</summary><p className="helper">If you haven’t checked, leave both as “I’m not sure.”</p><label htmlFor="view-topics">Are the selected groups about similar topics?</label><select id="view-topics" value={topics} onChange={event=>{setTopics(event.target.value as Comparability);invalidate();}}><option value="unknown">I’m not sure</option><option value="same">Yes, similar topics</option><option value="different">No, different topics</option></select>
      <label className="concern-label" htmlFor="view-formats">Do the groups use similar formats?</label><select id="view-formats" value={formats} onChange={event=>{setFormats(event.target.value as Comparability);invalidate();}}><option value="unknown">I’m not sure</option><option value="same">Yes, similar formats</option><option value="different">No, different formats</option></select>
      </details>{scope.kind === 'manual' && <label className="consent"><input type="checkbox" checked={scopeConfirmed} onChange={event=>{setScopeConfirmed(event.target.checked);setResult(null);setError('');}}/>I checked that these selected videos match my requested period.</label>}<button className="channel-submit">Compare selected public facts</button>
    </form>}
    {error && <p className="error" role="alert">{error}</p>}
    </details>
    {result && <div className="evidence-note" aria-labelledby="views-result-title">
      <h3 id="views-result-title" tabIndex={-1} ref={heading}>What the selected videos show</h3>
      {question && <p><strong>{answerViewsConcern(question,scopeMatch,result)}</strong></p>}
      <p><strong>{result.difference === null ? 'We can’t establish a difference from this selection.' : result.difference < 0 ? 'Recent videos in this selection have lower typical lifetime views.' : result.difference > 0 ? 'Recent videos in this selection have higher typical lifetime views.' : 'Both selected groups have the same typical lifetime views.'}</strong></p>
      <p><strong>{result.difference === null ? "We don’t have enough consistent facts to compare these groups." : `Typical lifetime views: ${number(result.recent.medianViews)} recent · ${number(result.earlier.medianViews)} earlier.`}</strong></p>
      <p className="muted">{result.recent.count} recent videos · {result.earlier.count} earlier videos. Selected videos only.</p>
      <p className="helper">Lifetime totals aren’t an equal-time comparison and don’t establish a channel-wide decline or its cause.</p>
      <h4>Your next step</h4>
      <p>{scopeMatch !== true ? 'Review the selection against your requested period before interpreting these numbers.' : !result.chronological ? "Adjust the groups so every recent video was published after every earlier video." : result.recent.missing || result.earlier.missing ? "Choose videos with available view counts, or add the missing figures from your YouTube Studio analytics." : result.topics !== 'same' || result.formats !== 'same' ? "Review the selected videos and keep similar content and formats together before interpreting the numbers." : "If you have access to this channel’s YouTube Studio, compare views over the same completed period after each video was published."}</p>
      {(scopeMatch !== true || !result.chronological || result.recent.missing > 0 || result.earlier.missing > 0 || result.topics !== 'same' || result.formats !== 'same') && <button type="button" onClick={reviewSelected}>Review selected videos</button>}
      <details className="sample-details"><summary>See details</summary><p className="muted">Public facts collected on {fetchedAt.slice(0,10)} (UTC). This selection does not represent the whole channel.</p><p>Question: {question || 'Not provided'}. Requested scope: {period || 'Default selection'}. {scope.kind === 'manual' && scopeConfirmed ? 'Scope match is creator-confirmed, not verified by Stratify.' : ''}</p><h4>Selected source videos</h4>{[{name:'Recent',rows:result.recent.rows},{name:'Earlier',rows:result.earlier.rows}].map(group=><div key={group.name}><p>{group.name} group</p><ul>{group.rows.map(video=><li key={video.video_id}><a className="source" href={video.source_url} target="_blank" rel="noopener noreferrer">{video.title || video.video_id}</a> — {video.views === null ? 'Views unavailable' : `${number(video.views)} lifetime views`}</li>)}</ul></div>)}<p>“Typical” means the median: the middle count after sorting, or the average of the two middle counts for an even-sized group.</p><dl className="measurement-list">{[{label:'Recent',value:result.recent},{label:'Earlier',value:result.earlier}].map(({label,value})=>{
        return <div key={label}><dt>{label} group</dt><dd>{value.count} videos; {value.available} available view counts</dd><dd>Median lifetime views: {number(value.medianViews)}</dd><dd>Age at collection: {value.newestDays === null ? 'Unavailable' : `${number(value.newestDays)}–${number(value.oldestDays)} days`}</dd></div>;
      })}</dl>
      <p>{result.difference === null ? 'The difference between groups is withheld because counts or publication order do not support it.' : `Recent median lifetime views are ${result.difference === 0 ? 'equal to' : result.difference < 0 ? 'lower than' : 'higher than'} the earlier median. Difference: ${number(result.difference)} views${result.percent === null ? ' (percentage unavailable because the earlier median is zero)' : ` (${number(result.percent)}%)`}.`}</p>
      <ul className="limits">{result.checks.map(check=><li key={check}>{check}</li>)}</ul>
      <p>Content, formats and independent footage have not been verified. {result.nextStep}</p><p className="muted">Stratify has not retrieved private analytics. This comparison alone does not justify a content change.</p>
      </details>
      <MatchedViews comparison={result} question={question} scopeMatch={scopeMatch}/>
    </div>}
  </section>;
}
