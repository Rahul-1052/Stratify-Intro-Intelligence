import type {PublicVideo} from './views-investigation';
export type CaptionEvidence = {videoId: string; text: string; source: 'creator_caption_unverified'};
const stop = new Set('a an the this that these those and or but for of to in on at by with is are was were be been it its we you i they he she our your my their from as not can do does did have has had will would all so just'.split(' '));
export function captionText(raw: string) {
  return raw.replace(/^\uFEFF/, '').split(/\r?\n/).filter(line => {
    const s=line.trim();
    return s && !/^\d+$/.test(s) && !s.includes('-->') && !/^(WEBVTT|NOTE|STYLE|REGION)(\s|$)/.test(s);
  }).map(line=>line.replace(/<[^>]*>/g,'').trim()).filter((line,i,all)=>i===0 || line!==all[i-1]).join('\n');
}
function words(text: string) {return (text.toLowerCase().match(/[\p{L}\p{N}]+/gu) || []).filter(word=>word.length>2 && !stop.has(word));}
function shingles(text: string) {
  const tokens=words(text), result=new Set<string>();
  for(let i=0;i+5<=tokens.length;i++) result.add(tokens.slice(i,i+5).join(' '));
  return result;
}
export function prepareCaptionComparison(videos: PublicVideo[], fetchedAt: string, evidence: CaptionEvidence[]) {
  if(!Number.isFinite(Date.parse(fetchedAt)) || new Set(videos.map(v=>v.video_id)).size!==videos.length) throw new Error('Collect a valid, unique video inventory before preparing groups.');
  const ids=new Set(videos.map(v=>v.video_id));
  if(evidence.length>100 || new Set(evidence.map(e=>e.videoId)).size!==evidence.length || evidence.some(e=>!ids.has(e.videoId) || e.source!=='creator_caption_unverified' || typeof e.text!=='string' || e.text.length>200000)) throw new Error('Use one caption file per known video, up to 100 files and 200,000 characters per video.');
  const cleaned=evidence.map(e=>({...e,text:captionText(e.text)}));
  // Remove identical repeated lines found in at least half of this caption sample.
  const lineCounts=new Map<string,number>();
  for(const e of cleaned) for(const line of new Set(e.text.split('\n').map(l=>l.toLowerCase().trim()))) lineCounts.set(line,(lineCounts.get(line)||0)+1);
  const texts=new Map(cleaned.map(e=>[e.videoId,e.text.split('\n').filter(l=>(lineCounts.get(l.toLowerCase().trim())||0)<Math.max(3,Math.ceil(cleaned.length/2))).join('\n')]));
  const usable=videos.filter(v=>words(texts.get(v.video_id)||'').length>=40 && v.published_at && Number.isFinite(Date.parse(v.published_at)) && Date.parse(fetchedAt)-Date.parse(v.published_at)>=7*86400000).sort((a,b)=>Date.parse(b.published_at!)-Date.parse(a.published_at!) || a.video_id.localeCompare(b.video_id));
  const vectors=new Map(usable.map(v=>[v.video_id,new Set(words(texts.get(v.video_id)!))]));
  const prints=new Map(usable.map(v=>[v.video_id,shingles(texts.get(v.video_id)!)]));
  const df=new Map<string,number>();
  for(const vector of vectors.values()) for(const token of vector) df.set(token,(df.get(token)||0)+1);
  const weight=(token:string)=>Math.log((usable.length+1)/((df.get(token)||0)+1))+1;
  function similarity(a:PublicVideo,b:PublicVideo) {
    const va=vectors.get(a.video_id)!,vb=vectors.get(b.video_id)!;
    const shared=[...va].filter(t=>vb.has(t));
    const dot=shared.reduce((sum,t)=>sum+weight(t)**2,0);
    const norm=(v:Set<string>)=>Math.sqrt([...v].reduce((sum,t)=>sum+weight(t)**2,0));
    return {score:dot/(norm(va)*norm(vb)),terms:shared.sort((a,b)=>weight(b)-weight(a)||a.localeCompare(b)).slice(0,8),shared:shared.length};
  }
  function overlap(a:PublicVideo,b:PublicVideo) {
    const pa=prints.get(a.video_id)!,pb=prints.get(b.video_id)!;
    return Math.min(pa.size,pb.size)>=10 && [...pa].filter(t=>pb.has(t)).length/Math.min(pa.size,pb.size)>=0.65;
  }
  const skipped=new Set<string>();
  const distinct:PublicVideo[]=[];
  for(const video of usable) {
    if(distinct.some(other=>overlap(video,other))) skipped.add(video.video_id);
    else distinct.push(video);
  }
  for(const anchor of distinct) {
    const matches=distinct.filter(v=>{
      const match=similarity(anchor,v);
      return match.shared>=4 && match.score>=0.15;
    });
    const recent=matches.slice(0,3);
    if(recent.length!==3 || recent[0].video_id!==anchor.video_id) continue;
    const boundary=Date.parse(recent[2].published_at!);
    const earlier=matches.filter(v=>Date.parse(v.published_at!)<boundary).slice(0,3);
    if(earlier.length!==3) continue;
    const selected=[...recent,...earlier];
    return {proposal:{recent,earlier,excluded:videos.length-6,cutoff:new Date(Date.parse(fetchedAt)-7*86400000).toISOString(),reason:'Groups use shared words in supplied captions, then publication order. Titles, views and durations do not affect selection. Substantial caption overlap is screened out. These are unvalidated selection heuristics, not proof of topic, format or independent footage.'}, coverage:{supplied:evidence.length,usable:usable.length,overlapSkipped:skipped.size}, matches:selected.map(v=>({videoId:v.video_id,terms:similarity(anchor,v).terms})), status:'caption_clues' as const};
  }
  return {proposal:null,coverage:{supplied:evidence.length,usable:usable.length,overlapSkipped:skipped.size},matches:[],status:'insufficient_caption_evidence' as const};
}
