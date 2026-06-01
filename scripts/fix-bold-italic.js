const fs = require('fs');
const path = require('path');

const srcDir = path.join(__dirname, '..', 'src');

function walk(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) return walk(fullPath);
    if (entry.isFile() && entry.name.endsWith('.md')) return [fullPath];
    return [];
  });
}

function fixFormatting(content) {
  let text = content;

  // MediaWiki-style italic markup was imported as //text//, which Markdown
  // renders literally. Convert the common cases before touching bold labels.
  text = text.replace(/\*\*\s*\/\/(.+?)\/\/\s*\*\*/g, '***$1***');
  text = text.replace(/\/\/([^/\n]+?)\/\//g, '*$1*');

  // Keep label punctuation inside bold markers, and make sure the closing
  // marker is followed by whitespace so Markdown can terminate the span.
  text = text.replace(/\*\*([^*\n]+?)\*\*([：:])\s*/g, '**$1$2**  ');
  text = text.replace(/\*\*([^*\n]+?[：:])\*\*(?=\S)/g, '**$1**  ');

  // Normalize spacing around emphasized spans. This is intentionally modest:
  // it removes excessive imported spaces without trying to reflow prose.
  text = text.replace(/ {2,}(\*\*)/g, ' $1');
  text = text.replace(/(\*\*) {3,}/g, '$1  ');
  text = text.replace(/\|\s*(\*\*)/g, '| $1');
  text = text.replace(/(\*\*)\s*\|/g, '$1 |');

  return text;
}

let changedCount = 0;

for (const file of walk(srcDir)) {
  const original = fs.readFileSync(file, 'utf8');
  const fixed = fixFormatting(original);

  if (fixed !== original) {
    try {
      fs.writeFileSync(file, fixed, 'utf8');
      changedCount += 1;
      console.log(`Fixed: ${path.relative(process.cwd(), file)}`);
    } catch (error) {
      console.warn(
        `Skipped: ${path.relative(process.cwd(), file)} (${error.code || error.message})`,
      );
    }
  }
}

console.log(`\nDone. Updated ${changedCount} file(s).`);
