# SWADE Wiki Implementation Plan

>  **For agentic workers:**  REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

 **Goal:**  Convert 560 TiddlyWiki Text entries to Markdown, set up VitePress, configure GitHub Pages CI deployment.

 **Architecture:**  One-shot Node.js script converts JSON to Markdown files preserving hierarchy. VitePress serves the static site with auto-generated sidebar. GitHub Actions deploys on push to main.

 **Tech Stack:**  VitePress (static site), Node.js (conversion script), GitHub Actions (CI/CD)

---

### Task 1: Initialize Project

 **Files:** 
- Create: `package.json`
- Create: `.gitignore`
- Modify: (new repo — `git init`)

- [ ]  **Step 1: Create package.json** 

```bash
cd "d:/Project Taiyi"
npm init -y
```

- [ ]  **Step 2: Install VitePress** 

Run: `npm install -D vitepress`

- [ ]  **Step 3: Create .gitignore** 

```
node_modules/
.vitepress/dist/
.vitepress/cache/
```

- [ ]  **Step 4: Verify** 

Run: `npx vitepress --version`

---

### Task 2: Write Conversion Script

 **Files:** 
- Create: `scripts/convert.js`

- [ ]  **Step 1: Create script skeleton that reads JSON and logs stats** 

```javascript
// scripts/convert.js
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

const isCategory = (title) => hasChildren.has(title);

// Stats
console.log(`Category pages (have children): ${data.filter(e => isCategory(e.title)).length}`);
console.log(`Leaf pages: ${data.filter(e => !isCategory(e.title)).length}`);
```

Run: `node scripts/convert.js`
Expected: prints stats.

- [ ]  **Step 2: Add path resolution and directory creation** 

```javascript
const outputDir = './src';

function getOutputPath(title) {
  if (isCategory(title)) {
    return path.join(outputDir, ...title.split('/'), 'index.md');
  }
  return path.join(outputDir, title + '.md');
}

// Create all needed directories first
const dirs = new Set();
for (const entry of data) {
  const out = getOutputPath(entry.title);
  dirs.add(path.dirname(out));
}
for (const dir of dirs) {
  fs.mkdirSync(dir, { recursive: true });
}
console.log(`Created ${dirs.size} directories`);
```

- [ ]  **Step 3: Add text conversion function** 

```javascript
function convertText(text) {
  let result = text;

  // 1. Remove <div class="statblock"> wrapper (keep content)
  result = result.replace(/<div class="statblock">/g, '');
  // Remove the matching </div> at the end of statblocks
  // (last </div> in each entry tends to close statblock)
  result = result.replace(/<\/div>(\s*)$/, '$1');

  // 2. Handle <<< blockquotes: split, prefix odd sections with >
  const parts = result.split('<<<');
  result = parts.map((part, i) => {
    if (i % 2 === 0) return part;       // outside quote
    return part.split('\n').map(line => '> ' + line).join('\n');  // inside quote
  }).join('');

  // 3. Headings: !!! → ##, !! → ###
  result = result.replace(/^!!! /gm, '## ');
  result = result.replace(/^!! /gm, '### ');

  // 4. Bold/italic: ''text'' →  **text** 
  result = result.replace(/''(.+?)''/g, ' **$1** ');

  // 5. Wiki links: [[display|path]] → [display](./path.md)
  result = result.replace(/\[\[([^\]|]+)\|([^\]]+)\]\]/g, '[$1](./$2.md)');

  // 6. Wiki links: [[path]] → [path](./path.md) (simple, no pipe)
  // But be careful: [[display|path]] was already handled
  // Handle plain links that don't contain |
  result = result.replace(/\[\[([^\]]+)\]\]/g, (match, inner) => {
    if (inner.includes('|')) return match; // already handled, shouldn't happen
    return `[${inner}](./${inner}.md)`;
  });

  // 7. <<mylist ...>> → TODO placeholder
  result = result.replace(/<<mylist\s+"([^"]+)"\s*>>/g, '<!-- TODO: mylist "$1" -->');

  // 8. Lists: TW * → MD - (only at line start)
  result = result.replace(/^\* /gm, '- ');

  // 9. Numbered lists: TW # → MD 1. (only at line start)
  result = result.replace(/^# /gm, '1. ');

  return result;
}
```

- [ ]  **Step 4: Add file writing with frontmatter** 

```javascript
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
    `original: ${entry.title}`,
    '---',
  ].filter(Boolean).join('\n');

  fs.writeFileSync(outPath, frontmatter + '\n\n' + converted, 'utf8');
}

console.log(`Wrote ${data.length} files`);
console.log(`<<mylist>> placeholders: ${mylistCount} in ${mylistLocations.length} files`);
if (mylistLocations.length > 0) {
  console.log('Locations:');
  mylistLocations.forEach(l => console.log(`  ${l.title} (${l.count})`));
}
```

- [ ]  **Step 5: Generate index.md for orphan directories** 

Directories that have no corresponding entry still need an index.md to list child pages.

```javascript
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
  const childFiles = fs.readdirSync(path.join(outputDir, dirRel))
    .filter(f => f.endsWith('.md') && f !== 'index.md')
    .map(f => f.replace('.md', ''));

  // Also find child dirs
  const childDirs = fs.readdirSync(path.join(outputDir, dirRel), { withFileTypes: true })
    .filter(d => d.isDirectory())
    .map(d => d.name);

  const links = [...childFiles, ...childDirs]
    .sort()
    .map(name => `- [${name}](./${name}/)`)
    .join('\n');

  const content = [
    '---',
    `title: ${dirName}`,
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
```

- [ ]  **Step 6: Run full conversion** 

Run: `node scripts/convert.js`

- [ ]  **Step 7: Verify output — spot check a few files** 

Run: `ls -R src/ | head -60`

---

### Task 3: Create Homepage

 **Files:** 
- Create: `src/index.md`

- [ ]  **Step 1: Write homepage** 

```markdown
---
layout: home

hero:
  name: "太一"
  text: "狂野世界规则书"
  tagline: Savage Worlds Adventure Edition · SWADE 核心规则与私设资源
  actions:
    - theme: brand
      text: 浏览核心规则
      link: /核心规则/
    - theme: alt
      text: 私设资源
      link: /私设/

features:
  - title: 核心规则
    details: 完整 SWADE 核心规则，含专长、负赘、奇术、技能等
    link: /核心规则/
  - title: 私设资源
    details: 世界观、自定义族裔、特殊规则等私设内容
    link: /私设/
---
```

- [ ]  **Step 2: Create 私设 placeholder** 

```bash
mkdir -p src/私设
```

```markdown
# 私设资源

_内容建设中..._
```

- [ ]  **Step 3: Commit** 

---

### Task 4: Configure VitePress

 **Files:** 
- Create: `.vitepress/config.js`

- [ ]  **Step 1: Generate sidebar config in convert script** 

Add to `scripts/convert.js` a function that generates the sidebar config JSON.

```javascript
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
    items.push({ text: '概览', link: urlBase + '/' });
  }

  // Then subdirectories
  const dirs = entries.filter(e => e.isDirectory()).sort((a,b) => a.name.localeCompare(b.name));
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
    .sort((a,b) => a.name.localeCompare(b.name));
  for (const f of files) {
    const name = f.name.replace('.md', '');
    items.push({ text: name, link: `${urlBase}/${name}` });
  }

  return items;
}

// Write sidebar config to a JSON file for VitePress to import
const sidebar = generateSidebar();
fs.writeFileSync('./.vitepress/sidebar.json', JSON.stringify(sidebar, null, 2), 'utf8');
console.log('Sidebar config generated');
```

- [ ]  **Step 2: Create .vitepress/config.js** 

```javascript
import { defineConfig } from 'vitepress'
import sidebar from './sidebar.json' assert { type: 'json' }

export default defineConfig({
  title: '太一 · 狂野世界规则书',
  description: 'Savage Worlds Adventure Edition 核心规则与私设资源',
  lang: 'zh-CN',
  cleanUrls: true,

  themeConfig: {
    nav: [
      { text: '首页', link: '/' },
      { text: '核心规则', link: '/核心规则/' },
      { text: '私设资源', link: '/私设/' },
    ],

    sidebar,

    search: {
      provider: 'local',
      options: {
        translations: {
          button: { buttonText: '搜索' },
          modal: { noResultsText: '无结果', resetButtonTitle: '清除' }
        }
      }
    },

    docFooter: {
      prev: '上一页',
      next: '下一页',
    },
  },
})
```

- [ ]  **Step 3: Add npm scripts to package.json** 

```json
{
  "scripts": {
    "dev": "vitepress dev src",
    "build": "vitepress build src",
    "preview": "vitepress preview src"
  }
}
```

- [ ]  **Step 4: Re-run convert to generate fresh sidebar** 

Run: `node scripts/convert.js`

- [ ]  **Step 5: Test dev server** 

Run: `npm run dev`
Expected: VitePress dev server starts, browse to localhost.

---

### Task 5: Set Up GitHub Actions Deployment

 **Files:** 
- Create: `.github/workflows/deploy.yml`

- [ ]  **Step 1: Create deploy workflow** 

```yaml
name: Deploy to GitHub Pages

on:
  push:
    branches: [main]

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: npm
      - run: npm ci
      - run: npm run build
      - uses: actions/upload-pages-artifact@v3
        with:
          path: src/.vitepress/dist
      - uses: actions/deploy-pages@v4
```

- [ ]  **Step 2: Verify workflow file syntax** 

Run: `cat .github/workflows/deploy.yml`

---

### Task 6: Initialize Git and Validate

 **Files:** 
- Create: (git init)

- [ ]  **Step 1: Initialize git repo** 

```bash
cd "d:/Project Taiyi"
git init
git add -A
git status
```

- [ ]  **Step 2: Review what will be committed** 

Check that `node_modules/`, `.vitepress/dist/`, `.vitepress/cache/` are excluded by .gitignore.

- [ ]  **Step 3: Commit** 

```bash
git add package.json package-lock.json .gitignore src/ .vitepress/ scripts/ .github/
git commit -m "feat: initialize SWADE wiki with VitePress and conversion script"
```

- [ ]  **Step 4: Build and verify static output** 

Run: `npm run build`
Expected: build succeeds, files in `src/.vitepress/dist/`

- [ ]  **Step 5: Check for conversion issues** 

Scan for broken links, empty pages, unclosed HTML.

```bash
# Find empty markdown files (only frontmatter)
node -e "const fs=require('fs');const g=require('glob');g.sync('src/**/*.md').forEach(f=>{const c=fs.readFileSync(f,'utf8');const body=c.split('---').slice(2).join('---').trim();if(!body||body.length<10)console.log('EMPTY:',f)})"
```

---

### Notes

- 20 `<<mylist>>` macros are marked as `<!-- TODO: mylist ... -->` in converted files — manually replace after conversion
- Sidebar is generated alphabetically — manually reorder groups later by editing `.vitepress/sidebar.json`
- All 552 entries with `<div class="statblock">` wrappers are stripped of the wrapper
- 40 `<<<` blockquote markers are converted to `>` prefixes
