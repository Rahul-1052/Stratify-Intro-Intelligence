const {test}=require('node:test');
const assert=require('node:assert/strict');
const {investigateViews}=require('../lib/views-investigation.ts');
const collected='2026-10-01T00:00:00Z';
const video=(id,date,views)=>({video_id:id,title:id,source_url:'https://www.youtube.com/watch?v='+id,published_at:date,duration:'PT5M',views});
const rows=[video('r1','2026-09-20',20),video('r2','2026-09-21',40),video('r3','2026-09-22',600),video('e1','2026-08-20',200),video('e2','2026-08-21',400),video('e3','2026-08-22',500)];
const run=(videos=rows,recent=['r1','r2','r3'],earlier=['e1','e2','e3'])=>investigateViews(videos,recent,earlier,collected,'unknown','unknown');
test('median handles outliers without diagnosing a decline',()=>{
 const r=run();assert.equal(r.recent.medianViews,40);assert.equal(r.earlier.medianViews,400);assert.equal(r.difference,-360);assert.equal(r.percent,-90);assert.equal(r.recent.newestDays,9);assert.equal(r.recent.oldestDays,11);assert.match(r.conclusion,/cannot establish/);assert.match(r.checks[0],/not views over equal time/);
});
test('missing count withholds group median and difference',()=>{
 const r=run(rows.map(v=>v.video_id==='r1'?{...v,views:null}:v));assert.equal(r.recent.missing,1);assert.equal(r.recent.medianViews,null);assert.equal(r.difference,null);assert.equal(r.percent,null);
});
test('zero baseline retains absolute difference and withholds percent',()=>{
 const r=run(rows.map(v=>v.video_id.startsWith('e')?{...v,views:0}:v));assert.equal(r.difference,40);assert.equal(r.percent,null);
});
test('interleaved dates withhold recent versus earlier difference',()=>{
 const r=run(rows,['r1','e3'],['e1','r2']);assert.equal(r.chronological,false);assert.equal(r.difference,null);
});
test('missing, malformed or future dates withhold chronology and age',()=>{
 for(const date of [null,'bad','2027-01-01']){const r=run(rows.map(v=>v.video_id==='r1'?{...v,published_at:date}:v));assert.equal(r.recent.oldestDays,null);assert.equal(r.difference,null);}
});
test('duplicate, overlapping, empty and foreign selections rejected',()=>{
 for(const [recent,earlier] of [[[],['e1']],[['r1'],[]],[['r1','r1'],['e1']],[['r1'],['r1']],[['outside'],['e1']]]) assert.throws(()=>run(rows,recent,earlier));
 assert.throws(()=>run([...rows,rows[0]]));
});
test('small samples and creator comparability assertions stay explicit',()=>{
 const r=investigateViews(rows,['r1'],['e1'],collected,'different','same');assert(r.checks.some(v=>v.includes('fewer than three')));assert(r.checks.some(v=>v.includes('topics as different')));assert(r.checks.some(v=>v.includes('not independently verified')));assert.equal(r.recent.medianViews,20);
});
test('even median and invalid metrics are handled',()=>{
 const r=run(rows,['r1','r2'],['e1','e2']);assert.equal(r.recent.medianViews,30);assert.equal(r.earlier.medianViews,300);
 for(const views of [-1,NaN,Infinity,Number.MAX_SAFE_INTEGER+1]) assert.equal(run(rows.map(v=>v.video_id==='r1'?{...v,views}:v)).recent.medianViews,null);
});
test('invalid collection date or comparability rejected',()=>{
 assert.throws(()=>investigateViews(rows,['r1'],['e1'],'bad','same','same'));
 assert.throws(()=>investigateViews(rows,['r1'],['e1'],collected,'invented','same'));
});
const {investigateWindow}=require('../lib/views-investigation.ts');
const evidence={days:7,metric:'engaged_views',counts:{r1:'20',r2:'40',r3:'600',e1:'200',e2:'400',e3:'500'},confirmed:true};
test('matched window reports user-entered medians and exceptions',()=>{
 const r=investigateWindow(run(),evidence);assert.equal(r.recentMedian,40);assert.equal(r.earlierMedian,400);assert.equal(r.difference,-360);assert.equal(r.percent,-90);assert.equal(r.recentAtOrAboveEarlierMedian,1);assert.equal(r.source,'creator_entered_unverified');assert.equal(r.comparableByCreator,false);
});
test('matched window rejects incomplete or unconfirmed evidence',()=>{
 for(const change of [{confirmed:false},{days:2},{metric:'watch_time'},{counts:{...evidence.counts,r1:''}},{counts:{...evidence.counts,r1:'1.5'}},{counts:{...evidence.counts,r1:'-1'}},{counts:{...evidence.counts,r1:'9007199254740992'}}]) assert.throws(()=>investigateWindow(run(),{...evidence,...change}));
});
test('window must have completed at public snapshot',()=>{
 assert.throws(()=>investigateWindow(run(),{...evidence,days:28}));
 assert.throws(()=>investigateWindow(run(rows.map(v=>v.video_id==='r1'?{...v,published_at:'2026-09-30T12:00:00Z'}:v)),evidence));
 assert.throws(()=>investigateWindow(run(rows,['r1','e3'],['e1','r2']),evidence));
});
test('zero is observed data, not missing, and zero baseline has no percent',()=>{
 const r=investigateWindow(run(),{...evidence,counts:{r1:'0',r2:'0',r3:'0',e1:'0',e2:'0',e3:'0'}});assert.equal(r.difference,0);assert.equal(r.percent,null);assert.equal(r.recentAtOrAboveEarlierMedian,3);
});
test('matched evidence can be used without public lifetime counts',()=>{
 const r=investigateWindow(run(rows.map(v=>({...v,views:null}))),evidence);assert.equal(r.difference,-360);
});
test('small samples stay labeled, positive and equal differences remain possible',()=>{
 const publicResult=investigateViews(rows,['r1'],['e1'],collected,'same','same');
 const r=investigateWindow(publicResult,{...evidence,counts:{r1:'300',e1:'100'}});assert.equal(r.difference,200);assert.equal(r.percent,200);assert.equal(r.smallSample,true);assert.equal(r.comparableByCreator,true);
 const equal=investigateWindow(publicResult,{...evidence,counts:{r1:'100',e1:'100'}});assert.equal(equal.difference,0);
});
