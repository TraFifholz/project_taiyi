// 2026-11-06 收官备团：郁垒、方泰安按 PC 实际强度重建，补缺卡、Token、墙与新场景。重复运行跳过已做项。
// 用法（服务器当前世界须为 taiyi）：node foundry/episodes/ep04-finale/prep-20261106/apply.mjs
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { login, emit, getDocs, createDocs, updateDocs, BASE } from 'file:///D:/Ateliar/Silver%20Wing/tools/fvtt/lib.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const MAPS = path.resolve(HERE, '../../../../campaign/prep/maps');
const walls = JSON.parse(fs.readFileSync(path.join(HERE, 'walls.json'), 'utf8'));
const DIR = 'worlds/taiyi/assets/maps/s16';
const rid = () => crypto.randomBytes(12).toString('base64').replace(/[^A-Za-z0-9]/g, '').slice(0, 16);
const log = [];
const say = s => { log.push(s); console.log(s); };
const P = s => `<p>${s}</p>`;

const { socket, cookie } = await login('taiyi');
let actors = await getDocs(socket, 'Actor');
const A = n => { const a = actors.find(x => x.name === n); if (!a) throw new Error('no actor ' + n); return a; };
const mod = (type, action, operation) => emit(socket, 'modifyDocument', { type, action, operation });
const itemUp = (a, updates) => mod('Item', 'update', { parentUuid: `Actor.${a._id}`, updates });
const itemNew = (a, data) => mod('Item', 'create', { parentUuid: `Actor.${a._id}`, data });
const it = (a, n) => { const i = a.items.find(x => x.name === n); if (!i) throw new Error(`no item ${a.name}/${n}`); return i; };
const cloneItem = (src, patch = {}) => {
  const i = structuredClone(src);
  i._id = rid();
  i.effects = (i.effects || []).map(e => ({ ...e, _id: rid(), origin: null }));
  return Object.assign(i, patch);
};
const power = (src, name, cost, desc, value) => {
  const i = cloneItem(src, { name });
  i.system.description = P(desc);
  i.system.build = { ...i.system.build, cost, limit: 8, level: value ?? 1 };
  for (const e of i.effects) {
    e.name = name;
    for (const c of e.system?.changes || []) if (value != null) c.value = value;
  }
  return i;
};
const ma = A('马铁鹰 · 铜锅外骨骼'), xia = A('夏满弓'), yuko = A('黑崎欲子');

// 郁垒：30 点，单项上限 8
const yl = A('郁垒');
if (!yl.items.some(i => i.name === '坚韧 · 残帧卸力')) {
  await updateDocs(socket, 'Actor', [{
    _id: yl._id, 'system.wounds.max': 3, 'system.attributes.spirit.die.sides': 10,
    'system.attributes.strength.die.sides': 8, 'system.attributes.vigor.die.sides': 10, 'prototypeToken.disposition': -1,
  }]);
  const conc = it(A('方泰安 · 困兽'), '集中');
  await itemNew(yl, [
    cloneItem(conc),
    power(it(ma, '坚韧 · 抗打躯体'), '坚韧 · 残帧卸力', 5, '坚韧 +5，不受穿甲削减。', 5),
    power(it(ma, '格挡 · 贴身架势'), '格挡 · 提前半秒', 3, '格挡 +3。', 3),
    power(it(ma, '顽强'), '顽强', 2, '已动摇时，再次仅造成动摇的伤害不会变成损伤。'),
    power(it(xia, '躲闪 · 护卫一隅'), '躲闪 · 半秒预判', 2, '活人有意瞄准他的直接远程攻击 -2。范围攻击、无人机器、环境伤害与黑崎欲子不受影响。'),
    power(it(xia, '离奇反射'), '离奇反射', 3, '回避时忽略灵巧 -2；不可回避的范围攻击可按 -2 回避。'),
    power(it(xia, '近战攻击 · 贴身截击'), '近战攻击 · 半帧切入', 5, '近战伤害 +2d6、穿甲 +2，已合入战术刀。'),
    power(it(yuko, '绝射'), '绝射', 2, '火器伤害 +d6，已合入手枪。'),
    power(it(ma, '顽强'), '跳帧', 6, '自定义，费用是估的。每回合一次，限定自由动作瞬移至多 6 格，不能穿实墙，不引发脱离攻击。跳帧前手表蜂鸣，察觉 TN 4（枪声、蒸汽下 -2）可预知。落地后到他下回合结束脆弱（针对他的攻击 +2）。'),
    power(it(ma, '顽强'), '超级属性 · 灵巧', 2, '灵巧 d10 → d12，已计入。'),
  ]);
  await itemUp(yl, [
    { _id: it(yl, '大口径消音手枪')._id, 'system.damage': '2d8+1d6' },
    { _id: it(yl, '战术刀')._id, 'system.damage': '@str+d4+2d6', 'system.ap': 2 },
    { _id: it(yl, '运动')._id, 'system.die.sides': 10 },
    { _id: it(yl, '半秒')._id, 'system.description': P('<b>奇能 30 点</b>，单项上限 8：跳帧 6、坚韧 5、近战 5、格挡 3、离奇反射 3、躲闪 2、顽强 2、绝射 2、灵巧 2。') + P('<b>抢先</b>：每轮一次，活人对手宣告行动后，他可以立即插入行动。') + P('<b>残帧</b>：断电或全黑时，他身边浮起微光，针对他的黑暗减值失效。') + P('<b>银线例外</b>：欲子的攻击不吃躲闪，他也不能用跳帧取消欲子已命中的攻击。') },
    { _id: it(yl, '本场行动与退出')._id, 'system.description': P('专长：冷静、快速、神射、双击、改良撤离、驰援护驾。') + P('前两轮保护方泰安；受 2 损或方已带不走时退入阴影。可以负伤、丢枪，不会被俘。灭口之前不离场。') + P('方说出“是上面——”，他答一句“不用”，然后开枪。') },
  ]);
  say('郁垒 重建');
} else say('郁垒 已做');

// 方泰安 · 困兽：22 点
const fa = A('方泰安 · 困兽');
if (!fa.items.some(i => i.name === '坚韧 · 液压骨架')) {
  await updateDocs(socket, 'Actor', [{
    _id: fa._id, 'system.attributes.smarts.die.sides': 10, 'system.attributes.spirit.die.sides': 10, 'system.attributes.vigor.die.sides': 10,
  }]);
  await itemNew(fa, [
    power(it(ma, '坚韧 · 抗打躯体'), '坚韧 · 液压骨架', 4, '坚韧 +4，不受穿甲削减。', 4),
    power(it(ma, '格挡 · 贴身架势'), '格挡 · 念动偏转', 2, '格挡 +2。', 2),
    power(it(ma, '顽强'), '顽强', 2, '已动摇时，再次仅造成动摇的伤害不会变成损伤。'),
    power(it(xia, '近战攻击 · 贴身截击'), '近战攻击 · 液压义手', 5, '义手伤害 +2d6、穿甲 +2，已合入。义手受 1 个损伤即失效，他动摇并失去此项与擒抱加值。'),
  ]);
  await itemUp(fa, [
    { _id: it(fa, '官威 · 掀桌（念动）')._id, 'system.damage': '4d8' },
    { _id: it(fa, '液压处决（义手）')._id, 'system.damage': '@str+d8+2d6', 'system.ap': 4 },
    { _id: it(fa, '困兽')._id, 'system.description': it(fa, '困兽').system.description + P('<b>奇能 22 点</b>：念动 9、近战 5、坚韧 4、格挡 2、顽强 2。') + P('<b>念动投掷</b>：上一轮公开升起重物并标落点，本轮 4d8、中型爆发。烟雾、蒸汽、闪光遮断视线时念动松手。') },
  ]);
  say('方泰安 重建');
} else say('方泰安 已做');

// 罗恺：把 S16 的狙击写进卡
const luo = A('罗恺');
if (!luo.items.some(i => i.name === '反器材狙击')) {
  const smg = it(luo, '消音冲锋枪');
  await itemNew(luo, [cloneItem(smg, { name: '反器材狙击', system: { ...structuredClone(smg.system), damage: '3d10+6', ap: 8, rof: 1 } })]);
  say('罗恺 补狙击');
}

// 不羁却 0 损伤
for (const a of actors.filter(a => a.type === 'npc' && a.system.wildcard && a.system.wounds?.max === 0 && a.name !== '郁垒')) {
  await updateDocs(socket, 'Actor', [{ _id: a._id, 'system.wounds.max': 3 }]);
  say('损伤上限→3: ' + a.name);
}

// 新卡
const folders = await getDocs(socket, 'Folder');
const FN = '第四话 收官 · 地下';
let fid = folders.find(f => f.type === 'Actor' && f.name === FN)?._id;
if (!fid) fid = (await createDocs(socket, 'Folder', [{ name: FN, type: 'Actor' }]))[0]._id;
const cap = A('PMC队长'), crawler = A('轻型履带警戒机'), heavy = A('追风重型自走机'), guard = A('管委会外围执勤员');
function derive(base, o) {
  const sys = structuredClone(base.system);
  for (const [k, v] of Object.entries(o.attrs || {})) sys.attributes[k].die.sides = v;
  sys.wildcard = false;
  sys.wounds = { value: 0, max: o.wounds ?? 0, ignored: 0 };
  sys.bennies = { value: 0, max: 0 };
  if (o.pace != null) sys.pace = { ...sys.pace, ground: o.pace };
  const items = base.items.map(i => cloneItem(i));
  for (const i of items) {
    if (i.type === 'skill' && o.skills?.[i.name]) i.system.die.sides = o.skills[i.name];
    if (i.type === 'armor' && o.armor != null) i.system.armor = o.armor;
    if (i.type === 'weapon' && o.weapons?.[i.name]) Object.assign(i.system, o.weapons[i.name]);
    if (i.type === 'ability') { i.name = '特殊能力'; i.system.description = o.note; }
  }
  const kept = o.dropWeapons ? items.filter(i => i.type !== 'weapon') : items;
  const proto = structuredClone(base.prototypeToken);
  proto.name = o.name;
  proto.disposition = o.disp ?? -1;
  proto.actorLink = false;
  if (o.img) proto.texture.src = o.img;
  return { name: o.name, type: 'npc', img: o.img || base.img, folder: fid, system: sys, items: kept, ownership: { default: 0 }, prototypeToken: proto };
}
const NEW = [
  derive(cap, { name: '外骨骼重装守卫', attrs: { agility: 6, smarts: 6, spirit: 8, strength: 10, vigor: 10 }, skills: { 射击: 8, 格斗: 10 }, armor: 4, weapons: { 手枪: { damage: '@str+d8+1d6', ap: 2 } }, note: P('龙套。E7 车库与防爆门。“手枪”一栏是液压拳。') + P('<b>液压管</b>：定点打击 -2 忽略护甲，并使其移速减半。') + P('<b>硬顶</b>：动摇时仍可移动半速。') }),
  derive(cap, { name: '玄盾金卡护卫', attrs: { agility: 8, smarts: 6, spirit: 8, strength: 8, vigor: 8 }, skills: { 射击: 10, 格斗: 8, 察觉: 8 }, armor: 4, weapons: { 突击步枪: { damage: '2d8+2', ap: 3 } }, note: P('龙套。方泰安的个人金卡护卫，数量看前面分流了多少。') + P('<b>拦枪</b>：每轮一次，紧邻方泰安时替他挨一发。') + P('<b>合同到期</b>：客服终端跳出“服务永久终止”后，全员放下枪走人。') }),
  derive(crawler, { name: '固定机枪炮塔', pace: 0, armor: 4, skills: { 射击: 8 }, weapons: { 遥控轻机枪: { damage: '3d8', ap: 2 } }, note: P('E8 机房。不能移动，只能转向。') + P('<b>接管</b>：骇入或电子学成功后反打方的防线。') }),
  derive(heavy, { name: '灰区重机枪机器人', wounds: 2, weapons: { 臂载机枪: { damage: '3d8', ap: 2 } }, note: P('E10 灰区破口与站壳。3d8 按 S15 口播。追热源，发热设备也会挨打。') + P('侧面维护口或顶部镜头定点 -2，命中忽略 4 护甲。') }),
  derive(guard, { name: '灾备厅技术员', disp: 0, dropWeapons: true, note: P('被迫销毁记录的技术员，不反抗。人质给正面远程轻度掩蔽（-2），失手差 2 以内命中人质。') }),
  derive(guard, { name: '陈培安维持舱', disp: 1, pace: 0, dropWeapons: true, img: 'icons/svg/aura.svg', note: P('物件。断电 3 轮倒计时，修理或电子学 TN 4 接上备用电源。') }),
];
const missing = NEW.filter(n => !actors.some(a => a.name === n.name));
if (missing.length) {
  await createDocs(socket, 'Actor', missing);
  say('新卡: ' + missing.map(m => m.name).join('、'));
}
actors = await getDocs(socket, 'Actor');

// 上传与新场景
const fd = new FormData();
fd.append('source', 'data');
fd.append('target', DIR);
fd.append('upload', new Blob([fs.readFileSync(path.join(MAPS, '铁山车场/铁山车场.webp'))], { type: 'image/webp' }), 's17-tieshan.webp');
const up = await fetch(BASE + '/upload', { method: 'POST', headers: { cookie }, body: fd });
if (!up.ok) throw new Error('upload ' + up.status);

let scenes = await getDocs(socket, 'Scene');
const S = n => scenes.find(s => s.name === n);
const dx = S('S16 · 旧城管委会地下（玩家版）');
async function newScene(name, src, w, h) {
  if (S(name)) return;
  const d = structuredClone(dx);
  delete d._id;
  delete d._stats;
  Object.assign(d, { name, width: w, height: h, tokens: [], walls: [], active: false, navigation: false, thumb: null });
  d.levels[0].background.src = src;
  d.levels[0]._id = rid();
  if (d.initialLevel) d.initialLevel = d.levels[0]._id;
  await createDocs(socket, 'Scene', [d]);
  say('新场景: ' + name);
}
await newScene('S16 · 旧城管委会地下（GM版）', `${DIR}/s16-dixia-gm.webp`, 7200, 5200);
await newScene('S17 · 铁山车场', `${DIR}/s17-tieshan.webp`, 4000, 3000);
scenes = await getDocs(socket, 'Scene');

// 墙
for (const [n, k] of [['S16 · 旧城管委会地下（玩家版）', 'dixia'], ['S16 · 灾备演示厅', 'zaibei'], ['S17 · 康民诊所', 'kangmin'], ['S17 · 铁山车场', 'tieshan']]) {
  const s = S(n);
  if ((s.walls || []).length) { say('墙已有: ' + n); continue; }
  const data = walls[k].map(([a, b, c, d, door]) => ({ c: [a, b, c, d].map(Math.round), door, ds: 0 }));
  await mod('Wall', 'create', { parentUuid: `Scene.${s._id}`, data });
  say(`墙 ${n}: ${data.length}`);
}

// Token
const tpl = S('S16 · 灾备演示厅').tokens[0];
function token(scene, name, x, y) {
  const a = actors.find(z => z.name === name);
  if (!a) throw new Error('no actor ' + name);
  const t = structuredClone(tpl);
  delete t._id;
  Object.assign(t, { name: a.prototypeToken?.name || a.name, actorId: a._id, actorLink: false, x, y, hidden: true, delta: null, disposition: a.prototypeToken?.disposition ?? -1 });
  t.texture = { ...t.texture, src: a.prototypeToken?.texture?.src || a.img };
  if ('level' in t) t.level = scene.levels[0]._id;
  return t;
}
const gunner = '罗恺湿活组 · 黑衣枪手';
const PLACE = {
  'S16 · 灾备演示厅': [['玄盾金卡护卫', 1550, 1350], ['玄盾金卡护卫', 2250, 1350], ['玄盾金卡护卫', 3550, 1400], ['玄盾金卡护卫', 3550, 1900], ['灾备厅技术员', 600, 1300], ['灾备厅技术员', 800, 1300], ['陈培安维持舱', 500, 1650], ['何凌 · B场行动', 300, 300]],
  'S17 · 康民诊所': [[gunner, 2000, 900], [gunner, 2200, 900], [gunner, 1000, 1300]],
  'S16 · 旧城管委会地下（玩家版）': [
    ['管委会外围执勤员', 500, 1300], ['管委会外围执勤员', 1200, 1300], ['封路自动机', 2000, 2200], ['封路自动机', 2300, 2200],
    ['PMC步枪手', 1900, 2700], ['PMC步枪手', 2200, 2800], ['PMC步枪手', 2400, 2600],
    ['封后路的街头打手', 50, 2750], ['封后路的街头打手', 50, 2850], ['封后路的街头打手', 150, 2850],
    ['轻型履带警戒机', 2400, 4350], ['追风机械犬', 3100, 1000], ['追风机械犬', 4300, 2000],
    ['PMC步枪手', 4800, 1200], ['PMC步枪手', 5300, 1200], ['PMC步枪手', 5800, 1200], ['PMC步枪手', 4800, 1600], ['PMC步枪手', 5900, 1000], ['PMC步枪手', 6200, 1600],
    ['外骨骼重装守卫', 5200, 1650], ['外骨骼重装守卫', 5400, 1650], ['外骨骼重装守卫', 5600, 1650], ['外骨骼重装守卫', 5800, 1650],
    ['固定机枪炮塔', 5000, 2200], ['固定机枪炮塔', 5800, 2200], ['灰区重机枪机器人', 6800, 3700],
  ],
  'S17 · 铁山车场': [['罗恺', 3300, 600], ['追风重型自走机', 1650, 1300], ['追风重型自走机', 2150, 1300],
    [gunner, 1000, 1100], [gunner, 1300, 1900], [gunner, 1800, 2000], [gunner, 2600, 1900], [gunner, 3000, 1700], [gunner, 3700, 1300], [gunner, 900, 1700]],
};
for (const [n, list] of Object.entries(PLACE)) {
  const s = S(n);
  const have = new Set((s.tokens || []).map(t => `${t.name}@${t.x},${t.y}`));
  const data = list.map(([a, x, y]) => token(s, a, x, y)).filter(t => !have.has(`${t.name}@${t.x},${t.y}`));
  if (data.length) {
    await mod('Token', 'create', { parentUuid: `Scene.${s._id}`, data });
    say(`Token ${n}: +${data.length}`);
  }
}

fs.writeFileSync(path.join(HERE, 'apply-log.json'), JSON.stringify({ at: new Date().toISOString(), log }, null, 1));
socket.close();
process.exit(0);
