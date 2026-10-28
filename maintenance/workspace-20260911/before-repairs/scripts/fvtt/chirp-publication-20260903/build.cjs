const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const source = path.resolve(__dirname, '../../../records/audits/chirp-publication-20260903/source');
const output = path.join(__dirname, 'module');
const original = file => fs.readFileSync(path.join(source, file), 'utf8');
const replace = (text, before, after) => {
  if (text.split(before).length !== 2) throw Error('Patch context is not unique: '+before.slice(0,80));
  return text.replace(before, after);
};
let app = original('apps/ChirpApp.js');
const nl = app.includes('\r\n') ? '\r\n' : '\n';
const lines = text => text.replace(/\n/g, nl);
app = replace(app, "import { L } from './chirp/chirp-utils.js';", "import { L, chirpNow } from './chirp/chirp-utils.js';"+nl+"import { publishedChirps } from './chirp/chirp-publication.js';");
app = replace(app, 'instance.state.posts.delete(data.chirpId);', 'instance._allPosts.delete(data.chirpId);');
app = replace(app, 'instance.state.posts.set(data.chirp.id, data.chirp);', 'instance._allPosts.set(data.chirp.id, foundry.utils.deepClone(data.chirp));');
app = replace(app, lines("      if (widgetManager.currentApp === 'chirp') {\n        instance.renderAfterRealtimeUpdate();\n      }\n    });\n\n    socket.register('updateProfile'"), lines("      instance.refreshPublishedPosts();\n      if (widgetManager.currentApp === 'chirp') {\n        instance.renderAfterRealtimeUpdate();\n      }\n    });\n\n    socket.register('updateProfile'"));
app = replace(app, '    this.state = {', '    this._allPosts = new Map();'+nl+'    this._publicationTimer = null;'+nl+'    this._publicationHooks = [];'+nl+nl+'    this.state = {');
const loadBefore = lines(`  async loadPosts() {
    const raw = (await game.settings.get(MODULE_ID, 'chirp-posts')) || {};
    this.state.posts.clear();
    for (const [id, chirp] of Object.entries(raw)) {
      this.state.posts.set(id, foundry.utils.deepClone(chirp));
    }
  }`);
const loadAfter = lines(`  async loadPosts() {
    const raw = (await game.settings.get(MODULE_ID, 'chirp-posts')) || {};
    this._allPosts.clear();
    for (const [id, chirp] of Object.entries(raw)) {
      this._allPosts.set(id, foundry.utils.deepClone(chirp));
    }
    this.refreshPublishedPosts();
  }

  refreshPublishedPosts(now = chirpNow()) {
    const visible = publishedChirps(this._allPosts, now);
    const changed = visible.size !== this.state.posts.size
      || [...visible.keys()].some(id => !this.state.posts.has(id));
    this.state.posts = visible;
    return changed;
  }

  startPublicationWatch() {
    if (this._publicationTimer !== null) return;
    const refresh = () => {
      if (this.widget?.currentApp !== 'chirp') return;
      if (this.refreshPublishedPosts()) this.renderAfterRealtimeUpdate();
    };
    for (const name of ['smartphoneTimeChanged', 'updateWorldTime']) {
      this._publicationHooks.push([name, Hooks.on(name, refresh)]);
    }
    this._publicationHooks.push(['updateSetting', Hooks.on('updateSetting', async setting => {
      if (setting.key !== MODULE_ID + '.chirp-posts') return;
      await this.loadPosts();
      if (this.widget?.currentApp === 'chirp') this.renderAfterRealtimeUpdate();
    })]);
    // Also handles real-time mode and time providers which omit a change hook.
    this._publicationTimer = setInterval(refresh, 1000);
  }

  stopPublicationWatch() {
    if (this._publicationTimer !== null) clearInterval(this._publicationTimer);
    this._publicationTimer = null;
    for (const [name, id] of this._publicationHooks) Hooks.off(name, id);
    this._publicationHooks = [];
  }`);
app = replace(app, loadBefore, loadAfter);
app = replace(app, '  async show(...args) {', '  async show(...args) {'+nl+'    this.startPublicationWatch();');
app = replace(app, '  onHide() {', '  onHide() {'+nl+'    this.stopPublicationWatch();');
app = replace(app, '  cleanup() {', '  cleanup() {'+nl+'    this.stopPublicationWatch();'+nl+'    this._allPosts.clear();');
app = replace(app, '  render() {', '  render() {'+nl+'    this.refreshPublishedPosts();');

let gm = original('socket/gmHandlers.js');
gm = replace(gm, lines("    posts[chirpId].isHidden = true;\n    posts[chirpId].publishTimestamp = publishTimestamp;\n    await game.settings.set(MODULE_ID, 'chirp-posts', posts);"), lines("    if (publishTimestamp == null || publishTimestamp === '' || !Number.isFinite(Number(publishTimestamp))) return { error: 'Invalid publication time' };\n    posts[chirpId].isHidden = true;\n    posts[chirpId].publishTimestamp = Number(publishTimestamp);\n    posts[chirpId].timestamp = Number(publishTimestamp);\n    await game.settings.set(MODULE_ID, 'chirp-posts', posts);\n    socket.executeForEveryone('updateChirp', { chirp: posts[chirpId] });"));
gm = replace(gm, '    posts[chirpId].isHidden = false;', lines("    posts[chirpId].isHidden = false;\n    posts[chirpId].publishTimestamp = null;\n    const now = chirpNow();\n    if (!Number.isFinite(Number(posts[chirpId].timestamp)) || Number(posts[chirpId].timestamp) > now) posts[chirpId].timestamp = now;"));
for (const [file,text] of [['apps/ChirpApp.js',app],['socket/gmHandlers.js',gm]]) {
  const target=path.join(output,file);fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,text);
}
const files=['apps/chirp/chirp-publication.js','apps/ChirpApp.js','socket/gmHandlers.js'];
const hash = file => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const manifest=files.map(file=>({file,before:fs.existsSync(path.join(source,file))?hash(path.join(source,file)):null,after:hash(path.join(output,file))}));
fs.writeFileSync(path.join(__dirname,'deployment.json'),JSON.stringify({module:'smartphone-chirp-app',version:'1.1.1',files:manifest},null,2));
console.log(JSON.stringify(manifest));
