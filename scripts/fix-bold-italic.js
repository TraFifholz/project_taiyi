const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const files = execSync('find src -name "*.md" -type f', { encoding: 'utf8' })
  .trim().split('\n').filter(Boolean);

files.forEach(file => {
  let content = fs.readFileSync(file, 'utf8');
  let changed = false;

  // 1. Fix double-opening bold: "** ** text**" → "**text**"
  content = content.replace(/\*\* \*\*(.+?)\*\*/g, (m, inner) => {
    changed = true;
    return '**' + inner.trim() + '**';
  });

  // 2. Fix "** //text//**" → "**text**" (bold wrapping italic)
  content = content.replace(/\*\* \/\/(.+?)\/\/\*\*/g, (m, inner) => {
    changed = true;
    return '**' + inner.trim() + '**';
  });

  // 3. Fix CJK char touching opening ** → add space
  content = content.replace(/([一-鿿　-〿＀-￯])\*\*/g, (m, c) => {
    changed = true;
    return c + ' **';
  });

  // 4. Fix closing ** touching CJK char → add space
  content = content.replace(/\*\*([一-鿿　-〿＀-￯])/g, (m, c) => {
    changed = true;
    return '** ' + c;
  });

  // 5. Fix closing ** touching number → add space
  content = content.replace(/\*\*(\d)/g, (m, d) => {
    changed = true;
    return '** ' + d;
  });

  // 6. Fix number touching opening ** → add space
  content = content.replace(/(\d)\*\*/g, (m, d) => {
    changed = true;
    return d + ' **';
  });

  // 7. Fix :** text (colon touching opening **) → : **text
  content = content.replace(/([：:])\*\*/g, (m, c) => {
    changed = true;
    return c + ' **';
  });

  // 8. Fix closing ** touching CJK punctuation like 、。）》 etc
  content = content.replace(/\*\*([、。）》\]」』）])/g, (m, p) => {
    changed = true;
    return '** ' + p;
  });

  // 9. Fix CJK punctuation touching opening **
  content = content.replace(/([（《\[「『])\*\*/g, (m, p) => {
    changed = true;
    return p + ' **';
  });

  // 10. Fix |** (table cell start touching bold)
  content = content.replace(/\|\*\*/g, (m) => {
    changed = true;
    return '| **';
  });

  // 11. Fix **| (bold touching table cell end)
  content = content.replace(/\*\*\|/g, (m) => {
    changed = true;
    return '** |';
  });

  if (changed) {
    fs.writeFileSync(file, content, 'utf8');
    console.log('Fixed: ' + file);
  }
});

console.log('\nDone.');
