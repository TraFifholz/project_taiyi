const fs=require('node:fs'),path=require('node:path'),{isDeepStrictEqual:equal}=require('node:util');
const base=path.resolve(__dirname,'../../discussion/npc/fvtt/relationship-copy-cleanup-20260903');
const read=f=>JSON.parse(fs.readFileSync(path.join(base,f),'utf8'));
const before=read('server-before.json'),after=read('server-after.json'),plan=read('plan.json');
function diff(a,b,p=''){if(equal(a,b))return [];if(a&&b&&typeof a==='object'&&typeof b==='object')return [...new Set([...Object.keys(a),...Object.keys(b)])].flatMap(k=>diff(a[k],b[k],p?`${p}.${k}`:k));return [{path:p,before:a,after:b}];}
const failures=[];
if(before.actors.length!==after.actors.length)failures.push('Actor count changed');
for(const old of before.actors){
  const a=structuredClone(old),b=structuredClone(after.actors.find(x=>x._id===old._id));
  if(!b){failures.push('Missing actor '+old._id);continue;}
  delete a._stats;delete b._stats;
  for(const p of plan.filter(p=>p.actorId===a._id)){
    const r=a.flags['stylish-relationship-tracker'].relationshipData.relationships.find(r=>r.id===p.relationshipId);
    r.bio=p.bio;r.taiyiImport={key:p.key};
  }
  const unexpected=diff(a,b);if(unexpected.length)failures.push({actor:old.name,unexpected});
}
for(const k of ['folders','journals','scenes'])if(!equal(before[k],after[k]))failures.push({collection:k,unexpected:diff(before[k],after[k])});
const rels=after.actors.flatMap(a=>(a.flags?.['stylish-relationship-tracker']?.relationshipData?.relationships||[]).map(r=>({actorId:a._id,owner:a.name,...r})));
const forbidden=/关系数值|未评定|不额外推定|不附加|不据此|不宣称|不再标为|其余队友当时|尚未向玩家|\bS\d+\b|records\/|discussion\//;
const residue=rels.filter(r=>forbidden.test(JSON.stringify({bio:r.bio,notes:r.notes,events:r.events,role:r.customRole})));
if(residue.length)failures.push({residue});
const imported=rels.filter(r=>r.taiyiImport);
if(imported.some(r=>Object.keys(r.taiyiImport).some(k=>k!=='key')))failures.push('Source metadata remains');
const report={verifiedAt:new Date().toISOString(),actors:after.actors.length,relations:rels.length,updated:plan.length,imported:imported.length,remainingInternalCopy:residue.length,onlyApprovedFieldsChanged:failures.length===0,failures};
fs.writeFileSync(path.join(base,'verification.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));if(failures.length)process.exitCode=1;
