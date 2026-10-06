const {test}=require('node:test');
const assert=require('node:assert/strict');
const {durationSeconds,selectedLengthEvidence,displayLength,proposeLengthComparison}=require('../lib/video-length-evidence.ts');
const row=(id,duration)=>({video_id:id,title:id,source_url:'https://www.youtube.com/watch?v='+id,published_at:null,duration,views:null});
test('reported ISO durations are measured without classifying formats',()=>{
 assert.equal(durationSeconds('PT24M'),1440);
 assert.equal(durationSeconds('P1DT1H2M3.5S'),90123.5);
 for(const value of [null,'bad','PT0S','P','PT','-PT10S']) assert.equal(durationSeconds(value),null);
 assert.equal(displayLength(95),'1 min 35 sec');
});
test('large length spread prompts review without calling a video a Short',()=>{
 const evidence=selectedLengthEvidence([row('shorter','PT35S'),row('longer','PT24M'),row('unknown',null)]);
 assert.equal(evidence.needsReview,true);assert.equal(evidence.missing,1);
 assert.equal(evidence.shortest.video.video_id,'shorter');assert.equal(evidence.longest.seconds,1440);
 assert.equal('format' in evidence,false);
});
test('similar lengths, all missing or small clips do not manufacture a mismatch',()=>{
 for(const rows of [[row('one',null)],[row('one','PT5M'),row('two','PT6M')],[row('one','PT5S'),row('two','PT50S')],[]]) assert.equal(selectedLengthEvidence(rows).needsReview,false);
});
test('review trigger boundary is explicit rather than a confidence score',()=>{
 assert.equal(selectedLengthEvidence([row('one','PT75S'),row('two','PT5M')]).needsReview,true);
 assert.equal(selectedLengthEvidence([row('one','PT76S'),row('two','PT5M')]).needsReview,false);
});

const collected='2026-10-06T00:00:00Z';
const sample=Array.from({length:9},(_,i)=>({...row('v'+i,i%3===0?'PT17S':'PT10M'),published_at:new Date(Date.parse(collected)-(i+8)*86400000).toISOString()}));
test('fallback separates measured lengths without using titles or views',()=>{
 const p=proposeLengthComparison(sample,collected);
 assert(p);assert.equal(p.recent.length,3);assert.equal(p.earlier.length,3);
 assert([...p.recent,...p.earlier].every(v=>v.duration==='PT10M'));
 assert.match(p.reason,/does not establish/);
 const changed=proposeLengthComparison(sample.map(v=>({...v,title:'renamed',views:999999})).reverse(),collected);
 assert.deepEqual(changed.recent.map(v=>v.video_id),p.recent.map(v=>v.video_id));
});
test('fallback permits three versus two and withholds insufficient measured groups',()=>{
 const five=sample.filter(v=>v.duration==='PT10M').slice(0,5);
 assert.equal(proposeLengthComparison(five,collected).earlier.length,2);
 assert.equal(proposeLengthComparison(five.slice(0,4),collected),null);
 assert.equal(proposeLengthComparison(five.map(v=>({...v,duration:null})),collected),null);
});
test('fallback preserves age and strict chronological boundaries',()=>{
 assert.equal(proposeLengthComparison(sample.map(v=>({...v,published_at:collected})),collected),null);
 assert.equal(proposeLengthComparison(sample.map(v=>({...v,published_at:'2026-09-01T00:00:00Z'})),collected),null);
 assert.equal(proposeLengthComparison(sample,'invalid'),null);
});
