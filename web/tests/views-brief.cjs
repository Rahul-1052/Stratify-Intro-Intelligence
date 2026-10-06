const {test}=require('node:test');
const assert=require('node:assert/strict');
const {parseViewsScope,proposeScopedViews,scopeMatchesSelection,answerViewsConcern}=require('../lib/views-brief.ts');
const {investigateViews}=require('../lib/views-investigation.ts');
const collected='2026-10-06T00:00:00Z';
const videos=Array.from({length:8},(_,i)=>({video_id:`v${i}`,title:`Video ${i}`,source_url:`https://www.youtube.com/watch?v=video${i}`,published_at:`2026-10-${String(5-i).padStart(2,'0')}T00:00:00Z`,duration:null,views:100-i}));
// Use valid dates across the month boundary.
videos.forEach((v,i)=>v.published_at=new Date(Date.parse(collected)-(i+1)*86400000).toISOString());
const scope=parseViewsScope('last 3 uploads vs previous 3 uploads');
const result=()=>investigateViews(videos,['v0','v1','v2'],['v3','v4','v5'],collected,'unknown','unknown');
test('paired counts are explicit and other scope text is not silently interpreted',()=>{
 assert.deepEqual(scope,{kind:'uploads',recent:3,earlier:3});
 assert.deepEqual(parseViewsScope('My last six uploads compared with the previous four videos.'),{kind:'uploads',recent:6,earlier:4});
 assert.deepEqual(parseViewsScope(''),{kind:'default'});
 for(const text of ['last six uploads','September vs August','last 3 tutorials vs previous 3 uploads','last 0 uploads vs previous 3 uploads','last 60 uploads vs previous 60 uploads']) assert.equal(parseViewsScope(text).kind,'manual');
});
test('requested uploads include fresh videos without silently substituting older ones',()=>{
 const proposal=proposeScopedViews([...videos].reverse(),collected,scope);
 assert.deepEqual(proposal.recent.map(v=>v.video_id),['v0','v1','v2']);
 assert.deepEqual(proposal.earlier.map(v=>v.video_id),['v3','v4','v5']);
 assert.equal(proposal.cutoff,null);assert.match(proposal.reason,/no seven-day cutoff/);
 assert.equal(scopeMatchesSelection(scope,videos,collected,result()),true);
});
test('missing or future dates, insufficient coverage and date ties withhold groups',()=>{
 for(const changed of [videos.slice(0,4),videos.map((v,i)=>i===0?{...v,published_at:null}:v),videos.map((v,i)=>i===0?{...v,published_at:'2027-01-01'}:v),videos.map((v,i)=>i===3?{...v,published_at:videos[2].published_at}:v)]) assert.equal(proposeScopedViews(changed,collected,scope),null);
});
test('manual adjustments cannot be reported as satisfying the requested groups',()=>{
 const adjusted=investigateViews(videos,['v1','v2'],['v4','v5'],collected,'same','same');
 assert.equal(scopeMatchesSelection(scope,videos,collected,adjusted),false);
 assert.match(answerViewsConcern('Are views lower?',false,adjusted),/do not match/);
 assert.equal(scopeMatchesSelection(parseViewsScope('September'),videos,collected,adjusted),null);
});
test('question-specific answers never manufacture causes or strategy',()=>{
 assert.match(answerViewsConcern('Why did my views drop?',true,result()),/cannot explain why/);
 assert.match(answerViewsConcern('How can I increase views?',true,result()),/cannot tell us how/);
 assert.match(answerViewsConcern('Are recent videos doing worse?',true,result()),/cannot establish an equal-time/);
 assert.match(answerViewsConcern('Compare lifetime views',true,result()),/recent median lifetime views are higher/);
 assert.match(answerViewsConcern('Why views dropped?',null,result()),/requested period/);
 assert.match(answerViewsConcern('How many views does each video have?',true,result()),/does not fully answer/);
 assert.match(answerViewsConcern('Should I keep my branding?',true,result()),/does not fully answer/);
});
