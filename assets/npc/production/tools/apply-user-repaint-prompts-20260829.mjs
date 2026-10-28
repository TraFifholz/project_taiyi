import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const read = (p) => JSON.parse(fs.readFileSync(p, "utf8"));
const write = (p, v) => fs.writeFileSync(p, `${JSON.stringify(v, null, 2)}\n`);
const verifiedPath = path.resolve(root, "control", "verified-tags.json");
const verified = read(verifiedPath);
for (const [tag, count] of Object.entries({
  hand_on_own_hip: 227838, smile: 4137280, hair_bun: 369572, single_hair_bun: 92257,
  business_suit: 8024, formal_clothes: 79012, black_necktie: 105467, hand_up: 555785,
  hand_on_own_face: 72697, looking_to_the_side: 279206, sideways_glance: 49121,
  holding_bag: 38181, handbag: 35166, pinstripe_pattern: 17785
})) verified.tags[tag] = { source: "mcp_verified", category: "general", count };
verified.updatedAt = "2026-08-29";
write(verifiedPath, verified);

const commonNeg = ["english_text","chinese_text","character_name","signature","watermark","text_focus","logo","emblem","insignia","badge","name_tag","id_card","barcode","qr_code","hologram","heads-up_display","magic","glowing","aura","light_particles","full_body","shoes","boots","sneakers","backlighting","overlighting"];
const prompts = {
  "LS-NPC-033": {
    version: 4, designStatus: "user-review-pose-and-expression-correction",
    sourceFacts: ["female, age forty-six, former ride-hailing driver and representative of seventeen blocked drivers", "drove for eleven years, keeps the mutual-aid account and supports a sick husband through night shifts", "speaks briefly and exactly but is not habitually hostile or grim", "ordinary person with one rugged exposed left forearm prosthesis in the current visual design"],
    designAssumptions: ["sturdy Chinese woman with a low black ponytail threaded with grey, sun-tanned skin and tired but approachable eyes", "worn brown bomber jacket over a dark red sweater with practical driver techwear and an old crossbody bag", "the blank appeal folder is tucked casually beneath the prosthetic arm at her side while her biological hand rests on her hip, avoiding a girlish protective clutch", "a small dry closed-mouth smile replaces the severe frown; strict cowboy shot with soft even frontal light"],
    sceneConcept: "A grounded middle-aged former driver and labor representative poses with relaxed authority rather than guarded severity.",
    tags: ["1girl","solo","solo_focus","mature_female","medium_hair","low_ponytail","ponytail","black_hair","grey_hair","brown_eyes","bags_under_eyes","thick_eyebrows","tan","smile","closed_mouth","looking_at_viewer","brown_jacket","jacket","open_jacket","bomber_jacket","red_sweater","shirt","long_sleeves","sleeves_rolled_up","belt","messenger_bag","shoulder_bag","crossbody_bag","folder","holding_folder","holding","hand_on_own_hip","standing","wristwatch","cyborg","science_fiction","prosthetic_arm","mechanical_arms","robot_joints","techwear","transparent_background","cowboy_shot"],
    naturalLanguageDetail: "A sturdy sun-tanned forty-six-year-old Chinese former driver wears a small dry closed-mouth smile, holding a thick blank appeal folder casually beneath her rugged left forearm prosthesis at her side while her biological hand rests on her hip, framed from head to mid-thigh under soft even frontal studio light.",
    negativeAdditions: commonNeg
  },
  "LS-NPC-046": {
    version: 4, designStatus: "identity-reference-t2i-v1",
    sourceFacts: ["female Yinzi Bank auditor from Jiangcheng and Li Hao's colleague, confirmed awakened with eidetic memory and transformation into a cat", "the authoritative local NPC reference shows black hair gathered in a low single bun with long loose sidelocks, grey eyes and a cool sideways glance", "the reference outfit is a fitted black business jacket over a grey pinstriped collared shirt and black necktie, with a structured grey-magenta shoulder bag", "standard portrait remains entirely human; cat form is a separate variant and unconfirmed white mist must not appear"],
    designAssumptions: ["translate the local NPC reference into tags rather than attaching it as i2i", "one hand is raised lightly to the side of her face while the other steadies the structured shoulder bag", "retain discreet magenta accents without badges, text or overt supernatural effects", "strict cowboy shot with soft even frontal light"],
    sceneConcept: "A stylish but controlled bank auditor whose urban professional silhouette follows the authoritative NPC reference.",
    tags: ["1girl","solo","solo_focus","mature_female","long_hair","black_hair","hair_bun","single_hair_bun","sidelocks","parted_bangs","hair_between_eyes","grey_eyes","half-closed_eyes","sideways_glance","looking_to_the_side","closed_mouth","business_suit","formal_clothes","suit","black_jacket","open_jacket","open_clothes","grey_shirt","collared_shirt","pinstripe_pattern","black_necktie","necktie","long_sleeves","black_pants","pants","belt","shoulder_bag","handbag","holding_bag","holding","hand_up","hand_on_own_face","standing","cyberpunk","streetwear","transparent_background","cowboy_shot"],
    naturalLanguageDetail: "A precise thirty-one-year-old Chinese bank auditor with black hair gathered in a low bun, long loose sidelocks and cool grey eyes gives a restrained sideways glance while wearing a fitted black business jacket, grey pinstriped shirt, black necktie and structured grey-magenta shoulder bag, framed from head to mid-thigh under soft even frontal studio light.",
    negativeAdditions: ["cat","animal","animal_ears","cat_ears","transformation","fog","smoke", ...commonNeg]
  },
  "LS-NPC-088": {
    version: 4, designStatus: "identity-reference-t2i-v2",
    designAssumptions: ["use the authoritative image only as visual evidence; do not attach any image to the NovelAI request", "lock vivid pink-red high-ponytail hair, purple eyes, thin glasses, weary sideways gaze, layered black-grey techwear and restrained purple accents", "strict 832x1216 head-to-mid-thigh cowboy shot with soft even frontal light and subdued edges"],
    sceneConcept: "Pure text-to-image reconstruction of Shen Man's canonical identity anchors.",
    naturalLanguageDetail: "A weary Chinese woman in her early thirties has vivid pink-red hair in a high ponytail, thin glasses over purple eyes and layered black-grey techwear with restrained purple accents, holding one unlit cigarette-like prop near her chest in a strict head-to-mid-thigh portrait under soft even frontal studio light."
  },
  "LS-NPC-089": {
    version: 5, designStatus: "identity-reference-t2i-v2",
    designAssumptions: ["use the authoritative image only as visual evidence; do not attach any image to the NovelAI request", "lock the androgynous young male face, long silver-grey high ponytail, large red bow, red earphones, striped undersleeves, oversized black t-shirt, black shorts and crossbody bag", "strict 832x1216 head-to-mid-thigh cowboy shot with soft even frontal light"],
    sceneConcept: "Pure text-to-image reconstruction of Shen Zhongqiu's canonical identity anchors.",
    naturalLanguageDetail: "An androgynous young Chinese man has long silver-grey hair in a high ponytail with a large red bow and wears red earphones, an oversized black t-shirt over black-pink striped undersleeves, black shorts and a crossbody bag in a strict head-to-mid-thigh portrait under soft even frontal studio light."
  },
  "LS-NPC-090": {
    version: 4, designStatus: "identity-reference-t2i-v2",
    designAssumptions: ["use the authoritative image only as visual evidence; do not attach any image to the NovelAI request", "lock long white hair, vivid red eyes, a small black-red hair ornament, white dress, necklace and oversized black coat with red trim", "keep her clearly childlike and ordinary in the standard portrait", "strict 832x1216 head-to-mid-thigh cowboy shot with soft even frontal light"],
    sceneConcept: "Pure text-to-image reconstruction of Zhu Yaoguang's canonical identity anchors.",
    naturalLanguageDetail: "A clearly childlike Chinese girl has long white hair, vivid red eyes and a small black-red hair ornament, wearing a white dress, delicate necklace and oversized black coat with red trim in a strict head-to-mid-thigh portrait under soft even frontal studio light."
  },
  "LS-NPC-103": {
    version: 3, designStatus: "user-review-soft-expression-correction",
    designAssumptions: ["provisional age twenty-nine with Aya's close facial structure, shoulder-length straight white hair, uneven bangs and red eyes", "a small reassuring closed-mouth smile and relaxed brow replace the guarded expression while preserving obvious family resemblance", "ordinary 2021 cream cardigan, muted blue shirt, dark jeans and plain brown shoulder bag", "strict head-to-mid-thigh cowboy shot with soft even frontal light"],
    sceneConcept: "A pre-disappearance adult relative of Aya remembered as gentle and approachable rather than guarded.",
    naturalLanguageDetail: "A pre-disappearance twenty-nine-year-old Chinese woman looks unmistakably like an adult Aya through the same shoulder-length straight white hair, uneven bangs, red eyes and facial proportions, but wears a small reassuring closed-mouth smile with relaxed brows above a cream cardigan, muted blue shirt and plain brown shoulder bag in a strict head-to-mid-thigh portrait under soft even frontal studio light."
  }
};

for (const [id, updates] of Object.entries(prompts)) {
  const p = path.resolve(root, "prompts", `${id}.json`);
  const prompt = read(p);
  Object.assign(prompt, updates);
  if (id === "LS-NPC-103") {
    prompt.tags = prompt.tags.filter((t) => !["serious", "expressionless"].includes(t));
    if (!prompt.tags.includes("smile")) prompt.tags.splice(prompt.tags.indexOf("closed_mouth"), 0, "smile");
  }
  write(p, prompt);
}

const masterPath = path.resolve(root, "control", "portrait-master.json");
const master = read(masterPath);
const decisionsPath = path.resolve(root, "control", "review-decisions.json");
const decisions = read(decisionsPath);
for (const id of Object.keys(prompts)) {
  const c = master.characters.find((x) => x.id === id);
  if (!c) throw new Error(`Missing ${id}`);
  c.promptStatus = "verified";
  c.productionStatus = "not_started";
  c.visualRefresh = "required_by_user_review";
  delete decisions.decisions[id];
}
master.updatedAt = new Date().toISOString();
decisions.updatedAt = master.updatedAt;
write(masterPath, master);
write(decisionsPath, decisions);
console.log("Applied six user-review repaint prompt corrections; identity trio locked to text-to-image only.");
