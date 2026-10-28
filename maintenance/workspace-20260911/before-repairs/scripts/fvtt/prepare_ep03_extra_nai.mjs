import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

const root = process.cwd();
const portraitRoot = path.join(root, 'records/prep/ep03-fvtt-20260903/portraits');
const sourceRoot = path.join(portraitRoot, 'extras-vehicles-20260904');
const output = path.join(sourceRoot, 'nai-20260904');
const production = path.join(root, 'discussion/npc/立绘生产');
const profilePath = path.join(production, 'control/api-profile.json');
const profile = JSON.parse(fs.readFileSync(profilePath, 'utf8'));
const priorPoolPath = path.join(portraitRoot, 'control/verified-tags.json');
const priorPool = JSON.parse(fs.readFileSync(priorPoolPath, 'utf8')).tags;
const actorManifestPath = path.join(sourceRoot, 'manifest.json');
const actorManifest = JSON.parse(fs.readFileSync(actorManifestPath, 'utf8'));
const actorByKey = new Map(actorManifest.assets.map((entry) => [entry.key, entry]));
const sha = (value) => crypto.createHash('sha256').update(value).digest('hex');
const createdAt = new Date().toISOString();

// Counts below were refreshed through Danbooru MCP on 2026-09-04 for this batch.
const refreshedTags = {
  hard_hat: 2121,
  wrench: 6582,
  beanie: 35417,
  winter_clothes: 27124,
  looking_away: 34936,
  safety_glasses: 1207,
  driving: 6449,
  steering_wheel: 5063,
  car_interior: 6144,
  business_suit: 8042,
  formal_clothes: 79141,
  office_lady: 22615,
  suit: 106437,
  drone: 4568,
  no_humans: 234614,
  robot: 92626,
  vehicle_focus: 15349,
  quadcopter: 237,
  propeller: 1907,
  rotor: 40,
  camera: 32000,
  security_camera: 393,
  machinery: 9181,
  science_fiction: 59153,
  flying: 43580,
  midair: 11378,
  blue_theme: 39701,
  white_theme: 4499,
  grey_theme: 2263,
  from_above: 145481,
  industrial: 663,
  circuit_board: 497,
  floating: 60676,
  facing_viewer: 102893,
  reflection: 56226,
  shiny: 4817,
  circle: 7501,
  surveillance: 21,
  outline: 90314
};

const commonNegative = [
  'watermark', 'signature', 'character_name', 'english_text', 'chinese_text',
  'logo', 'emblem', 'badge', 'text_focus', 'hologram', 'heads-up_display',
  'glowing', 'aura', 'light_particles', 'child', 'school_uniform', 'weapon', 'gun'
];

const definitions = [
  {
    key: 'cleaner', characterId: 'EP03-EXTRA-CLEANER', slug: 'extra-cleaner',
    sourceFacts: ['穗安合规服务的清理人员模板；负责工业拆卸和数据清理，不是具名人物。'],
    designAssumptions: ['成年中国男性，短黑发、棕眼，佩戴安全帽与护目镜。', '灰色工业夹克、黑色工装裤、工具腰带、手套，手持普通扳手。'],
    sceneConcept: '成年中国男性合规清理员独自站在透明背景前，短黑发、棕眼，戴灰色安全帽和透明护目镜；穿耐磨灰色工业夹克、黑色工装裤、工具腰带和手套，一手自然握着普通扳手；冷静无表情，三分之四身，柔和均匀正面光。',
    tags: ['highres','1boy','solo','male_focus','mature_male','short_hair','black_hair','brown_eyes','hard_hat','helmet','safety_glasses','grey_jacket','jacket','collared_shirt','grey_shirt','long_sleeves','zipper','pocket','black_pants','cargo_pants','belt','utility_belt','pouch','black_gloves','gloves','boots','holding','wrench','serious','expressionless','closed_mouth','looking_at_viewer','standing','cowboy_shot','transparent_background','shadow','flat_color'],
    naturalLanguageDetail: 'An adult Chinese industrial compliance cleanup worker in plain grey protective workwear holds one ordinary wrench at his side. He is practical and anonymous, with no logo, readable text, weapon, or supernatural effect.',
    negativeAdditions: ['facial_hair','muscular_male']
  },
  {
    key: 'qingshao', characterId: 'EP03-EXTRA-QINGSHAO', slug: 'extra-qingshao',
    sourceFacts: ['棍木会青梢队成员模板；负责登车、固定车辆与救援，不是具名人物。'],
    designAssumptions: ['成年中国女性，短棕发、棕眼，机警结实。', '深绿骑行夹克、灰色高领内搭、黑工装裤、半指手套、安全绳与摩托头盔。'],
    sceneConcept: '成年中国女性青梢队员独自站在透明背景前，短棕发、棕眼；穿深绿色骑行夹克、灰色高领内搭、黑色工装裤、半指手套和简洁安全带，一手提普通摩托头盔，另一手扶腰；神情自信警觉，三分之四身，柔和均匀正面光。',
    tags: ['highres','1girl','solo','mature_female','short_hair','brown_hair','brown_eyes','swept_bangs','hair_behind_ear','green_jacket','bomber_jacket','high_collar','grey_shirt','long_sleeves','zipper','pocket','black_pants','cargo_pants','belt','utility_belt','pouch','fingerless_gloves','black_gloves','earpiece','boots','holding','helmet','motorcycle_helmet','harness','hand_on_own_hip','smirk','closed_mouth','looking_at_viewer','standing','cowboy_shot','transparent_background','shadow','flat_color'],
    naturalLanguageDetail: 'An adult Chinese street crew member wears practical dark forest-green riding gear with a plain climbing safety tether. She holds a simple motorcycle helmet and has no gang logo, weapon, readable text, or supernatural effect.',
    negativeAdditions: ['cleavage','midriff']
  },
  {
    key: 'ma-driver', characterId: 'EP03-EXTRA-MA-DRIVER', slug: 'extra-ma-driver',
    sourceFacts: ['马铁鹰冷藏车的普通司机模板；不是马铁鹰本人，也不是具名人物。'],
    designAssumptions: ['成年中国男性，短乱黑发、棕眼、眼下倦色，戴深色针织帽。', '旧蓝色保暖工作夹克、灰色内搭、黑手套，在方向盘后保持警惕。'],
    sceneConcept: '成年中国男性冷链司机坐在透明背景前的驾驶姿势中，短乱黑发、棕眼、眼下倦色，戴深色针织帽；穿旧蓝色保暖工作夹克、灰色内搭和黑手套，双手扶住简化的方向盘；神情疲惫警惕，上半身构图，柔和均匀正面光。',
    tags: ['highres','1boy','solo','male_focus','mature_male','short_hair','black_hair','messy_hair','brown_eyes','bags_under_eyes','beanie','winter_clothes','blue_jacket','jacket','grey_shirt','shirt','long_sleeves','high_collar','zipper','pocket','black_pants','pants','belt','black_gloves','gloves','holding','driving','steering_wheel','car_interior','sitting','serious','closed_mouth','looking_away','upper_body','transparent_background','shadow','flat_color'],
    naturalLanguageDetail: 'A tired adult Chinese refrigerated-truck driver sits behind only a simplified steering wheel fragment, dressed in worn cold-weather workwear. Keep him clearly human and ordinary; no full vehicle, logo, readable text, weapon, or supernatural effect.',
    negativeAdditions: ['facial_hair','muscular_male','vehicle_focus']
  },
  {
    key: 'auditor', characterId: 'EP03-EXTRA-AUDITOR', slug: 'extra-auditor',
    sourceFacts: ['M-3随车审计员模板；是需要保护的无武装目标，不是具名人物。'],
    designAssumptions: ['成年中国女性，黑色马尾、棕眼、长方眼镜，神情严肃。', '黑色商务套装外罩普通橙色反光背心，手持审计平板。'],
    sceneConcept: '成年中国女性随车审计员独自站在透明背景前，黑色马尾、棕眼、长方眼镜；黑色商务西装、白衬衫、黑裤外罩一件无字橙色反光安全背心，双手抱住审计平板；严肃而克制，三分之四身，柔和均匀正面光。',
    tags: ['highres','1girl','solo','mature_female','black_hair','ponytail','brown_eyes','hair_behind_ear','glasses','rectangular_eyewear','business_suit','formal_clothes','suit','black_jacket','jacket','collared_shirt','white_shirt','long_sleeves','collar','necktie','black_pants','pants','belt','wristwatch','holding','tablet_pc','office_lady','serious','expressionless','closed_mouth','looking_at_viewer','standing','cowboy_shot','transparent_background','shadow','flat_color'],
    naturalLanguageDetail: 'An adult Chinese field auditor wears a plain orange reflective safety vest over a conservative black business suit and holds an unmarked audit tablet with both hands. She is an unarmed protection target with no logo, badge, readable text, or supernatural effect.',
    negativeAdditions: ['cleavage','midriff','weapon','gun']
  },
  {
    key: 'drone', characterId: 'EP03-EXTRA-DRONE', slug: 'extra-drone',
    sourceFacts: ['追风使用的警戒无人机模板；负责监控和警戒，不是武装炮艇。'],
    designAssumptions: ['紧凑白灰机身、蓝色识别块、四旋翼与中央摄像球。', '仅保留小型非致命接触探针，不出现枪炮、导弹或可读编号。'],
    sceneConcept: '一台紧凑的白灰色近未来交通警戒四旋翼无人机悬停在透明背景前，四个旋翼、蓝色识别块、中央摄像球和短小传感探针清楚可辨；高位三分之四前视角，轮廓紧凑，柔和均匀棚拍光，没有武器、文字或标志。',
    tags: ['highres','absurdres','no_humans','solo','drone','robot','vehicle_focus','quadcopter','propeller','rotor','camera','security_camera','machinery','science_fiction','industrial','circuit_board','flying','midair','floating','facing_viewer','from_above','blue_theme','white_theme','grey_theme','reflection','shiny','circle','surveillance','outline','simple_background','transparent_background','shadow','flat_color'],
    naturalLanguageDetail: 'A compact near-future traffic-monitoring quadcopter with four clearly separated rotors, a white-and-grey shell, restrained blue panels, one central camera ball, and one short nonlethal contact probe. Clean game-token silhouette; no human pilot, gun, cannon, missile, logo, readable text, or supernatural glow.',
    negativeAdditions: ['1girl','1boy','weapon','gun','holding_weapon']
  }
];

function writeJson(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, JSON.stringify(value, null, 2) + '\n', { flag: 'wx' });
}

const selectedTagEvidence = {};
for (const spec of definitions) {
  const actor = actorByKey.get(spec.key);
  if (!actor) throw new Error(`Missing source Actor entry: ${spec.key}`);
  spec.characterName = actor.name;
  spec.actorId = actor.actorId;
  if (new Set(spec.tags).size !== spec.tags.length) throw new Error(`Duplicate positive tag: ${spec.characterId}`);
  if (spec.key !== 'drone' && spec.tags.length < 35) throw new Error(`Human prompt under 35 tags: ${spec.characterId}`);
  for (const tag of [...spec.tags, ...commonNegative, ...spec.negativeAdditions]) {
    const evidence = priorPool[tag] ?? (refreshedTags[tag] ? { source: 'mcp_verified_20260904', category: 'general', count: refreshedTags[tag] } : null);
    if (!evidence || ('count' in evidence && !(evidence.count > 0))) throw new Error(`Unverified or zero-count tag: ${tag}`);
    selectedTagEvidence[tag] = evidence;
  }
}

const humanBasePrompt = profile.basePrompt;
const droneBasePrompt = profile.basePrompt
  .replace(', tachi-e', '')
  .replace(', cowboy shot', '')
  .replace(', 0.3::techwear::', '');

const batch = {
  schemaVersion: 1,
  createdAt,
  status: 'prepared',
  purpose: 'EP03 supporting NPC NovelAI candidates; vehicles excluded',
  userRequest: 'npc用nai过一遍',
  model: profile.model,
  profileSha256: sha(fs.readFileSync(profilePath)),
  actorManifestSha256: sha(fs.readFileSync(actorManifestPath)),
  characters: []
};

for (const spec of definitions) {
  const runId = `20260904-ep03-${spec.slug}-nai-v1`;
  const seed = crypto.createHash('sha256').update(runId).digest().readUInt32BE(0) & 0x7fffffff;
  const basePrompt = spec.key === 'drone' ? droneBasePrompt : humanBasePrompt;
  const negative = [...new Set([...commonNegative, ...spec.negativeAdditions])];
  const characterPrompt = `${spec.tags.map((tag) => tag.replaceAll('_', ' ')).join(', ')}. ${spec.naturalLanguageDetail}`;
  const negativePrompt = [profile.negativePrompt, ...negative.map((tag) => tag.replaceAll('_', ' '))].join(', ');
  const condition = (text, characterText, useOrder) => ({
    caption: { base_caption: text, char_captions: [{ char_caption: characterText, centers: [{ x: 0.5, y: 0.5 }] }] },
    use_coords: false,
    use_order: useOrder,
    legacy_uc: false
  });
  const request = {
    meta: {
      schemaVersion: 1, runId, characterId: spec.characterId, characterName: spec.characterName,
      actorId: spec.actorId, designStatus: 'provisional', designAssumptions: spec.designAssumptions,
      humanInitiated: true, humanInitiatedAt: createdAt,
      credentialPolicy: 'runtime-only; never logged'
    },
    payload: {
      action: 'generate', input: basePrompt, model: profile.model,
      parameters: {
        ...profile.parameters,
        seed,
        prompt: basePrompt,
        negative_prompt: negativePrompt,
        v4_prompt: condition(basePrompt, characterPrompt, true),
        v4_negative_prompt: condition(negativePrompt, '', false)
      }
    }
  };
  const runDir = path.join(output, 'runs', runId);
  writeJson(path.join(output, 'prompts', `${spec.characterId}.json`), {
    schemaVersion: 1, version: 1, designStatus: 'provisional', ...spec,
    seed, negativeAdditions: negative,
    sourceLocator: 'extras-vehicles-20260904/manifest.json and README.md'
  });
  writeJson(path.join(runDir, 'request.json'), request);
  writeJson(path.join(runDir, 'manifest.json'), {
    schemaVersion: 1, runId, characterId: spec.characterId, characterName: spec.characterName,
    actorId: spec.actorId, status: 'queued', requestFile: 'request.json', resultFile: null,
    rawAssets: [], candidateAsset: null,
    qa: { technical: 'pending', visual: 'pending', notes: [] }
  });
  batch.characters.push({
    characterId: spec.characterId, name: spec.characterName, actorId: spec.actorId,
    runId, seed, tagCount: spec.tags.length,
    requestSha256: sha(JSON.stringify(request)),
    requestFile: path.relative(output, path.join(runDir, 'request.json')).replaceAll('\\', '/')
  });
}

writeJson(path.join(output, 'control/verified-tags.json'), {
  schemaVersion: 1,
  verifiedAt: createdAt,
  policy: 'Every emitted positive and additional negative tag is backed by the prior EP03 MCP pool or refreshed Danbooru MCP evidence from 2026-09-04.',
  tags: selectedTagEvidence
});
writeJson(path.join(output, 'control/batch.json'), batch);
const prose = definitions.map((spec, index) => `### Prompt ${index + 1} — ${spec.characterName}\n\n\`${spec.tags.join(', ')}\`\n`).join('\n');
fs.mkdirSync(path.join(output, 'prompts'), { recursive: true });
fs.writeFileSync(path.join(output, 'prompts/prompts.md'), `# EP03 supporting NPC NAI prompts\n\nNAI Diffusion V5 Curated; existing portrait artist mix and negative preset retained.\n\n${prose}`, { flag: 'wx' });
console.log(JSON.stringify({ prepared: batch.characters, model: profile.model, dimensions: [profile.parameters.width, profile.parameters.height], steps: profile.parameters.steps, output }, null, 2));
