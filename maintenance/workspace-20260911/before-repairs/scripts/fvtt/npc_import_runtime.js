async function taiyiNpcImport(action, manifest = null, options = {}) {
  const scope = "world";
  const key = "taiyiNpc";
  const relScope = "stylish-relationship-tracker";
  if (!game.ready || game.world.id !== "taiyi" || game.system.id !== "swade") throw new Error("Expected ready taiyi / swade world");
  if (!game.user.isGM) throw new Error("A GM session is required");
  const clone = value => foundry.utils.deepClone(value);
  const source = actor => actor.toObject(true);
  const equal = (a, b) => JSON.stringify(a) === JSON.stringify(b);
  const tag = actor => actor.getFlag(scope, key);
  const normalizeName = name => String(name || "").normalize("NFKC").replace(/\s+/g, "").toLowerCase();

  if (action === "snapshot") return {
    capturedAt: new Date().toISOString(), worldId: game.world.id, system: {id: game.system.id, version: game.system.version},
    coreVersion: game.version, user: {id: game.user.id, name: game.user.name, isGM: game.user.isGM},
    modules: [...game.modules.values()].filter(m => [relScope, "glitchsmith-lib", "swade-StylishActionHud-integration", "swade-supers-companion"].includes(m.id)).map(m => ({id:m.id,version:m.version,active:m.active})),
    actors: game.actors.map(source),
    folders: game.folders.filter(f => ["Actor", "JournalEntry"].includes(f.type)).map(f => f.toObject(true)),
    journals: game.journal.map(j => j.toObject(true)),
    scenes: game.scenes.map(s => ({id:s.id,name:s.name,active:s.active,tokens:s.tokens.map(t=>t.toObject(true))})),
    users: game.users.map(u => ({id:u.id,name:u.name,role:u.role,active:u.active,character:u.character?.id || null})),
    actorTypes: Object.keys(CONFIG.Actor.dataModels || {}),
  };

  if (!manifest || manifest.worldId !== game.world.id || manifest.systemId !== game.system.id) throw new Error("Manifest world/system mismatch");
  // Evidence summaries are GM material. Only separately reviewed prose may enter player-facing bios.
  for (const rel of manifest.relationships.filter(r => r.delivery === "tracker")) {
    if (typeof rel.playerBio !== "string" || /关系数值|未评定|不额外推定|不附加|不据此|不宣称|尚未向玩家|(?:^|\s)S\d+\b|records\/|discussion\//.test(rel.playerBio)) throw new Error(`Missing or internal player biography: ${rel.id}`);
  }
  const selected = new Set(options.ids || manifest.actors.map(a=>a.id));
  const mappings = new Map();
  const conflicts = [];
  for (const spec of [...manifest.actors, ...manifest.players]) {
    const aliases = new Set(spec.aliases.map(normalizeName));
    let matches = game.actors.filter(a => tag(a)?.id === spec.id);
    if (!matches.length && spec.actorId) {
      const actor = game.actors.get(spec.actorId);
      if (actor) matches = [actor];
    }
    if (!matches.length) matches = game.actors.filter(a => aliases.has(normalizeName(a.name)));
    if (matches.length > 1) conflicts.push({id:spec.id,matches:matches.map(a=>({id:a.id,name:a.name,type:a.type}))});
    else if (matches.length === 1) mappings.set(spec.id, matches[0]);
  }
  const relevantConflicts = conflicts.filter(c => selected.has(c.id) || manifest.players.some(p=>p.id===c.id));
  if (relevantConflicts.length && action !== "preview") throw new Error(`Unresolved matches: ${JSON.stringify(relevantConflicts)}`);
  const missingPlayers = manifest.players.filter(p=>!mappings.has(p.id)).map(p=>({id:p.id,name:p.name}));

  function actorChanges(actor, spec) {
    const patch = {};
    if (actor.img !== spec.actorImage) patch.img = spec.actorImage;
    const customPortrait = spec.portraitCustomImage || spec.fullPortrait;
    if (customPortrait && actor.getFlag("ginzzzu-portraits", "portraitCustomImage") !== customPortrait) patch["flags.ginzzzu-portraits.portraitCustomImage"] = customPortrait;
    if (actor.prototypeToken.texture.src !== spec.tokenImage) patch["prototypeToken.texture.src"] = spec.tokenImage;
    if (actor.prototypeToken.ring?.enabled && spec.tokenImage.startsWith("worlds/taiyi/assets/npc/avatars/")) {
      if(actor.prototypeToken.ring.subject.texture!==spec.tokenImage)patch["prototypeToken.ring.subject.texture"]=spec.tokenImage;
      if(actor.prototypeToken.ring.subject.scale!==1)patch["prototypeToken.ring.subject.scale"]=1;
      if(actor.prototypeToken.texture.scaleX!==1)patch["prototypeToken.texture.scaleX"]=1;
      if(actor.prototypeToken.texture.scaleY!==1)patch["prototypeToken.texture.scaleY"]=1;
    }
    const expectedTag = {id:spec.id,sourceSha256:spec.approvedSha256,approvedRun:spec.approvedRun,placeholder:tag(actor)?.placeholder ?? false};
    if (!equal(tag(actor), expectedTag)) patch[`flags.${scope}.${key}`] = expectedTag;
    return patch;
  }
  const preview = manifest.actors.filter(a=>selected.has(a.id)).map(spec=>{
    const actor=mappings.get(spec.id);
    return {id:spec.id,name:spec.displayName,actorId:actor?.id||null,action:conflicts.some(c=>c.id===spec.id)?"conflict":actor?(Object.keys(actorChanges(actor,spec)).length?"update":"unchanged"):"create",fields:actor?Object.keys(actorChanges(actor,spec)):[]};
  });
  if (action === "preview") return {worldId:game.world.id,conflicts,missingPlayers,actors:preview,matches:[...mappings].map(([id,a])=>({id,actorId:a.id,name:a.name,type:a.type})),supplemental:manifest.supplemental.map(s=>({name:s.name,decision:s.decision,matches:game.actors.filter(a=>normalizeName(a.name).includes(normalizeName(s.name))).map(a=>({id:a.id,name:a.name,img:a.img,type:a.type,hasShop:!!a.flags["stylish-shop"]}))}))};

  if (action === "journal") {
    if (!options.write || options.expectedWorld !== "taiyi") throw new Error("Explicit write and expectedWorld required");
    const escape = value => String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
    const nameFor = id => manifest.actors.find(a=>a.id===id)?.canonicalName || manifest.players.find(p=>p.id===id)?.name || id;
    const linkFor = id => mappings.has(id) ? `@UUID[${mappings.get(id).uuid}]{${escape(nameFor(id))}}` : escape(nameFor(id));
    const journalTag = "taiyi-npc-import-gm-archive";
    let journal = game.journal.find(j=>j.getFlag("world","taiyiNpcArchive")===journalTag);
    const created = !journal;
    if (!journal) journal=await JournalEntry.create({name:"龙散 NPC｜身份与关系来源（GM）",ownership:{default:0},flags:{world:{taiyiNpcArchive:journalTag}}});
    if (Object.entries(journal.ownership).some(([userId,level])=>level>0&&(userId==="default"||!game.users.get(userId)?.isGM))) throw new Error("GM archive has non-GM ownership; refusing to write secrets");
    let pageCreated=0,pageUpdated=0,pageUnchanged=0;
    for (const spec of manifest.actors.filter(a=>selected.has(a.id))) {
      const rels=manifest.relationships.filter(r=>r.sourceId===spec.id||r.targetId===spec.id);
      const content=`<p><strong>GM 专用资料。人物立绘已采用；涉及未公开身份及关系，不对玩家分享本页。</strong></p><p>${linkFor(spec.id)}</p><p>稳定编号：${escape(spec.id)}；状态：${escape(spec.narrativeStatus)}</p><p>身份／归档用途：${escape(spec.privateRole)}</p><p>人物源状态：${escape(spec.sourceStatus)}。图像采用不表示全部候选剧情已确认。</p><h2>已有关系</h2><ul>${rels.map(r=>`<li>${linkFor(r.sourceId)} — ${linkFor(r.targetId)}：${escape(r.bio)}<br>证据类别：${escape(r.evidenceStatus)}；去向：${escape(r.delivery)}；来源：${escape(r.source.file)}:${r.source.line}</li>`).join("")||"<li>尚未录入独立人物关系；不按同组织自动互连。</li>"}</ul><p>23 条关系提案留在本地待审，不在此转为正式关系。</p>`;
      const page=journal.pages.find(p=>p.flags.world?.taiyiNpcId===spec.id);
      if(!page){await journal.createEmbeddedDocuments("JournalEntryPage",[{name:`${spec.id} ${spec.canonicalName}`,type:"text",ownership:{default:-1},text:{content,format:1},flags:{world:{taiyiNpcId:spec.id}}}]);pageCreated++;}
      else if(page.text.content!==content){await page.update({"text.content":content});pageUpdated++;}
      else pageUnchanged++;
    }
    return {worldId:game.world.id,journalId:journal.id,created,pageCreated,pageUpdated,pageUnchanged,ownership:clone(journal.ownership)};
  }

  if (action === "apply") {
    if (!options.write || options.expectedWorld !== "taiyi") throw new Error("Explicit write and expectedWorld required");
    if (missingPlayers.length) throw new Error(`Missing PC mapping: ${JSON.stringify(missingPlayers)}`);
    if (!game.modules.get(relScope)?.active) throw new Error("Relationship module is not active; use reviewed Journal fallback instead");
    const before = new Map(game.actors.map(a=>[a.id,source(a)]));
    const changes = [];
    const ensureFolder = async(name,parent=null)=>{
      let folder=game.folders.find(f=>f.type==="Actor"&&f.name===name&&(f.folder?.id||null)===parent);
      if (!folder) folder=await Folder.create({name,type:"Actor",folder:parent,sorting:"a"});
      return folder;
    };
    const root = await ensureFolder("龙散 NPC");
    const folders={};
    for(const spec of manifest.actors.filter(a=>selected.has(a.id))) {
      let actor=mappings.get(spec.id);
      if (actor) {
        if (actor.type !== "npc") throw new Error(`Refusing to change non-NPC match: ${spec.id}/${actor.name}/${actor.type}`);
        const patch=actorChanges(actor,spec);
        if(Object.keys(patch).length){ await actor.update(patch,{render:false}); changes.push({id:spec.id,actorId:actor.id,action:"updated",fields:Object.keys(patch)}); }
        else changes.push({id:spec.id,actorId:actor.id,action:"unchanged"});
      } else {
        const category=spec.folder.split(" / ")[1];
        if(!folders[category])folders[category]=await ensureFolder(category,root.id);
        actor=await Actor.create({name:spec.displayName,type:"npc",img:spec.actorImage,folder:folders[category].id,ownership:{default:0},system:{details:{biography:{value:spec.publicBiography}}},prototypeToken:{name:spec.displayName,actorLink:true,width:1,height:1,texture:{src:spec.tokenImage},disposition:0,displayName:0,displayBars:0,sight:{enabled:false}},flags:{"ginzzzu-portraits":{portraitCustomImage:spec.portraitCustomImage||spec.fullPortrait},world:{taiyiNpc:{id:spec.id,sourceSha256:spec.approvedSha256,approvedRun:spec.approvedRun,placeholder:true}}}},{renderSheet:false});
        mappings.set(spec.id,actor);
        changes.push({id:spec.id,actorId:actor.id,action:"created"});
      }
    }
    const relApi=await import("/modules/stylish-relationship-tracker/scripts/core/relationships.js");
    const relationChanges=[];
    for(const rel of manifest.relationships.filter(r=>r.delivery==="tracker")) {
      const ends=[[rel.sourceId,rel.targetId,rel.targetRole],[rel.targetId,rel.sourceId,rel.sourceRole]];
      if(!selected.has(rel.sourceId)&&!selected.has(rel.targetId))continue;
      for(const [ownerId,targetId,role] of ends) {
        const owner=mappings.get(ownerId),target=mappings.get(targetId);
        if(!owner||!target){relationChanges.push({id:rel.id,ownerId,targetId,action:"deferred-missing-actor"});continue;}
        const relKey=`${rel.id}:${ownerId}`;
        const storage=await relApi.getRelationshipStorageData(owner);
        let existing=storage.relationships.find(r=>r.taiyiImport?.key===relKey);
        if(!existing) {
          const sameTarget=storage.relationships.filter(r=>r.entryType==="actor"&&r.targetUuid===target.uuid);
          if(sameTarget.length){relationChanges.push({id:rel.id,ownerId,targetId,actorId:owner.id,relationshipIds:sameTarget.map(r=>r.id),action:"reused-existing-preserved"});continue;}
        }
        const targetSpec=manifest.actors.find(a=>a.id===targetId);
        const patch={entryType:"actor",targetUuid:target.uuid,customName:targetSpec?.displayName||target.name,customRole:role,portrait:targetSpec?.relationshipPortrait||targetSpec?.fullPortrait||target.img,listImage:targetSpec?.relationshipListImage||target.img,mapThumbnail:targetSpec?.relationshipMapThumbnail||target.img,portraitPresentation:targetSpec?"cutout":"framed",portraitScale:targetSpec?0.75:1,portraitOffset:{x:0,y:0},bio:rel.playerBio,visibility:"players",playerEditable:false,taiyiImport:{key:relKey}};
        if(existing) {
          if(Object.entries(patch).some(([k,v])=>!equal(existing[k],v))) {await relApi.updateRelationship(owner,existing.id,patch);relationChanges.push({id:rel.id,ownerId,targetId,relationshipId:existing.id,action:"updated"});}
          else relationChanges.push({id:rel.id,ownerId,targetId,relationshipId:existing.id,action:"unchanged"});
        } else {
          const created=await relApi.createRelationship(owner,{...patch,rank:0,rankProgress:0,rankMacroTriggers:[],events:[],stats:[],giftProfileMode:"disabled",locked:false,unlockOnGift:false});
          relationChanges.push({id:rel.id,ownerId,targetId,actorId:owner.id,relationshipId:created.id,action:"created"});
        }
      }
    }
    const protectedFailures=[];
    for(const [id,old] of before) {
      const current=source(game.actors.get(id));
      for(const field of ["system","items","effects","ownership"]){if(!equal(old[field],current[field]))protectedFailures.push({id,name:old.name,field});}
      if(!equal(old.flags?.["stylish-shop"],current.flags?.["stylish-shop"]))protectedFailures.push({id,name:old.name,field:"stylish-shop"});
      const oldRels=old.flags?.[relScope]?.relationshipData?.relationships||[];
      const nowRels=current.flags?.[relScope]?.relationshipData?.relationships||[];
      for(const r of oldRels.filter(r=>!r.taiyiImport))if(!equal(r,nowRels.find(n=>n.id===r.id)))protectedFailures.push({id,name:old.name,field:`relationship:${r.id}`});
    }
    return {worldId:game.world.id,changes,relationChanges,protectedFailures,matches:[...mappings].map(([id,a])=>({id,actorId:a.id,name:a.name}))};
  }

  if (action === "verify") {
    const records=manifest.actors.map(spec=>{
      const actor=mappings.get(spec.id);
      if(!actor)return{id:spec.id,error:"missing"};
      const own=actor.flags[relScope]?.relationshipData?.relationships||[];
      return{id:spec.id,actorId:actor.id,name:actor.name,img:actor.img,token:actor.prototypeToken.texture.src,imageMatch:actor.img===spec.actorImage&&actor.prototypeToken.texture.src===spec.tokenImage,ringImageMatch:!actor.prototypeToken.ring?.enabled||!spec.tokenImage.startsWith("worlds/taiyi/assets/npc/avatars/")||actor.prototypeToken.ring.subject.texture===spec.tokenImage,placeholder:tag(actor)?.placeholder,itemCount:actor.items.size,relationCount:own.length,importedRelationKeys:own.filter(r=>r.taiyiImport).map(r=>r.taiyiImport.key),brokenTargets:own.filter(r=>r.entryType==="actor"&&r.targetUuid?.startsWith("Actor.")&&!game.actors.has(r.targetUuid.split(".")[1])).map(r=>r.id)};
    });
    return{worldId:game.world.id,records,conflicts,missingPlayers};
  }
  throw new Error(`Unsupported action: ${action}`);
}
