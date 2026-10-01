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
