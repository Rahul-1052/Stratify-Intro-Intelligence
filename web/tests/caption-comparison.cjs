const {test}=require('node:test');
const assert=require('node:assert/strict');
const {captionText,prepareCaptionComparison}=require('../lib/caption-comparison.ts');
const fetched='2026-10-05T18:00:00Z';
const words='budget expenses savings income spending planning debt loans cash reserve goals strategy monthly balance costs payments invest accounts emergency needs';
const videos=Array.from({length:8},(_,i)=>({video_id:'caption'+i,title:'Different title '+i,source_url:'https://www.youtube.com/watch?v=caption'+i,published_at:`2026-09-${28-i}T17:00:00Z`,duration:null,views:i}));
const content=(i)=>Array.from({length:3},(_,j)=>words.split(' ').map((w,k)=>`${words.split(' ')[(k*(2*i+1)+j)%20]} detail${i}section${j}`).join(' ')).join('\n');
const evidence=videos.map((v,i)=>({videoId:v.video_id,text:content(i),source:'creator_caption_unverified'}));
test('caption parser removes timing, tags and adjacent repeated cues',()=>{
 assert.equal(captionText('WEBVTT\n\n00:00:00.000 --> 00:00:01.000\n<b>Hello there</b>\nHello there\n2\n00:00:01,000 --> 00:00:02,000\nNew line'),'Hello there\nNew line');
});
test('different titles and view totals do not control caption matching',()=>{
 const result=prepareCaptionComparison(videos,fetched,evidence);
 assert(result.proposal);assert.equal(result.status,'caption_clues');
 const changed=prepareCaptionComparison(videos.map(v=>({...v,title:'Renamed',views:999999})).reverse(),fetched,evidence);
 assert.deepEqual(changed.proposal.recent.map(v=>v.video_id),result.proposal.recent.map(v=>v.video_id));
 assert(result.matches.every(m=>m.terms.length));
});
test('short, empty or repeated boilerplate captions abstain',()=>{
 for(const text of ['', 'Hello', Array(5).fill(words).join('\n')]) {
 const result=prepareCaptionComparison(videos,fetched,evidence.map(e=>({...e,text})));
 assert.equal(result.proposal,null);
 }
});
test('substantially overlapping text is screened even when titles differ',()=>{
 const long=Array.from({length:80},(_,i)=>'unique'+i).join(' ');
 const copy=evidence.map((e,i)=>i<2?{...e,text:long}:e);
 const result=prepareCaptionComparison(videos,fetched,copy);
 assert(result.coverage.overlapSkipped>=1);
 if(result.proposal) assert(![...result.proposal.recent,...result.proposal.earlier].some(v=>v.video_id==='caption1'));
});
test('foreign duplicate oversized or wrong-provenance evidence rejected',()=>{
 for(const bad of [[{...evidence[0],videoId:'outside'}],[evidence[0],evidence[0]],[{...evidence[0],text:'a'.repeat(200001)}],[{...evidence[0],source:'verified'}]]) assert.throws(()=>prepareCaptionComparison(videos,fetched,bad));
});
test('fresh videos and equal-time boundaries cannot enter completed groups',()=>{
 const fresh=videos.map(v=>({...v,published_at:'2026-10-05T17:00:00Z'}));
 assert.equal(prepareCaptionComparison(fresh,fetched,evidence).proposal,null);
 const ties=videos.map(v=>({...v,published_at:'2026-09-01T00:00:00Z'}));
 assert.equal(prepareCaptionComparison(ties,fetched,evidence).proposal,null);
});
test('unrelated text cannot manufacture a matching pair of groups',()=>{
 const different=evidence.map((e,i)=>({...e,text:Array.from({length:60},(_,k)=>`subject${i}word${k}`).join(' ')}));
 assert.equal(prepareCaptionComparison(videos,fetched,different).proposal,null);
});
test('caption matching does not claim format or verified provenance',()=>{
 const result=prepareCaptionComparison(videos,fetched,evidence);
 assert.match(result.proposal.reason,/unvalidated/);
 assert.match(result.proposal.reason,/not proof/);
 assert.equal('formats' in result.proposal,false);
});
