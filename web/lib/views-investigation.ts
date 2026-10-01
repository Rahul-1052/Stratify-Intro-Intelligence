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

export type WindowEvidence = {days: number; metric: 'views' | 'engaged_views'; counts: Record<string,string>; confirmed: boolean};
export function investigateWindow(publicResult: ReturnType<typeof investigateViews>, evidence: WindowEvidence) {
  if (![1,7,28].includes(evidence.days)) throw new Error('Choose the first 24 hours, 7 days or 28 days.');
  if (!['views','engaged_views'].includes(evidence.metric) || evidence.confirmed !== true)
    throw new Error('Confirm a completed window and the same metric definition for every selected video.');
  if (!publicResult.chronological) throw new Error('Review publication dates and separate recent and earlier groups first.');
  if ([publicResult.recent,publicResult.earlier].some(group=>group.newestDays === null || group.newestDays < evidence.days))
    throw new Error('At least one selected video had not completed this window when public facts were collected. Choose a shorter window or recollect the facts.');
  const read = (id: string) => {
    const text = evidence.counts[id]?.trim();
    if (!text || !/^\d+$/.test(text) || !Number.isSafeInteger(Number(text)))
      throw new Error('Enter a whole, nonnegative count for every selected video. Leave unavailable data out of this comparison; never enter zero for missing data.');
    return Number(text);
  };
  const recentCounts = publicResult.recent.rows.map(video=>read(video.video_id));
  const earlierCounts = publicResult.earlier.rows.map(video=>read(video.video_id));
  const recentMedian = median(recentCounts), earlierMedian = median(earlierCounts);
  const difference = recentMedian-earlierMedian;
  return {days:evidence.days,metric:evidence.metric,recentMedian,earlierMedian,difference,
    percent: earlierMedian === 0 ? null : difference/earlierMedian*100,
    recentCount:recentCounts.length,earlierCount:earlierCounts.length,
    recentAtOrAboveEarlierMedian:recentCounts.filter(value=>value>=earlierMedian).length,
    comparableByCreator: publicResult.topics === 'same' && publicResult.formats === 'same',
    smallSample: recentCounts.length < 3 || earlierCounts.length < 3,
    source:'creator_entered_unverified' as const};
}
