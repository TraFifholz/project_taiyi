const fs=require('fs'),path=require('path');
const dir=path.resolve(__dirname,'../../discussion/npc/fvtt/refresh-20260902');
const read=f=>JSON.parse(fs.readFileSync(path.join(dir,f),'utf8'));
const before=read('server-before.json'),after=read('server-after.json');
const preview=read('runtime-preview.json').preview;
const pcIds=[...new Set(before.users.filter(u=>u.role<3&&u.character).map(u=>u.character))];
const failures=[];const changed=[];
const equal=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
function diff(a,b,p=''){
 if(equal(a,b))return [];
 if(a&&b&&typeof a==='object'&&typeof b==='object')return [...new Set([...Object.keys(a),...Object.keys(b)])].flatMap(k=>diff(a[k],b[k],p?`${p}.${k}`:k));
 return [{path:p,before:a,after:b}];
}
const directions=[];
if(before.actors.length!==after.actors.length)failures.push('Actor count changed');
for(const old of before.actors){
 const now=after.actors.find(a=>a._id===old._id);if(!now){failures.push('Missing Actor '+old._id);continue;}
 const a=structuredClone(old),b=structuredClone(now);
 delete a._stats;delete b._stats;
 const oldData=a.flags?.['stylish-relationship-tracker']?.relationshipData;
 const newData=b.flags?.['stylish-relationship-tracker']?.relationshipData;
 if(oldData&&newData){
   const olds=oldData.relationships||[],news=newData.relationships||[];
   for(const rel of olds){
     const current=news.find(r=>r.id===rel.id);if(!current){failures.push(`Lost relation ${old.name}/${rel.id}`);continue;}
     const patch=preview.portraits.find(p=>p.ownerId===old._id&&p.relationshipId===rel.id)?.patch||{};
     const diffs=diff(rel,current);
     for(const d of diffs){
       const expectedSyncCounter=d.path==='sync.appliedRevision'&&Object.keys(patch).length>0&&d.after===d.before+1;
       if(!expectedSyncCounter&&!(d.path in patch)&&!Object.keys(patch).some(k=>d.path.startsWith(k+'.')))failures.push({actor:old.name,relationship:rel.id,...d});
     }
     for(const [key,val] of Object.entries(patch))if(!equal(current[key],val))failures.push(`Portrait patch mismatch ${old.name}/${rel.id}/${key}`);
     if(diffs.length)changed.push({actor:old.name,relationship:rel.id,fields:diffs.map(d=>d.path)});
   }
   for(const rel of news.filter(r=>!olds.some(o=>o.id===r.id))){
     const target=rel.targetUuid?.replace(/^Actor\./,'');
     if(!pcIds.includes(old._id)||!pcIds.includes(target)||target===old._id||rel.rank!==1||rel.rankProgress!==0||rel.polarity!=='positive'||rel.events.length||rel.rankMacroTriggers.length)failures.push({unexpectedNewRelation:rel.id,owner:old.name});
     directions.push({owner:old._id,target,rank:rel.rank});
   }
   oldData.relationships=[];newData.relationships=[];
   const cap=preview.capacity.find(p=>p.ownerId===old._id);
   if(cap){if(newData.profile.maxRelationshipSlots!==cap.to)failures.push('Capacity mismatch '+old.name);oldData.profile.maxRelationshipSlots=cap.to;}
 }
 const protectedDiffs=diff(a,b);if(protectedDiffs.length)failures.push({actor:old.name,protectedDiffs});
}
for(const owner of pcIds)for(const target of pcIds.filter(t=>t!==owner)){
 const rels=after.actors.find(a=>a._id===owner).flags['stylish-relationship-tracker'].relationshipData.relationships.filter(r=>r.targetUuid==='Actor.'+target);
 if(rels.length!==1||rels[0].rank!==1)failures.push({badPartyPair:[owner,target],count:rels.length,ranks:rels.map(r=>r.rank)});
}
for(const k of ['scenes','folders'])if(!equal(before[k],after[k]))failures.push({protectedWorldCollection:k});
const syncRegistryChanges=[];
if(before.journals.length!==after.journals.length)failures.push('Journal count changed');
for(const old of before.journals){
 const a=structuredClone(old),b=structuredClone(after.journals.find(j=>j._id===old._id));
 if(!b){failures.push('Missing Journal '+old._id);continue;}
 delete a._stats;delete b._stats;
 const groups=a.flags?.['stylish-relationship-tracker']?.relationshipSyncRegistry?.groups||[];
 for(const group of groups){
   const patch=preview.portraits.find(p=>group.members.some(m=>m.ownerActorUuid==='Actor.'+p.ownerId&&m.relationshipId===p.relationshipId))?.patch;
   if(patch){Object.assign(group.content,patch);group.revision+=1;syncRegistryChanges.push({id:group.id,members:group.members.length,fields:Object.keys(patch),expectedRevision:group.revision});}
 }
 const changes=diff(a,b);if(changes.length)failures.push({journal:old.name,protectedDiffs:changes});
}
const whiteBefore=before.actors.find(a=>a._id==='vqcEA8al2OfxGc0p'),whiteAfter=after.actors.find(a=>a._id==='vqcEA8al2OfxGc0p');
const report={verifiedAt:new Date().toISOString(),actorCount:after.actors.length,players:pcIds.length,partyPairs:15,partyDirections:30,createdDirections:directions.length,relationshipImageChanges:changed,syncRegistryChanges,whiteAvatarUnchanged:equal(whiteBefore.img,whiteAfter.img),whitePrototypeTokenUnchanged:equal(whiteBefore.prototypeToken,whiteAfter.prototypeToken),sceneTokensUnchanged:equal(before.scenes,after.scenes),failures};
fs.writeFileSync(path.join(dir,'verification.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));if(failures.length)process.exitCode=1;
