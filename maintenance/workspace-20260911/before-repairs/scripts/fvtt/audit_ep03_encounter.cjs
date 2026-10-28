'use strict';
const fs=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');
const OUT=path.resolve(__dirname,'../../records/prep/ep03-fvtt-20260903');
const read=file=>JSON.parse(fs.readFileSync(path.join(OUT,file),'utf8'));
const manifest=read('manifest.json'),before=read('server-before.json'),after=read('server-after.json');
const stable=value=>JSON.stringify(value,(_k,v)=>v&&typeof v==='object'&&!Array.isArray(v)?Object.fromEntries(Object.entries(v).sort(([a],[b])=>a.localeCompare(b))):v);
const stripStats=obj=>{if(Array.isArray(obj))return obj.map(stripStats);if(obj&&typeof obj==='object')return Object.fromEntries(Object.entries(obj).filter(([k])=>k!=='_stats').map(([k,v])=>[k,stripStats(v)]));return obj;};
const failures=[],test=(condition,message)=>{if(!condition)failures.push(message);};
test(after.passed,'runtime readback did not pass');
test(after.actors.length===before.actors.length+15,'expected exactly 15 new Actors');
const targets=new Set(manifest.actors.map(a=>a.data._id));
let untouched=0,protectedExisting=0,items=0,powers=0;
for(const old of before.actors) {
  const current=after.actors.find(a=>a._id===old._id);
  test(!!current,'missing existing Actor '+old.name);if(!current)continue;
  if(!targets.has(old._id)) {
    test(stable(stripStats(old))===stable(stripStats(current)),'unrelated Actor changed '+old.name);untouched++;continue;
  }
  for(const key of ['name','img','prototypeToken','ownership','folder'])test(stable(old[key])===stable(current[key]),'protected '+old.name+'.'+key);
  const flags=structuredClone(current.flags);delete flags.world?.taiyiEp03;
  test(stable(flags)===stable(old.flags),'unrelated flags changed '+old.name);
  protectedExisting++;
}
for(const spec of manifest.actors) {
  const actual=after.actors.find(a=>a._id===spec.data._id);
  if(!actual){test(false,'missing target '+spec.name);continue;}
  items+=actual.items.length;
  const supers=actual.items.filter(i=>i.type==='swade-supers-companion.superPower');powers+=supers.length;
  test(supers.reduce((s,i)=>s+i.system.build.cost,0)===spec.budget,'budget mismatch '+spec.name);
  test(new Set(actual.items.map(i=>i._id)).size===actual.items.length,'duplicate embedded IDs '+spec.name);
  test(actual.flags?.world?.taiyiEp03?.key===spec.key,'missing stable import key '+spec.name);
  for(const weapon of spec.data.items.filter(i=>i.type==='weapon')) {
    const current=actual.items.find(i=>i._id===weapon._id);
    test(current?.system.currentShots===weapon.system.currentShots,'ammo changed during smoke '+spec.name+' '+weapon.name);
  }
  test(actual.system.wounds.value===0,'unexpected injury during smoke '+spec.name);
  if(!spec.existingId)test(actual.ownership.default===0,'new actor visible to players '+spec.name);
  if(actual.type==='npc')test(actual.system.powerPoints.general.max===0&&actual.system.powerPoints.general.value===0,'ordinary PP pool polluted '+spec.name);
}
test(stable(before.scenes)===stable(after.scenes),'scene Tokens changed');
test(stable(before.combats)===stable(after.combats),'combat changed');
test(after.journalData?.ownership?.default===0,'GM reference visibility wrong');
test(after.journalData?.pages?.length===1,'GM reference page missing');
for(const spec of manifest.actors)test(after.journalData.pages[0].text.content.includes('Actor.'+spec.data._id),'journal actor link missing '+spec.name);
const result={verifiedAt:new Date().toISOString(),world:after.world,named:7,extraTemplates:5,vehicleTemplates:7,newActors:15,filledExisting:protectedExisting,untouchedExisting:untouched,items,powers,playerActorsUnchanged:before.actors.filter(a=>a.type==='character').every(a=>stable(stripStats(a))===stable(stripStats(after.actors.find(b=>b._id===a._id)))),sceneTokensUnchanged:stable(before.scenes)===stable(after.scenes),failures,passed:failures.length===0};
fs.writeFileSync(path.join(OUT,'verification.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result,null,2));assert.equal(failures.length,0,failures.join('\n'));
