const fs = require('fs');
const path = require('path');

const data = JSON.parse(fs.readFileSync('./Tiddlywiki.json', 'utf8'));
console.log(`Loaded ${data.length} entries`);

// Build parent-child relationship
const hasChildren = new Set();
for (const entry of data) {
  const parts = entry.title.split('/');
  for (let i = 1; i < parts.length; i++) {
    hasChildren.add(parts.slice(0, i + 1).join('/'));
  }
}

function isCategory(title) {
  return hasChildren.has(title);
}

console.log(`Category pages (have children): ${data.filter(e => isCategory(e.title)).length}`);
console.log(`Leaf pages: ${data.filter(e => !isCategory(e.title)).length}`);

const outputDir = './src';

function getOutputPath(title) {
  if (isCategory(title)) {
    return path.join(outputDir, ...title.split('/'), 'index.md');
  }
  return path.join(outputDir, title + '.md');
}

// Create all needed directories
const dirs = new Set();
for (const entry of data) {
  const out = getOutputPath(entry.title);
  dirs.add(path.dirname(out));
}
for (const dir of dirs) {
  fs.mkdirSync(dir, { recursive: true });
}
console.log(`Created ${dirs.size} directories`);

// Compute relative link from one page to another
function relativeLink(fromTitle, toTitle) {
  const fromParts = fromTitle.split('/');
  const toParts = toTitle.split('/');
  let i = 0;
  while (i < fromParts.length && i < toParts.length && fromParts[i] === toParts[i]) {
    i++;
  }
  const upLevels = fromParts.length - i;
  const downParts = toParts.slice(i);
  let rel = upLevels === 0 ? './' : '../'.repeat(upLevels);
  if (downParts.length > 0) {
    rel += downParts.join('/') + '/';
  }
  return rel;
}

function convertText(text, sourceTitle) {
  let result = text;

  // 1. Remove all <div ...> and </div> tags
  result = result.replace(/<div[^>]*>/gi, '');
  result = result.replace(/<\/div>/gi, '');

  // 2. Handle <<< blockquotes: split, prefix odd sections with >
  const parts = result.split('<<<');
  result = parts.map((part, i) => {
    if (i % 2 === 0) return part;       // outside quote
    return part.split('\n').map(line => line.startsWith('>') ? line : '> ' + line).join('\n');  // inside quote
  }).join('');

  // 3. Headings: TW !..! → MD #..#
  // Must process more bangs first to avoid partial matches
  result = result.replace(/^!!!!\s?/gm, '#### ');
  result = result.replace(/^!!!\s?/gm, '### ');
  result = result.replace(/^!!\s?/gm, '## ');
  result = result.replace(/^!\s?/gm, '# ');
  // Also handle headings inside blockquotes
  result = result.replace(/^> !!!!\s?/gm, '> #### ');
  result = result.replace(/^> !!!\s?/gm, '> ### ');
  result = result.replace(/^> !!\s?/gm, '> ## ');
  result = result.replace(/^> !\s?/gm, '> # ');

  // 4. Bold/italic: ''text'' → **text**
  result = result.replace(/''(.+?)''/g, '**$1**');

  // 5. Wiki links: [[display|path]] → [display](relative/path/)
  result = result.replace(/\[\[([^\]|]+)\|([^\]]+)\]\]/g, (match, display, target) => {
    const rel = relativeLink(sourceTitle, target);
    return `[${display}](${rel})`;
  });

  // 6. Wiki links: [[path]] → [path](relative/path/) (simple, no pipe)
  result = result.replace(/\[\[([^\]]+)\]\]/g, (match, inner) => {
    if (inner.includes('|')) return match;
    const rel = relativeLink(sourceTitle, inner);
    return `[${inner}](${rel})`;
  });

  // 7. <<mylist "filter">> → TODO placeholder
  result = result.replace(/<<mylist\s+"([^"]+)"\s*>>/g, '<!-- TODO: mylist "$1" -->');

  // 8. Lists: TW * → MD - (only at line start)
  result = result.replace(/^\* /gm, '- ');

  // 9. Numbered lists: TW # → MD 1. (only at line start)
  result = result.replace(/^# /gm, '1. ');

  // 10. Remove self-closing TW widget tags: <$macrocall ... />, <$action-setfield ... />
  result = result.replace(/<\$[\w-]+[^>]*\/>/g, '');

  // 11. Remove TW widget opening and closing tags (keep inner content)
  result = result.replace(/<\/?\$[\w-]+[^>]*>/g, '');

  // 12. Escape Vue template interpolation: {{ }} -> HTML entities
  result = result.replace(/\{\{/g, '&#123;&#123;');
  result = result.replace(/\}\}/g, '&#125;&#125;');

  // 13. Handle HTML list tags: strip tags, convert </li> to <br> for table cell separation
  result = result.replace(/<ul>/gi, '');
  result = result.replace(/<\/ul>/gi, '');
  result = result.replace(/<ol[^>]*>/gi, '');
  result = result.replace(/<\/ol>/gi, '');
  result = result.replace(/<li>/gi, '');
  result = result.replace(/<\/li>/gi, '<br>');

  return result;
}

let mylistCount = 0;
const mylistLocations = [];

// Entries to exclude from individual file generation (consolidated later)
function isConsolidated(title) {
  const parts = title.split('/');
  // Individual 专长 entries: 核心规则/专长/XXX and beyond (depth >= 3)
  if (parts.length >= 3 && parts[1] === '专长') return true;
  // Individual 负赘 entries: 核心规则/负赘/XXX and beyond (depth >= 3)
  if (parts.length >= 3 && parts[1] === '负赘') return true;
  return false;
}

// Entries to skip entirely (bestiary — deleted)
function isSkipped(title) {
  const parts = title.split('/');
  if (parts.length >= 2) {
    if (parts[1] === '生物列表') return true;
    if (parts[1] === '生物图鉴') return true;
    if (parts[1] === '特殊能力') return true;
    // Skip state summaries page (moved under 主持游戏)
    if (title === '核心规则/状态速查') return true;
  }
  return false;
}

const consolidatedEntries = [];
const normalEntries = [];
let skippedCount = 0;

for (const entry of data) {
  if (isSkipped(entry.title)) {
    skippedCount++;
  } else if (isConsolidated(entry.title)) {
    consolidatedEntries.push(entry);
  } else {
    normalEntries.push(entry);
  }
}

console.log(`Skipped ${skippedCount} entries (bestiary, etc.)`);

for (const entry of normalEntries) {
  const outPath = getOutputPath(entry.title);
  const converted = convertText(entry.text, entry.title);

  // Count mylist placeholders for report
  const mylists = converted.match(/<!-- TODO: mylist/g);
  if (mylists) {
    mylistCount += mylists.length;
    mylistLocations.push({ title: entry.title, count: mylists.length });
  }

  const frontmatter = [
    '---',
    `title: ${JSON.stringify(entry['中文名'] || entry.title.split('/').pop())}`,
    entry['英文名'] ? `title_en: ${JSON.stringify(entry['英文名'])}` : '',
    `original: ${JSON.stringify(entry.title)}`,
    '---',
  ].filter(line => line !== '').join('\n');

  fs.writeFileSync(outPath, frontmatter + '\n\n' + converted.trim() + '\n', 'utf8');
}

console.log(`Wrote ${normalEntries.length} individual files, ${consolidatedEntries.length} to consolidate`);

// ---- Consolidation: 专长 by type, 负赘 into single pages ----

// Group 专长 by 专长类型
const edgeTypeGroups = {};
const hindranceEntries = [];
for (const e of consolidatedEntries) {
  if (e.title.startsWith('核心规则/专长/')) {
    const type = e['专长类型'] || '其他专长';
    if (!edgeTypeGroups[type]) edgeTypeGroups[type] = [];
    edgeTypeGroups[type].push(e);
  } else if (e.title.startsWith('核心规则/负赘/')) {
    hindranceEntries.push(e);
  }
}

// Write consolidated 专长 type pages
const edgeDir = path.join(outputDir, '核心规则', '专长');
for (const [typeName, entries] of Object.entries(edgeTypeGroups)) {
  entries.sort((a, b) => (a['英文名'] || '').localeCompare(b['英文名'] || ''));
  const typeSlug = typeName.replace(/ /g, '_');
  const outPath = path.join(edgeDir, `${typeSlug}.md`);

  let body = `# ${typeName}\n\n`;
  for (const e of entries) {
    const converted = convertText(e.text, e.title);
    body += `## ${e['中文名'] || e.title.split('/').pop()}\n\n`;
    if (e['英文名']) body += `**英文名：** ${e['英文名']}\n\n`;
    body += converted + '\n\n---\n\n';
  }

  const fm = [
    '---',
    `title: ${JSON.stringify(typeName)}`,
    '---',
  ].join('\n');
  fs.writeFileSync(outPath, fm + '\n\n' + body, 'utf8');
  console.log(`  ${typeName}: ${entries.length} edges → 专长/${typeSlug}.md`);
}

// Write consolidated 负赘 page
hindranceEntries.sort((a, b) => (a['英文名'] || '').localeCompare(b['英文名'] || ''));
let hBody = `# 负赘 Hindrances\n\n`;
for (const e of hindranceEntries) {
  const converted = convertText(e.text, e.title);
  const isMajor = e.text.includes('主要负赘') || e.text.includes('Major');
  hBody += `## ${e['中文名'] || e.title.split('/').pop()}\n\n`;
  if (e['英文名']) hBody += `**英文名：** ${e['英文名']}\n\n`;
  hBody += `_${isMajor ? '主要负赘 Major' : '次要负赘 Minor'}_\n\n`;
  hBody += converted + '\n\n---\n\n';
}
const hPath = path.join(outputDir, '核心规则', '负赘.md');
const hFm = ['---', 'title: "负赘"', 'title_en: "Hindrances"', '---'].join('\n');
fs.writeFileSync(hPath, hFm + '\n\n' + hBody, 'utf8');
console.log(`  Hindrances: ${hindranceEntries.length} entries → 核心规则/负赘.md`);

// Remove old individual directories
const { execSync } = require('child_process');
function safeRemove(dir) {
  if (fs.existsSync(dir)) {
    try { execSync(`rm -rf "${dir}"`, { stdio: 'pipe' }); } catch (e) {}
  }
}
for (const e of consolidatedEntries) {
  safeRemove(path.join(outputDir, e.title));
}
// Also clean up dirs that were parent containers
safeRemove(path.join(outputDir, '核心规则', '负赘', '详述'));
safeRemove(path.join(outputDir, '核心规则', '专长', '详述'));

console.log(`Wrote ${normalEntries.length} normal + ${Object.keys(edgeTypeGroups).length} edge-type + 1 hindrance = ${normalEntries.length + Object.keys(edgeTypeGroups).length + 1} files`);
console.log(`<<mylist>> placeholders: ${mylistCount} in ${mylistLocations.length} files`);
if (mylistLocations.length > 0) {
  console.log('Locations:');
  mylistLocations.forEach(l => console.log(`  ${l.title} (${l.count})`));
}

// Find directories without a matching entry
const entryTitles = new Set(data.map(e => e.title));
const dirsNeedingIndex = [];

for (const dir of dirs) {
  const relPath = path.relative(outputDir, dir);
  if (!relPath) continue; // skip root src/
  const normalized = relPath.replace(/\\/g, '/');
  if (!entryTitles.has(normalized)) {
    dirsNeedingIndex.push(normalized);
  }
}

for (const dirRel of dirsNeedingIndex) {
  const dirName = dirRel.split('/').pop();
  const dirAbs = path.join(outputDir, dirRel);
  const childNames = [];

  if (fs.existsSync(dirAbs)) {
    const dirents = fs.readdirSync(dirAbs, { withFileTypes: true });

    // Subdirectories first
    const childDirs = dirents
      .filter(d => d.isDirectory())
      .map(d => d.name)
      .sort();

    // Then .md files (excluding index.md)
    const childFiles = dirents
      .filter(d => d.isFile() && d.name.endsWith('.md') && d.name !== 'index.md')
      .map(f => f.name.replace('.md', ''))
      .sort();

    childNames.push(...childDirs, ...childFiles);
  }

  const links = childNames
    .map(name => `- [${name}](./${name}/)`)
    .join('\n');

  const content = [
    '---',
    `title: ${JSON.stringify(dirName)}`,
    '---',
    '',
    `# ${dirName}`,
    '',
    links || '_暂无子页面_',
    '',
  ].join('\n');

  const indexPath = path.join(outputDir, dirRel, 'index.md');
  fs.writeFileSync(indexPath, content, 'utf8');
}

console.log(`Generated ${dirsNeedingIndex.length} auto-index pages`);

// ============================================================
// Sidebar generation — chapter-based structure
// ============================================================

// Map title to 中文名 for display names
const titleToName = {};
for (const entry of data) {
  if (entry['中文名']) titleToName[entry.title] = entry['中文名'];
}

function getDisplayName(pageTitle) {
  return titleToName[pageTitle] || pageTitle.split('/').pop();
}

// Recursively build sidebar items from filesystem (for sub-pages)
function buildChildItems(absPath, urlBase, depth = 0) {
  if (!fs.existsSync(absPath)) return [];
  const entries = fs.readdirSync(absPath, { withFileTypes: true });
  const items = [];

  const dirs = entries
    .filter(e => e.isDirectory())
    .sort((a, b) => a.name.localeCompare(b.name, 'zh-CN'));

  for (const d of dirs) {
    const childPath = path.join(absPath, d.name);
    const childUrl = `${urlBase}/${d.name}`;
    const childItems = buildChildItems(childPath, childUrl, depth + 1);
    items.push({
      text: getPageName(`${urlBase.replace(/^\//, '').replace(/\//g, '/')}/${d.name}`),
      collapsed: true,
      items: childItems.length > 0 ? childItems : undefined,
      link: childItems.length === 0 ? `${childUrl}/` : undefined,
    });
  }

  const files = entries
    .filter(e => e.isFile() && e.name.endsWith('.md') && e.name !== 'index.md')
    .sort((a, b) => a.name.localeCompare(b.name, 'zh-CN'));

  for (const f of files) {
    const name = f.name.replace('.md', '');
    items.push({ text: name, link: `${urlBase}/${name}` });
  }

  return items;
}

function getPageName(pagePath) {
  return titleToName[pagePath] || pagePath.split('/').pop();
}

// Sidebar chapter structure (manually curated)
const chapters = [
  {
    group: '第一章：角色',
    key: '/核心规则/角色/',
    entries: [
      { text: '负赘', title: '核心规则/负赘' },
      { text: '特性', title: '核心规则/特性' },
      { text: '专长', title: '核心规则/专长' },
      { text: '升级', title: '核心规则/升级' },
    ]
  },
  {
    group: '第二章：装备',
    key: '/核心规则/装备/',
    entries: [
      { text: '普通装备', title: '核心规则/普通装备' },
      { text: '护甲', title: '核心规则/护甲' },
      { text: '单兵武器', title: '核心规则/单兵武器' },
      { text: '现代火器', title: '核心规则/现代火器' },
      { text: '特殊武器', title: '核心规则/特殊武器' },
      { text: '载具', title: '核心规则/载具' },
    ]
  },
  {
    group: '第三章：规则',
    key: '/核心规则/规则/',
    entries: [
      { text: '不羁角色与龙套们', title: '核心规则/不羁角色与龙套们' },
      { text: '特性投骰', title: '核心规则/特性投骰' },
      { text: '助力点', title: '核心规则/助力点' },
      { text: '战斗', title: '核心规则/战斗' },
      { text: '治疗', title: '核心规则/治疗' },
      { text: '情景规则', title: '核心规则/情景规则' },
      { text: '体型表', title: '核心规则/体型表' },
    ]
  },
  {
    group: '第四章：冒险工具箱',
    key: '/核心规则/冒险工具箱/',
    entries: [
      { text: '盟友', title: '核心规则/冒险工具箱/盟友' },
      { text: '追逐与载具', title: '核心规则/冒险工具箱/追逐与载具' },
      { text: '剧情任务', title: '核心规则/冒险工具箱/剧情任务' },
      { text: '恐惧', title: '核心规则/冒险工具箱/恐惧' },
      { text: '危难', title: '核心规则/冒险工具箱/危难' },
      { text: '幕间', title: '核心规则/冒险工具箱/幕间' },
      { text: '大规模作战', title: '核心规则/冒险工具箱/大规模作战' },
      { text: '打点关系', title: '核心规则/冒险工具箱/打点关系' },
      { text: '快速遭遇', title: '核心规则/冒险工具箱/快速遭遇' },
      { text: '设定规则', title: '核心规则/冒险工具箱/设定规则' },
      { text: '社交冲突', title: '核心规则/冒险工具箱/社交冲突' },
      { text: '旅行', title: '核心规则/冒险工具箱/旅行' },
      { text: '财富', title: '核心规则/冒险工具箱/财富' },
    ]
  },
  {
    group: '第五章：奇术',
    key: '/核心规则/奇术/',
    entries: [
      { text: '特效', title: '核心规则/特效' },
      { text: '启动', title: '核心规则/启动' },
      { text: '奇术调整', title: '核心规则/奇术调整' },
      { text: '奥法装置', title: '核心规则/奥法装置' },
      { text: '奇术列表', title: '核心规则/奇术列表' },
    ]
  },
  {
    group: '第六章：主持游戏',
    key: '/核心规则/主持游戏/',
    entries: [
      { text: '进行游戏', title: '核心规则/进行游戏' },
      { text: '状态速查', title: '核心规则/状态速查' },
    ]
  },
];

function generateSidebar() {
  const srcdir = './src';
  const sidebar = {};

  for (const ch of chapters) {
    const items = [];
    for (const entry of ch.entries) {
      const pageDir = path.join(srcdir, entry.title);
      const urlBase = `/${entry.title}`;
      const children = buildChildItems(pageDir, urlBase);

      const item = { text: entry.text, collapsed: true };

      if (children.length > 0) {
        item.items = children;
      } else {
        item.link = `${urlBase}/`;
      }

      items.push(item);
    }

    sidebar[ch.key] = items;
  }

  return sidebar;
}

const sidebar = generateSidebar();
const sidebarDir = './src/.vitepress';
if (!fs.existsSync(sidebarDir)) {
  fs.mkdirSync(sidebarDir, { recursive: true });
}
fs.writeFileSync(path.join(sidebarDir, 'sidebar.json'), JSON.stringify(sidebar, null, 2), 'utf8');
console.log('Sidebar config written to src/.vitepress/sidebar.json');
