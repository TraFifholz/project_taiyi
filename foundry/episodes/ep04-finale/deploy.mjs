// 第四话收官篇部署到 fvtt.univare.icu / taiyi：上传地图，建场景（隐藏 Token）与两本日志，回读校验并写 deployment.json。
// 用法（服务器当前世界须为 taiyi）：
//   python -I foundry/episodes/ep04-finale/build_payload.py
//   node foundry/episodes/ep04-finale/deploy.mjs            # 部署（已存在的同名场景/日志跳过，不覆盖）
//   node foundry/episodes/ep04-finale/deploy.mjs --verify   # 只回读校验
//   node foundry/episodes/ep04-finale/deploy.mjs --verify --refresh-pages   # 卡片改过后，原地更新两本日志的正文
// 登录走 silver-wing/tools/fvtt 的 QA 账号（secrets 在 silver-wing/tools/secrets）。本机有环境代理时 Node 的 fetch 默认直连，无需处理。
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { login, emit, getDocs, createDocs, BASE } from 'file:///D:/SilverWing/silver-wing/tools/fvtt/lib.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const payload = JSON.parse(fs.readFileSync(path.join(HERE, 'payload.json'), 'utf8'));
const VERIFY_ONLY = process.argv.includes('--verify');
const DIR = 'worlds/taiyi/assets/maps/s16';
const SCENE_FOLDER = '03 · 战斗与剧情';
const GM_JOURNAL = 'S16 · 收官篇主持卡（GM）';
const HANDOUT_JOURNAL = 'S16 · 收官篇玩家道具（GM 展示用）';

const rid = () => crypto.randomBytes(12).toString('base64').replace(/[^A-Za-z0-9]/g, '').slice(0, 16);
const sha = buf => crypto.createHash('sha256').update(buf).digest('hex');

// 场景与 Token 摆放（坐标为像素，每格 100；全部隐藏，按桌上实际再拖）
const SCENES = [
  {
    name: 'S16 · 灾备演示厅', file: 's16-zaibei.webp', width: 4000, height: 3200,
    tokens: [
      ['方泰安 · 困兽', 1950, 1250],
      ['郁垒', 1850, 2400],
      ['罗恺', 3300, 1500],
      ['罗恺湿活组 · 黑衣枪手', 800, 1000], ['罗恺湿活组 · 黑衣枪手', 900, 1250],
      ['PMC步枪手', 1200, 700], ['PMC步枪手', 2400, 700], ['PMC步枪手', 3000, 1300], ['PMC步枪手', 3000, 1700],
    ],
  },
  {
    name: 'S16 · 红线封街路口', file: 's16-fengjie.webp', width: 4400, height: 3000,
    tokens: [
      ['方泰安 · 困兽', 3700, 1350],
      ['郁垒', 3700, 1500],
      ['秦有邻', 2900, 700],
      ['管委会外围执勤员', 3200, 950], ['管委会外围执勤员', 3400, 1000],
      ['管委会外围执勤员', 3200, 2000], ['管委会外围执勤员', 3400, 1950],
    ],
  },
  { name: 'S16 · 旧城管委会地下（玩家版）', file: 's16-dixia-player.webp', width: 7200, height: 5200, tokens: [] },
];

async function upload(cookie, file, remoteName) {
  const buf = fs.readFileSync(file);
  const fd = new FormData();
  fd.append('source', 'data');
  fd.append('target', DIR);
  fd.append('upload', new Blob([buf], { type: 'image/webp' }), remoteName);
  const r = await fetch(BASE + '/upload', { method: 'POST', headers: { cookie }, body: fd });
  const t = await r.text();
  if (!r.ok || !/success/i.test(t)) throw new Error(`upload ${remoteName}: ${r.status} ${t.slice(0, 200)}`);
  return sha(buf);
}

async function remoteSha(cookie, remoteName) {
  const r = await fetch(`${BASE}/${DIR}/${remoteName}`, { headers: { cookie } });
  return r.ok ? sha(Buffer.from(await r.arrayBuffer())) : `HTTP ${r.status}`;
}

const { socket, cookie } = await login('taiyi');
const report = { world: 'taiyi', at: new Date().toISOString(), assets: [], scenes: [], journals: [], skipped: [] };

if (!VERIFY_ONLY) {
  await emit(socket, 'manageFiles', { action: 'createDirectory', storage: 'data', target: DIR }, {}).catch(() => {});
  for (const u of payload.uploads) {
    const exists = (await remoteSha(cookie, u.remote)) === sha(fs.readFileSync(u.local));
    if (!exists) await upload(cookie, u.local, u.remote);
  }

  const folders = await getDocs(socket, 'Folder');
  const sceneFolder = folders.find(f => f.type === 'Scene' && f.name === SCENE_FOLDER)?._id ?? null;
  const actors = await getDocs(socket, 'Actor');
  const actorByName = n => actors.find(a => a.name === n) ?? (() => { throw new Error('actor not found: ' + n); })();
  const existingScenes = new Set((await getDocs(socket, 'Scene')).map(s => s.name));

  for (const sc of SCENES) {
    if (existingScenes.has(sc.name)) { report.skipped.push(sc.name); continue; }
    const levelId = rid();
    const tokens = sc.tokens.map(([name, x, y]) => {
      const a = actorByName(name);
      const proto = structuredClone(a.prototypeToken ?? {});
      return {
        ...proto, _id: rid(), name: a.name, actorId: a._id, actorLink: false, x, y, hidden: true, level: levelId,
        texture: { ...(proto.texture ?? {}), src: proto.texture?.src || a.img },
        disposition: proto.disposition ?? -1, width: proto.width ?? 1, height: proto.height ?? 1,
      };
    });
    await createDocs(socket, 'Scene', [{
      name: sc.name, folder: sceneFolder, width: sc.width, height: sc.height, padding: 0, navigation: false,
      tokenVision: false, ownership: { default: 0 },
      grid: { type: 1, size: 100, distance: 1, units: '英寸', alpha: 0, style: 'solidLines', thickness: 1, color: '#000000' },
      levels: [{ _id: levelId, name: '地面', background: { src: `${DIR}/${sc.file}`, color: '#141210' }, elevation: { bottom: 0, top: 20 } }],
      tokens,
    }]);
  }

  const existingJournals = new Set((await getDocs(socket, 'JournalEntry')).map(j => j.name));
  const textPage = (p, i) => ({ name: p.name, type: 'text', sort: (i + 1) * 100000, text: { content: p.html, format: 1 } });
  if (existingJournals.has(GM_JOURNAL)) report.skipped.push(GM_JOURNAL);
  else await createDocs(socket, 'JournalEntry', [{ name: GM_JOURNAL, ownership: { default: 0 }, pages: payload.gmPages.map(textPage) }]);
  if (existingJournals.has(HANDOUT_JOURNAL)) report.skipped.push(HANDOUT_JOURNAL);
  else {
    const pages = payload.handouts.map(textPage);
    pages.push({ name: '旧城管委会地下结构图', type: 'image', sort: (pages.length + 1) * 100000, src: `${DIR}/s16-dixia-player.webp` });
    await createDocs(socket, 'JournalEntry', [{ name: HANDOUT_JOURNAL, ownership: { default: 0 }, pages }]);
  }
}

// --refresh-pages：同名日志已存在时，按页名原地更新正文（不删不建）
if (process.argv.includes('--refresh-pages')) {
  const js = await getDocs(socket, 'JournalEntry');
  for (const [name, src] of [[GM_JOURNAL, payload.gmPages], [HANDOUT_JOURNAL, payload.handouts]]) {
    const j = js.find(x => x.name === name);
    if (!j) continue;
    const updates = src.map(p => ({ _id: j.pages.find(pg => pg.name === p.name)?._id, 'text.content': p.html })).filter(u => u._id);
    const r = await emit(socket, 'modifyDocument', { type: 'JournalEntryPage', action: 'update', operation: { parentUuid: `JournalEntry.${j._id}`, updates } });
    if (r.error) throw new Error(JSON.stringify(r.error));
    report.refreshed = (report.refreshed ?? 0) + updates.length;
  }
}

// 回读校验
for (const u of payload.uploads) {
  const want = sha(fs.readFileSync(u.local));
  const got = await remoteSha(cookie, u.remote);
  report.assets.push({ remote: `${DIR}/${u.remote}`, sha256: got, ok: got === want });
}
const scenesNow = await getDocs(socket, 'Scene');
for (const sc of SCENES) {
  const s = scenesNow.find(x => x.name === sc.name);
  const lvl = s?.levels?.[0];
  report.scenes.push({
    name: sc.name, id: s?._id ?? null, background: lvl?.background?.src ?? null,
    tokens: s?.tokens?.length ?? 0, expectedTokens: sc.tokens.length,
    allHidden: (s?.tokens ?? []).every(t => t.hidden), allOnLevel: (s?.tokens ?? []).every(t => t.level === lvl?._id),
    active: s?.active ?? null,
    ok: !!s && s.tokens.length === sc.tokens.length && (s.tokens ?? []).every(t => t.hidden && t.level === lvl?._id) && !s.active,
  });
}
const journalsNow = await getDocs(socket, 'JournalEntry');
for (const [name, n] of [[GM_JOURNAL, payload.gmPages.length], [HANDOUT_JOURNAL, payload.handouts.length + 1]]) {
  const j = journalsNow.find(x => x.name === name);
  report.journals.push({ name, id: j?._id ?? null, pages: j?.pages?.length ?? 0, expectedPages: n, defaultOwnership: j?.ownership?.default, ok: !!j && j.pages.length === n && j.ownership?.default === 0 });
}
report.passed = [...report.assets, ...report.scenes, ...report.journals].every(x => x.ok);
fs.writeFileSync(path.join(HERE, 'deployment.json'), JSON.stringify(report, null, 2));
console.log(JSON.stringify({ passed: report.passed, refreshed: report.refreshed ?? 0, skipped: report.skipped, assets: report.assets.map(a => a.ok), scenes: report.scenes.map(s => [s.tokens, s.ok]), journals: report.journals.map(j => [j.pages, j.ok]) }));
socket.close();
process.exit(report.passed ? 0 : 1);
