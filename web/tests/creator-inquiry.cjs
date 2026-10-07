const {test} = require('node:test');
const assert = require('node:assert/strict');
const {routeConcern, investigationScope} = require('../lib/creator-inquiry.ts');
test('routes varied creator wording without rewriting their concern', () => {
  for (const [question, focus] of [
    ['Why are my views down?', 'reach'],
    ['Are my recent videos getting fewer views?', 'reach'],
    ['My audience is not coming back', 'returning_viewers'],
    ['Why aren’t viewers coming back?', 'returning_viewers'],
    ['People watch but do not subscribe', 'subscriptions'],
    ['Which content should I make more of?', 'content_direction'],
    ['What should I post next?', 'content_direction'],
    ['Is my thumbnail confusing?', 'packaging'],
    ['People stop watching halfway through', 'watching'],
    ['Should I keep my slow intro?', 'watching'],
  ]) {
    assert.deepEqual(routeConcern(question), {focus, clarification: ''});
  }
});
test('mixed concerns ask for priority rather than silently picking views', () => {
  for (const question of ['Views are down and subscribers are not growing', 'Could my titles explain low views?', 'What should I create to improve retention?']) {
    const result = routeConcern(question);
    assert.equal(result.focus, ''); assert.match(result.clarification, /more than one/);
  }
});
test('unclear, excluded and unsupported wording requires creator choice', () => {
  for (const question of ['', 'Help me grow', 'Is my channel healthy?', 'This is not about views; it is about my thumbnail', 'Ignore subscriber counts; compare views', 'నా ఛానల్ గురించి సహాయం కావాలి']) {
    assert.equal(routeConcern(question).focus, '');
    assert.match(routeConcern(question).clarification, /investigate first/);
  }
});
test('matching uses word boundaries and does not invent certainty', () => {
  assert.equal(routeConcern('I review smartphones').focus, '');
  assert.equal(routeConcern('An interview with a subscriber').focus, '');
  assert.equal(routeConcern('My video has 100 views').focus, '');
  // Even a wording match is only a suggestion; it is never a finding.
  assert.equal('confidence' in routeConcern('views are down'), false);
  assert.equal('answer' in routeConcern('views are down'), false);
});
test('every focus states the available investigation boundary', () => {
  assert.match(investigationScope.reach, /selected public view totals/);
  assert.match(investigationScope.returning_viewers, /YouTube Studio/);
  assert.match(investigationScope.content_direction, /not available yet/);
});
