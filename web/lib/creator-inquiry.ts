// Conservative wording clues, not semantic understanding or a diagnosis.
export type InquiryFocus = 'reach' | 'returning_viewers' | 'subscriptions' | 'content_direction' | 'packaging' | 'watching' | 'open_question';
export function routeConcern(question: string): {focus: InquiryFocus | ''; clarification: string} {
  const text = question.toLowerCase().replace(/[’‘]/g, "'");
  const candidates: InquiryFocus[] = [];
  const asksForInvestigation = /\b(?:why|how|what|which|should|compare|help|improve|increase|decrease|fewer|more|less|down|low|falling|dropped|dropping|declining|not|aren't|isn't|don't|stop|stopped|stopping|confusing|struggling)\b/.test(text);
  if (!asksForInvestigation) return {focus: '', clarification: 'What would you like us to investigate first?'};
  // Explicit exclusions require creator review rather than guessing their scope.
  if (/\b(?:not about|don't mean|do not mean|ignore|instead of|rather than)\b/.test(text)) return {focus: '', clarification: 'What would you like us to investigate first?'};
  if (/\bviews\b|\breach\b/.test(text)) candidates.push('reach');
  if (/\breturning viewers\b|\bviewers?\b.{0,35}\b(?:return|returning|come back|coming back)\b|\baudience\b.{0,35}\b(?:return|come back|coming back)\b/.test(text)) candidates.push('returning_viewers');
  if (/\bsubscribers?\b|\bsubscrib(?:e|es|ing)\b|\bsubscriptions?\b/.test(text)) candidates.push('subscriptions');
  if (/\bthumbnails?\b|\btitles?\b|\bctr\b|\bclick.through\b/.test(text)) candidates.push('packaging');
  if (/\bretention\b|\bintro(?:s)?\b|\bpacing\b|\bwatch time\b|\b(?:stop|stopped|stopping) watching\b/.test(text)) candidates.push('watching');
  if (/\bwhat\b.{0,35}\b(?:create|post|upload|make)\b|\bwhich content\b|\bcontent (?:ideas?|direction)\b|\bnew (?:topic|direction)\b/.test(text)) candidates.push('content_direction');
  if (candidates.length === 1) return {focus: candidates[0], clarification: ''};
  return {focus: '', clarification: candidates.length > 1 ? 'You mentioned more than one concern. Which should we investigate first?' : 'What would you like us to investigate first?'};
}

export const investigationScope: Record<InquiryFocus, string> = {
  reach: 'We can compare selected public view totals. Explaining a change needs comparable videos and views measured over the same time after publication.',
  returning_viewers: 'Answering this needs returning-viewer numbers from YouTube Studio. For now, we can collect public facts and identify the missing evidence.',
  subscriptions: 'Answering this needs subscribers gained by video from YouTube Studio. For now, we can collect public facts and identify the missing evidence.',
  content_direction: 'This needs your goals, reviewed content and relevant audience feedback. For now, we can collect public facts; content recommendations are not available yet.',
  packaging: 'This needs actual thumbnails and titles, with relevant click-through and traffic data. For now, we can collect public facts; packaging analysis is not available yet.',
  watching: 'This needs video content, your intended viewing experience and retention data. Public facts alone cannot answer it.',
  open_question: 'We can collect public facts. Your question may need other evidence before we can answer it.',
};
