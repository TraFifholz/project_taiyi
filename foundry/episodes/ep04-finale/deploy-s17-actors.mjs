// S17 康民诊所的两张生物卡：鬼火（龙套）、吕文博的保险（不羁）。数据见 campaign/prep/sessions/S16-NPC数据.md 第 7.5 节。
// 用法（服务器当前世界须为 taiyi）：node foundry/episodes/ep04-finale/deploy-s17-actors.mjs
// 骨架复制自世界里的 PMC步枪手（技能）与罗恺（电击棍），同名角色已存在就跳过。
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { login, getDocs, createDocs, BASE } from 'file:///D:/Ateliar/Silver%20Wing/tools/fvtt/lib.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const FOLDER = '第四话 S17 · 诊所';
const DIR = 'worlds/taiyi/assets/maps/s16';
const rid = () => crypto.randomBytes(12).toString('base64').replace(/[^A-Za-z0-9]/g, '').slice(0, 16);

const SPECIAL_WISP = [
  '<p><b>电击触碰</b>：格斗，2d6，无视金属护甲。</p>',
  '<p><b>虚体</b>：普通子弹和普通近战 -2。燃烧、电击、奇能、亡灵克星不受影响。</p>',
  '<p><b>灯下隐没</b>：灯亮时对它的攻击再 -2；全黑时不生效。</p>',
  '<p><b>执念</b>：每轮一次，对最近目标低语，心魂 TN 4，失败分神。</p>',
  '<p><b>打散</b>：放出一句病人的记忆。</p>',
].join('');
const SPECIAL_BOSS = SPECIAL_WISP + [
  '<p><b>召回</b>：一个动作，重聚一团被打散的鬼火，整场最多两次；Spirit 泵关掉后不能用。</p>',
  '<p><b>闪回</b>：集中对抗目标心魂，6 英寸内一人。成功动摇；优良再加一级疲乏。</p>',
  '<p><b>认出名字</b>：有人叫出“白念秋”，它停一轮，之后攻击 -2。受 2 个损伤或被叫出名字后放完那一晚，散掉。</p>',
].join('');

const CREATURES = [
  {
    name: '鬼火', img: `${DIR}/s17-wisp.webp`, wild: false, pace: 8, toughMod: 0, special: SPECIAL_WISP,
    attrs: { agility: 10, smarts: 4, spirit: 8, strength: 4, vigor: 6 },
    skills: { 运动: 8, 格斗: 8, 察觉: 8, 潜行: 10 },
  },
  {
    name: '吕文博的保险', img: `${DIR}/s17-insurance.webp`, wild: true, pace: 6, toughMod: 1, special: SPECIAL_BOSS,
    attrs: { agility: 10, smarts: 8, spirit: 10, strength: 4, vigor: 8 },
    skills: { 运动: 8, 格斗: 8, 察觉: 10, 潜行: 8 },
  },
];

const { socket, cookie } = await login('taiyi');

for (const f of ['s17-wisp.webp', 's17-insurance.webp']) {
  const buf = fs.readFileSync(path.join(HERE, 'tokens', f));
  const fd = new FormData();
  fd.append('source', 'data');
  fd.append('target', DIR);
  fd.append('upload', new Blob([buf], { type: 'image/webp' }), f);
  const r = await fetch(BASE + '/upload', { method: 'POST', headers: { cookie }, body: fd });
  const t = await r.text();
  if (!r.ok || !/success/i.test(t)) throw new Error(`upload ${f}: ${r.status} ${t.slice(0, 200)}`);
}

const actors = await getDocs(socket, 'Actor');
const base = actors.find(a => a.name === 'PMC步枪手');
const melee = actors.find(a => a.name === '罗恺').items.find(i => i.name === '电击棍');
const note = base.items.find(i => i.type === 'ability');
if (!base || !melee || !note) throw new Error('skeleton not found');

const folders = await getDocs(socket, 'Folder');
let folderId = folders.find(f => f.type === 'Actor' && f.name === FOLDER)?._id;
if (!folderId) folderId = (await createDocs(socket, 'Folder', [{ name: FOLDER, type: 'Actor' }]))[0]._id;

const made = [];
for (const c of CREATURES) {
  if (actors.some(a => a.name === c.name)) { made.push(`skip ${c.name}`); continue; }
  const sys = structuredClone(base.system);
  for (const [k, v] of Object.entries(c.attrs)) sys.attributes[k].die.sides = v;
  sys.wildcard = c.wild;
  sys.wounds = { value: 0, max: c.wild ? 3 : 0, ignored: 0 };
  sys.bennies = c.wild ? { value: 2, max: 2 } : { value: 0, max: 0 };
  sys.pace = { ...sys.pace, base: 'fly', ground: 0, fly: c.pace };
  sys.stats.toughness.modifier = c.toughMod;

  const items = [];
  for (const [n, sides] of Object.entries(c.skills)) {
    const sk = base.items.find(i => i.type === 'skill' && i.name === n);
    const it = structuredClone(sk);
    it._id = rid();
    it.system.die.sides = sides;
    items.push(it);
  }
  const w = structuredClone(melee);
  w._id = rid();
  w.name = '电击触碰';
  w.system.damage = '2d6';
  items.push(w);
  const ab = structuredClone(note);
  ab._id = rid();
  ab.name = '特殊能力';
  ab.system.description = c.special;
  items.push(ab);

  const proto = structuredClone(base.prototypeToken);
  proto.name = c.name;
  proto.texture.src = c.img;
  proto.disposition = -1;

  await createDocs(socket, 'Actor', [{
    name: c.name, type: 'npc', img: c.img, folder: folderId, system: sys, items,
    ownership: { default: 0 }, prototypeToken: proto,
  }]);
  made.push(`made ${c.name}`);
}

const after = await getDocs(socket, 'Actor');
for (const c of CREATURES) {
  const a = after.find(x => x.name === c.name);
  console.log(JSON.stringify({ name: a?.name, wild: a?.system?.wildcard, agi: a?.system?.attributes?.agility?.die?.sides, pace: a?.system?.pace?.fly, items: a?.items?.map(i => i.name), ownership: a?.ownership?.default }));
}
console.log(made.join(' | '));
socket.close();
process.exit(0);
