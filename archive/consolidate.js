// Consolidate individual 专长 and 负赘 pages into grouped pages

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const data = JSON.parse(fs.readFileSync('./Tiddlywiki.json', 'utf8'));
const outputDir = './src';

// ---- Helpers ----

function convertText(text, sourceTitle) {
  let result = text;

  result = result.replace(/<div[^>]*>/gi, '');
  result = result.replace(/<\/div>/gi, '');

  const parts = result.split('<<<');
  result = parts.map((part, i) => {
    if (i % 2 === 0) return part;
    return part.split('\n').map(line => line.startsWith('>') ? line : '> ' + line).join('\n');
  }).join('');

  result = result.replace(/^!!!!\s?/gm, '#### ');
  result = result.replace(/^!!!\s?/gm, '### ');
  result = result.replace(/^!!\s?/gm, '## ');
  result = result.replace(/^!\s?/gm, '# ');
  result = result.replace(/^> !!!!\s?/gm, '> #### ');
  result = result.replace(/^> !!!\s?/gm, '> ### ');
  result = result.replace(/^> !!\s?/gm, '> ## ');
  result = result.replace(/^> !\s?/gm, '> # ');

  result = result.replace(/''(.+?)''/g, '**$1**');

  // Relative links
  function relativeLink(from, to) {
    const fp = from.split('/'), tp = to.split('/');
    let i = 0;
    while (i < fp.length && i < tp.length && fp[i] === tp[i]) i++;
    const ups = fp.length - i;
    const downs = tp.slice(i);
    let rel = ups === 0 ? './' : '../'.repeat(ups);
    if (downs.length > 0) rel += downs.join('/') + '/';
    return rel;
  }

  result = result.replace(/\[\[([^\]|]+)\|([^\]]+)\]\]/g, (m, display, target) => {
    return `[${display}](${relativeLink(sourceTitle, target)})`;
  });
  result = result.replace(/\[\[([^\]]+)\]\]/g, (m, inner) => {
    if (inner.includes('|')) return m;
    return `[${inner}](${relativeLink(sourceTitle, inner)})`;
  });

  result = result.replace(/<<mylist\s+"([^"]+)"\s*>>/g, '<!-- TODO: mylist "$1" -->');
  result = result.replace(/^\* /gm, '- ');
  result = result.replace(/^# /gm, '1. ');
  result = result.replace(/<\$[\w-]+[^>]*\/>/g, '');
  result = result.replace(/<\/?\$[\w-]+[^>]*>/g, '');
  result = result.replace(/\{\{/g, '&#123;&#123;');
  result = result.replace(/\}\}/g, '&#125;&#125;');
  result = result.replace(/<ul>/gi, '');
  result = result.replace(/<\/ul>/gi, '');
  result = result.replace(/<ol[^>]*>/gi, '');
  result = result.replace(/<\/ol>/gi, '');
  result = result.replace(/<li>/gi, '');
  result = result.replace(/<\/li>/gi, '<br>');

  return result.trim();
}

function removeDir(dir) {
  if (fs.existsSync(dir)) {
    try {
      execSync(`rm -rf "${dir}"`, { stdio: 'pipe' });
    } catch (e) {
      console.log(`  Warning: Failed to remove ${dir}: ${e.message}`);
    }
  }
}

// ---- Consolidate 专长 by type ----

const edges = data.filter(e =>
  e.title.startsWith('核心规则/专长/') && e.title.split('/').length === 3
);

console.log(`Found ${edges.length} individual edge entries`);

// Group by 专长类型
const typeGroups = {};
for (const e of edges) {
  const type = e['专长类型'] || '其他专长';
  if (!typeGroups[type]) typeGroups[type] = [];
  typeGroups[type].push(e);
}

console.log(`Grouped into ${Object.keys(typeGroups).length} types:`);

// Remove old individual edge dirs
for (const e of edges) {
  const dir = path.join(outputDir, e.title);
  removeDir(dir);
}
console.log('Removed individual edge directories');

// Create consolidated edge type pages
const edgeTypeDir = path.join(outputDir, '核心规则', '专长');
fs.mkdirSync(edgeTypeDir, { recursive: true });

for (const [typeName, entries] of Object.entries(typeGroups)) {
  // Sort by 英文名
  entries.sort((a, b) => (a['英文名'] || '').localeCompare(b['英文名'] || ''));

  const typeSlug = typeName.replace(/ /g, '_');
  const outPath = path.join(edgeTypeDir, `${typeSlug}.md`);

  let body = `# ${typeName}\n\n`;

  for (const e of entries) {
    const converted = convertText(e.text, e.title);
    body += `## ${e['中文名'] || e.title.split('/').pop()}\n\n`;
    if (e['英文名']) body += `**英文名：** ${e['英文名']}\n\n`;
    body += converted + '\n\n---\n\n';
  }

  const frontmatter = [
    '---',
    `title: ${JSON.stringify(typeName.split(' ').pop())}`,
    `title_full: ${JSON.stringify(typeName)}`,
    '---',
  ].join('\n');

  fs.writeFileSync(outPath, frontmatter + '\n\n' + body, 'utf8');
  console.log(`  ${typeName}: ${entries.length} edges → ${typeSlug}.md`);
}

// ---- Consolidate 负赘 ----

const hindrances = data.filter(e =>
  e.title.startsWith('核心规则/负赘/') && e.title.split('/').length === 3
);

console.log(`\nFound ${hindrances.length} individual hindrance entries`);

// Remove old individual hindrance dirs
for (const e of hindrances) {
  const dir = path.join(outputDir, e.title);
  removeDir(dir);
}
console.log('Removed individual hindrance directories');

// Sort hindrances
hindrances.sort((a, b) => (a['英文名'] || '').localeCompare(b['英文名'] || ''));

let hindranceBody = `# 负赘 Hindrances\n\n`;
for (const e of hindrances) {
  const converted = convertText(e.text, e.title);
  // Determine if major or minor from text
  const isMajor = e.text.includes('主要负赘') || e.text.includes('Major');

  hindranceBody += `## ${e['中文名'] || e.title.split('/').pop()}\n\n`;
  if (e['英文名']) hindranceBody += `**英文名：** ${e['英文名']}\n\n`;
  if (isMajor) hindranceBody += `_主要负赘 Major_\n\n`;
  else hindranceBody += `_次要负赘 Minor_\n\n`;
  hindranceBody += converted + '\n\n---\n\n';
}

const hindranceOut = path.join(outputDir, '核心规则', '负赘.md');
const hindranceFM = [
  '---',
  'title: "负赘"',
  'title_en: "Hindrances"',
  '---',
].join('\n');
fs.writeFileSync(hindranceOut, hindranceFM + '\n\n' + hindranceBody, 'utf8');
console.log(`Wrote consolidated 负赘.md (${hindrances.length} entries)`);

// ---- Also remove 负赘/详述 directory ----
removeDir(path.join(outputDir, '核心规则', '负赘', '详述'));
// Remove old 负赘 directory (not the .md file)
const oldHindranceDirs = fs.readdirSync(path.join(outputDir, '核心规则', '负赘'), { withFileTypes: true })
  .filter(d => d.isDirectory());
for (const d of oldHindranceDirs) {
  removeDir(path.join(outputDir, '核心规则', '负赘', d.name));
}

// ---- Remove old 专长/详述 directory ----
removeDir(path.join(outputDir, '核心规则', '专长', '详述'));
const oldEdgeDirs = fs.readdirSync(edgeTypeDir, { withFileTypes: true })
  .filter(d => d.isDirectory());
for (const d of oldEdgeDirs) {
  removeDir(path.join(edgeTypeDir, d.name));
}

console.log('\nDone. Run "node scripts/fix-mylist.js" next to update mylist references.');
console.log('Then update the sidebar manually or re-run convert.js sidebar generation.');
