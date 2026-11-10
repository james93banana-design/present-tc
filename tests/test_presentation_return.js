// Deterministic scheduling tests; browser layout is verified separately.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const code = fs.readFileSync(path.join(__dirname, '../assets/html/presentation-return.js'), 'utf8');
function setup() {
  let presenting = false, next = 0;
  const frames = new Map(), calls = [];
  const window = {dispatchEvent: e => calls.push(e.type)};
  vm.runInNewContext(code, {window, Event, requestAnimationFrame: fn => {
    frames.set(++next, fn); return next;
  }, cancelAnimationFrame: id => frames.delete(id)});
  const helper = window.createPresentationReturn({isPresenting: () => presenting});
  const page = id => ({isConnected: true, scrollIntoView: opts => calls.push([id, opts.behavior])});
  return {helper, calls, page, present: value => { presenting = value; },
    frame: () => { const batch = [...frames.values()]; frames.clear(); batch.forEach(fn => fn()); }};
}
const microtasks = async () => { await Promise.resolve(); await Promise.resolve(); await Promise.resolve(); };
test('returns to the exit page immediately and after two layout frames', async () => {
  const s = setup(); s.helper.begin(); s.helper.restore(s.page(8));
  assert.deepEqual(s.calls, ['tc-fit', [8, 'instant']]);
  await microtasks(); s.frame(); s.frame();
  assert.deepEqual(s.calls, ['tc-fit', [8, 'instant'], 'tc-fit', [8, 'instant']]);
});
test('repositions after native fullscreen exit finishes', async () => {
  const s = setup(); let finish;
  s.helper.restore(s.page(6), new Promise(resolve => { finish = resolve; }));
  s.frame(); s.frame(); const before = s.calls.length;
  finish(); await microtasks(); s.frame(); s.frame();
  assert.equal(s.calls.length, before + 2);
  assert.deepEqual(s.calls.at(-1), [6, 'instant']);
});
test('rapid reentry invalidates old frames and fullscreen completion', async () => {
  const s = setup(); let finish;
  s.helper.restore(s.page(6), new Promise(resolve => { finish = resolve; }));
  s.frame(); s.helper.begin(); s.present(true);
  const before = s.calls.length;
  finish(); await microtasks(); s.frame(); s.frame();
  assert.equal(s.calls.length, before);
  s.present(false); s.helper.restore(s.page(8));
  await microtasks(); s.frame(); s.frame();
  assert.deepEqual(s.calls.at(-1), [8, 'instant']);
});
test('a later exit supersedes an earlier pending exit', async () => {
  const s = setup(); let finish;
  s.helper.restore(s.page(6), new Promise(resolve => { finish = resolve; }));
  s.helper.begin(); s.helper.restore(s.page(8));
  const before = s.calls.length;
  finish(); await microtasks(); s.frame(); s.frame();
  assert.deepEqual(s.calls.slice(before), ['tc-fit', [8, 'instant']]);
});
test('rejected fullscreen exit still restores reading position', async () => {
  const s = setup(); s.helper.restore(s.page(6), Promise.reject(new Error('denied')));
  await microtasks(); s.frame(); s.frame();
  assert.deepEqual(s.calls.at(-1), [6, 'instant']);
});
test('removed pages are ignored', async () => {
  const s = setup(), page = s.page(8); page.isConnected = false;
  s.helper.restore(page); await microtasks(); s.frame(); s.frame();
  assert.deepEqual(s.calls, []);
});
