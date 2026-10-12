const {test}=require('node:test');
const assert=require('node:assert/strict');
const {namedSeriesOptions}=require('../lib/named-series.ts');
const collected='2026-10-06T00:00:00Z';
const videos=Array.from({length:6},(_,i)=>({video_id:'v'+i,title:i===0?'The Call | A Short Film':`The Influencer Agency - Ep 0${6-i} - Different story`,published_at:new Date(Date.parse(collected)-(i+8)*86400000).toISOString(),duration:'PT10M',views:100+i,source_url:'https://www.youtube.com/watch?v=v'+i}));
test('series choice replaces mixed groups with three recent and two earlier episodes',()=>{
 const [p]=namedSeriesOptions(videos,['v0','v1','v2','v3','v4','v5'],collected);
 assert.equal(p.label,'The Influencer Agency');assert.equal(p.recent.length,3);assert.equal(p.earlier.length,2);
 assert(![...p.recent,...p.earlier].some(v=>v.video_id==='v0'));assert.equal(p.excluded,1);
 assert.match(p.reason,/unverified/);
 const changed=namedSeriesOptions(videos.map(v=>({...v,views:999999})).reverse(),['v0','v1','v2'],collected)[0];
 assert.deepEqual(changed.recent.map(v=>v.video_id),p.recent.map(v=>v.video_id));
});
test('ambiguous episodes, insufficient coverage and tied chronology offer no replacement',()=>{
 assert.deepEqual(namedSeriesOptions(videos.slice(0,5),['v0','v1','v2'],collected),[]);
 assert.deepEqual(namedSeriesOptions(videos.map((v,i)=>i===2?{...v,title:videos[1].title}:v),['v0','v1','v2'],collected),[]);
 assert.deepEqual(namedSeriesOptions(videos.map(v=>({...v,published_at:'2026-09-01'})),['v0','v1','v2'],collected),[]);
});
test('different names are not guessed into series and pure series selections need no prompt',()=>{
 assert.deepEqual(namedSeriesOptions(videos.map(v=>({...v,title:'unlabeled '+v.video_id})),['v0','v1','v2'],collected),[]);
 assert.deepEqual(namedSeriesOptions(videos,['v1','v2','v3'],collected),[]);
});
