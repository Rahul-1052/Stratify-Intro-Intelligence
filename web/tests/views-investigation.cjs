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
const {suggestNextSteps}=require('../lib/views-investigation.ts');
const comparable=()=>investigateViews(rows,['r1','r2','r3'],['e1','e2','e3'],collected,'same','same');
const matched=(extra={})=>investigateWindow(comparable(),{...evidence,...extra});
test('suggestions cite only existing evidence and preserve provenance',()=>{
 const plan=suggestNextSteps(matched());assert.equal(plan.suggestions[0].id,'collect_impressions');
 assert(plan.suggestions.every(s=>s.evidenceIds.every(id=>plan.evidence.some(e=>e.id===id))));
 assert(plan.evidence.every(e=>e.source==='creator_entered_unverified'));assert.equal(plan.evidence[0].videoIds.length,6);
});
test('topic uncertainty and small selection take priority over exposure interpretation',()=>{
 const publicResult=investigateViews(rows,['r1'],['e1'],collected,'unknown','same');
 const plan=suggestNextSteps(investigateWindow(publicResult,evidence));assert.deepEqual(plan.suggestions.map(s=>s.id),['review_comparability','review_small_sample']);assert.equal(plan.status,'comparison_needs_review');
});
test('lower views and impressions lead to traffic-source investigation, not a cause',()=>{
 const plan=suggestNextSteps(matched({impressions:{r1:'10',r2:'20',r3:'30',e1:'100',e2:'200',e3:'300'}}));assert.equal(plan.suggestions[0].id,'inspect_exposure');assert.match(plan.suggestions[0].limitation,/not established as causing/);assert.deepEqual(plan.suggestions[0].evidenceIds,['matched_views','matched_impressions']);
});
test('equal or higher impressions with lower views never calculate CTR',()=>{
 for(const value of ['200','500']){
 const plan=suggestNextSteps(matched({impressions:{r1:value,r2:value,r3:value,e1:'100',e2:'200',e3:'300'}}));assert.equal(plan.suggestions[0].id,'inspect_source_mix');assert.match(plan.suggestions[0].limitation,/not the platform’s impression click-through rate/);assert.equal('ctr' in plan,false);
 }
});
test('equal or higher viewing counts do not presume decline',()=>{
 for(const value of ['400','900']){const plan=suggestNextSteps(matched({counts:{...evidence.counts,r1:value,r2:value,r3:value}}));assert.equal(plan.suggestions[0].id,'revisit_concern');}
});
test('optional impressions require complete valid counts while zero stays valid',()=>{
 assert.throws(()=>matched({impressions:{r1:'10'}}));assert.throws(()=>matched({impressions:{...evidence.counts,r1:'-1'}}));
 const r=matched({impressions:Object.fromEntries(rows.map(v=>[v.video_id,'0']))});assert.equal(r.impressions.recentMedian,0);assert.equal(r.impressions.earlierMedian,0);
});

const {proposeComparison}=require('../lib/views-investigation.ts');
test('prepared groups ignore performance and input order and preserve unknown metrics',()=>{
 const a=proposeComparison(rows,collected),b=proposeComparison([...rows].reverse().map(v=>({...v,views:null,title:'changed',duration:null})),collected);
 assert.deepEqual(a.recent.map(v=>v.video_id),b.recent.map(v=>v.video_id));assert.deepEqual(a.earlier.map(v=>v.video_id),b.earlier.map(v=>v.video_id));assert.equal(a.recent.length,3);assert.equal(a.earlier.length,3);
});
test('proposal excludes fresh invalid future dates and refuses insufficient separate groups',()=>{
 assert.equal(proposeComparison(rows.slice(0,5),collected),null);
 const extra=[video('fresh','2026-09-30',999999),video('future','2027-01-01',0),video('missing',null,0)];
 assert.equal(proposeComparison([...rows,...extra],collected).excluded,3);
 assert.equal(proposeComparison(rows.map(v=>({...v,published_at:'2026-09-20'})),collected),null);
 assert.throws(()=>proposeComparison([...rows,rows[0]],collected));assert.throws(()=>proposeComparison(rows,'bad'));
});

const {comparisonTitleWarnings}=require('../lib/views-investigation.ts');
test('explicit conflicting title clues prompt review without changing selection or proving formats',()=>{
 const selected=[{...rows[0],title:'Half Filipino | Standup Comedy'},{...rows[1],title:'Good Day LA interview'}];
 const before=JSON.stringify(selected), warnings=comparisonTitleWarnings(selected);
 assert.equal(warnings.length,2);assert.deepEqual(warnings.map(w=>w.label),['stand-up comedy','interview']);assert.equal(JSON.stringify(selected),before);
 assert.equal(comparisonTitleWarnings([{...rows[0],title:'LIVE Proposal!'}, {...rows[1],title:'A funny story'}]).length,0);
 assert.equal(comparisonTitleWarnings([{...rows[0],title:'Stand-up Comedy'}, {...rows[1],title:'Standup Comedy'}]).length,0);
 assert.equal(comparisonTitleWarnings([{...rows[0],title:'Interviewing myself'}, {...rows[1],title:'Standup Comedy'}]).length,0);
});
