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

function convertText(text) {
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

  // 5. Wiki links: [[display|path]] → [display](/path/) (all entries are categories at path/index.md)
  result = result.replace(/\[\[([^\]|]+)\|([^\]]+)\]\]/g, '[$1](/$2/)');

  // 6. Wiki links: [[path]] → [path](/path/) (simple, no pipe)
  result = result.replace(/\[\[([^\]]+)\]\]/g, (match, inner) => {
    if (inner.includes('|')) return match; // already handled
    return `[${inner}](/${inner}/)`;
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

for (const entry of data) {
  const outPath = getOutputPath(entry.title);
  const converted = convertText(entry.text);

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

console.log(`Wrote ${data.length} files`);
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
// Sidebar generation
// ============================================================

function generateSidebar() {
  const srcdir = './src';
  const sidebar = {};

  // Only process top-level dirs under src/
  const topDirs = fs.readdirSync(srcdir, { withFileTypes: true })
    .filter(d => d.isDirectory() && d.name !== '私设')
    .map(d => d.name);

  for (const dir of topDirs) {
    const base = `/${dir}/`;
    const items = buildSidebarItems(path.join(srcdir, dir), `/${dir}`);
    sidebar[base] = items;
  }

  return sidebar;
}

function buildSidebarItems(absPath, urlBase) {
  const entries = fs.readdirSync(absPath, { withFileTypes: true });
  const items = [];

  // index.md first
  if (fs.existsSync(path.join(absPath, 'index.md'))) {
    items.push({ text: '概览', link: urlBase });
  }

  // Then subdirectories
  const dirs = entries.filter(e => e.isDirectory()).sort((a, b) => a.name.localeCompare(b.name, 'zh-CN'));
  for (const d of dirs) {
    items.push({
      text: d.name,
      collapsed: true,
      items: buildSidebarItems(path.join(absPath, d.name), `${urlBase}/${d.name}`)
    });
  }

  // Then files (excluding index.md)
  const files = entries
    .filter(e => e.isFile() && e.name.endsWith('.md') && e.name !== 'index.md')
    .sort((a, b) => a.name.localeCompare(b.name, 'zh-CN'));
  for (const f of files) {
    const name = f.name.replace('.md', '');
    items.push({ text: name, link: `${urlBase}/${name}` });
  }

  return items;
}

// Generate sidebar JSON
const sidebar = generateSidebar();
const sidebarDir = './src/.vitepress';
if (!fs.existsSync(sidebarDir)) {
  fs.mkdirSync(sidebarDir, { recursive: true });
}
fs.writeFileSync(path.join(sidebarDir, 'sidebar.json'), JSON.stringify(sidebar, null, 2), 'utf8');
console.log('Sidebar config written to src/.vitepress/sidebar.json');
