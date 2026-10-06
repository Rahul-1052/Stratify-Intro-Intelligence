const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const AxeBuilder = require('@axe-core/playwright').default;
const qa = process.env.STRATIFY_QA_DIR;
const audit = async page => {const result = await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa']).analyze(); assert.deepEqual(result.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>n.target)})), []);};
(async()=>{const browser=await chromium.launch({headless:true,executablePath:process.env.STRATIFY_CHROMIUM_PATH,args:['--no-sandbox']});const context=await browser.newContext();const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
await page.goto('http://127.0.0.1:3005');
await page.getByRole('button',{name:'Create profile',exact:true}).waitFor();
await page.keyboard.press('Tab');assert.equal(await page.locator(':focus').innerText(),'Skip to workspace');await page.keyboard.press('Enter');assert.equal(await page.locator(':focus').getAttribute('id'),'workspace');
await page.getByLabel('Creator name').fill('Browser QA');await page.getByLabel('Channel name',{exact:true}).fill('Synthetic clip validation');await page.getByRole('button',{name:'Create profile',exact:true}).click();await page.getByText('No saved analyses yet.').waitFor();
await page.getByText('Optional: observe an owned video’s opening',{exact:true}).click();await page.getByLabel('Video file').setInputFiles(`${qa}/owned.mp4`);await page.getByLabel('I own this video').check();await page.getByRole('button',{name:'Observe intro'}).click();await page.getByRole('button',{name:'Save this analysis'}).waitFor({timeout:60000});
assert.equal(await page.locator('.creator-report .experiment').count(),1);assert.equal(await page.locator('tbody tr').count(),20);await page.getByText('View sampled frame measurements',{exact:true}).click();await page.getByText('View sampled frame measurements',{exact:true}).click();
await page.getByRole('button',{name:'Save this analysis'}).click();await page.getByRole('button',{name:'Open owned.mp4, revision 1'}).waitFor();
await page.getByLabel('Experiment status for').first().selectOption('running');await page.getByText('Experiment status saved.',{exact:true}).waitFor();
for(const width of [1440,768,390,320]){await page.setViewportSize({width,height:1000});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`overflow at ${width}`);await page.screenshot({path:`${qa}/report-${width}.png`,fullPage:true});await audit(page);}
await page.reload();await page.getByRole('button',{name:'Open owned.mp4, revision 1'}).click();await page.getByRole('heading',{name:'Saved analysis',exact:true}).waitFor();assert.equal(await page.locator(':focus').innerText(),'Saved analysis');assert.equal(await page.locator('.reopened-report .confidence-row b').first().innerText(),'High');assert.equal(await page.locator('.reopened-report .finding').count(),1);assert.equal(await page.getByLabel('Experiment status for').first().inputValue(),'running');await page.screenshot({path:`${qa}/reopened-320.png`,fullPage:true});
await page.getByRole('button',{name:'Close saved analysis'}).click();assert.match(await page.locator(':focus').getAttribute('aria-label'),/revision 1/);
await page.route('**/api/memory',route=>route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'Memory unavailable for QA'})}));await page.reload();await page.getByRole('alert').filter({hasText:'Memory unavailable for QA'}).waitFor();await page.unroute('**/api/memory');await page.getByRole('button',{name:'Retry saved history'}).click();await page.getByRole('button',{name:'Open owned.mp4, revision 1'}).waitFor();
await page.getByText('Optional: observe an owned video’s opening',{exact:true}).click();await page.getByLabel('Video file').setInputFiles(`${qa}/stable.mp4`);await page.getByLabel('I own this video').check();await page.getByRole('button',{name:'Observe intro'}).click();await page.getByText('No experiment is supported yet.',{exact:true}).waitFor({timeout:60000});assert.equal(await page.locator('.creator-report .experiment').count(),0);await page.screenshot({path:`${qa}/abstention-320.png`,fullPage:true});
// Channel UI contract uses explicit fixtures; existing upload/memory coverage above uses real services.
await page.reload();
await page.route('**/api/channel-workspace', async route => {
  const input = route.request().postDataJSON();
  assert.equal(input.concern, 'Why are my views down?');
  assert.deepEqual(input.inquiry,{focus:'reach',question:'Which recent videos lost reach?',period:'Last six uploads',confirmed:true});
  await route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'Channel facts unavailable for QA'})});
});
await page.getByLabel('YouTube channel link or @handle').fill('@fixture');
// Starter clicks fill editable text without submitting or collecting evidence.
for (const [starter, expectedFocus] of [
  ['Are my recent videos getting fewer views?', 'reach'],
  ['Which content should I make more of?', 'content_direction'],
  ['Why aren’t viewers coming back?', 'returning_viewers'],
]) {
  await page.getByRole('button',{name:starter,exact:true}).click();
  assert.equal(await page.getByLabel('What would you like help understanding about your channel?').inputValue(),starter);
  assert.equal(await page.locator('#inquiry-title').count(),0);
  await page.getByRole('button',{name:'Review my question'}).click();
  assert.equal(await page.getByLabel('Investigation focus').inputValue(),expectedFocus);
  assert.equal(await page.getByLabel('The question you want Stratify to investigate').inputValue(),starter);
  if (expectedFocus !== 'reach') assert.match(await page.locator('#investigation-scope').innerText(), /YouTube Studio|not available yet/);
  await page.getByRole('button',{name:'Edit channel or original concern'}).click();
}
await page.getByLabel('What would you like help understanding about your channel?').fill('Views are down and subscribers are not growing');
await page.getByRole('button',{name:'Review my question'}).click();
assert.equal(await page.getByLabel('Investigation focus').inputValue(),'');
await page.getByText('You mentioned more than one concern. Which should we investigate first?',{exact:true}).waitFor();
await page.getByRole('button',{name:'Edit channel or original concern'}).click();
await page.getByLabel('What would you like help understanding about your channel?').fill('Why are my views down?');
await page.getByRole('button',{name:'Review my question'}).click();
assert.equal(await page.locator(':focus').innerText(), 'Let’s make sure we understand your question');
assert.equal(await page.getByLabel('Investigation focus').inputValue(),'reach');
await page.getByLabel('The question you want Stratify to investigate').fill('Which recent videos lost reach?');
assert.equal(await page.getByLabel('Investigation focus').inputValue(),'');
await page.getByLabel('Investigation focus').selectOption('reach');
await page.getByLabel('Which period or videos do you mean? (optional)').fill('Last six uploads');
await page.getByRole('button',{name:'Confirm question and collect facts'}).click();
await page.getByRole('alert').filter({hasText:'Channel facts unavailable for QA'}).waitFor();
assert.equal(await page.getByLabel('What would you like help understanding about your channel?').inputValue(), 'Why are my views down?');
await page.unroute('**/api/channel-workspace');
await page.route('**/api/channel-workspace', route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({
  inquiry:{focus:'reach',question:'Which recent videos lost reach?',period:'Last six uploads',evidence_needed:['Views measured over the same time after publication']},
  concern:'Why are my views down?', fetched_at:'2026-10-01T12:00:00Z',
  channel:{title:'Fixture channel',source_url:'https://www.youtube.com/@fixture',created_at:'2020-01-01',subscribers:null,video_count:3},
  coverage:{entries_checked:2,videos_available:2,unavailable_entries:0,more_uploads_available:true,uploads_playlist_available:true,oldest_published_at:'2025-01-01',newest_published_at:'2026-01-01'},
  videos:[{video_id:'fixture1',title:'A deliberately long public video title to verify narrow screens',source_url:'https://www.youtube.com/watch?v=abcdefghijk',published_at:'2026-01-01',duration:'PT5M',views:0,likes:null,comments:null},{video_id:'fixture2',title:'Earlier tutorial',source_url:'https://www.youtube.com/watch?v=bcdefghijkl',published_at:'2025-01-01',duration:'PT6M',views:100,likes:3,comments:0}],
  limitations:['Public counts do not establish why performance changed.']
})}));
await page.getByRole('button',{name:'Confirm question and collect facts'}).click();
await page.getByRole('heading',{name:'Fixture channel',exact:true}).waitFor();
assert.equal(await page.getByRole('button',{name:'Prepare a comparison for me',exact:true}).isDisabled(),true);
await page.getByText('Choose videos that match your requested period. Stratify has not applied that scope automatically.',{exact:true}).waitFor();
assert.equal(await page.locator('.workflow-step').first().getAttribute('open'),null);
assert.equal(await page.locator('.workflow-step').nth(1).getAttribute('open'),null);
assert.equal(await page.locator(':focus').innerText(), 'Fixture channel');
assert.equal(await page.locator('[aria-labelledby="channel-result-title"]').getByText('Which recent videos lost reach?',{exact:true}).count(),1);
await page.getByText('Inspect the public video facts (2)',{exact:true}).click();
assert.equal(await page.getByRole('region',{name:'Channel video facts'}).getByText('Unavailable',{exact:true}).count(),2);
await page.getByRole('button',{name:'Compare selected public facts'}).click();
await page.getByRole('alert').filter({hasText:'Select at least one recent video and one earlier video.'}).waitFor();
await page.getByRole('button',{name:'Choose videos myself',exact:true}).click();
await page.getByLabel('Comparison group for A deliberately long public video title to verify narrow screens').selectOption('recent');
await page.getByLabel('Comparison group for Earlier tutorial').selectOption('earlier');
await page.getByLabel('I checked that these selected videos match my requested period.').check();
await page.getByRole('button',{name:'Compare selected public facts'}).click();
await page.getByRole('heading',{name:'What the selected videos show',exact:true}).waitFor();
await page.waitForFunction(()=>document.activeElement?.id==='views-result-title');
assert.equal(await page.locator(':focus').innerText(),'What the selected videos show');
await page.getByText('Recent videos in this selection have lower typical lifetime views.',{exact:true}).waitFor();
assert.equal(await page.getByText('Adjust selected videos',{exact:true}).evaluate(node=>node.parentElement.open),false);
for (const name of ['Your next step']) {
  assert.equal(await page.getByRole('heading',{name,exact:true}).count(),1);
}
assert.equal(await page.getByText('See details',{exact:true}).evaluate(node=>node.parentElement.open),false);
await page.getByText('See details',{exact:true}).click();
await page.getByText(/Difference: -100 views/).waitFor();
assert.equal(await page.getByLabel('Window count for Earlier tutorial').isVisible(),false);
await page.getByText('Add my analytics (optional)',{exact:true}).click();
await page.getByLabel('Window count for A deliberately long public video title to verify narrow screens').fill('0');
await page.getByLabel('Window count for Earlier tutorial').fill('100');
await page.getByRole('button',{name:'Review matched-window evidence'}).click();
await page.getByRole('alert').filter({hasText:'Confirm a completed window'}).waitFor();
await page.getByLabel('I checked that every count uses this completed window').check();
await page.getByRole('button',{name:'Review matched-window evidence'}).click();
await page.getByRole('heading',{name:'Your views investigation',exact:true}).waitFor();
await page.waitForFunction(()=>document.activeElement?.id==='matched-result-title');
await page.getByText(/the selected recent group has a lower median engaged views count over the first 7 days/).waitFor();
await page.getByText('0 of 1 selected recent videos are at or above the earlier group’s median.',{exact:false}).waitFor();
await page.getByLabel('Add registered thumbnail impressions for these same windows').check();
assert.equal(await page.getByRole('heading',{name:'Your views investigation',exact:true}).count(),0);
await page.getByLabel('Window impressions for A deliberately long public video title to verify narrow screens').fill('20');
await page.getByLabel('Window impressions for Earlier tutorial').fill('100');
await page.getByLabel('I checked that every count uses this completed window').check();
await page.getByRole('button',{name:'Review matched-window evidence'}).click();
await page.getByRole('heading',{name:'Suggestions supported by this evidence',exact:true}).waitFor();
await page.getByRole('link',{name:'Selected comparison context',exact:true}).first().click();
await page.waitForFunction(()=>document.activeElement?.id==='suggestion-evidence-selection_context');
await page.getByText(/Selected recent median registered thumbnail impressions: 20; earlier median: 100/).waitFor();
for(const width of [1440,768,390,320]){
  await page.setViewportSize({width,height:1000});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth), `channel overflow at ${width}`);
  await audit(page);await page.screenshot({path:`${qa}/channel-${width}.png`,fullPage:true});
}
await page.getByLabel('Time after each video was published').selectOption('28');
assert.equal(await page.getByRole('heading',{name:'Your views investigation',exact:true}).count(),0);
assert.equal(await page.getByLabel('Window count for Earlier tutorial').inputValue(),'');
assert.equal(await page.getByLabel('Window impressions for Earlier tutorial').inputValue(),'');
assert.equal(await page.getByLabel('I checked that every count uses this completed window').isChecked(),false);
await page.getByRole('button',{name:'Review selected videos',exact:true}).click();
await page.waitForFunction(()=>document.activeElement?.id==='comparison-search');
assert.equal(await page.getByLabel('Show selected videos only').isChecked(),true);
assert.equal(await page.getByText('Adjust selected videos',{exact:true}).evaluate(node=>node.parentElement.open),true);
await page.getByText('Check topics and formats (optional)',{exact:true}).click();
await page.getByLabel('Do the groups use similar formats?').selectOption('different');
assert.equal(await page.getByRole('heading',{name:'What the selected videos show',exact:true}).count(),0);
await page.getByLabel('Comparison group for Earlier tutorial').selectOption('');
await page.getByRole('button',{name:'Compare selected public facts'}).click();
await page.getByRole('alert').filter({hasText:'Select at least one recent video and one earlier video.'}).waitFor();
await page.getByRole('button',{name:'Edit channel or original concern'}).click();
assert.equal(await page.getByRole('heading',{name:'Fixture channel',exact:true}).count(),0);
await page.getByLabel('What would you like help understanding about your channel?').fill('I want to grow');
await page.getByRole('button',{name:'Review my question'}).click();
assert.equal(await page.getByLabel('Investigation focus').inputValue(),'');
assert.equal(await page.getByLabel('The question you want Stratify to investigate').inputValue(),'I want to grow');
assert.equal(await page.getByLabel('Which period or videos do you mean? (optional)').inputValue(),'');
// Caption matching uses synthetic text, never a claim about a live creator's videos.
await page.unroute('**/api/channel-workspace');
const captionVideos=Array.from({length:8},(_,i)=>({video_id:`testvideo0${i}x`,title:`Different title ${i}`,source_url:`https://www.youtube.com/watch?v=testvideo0${i}x`,published_at:`2026-09-${28-i}T17:00:00Z`,duration:null,views:i,likes:null,comments:null}));
await page.route('**/api/channel-workspace',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({concern:'I want to grow',fetched_at:'2026-10-05T18:00:00Z',inquiry:{question:'I want to grow',focus:'reach',period:'',evidence_needed:[]},channel:{title:'Caption fixture',source_url:'https://www.youtube.com/@fixture',created_at:null,subscribers:null,video_count:8},coverage:{entries_checked:8,videos_available:8,unavailable_entries:0,more_uploads_available:false,uploads_playlist_available:true,oldest_published_at:'2026-09-21',newest_published_at:'2026-09-28'},videos:captionVideos,limitations:[]})}));
await page.getByLabel('Investigation focus').selectOption('reach');
await page.getByRole('button',{name:'Confirm question and collect facts'}).click();
await page.getByRole('heading',{name:'Caption fixture',exact:true}).waitFor();
await page.route('**/api/public-captions', route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({results:captionVideos.map(v=>({video_id:v.video_id,status:'blocked',text:null}))})}));
await page.getByRole('button',{name:'Prepare a comparison for me',exact:true}).click();
await page.getByText(/This setup uses dates only; no content match was established/).waitFor();
await page.getByText('Provisional selection by date. Video content, formats and shared material have not been verified. Matching titles do not establish a fair comparison.',{exact:true}).waitFor();
await page.getByText('Add captions for content-based grouping (optional)',{exact:true}).click();
await page.getByLabel('Caption files (SRT, VTT or TXT)').setInputFiles({name:'unmatched.srt',mimeType:'text/plain',buffer:Buffer.from('hello')});
await page.getByRole('alert').filter({hasText:'Could not match unmatched.srt'}).waitFor();
const vocabulary='budget expenses savings income spending planning debt loans cash reserve goals strategy monthly balance costs payments invest accounts emergency needs'.split(' ');
await page.getByLabel('Caption files (SRT, VTT or TXT)').setInputFiles(captionVideos.map((v,i)=>({name:`${v.video_id}.txt`,mimeType:'text/plain',buffer:Buffer.from(Array.from({length:3},(_,j)=>vocabulary.map((w,k)=>`${vocabulary[(k*(2*i+1)+j)%20]} detail${i}section${j}`).join(' ')).join('\n'))})));
await page.getByText(/8 captions available .*8 have enough text/).waitFor();
await page.getByRole('button',{name:'Prepare a comparison for me',exact:true}).click();
await page.getByText('Provisional selection using shared caption wording. Topic, format and footage independence are not verified.',{exact:true}).waitFor();
await page.getByText('Why these videos?',{exact:true}).click();
await page.getByText(/Different title 0: shared words/).waitFor();
for(const width of [1440,768,390,320]) {await page.setViewportSize({width,height:1000});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await audit(page);}
await page.getByRole('button',{name:'Remove captions',exact:true}).click();
assert.equal(await page.getByRole('heading',{name:'Review the proposed groups',exact:true}).count(),0);
await page.unroute('**/api/public-captions');
await page.route('**/api/public-captions',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({results:captionVideos.map((v,i)=>({video_id:v.video_id,status:'available',text:Array.from({length:3},(_,j)=>vocabulary.map((w,k)=>`${vocabulary[(k*(2*i+1)+j)%20]} detail${i}section${j}`).join(' ')).join('\n')}))})}));
await page.getByRole('button',{name:'Prepare a comparison for me',exact:true}).click();
await page.getByText(/8 of 8 candidate uploads have retrieved English captions/).waitFor();
await page.getByText('Provisional selection using shared caption wording. Topic, format and footage independence are not verified.',{exact:true}).waitFor();
await page.getByRole('button',{name:'Remove captions',exact:true}).click();
await page.unroute('**/api/public-captions');
await page.route('**/api/public-captions',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({results:captionVideos.map((v,i)=>({video_id:v.video_id,status:'available',text:Array.from({length:60},(_,k)=>`topic${i}word${k}`).join(' ')}))})}));
await page.getByRole('button',{name:'Prepare a comparison for me',exact:true}).click();
await page.getByText(/No content-based groups were prepared. The current shared-word rules/).waitFor();
await page.getByText('Why no groups were prepared',{exact:true}).click();
await page.getByText(/largest shared-word match set had 1 uploads/).waitFor();
assert.equal(await page.getByRole('heading',{name:'Review the proposed groups',exact:true}).count(),0);
// Requested upload counts reach the actual selection; this is still date-only evidence.
await page.getByRole('button',{name:'Edit channel or original concern'}).click();
await page.getByLabel('What would you like help understanding about your channel?').fill('Why did my views drop?');
await page.getByRole('button',{name:'Review my question'}).click();
await page.getByLabel('Which period or videos do you mean? (optional)').fill('last 3 uploads vs previous 3 uploads');
await page.unroute('**/api/channel-workspace');
await page.route('**/api/channel-workspace',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({concern:'Why did my views drop?',fetched_at:'2026-10-05T18:00:00Z',inquiry:{question:'Why did my views drop?',focus:'reach',period:'last 3 uploads vs previous 3 uploads',evidence_needed:[]},channel:{title:'Scoped fixture',source_url:'https://www.youtube.com/@fixture',created_at:null,subscribers:null,video_count:8},coverage:{entries_checked:8,videos_available:8,unavailable_entries:0,more_uploads_available:false,uploads_playlist_available:true,oldest_published_at:'2026-09-21',newest_published_at:'2026-09-28'},videos:captionVideos,limitations:[]})}));
await page.getByRole('button',{name:'Confirm question and collect facts'}).click();
await page.getByRole('heading',{name:'Scoped fixture',exact:true}).waitFor();
await page.getByRole('button',{name:'Prepare a comparison for me',exact:true}).click();
await page.getByText(/We picked 3 recent and 3 earlier available uploads from your requested scope/).waitFor();
await page.getByRole('button',{name:'Compare selected public facts',exact:true}).click();
await page.getByText('These public counts cannot explain why views changed.',{exact:true}).waitFor();
await page.getByText('See details',{exact:true}).click();
await page.getByRole('heading',{name:'Selected source videos',exact:true}).waitFor();
await audit(page);assert.deepEqual(errors,[]);console.log('PASS: real upload/report/profile/save/reload/reopen/status persistence; 4 widths; skip link; focus return; memory failure/retry; abstention; no browser exceptions');await browser.close();})().catch(e=>{console.error(e);process.exit(1)});
