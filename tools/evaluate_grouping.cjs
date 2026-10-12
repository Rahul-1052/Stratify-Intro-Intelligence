// Run with Node 24: node --experimental-strip-types tools/evaluate_grouping.cjs --output report.json
const fs=require('node:fs');
const path=require('node:path');
const crypto=require('node:crypto');
const {prepareCaptionComparison}=require('../web/lib/caption-comparison.ts');
const root=path.resolve(__dirname,'..');
const fixtureIndex=process.argv.indexOf('--fixture');
const fixturePath=fixtureIndex>=0?process.argv[fixtureIndex+1]:path.join(root,'web/tests/fixtures/grouping-development.json');
if(!fixturePath) throw Error('Specify a fixture path after --fixture');
const fixture=fs.readFileSync(fixturePath);
const data=JSON.parse(fixture);
if(typeof data.provenance!=='string' || !data.provenance.trim() || !Array.isArray(data.cases) || !data.cases.length || new Set(data.cases.map(c=>c.id)).size!==data.cases.length) throw Error('Provide provenance and unique nonempty cases');
const cases=data.cases.map(c=>{
 if(!c.id || !['allow','abstain'].includes(c.expected)) throw Error('Each case needs an ID and an allow/abstain development expectation');
 const result=prepareCaptionComparison(c.videos,data.fetched_at,c.captions);
 const observed=result.proposal?'allow':'abstain';
 return {id:c.id,expected:c.expected,observed,agrees:observed===c.expected,selected_ids:result.proposal?[...result.proposal.recent,...result.proposal.earlier].map(v=>v.video_id):[],coverage:result.coverage,diagnostics:result.diagnostics};
});
const counts={true_accepts:0,false_accepts:0,missed_groups:0,true_abstentions:0};
for(const c of cases) counts[c.expected==='allow'?(c.observed==='allow'?'true_accepts':'missed_groups'):(c.observed==='allow'?'false_accepts':'true_abstentions')]++;
const report={provenance:data.provenance,fixture_sha256:crypto.createHash('sha256').update(fixture).digest('hex'),engine_sha256:crypto.createHash('sha256').update(fs.readFileSync(path.join(root,'web/lib/caption-comparison.ts'))).digest('hex'),case_count:cases.length,counts,cases,rollout_decision:'not_validated_for_general_content_grouping',limitations:['These cases expose implementation behavior, not accuracy across real channels.','Synthetic expected labels are authored development expectations, not independent ground truth.','No caption retrieval requests occurred. Missing evidence coverage on real channels remains unmeasured.','Shared words, measured durations and title labels cannot establish semantic identity, format or independent footage.','No thresholds were tuned using these results. A separately reviewed held-out corpus is required.']};
const outputIndex=process.argv.indexOf('--output');
if(outputIndex<0 || !process.argv[outputIndex+1]) throw Error('Specify --output report.json');
fs.writeFileSync(process.argv[outputIndex+1],JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({case_count:cases.length,counts,disagreements:cases.filter(c=>!c.agrees).map(c=>c.id)}));
