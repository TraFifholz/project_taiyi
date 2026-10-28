import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..");
const npcRoot = path.resolve(root, "../../../campaign/npcs");
const now = new Date().toISOString();

const readJson = (p) => JSON.parse(fs.readFileSync(p, "utf8"));
const writeJson = (p, v) => fs.writeFileSync(p, `${JSON.stringify(v, null, 2)}\n`);
const sha256 = (p) => crypto.createHash("sha256").update(fs.readFileSync(p)).digest("hex");

const refDir = path.resolve(root, "assets", "reference", "identity");
const references = [
  ["LS-NPC-088", "沈漫", "沈漫.png", "385f14807aedee30a2d71e6ae1c26c4ed9076c124627126e2e81288a660564ee"],
  ["LS-NPC-089", "沈仲秋", "沈仲秋.png", "761c76c5a36722a573bb0409638700729928e3f769b9146218ccbda48a6ecb6b"],
  ["LS-NPC-090", "阿瑶（朱瑶光）", "朱瑶光.png", "e4ec2b5a0221d5eb050e88d4b80d926b3bc59fb55820e0e12eeab8ba79d18d6f"],
  ["LS-NPC-096", "周凛", "周凛.png", "f36ec7ea85214e085f4148e193a068e92b0bf722733cb58295305c35f9021414"]
];
for (const [, , file] of references) {
  const p = path.resolve(refDir, file);
  if (!fs.existsSync(p)) throw new Error(`Missing converted identity reference: ${p}`);
}
writeJson(path.resolve(root, "control", "identity-reference-manifest.json"), {
  schemaVersion: 1,
  updatedAt: now,
  policy: "Identity references are authoritative for stable appearance. Only LS-NPC-088/089/090 are attached to the current NovelAI i2i requests; LS-NPC-096 is visual canon evidence for the male correction.",
  entries: references.map(([id, name, file, sourceSha256]) => ({
    id,
    name,
    sourceDirectory: "C:/Users/Fifholz/Pictures/龙散战记/NPC",
    localCopy: `assets/reference/identity/${file}`,
    sourceSha256,
    localPngSha256: sha256(path.resolve(refDir, file)),
    width: 832,
    height: 1216,
    mode: "RGBA",
    generationUse: ["LS-NPC-088", "LS-NPC-089", "LS-NPC-090"].includes(id) ? "img2img-strength-0.5" : "canon-evidence-only"
  }))
});

const verifiedPath = path.resolve(root, "control", "verified-tags.json");
const verified = readJson(verifiedPath);
const addVerified = {
  purple_eyes: 1190439, hooded_jacket: 88518, cigarette: 49787, pleated_skirt: 705517,
  hair_bow: 755788, red_bow: 329497, striped_sleeves: 6476, black_shorts: 195041,
  short_shorts: 192615, hair_ornament: 2052734, white_dress: 449086, off_shoulder: 343681,
  red_trim: 9300, jirai_kei: 8039, black_mask: 15163, black_nails: 120752,
  yellow_eyes: 1014067, frilled_shirt: 37305, pink_shirt: 72670, black_bow: 225020,
  black_ribbon: 192674, choker: 615788, hair_over_one_eye: 367663, talisman: 4601,
  frills: 767259, bow: 1716512, long_bangs: 47331, layered_clothes: 9346,
  one_eye_covered: 72501
};
for (const [tag, count] of Object.entries(addVerified)) {
  verified.tags[tag] = { source: "mcp_verified", category: "general", count };
}
verified.updatedAt = "2026-08-29";
writeJson(verifiedPath, verified);

const commonNeg = ["english_text","chinese_text","character_name","signature","watermark","text_focus","logo","emblem","insignia","badge","name_tag","id_card","barcode","qr_code","hologram","heads-up_display","magic","glowing","aura","light_particles","full_body","shoes","boots","sneakers","backlighting","overlighting"];
const prompts = {
  "LS-NPC-088": {
    schemaVersion: 1, characterId: "LS-NPC-088", characterName: "沈漫", version: 3,
    designStatus: "identity-reference-i2i-v1",
    sourceFacts: [
      "female, appears in her early thirties but may be older, owner of Suiyuan Office and confirmed awakened main-story mentor",
      "the authoritative local identity reference shows vivid pink-red hair in a high ponytail, purple eyes behind thin glasses, a weary sideways gaze and layered black-grey techwear",
      "her current right hand is a data-factor reconstruction but appears outwardly human in the standard portrait; purple flame and silver wings remain ability-only variants"
    ],
    designAssumptions: ["Preserve the reference face, hair silhouette, glasses, black-grey layered jacket, muted purple accents and cigarette-like hand pose", "NovelAI image-to-image uses the registered identity PNG at strength 0.5 and noise 0.5", "Strict head-to-mid-thigh cowboy shot with soft even frontal light and subdued edges"],
    sceneConcept: "Identity-preserving i2i portrait based on the registered local reference.",
    tags: ["1girl","solo","solo_focus","mature_female","long_hair","pink_hair","high_ponytail","messy_hair","purple_eyes","glasses","half-closed_eyes","serious","closed_mouth","looking_at_viewer","hooded_jacket","black_jacket","grey_hoodie","open_jacket","open_clothes","oversized_clothes","layered_clothes","long_sleeves","pleated_skirt","black_skirt","belt","buckle","cigarette","holding","standing","cyberpunk","techwear","transparent_background","cowboy_shot"],
    naturalLanguageDetail: "Preserve the authoritative reference identity of a weary Chinese woman with vivid pink-red high-ponytail hair, thin glasses, layered black-grey techwear and restrained purple accents, framed from head to mid-thigh under soft even frontal studio light.",
    negativeAdditions: commonNeg,
    seed: 882174630,
    sourceLocator: "identity-reference-manifest.json LS-NPC-088; NPC立绘设定终稿.md LS-NPC-088; records/memory/campaign-state.md"
  },
  "LS-NPC-089": {
    schemaVersion: 1, characterId: "LS-NPC-089", characterName: "沈仲秋", version: 4,
    designStatus: "identity-reference-i2i-v1",
    sourceFacts: [
      "male young adult and Shen Man's younger male cousin; manages the esports room and generator at Suiyuan Office",
      "the authoritative local identity reference shows an androgynous youthful face, long silver-grey hair in a high ponytail with a large red bow, grey eyes, red earphones and black-pink layered streetwear",
      "in play he moves equipment, watches over Aya and hands over keys"
    ],
    designAssumptions: ["Preserve the reference face, silver-grey ponytail, large red hair bow, earphones, striped undersleeves, black t-shirt, shorts and crossbody bag", "NovelAI image-to-image uses the registered identity PNG at strength 0.5 and noise 0.5", "Strict head-to-mid-thigh cowboy shot with soft even frontal light"],
    sceneConcept: "Identity-preserving i2i portrait based on the registered local reference.",
    tags: ["1boy","solo","male_focus","solo_focus","long_hair","grey_hair","high_ponytail","hair_bow","red_bow","long_bangs","hair_over_one_eye","grey_eyes","serious","closed_mouth","looking_at_viewer","earphones","black_shirt","t-shirt","striped_sleeves","long_sleeves","layered_clothes","black_shorts","short_shorts","crossbody_bag","bag","belt","key","standing","streetwear","punk","transparent_background","cowboy_shot"],
    naturalLanguageDetail: "Preserve the authoritative reference identity of an androgynous young Chinese man with a silver-grey high ponytail, large red bow, red earphones, black-pink layered streetwear, shorts and a crossbody bag, framed from head to mid-thigh under soft even frontal studio light.",
    negativeAdditions: commonNeg,
    seed: 891563204,
    sourceLocator: "identity-reference-manifest.json LS-NPC-089; NPC立绘设定终稿.md LS-NPC-089; records/memory/entities.md"
  },
  "LS-NPC-090": {
    schemaVersion: 1, characterId: "LS-NPC-090", characterName: "阿瑶（朱瑶光）", version: 3,
    designStatus: "identity-reference-i2i-v1",
    sourceFacts: [
      "girl with a mind approximately eight to nine years old; current outward age remains unconfirmed; confirmed awakened PC life-binding and anchor candidate",
      "the authoritative local identity reference shows long white hair, vivid red eyes, a small black-red hair ornament, a white dress and an oversized black coat with red trim",
      "standard portrait must remain childlike and must not show persistent data streams, disaster aura or plot-scale effects"
    ],
    designAssumptions: ["Preserve the reference face, long white hair, red eyes, hair ornament, white dress, necklace and black-red oversized coat", "NovelAI image-to-image uses the registered identity PNG at strength 0.5 and noise 0.5", "Strict head-to-mid-thigh cowboy shot with soft even frontal light"],
    sceneConcept: "Identity-preserving i2i portrait based on the registered local reference.",
    tags: ["1girl","solo","solo_focus","child","petite","long_hair","white_hair","straight_hair","red_eyes","hair_ornament","serious","closed_mouth","looking_at_viewer","white_dress","off_shoulder","black_coat","open_coat","open_clothes","oversized_clothes","red_trim","necklace","long_sleeves","standing","transparent_background","simple_background","cowboy_shot"],
    naturalLanguageDetail: "Preserve the authoritative reference identity of a clearly childlike Chinese girl with long white hair, vivid red eyes, a small black-red hair ornament, white dress, necklace and oversized black coat with red trim, framed from head to mid-thigh under soft even frontal studio light.",
    negativeAdditions: ["mature_female","large_breasts","cleavage","makeup","gun","weapon", ...commonNeg],
    seed: 903418527,
    sourceLocator: "identity-reference-manifest.json LS-NPC-090; NPC立绘设定终稿.md LS-NPC-090; records/memory/campaign-state.md"
  },
  "LS-NPC-096": {
    schemaVersion: 1, characterId: "LS-NPC-096", characterName: "周凛", version: 5,
    designStatus: "canon-sex-correction-male",
    sourceFacts: ["male adult independent broker in the Yellow District, ordinary", "takes deposits first, leaves no records and previously served as a contact for Yuzi and Tangsuo", "the local canon image confirms a mature Chinese man with short black hair, light stubble and dark black-magenta techwear"],
    designAssumptions: ["Preserve the male identity, short black hair, lined face, stubble and black jacket with restrained magenta lining", "Strict head-to-mid-thigh cowboy shot; no organization insignia or readable text", "Soft even frontal light with subdued edges"],
    sceneConcept: "Corrected male portrait for the Yellow District independent broker.",
    tags: ["1boy","solo","male_focus","solo_focus","mature_male","short_hair","black_hair","grey_eyes","stubble","serious","closed_mouth","looking_at_viewer","hooded_jacket","black_jacket","open_jacket","open_clothes","black_shirt","shirt","long_sleeves","cargo_pants","pants","belt","standing","cyberpunk","techwear","streetwear","transparent_background","cowboy_shot"],
    naturalLanguageDetail: "A mature Chinese male broker with short black hair, a lined guarded face and light stubble wears a black hooded techwear jacket with restrained magenta lining over dark cargo trousers, framed from head to mid-thigh under soft even frontal studio light.",
    negativeAdditions: ["1girl","female","mature_female", ...commonNeg],
    seed: 962705318,
    sourceLocator: "C:/Users/Fifholz/Pictures/龙散战记/NPC/周凛.webp; NPC立绘设定终稿.md LS-NPC-096; records/memory/entities.md"
  },
  "LS-NPC-N3": {
    schemaVersion: 1, characterId: "LS-NPC-N3", characterName: "棍木女（代称）", version: 1,
    designStatus: "actual-play-anchored-jirai-kei",
    sourceFacts: ["female Gunmu Society measurer who directly contacted Li Hao outside the noodle shop in session 7", "confirmed appearance: jirai-kei clothing, one eye covered by an eyepatch, black mouth mask, black nail polish and a single visible golden eye", "confirmed behavior: near-emotionless electronic synthetic voice, calls herself a nonexistent existence, announces the divine-child prophecy and gives Li Hao a small wooden protective tag", "real name, age, nature of the golden eye and whether her anomaly is awakened or technological remain unknown"],
    designAssumptions: ["provisional long black twintails and a black-pink frilled jirai-kei outfit provide a coherent silhouette without defining her real identity", "the golden visible eye is depicted without exposed machinery so the supernatural-versus-cybernetic question remains open", "Strict head-to-mid-thigh cowboy shot with her black-nailed hand holding one small plain wooden tag"],
    sceneConcept: "The recurring Gunmu Society measurer who contacted Li Hao, represented by her stable actual-play visual anchors.",
    tags: ["1girl","solo","solo_focus","long_hair","black_hair","twintails","yellow_eyes","eyepatch","one_eye_covered","mouth_mask","black_mask","serious","looking_at_viewer","black_nails","nail_polish","jirai_kei","frilled_shirt","pink_shirt","black_skirt","pleated_skirt","black_bow","black_ribbon","choker","frills","bow","long_sleeves","holding","talisman","standing","cyberpunk","streetwear","transparent_background","cowboy_shot"],
    naturalLanguageDetail: "A guarded Chinese woman in black-pink jirai-kei clothing exposes only one golden eye between an eyepatch and black mouth mask, her black-polished fingers holding one small plain wooden protective tag in a strict head-to-mid-thigh portrait under soft even frontal studio light.",
    negativeAdditions: commonNeg,
    seed: 113709887,
    sourceLocator: "records/memory/session-07.md lines 69-77 and 109-113; records/memory/campaign-state.md Gunmu Woman; actual transcript S7 lines 3785-3899"
  }
};
for (const [id, prompt] of Object.entries(prompts)) writeJson(path.resolve(root, "prompts", `${id}.json`), prompt);

const masterPath = path.resolve(root, "control", "portrait-master.json");
const master = readJson(masterPath);
master.targetCount = 93;
for (const id of ["LS-NPC-088","LS-NPC-089","LS-NPC-090","LS-NPC-096"]) {
  const c = master.characters.find((x) => x.id === id);
  if (!c) throw new Error(`Missing ${id}`);
  if (c.approvedAsset) c.supersededApproval = { approvedAsset: c.approvedAsset, approvedRun: c.approvedRun, approvedSha256: c.approvedSha256, approvedAt: c.approvedAt, reason: "Canonical identity reference or sex correction superseded the approved candidate on 2026-08-29" };
  c.approvedAsset = null;
  delete c.approvedRun; delete c.approvedSha256; delete c.approvedAt;
  c.promptStatus = "verified";
  c.productionStatus = "not_started";
  c.visualRefresh = "required_by_canon_correction";
}
const zhou = master.characters.find((x) => x.id === "LS-NPC-096");
zhou.unknowns = "年龄细节、交易道具；性别已确认为男";
zhou.visualDirective = "mature male broker in black-magenta hooded techwear, short black hair and light stubble";
if (!master.characters.some((x) => x.id === "LS-NPC-N3")) {
  master.characters.push({ id: "LS-NPC-N3", name: "棍木女（代称）", organization: "棍木会；测量者／李好木签联系人", marker: "【超·疑】", grade: "B", priority: "P0", sourceStatus: "source_ready", promptStatus: "verified", productionStatus: "not_started", approvedAsset: null, latestRun: null, unknowns: "本名、年龄、金瞳性质、真实能力与是否为技术改造", sourceLocator: "S7逐字稿L3785-L3899；records/memory/session-07.md", visualLayer: "cyberpunk-signal", targetStyle: "jirai-kei-gunmu-measurer", visualDirective: "black-pink jirai-kei, eyepatch, black mouth mask, black nails, one visible golden eye and a wooden protective tag", visualRefresh: "new_actual_play_anchor" });
}
master.visualRefreshPolicy = { cyberpunkSignal: 45, diverseCivic: 48, refresh: 73, retain: 20 };
master.updatedAt = now;
writeJson(masterPath, master);

const planPath = path.resolve(root, "control", "visual-refresh-plan.json");
const plan = readJson(planPath);
plan.targetPopulation = 93;
plan.policy.cyberpunkSignalTarget = "45/93 = 48.4% after adding the actual-play Gunmu measurer";
plan.policy.remainderTarget = "48/93 = 51.6%, preserving varied non-cyber silhouettes";
plan.counts = { cyberpunkSignal: 45, diverseCivic: 48, refresh: 73, retain: 20 };
if (!plan.entries.some((x) => x.id === "LS-NPC-N3")) plan.entries.push({ id: "LS-NPC-N3", name: "棍木女（代称）", organization: "棍木会；测量者／李好木签联系人", layer: "cyberpunk-signal", targetStyle: "jirai-kei-gunmu-measurer", refresh: true, designDirective: "black-pink jirai-kei, eyepatch, black mouth mask, black nails, one visible golden eye and a wooden protective tag", addTags: ["cyberpunk","streetwear","jirai_kei","eyepatch","mouth_mask","black_nails","yellow_eyes"] });
plan.updatedAt = now;
writeJson(planPath, plan);

const decisionsPath = path.resolve(root, "control", "review-decisions.json");
const decisions = readJson(decisionsPath);
for (const id of ["LS-NPC-088","LS-NPC-089","LS-NPC-090","LS-NPC-096"]) delete decisions.decisions[id];
decisions.updatedAt = now;
writeJson(decisionsPath, decisions);

function replaceIn(file, replacements) {
  const p = path.resolve(npcRoot, file);
  let s = fs.readFileSync(p, "utf8");
  for (const [a, b] of replacements) {
    if (!s.includes(a)) throw new Error(`Text not found in ${file}: ${a.slice(0, 80)}`);
    s = s.replaceAll(a, b);
  }
  fs.writeFileSync(p, s);
}

replaceIn("reference/NPC立绘设定终稿.md", [
  ["（92 个活跃槽事实源）", "（93 个活跃槽事实源）"],
  ["最终 92 个活跃槽＝原 107 槽排除或合并 14 人＋新增 2 人－退役 3 名一次性人物。", "最终 93 个活跃槽＝原 107 槽排除或合并 14 人＋新增 3 人－退役 3 名一次性人物；N3 为实跑漏录补回。"],
  ["## 三、92 个活跃槽逐人事实卡", "## 三、93 个活跃槽逐人事实卡"],
  ["| LS-NPC-088 | A／P0 | 沈漫 | 随缘事务所；老板、主线导师 | 【超】 | 女；30岁出头或更老，难判断 | 头发随意扎起；倦怠眼神；外表年龄模糊 | 宽松长款外套；右手为数据因子重构替代物 |", "| LS-NPC-088 | A／P0 | 沈漫 | 随缘事务所；老板、主线导师 | 【超】 | 女；30岁出头或更老，难判断 | 正式参考：玫红高马尾、紫瞳、细框眼镜、倦怠侧视 | 正式参考：黑灰分层机能外套、灰色内搭、紫色点缀；右手为数据因子重构替代物 |"],
  ["| LS-NPC-089 | B／P0 | 沈仲秋 | 随缘事务所；电竞房与发电机管理 | 普通 | 男；年轻成年人 | 待设计 | 待设计 |", "| LS-NPC-089 | B／P0 | 沈仲秋 | 随缘事务所；电竞房与发电机管理 | 普通 | 男；年轻成年人，外貌偏中性 | 正式参考：银灰长发高马尾、大红蝴蝶结、灰瞳 | 正式参考：黑粉叠穿、条纹长袖、短裤、斜挎包与红色耳机 |"],
  ["| LS-NPC-090 | B／P0 | 阿瑶（朱瑶光） | 随缘事务所；PC生命绑定／锚点候选 | 【超】 | 女孩；心智约8—9岁，外观年龄待确认 | 白发、红眼 | 服装待设计 |", "| LS-NPC-090 | B／P0 | 阿瑶（朱瑶光） | 随缘事务所；PC生命绑定／锚点候选 | 【超】 | 女孩；心智约8—9岁，外观年龄待确认 | 正式参考：白色长发、鲜红眼睛、小型黑红发饰 | 正式参考：白裙、项链、黑色红边宽大外套 |"],
  ["| LS-NPC-096 | B／P0 | 周凛 | 自由人；黄区掮客 | 普通 | 女；年龄待设计 | 待设计 | 待设计 |", "| LS-NPC-096 | B／P0 | 周凛 | 自由人；黄区掮客 | 普通 | 男；成年 | 正式参考：黑色短发、面部细纹、淡胡茬 | 正式参考：黑色机能夹克、洋红内衬、深色工装裤 |"],
  ["| LS-NPC-070 |", "| LS-NPC-N3 | B／P0 | 棍木女（代称） | 棍木会；测量者／李好木签联系人 | 【超·疑】 | 女；年龄不明 | 地雷系；眼罩遮一眼、黑色口罩、唯一露出的眼睛为金色、黑色美甲 | 黑粉地雷系服装；手持小木签 | 无机质电子合成音；自称“不存在的存在” | 是但不定性：金瞳与电子音可见，暂不写死为觉醒或义体 | S7 主动接触李好、宣告神子预言、赠木签护身 | 本名、年龄、金瞳性质、真实能力与改造程度 | S7逐字稿L3785-L3899；session-07.md§棍木女 |\n| LS-NPC-070 |"],
  ["活跃稳定 ID：92 个", "活跃稳定 ID：93 个"]
]);

replaceIn("roster/全城NPC名单.md", [
  ["（104 个活跃工作身份槽）", "（105 个活跃工作身份槽）"],
  ["不表示 104 个活跃身份均已拍板", "不表示 105 个活跃身份均已拍板"],
  ["## 十七、棍木会（3）", "## 十七、棍木会（4）"],
  ["71. 阿噪｜噪音艺术家", "71. 阿噪｜噪音艺术家\nN3. 棍木女（代称）【超·疑】｜测量者｜金色单瞳、地雷系穿搭、木签联系人（实跑漏录补回）"],
  ["**104 个活跃身份槽**", "**105 个活跃身份槽**"],
  ["| 【超】（含 17 名【超·潜】） | 54 |", "| 【超】（含 17 名【超·潜】及 N3【超·疑】） | 55 |"],
  ["| 三类标记合计 | 57 人（54.8%） |", "| 三类标记合计 | 58 人（55.2%） |"]
]);

replaceIn("reference/NPC最终意见版.md", [
  ["（92 个活跃身份槽）", "（93 个活跃身份槽）"],
  ["形成 92 个活跃建议槽。", "形成 93 个活跃建议槽；其中 N3 棍木女为实跑漏录补回。"],
  ["而不是 92 个各自携带", "而不是 93 个各自携带"],
  ["本版 92 个活跃槽", "本版 93 个活跃槽"],
  ["| 棍木会 | 2 | 69 贺梦琪、70 老井 | 一个街面据点、一个有历史重量的实干家已经足够 |", "| 棍木会 | 3 | 69 贺梦琪、70 老井、N3 棍木女 | 据点、实干维护者与实跑测量者三层；棍木女补回后承接李好木签与神子预言 |"],
  ["合计：75（组织）＋3（事务所）＋7（日常接点）＋7（自由/档案）＝**92 个活跃身份槽**。", "合计：76（组织）＋3（事务所）＋7（日常接点）＋7（自由/档案）＝**93 个活跃身份槽**。"],
  ["先冻结上述 92 个活跃槽", "先冻结上述 93 个活跃槽"]
]);

replaceIn("NPC工作总控.md", [
  ["104 个活跃身份槽", "105 个活跃身份槽"],
  ["`NPC最终意见版.md`（92 个活跃槽）", "`NPC最终意见版.md`（93 个活跃槽）"],
  ["| 编号身份槽 | 104 |", "| 编号身份槽 | 105 |"],
  ["| 【超】（含 17 名【超·潜】） | 54 |", "| 【超】（含 17 名【超·潜】及 N3【超·疑】） | 55 |"],
  ["| 三类标记合计 | 57／104（54.8%） |", "| 三类标记合计 | 58／105（55.2%） |"],
  ["得到 92 个活跃槽。", "得到 93 个活跃槽（含实跑漏录补回的 N3 棍木女）。"],
  ["### R｜实跑锚定（22）", "### R｜实跑锚定（23）"],
  ["107 男偶像。", "107 男偶像、N3 棍木女（代称）。"]
]);

console.log("Applied identity references, Zhou Lin male correction, and LS-NPC-N3 Gunmu Woman roster restoration.");
