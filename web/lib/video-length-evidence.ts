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
