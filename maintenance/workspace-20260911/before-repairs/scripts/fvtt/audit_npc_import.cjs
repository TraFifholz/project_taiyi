const fs=require('node:fs'),util=require('node:util');
const base='discussion/npc/fvtt/';
const before=JSON.parse(fs.readFileSync(base+'server-before-2026-09-02T13-34-20-607Z.json','utf8'));
const after=JSON.parse(fs.readFileSync(process.argv[2]||base+'server-after.json','utf8'));
const main=JSON.parse(fs.readFileSync(base+'npc-import-manifest.json','utf8'));
const extra=JSON.parse(fs.readFileSync(base+'supplemental-import-manifest.json','utf8'));
const failures=[],checks={}; const relScope='stylish-relationship-tracker';
const same=(a,b)=>util.isDeepStrictEqual(a,b);
function assert(ok,kind,details){checks[kind]=(checks[kind]||0)+1;if(!ok)failures.push({kind,...details});}
const oldIds=new Set(before.actors.map(a=>a._id));
const tag=a=>a.flags?.world?.taiyiNpc;
const rels=a=>a?.flags?.[relScope]?.relationshipData?.relationships||[];
for(const old of before.actors){
 const now=after.actors.find(a=>a._id===old._id);assert(!!now,'existing-actor-present',{id:old._id});if(!now)continue;
 for(const k of ['system','items','effects','ownership','name','folder'])assert(same(old[k],now[k]),'protected-actor-field',{id:old._id,name:old.name,field:k});
 for(const [k,v] of Object.entries(old.flags||{}))if(k!==relScope&&k!=='world')assert(same(v,now.flags?.[k]),'protected-actor-flag',{id:old._id,field:k});
 const oldWorld={...old.flags?.world},nowWorld={...now.flags?.world};delete oldWorld.taiyiNpc;delete nowWorld.taiyiNpc;
 assert(same(oldWorld,nowWorld),'protected-other-world-flags',{id:old._id});
 if(old.flags?.[relScope]?.relationshipData)assert(same(old.flags[relScope].relationshipData.profile,now.flags?.[relScope]?.relationshipData?.profile),'protected-relationship-profile',{id:old._id});
 const oldToken=structuredClone(old.prototypeToken),nowToken=structuredClone(now.prototypeToken);
 if(['LS-NPC-088','LS-NPC-090'].includes(tag(now)?.id)){
  for(const k of ['src','scaleX','scaleY'])nowToken.texture[k]=oldToken.texture[k];
  for(const k of ['texture','scale'])nowToken.ring.subject[k]=oldToken.ring.subject[k];
 }
 assert(same(oldToken,nowToken),'protected-prototype-token',{id:old._id,name:old.name});
 for(const r of rels(old))assert(same(r,rels(now).find(x=>x.id===r.id)),'protected-existing-relationship',{actorId:old._id,relationshipId:r.id});
}
assert(same(before.scenes,after.scenes),'existing-scenes-and-tokens',{});
for(const old of before.journals){const now=after.journals.find(j=>j._id===old._id);assert(!!now,'existing-journal-present',{id:old._id});if(now)for(const field of ['name','folder','ownership','pages','flags'])assert(same(old[field],now[field]),'protected-existing-journal',{id:old._id,field});}
for(const old of before.folders){const now=after.folders.find(f=>f._id===old._id);assert(!!now,'existing-folder-present',{id:old._id});if(now)for(const field of ['name','type','folder','sorting','sort','color','flags'])assert(same(old[field],now[field]),'protected-existing-folder',{id:old._id,field});}
const mapping=new Map();
for(const spec of [...main.actors,...extra.actors]){
 const matches=after.actors.filter(a=>tag(a)?.id===spec.id);assert(matches.length===1,'unique-stable-identity',{id:spec.id,count:matches.length});if(matches.length!==1)continue;
 const a=matches[0];mapping.set(spec.id,a);
 assert(a.type==='npc'&&a.img===spec.actorImage&&a.prototypeToken.texture.src===spec.tokenImage,'npc-assets',{id:spec.id});
 if(a.prototypeToken.ring?.enabled&&spec.tokenImage.startsWith('worlds/taiyi/assets/npc/avatars/'))assert(a.prototypeToken.ring.subject.texture===spec.tokenImage&&a.prototypeToken.ring.subject.scale===1&&a.prototypeToken.texture.scaleX===1&&a.prototypeToken.texture.scaleY===1,'dynamic-ring-artwork',{id:spec.id});
 if(!oldIds.has(a._id)){
  assert(a.items.length===0&&a.effects.length===0,'empty-new-card',{id:spec.id,items:a.items.length,effects:a.effects.length});
  assert(a.system.details.biography.value.includes('数值待填'),'placeholder-label',{id:spec.id});
  assert(a.ownership.default===0&&Object.entries(a.ownership).every(([id,v])=>id==='default'||v===0||after.users.find(u=>u.id===id)?.role>=3),'new-card-permission',{id:spec.id});
 }
}
for(const p of main.players){const a=after.actors.find(a=>a._id===p.actorId)||after.actors.find(a=>p.aliases.includes(a.name));if(a)mapping.set(p.id,a);else failures.push({kind:'missing-player',id:p.id});}
for(const r of [...main.relationships,...extra.relationships].filter(r=>r.delivery==='tracker')){
 for(const [ownerId,targetId] of [[r.sourceId,r.targetId],[r.targetId,r.sourceId]]){
  const owner=mapping.get(ownerId),target=mapping.get(targetId);const matches=rels(owner).filter(x=>x.entryType==='actor'&&x.targetUuid===`Actor.${target?._id}`);
  assert(!!owner&&!!target&&matches.length===1,'relationship-direction',{id:r.id,ownerId,targetId,count:matches.length});
 }
}
let importedRelationships=0;
for(const a of after.actors){
 const keys=new Set();
 for(const r of rels(a).filter(x=>x.taiyiImport)){
  importedRelationships++;
  assert(!keys.has(r.taiyiImport.key),'unique-imported-relationship',{actorId:a._id,key:r.taiyiImport.key});keys.add(r.taiyiImport.key);
  assert(r.rank===0&&r.rankProgress===0&&!(r.rankMacroTriggers||[]).length&&!(r.events||[]).length&&!(r.stats||[]).length&&r.giftProfileMode==='disabled','unrated-no-reward',{actorId:a._id,id:r.id});
  assert(after.actors.some(t=>`Actor.${t._id}`===r.targetUuid),'valid-relationship-target',{actorId:a._id,id:r.id});
 }
}
const journal=after.journals.find(j=>j.flags?.world?.taiyiNpcArchive==='taiyi-npc-import-gm-archive');
assert(!!journal,'gm-journal-exists',{});
if(journal){
 assert(journal.ownership.default===0&&Object.entries(journal.ownership).every(([id,v])=>id==='default'||v<=0||after.users.find(u=>u.id===id)?.role>=3),'gm-journal-ownership',{});
 for(const spec of [...main.actors,...extra.actors])assert(journal.pages.filter(p=>p.flags?.world?.taiyiNpcId===spec.id).length===1,'gm-source-page',{id:spec.id});
}
const report={checkedAt:new Date().toISOString(),beforeActorCount:before.actors.length,afterActorCount:after.actors.length,newActorCount:after.actors.filter(a=>!oldIds.has(a._id)).length,mainNpcIdentities:main.actors.length,supplementalMatched:extra.actors.length,importedRelationships,originalRelationships:before.actors.reduce((n,a)=>n+rels(a).length,0),gmSourcePages:journal?.pages.length||0,checks,failures};
fs.writeFileSync(base+'final-data-audit.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));if(failures.length)process.exitCode=1;
