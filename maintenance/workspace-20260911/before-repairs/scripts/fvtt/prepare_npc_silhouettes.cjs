const fs=require('fs'),path=require('path');
const prod=path.resolve(__dirname,'../../discussion/npc/立绘生产');
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const write=(p,x)=>fs.writeFileSync(p,JSON.stringify(x,null,2)+'\n');
const base=read(path.join(prod,'runs/20260829-ls-npc-006-refresh-v2/request.json'));
const pool=read(path.join(prod,'control/verified-tags.json')).tags;
const specs=[
 {id:'UTILITY-MALE',name:'通用男性纯黑剪影',slug:'male-silhouette',seed:2026090201,tags:['1boy','solo','silhouette','faceless','short_hair','jacket','pants','standing','monochrome','transparent_background'],detail:'An anonymous adult man standing upright in an ordinary jacket and trousers, a single completely solid opaque black silhouette with a clear masculine head and shoulder outline, featureless filled black interior, clean continuous contour, neutral arms resting at his sides, isolated transparent character cutout under flat neutral studio lighting.'},
 {id:'UTILITY-FEMALE',name:'通用女性纯黑剪影',slug:'female-silhouette',seed:2026090202,tags:['1girl','solo','silhouette','faceless','ponytail','jacket','pants','standing','monochrome','transparent_background'],detail:'An anonymous adult woman standing upright in an ordinary fitted jacket and trousers, a single completely solid opaque black silhouette with a clear feminine contour and a simple ponytail, featureless filled black interior, clean continuous contour, neutral arms resting at her sides, isolated transparent character cutout under flat neutral studio lighting.'},
 {id:'LS-NPC-072-ANONYMOUS',name:'S.H. 男性 Glitch 剪影',slug:'sh-glitch-silhouette',seed:2026090203,tags:['1boy','solo','silhouette','faceless','short_hair','jacket','pants','standing','glitch','cyberpunk','transparent_background'],detail:'The anonymous online contact S.H., an adult male represented by a featureless opaque black standing silhouette in a plain jacket, with restrained cyan and magenta RGB split edges and several clearly displaced horizontal glitch slices cutting through the head and upper torso, isolated transparent cutout under flat neutral lighting, a digital anonymity image with a readable male contour.'}
];
for(const s of specs){
 const missing=s.tags.filter(t=>!pool[t]);if(missing.length)throw Error('Missing tags '+missing);
 s.runId=`20260902-utility-${s.slug}-v1`;const dir=path.join(prod,'runs',s.runId);fs.mkdirSync(dir,{recursive:true});
 const req=structuredClone(base);Object.assign(req.meta,{runId:s.runId,characterId:s.id,characterName:s.name,promptVersion:1,designStatus:'utility-anonymous-portrait',designAssumptions:[],humanInitiatedAt:new Date().toISOString(),humanRequest:'其他 NPC 男、女纯黑剪影各一张；S.H. 男剪影加 Glitch；使用 NAI。',promptFile:`runs/${s.runId}/request.json`});delete req.meta.supersedesRun;
 req.payload.parameters.seed=s.seed;
 req.payload.parameters.v4_prompt.caption.char_captions[0].char_caption=s.tags.map(t=>t==='silhouette'?'3::silhouette::':t.replaceAll('_',' ')).join(', ')+'. '+s.detail;
 write(path.join(dir,'request.json'),req);
 write(path.join(dir,'manifest.json'),{schemaVersion:1,runId:s.runId,characterId:s.id,characterName:s.name,designStatus:'utility-anonymous-portrait',status:'prepared',requestFile:'request.json',rawAssets:[],qa:{technical:'pending',visual:'pending',notes:[]},scope:s.id.startsWith('UTILITY')?'Reusable anonymous NPC placeholder':'Anonymous presentation of S.H.; no physical identity or supernatural ability claim'});
}
write(path.join(prod,'control/utility-silhouettes-20260902.json'),{schemaVersion:1,requestedAt:'2026-09-02',provider:'NovelAI',assets:specs.map(({tags,detail,...s})=>s)});
console.log(JSON.stringify(specs.map(s=>({runId:s.runId,tags:s.tags.length,seed:s.seed}))));
