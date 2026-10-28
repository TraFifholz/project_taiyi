const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const audit = path.resolve(__dirname, '../../../records/audits/chirp-publication-20260903');
const report = [];
let now = 1000, nextId = 1;
const timers = new Map(), hooks = new Map(), handlers = new Map(), broadcasts = [];
const settings = new Map([['smartphone-widget.useGameTime', true]]);
const widget = { currentApp: 'chirp', apps: new Map(), element: null };
const game = { user: { isGM: true }, i18n: { localize: k => k, format: k => k }, settings: {
  get: (m, k) => structuredClone(settings.get(m + '.' + k)),
  set: async (m, k, v) => settings.set(m + '.' + k, structuredClone(v)),
  register: () => {}, settings: new Map(),
} };
const context = vm.createContext({ console, Map, Set, Date, Number, Array, Object, JSON,
  game, foundry: { utils: { deepClone: structuredClone } }, navigator: { language: 'en-US' },
  document: { activeElement: null },
  Hooks: { on: (name, fn) => { const id = nextId++; hooks.set(id, { name, fn }); return id; }, off: (name, id) => hooks.delete(id) },
  setInterval: fn => { const id = nextId++; timers.set(id, fn); return id; }, clearInterval: id => timers.delete(id),
  setTimeout: () => 0, clearTimeout: () => {},
  mockWidget: widget, clockNow: () => now,
});
const cache = new Map();
function getModule(id) {
  id = path.posix.normalize(id);
  if (cache.has(id)) return cache.get(id);
  let text;
  if (id.endsWith('/BaseApp.js')) text = 'export class BaseApp { constructor(widget){this.widget=widget;} updateContent(html){this.html=html;this.renderCount=(this.renderCount||0)+1;} hide(){} removeAllListeners(){} }';
  else if (id.endsWith('/smartphone-widget.js')) text = 'export class SmartphoneWidget { static async getInstance(){return mockWidget;} static registerBadgeUpdater(){} static updateBadge(){} }';
  else if (id.endsWith('/SmartphoneTime.js')) text = 'export class SmartphoneTime { static now(){return clockNow();} static format(t){return String(t);} }';
  else {
    const local = path.join(__dirname, 'module', id);
    text = fs.readFileSync(fs.existsSync(local) ? local : path.join(audit, 'source', id), 'utf8');
  }
  const mod = new vm.SourceTextModule(text, { context, identifier: id,
    importModuleDynamically: async spec => { const dep = getModule(path.posix.join(path.posix.dirname(id), spec)); if (dep.status === 'unlinked') await dep.link(linker); if (dep.status === 'linked') await dep.evaluate(); return dep; },
  });
  cache.set(id, mod); return mod;
}
const linker = (spec, ref) => getModule(path.posix.join(path.posix.dirname(ref.identifier), spec));
async function load(id) { const mod = getModule(id); if (mod.status === 'unlinked') await mod.link(linker); if (mod.status === 'linked') await mod.evaluate(); return mod.namespace; }
const emit = async name => { for (const h of [...hooks.values()]) if (h.name === name) await h.fn(); };
const makePost = (id, timestamp, extra = {}) => ({ id, timestamp, authorSocialId: 'author', content: id + '_BODY #test', media: [], likes: ['me'], bookmarks: ['me'], rechirps: ['me'], ...extra });

(async () => {
  const { ChirpApp } = await load('apps/ChirpApp.js');
  const { publishedChirps } = await load('apps/chirp/chirp-publication.js');
  const app = new ChirpApp(widget); widget.apps.set('chirp', app);
  const fixture = {
    past: makePost('past', 900), due: makePost('due', 1000),
    future: makePost('future', 2000, { pinned: true, media: [{ src: 'future-image.webp', type: 'image' }] }),
    scheduled: makePost('scheduled', 900, { isHidden: true, publishTimestamp: 2000 }),
    released: makePost('released', 900, { isHidden: true, publishTimestamp: 950 }),
    draft: makePost('draft', 900, { isHidden: true }),
    quote: makePost('quote', 900, { quoteChirpId: 'future' }),
    reply: makePost('reply', 900, { replyTo: 'future' }),
    nested: makePost('nested', 900, { replyTo: 'reply' }),
    futureReply: makePost('futureReply', 2000, { replyTo: 'past' }),
    oldReply: makePost('oldReply', 900, { replyTo: 'past' }),
    invalid: makePost('invalid', 'bad'), missing: makePost('missing', null),
    malformedSchedule: makePost('malformedSchedule', 900, { publishTimestamp: 'bad' }),
  };
  const serialized = JSON.stringify(fixture);
  settings.set('smartphone-chirp-app.chirp-posts', fixture);
  await app.loadPosts();
  assert.deepEqual([...app.state.posts.keys()].sort(), ['past', 'due', 'released', 'quote', 'oldReply'].sort());
  assert.equal(app._allPosts.size, 14);
  assert.equal(JSON.stringify(fixture), serialized);
  report.push('Publication boundary, hidden drafts, schedules, invalid dates, nested replies, raw data preservation');

  app.state.me = 'me'; app.state.following = ['author'];
  for (const id of ['me', 'author']) app.state.accounts.set(id, { socialId: id, handle: id, name: id, bio: '', followers: [], following: ['author'], chirpIds: [], profilePal: ['#000', '#fff'] });
  const views = [
    ['timeline', { tab: 'forYou' }], ['timeline', { tab: 'following' }],
    ...['chirps', 'replies', 'media', 'likes'].map(profileTab => ['profile', { handle: 'author', profileTab }]),
    ['search', { q: '#test' }], ['detail', { chirpId: 'future' }],
    ['detail', { chirpId: 'past' }], ['bookmarks', {}],
    ...['top', 'latest', 'media'].map(trendTab => ['trend_detail', { trendName: '#test', trendTab }]),
  ];
  for (const [view, params] of views) {
    app.currentView = view; app.viewParams = { ...params, _displayCount: 1000 }; app.render();
    for (const id of ['future', 'futureReply', 'scheduled', 'draft', 'reply', 'nested', 'invalid', 'missing', 'malformedSchedule']) {
      assert.ok(!app.html.includes(id + '_BODY'), `${view}/${params.tab}: leaked ${id}`);
    }
    assert.ok(!app.html.includes('future-image.webp'));
  }
  app.currentView = 'timeline'; app.viewParams = {}; app.render();
  assert.ok(app.html.includes('past_BODY')); assert.ok(app.html.includes('CHIRP.unavailableChirp'));
  report.push('Actual renderers: both timelines, four profile tabs, search, detail, bookmarks, trend and quoted-post fallback');

  app.startPublicationWatch(); app.startPublicationWatch();
  assert.equal(timers.size, 1); assert.equal(hooks.size, 3);
  now = 1999; await emit('updateWorldTime'); assert.ok(!app.html.includes('future_BODY'));
  now = 2000; await emit('smartphoneTimeChanged'); assert.ok(app.html.includes('future_BODY')); assert.ok(app.state.posts.has('nested')); assert.ok(app.state.posts.has('scheduled'));
  now = 999; [...timers.values()][0](); assert.ok(!app.html.includes('future_BODY')); assert.ok(!app.state.posts.has('due'));
  app.currentView = 'compose'; const renderCount = app.renderCount;
  now = 2000; await emit('updateWorldTime'); assert.equal(app.renderCount, renderCount); assert.equal(app._hasDeferredRealtimeRender, true);
  app.currentView = 'timeline'; app.flushDeferredRealtimeRender(); assert.ok(app.html.includes('future_BODY'));
  app.onHide(); assert.equal(timers.size, 0); assert.equal(hooks.size, 0);
  app.startPublicationWatch(); assert.equal(timers.size, 1); assert.equal(hooks.size, 3);
  report.push('Inclusive due time, two clock hooks, polling, clock rewind, composing-draft preservation, hide/reopen cleanup');

  // Use the production socket callback without registering settings a second time.
  ChirpApp.registerSettings = async () => {};
  ChirpApp.initialize({ register: (name, fn) => handlers.set(name, fn) });
  app.currentView = 'timeline'; now = 1000;
  await handlers.get('updateChirp')({ chirp: makePost('realtime', 3000) });
  assert.ok(app._allPosts.has('realtime')); assert.ok(!app.state.posts.has('realtime')); assert.ok(!app.html.includes('realtime_BODY'));
  now = 3000; await emit('updateWorldTime'); assert.ok(app.html.includes('realtime_BODY')); assert.ok(app.html.includes('future-image.webp'));
  await handlers.get('updateChirp')({ chirp: makePost('realtime', 4000) });
  assert.ok(!app.state.posts.has('realtime')); assert.ok(!app.html.includes('realtime_BODY'));
  await handlers.get('updateChirp')({ deleted: true, chirpId: 'realtime' });
  assert.ok(!app._allPosts.has('realtime')); assert.ok(!app.html.includes('realtime_BODY'));
  settings.set('smartphone-chirp-app.chirp-posts', { changed: makePost('changed', 5000) });
  for (const h of hooks.values()) if (h.name === 'updateSetting') await h.fn({ key: 'smartphone-chirp-app.chirp-posts' });
  assert.deepEqual([...app._allPosts.keys()], ['changed']); assert.equal(app.state.posts.size, 0);
  app.cleanup(); assert.equal(timers.size, 0); assert.equal(hooks.size, 0); assert.equal(app._allPosts.size, 0);
  report.push('Actual realtime callback and world-setting refresh do not bypass publication filtering');

  const { registerGmHandlers } = await load('socket/gmHandlers.js');
  registerGmHandlers({ register: (name, fn) => handlers.set(name, fn), executeForEveryone: (...args) => broadcasts.push(structuredClone(args)) });
  settings.set('smartphone-chirp-app.chirp-posts', { p: makePost('p', 900) }); now = 1000;
  assert.ok((await handlers.get('chirp_gmScheduleChirp')({ chirpId: 'p', publishTimestamp: 'bad' })).error);
  assert.equal(broadcasts.length, 0);
  await handlers.get('chirp_gmScheduleChirp')({ chirpId: 'p', publishTimestamp: 2000 });
  let saved = settings.get('smartphone-chirp-app.chirp-posts');
  assert.equal(saved.p.timestamp, 2000); assert.equal(saved.p.isHidden, true); assert.equal(broadcasts.length, 1);
  assert.equal(publishedChirps(saved, 1999).size, 0); assert.equal(publishedChirps(saved, 2000).size, 1);
  await handlers.get('chirp_gmPublishChirp')({ chirpId: 'p' }); saved = settings.get('smartphone-chirp-app.chirp-posts');
  assert.equal(saved.p.timestamp, 1000); assert.equal(saved.p.publishTimestamp, null); assert.equal(saved.p.isHidden, false);
  game.user.isGM = false; assert.ok((await handlers.get('chirp_gmScheduleChirp')({ chirpId: 'p', publishTimestamp: 2000 })).error);
  report.push('Native schedule/publish handlers: date validation, immediate broadcast, due visibility, manual publish and existing GM guard');

  const before = JSON.parse(fs.readFileSync(path.join(audit, 'before.json'), 'utf8'));
  const rawBefore = JSON.stringify(before.posts);
  const visible = publishedChirps(before.posts, before.now);
  assert.equal(Object.values(before.posts).filter(p => p.timestamp > before.now).length, 68);
  assert.equal([...visible.values()].filter(p => p.timestamp > before.now).length, 0);
  assert.equal(JSON.stringify(before.posts), rawBefore);
  report.push(`Real snapshot: ${Object.keys(before.posts).length} preserved; ${visible.size} eligible; 68 future posts excluded`);
  fs.writeFileSync(path.join(audit, 'test-results.json'), JSON.stringify({ status: 'PASS', checks: report }, null, 2));
  console.log(JSON.stringify({ status: 'PASS', checks: report }, null, 2));
})().catch(error => { console.error(error); process.exitCode = 1; });
