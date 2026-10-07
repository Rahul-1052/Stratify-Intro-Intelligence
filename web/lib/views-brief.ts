import type {PublicVideo, investigateViews} from './views-investigation';

export type ViewsScope = {kind: 'default'} | {kind: 'manual'; message: string} | {kind: 'uploads'; recent: number; earlier: number};
export function parseViewsScope(period: string): ViewsScope {
  const normalized = period.trim().toLowerCase().replace(/[.!?]+$/, '').replace(/\bmy\s+/g, '');
  if (!normalized) return {kind: 'default'};
  const words: Record<string,number> = {one:1,two:2,three:3,four:4,five:5,six:6,seven:7,eight:8,nine:9,ten:10};
  const match = normalized.match(/^(?:last|latest) (\d+|one|two|three|four|five|six|seven|eight|nine|ten) (?:uploads|videos) (?:vs\.?|versus|compared (?:with|to)) (?:the )?previous (\d+|one|two|three|four|five|six|seven|eight|nine|ten) (?:uploads|videos)$/);
  if (match) {
    const recent = words[match[1]] || Number(match[1]), earlier = words[match[2]] || Number(match[2]);
    if (recent > 0 && earlier > 0 && recent + earlier <= 100) return {kind: 'uploads', recent, earlier};
  }
  return {kind:'manual',message:'Choose videos that match your requested period. Stratify has not applied that scope automatically.'};
}

export function proposeScopedViews(videos: PublicVideo[], fetchedAt: string, scope: Extract<ViewsScope,{kind:'uploads'}>) {
  const collected = Date.parse(fetchedAt);
  if (!Number.isFinite(collected) || new Set(videos.map(v=>v.video_id)).size !== videos.length) return null;
  // Do not omit unavailable or future dates and silently substitute older uploads.
  if (videos.some(v=>!v.published_at || !Number.isFinite(Date.parse(v.published_at)) || Date.parse(v.published_at) > collected)) return null;
  const ordered = [...videos].sort((a,b)=>Date.parse(b.published_at!)-Date.parse(a.published_at!) || a.video_id.localeCompare(b.video_id));
  const recent = ordered.slice(0,scope.recent), earlier = ordered.slice(scope.recent,scope.recent+scope.earlier);
  if (recent.length !== scope.recent || earlier.length !== scope.earlier || Date.parse(recent.at(-1)!.published_at!) <= Date.parse(earlier[0].published_at!)) return null;
  return {recent,earlier,excluded:videos.length-recent.length-earlier.length,cutoff:null,
    reason:`Your requested last ${scope.recent} available public uploads versus the previous ${scope.earlier}. Selected by publication date, including fresh uploads; no seven-day cutoff was applied. Private or unavailable uploads are outside this inventory. Content comparability is unverified.`};
}

export function scopeMatchesSelection(scope: ViewsScope, videos: PublicVideo[], fetchedAt: string, result: ReturnType<typeof investigateViews>): boolean | null {
  if (scope.kind === 'default') return true;
  if (scope.kind === 'manual') return null;
  const expected = proposeScopedViews(videos,fetchedAt,scope);
  if (!expected) return false;
  const matches = (rows: PublicVideo[], ids: PublicVideo[]) => rows.length === ids.length && rows.every(row=>ids.some(video=>video.video_id === row.video_id));
  return matches(result.recent.rows,expected.recent) && matches(result.earlier.rows,expected.earlier);
}

export function answerViewsConcern(question: string, scopeMatch: boolean | null, result: ReturnType<typeof investigateViews>) {
  // Wording clues only. A confirmed views focus does not authorize causal claims.
  const wording = question.toLowerCase();
  if (scopeMatch === false) return 'These selected videos do not match your requested upload groups.';
  if (scopeMatch === null) return 'Check that these videos match your requested period before interpreting this comparison.';
  if (/\bwhy\b|\b(?:cause|causing|reason)\b/.test(wording)) return 'These public counts cannot explain why views changed.';
  if (/\b(?:increase|improve|grow|boost)\b|\bhow\b.{0,35}\b(?:get|gain|reach)\b/.test(wording)) return 'These public counts alone cannot tell us how to increase views.';
  if (!result.chronological || result.difference === null) return 'The available counts or dates do not support this comparison yet.';
  if (/\blifetime\b/.test(wording) && /\b(?:compare|fewer|lower|higher|more)\b/.test(wording)) return `For these selected videos, recent median lifetime views are ${result.difference < 0 ? 'lower' : result.difference > 0 ? 'higher' : 'the same'}.`;
  if (/\b(?:compare|fewer|lower|higher|more|down|drop|dropped|dropping|worse|better|changed|change|lost)\b/.test(wording)) return 'We cannot establish an equal-time performance change from lifetime views alone.';
  return 'This comparison describes selected view totals; it does not fully answer your question.';
}
