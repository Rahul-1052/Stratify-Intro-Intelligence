import type {PublicVideo} from './views-investigation';

export function durationSeconds(value: string | null): number | null {
  const match = value?.match(/^P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?)?$/);
  if (!match) return null;
  const seconds = Number(match[1] || 0)*86400 + Number(match[2] || 0)*3600 + Number(match[3] || 0)*60 + Number(match[4] || 0);
  return Number.isFinite(seconds) && seconds > 0 && seconds <= Number.MAX_SAFE_INTEGER ? seconds : null;
}

export function selectedLengthEvidence(videos: PublicVideo[]) {
  const measured = videos.flatMap(video=>{
    const seconds = durationSeconds(video.duration);
    return seconds === null ? [] : [{video,seconds}];
  }).sort((a,b)=>a.seconds-b.seconds);
  const shortest = measured[0] || null, longest = measured.at(-1) || null;
  const ratio = shortest && longest ? longest.seconds/shortest.seconds : null;
  // A provisional review trigger, not a validated format or fairness classifier.
  const needsReview = measured.length >= 2 && longest!.seconds >= 300 && ratio! >= 4;
  return {measured,missing:videos.length-measured.length,shortest,longest,ratio,needsReview};
}

export function displayLength(seconds: number) {
  const rounded = Math.round(seconds);
  return rounded < 60 ? `${rounded} sec` : rounded < 3600 ? `${Math.floor(rounded/60)} min${rounded%60 ? ` ${rounded%60} sec` : ''}` : `${Math.floor(rounded/3600)} hr ${Math.floor(rounded%3600/60)} min`;
}

export function proposeLengthComparison(videos: PublicVideo[], fetchedAt: string) {
  const collected=Date.parse(fetchedAt);
  if(!Number.isFinite(collected) || new Set(videos.map(v=>v.video_id)).size!==videos.length) return null;
  const eligible=videos.flatMap(video=>{
    const seconds=durationSeconds(video.duration), published=Date.parse(video.published_at || '');
    return seconds!==null && Number.isFinite(published) && collected-published>=7*86400000 ? [{video,seconds}] : [];
  }).sort((a,b)=>a.seconds-b.seconds || a.video.video_id.localeCompare(b.video.video_id));
  const proposals=[];
  for(const minimum of eligible) {
    // A measured-length window, not a content or format classification.
    const ordered=eligible.filter(row=>row.seconds>=minimum.seconds && row.seconds<minimum.seconds*4).map(row=>row.video).sort((a,b)=>Date.parse(b.published_at!)-Date.parse(a.published_at!) || a.video_id.localeCompare(b.video_id));
    const recent=ordered.slice(0,3);
    if(recent.length!==3) continue;
    const earlier=ordered.filter(v=>Date.parse(v.published_at!)<Date.parse(recent[2].published_at!)).slice(0,3);
    if(earlier.length<2) continue;
    proposals.push({recent,earlier,excluded:videos.length-recent.length-earlier.length,cutoff:new Date(collected-7*86400000).toISOString(),reason:'Captions were unavailable. These groups use publication dates and measured durations within a less-than-fourfold length range. Unknown durations are excluded. Titles and view counts do not influence selection. This provisional rule does not establish similar topics, formats or independent footage; older matching uploads may replace newer uploads outside the length range.'});
  }
  proposals.sort((a,b)=>b.earlier.length-a.earlier.length || Date.parse(b.recent[0].published_at!)-Date.parse(a.recent[0].published_at!) || Date.parse(b.recent[2].published_at!)-Date.parse(a.recent[2].published_at!) || a.recent.map(v=>v.video_id).join().localeCompare(b.recent.map(v=>v.video_id).join()));
  return proposals[0] || null;
}
