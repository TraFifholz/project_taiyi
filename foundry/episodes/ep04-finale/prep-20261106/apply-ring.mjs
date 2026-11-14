// 收官场景的 Token 开动态环：上传 tokens-ring/，写角色原型与未激活场景的 Token。
// 已有环内图的角色沿用原图；不动激活场景与 PC。旧值写 ring-before.json。
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { login, emit, getDocs, updateDocs, BASE } from 'file:///D:/Ateliar/Silver%20Wing/tools/fvtt/lib.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const DIR = 'worlds/taiyi/assets/npc/tokens-ring';
const map = JSON.parse(fs.readFileSync(path.join(HERE, 'ring-map.json'), 'utf8'));
const SCENES = ['S16 · 灾备演示厅', 'S17 · 康民诊所', 'S16 · 旧城管委会地下（玩家版）', 'S17 · 铁山车场', 'S16 · 红线封街路口'];
const COLOR = { 玄盾金卡护卫: '#d9a400', 外骨骼重装守卫: '#d97b1f' };

const { socket, cookie } = await login('taiyi');
await emit(socket, 'manageFiles', { action: 'createDirectory', storage: 'data', target: DIR }, {}).catch(() => {});
for (const f of new Set(Object.values(map))) {
  const fd = new FormData();
  fd.append('source', 'data');
  fd.append('target', DIR);
  fd.append('upload', new Blob([fs.readFileSync(path.join(HERE, 'tokens-ring', f))], { type: 'image/webp' }), f);
  const r = await fetch(BASE + '/upload', { method: 'POST', headers: { cookie }, body: fd });
  if (!r.ok) throw new Error(`upload ${f}: ${r.status}`);
}

const actors = await getDocs(socket, 'Actor');
const scenes = await getDocs(socket, 'Scene');
const before = { actors: {}, tokens: {} };
const ringOf = new Map();
const touched = new Set();
for (const n of SCENES) {
  const s = scenes.find(x => x.name === n);
  if (s.active) throw new Error('active scene: ' + n);
  for (const t of s.tokens) touched.add(t.actorId);
}
const updates = [];
for (const id of touched) {
  const a = actors.find(x => x._id === id);
  if (!a) continue;
  const p = a.prototypeToken;
  let tex = p.ring?.enabled ? p.ring.subject?.texture : null;
  if (!tex && map[p.texture.src]) tex = `${DIR}/${map[p.texture.src]}`;
  if (!tex) { console.log('跳过', a.name, p.texture.src); continue; }
  const color = COLOR[a.name] ?? p.ring?.colors?.ring ?? null;
  ringOf.set(id, { enabled: true, tex, color });
  before.actors[a.name] = p.ring;
  if (!p.ring?.enabled || p.ring.subject?.texture !== tex || (p.ring.colors?.ring ?? null) !== color) {
    updates.push({ _id: id, 'prototypeToken.ring.enabled': true, 'prototypeToken.ring.subject.texture': tex, 'prototypeToken.ring.colors.ring': color });
  }
}
if (updates.length) await updateDocs(socket, 'Actor', updates);
console.log('角色原型', updates.length);

for (const n of SCENES) {
  const s = scenes.find(x => x.name === n);
  const ups = [];
  for (const t of s.tokens) {
    const r = ringOf.get(t.actorId);
    if (!r) continue;
    before.tokens[`${n}/${t._id}`] = t.ring;
    ups.push({ _id: t._id, 'ring.enabled': true, 'ring.subject.texture': r.tex, 'ring.colors.ring': r.color });
  }
  if (ups.length) await emit(socket, 'modifyDocument', { type: 'Token', action: 'update', operation: { parentUuid: `Scene.${s._id}`, updates: ups } });
  console.log(n, ups.length);
}
fs.writeFileSync(path.join(HERE, 'ring-before.json'), JSON.stringify(before));

const after = await getDocs(socket, 'Scene');
for (const n of SCENES) {
  const s = after.find(x => x.name === n);
  const t = s.tokens;
  console.log(n, '环', t.filter(x => x.ring?.enabled).length, '/', t.length, '隐藏', t.filter(x => x.hidden).length, 'active', s.active);
}
const probe = await fetch(`${BASE}/${DIR}/${Object.values(map)[0]}`, { headers: { cookie } });
console.log('图片', probe.status, 'active', after.filter(s => s.active).map(s => s.name));
socket.close();
process.exit(0);
