/**
 * generate_powers.js
 * 从奇能.json生成第五章：奇能 的所有Markdown文件
 */

const fs = require('fs');
const path = require('path');

const data = JSON.parse(fs.readFileSync(
  path.join(__dirname, '..', '奇能.json'), 'utf8'
));

// 四大流派名称映射（JSON字段名 → 新名称）
const arcaneKeys = {
  '塑躯 Biokinesis': '铸肉体',
  '超感 ESP': '开天眼',
  '念控 Psychokinesis': '意动法',
  '传心 Telepathy': '摄心术'
};

// 术语替换
function applyTerminology(text) {
  if (!text) return '';
  // 顺序很重要：先替换复合词，再替换单词
  text = text.replace(/奇术点/g, '奇能点');
  text = text.replace(/奇术限度/g, '奇能限度');
  text = text.replace(/奇术调整/g, '奇能调整');
  text = text.replace(/奇术类型/g, '奇能类型');
  text = text.replace(/超能奇术/g, '超能奇能');
  text = text.replace(/奇术/g, '奇能');
  text = text.replace(/塑躯者/g, '铸肉体者');
  text = text.replace(/塑躯\(bk\)/g, '铸肉体(bk)');
  text = text.replace(/塑躯/g, '铸肉体');
  text = text.replace(/超感者/g, '开天眼者');
  text = text.replace(/超感/g, '开天眼');
  text = text.replace(/念控者/g, '意动法者');
  text = text.replace(/念控\(pk\)/g, '意动法(pk)');
  text = text.replace(/念控/g, '意动法');
  text = text.replace(/传心者/g, '摄心术者');
  text = text.replace(/传心/g, '摄心术');
  return text;
}

// Wiki标记 → Markdown
function wikiToMd(text) {
  if (!text) return '';

  // 移除 \define 宏块
  text = text.replace(/\\define[\s\S]*?\\end\n?/g, '');

  // 移除HTML标签
  text = text.replace(/<div[^>]*>/g, '');
  text = text.replace(/<\/div>/g, '');
  text = text.replace(/<\$[^>]*\/>/g, '');
  text = text.replace(/<\$[^>]*>[\s\S]*?<\/\$[^>]*>/g, '');

  // 移除模板调用 {{...}}
  text = text.replace(/\{\{[^}]*\}\}/g, '');

  // 标题转换（必须在粗体转换前）
  text = text.replace(/^!!!![ ]*(.+)$/gm, '### $1');
  text = text.replace(/^!!![ ]*(.+)$/gm, '## $1');
  text = text.replace(/^!![ ]*(.+)$/gm, '# $1');

  // 粗体 ''text'' → **text**
  text = text.replace(/''/g, '**');

  // 移除 引用 标记行
  text = text.replace(/^引用\s*$/gm, '');

  // 移除表格行首的 > 引用标记
  text = text.replace(/^>\s*/gm, '');

  // 列表项 ' text → - text（行首）
  text = text.replace(/^' /gm, '- ');

  // 斜体 _text_ → *text*
  text = text.replace(/_([^_\n]{1,120})_/g, '*$1*');

  // 应用术语替换
  text = applyTerminology(text);

  // 清理多余空行
  text = text.replace(/\n{3,}/g, '\n\n');
  text = text.trim();

  return text;
}

// 创建目录
const baseDir = path.join(__dirname, '..', 'src', '核心规则', '奇能');
fs.mkdirSync(path.join(baseDir, '流派'), { recursive: true });
fs.mkdirSync(path.join(baseDir, '奇能列表'), { recursive: true });

// 分类条目
const powers = data.filter(d => d.tags === '奇术');
const adjustments = data.filter(d => d.tags === '奇术调整');
const arcaneIntros = data.filter(d =>
  !d.tags && Object.keys(arcaneKeys).includes(d.title)
);
const specialEdges = data.filter(d =>
  d.tags && d.tags.includes('专长') && !d.tags.includes('奇术')
);
const hindrances = data.filter(d =>
  d.tags && d.tags.includes('负赘') && !d.tags.includes('奇术')
);

console.log(`奇能: ${powers.length}, 调整: ${adjustments.length}, 流派: ${arcaneIntros.length}`);

// ─── 生成各字母奇能页面 ──────────────────────────────────────

// 按英文名首字母分组
const byLetter = {};
for (const power of powers) {
  const eng = (power['英文名'] || '').trim();
  const letter = (eng[0] || 'Z').toUpperCase();
  if (!byLetter[letter]) byLetter[letter] = [];
  byLetter[letter].push(power);
}

// 每组内按英文名排序
for (const letter in byLetter) {
  byLetter[letter].sort((a, b) =>
    (a['英文名'] || '').localeCompare(b['英文名'] || '', 'en')
  );
}

// 构建单个奇能的内容块
function powerBlock(power) {
  let content = '';

  const rawTitle = power.title || '';
  const title = applyTerminology(rawTitle);
  content += `## ${title}\n\n`;

  // 正文
  const mainText = wikiToMd(power.text);
  content += mainText + '\n\n';

  // 流派特效表（只在有非空值时展示）
  const effects = Object.entries(arcaneKeys)
    .filter(([oldKey]) => power[oldKey] !== undefined)
    .map(([oldKey, newName]) => ({
      name: newName,
      effect: power[oldKey] ? applyTerminology(power[oldKey]) : '—'
    }));

  if (effects.length > 0) {
    content += '> **流派特效**\n>\n';
    for (const { name, effect } of effects) {
      content += `> **${name}：** ${effect}\n>\n`;
    }
    content += '\n';
  }

  return content;
}

// 生成字母页
for (const [letter, lPowers] of Object.entries(byLetter)) {
  let content = `---\ntitle: "奇能列表 · ${letter}"\n---\n\n`;
  content += `# 奇能列表 · ${letter}\n\n`;

  for (const power of lPowers) {
    content += powerBlock(power);
    content += '---\n\n';
  }

  const file = path.join(baseDir, '奇能列表', `${letter}.md`);
  fs.writeFileSync(file, content, 'utf8');
  console.log('OK:', file.replace(process.cwd(), '.'));
}

// 生成奇能列表索引
const sortedLetters = Object.keys(byLetter).sort();
let listIndex = `---\ntitle: "奇能列表"\n---\n\n# 奇能列表\n\n`;
listIndex += '按英文名首字母排列。\n\n';
for (const letter of sortedLetters) {
  listIndex += `## ${letter}\n\n`;
  for (const p of byLetter[letter]) {
    listIndex += `- [${applyTerminology(p.title)}](./${letter}#${(p['英文名'] || '').toLowerCase().replace(/[^a-z]/g, '-')})\n`;
  }
  listIndex += '\n';
}
fs.writeFileSync(path.join(baseDir, '奇能列表', 'index.md'), listIndex, 'utf8');
console.log('OK: 奇能列表/index.md');

// ─── 生成四大流派页面 ──────────────────────────────────────

for (const [oldKey, newName] of Object.entries(arcaneKeys)) {
  const intro = arcaneIntros.find(d => d.title === oldKey);
  const introText = intro ? wikiToMd(intro.text) : '';

  // 该流派推荐的奇能（JSON中有该流派字段的）
  const recPowers = powers
    .filter(p => p[oldKey] !== undefined)
    .sort((a, b) => (a['英文名'] || '').localeCompare(b['英文名'] || '', 'en'));

  let content = `---\ntitle: "${newName}"\n---\n\n`;
  content += `# ${newName}\n\n`;
  content += introText + '\n\n';

  content += '## 推荐奇能\n\n';
  content += '| 奇能 | 流派特效 |\n';
  content += '|------|----------|\n';
  for (const p of recPowers) {
    const pTitle = applyTerminology(p.title);
    const effect = p[oldKey] ? applyTerminology(p[oldKey]) : '—';
    content += `| ${pTitle} | ${effect} |\n`;
  }
  content += '\n';

  const file = path.join(baseDir, '流派', `${newName}.md`);
  fs.writeFileSync(file, content, 'utf8');
  console.log('OK:', file.replace(process.cwd(), '.'));
}

// 生成流派索引
let arcaneIdx = `---\ntitle: "四大流派"\n---\n\n# 四大流派\n\n`;
arcaneIdx += `在龙散市，异能者根据遗传标记划分为四大流派，每名异能者只能归属其一（除非具备[双重秉赋](../专长与负赘#双重秉赋-double-gifted)专长）。\n\n`;
for (const newName of Object.values(arcaneKeys)) {
  arcaneIdx += `- [**${newName}**](./${newName})\n`;
}
arcaneIdx += '\n';
fs.writeFileSync(path.join(baseDir, '流派', 'index.md'), arcaneIdx, 'utf8');
console.log('OK: 流派/index.md');

// ─── 生成奇能调整页面 ──────────────────────────────────────

const sortedAdj = [...adjustments].sort((a, b) =>
  (a['英文名'] || '').localeCompare(b['英文名'] || '', 'en')
);

let adjPage = `---\ntitle: "奇能调整"\n---\n\n# 奇能调整 Power Modifications\n\n`;
adjPage += `以下调整可以附加到具体奇能上，用于拓展或限制其效果。每项调整的费用标注于名称后的括号中（正数为增加奇能点消耗，负数为减少）。\n\n`;

for (const adj of sortedAdj) {
  const title = applyTerminology(adj.title);
  adjPage += `## ${title}\n\n`;
  adjPage += wikiToMd(adj.text) + '\n\n';
  adjPage += '---\n\n';
}

fs.writeFileSync(path.join(baseDir, '奇能调整.md'), adjPage, 'utf8');
console.log('OK: 奇能调整.md');

// ─── 生成专长与负赘页面 ──────────────────────────────────────

let edgePage = `---\ntitle: "奇能专长与负赘"\n---\n\n# 奇能专长与负赘\n\n`;
edgePage += `## 相关专长\n\n`;

for (const edge of specialEdges) {
  const title = applyTerminology(edge.title);
  edgePage += `### ${title}\n\n`;
  edgePage += wikiToMd(edge.text) + '\n\n';
  edgePage += '---\n\n';
}

edgePage += `## 相关负赘\n\n`;

for (const h of hindrances) {
  const title = applyTerminology(h.title);
  const isMinor = h.tags.includes('次要');
  const isMajor = h.tags.includes('主要');
  const grade = isMajor && isMinor ? '次要/主要' : isMajor ? '主要' : '次要';
  edgePage += `### ${title} *(${grade})*\n\n`;
  edgePage += wikiToMd(h.text) + '\n\n';
  edgePage += '---\n\n';
}

fs.writeFileSync(path.join(baseDir, '专长与负赘.md'), edgePage, 'utf8');
console.log('OK: 专长与负赘.md');

// ─── 生成章节首页 index.md ──────────────────────────────────────

const sysRulesEntry = data.find(d => d.title === '奇术 Powers');
const superPowersEntry = data.find(d => d.title === '超能奇术 Super Powers');

let indexContent = `---\ntitle: "第五章：奇能"\n---\n\n# 第五章：奇能\n\n`;

if (sysRulesEntry) {
  indexContent += wikiToMd(sysRulesEntry.text) + '\n\n';
}

if (superPowersEntry) {
  indexContent += '## 超能奇能 Super Powers\n\n';
  indexContent += wikiToMd(superPowersEntry.text) + '\n\n';
}

// 集中技能条目
const focusEntry = data.find(d => d.title === '集中 Focus');
if (focusEntry) {
  indexContent += '## 集中 Focus\n\n';
  indexContent += wikiToMd(focusEntry.text) + '\n\n';
}

fs.writeFileSync(path.join(baseDir, 'index.md'), indexContent, 'utf8');
console.log('OK: index.md');

// ─── 统计 ──────────────────────────────────────

console.log('\n=== 生成完毕 ===');
console.log(`字母页: ${Object.keys(byLetter).length} 个`);
console.log(`流派页: ${Object.keys(arcaneKeys).length} 个 + 1 索引`);
console.log('调整页: 1 个');
console.log('专长与负赘页: 1 个');
console.log('章节首页: 1 个');
console.log('奇能列表索引: 1 个');
