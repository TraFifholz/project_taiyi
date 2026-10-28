const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const { login } = require('./calendaria-2030/world.cjs');
const { base } = require('./calendaria-2030/inspect.cjs');

const ROOT = path.resolve(__dirname, '../../records/prep/ep03-fvtt-20260903/portraits/extras-vehicles-20260904');
const REMOTE_DIR = 'worlds/taiyi/assets/npc/avatars';
const specs = [
  ['合规清理员', '3b235949f8822316', 'nai-20260904/assets/candidates/EP03-EXTRA-CLEANER-合规清理员-nai-avatar.webp', 'EP03-EXTRA-CLEANER-nai-avatar.webp', '7ebd3eef7c1d841dc4edcfaeef20e68e7815bd7fd376e0b04f1b2eac7dd92a87'],
  ['青梢队成员', 'edf233155b4144b1', 'nai-20260904/assets/candidates/EP03-EXTRA-QINGSHAO-青梢队成员-nai-avatar.webp', 'EP03-EXTRA-QINGSHAO-nai-avatar.webp', 'd444e90027fda12e1a05249e66f696df655e000a8b1c15b2fb42661084b926dc'],
  ['冷藏车司机', '58225f08c387421e', 'nai-20260904/assets/candidates/EP03-EXTRA-MA-DRIVER-冷藏车司机-nai-avatar.webp', 'EP03-EXTRA-MA-DRIVER-nai-avatar.webp', '139d91659bcbe32b334d3762954ea9ae00f812ebd1627dcae6bae5f2341c97ec'],
  ['M-3 随车审计员', 'c97aece17d9be1cc', 'nai-20260904/assets/candidates/EP03-EXTRA-AUDITOR-M-3 随车审计员-nai-avatar.webp', 'EP03-EXTRA-AUDITOR-nai-avatar.webp', 'b1db01fda833efb74d6f6cd826bff51e7e9cbdbd224cd7a18c677495c29af898'],
  ['追风警戒无人机', 'f4202ab0f6698a33', 'nai-20260904/assets/candidates/EP03-EXTRA-DRONE-追风警戒无人机-nai-avatar.webp', 'EP03-EXTRA-DRONE-nai-avatar.webp', '5201697595db05fe0321ff9d6655657ee6b6b19dc5d12a997b5f783ce3d9d32d'],
  ['中继车 M-3', '298635cb754b5aea', 'generated/EP03-VEHICLE-M3.png', 'EP03-VEHICLE-M3.png', 'ffe62ef94e2fb036f437d68da074ed7ac08e7a5025b86095727634ab90861394'],
  ['零号库载车 Z-0', 'afe354e8fe5faec3', 'generated/EP03-VEHICLE-Z0.png', 'EP03-VEHICLE-Z0.png', 'c464d46cdb9ba804d6ab2fccdfb0947e73e306a4e48687f172e46a2b78e4135d'],
  ['追风载客轿车／空诱饵车', 'e259aa8a691ed14b', 'generated/EP03-VEHICLE-PASSENGER.png', 'EP03-VEHICLE-PASSENGER.png', 'b5147fbd45f3d6813b962ee3d308ce69b6cc01aff0dedc849b7d54dde3a72066'],
  ['马铁鹰的短轴冷藏厢车', '3a333216b680256b', 'generated/EP03-VEHICLE-COLD-TRUCK.png', 'EP03-VEHICLE-COLD-TRUCK.png', '767936ae3c506934ecc607a9c6ce51c061cbccda6ec2d6b5b1779ed2fe4e0887'],
  ['罗恺的白色 SUV', '698ef8d10a6b1491', 'generated/EP03-VEHICLE-WHITE-SUV.png', 'EP03-VEHICLE-WHITE-SUV.png', '3997fd2c53359ac19bbe141362cd103988c3fd44dd4d2c16a28ef3933103fd0b'],
  ['青梢队行动车', '389b4cc35538b135', 'generated/EP03-VEHICLE-QINGSHAO.png', 'EP03-VEHICLE-QINGSHAO.png', '0852519af0d4f4ebf6aed7c45530ebf46016515ad4b1339805919014538e790e'],
  ['欲子的退役玄盾巡逻越野车', '864f29cc4b5e420c', 'generated/EP03-VEHICLE-PATROL-SUV.png', 'EP03-VEHICLE-PATROL-SUV.png', 'bab8bef51d7871c1a226c16e528164473dfca024d8b0f882724980cc3b172ab2'],
].map(([name, actorId, local, remote, sha256]) => ({name, actorId, local:path.join(ROOT, local), remote, sha256, remotePath:`${REMOTE_DIR}/${remote}`}));

const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
async function modify(c, type, action, operation) {
  const response = await c.call('modifyDocument', {type, action, operation});
  if (response?.error) throw Error(JSON.stringify(response.error));
  return response;
}
function actorOf(world, id) { return world.actors.find(a => a._id === id); }
function tokenRows(world, actorId) {
  return world.scenes.flatMap(scene => (scene.tokens || []).filter(t => t.actorId === actorId).map(t => ({sceneId:scene._id, sceneName:scene.name, tokenId:t._id, src:t.texture?.src})));
}
async function upload(c, spec) {
  const bytes = fs.readFileSync(spec.local);
  assert.equal(sha(bytes), spec.sha256, `Local hash mismatch: ${spec.name}`);
  const form = new FormData();
  form.set('source', 'data');
  form.set('target', REMOTE_DIR);
  form.set('upload', new File([bytes], spec.remote, {type:spec.remote.endsWith('.webp')?'image/webp':'image/png'}));
  form.set('overwrite', 'true');
  const response = await fetch(`${base}/upload`, {method:'POST', headers:{Cookie:c.cookie}, body:form});
  const text = await response.text();
  let data; try { data = JSON.parse(text); } catch { throw Error(`Upload response ${response.status}: ${text.slice(0,200)}`); }
  if (!response.ok || data.error) throw Error(`Upload failed ${spec.name}: ${JSON.stringify(data)}`);
  const reported = data.path || data.url || data.file || spec.remotePath;
  assert(reported.includes(spec.remote), `Unexpected upload path for ${spec.name}: ${JSON.stringify(data)}`);
  const check = await fetch(`${base}/${spec.remotePath}?verify=${Date.now()}`, {headers:{Cookie:c.cookie}, cache:'no-store'});
  assert(check.ok, `Remote fetch failed ${spec.name}: ${check.status}`);
  const remoteBytes = Buffer.from(await check.arrayBuffer());
  assert.equal(sha(remoteBytes), spec.sha256, `Remote hash mismatch: ${spec.name}`);
  return {bytes:remoteBytes.length, response:data};
}
async function main() {
  const write = process.argv.includes('--write');
  const verify = process.argv.includes('--verify');
  for (const s of specs) assert(fs.existsSync(s.local), `Missing local file: ${s.local}`);
  const c = await login();
  try {
    const before = c.world;
    assert.equal(before.world.id, 'taiyi');
    assert.equal(before.system.id, 'swade');
    assert.equal(c.user.name, 'AssistantAgent');
    assert(c.user.role >= 4);
    const inventory = specs.map(s => {
      const actor = actorOf(before, s.actorId);
      assert(actor, `Missing actor ${s.name}`);
      assert.equal(actor.name, s.name, `Actor identity mismatch ${s.actorId}`);
      return {name:s.name, actorId:s.actorId, type:actor.type, img:actor.img, prototypeToken:actor.prototypeToken?.texture?.src, sceneTokens:tokenRows(before, s.actorId)};
    });
    console.log(JSON.stringify({mode:write?'write':verify?'verify':'preflight', world:before.world.id, system:before.system.id, user:c.user.name, targets:inventory.length, existingSceneTokens:inventory.reduce((n,x)=>n+x.sceneTokens.length,0), inventory}, null, 2));
    if (verify) {
      const checked=[];
      for (const s of specs) {
        const actor=actorOf(before,s.actorId);
        assert.equal(actor.img,s.remotePath,`Actor image mismatch: ${s.name}`);
        assert.equal(actor.prototypeToken?.texture?.src,s.remotePath,`Prototype token mismatch: ${s.name}`);
        const response=await fetch(`${base}/${s.remotePath}?verify=${Date.now()}`,{headers:{Cookie:c.cookie},cache:'no-store'});
        assert(response.ok,`Remote fetch failed ${s.name}: ${response.status}`);
        const bytes=Buffer.from(await response.arrayBuffer());
        assert.equal(sha(bytes),s.sha256,`Remote hash mismatch: ${s.name}`);
        for(const t of tokenRows(before,s.actorId))assert.equal(t.src,s.remotePath,`Scene token mismatch: ${s.name}/${t.sceneName}`);
        checked.push({name:s.name,actorId:s.actorId,path:s.remotePath,sha256:s.sha256,bytes:bytes.length});
      }
      console.log(JSON.stringify({passed:true,world:before.world.id,user:c.user.name,remoteHashesMatched:checked.length,actorImagesMatched:checked.length,prototypeTokensMatched:checked.length,sceneTokensMatched:inventory.reduce((n,x)=>n+x.sceneTokens.length,0),checked},null,2));
      return;
    }
    if (!write) return;
    const uploaded=[];
    for (const s of specs) uploaded.push({name:s.name, ...(await upload(c,s))});
    for (const s of specs) {
      const old = actorOf(before, s.actorId);
      const patch = {_id:s.actorId, img:s.remotePath, 'prototypeToken.texture.src':s.remotePath};
      if (old.prototypeToken?.ring?.enabled) {
        patch['prototypeToken.ring.subject.texture'] = s.remotePath;
        patch['prototypeToken.ring.subject.scale'] = 1;
      }
      await modify(c, 'Actor', 'update', {updates:[patch], diff:true, recursive:true, render:false});
      for (const scene of before.scenes) {
        const updates=(scene.tokens||[]).filter(t=>t.actorId===s.actorId).map(t=>{
          const u={_id:t._id, 'texture.src':s.remotePath};
          if(t.ring?.enabled){u['ring.subject.texture']=s.remotePath;u['ring.subject.scale']=1;}
          return u;
        });
        if(updates.length)await modify(c,'Token','update',{parentUuid:`Scene.${scene._id}`,updates,diff:true,recursive:true,render:false});
      }
    }
    const after = await c.call('world');
    const actors = specs.map(s => {
      const a=actorOf(after,s.actorId);
      assert.equal(a.img,s.remotePath,`Actor image readback mismatch: ${s.name}`);
      assert.equal(a.prototypeToken?.texture?.src,s.remotePath,`Prototype token readback mismatch: ${s.name}`);
      if(a.prototypeToken?.ring?.enabled)assert.equal(a.prototypeToken.ring.subject.texture,s.remotePath,`Prototype ring mismatch: ${s.name}`);
      const tokens=tokenRows(after,s.actorId);
      for(const t of tokens)assert.equal(t.src,s.remotePath,`Scene token mismatch: ${s.name}/${t.sceneName}`);
      return {name:s.name,actorId:s.actorId,path:s.remotePath,sha256:s.sha256,sceneTokens:tokens};
    });
    const report={verifiedAt:new Date().toISOString(),world:after.world.id,system:after.system.id,user:c.user.name,passed:true,actors,actorImagesChanged:actors.length,prototypeTokensChanged:actors.length,sceneTokensChanged:actors.reduce((n,a)=>n+a.sceneTokens.length,0),uploaded:uploaded.map(x=>({name:x.name,bytes:x.bytes}))};
    console.log(JSON.stringify(report,null,2));
  } finally { c.socket.disconnect(); }
}
main().catch(error => { console.error(error.stack); process.exitCode=1; });
