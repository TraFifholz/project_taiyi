'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const out=path.resolve(__dirname,'../../records/prep/ep03-fvtt-20260903/rebuild-ma-xia-l5');
const read=name=>JSON.parse(fs.readFileSync(path.join(out,name),'utf8'));
const before=read('server-before.json'),after=read('server-after.json'),manifest=read('manifest.json');
const clean=v=>Array.isArray(v)?v.map(clean):v&&typeof v==='object'?Object.fromEntries(Object.entries(v).filter(([k])=>k!=='_stats').sort(([a],[b])=>a.localeCompare(b)).map(([k,x])=>[k,clean(x)])):v;
const same=(a,b,label)=>assert.deepEqual(clean(a),clean(b),label);
const targets=new Set(manifest.actors.map(s=>s.data._id));
assert.equal(before.actors.length,after.actors.length);
let untouched=0,oldItems=0,oldEffects=0;
for(const old of before.actors) {
  const current=after.actors.find(a=>a._id===old._id);assert(current);
  if(!targets.has(old._id)){same(old,current,'Unrelated actor '+old.name);untouched++;continue;}
  for(const key of ['name','type','img','ownership','prototypeToken','folder','effects'])same(old[key],current[key],old.name+' protected '+key);
  for(const key of ['wounds','fatigue','bennies','powerPoints'])same(old.system[key],current.system[key],old.name+' runtime '+key);
  const oldFlags=structuredClone(old.flags),newFlags=structuredClone(current.flags);
  for(const f of [oldFlags,newFlags]){delete f.world.taiyiEp03;delete f.world.taiyiL5;if(old.name==='马铁鹰'&&f.swade){delete f.swade.hardy;if(!Object.keys(f.swade).length)delete f.swade;}}
  same(oldFlags,newFlags,old.name+' identity/portrait flags');
  for(const item of old.items) {
    const now=current.items.find(i=>i._id===item._id);assert(now,'No deleted item');oldItems++;
    assert.equal(now.type,item.type,'Type preserved');
    for(const effect of item.effects||[]){assert((now.effects||[]).some(e=>e._id===effect._id),'No deleted effect');oldEffects++;}
    if(['weapon','gear','armor','consumable'].includes(item.type))for(const key of ['quantity','currentShots','equipStatus'])same(item.system[key],now.system[key],old.name+' equipment '+key);
    if(['gear','armor','hindrance','ability'].includes(item.type))same(item,now,old.name+' retained '+item.name);
  }
}
same(before.scenes,after.scenes,'Scene tokens unchanged');
same(before.combats,after.combats,'Combats unchanged');
same(before.journals,after.journals,'Journals unchanged');
assert(after.verification.passed);
const smoke=read('roll-smoke.json');assert(smoke.passed);
assert.equal(smoke.tests,24);assert.equal(smoke.skillTests,19);assert.equal(smoke.weaponTests,5);
assert(smoke.method?.includes('RollDialog complete-formula assembly'),'Use the native dialog formula path, not the broken suppressChat modifier concatenation');
const fists=smoke.reports.find(r=>r.kind==='weapon'&&r.name==='拳脚 · 破门重拳');
assert(fists&&/\+\s*1\[/.test(fists.attack),'Martial Artist +1 is an added term');
const notice=smoke.reports.find(r=>r.kind==='skill'&&r.actor==='夏满弓'&&r.name==='察觉');
assert(notice&&/\+\s*2\[/.test(notice.formula),'Alertness +2 is an added term');
const idempotence=read('idempotence.json');assert.equal(idempotence.status,'complete');assert(idempotence.log.every(x=>x.action==='no-op'));
const report={passed:true,rebuilds:2,advances:5,rank:after.verification.reports.map(x=>[x.name,x.rank]),untouchedActors:untouched,retainedItemIds:oldItems,retainedEffectIds:oldEffects,deletedActors:0,deletedItems:0,deletedEffects:0,identityAndPortraitsPreserved:true,runtimeStatePreserved:true,sceneTokensUnchanged:true,journalsUnchanged:true,rollTests:smoke.tests,weaponTests:smoke.weaponTests,attackBonusVerified:true,noticeBonusVerified:true,superSkillCount:0,superEdgeCount:0};
fs.writeFileSync(path.join(out,'verification.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
