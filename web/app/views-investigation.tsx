'use client';
import {prepareCaptionComparison, type CaptionEvidence} from '../lib/caption-comparison';
import MatchedViews from './matched-views';
import {FormEvent, useEffect, useRef, useState} from 'react';
import {relatedTitleGroups, comparisonTitleWarnings, proposeComparison, investigateViews, type PublicVideo, type Comparability} from '../lib/views-investigation';
const number = (value: number | null) => value === null ? 'Unavailable' : value.toLocaleString(undefined,{maximumFractionDigits:1});
export default function ViewsInvestigation({videos, fetchedAt}: {videos: PublicVideo[]; fetchedAt: string}) {
  const [manual,setManual] = useState(false);
  const [captions,setCaptions] = useState<CaptionEvidence[]>([]);
  const [captionError,setCaptionError] = useState('');
  const [retrievalNotice,setRetrievalNotice] = useState('');
  const [captionBusy,setCaptionBusy] = useState(false);
  const captionProposal = captions.length ? prepareCaptionComparison(videos,fetchedAt,captions) : null;
  const proposal = captionProposal ? captionProposal.proposal : proposeComparison(videos,fetchedAt);
  const [prepared,setPrepared] = useState(false);
  const [search,setSearch] = useState('');
  const [page,setPage] = useState(0);
  const filtered = videos.filter(video => `${video.title} ${video.published_at || ''}`.toLowerCase().includes(search.toLowerCase()));
  const visible = filtered.slice(page * 10, page * 10 + 10);
  const [selection,setSelection] = useState<Record<string,string>>({});
  const warnings = comparisonTitleWarnings(videos.filter(v=>selection[v.video_id]==='recent' || selection[v.video_id]==='earlier'));
  const related = relatedTitleGroups(videos.filter(v=>selection[v.video_id]==='recent' || selection[v.video_id]==='earlier'));
  const relatedNote = related.length > 0 && <div className="evidence-note"><h4>Possible related parts</h4><p>These titles may refer to parts of the same material. Check before treating them as separate examples.</p>{related.map(group=><ul key={group[0].video_id}>{group.map(video=><li key={video.video_id}>{video.title}</li>)}</ul>)}<p className="helper">Names alone cannot confirm shared material. Different names can also refer to related videos.</p></div>;
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
    if (!captions.length) {
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
    <h3 id="views-investigation-title">Investigate a change in views</h3>
    <p className="muted">Let Stratify prepare a starting comparison, or choose the videos yourself.</p>
    <details className="sample-details"><summary>Add captions for content-based grouping (optional)</summary><p>Supply caption files for several recent and earlier videos. Stratify can look for shared wording across different titles and screen for substantial text overlap. Supplied files are creator-provided and unverified. Neither supplied nor retrieved captions establish the video’s format.</p><label htmlFor="comparison-captions">Caption files (SRT, VTT or TXT)</label><input id="comparison-captions" type="file" multiple accept=".srt,.vtt,.txt" disabled={captionBusy} onChange={event=>{void readCaptions(event.currentTarget.files);event.currentTarget.value='';}}/><p className="helper">Include the YouTube video ID in each filename, for example 5ddEDYTFWTc.srt. Up to 100 files, 2 MB combined. Supplied files stay in this page and are cleared on reload; they are not uploaded or saved.</p>{captionError && <p role="alert" className="error">{captionError}</p>}{captionBusy && <p role="status">Reading captions…</p>}{captionProposal && <><p role="status">{captionProposal.coverage.supplied} captions available ({captions.filter(c=>c.source==='public_caption_unverified').length} retrieved automatically, {captions.filter(c=>c.source==='creator_caption_unverified').length} from supplied files); {captionProposal.coverage.usable} have enough text and meet the age cutoff. {captionProposal.coverage.overlapSkipped} screened out for substantial caption overlap.</p><button type="button" onClick={()=>{setCaptions([]);setRetrievalNotice('');setSelection({});setPrepared(false);invalidate();}}>Remove captions</button></>}</details>
    <button type="button" onClick={()=>{void prepare();}} disabled={!proposal || captionBusy}>Prepare a comparison for me</button>{' '}<button type="button" disabled={captionBusy} onClick={()=>{setManual(true);}}>Choose videos myself</button>
    {retrievalNotice && <p role="status" className="helper">{retrievalNotice}</p>}
    {captionProposal && !captionProposal.proposal && <details className="sample-details"><summary>Why no groups were prepared</summary><p>{captionProposal.diagnostics.distinct} uploads remained after text-overlap screening. The largest shared-word match set had {captionProposal.diagnostics.largestMatchSet} uploads; the best earlier group had {captionProposal.diagnostics.bestEarlierCount} strictly older matches after selecting three recent uploads.</p><p>Matching thresholds are provisional. Different wording, timing ties and unavailable captions can prevent a selection; no performance finding follows.</p></details>}
    {!proposal && <p className="helper">{captionProposal ? 'No content-based groups were prepared. The current shared-word rules did not find three recent and three strictly older matches. This does not establish that your videos are unrelated.' : 'Not enough dated uploads for two groups of three at least 7 days old. You can choose videos manually.'}</p>}
    {prepared && <div className="evidence-note"><h4>Review the proposed groups</h4><p>We picked three recent uploads and three earlier uploads, all at least 7 days old. Check that these videos fit your question.</p><p className="helper">{captionProposal ? 'Provisional selection using shared caption wording. Topic, format and footage independence are not verified.' : 'Provisional selection by date. Video content, formats and shared material have not been verified. Matching titles do not establish a fair comparison.'}</p>{mismatchNote}{relatedNote}<details className="sample-details"><summary>Why these videos?</summary><p>{proposal?.reason}</p>{captionProposal && <p>Caption reference: {videos.find(v=>v.video_id===captionProposal.diagnostics.referenceVideoId)?.title || 'Unavailable'}. Shared words below are measured against this reference, which may be an earlier upload.</p>}{captionProposal && <ul>{captionProposal.matches.map(match=><li key={match.videoId}>{videos.find(v=>v.video_id===match.videoId)?.title}: shared words — {match.terms.join(', ')}.</li>)}</ul>}<p>Publication cutoff: {proposal?.cutoff.replace('T',' ').replace(/Z$/, ' UTC')}. Uploads must be at least 168 hours old at collection; the displayed calendar date alone is not enough.</p><p>Your question and requested period have not been interpreted or applied. {proposal?.excluded} other uploads are left out of this selection.</p></details><div className="measurement-list">{['recent','earlier'].map(group=><div key={group}><h4>{group==='recent'?'Recent group':'Earlier group'}</h4><ul>{videos.filter(v=>selection[v.video_id]===group).map(v=><li key={v.video_id}><a className="source" href={v.source_url} target="_blank" rel="noopener noreferrer">{v.title || 'Untitled video'}</a> — {v.published_at?.slice(0,10)}</li>)}</ul></div>)}</div><button type="button" onClick={()=>setManual(true)}>Adjust comparison</button></div>}
    {!prepared && <>{mismatchNote}{relatedNote}</>}
    {!videos.length ? <p>No public videos are available to select. A comparison cannot be made.</p> : <form onSubmit={investigate}>
      <details className="sample-details" open={manual} onToggle={event=>setManual(event.currentTarget.open)}><summary>Adjust comparison / select videos manually</summary>
        <label htmlFor="comparison-search">Find a video by title or date</label><input id="comparison-search" type="search" value={search} onChange={event=>{setSearch(event.target.value);setPage(0);}} placeholder="For example: Guardian or 2026-09"/><p className="helper">Showing {filtered.length ? page*10+1 : 0}–{Math.min(page*10+10,filtered.length)} of {filtered.length} matches. Selections stay selected across searches and pages.</p><div className="video-selection" role="region" aria-label="Videos available for comparison" tabIndex={0}>{visible.map(video=><div key={video.video_id} className="video-selection-row">
          <div><a className="source" href={video.source_url} target="_blank" rel="noopener noreferrer">{video.title || 'Untitled video'} ↗</a><p className="muted">Published: {video.published_at?.slice(0,10) || 'Unavailable'} · Public views: {number(video.views)}</p></div>
          <label><span className="sr-only">Comparison group for {video.title || video.video_id}</span><select value={selection[video.video_id] || ''} onChange={event=>{setSelection({...selection,[video.video_id]:event.target.value});setPrepared(false);invalidate();}}><option value="">Leave out</option><option value="recent">Recent group</option><option value="earlier">Earlier group</option></select></label>
        </div>)}</div>
        <button type="button" disabled={page===0} onClick={()=>setPage(page-1)}>Previous videos</button>{' '}<button type="button" disabled={(page+1)*10>=filtered.length} onClick={()=>setPage(page+1)}>Next videos</button>
      </details>
      <p className="helper">Selected: {Object.values(selection).filter(v=>v==='recent').length} recent, {Object.values(selection).filter(v=>v==='earlier').length} earlier. Each video belongs to one group.</p>
      <details className="sample-details"><summary>Check topics and formats (optional)</summary><p className="helper">If you haven’t checked, leave both as “I’m not sure.”</p><label htmlFor="view-topics">Are the selected groups about similar topics?</label><select id="view-topics" value={topics} onChange={event=>{setTopics(event.target.value as Comparability);invalidate();}}><option value="unknown">I’m not sure</option><option value="same">Yes, similar topics</option><option value="different">No, different topics</option></select>
      <label className="concern-label" htmlFor="view-formats">Do the groups use similar formats?</label><select id="view-formats" value={formats} onChange={event=>{setFormats(event.target.value as Comparability);invalidate();}}><option value="unknown">I’m not sure</option><option value="same">Yes, similar formats</option><option value="different">No, different formats</option></select>
      </details><button className="channel-submit">Compare selected public facts</button>
    </form>}
    {error && <p className="error" role="alert">{error}</p>}
    {result && <div className="evidence-note" aria-labelledby="views-result-title">
      <h3 id="views-result-title" tabIndex={-1} ref={heading}>What the selected videos show</h3>
      <h4>What we found</h4>
      <p><strong>{result.difference === null ? 'We can’t establish a difference from this selection.' : result.difference < 0 ? 'The selected recent videos have a lower middle lifetime view count. This alone does not prove a performance decline.' : result.difference > 0 ? 'The selected recent videos have a higher middle lifetime view count. This selection does not show fewer public views.' : 'The selected groups have the same middle lifetime view count.'}</strong></p>
      <h4>Evidence behind it</h4>
      <p><strong>{result.difference === null ? "We don’t have enough consistent facts to compare these groups." : `The middle lifetime view count is ${number(result.recent.medianViews)} for your recent videos and ${number(result.earlier.medianViews)} for your earlier videos.`}</strong></p>
      <p className="muted">Based on {result.recent.count} selected recent videos and {result.earlier.count} selected earlier videos. Public facts collected on {fetchedAt.slice(0,10)} (UTC). This is a selected sample, not a finding about the whole channel.</p>
      <details className="sample-details"><summary>See the numbers and comparison limits</summary><dl className="measurement-list">{[{label:'Recent',value:result.recent},{label:'Earlier',value:result.earlier}].map(({label,value})=>{
        return <div key={label}><dt>{label} group</dt><dd>{value.count} videos; {value.available} available view counts</dd><dd>Median lifetime views: {number(value.medianViews)}</dd><dd>Age at collection: {value.newestDays === null ? 'Unavailable' : `${number(value.newestDays)}–${number(value.oldestDays)} days`}</dd></div>;
      })}</dl>
      <p>{result.difference === null ? 'The difference between groups is withheld because counts or publication order do not support it.' : `Recent median lifetime views are ${result.difference === 0 ? 'equal to' : result.difference < 0 ? 'lower than' : 'higher than'} the earlier median. Difference: ${number(result.difference)} views${result.percent === null ? ' (percentage unavailable because the earlier median is zero)' : ` (${number(result.percent)}%)`}.`}</p>
      <ul className="limits">{result.checks.map(check=><li key={check}>{check}</li>)}</ul>
      </details>
      <h4>What remains unknown</h4>
      <p>These are lifetime view totals. They don’t establish how the groups performed over the same time after publication or explain why views differ. Similar content, formats and independent footage have not been verified.</p>
      <h4>Your next step</h4><p>{result.nextStep}</p><p className="muted">Stratify has not retrieved those private analytics. No content change or experiment is justified by this comparison alone.</p>
      <MatchedViews comparison={result}/>
    </div>}
  </section>;
}
