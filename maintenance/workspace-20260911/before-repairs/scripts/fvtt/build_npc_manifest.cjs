"use strict";
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const ROOT = path.resolve(__dirname, "../..");
const OUT = path.join(ROOT, "discussion/npc/fvtt");
const playerBios = JSON.parse(fs.readFileSync(path.join(OUT, "relationship-player-bios.json"), "utf8"));
const read = file => JSON.parse(fs.readFileSync(path.join(ROOT, file), "utf8"));
const master = read("discussion/npc/立绘生产/control/portrait-master.json");
const retired = read("discussion/npc/立绘生产/control/retired-characters.json");
const presentationOverridesPath = path.join(OUT, "presentation-overrides.json");
const presentationOverrides = fs.existsSync(presentationOverridesPath) ? JSON.parse(fs.readFileSync(presentationOverridesPath, "utf8")) : {};
const npc = n => `LS-NPC-${n}`;
const pc = n => `LS-PC-${n}`;
const sources = {};
function evidence(file, needle) {
  const text = fs.readFileSync(path.join(ROOT, file), "utf8");
  const lines = text.split(/\r?\n/);
  const line = lines.findIndex(s => s.includes(needle));
  if (line < 0) throw new Error(`Missing source anchor: ${file}: ${needle}`);
  sources[file] = crypto.createHash("sha256").update(text).digest("hex");
  return {file, line: line + 1, anchor: needle};
}
const ENT = "records/memory/entities.md";
const STATE = "records/memory/campaign-state.md";
const GANG = "discussion/npc/帮派黑道.md";
const DAILY = "discussion/npc/日常接点.md";
const alias = {
  "006": ["小猪猪"], "025": ["葛兆康", "老葛"], "033": ["赵明之", "赵明哲"],
  "044": ["远哥"], "046": ["何林", "何玲"], "057": ["铁手", "李铁牙", "铁牙"],
  "061": ["荷叶白", "何月白"], "070": ["老井", "井叔"], "072": ["苏晦", "S.H."],
  "088": ["沈曼", "审判", "神庙"], "089": ["沈中秋", "阿秋", "沈奏秋"],
  "090": ["朱瑶光", "阿瑶", "小瑶"], "095": ["Sabrina", "萨布里娜", "savina"],
  "096": ["周林", "周玲", "周玲玲"], "100": ["陈冰"],
  "103": ["朱恒", "朱蘅"], "106": ["Red Queen"], "107": ["男偶像"],
  "N3": ["闻笙", "棍木女", "棍木女（代称）"]
};
const names = {"072": "S.H.", "090": "阿瑶", "103": "朱恒（身份待核）", "107": "男偶像", "N3": "棍木女"};
const played = new Set("001 006 033 037 044 046 057 061 065 072 077 088 089 090 095 096 098 100 101 103 106 107 N3".split(" "));
const actors = master.characters.map(c => {
  const key = c.id.replace("LS-NPC-", "");
  const archival = ["037", "103", "105", "106", "107"].includes(key);
  return {
    id: c.id, canonicalName: c.name, displayName: names[key] || c.name,
    aliases: [...new Set([c.name, names[key], ...(alias[key] || [])].filter(Boolean))],
    priority: c.priority, sourceStatus: c.sourceStatus,
    narrativeStatus: key === "037" ? "已故档案" : key === "103" ? "失踪档案，身份待核" : archival ? "幕后／失踪档案" : played.has(key) ? "实跑已出现或提及" : "GM储备",
    folder: archival ? "龙散 NPC / 档案人物" : "龙散 NPC / 城市人物",
    privateRole: c.organization,
    publicBiography: `<p>数值待填。本卡先用于人物识别、头像、Token 与已有关系记录。</p>${key === "037" ? "<p>已故人物档案。</p>" : key === "103" ? "<p>失踪人物档案；身份尚待核实。</p>" : ""}`,
    approvedAsset: `discussion/npc/立绘生产/${c.approvedAsset}`,
    approvedSha256: c.approvedSha256, approvedRun: c.approvedRun,
    actorImage: `worlds/taiyi/assets/npc/avatars/${c.id}.webp`,
    tokenImage: `worlds/taiyi/assets/npc/avatars/${c.id}.webp`,
    fullPortrait: `worlds/taiyi/assets/npc/portraits/${c.id}.webp`,
    portraitCustomImage: presentationOverrides[c.id]?.portraitCustomImage || presentationOverrides[c.id]?.fullPortrait || `worlds/taiyi/assets/npc/portraits/${c.id}.webp`,
    ...(presentationOverrides[c.id] || {}),
    identityConflict: key === "103" ? "朱恒与朱蘅是否同一人未定；多个服务器匹配项必须人工核对" : null,
    decision: "pending-server-inventory", actorId: null,
    source: evidence("discussion/npc/立绘生产/control/portrait-master.json", `\"id\": \"${c.id}\"`)
  };
});
const players = [
  ["lihao", "李好", ["李好"]], ["yuko", "黑崎欲子", ["黑崎欲子", "黑崎玉子", "玉子"]],
  ["tangsuo", "唐索", ["唐索"]], ["lei", "雷武龙", ["雷武龙"]],
  ["kevlar", "凯芙拉·威尔森", ["凯芙拉·威尔森", "凯芙拉", "武士萌萌香"]],
  ["arkan", "阿尔坎·希耶尔", ["阿尔坎·希耶尔", "阿尔坎"]]
].map(([id,name,aliases])=>({id:pc(id),name,aliases,create:false,actorId:null}));
const relationships = [];
function relation(a,b,aRole,bRole,bio,file,anchor,status="played",delivery="tracker") {
  const key = [a,b].sort().join("|");
  if (relationships.some(r=>[r.sourceId,r.targetId].sort().join("|")===key)) throw new Error(`Duplicate relation ${key}`);
  const id = "taiyi-rel-"+crypto.createHash("sha256").update(key).digest("hex").slice(0,16);
  if(delivery === "tracker" && typeof playerBios[id] !== "string") throw new Error(`Missing reviewed player biography: ${id}`);
  relationships.push({id,sourceId:a,targetId:b,sourceRole:aRole,targetRole:bRole,bio,...(delivery === "tracker" ? {playerBio:playerBios[id]} : {}),evidenceStatus:status,delivery,visibility:delivery==="tracker"?"players":"gm",source:evidence(file,anchor),numericalProgress:"unrated",createReciprocal:true});
}
relation(npc("088"),npc("089"),"堂姐","堂弟","沈漫与沈仲秋为堂姐弟。","discussion/npc/关键NPC.md","堂弟**沈仲秋**","established");
relation(npc("088"),npc("090"),"法定监护人","被监护人","警局登记沈漫为阿瑶的法定监护人。",STATE,"法定监护人");
relation(npc("089"),npc("090"),"照看者","被照看者","S11 沈仲秋照看阿瑶并协助事务所搬迁。",STATE,"照看阿瑶");
relation(npc("088"),npc("100"),"老同学","老同学","沈漫与陈斌是中学时代的老同学。",ENT,"沈曼初中/高中同学");
relation(npc("100"),npc("095"),"主治医生","义肢康复患者","陈斌负责萨布里娜的义肢医疗方案；S11 已进入康复阶段。",ENT,"负责 Sabrina 义肢方案");
relation(npc("088"),npc("103"),"好友","失踪好友","沈漫在 S11 提及失踪好友朱恒；不据此确认朱蘅身份或亲缘。",ENT,"| 朱恒（疑=朱蘅）", "played","gm-journal");
relation(npc("100"),npc("103"),"高中同学","高中同学","陈斌与沈漫、朱恒属于高中旧识；朱恒丈夫的身份不在本条确认。",STATE,"高中 F4", "played","gm-journal");
relation(pc("lihao"),npc("044"),"分行下属","直接主管","陈志远是李好在龙散分行的直接上级。",ENT,"李好的直接上级");
relation(pc("lihao"),npc("046"),"前同事","前同事","李好与何凌曾在江城分行共事；后续有审计与调查联络。",ENT,"李好的前同事");
relation(pc("lihao"),npc("N3"),"木签持有者","异常联系人","S7 棍木女在面馆外主动接触李好并赠予木签。",STATE,"赠予木签护身符");
relation(pc("lihao"),npc("037"),"受托人","已故委托人","李好答应并完成传达白念秋姐姐托付的请求；白念秋已故。",STATE,"你的事我没有不答应的理由");
relation(pc("lihao"),npc("095"),"救助者","获救者","萨布里娜在码头事件中获李好救助，S11 当面向他道谢。",STATE,"被李好挖出");
relation(pc("lihao"),npc("088"),"照片托付对象／事务所同伴","照片托付者／事务所老板","沈漫在高铁上把阿瑶照片交给李好；后续共同参与事务所生活。",STATE,"沈漫在高铁上");
relation(pc("yuko"),npc("096"),"曾受委托的执行者","接头人","照片委托经周凛接洽；S3 已取消，不再标为进行中的交易。",STATE,"周凛已在 S3 取消委托");
relation(pc("tangsuo"),npc("096"),"曾受委托的执行者","接头人","唐索参与周凛的照片委托；S3 已取消。",STATE,"周凛已在 S3 取消委托");
relation(pc("yuko"),npc("033"),"司机旧识／受托人","司机旧识／委托人","S11 赵明芝代表司机方委托欲子追回冻结款；其余队友当时尚未正式入局。",ENT,"与欲子在北环等单时相识");
relation(pc("yuko"),npc("101"),"夜宵摊新识","夜宵摊新识","欲子以阿玉自称结识梁文川并交换联系方式；不附加委托或内幕关系。",ENT,"S10 欲子在夜宵摊");
relation(pc("kevlar"),npc("095"),"朋友／义肢协助者","朋友／康复者","凯芙拉与萨布里娜是朋友，S11 协助安装定制义肢与康复算法。",ENT,"凯芙拉的巴西朋友");
relation(pc("kevlar"),npc("065"),"港口业务联系人","物流联系人","凯芙拉通过宋远的港口物流线参与码头事务。",STATE,"凯芙拉通过宋远");
relation(pc("arkan"),npc("006"),"节点维修受托人","运维委托人","翟明珠委托阿尔坎修复楚钢相关节点。",ENT,"委托阿尔坎修复楚钢节点");
relation(pc("arkan"),npc("072"),"TXT 联系对象","TXT 联系人","S.H. 在工云广场网吧通过 TXT 联系阿尔坎与凯芙拉。",ENT,"以 TXT 方式在工云广场网吧");
relation(pc("kevlar"),npc("072"),"TXT 联系对象","TXT 联系人","S.H. 在工云广场网吧通过 TXT 联系凯芙拉与阿尔坎。",ENT,"以 TXT 方式在工云广场网吧");
for(const p of ["arkan","lei","tangsuo"]) relation(pc(p),npc("061"),"诊所接点","神经接口校准技师","S1 月下诊所是双方交集中的接点；不额外推定手术、师承或秘密归属。",ENT,"S1 中是阿尔坎、雷武龙、唐索发生交集的节点");
for(const p of players) relation(p.id,npc("090"),"生命绑定同伴","生命绑定同伴","码头事件后阿瑶修补众人，事务所中确认生命绑定。",STATE,"生命绑定、世界规则、数据因子概念");
relation(npc("N3"),npc("069"),"被掩护的测量者","外围联络与掩护者","贺梦琪为闻笙提供外围联络与现实生活掩护；尚未向玩家揭露。",GANG,"闻笙的外围联络人与现实生活掩护", "gm-established","gm-journal");
relation(npc("N3"),npc("070"),"后辈／测量者","木签制作前辈","老井教闻笙制作与回收木签；尚未向玩家揭露。",GANG,"教她制作与回收木签的前辈", "gm-established","gm-journal");
relation(npc("080"),npc("090"),"父亲（GM设定）","女儿（GM设定）","既有设定中朱见微为阿瑶父亲；不借此认定失踪者朱恒的身份。",ENT,"阿瑶父亲，ARP", "gm-established","gm-journal");
relation(pc("lihao"),npc("091"),"短租住客","公寓前台","既有人物稿将林彬作为李好临时住所的前台接点；实跑接触细节未复核。",DAILY,"李好的临时住所所在楼", "established","gm-journal");
relation(pc("yuko"),npc("092"),"茶馆常客","茶馆老板娘","既有人物稿中的固定角落桌与长期默契；不宣称为已核对的实跑事件。",DAILY,"欲子在这里有一张固定的角落桌", "established","gm-journal");
relation(pc("kevlar"),npc("093"),"维修合作方","稳定维修委托方","既有人物稿中的维修委托关系。",DAILY,"他是她在龙散最稳定的收入来源", "established","gm-journal");
relation(pc("lei"),npc("094"),"拳场拳手","拳场场务","既有人物稿中杨振邦熟悉并看好雷武龙。",DAILY,"他对雷武龙的态度", "established","gm-journal");
relation(pc("yuko"),npc("056"),"街面合作方","帮派旧相识","既有人物稿中双方按次结算、互不欠账的旧合作。",GANG,"两人是旧相识", "established","gm-journal");
const opinionFile="discussion/npc/NPC最终意见版.md";
const opinion=fs.readFileSync(path.join(ROOT,opinionFile),"utf8");
const proposalSection=opinion.split("## 六、保留并建议坐实的跨组织关系")[1].split("## 七、")[0];
const proposals=proposalSection.split(/\r?\n/).filter(l=>l.startsWith("| ")&&l.includes("—")).map(l=>{const cells=l.split("|").map(v=>v.trim());return {pair:cells[1],type:cells[2],note:cells[3],decision:"hold-proposal",source:evidence(opinionFile,cells[1])};});
if(proposals.length!==21)throw new Error(`Expected 21 proposals, got ${proposals.length}`);
for(const [pair,anchor] of [["周敏—林彬","与林彬是经常核实住客信息"],["程雯—于正清","与于正清是大学老同学"]])proposals.push({pair,decision:"hold-proposal",source:evidence(opinionFile,anchor)});
const organizations=actors.map(a=>({id:`taiyi-org-${a.id}`,sourceId:a.id,name:a.privateRole.split("；")[0],evidenceStatus:"registry-role",delivery:"gm-journal",note:"归档组织／用途，不推导彼此相识，不代表当前公开身份",source:a.source}));
const supplemental=[
  {name:"尼索科托夫",decision:"check-existing-merchant",image:"discussion/npc/尼索科托夫.webp",source:evidence(STATE,"**尼索科托夫先生**")},
  {name:"李文亚",decision:"archival-existing-only-until-image-found",source:evidence(STATE,"**李文亚教授**")},
  {name:"苏志国",decision:"archival-existing-only-until-image-found",source:evidence(STATE,"名字苏志国")},
  {name:"黑骑士",decision:"encounter-entity-check-existing",source:evidence(ENT,"| 黑骑士 |")},
  {name:"死灵术士",decision:"encounter-entity-check-existing",source:evidence(ENT,"| 死灵术士 |")},
  {name:"交管7号",decision:"chapter-design-no-premature-reveal",source:evidence(STATE,"交管7号")}
];
const report={schemaVersion:1,worldId:"taiyi",systemId:"swade",status:"prepared-awaiting-runtime-inventory",actors,players,relationships,organizations,proposals,supplemental,retired:retired.characters.map(c=>({id:c.id,name:c.name,decision:"preserve-existing-do-not-recreate"})),sourceHashes:sources,guardrails:{preserveSystem:true,preserveItems:true,preserveEffects:true,preserveOwnership:true,preserveSceneTokens:true,defaultOwnership:0,noNewStatistics:true,noRankTriggers:true}};
fs.mkdirSync(OUT,{recursive:true});
fs.writeFileSync(path.join(OUT,"npc-import-manifest.json"),JSON.stringify(report,null,2)+"\n");
console.log(JSON.stringify({actors:actors.length,players:players.length,relationships:relationships.length,trackerFacts:relationships.filter(r=>r.delivery==="tracker").length,gmRelationships:relationships.filter(r=>r.delivery==="gm-journal").length,gmOrganizationRecords:organizations.length,heldProposals:proposals.length,supplemental:supplemental.length}));
