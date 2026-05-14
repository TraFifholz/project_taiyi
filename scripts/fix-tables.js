// Fix TiddlyWiki-style tables in all .md files → proper Markdown tables
const fs = require('fs');
const path = require('path');

function walkDir(dir) {
  const results = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      results.push(...walkDir(full));
    } else if (entry.name.endsWith('.md')) {
      results.push(full);
    }
  }
  return results;
}

function isSeparatorRow(line) {
  return /^\|[\s\-:]+\|/.test(line) && line.includes('---');
}

function isTableLine(line) {
  // Starts with optional whitespace then |
  if (/^\s*\|/.test(line)) return true;
  // OR: has 3+ | chars (4+ cells), not a wiki link, not a list/heading/blockquote
  const trimmed = line.trim();
  // Skip markdown lists (marker + whitespace), headings (# text), blockquotes (> text)
  if (/^[-*>#]/.test(trimmed)) {
    // But allow negative numbers or ranges like "-4", "4-5" — those aren't lists
    // List items have -/* followed by space, or digit+. followed by space
    if (/^[-*]\s/.test(trimmed)) return false;   // - item or * item
    if (/^>\s/.test(trimmed)) return false;      // > blockquote
    if (/^#{1,6}\s/.test(trimmed)) return false; // # heading
  }
  const pipeCount = (trimmed.match(/\|/g) || []).length;
  if (pipeCount >= 3) {
    // Make sure pipes aren't inside [[...]]
    const stripped = trimmed.replace(/\[\[[^\]]+\]\]/g, '');
    const realPipes = (stripped.match(/\|/g) || []).length;
    return realPipes >= 2;
  }
  return false;
}

function fixTables(content) {
  const lines = content.split('\n');
  const out = [];
  let i = 0;
  let tablesFixed = 0;

  while (i < lines.length) {
    if (isTableLine(lines[i]) && !isSeparatorRow(lines[i])) {
      // Collect consecutive table lines (skip existing separator rows)
      const tableLines = [];
      while (i < lines.length && isTableLine(lines[i])) {
        const t = lines[i].trim();
        if (!isSeparatorRow(t)) {
          tableLines.push(t);
        } else {
          tableLines.push(t);
        }
        i++;
      }

      if (tableLines.length >= 2) {
        const hasSeparator = tableLines.some(l => isSeparatorRow(l));

        if (!hasSeparator) {
          // Fix TW column merge syntax: |< → empty cell
          let fixed = tableLines.map(l => {
            l = l.replace(/\|<\|/g, '||');
            l = l.replace(/\|<(?=\|)/g, '| ');
            l = l.replace(/\|~\|/g, '||');
            return l;
          });

          // Normalize: ensure leading |, then build separator
          fixed = fixed.map(l => {
            l = l.trim();
            if (!l.startsWith('|')) l = '| ' + l;
            return l;
          });

          // Build separator from first row's column count
          const firstRowCells = fixed[0].replace(/^\|/, '').replace(/\|$/, '').split('|');
          const separator = '|' + firstRowCells.map(() => ' --- ').join('|') + '|';

          fixed.splice(1, 0, separator);

          // Fix cell spacing
          fixed = fixed.map(l => {
            if (isSeparatorRow(l)) return l;
            return '| ' + l.replace(/^\| ?/, '').replace(/ ?\|$/, '').split('|').map(c => c.trim()).join(' | ') + ' |';
          });

          out.push(...fixed);
          tablesFixed++;
        } else {
          // Has separator — just fix TW merge syntax and normalize spacing
          let fixed = tableLines.map(l => {
            if (isSeparatorRow(l)) return l;
            l = l.trim();
            if (!l.startsWith('|')) l = '| ' + l;
            l = l.replace(/\|<\|/g, '||');
            l = l.replace(/\|<(?=\|)/g, '| ');
            l = l.replace(/\|~\|/g, '||');
            return '| ' + l.replace(/^\| ?/, '').replace(/ ?\|$/, '').split('|').map(c => c.trim()).join(' | ') + ' |';
          });
          out.push(...fixed);
        }
      } else {
        out.push(tableLines[0]);
      }
    } else {
      out.push(lines[i]);
      i++;
    }
  }

  return { content: out.join('\n'), tablesFixed };
}

const srcDir = './src';
const files = walkDir(srcDir);
console.log(`Found ${files.length} .md files`);

let totalFixed = 0;
const fixedFiles = [];

for (const file of files) {
  const original = fs.readFileSync(file, 'utf8');
  const { content, tablesFixed } = fixTables(original);
  if (tablesFixed > 0) {
    fs.writeFileSync(file, content, 'utf8');
    totalFixed += tablesFixed;
    fixedFiles.push({ file: path.relative('.', file), count: tablesFixed });
    console.log(`  ${path.relative('.', file)}: ${tablesFixed} tables`);
  }
}

console.log(`\nFixed ${totalFixed} tables across ${fixedFiles.length} files`);
