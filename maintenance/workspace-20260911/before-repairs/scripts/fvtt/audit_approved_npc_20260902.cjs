const fs=require('fs'),path=require('path');const dir=path.resolve(__dirname,'../../discussion/npc/fvtt/approved-20260902');
const read=f=>JSON.parse(fs.readFileSync(path.join(dir,f),'utf8'));
const before=read('server-before.json'),after=read('server-after.json'),spec=read('runtime-spec.json');
const customPortraits=read('custom-portrait-spec.json');
const equal=require('node:util').isDeepStrictEqual;
function diff(a,b,p=''){if(equal(a,b))return [];if(a&&b&&typeof a==='object'&&typeof b==='object')return [...new Set([...Object.keys(a),...Object.keys(b)])].flatMap(k=>diff(a[k],b[k],p?`${p}.${k}`:k));return [{path:p,before:a,after:b}];}
const failures=[],changes=[],relations=[];
if(before.actors.length!==after.actors.length)failures.push('Actor count changed');
for(const old of before.actors){
 const a=structuredClone(old),b=structuredClone(after.actors.find(x=>x._id===old._id));if(!b){failures.push('Missing actor '+old._id);continue;}
 delete a._stats;delete b._stats;
 const custom=customPortraits.find(s=>s.actorId===old._id);
 if(custom){a.flags??={};a.flags['ginzzzu-portraits']??={};a.flags['ginzzzu-portraits'].portraitCustomImage=custom.portraitCustomImage;}
 if(old._id===spec.zhai.actorId){a.img=spec.zhai.actorImage;a.prototypeToken.texture.src=spec.zhai.tokenImage;Object.assign(a.flags.world.taiyiNpc,{approvedRun:spec.zhai.approvedRun,sourceSha256:spec.zhai.approvedSha256});if(a.prototypeToken.ring?.enabled){a.prototypeToken.ring.subject.texture=spec.zhai.tokenImage;a.prototypeToken.ring.subject.scale=1;}}
 const arr=a.flags?.['stylish-relationship-tracker']?.relationshipData?.relationships||[];
 for(const r of arr){
   let patch;
   if(r.targetUuid===spec.zhai.actorUuid)patch={portrait:spec.zhai.fullPortrait,listImage:spec.zhai.actorImage,mapThumbnail:spec.zhai.actorImage};
   if(r.targetUuid===spec.sh.actorUuid)patch={portrait:spec.sh.relationshipPortrait,listImage:spec.sh.relationshipListImage,mapThumbnail:spec.sh.relationshipMapThumbnail};
   if(patch){Object.assign(r,patch);relations.push({ownerId:a._id,owner:a.name,relationshipId:r.id,target:r.targetUuid,...patch});}
 }
 const unexpected=diff(a,b);if(unexpected.length)failures.push({actor:old.name,unexpected});
 const originalDiff=diff(old,after.actors.find(x=>x._id===old._id)).filter(x=>!x.path.startsWith('_stats.'));if(originalDiff.length)changes.push({actor:old.name,fields:originalDiff.map(d=>d.path)});
}
for(const key of ['journals','folders','scenes'])if(!equal(before[key],after[key]))failures.push({unexpectedCollection:key});
const customVerified=customPortraits.filter(s=>after.actors.find(a=>a._id===s.actorId)?.flags?.['ginzzzu-portraits']?.portraitCustomImage===s.portraitCustomImage).length;
if(customVerified!==customPortraits.length)failures.push('Custom portrait mapping mismatch');
const whiteBefore=before.actors.find(a=>a._id==='vqcEA8al2OfxGc0p'),whiteAfter=after.actors.find(a=>a._id===whiteBefore._id);
const whiteRelations=s=>s.actors.flatMap(a=>(a.flags?.['stylish-relationship-tracker']?.relationshipData?.relationships||[]).filter(r=>r.targetUuid==='Actor.'+whiteBefore._id).map(r=>({owner:a._id,relationship:r})));
const ranks=s=>s.actors.map(a=>({id:a._id,relations:(a.flags?.['stylish-relationship-tracker']?.relationshipData?.relationships||[]).map(r=>({id:r.id,rank:r.rank}))}));
const report={verifiedAt:new Date().toISOString(),actorCount:after.actors.length,customPortraitsVerified:customVerified,requestedPortraitMappingPassed:customVerified===93,changes,relations,whiteAvatarTokenAndRelationsPreserved:equal(whiteBefore.img,whiteAfter.img)&&equal(whiteBefore.prototypeToken,whiteAfter.prototypeToken)&&equal(whiteRelations(before),whiteRelations(after)),partyRanksPreserved:equal(ranks(before),ranks(after)),sceneTokensPreserved:equal(before.scenes,after.scenes),failures};
fs.writeFileSync(path.join(dir,'verification.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));if(failures.length)process.exitCode=1;
