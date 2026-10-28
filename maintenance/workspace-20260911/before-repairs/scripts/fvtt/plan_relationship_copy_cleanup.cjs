const fs=require('node:fs'),path=require('node:path');
const base=path.resolve(__dirname,'../../discussion/npc/fvtt'),out=path.join(base,'relationship-copy-cleanup-20260903');
const read=f=>JSON.parse(fs.readFileSync(f,'utf8'));
const before=read(path.join(out,'server-before.json'));
const rels=['npc-import-manifest.json','supplemental-import-manifest.json'].flatMap(f=>read(path.join(base,f)).relationships);
const plan=[];
for(const actor of before.actors)for(const r of actor.flags?.['stylish-relationship-tracker']?.relationshipData?.relationships||[]){
  if(!r.taiyiImport)continue;
  const id=r.taiyiImport.key.split(':')[0],source=rels.find(s=>s.id===id&&s.delivery==='tracker');
  if(!source||typeof source.playerBio!=='string')throw Error('Unknown imported relationship: '+r.id);
  if(r.bio!==source.bio+'\n\n关系数值：未评定。')throw Error('Biography edited after import; review separately: '+r.id);
  plan.push({actorId:actor._id,owner:actor.name,relationshipId:r.id,name:r.customName,targetUuid:r.targetUuid,key:r.taiyiImport.key,beforeBio:r.bio,bio:source.playerBio});
}
fs.writeFileSync(path.join(out,'plan.json'),JSON.stringify(plan,null,2)+'\n');
console.log(JSON.stringify({relationships:plan.length,actors:new Set(plan.map(p=>p.actorId)).size,clinic:plan.filter(p=>p.key.includes('522a2edb4b3091ac')||p.key.includes('bcb101f1081ad140')||p.key.includes('00d1fa01d50dac2e')).map(p=>({owner:p.owner,bio:p.bio}))},null,2));
