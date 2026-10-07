import type {PublicVideo} from './views-investigation';

// Explicit episode labels are title clues, never verified topic or footage evidence.
export function namedSeriesOptions(videos:PublicVideo[], selectedIds:string[], fetchedAt:string) {
  const collected=Date.parse(fetchedAt);
  if(!Number.isFinite(collected) || new Set(videos.map(v=>v.video_id)).size!==videos.length) return [];
  const groups=new Map<string,{label:string;rows:{video:PublicVideo;episode:number}[]}>();
  for(const video of videos) {
    const match=video.title?.match(/^(.+?)\s*[-|:]\s*ep(?:isode)?\.?\s*(\d+)\b/i);
    if(!match || !video.published_at || !Number.isFinite(Date.parse(video.published_at)) || collected-Date.parse(video.published_at)<7*86400000) continue;
    const label=match[1].trim(),key=label.toLowerCase().replace(/\s+/g,' ');
    if(!groups.has(key)) groups.set(key,{label,rows:[]});
    groups.get(key)!.rows.push({video,episode:Number(match[2])});
  }
  return [...groups.values()].flatMap(group=>{
    const ids=new Set(group.rows.map(row=>row.video.video_id));
    if(selectedIds.filter(id=>ids.has(id)).length<2 || selectedIds.every(id=>ids.has(id))) return [];
    // Repeated episode numbers may be parts or reuploads; do not resolve them by guessing.
    if(new Set(group.rows.map(row=>row.episode)).size!==group.rows.length) return [];
    const ordered=group.rows.map(row=>row.video).sort((a,b)=>Date.parse(b.published_at!)-Date.parse(a.published_at!) || a.video_id.localeCompare(b.video_id));
    const recent=ordered.slice(0,3);
    if(recent.length!==3) return [];
    const earlier=ordered.filter(v=>Date.parse(v.published_at!)<Date.parse(recent[2].published_at!)).slice(0,3);
    if(earlier.length<2) return [];
    return [{label:group.label,recent,earlier,excluded:videos.length-recent.length-earlier.length,cutoff:new Date(collected-7*86400000).toISOString(),reason:`You chose titles labeled “${group.label}” with explicit episode numbers. Groups use publication dates, not view counts. The labels are unverified clues; they do not establish similar topics, formats, independent footage or equal viewing time.`}];
  }).sort((a,b)=>a.label.localeCompare(b.label));
}
