// Fix mylist placeholders in converted Markdown files
// Reads Tiddlywiki.json to resolve <<mylist>> queries, replaces TODO placeholders

const fs = require('fs');
const path = require('path');

// Load source data
const data = JSON.parse(fs.readFileSync('./Tiddlywiki.json', 'utf8'));

// Parse mylist filter string: [tag[X]prefix[Y]sort[Z]...]
function parseFilter(filter) {
  const conditions = {};
  const re = /([^\[]+)\[([^\]]+)\]/g;
  let m;
  while ((m = re.exec(filter)) !== null) {
    conditions[m[1]] = m[2];
  }
  return conditions;
}

// Query entries matching the filter
function queryEntries(conditions) {
  let results = data.slice();

  if (conditions.tag) {
    // tag filter matches the 'tag' field or 'tags' field (comma-separated)
    const tagVal = conditions.tag;
    results = results.filter(e => {
      if (e.tag === tagVal) return true;
      if (e.tags && e.tags.split(' ').includes(tagVal)) return true;
      return false;
    });
  }

  if (conditions.prefix) {
    const prefix = conditions.prefix;
    results = results.filter(e => e.title && e.title.startsWith(prefix));
  }

  if (conditions['专长类型']) {
    const typeVal = conditions['专长类型'];
    results = results.filter(e => e['专长类型'] && e['专长类型'].includes(typeVal));
  }

  // Sort
  if (conditions.sort === '英文名') {
    results.sort((a, b) => (a['英文名'] || '').localeCompare(b['英文名'] || ''));
  } else if (conditions.sort === '中文名') {
    results.sort((a, b) => (a['中文名'] || '').localeCompare(b['中文名'] || '', 'zh-CN'));
  }

  return results;
}

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

// Generate markdown list for matching entries
function generateList(results, sourceTitle) {
  if (results.length === 0) return '_暂无条目_';
  return results.map(e => {
    const name = e['中文名'] || e.title.split('/').pop();
    const rel = relativeLink(sourceTitle, e.title);
    return `- [${name}](${rel})`;
  }).join('\n');
}

// Extract page title from file path: src/核心规则/奥法背景/index.md → 核心规则/奥法背景
function getTitleFromFile(filePath) {
  const rel = path.relative(srcDir, filePath).replace(/\\/g, '/');
  // Remove /index.md suffix
  return rel.replace(/\/index\.md$/, '');
}

// Walk all markdown files
function walk(dir) {
  const results = [];
  const list = fs.readdirSync(dir, { withFileTypes: true });
  for (const item of list) {
    const p = path.join(dir, item.name);
    if (item.isDirectory()) {
      results.push(...walk(p));
    } else if (item.name.endsWith('.md')) {
      results.push(p);
    }
  }
  return results;
}

// Process all files
const srcDir = './src';
const files = walk(srcDir);

let fixCount = 0;
const report = [];

for (const file of files) {
  let content = fs.readFileSync(file, 'utf8');
  const placeholderRe = /<!-- TODO: mylist "([^"]+)" -->/g;
  let match;
  let fileModified = false;

  while ((match = placeholderRe.exec(content)) !== null) {
    const filterStr = match[1];
    const conditions = parseFilter(filterStr);
    const entries = queryEntries(conditions);
    const sourceTitle = getTitleFromFile(file);
    const list = generateList(entries, sourceTitle);

    // Replace first occurrence only (there should be one per file)
    content = content.replace(match[0], list);
    fileModified = true;
    fixCount++;
    report.push({
      file: path.relative(srcDir, file),
      filter: filterStr,
      count: entries.length
    });
  }

  if (fileModified) {
    fs.writeFileSync(file, content, 'utf8');
  }
}

console.log(`Fixed ${fixCount} mylist placeholders in ${report.length} files:`);
report.forEach(r => {
  console.log(`  ${r.file}: ${r.count} entries (filter: ${r.filter})`);
});
