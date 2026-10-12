export type PublicVideo = {video_id: string; title: string; source_url: string; published_at: string | null; duration: string | null; views: number | null};
export type Comparability = 'same' | 'different' | 'unknown';
const median = (values: number[]) => {
  const sorted = [...values].sort((a,b)=>a-b), mid = Math.floor(sorted.length/2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid-1]+sorted[mid])/2;
};
export function investigateViews(videos: PublicVideo[], recentIds: string[], earlierIds: string[], fetchedAt: string, topics: Comparability, formats: Comparability) {
  const ids = new Set(videos.map(video=>video.video_id));
  if (ids.size !== videos.length || new Set(recentIds).size !== recentIds.length || new Set(earlierIds).size !== earlierIds.length)
    throw new Error('Each video must appear only once.');
  if (!recentIds.length || !earlierIds.length) throw new Error('Select at least one recent video and one earlier video.');
  if ([...recentIds,...earlierIds].some(id=>!ids.has(id)) || recentIds.some(id=>earlierIds.includes(id)))
    throw new Error('Use separate groups of videos from this evidence record.');
  const collected = Date.parse(fetchedAt);
  if (!Number.isFinite(collected)) throw new Error('A valid collection time is needed. Collect the channel facts again.');
  if (![topics,formats].every(value=>['same','different','unknown'].includes(value))) throw new Error('Review topic and format comparability.');
  const group = (selected: string[]) => {
    const rows = selected.map(id=>videos.find(video=>video.video_id===id)!);
    const dated = rows.map(video=>video.published_at ? Date.parse(video.published_at) : NaN);
    const validDates = dated.every(value=>Number.isFinite(value) && value <= collected);
    const available = rows.filter(video=>typeof video.views === 'number' && Number.isSafeInteger(video.views) && video.views >= 0);
    return {rows, count: rows.length, available: available.length, missing: rows.length-available.length,
      medianViews: available.length === rows.length ? median(available.map(video=>video.views!)) : null,
      oldestDays: validDates ? Math.max(...dated.map(value=>(collected-value)/86400000)) : null,
      newestDays: validDates ? Math.min(...dated.map(value=>(collected-value)/86400000)) : null,
      earliest: validDates ? Math.min(...dated) : null, latest: validDates ? Math.max(...dated) : null};
  };
  const recent = group(recentIds), earlier = group(earlierIds);
  const chronological = recent.earliest !== null && earlier.latest !== null && recent.earliest > earlier.latest;
  const checks = ['Public views are lifetime totals measured at collection, not views over equal time after publication.'];
  if (!chronological) checks.push('Publication dates do not establish two separate recent and earlier groups. Review your selection or missing dates.');
  if (recent.count < 3 || earlier.count < 3) checks.push('At least one group has fewer than three videos. A single unusual video can dominate this small sample.');
  if (recent.missing || earlier.missing) checks.push('Some view counts are unavailable. Group medians and the difference are withheld rather than treating them as zero.');
  checks.push(topics === 'same' ? 'You described the topics as similar; Stratify has not independently verified that.' : topics === 'different' ? 'You described the topics as different. Topic changes can limit this comparison.' : 'Topic comparability is unknown. Titles alone do not verify it.');
  checks.push(formats === 'same' ? 'You described the formats as similar; Stratify has not independently verified that.' : formats === 'different' ? 'You described the formats as different. Keep formats separate before interpreting differences.' : 'Format comparability is unknown. Duration alone does not identify Shorts, regular videos or livestreams.');
  const difference = chronological && recent.medianViews !== null && earlier.medianViews !== null ? recent.medianViews-earlier.medianViews : null;
  const percent = difference !== null && earlier.medianViews !== 0 ? difference / earlier.medianViews! * 100 : null;
  return {recent, earlier, chronological, difference, percent, checks, topics, formats,
    conclusion: 'These public facts cannot establish a decline over equal viewing time or explain its cause.',
    nextStep: 'Compare views for these same videos over the same number of days after publication in your channel analytics. Review impressions and traffic sources before investigating titles, thumbnails or the viewing experience.'};
}

export type WindowEvidence = {days: number; metric: 'views' | 'engaged_views'; counts: Record<string,string>; confirmed: boolean; impressions?: Record<string,string>};
export function investigateWindow(publicResult: ReturnType<typeof investigateViews>, evidence: WindowEvidence) {
  if (![1,7,28].includes(evidence.days)) throw new Error('Choose the first 24 hours, 7 days or 28 days.');
  if (!['views','engaged_views'].includes(evidence.metric) || evidence.confirmed !== true)
    throw new Error('Confirm a completed window and the same metric definition for every selected video.');
  if (!publicResult.chronological) throw new Error('Review publication dates and separate recent and earlier groups first.');
  if ([publicResult.recent,publicResult.earlier].some(group=>group.newestDays === null || group.newestDays < evidence.days))
    throw new Error('At least one selected video had not completed this window when public facts were collected. Choose a shorter window or recollect the facts.');
  const read = (id: string, values = evidence.counts) => {
    const text = values[id]?.trim();
    if (!text || !/^\d+$/.test(text) || !Number.isSafeInteger(Number(text)))
      throw new Error('Enter a whole, nonnegative count for every selected video. Leave unavailable data out of this comparison; never enter zero for missing data.');
    return Number(text);
  };
  const recentCounts = publicResult.recent.rows.map(video=>read(video.video_id));
  const earlierCounts = publicResult.earlier.rows.map(video=>read(video.video_id));
  const recentMedian = median(recentCounts), earlierMedian = median(earlierCounts);
  const difference = recentMedian-earlierMedian;
  const impressions = evidence.impressions ? {
    recentMedian: median(publicResult.recent.rows.map(video=>read(video.video_id,evidence.impressions))),
    earlierMedian: median(publicResult.earlier.rows.map(video=>read(video.video_id,evidence.impressions))),
  } : null;
  return {impressions,videoIds:[...publicResult.recent.rows,...publicResult.earlier.rows].map(video=>video.video_id),days:evidence.days,metric:evidence.metric,recentMedian,earlierMedian,difference,
    percent: earlierMedian === 0 ? null : difference/earlierMedian*100,
    recentCount:recentCounts.length,earlierCount:earlierCounts.length,
    recentAtOrAboveEarlierMedian:recentCounts.filter(value=>value>=earlierMedian).length,
    comparableByCreator: publicResult.topics === 'same' && publicResult.formats === 'same',
    smallSample: recentCounts.length < 3 || earlierCounts.length < 3,
    source:'creator_entered_unverified' as const};
}


export function suggestNextSteps(result: ReturnType<typeof investigateWindow>) {
  const evidence = [
    {id:'matched_views', observation:`Selected recent median: ${result.recentMedian}; earlier median: ${result.earlierMedian}. Metric: ${result.metric}. ${result.days === 1 ? 'First 24 hours' : `First ${result.days} days`}.`, source:result.source,videoIds:result.videoIds},
    {id:'selection_context', observation:`Selected videos: ${result.recentCount} recent and ${result.earlierCount} earlier. Topics/formats described as similar: ${result.comparableByCreator ? 'yes' : 'no or unknown'}.`,source:result.source,videoIds:result.videoIds},
  ];
  if (result.impressions) evidence.push({id:'matched_impressions',observation:`Selected recent median registered thumbnail impressions: ${result.impressions.recentMedian}; earlier median: ${result.impressions.earlierMedian}. ${result.days === 1 ? 'First 24 hours' : `First ${result.days} days`}.`,source:result.source,videoIds:result.videoIds});
  const suggestions: {id:string; action:string; reason:string; evidenceIds:string[]; limitation:string}[]=[];
  if (!result.comparableByCreator) suggestions.push({id:'review_comparability',action:'Review topic and format differences before interpreting this as a content-performance change.',reason:'The selected groups have different or unknown topics/formats according to your assessment.',evidenceIds:['selection_context'],limitation:'Stratify has not inspected the content or independently verified comparability.'});
  if (result.smallSample) suggestions.push({id:'review_small_sample',action:'Inspect these videos individually, or add relevant comparable examples if they exist.',reason:'At least one selected group contains fewer than three videos.',evidenceIds:['selection_context','matched_views'],limitation:'Do not add unrelated videos just to increase the sample. A larger selection still does not prove a cause.'});
  if (suggestions.length) return {evidence,suggestions,status:'comparison_needs_review' as const};
  if (result.difference >= 0) suggestions.push({id:'revisit_concern',action:'Revisit which videos, metric or viewing window prompted the concern.',reason:'The entered matched-window medians do not show a decrease in this selection.',evidenceIds:['matched_views'],limitation:'Other selections or individual videos may behave differently; this is not a whole-channel conclusion.'});
  else if (!result.impressions) suggestions.push({id:'collect_impressions',action:'Check registered thumbnail impressions and traffic sources for these same videos over the same windows.',reason:'The entered views median is lower, but exposure evidence has not been supplied.',evidenceIds:['matched_views'],limitation:'A views difference alone cannot distinguish exposure changes from audience-response changes.'});
  else if (result.impressions.recentMedian < result.impressions.earlierMedian) suggestions.push({id:'inspect_exposure',action:'Inspect the traffic-source breakdown to see where registered thumbnail exposure changed.',reason:'Both the entered views median and registered thumbnail impressions median are lower in the recent selection.',evidenceIds:['matched_views','matched_impressions'],limitation:'These two group-level changes co-occur; one is not established as causing the other. Registered impressions do not cover every source of views.'});
  else suggestions.push({id:'inspect_source_mix',action:'Review traffic-source mix, then the platform’s source-specific click-through and retention evidence where available.',reason:'The entered views median is lower while the registered thumbnail impressions median is equal or higher.',evidenceIds:['matched_views','matched_impressions'],limitation:'This does not establish worse thumbnails or retention. Total views divided by impressions is not the platform’s impression click-through rate.'});
  return {evidence,suggestions,status:'investigation_steps_only' as const};
}

// A date-only starting point, not topic/format classification or a performance ranking.
export function proposeComparison(videos: PublicVideo[], fetchedAt: string) {
  const collected = Date.parse(fetchedAt);
  if (!Number.isFinite(collected) || new Set(videos.map(v=>v.video_id)).size !== videos.length) throw new Error('Collect a valid, unique video inventory before preparing groups.');
  const eligible = videos.filter(v=>v.published_at && Number.isFinite(Date.parse(v.published_at)) && (collected-Date.parse(v.published_at))/86400000 >= 7)
    .sort((a,b)=>Date.parse(b.published_at!)-Date.parse(a.published_at!) || a.video_id.localeCompare(b.video_id));
  const recent = eligible.slice(0,3);
  const boundary = recent.length ? Date.parse(recent[recent.length-1].published_at!) : NaN;
  const earlier = eligible.filter(v=>Date.parse(v.published_at!) < boundary).slice(0,3);
  if (recent.length !== 3 || earlier.length !== 3) return null;
  return {recent, earlier, cutoff: new Date(collected - 7 * 86400000).toISOString(), excluded: videos.length-6, reason: 'Three newest uploads at least 7 days old, followed by three uploads strictly older than that group. Date ties use video ID order. Views, titles and durations do not influence selection. Seven days is a setup default, not a statistical reliability threshold.'};
}

// Explicit title clues only. These warnings never classify content or alter groups.
export function comparisonTitleWarnings(videos: PublicVideo[]) {
  const patterns: [string, RegExp][] = [
    ['interview', /\binterview\b/i], ['stand-up comedy', /\bstand[ -]?up comedy\b/i],
    ['podcast', /\bpodcast\b/i], ['livestream', /\blivestream\b|\blive stream\b/i],
    ['trailer', /\btrailer\b/i], ['full show', /\bfull(?:\s+crowd[ -]work)?\s+show\b/i], ['clip', /\bclips?\b/i],
  ];
  const clues = videos.flatMap(v=>patterns.filter(([,pattern])=>pattern.test(v.title)).map(([label])=>({videoId:v.video_id,title:v.title,label})));
  const fullShows = clues.filter(c=>c.label === 'full show');
  if (fullShows.length > 0 && fullShows.length < videos.length) return fullShows.map(c=>({...c,message:'This title says full show; other selected titles do not. Their formats are unknown, so review whether they belong together.'}));
  if (new Set(clues.map(c=>c.label)).size < 2) return [];
  return clues.map(c=>({...c,message:`Title mentions “${c.label}”. Other selected titles use different content labels; check whether they belong in the same comparison.`}));
}

// A naming clue, never proof of shared footage or independent observations.
export function relatedTitleGroups(videos: PublicVideo[]) {
  const normalize = (title: string) => title.toLowerCase().replace(/\bpart\s*\d+\b/gi, '').replace(/[^\p{L}\p{N}]+/gu, ' ').trim();
  const groups = new Map<string, PublicVideo[]>();
  for (const video of videos) {
    const key = normalize(video.title);
    if (!key) continue;
    groups.set(key, [...(groups.get(key) || []), video]);
  }
  return [...groups.values()].filter(group => group.length > 1 && group.some(video => /\bpart\s*\d+\b/i.test(video.title)));
}
