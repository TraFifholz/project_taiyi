const fs=require('fs'),path=require('path'),crypto=require('crypto');
const root=path.resolve(__dirname,'../..'),prod=path.join(root,'discussion/npc/立绘生产');
const out=path.join(root,'discussion/npc/fvtt/approved-20260902');fs.mkdirSync(out,{recursive:true});
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));const write=(p,x)=>fs.writeFileSync(p,JSON.stringify(x,null,2)+'\n');
const now=new Date().toISOString(),runId='20260902-ls-npc-006-pink-v4';
for(const rel of ['control/portrait-master.json','control/review-decisions.json','control/utility-silhouettes-20260902.json']){const dest=path.join(out,path.basename(rel)+'.before');if(!fs.existsSync(dest))fs.copyFileSync(path.join(prod,rel),dest);}
const master=read(path.join(prod,'control/portrait-master.json')),c=master.characters.find(c=>c.id==='LS-NPC-006');
if(c.approvedRun!==runId){c.supersededApprovals??=[];if(!c.supersededApprovals.some(s=>s.approvedRun===c.approvedRun))c.supersededApprovals.push({approvedRun:c.approvedRun,approvedAsset:c.approvedAsset,approvedSha256:c.approvedSha256,approvedAt:c.approvedAt,reason:'2026-09-02 用户通过粉发、巨乳 NAI 修订'});}
c.pendingRevision={...c.pendingRevision,status:'approved',approvedAt:now};write(path.join(prod,'control/portrait-master.json'),master);
const review=read(path.join(prod,'control/review-decisions.json'));review.updatedAt=now;review.decisions['LS-NPC-006']={decision:'pass',runId,updatedAt:now,note:'用户在候选与剪影预览后回复“通过”，正式采用。'};write(path.join(prod,'control/review-decisions.json'),review);
const run=path.join(prod,'runs',runId,'manifest.json'),m=read(run);m.approval={status:'approved',approvedAt:now,userText:'通过'};write(run,m);
const utilityPath=path.join(prod,'control/utility-silhouettes-20260902.json'),utility=read(utilityPath);
for(const a of utility.assets){a.approval={status:'approved',approvedAt:now,userText:'通过'};const mp=path.join(prod,'runs',a.runId,'manifest.json'),rm=read(mp);rm.approval=a.approval;write(mp,rm);}
write(utilityPath,utility);
write(path.join(out,'approval.json'),{approvedAt:now,userText:'通过',characterId:c.id,runId,utilityAssets:utility.assets.map(a=>a.asset),scope:'翟明珠正式入库与 FVTT 图片更新；三张剪影通过；S.H. Relationship 使用 Glitch 版；通用男女剪影保留为缺图素材'});
console.log('Recorded explicit user approval for Zhai Mingzhu and three silhouettes');
