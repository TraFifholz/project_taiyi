import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const root = process.cwd();
const production = path.join(root, 'discussion/npc/立绘生产');
const output = path.join(root, 'records/prep/ep03-fvtt-20260903/portraits');
const profilePath = path.join(production, 'control/api-profile.json');
const profile = JSON.parse(fs.readFileSync(profilePath, 'utf8'));
const masterPath = path.join(production, 'control/portrait-master.json');
const master = JSON.parse(fs.readFileSync(masterPath, 'utf8'));
const pool = JSON.parse(fs.readFileSync(path.join(output, 'control/verified-tags.json'), 'utf8')).tags;
const reference = JSON.parse(fs.readFileSync(path.join(production, 'control/reference-manifest.json'), 'utf8'));
const sha = value => crypto.createHash('sha256').update(value).digest('hex');
const sourcePath = path.join(root, 'records/prep/ep03-fvtt-20260903/module-before.md');
const source = fs.readFileSync(sourcePath, 'utf8');
const date = new Date().toISOString();
const commonNegative = ['watermark', 'signature', 'character_name', 'english_text', 'chinese_text', 'logo', 'emblem', 'badge', 'text_focus', 'hologram', 'heads-up_display', 'glowing', 'aura', 'light_particles', 'child', 'school_uniform', 'weapon', 'gun'];
const definitions = [
  {
    characterId: 'EP03-LUO-KAI', characterName: '罗恺', actorId: 'f5cd5bab755a2027', slug: 'luo-kai',
    sourceFacts: ['42岁，穗安合规服务设备回收主管。', '带四名清理员，伪装成追风维修人员，为方泰安执行清理任务。'],
    designAssumptions: ['短黑发、两鬓少量灰发、棕眼，脸形瘦长，神情克制。', '灰色维修夹克配白衬衫、黑工装裤、手套和普通通讯耳机；持维修平板。'],
    sceneConcept: '一名42岁的中国男性维修主管独自站在透明背景前；短黑发两鬓泛灰，脸部有中年感，目光平直冷静；灰色工作夹克下穿白衬衫，黑工装裤与工具腰带，一手托住维修平板、另一只戴手套的手停在平板边缘；三分之四身构图，均匀柔和的正面工作室光，仅保留自然衣褶阴影。',
    tags: ['highres', '1boy', 'solo', 'male_focus', 'mature_male', 'short_hair', 'black_hair', 'grey_hair', 'multicolored_hair', 'brown_eyes', 'swept_bangs', 'grey_jacket', 'jacket', 'collared_shirt', 'white_shirt', 'long_sleeves', 'collar', 'zipper', 'pocket', 'black_pants', 'cargo_pants', 'belt', 'utility_belt', 'pouch', 'black_gloves', 'gloves', 'wristwatch', 'earpiece', 'holding', 'tablet_pc', 'expressionless', 'serious', 'closed_mouth', 'looking_at_viewer', 'standing', 'transparent_background', 'shadow', 'flat_color'],
    naturalLanguageDetail: 'A composed forty-two-year-old Chinese equipment recovery supervisor with a long mature face and greying temples wears a plain grey maintenance jacket over a white collared shirt and holds a rugged tablet at his waist, shown from head to mid-thigh under soft even frontal studio light.',
    negativeAdditions: ['facial_hair', 'muscular_male']
  },
  {
    characterId: 'EP03-XIN-HUA', characterName: '辛桦', actorId: '57cb77448d90157a', slug: 'xin-hua',
    sourceFacts: ['30岁上下的女性，棍木会青梢队领队。', '负责驾驶、抢芯片与谈判；注重队员安全，不主动攻击乘客。'],
    designAssumptions: ['短棕发、棕眼、利落结实的成年人形象，带克制的自信笑意。', '深绿飞行夹克、灰色高领内搭、黑工装裤、半指手套与普通耳机，手提摩托头盔。'],
    sceneConcept: '一名约30岁的中国女性街面领队独自站在透明背景前；短棕发向侧面梳开，棕眼，表情自信而警觉；深绿飞行夹克配灰色高领内搭、黑工装裤和半指手套，一手叉腰，另一手提着普通摩托头盔垂在大腿旁；三分之四身构图，均匀柔和正面光，不出现能力特效。',
    tags: ['highres', '1girl', 'solo', 'mature_female', 'short_hair', 'brown_hair', 'brown_eyes', 'swept_bangs', 'hair_behind_ear', 'green_jacket', 'bomber_jacket', 'high_collar', 'grey_shirt', 'long_sleeves', 'zipper', 'pocket', 'black_pants', 'cargo_pants', 'belt', 'utility_belt', 'pouch', 'fingerless_gloves', 'black_gloves', 'earpiece', 'boots', 'holding', 'helmet', 'motorcycle_helmet', 'hand_on_own_hip', 'smirk', 'closed_mouth', 'looking_at_viewer', 'standing', 'transparent_background', 'shadow', 'flat_color'],
    naturalLanguageDetail: 'A practical thirty-year-old Chinese woman street crew leader in a dark forest-green bomber jacket and a fully covered grey high-collar shirt rests one hand on her hip and holds a plain motorcycle helmet beside her thigh with the other hand, shown from head to mid-thigh under soft even frontal studio light.',
    negativeAdditions: ['cleavage', 'midriff']
  },
  {
    characterId: 'EP03-XIA-LEI', characterName: '夏磊', actorId: 'f0767585fdbe1cf3', slug: 'xia-lei',
    sourceFacts: ['33岁，追风旧城调度中心前员工。', '曾帮助司机整理申诉材料而被解雇；真诚但误信匿名情报。'],
    designAssumptions: ['短而略乱的黑发、棕眼、细框长方眼镜，略显疲惫，身形偏瘦。', '旧蓝色夹克、普通灰T恤、黑裤、棕色单肩包；双手抱着合上的旧笔记本电脑。'],
    sceneConcept: '一名33岁的中国男性前调度员独自站在透明背景前；短黑发略乱，戴长方眼镜，眼下有淡淡倦色，紧张但愿意帮助别人；旧蓝夹克敞开露出灰T恤，黑裤与棕色单肩包，微微缩肩，用双手把合上的旧笔记本电脑抱在腹前；三分之四身构图，柔和均匀正面光，保留自然浅阴影。',
    tags: ['highres', '1boy', 'solo', 'male_focus', 'mature_male', 'short_hair', 'black_hair', 'messy_hair', 'brown_eyes', 'glasses', 'rectangular_eyewear', 'black-framed_eyewear', 'bags_under_eyes', 'blue_jacket', 'jacket', 'open_jacket', 'grey_shirt', 'shirt', 'long_sleeves', 'zipper', 'pocket', 'black_pants', 'pants', 'belt', 'shoulder_bag', 'brown_bag', 'bag', 'strap', 'laptop', 'holding', 'nervous_smile', 'smile', 'closed_mouth', 'looking_at_viewer', 'standing', 'hunched_over', 'transparent_background', 'shadow', 'flat_color'],
    naturalLanguageDetail: 'A tired but sincere thirty-three-year-old Chinese former dispatch clerk with a lean build and rectangular glasses wears a faded blue jacket and a plain grey T-shirt, slightly hunching his shoulders while holding a closed worn laptop against his abdomen with both hands, shown from head to mid-thigh under soft even frontal studio light.',
    negativeAdditions: ['facial_hair', 'muscular_male']
  }
];
function writeJson(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, JSON.stringify(value, null, 2) + '\n', { flag: 'wx' });
}
const batch = {
  schemaVersion: 1, createdAt: date, status: 'prepared', purpose: 'EP03专用NPC头像候选；非城市正式立绘采用',
  userRequest: '用nai生成一下头像',
  model: profile.model, masterUnchangedSha256: sha(fs.readFileSync(masterPath)), profileSha256: sha(fs.readFileSync(profilePath)),
  sourceFile: sourcePath, sourceSha256: sha(fs.readFileSync(sourcePath)), characters: []
};
for (const spec of definitions) {
  if (!source.includes(`### ${spec.characterName}`)) throw new Error(`Not in original module: ${spec.characterName}`);
  if (master.characters.some(c => c.id === spec.characterId || c.name === spec.characterName)) throw new Error(`Already in formal portrait control: ${spec.characterName}`);
  const negative = [...new Set([...commonNegative, ...spec.negativeAdditions])];
  for (const tag of [...spec.tags, ...negative]) if (!pool[tag] || !(pool[tag].count > 0)) throw new Error(`Unverified tag: ${tag}`);
  for (const tag of profile.negativePrompt.split(', ').map(t => t.replaceAll(' ', '_'))) if (!pool[tag]) throw new Error(`Missing inherited negative evidence: ${tag}`);
  if (new Set(spec.tags).size !== spec.tags.length || spec.tags.length < 35) throw new Error('Tag coverage/duplicate error');
  const runId = `20260903-ep03-${spec.slug}-v1`;
  const seed = crypto.createHash('sha256').update(runId).digest().readUInt32BE(0) & 0x7fffffff;
  const promptSpec = { schemaVersion: 1, version: 1, designStatus: 'provisional', ...spec, negativeAdditions: negative, seed, sourceLocator: 'records/prep/ep03-fvtt-20260903/module-before.md 人物章节' };
  const characterPrompt = spec.tags.map(t => t.replaceAll('_', ' ')).join(', ') + '. ' + spec.naturalLanguageDetail;
  const negativePrompt = [profile.negativePrompt, ...negative.map(t => t.replaceAll('_', ' '))].join(', ');
  const condition = text => ({ caption: { base_caption: text, char_captions: [{ char_caption: text === profile.basePrompt ? characterPrompt : '', centers: [{ x: 0.5, y: 0.5 }] }] }, use_coords: false, use_order: text === profile.basePrompt, legacy_uc: false });
  const request = {
    meta: { schemaVersion: 1, runId, characterId: spec.characterId, characterName: spec.characterName, actorId: spec.actorId, designStatus: 'provisional', designAssumptions: spec.designAssumptions, humanInitiated: true, humanInitiatedAt: date, templateUse: 'metadata-import-only', templateSha256: reference.sha256, credentialPolicy: 'runtime-only; never logged' },
    payload: { action: 'generate', input: profile.basePrompt, model: profile.model, parameters: { ...profile.parameters, seed, prompt: profile.basePrompt, negative_prompt: negativePrompt, v4_prompt: condition(profile.basePrompt), v4_negative_prompt: condition(negativePrompt) } }
  };
  const runDir = path.join(output, 'runs', runId);
  writeJson(path.join(output, 'prompts', spec.characterId + '.json'), promptSpec);
  writeJson(path.join(runDir, 'request.json'), request);
  writeJson(path.join(runDir, 'manifest.json'), { schemaVersion: 1, runId, characterId: spec.characterId, characterName: spec.characterName, designStatus: 'provisional', status: 'queued', requestFile: 'request.json', resultFile: null, rawAssets: [], candidateAsset: null, qa: { technical: 'pending', visual: 'pending', notes: [] } });
  batch.characters.push({ characterId: spec.characterId, name: spec.characterName, actorId: spec.actorId, runId, seed, tags: spec.tags.length, requestSha256: sha(JSON.stringify(request)), requestFile: path.relative(output, path.join(runDir, 'request.json')).replaceAll('\\', '/') });
}
writeJson(path.join(output, 'control/batch.json'), batch);
const prose = definitions.map((spec, i) => `### Prompt ${i + 1} — ${spec.characterName}\n\n\`${spec.tags.join(', ')}\`\n\n${spec.naturalLanguageDetail}\n`).join('\n');
fs.writeFileSync(path.join(output, 'prompts/prompts.md'), '# EP03 NAI 头像候选提示词\n\n固定画风与负面预设原样沿用项目；完整参数见各 run/request.json。\n\n' + prose, { flag: 'wx' });
console.log(JSON.stringify({ prepared: batch.characters, model: profile.model, dimensions: [profile.parameters.width, profile.parameters.height], steps: profile.parameters.steps, formalControlUnchanged: sha(fs.readFileSync(masterPath)) === batch.masterUnchangedSha256 }, null, 2));
