const fs=require('node:fs'),path=require('node:path');
const base=path.resolve(__dirname,'../../discussion/npc/fvtt');
const out=path.join(base,'relationship-copy-cleanup-20260903');
fs.mkdirSync(out,{recursive:true});
const bios=JSON.parse(fs.readFileSync(path.join(base,'relationship-player-bios.json'),'utf8'));
for(const name of ['npc-import-manifest.json','supplemental-import-manifest.json']){
  const file=path.join(base,name),original=fs.readFileSync(file,'utf8');
  const backup=path.join(out,name+'.before');if(!fs.existsSync(backup))fs.writeFileSync(backup,original);
  const manifest=JSON.parse(original);
  for(const r of manifest.relationships.filter(r=>r.delivery==='tracker')){
    if(typeof bios[r.id]!=='string')throw Error('Unreviewed relationship '+r.id);
    r.playerBio=bios[r.id];
  }
  fs.writeFileSync(file,JSON.stringify(manifest,null,2)+'\n');
}
console.log('Reviewed player prose separated from evidence for 30 relationship pairs.');
