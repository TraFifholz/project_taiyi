const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const input = path.join(root, 'src', '地铁图.svg');
const outDir = path.join(root, 'discussion', '地图');
const out = path.join(outDir, 'longsan_city_street_base.svg');
const terrainInput = path.join(outDir, 'longsan_terrain_grid.txt');

const source = fs.readFileSync(input, 'utf8');
const terrainText = fs.existsSync(terrainInput)
  ? fs.readFileSync(terrainInput, 'utf8').replace(/\r/g, '').trimEnd()
  : '';

const viewBox = source.match(/viewBox="([^"]+)"/)?.[1] || '-538 -276.41107177734375 1292.7310180664062 958.86669921875';
const [minX, minY, width, height] = viewBox.split(/\s+/).map(Number);
const maxX = minX + width;
const maxY = minY + height;
const terrainRows = terrainText ? terrainText.split('\n') : [];
const terrainHeight = terrainRows.length || 1;
const terrainWidth = terrainRows.reduce((m, row) => Math.max(m, row.length), 1);
const cellW = width / terrainWidth;
const cellH = height / terrainHeight;

const terrainMeta = {
  '^': { id: 'hill', className: 'terrain hill-grid' },
  '~': { id: 'river', className: 'terrain river-grid' },
  '.': { id: 'suburb', className: 'terrain suburb-grid' },
  '#': { id: 'center', className: 'terrain center-grid' },
  F: { id: 'factory', className: 'terrain factory-grid' },
  X: { id: 'collapse', className: 'terrain collapse-grid' },
  ' ': { id: 'empty', className: 'terrain empty-grid' },
};

function terrainCharAt(x, y) {
  if (!terrainRows.length) return '.';
  const col = Math.max(0, Math.min(terrainWidth - 1, Math.floor((x - minX) / cellW)));
  const row = Math.max(0, Math.min(terrainHeight - 1, Math.floor((y - minY) / cellH)));
  return terrainRows[row]?.[col] || ' ';
}

function terrainAt(x, y) {
  return terrainMeta[terrainCharAt(x, y)]?.id || 'empty';
}

const paths = [];
for (const match of source.matchAll(/<g id="line_([^"]+)"[\s\S]*?<\/g>/g)) {
  const group = match[0];
  const id = match[1];
  for (const p of group.matchAll(/<path\b([^>]*)\sd="([^"]+)"([^>]*)>/g)) {
    const attrs = `${p[1]} ${p[3]}`;
    const stroke = attrs.match(/stroke="([^"]+)"/)?.[1] || '#999';
    if (stroke.toLowerCase() === 'white') continue;
    const dashed = /stroke-dasharray=/.test(attrs);
    paths.push({
      id,
      d: p[2],
      stroke,
      dashed,
      isRiver: id.startsWith('river') || stroke.toLowerCase() === '#b9e3f9',
    });
  }
}

const stations = [];
for (const match of source.matchAll(/<g id="(stn(?!_name)[^"]*)" transform="translate\(([-\d.]+),\s*([-\d.]+)\)"/g)) {
  stations.push({ id: match[1], x: Number(match[2]), y: Number(match[3]) });
}

function hashSeed(s) {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

function rng(seed) {
  let t = seed >>> 0;
  return () => {
    t += 0x6D2B79F5;
    let r = Math.imul(t ^ (t >>> 15), 1 | t);
    r ^= r + Math.imul(r ^ (r >>> 7), 61 | r);
    return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
  };
}

function esc(s) {
  return String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
}

function poly(points, attrs) {
  return `<polygon points="${points.map(p => `${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ')}" ${attrs}/>`;
}

function pathEl(d, attrs) {
  return `<path d="${esc(d)}" ${attrs}/>`;
}

function rect(x, y, w, h, attrs) {
  return `<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${w.toFixed(1)}" height="${h.toFixed(1)}" ${attrs}/>`;
}

function rotatePoint(cx, cy, x, y, a) {
  const c = Math.cos(a), s = Math.sin(a);
  const dx = x - cx, dy = y - cy;
  return [cx + dx * c - dy * s, cy + dx * s + dy * c];
}

function buildingBlock(cx, cy, x, y, w, h, angle, cls) {
  const pts = [
    rotatePoint(cx, cy, x, y, angle),
    rotatePoint(cx, cy, x + w, y, angle),
    rotatePoint(cx, cy, x + w, y + h, angle),
    rotatePoint(cx, cy, x, y + h, angle),
  ];
  return poly(pts, `class="${cls}"`);
}

function localStreet(cx, cy, x1, y1, x2, y2, angle, cls) {
  const a = rotatePoint(cx, cy, cx + x1, cy + y1, angle);
  const b = rotatePoint(cx, cy, cx + x2, cy + y2, angle);
  return `<line x1="${a[0].toFixed(1)}" y1="${a[1].toFixed(1)}" x2="${b[0].toFixed(1)}" y2="${b[1].toFixed(1)}" class="${cls}"/>`;
}

function inCollapse(x, y) {
  return terrainAt(x, y) === 'collapse';
}

function terrainRects() {
  const rects = [];
  for (let y = 0; y < terrainHeight; y++) {
    let start = 0;
    let current = terrainRows[y]?.[0] || ' ';
    for (let x = 1; x <= terrainWidth; x++) {
      const next = x < terrainWidth ? terrainRows[y]?.[x] || ' ' : null;
      if (next === current) continue;
      const meta = terrainMeta[current] || terrainMeta[' '];
      rects.push(rect(
        minX + start * cellW,
        minY + y * cellH,
        (x - start) * cellW,
        cellH,
        `class="${meta.className}"`
      ));
      start = x;
      current = next;
    }
  }
  return rects.join('\n    ');
}

function terrainCellPolys(char) {
  const polys = [];
  for (let y = 0; y < terrainHeight; y++) {
    for (let x = 0; x < terrainWidth; x++) {
      if ((terrainRows[y]?.[x] || ' ') !== char) continue;
      const pad = char === '~' ? 0.04 : 0.08;
      const x1 = minX + (x + pad) * cellW;
      const y1 = minY + (y + pad) * cellH;
      const x2 = minX + (x + 1 - pad) * cellW;
      const y2 = minY + (y + 1 - pad) * cellH;
      polys.push([[x1, y1], [x2, y1], [x2, y2], [x1, y2]]);
    }
  }
  return polys;
}

const secondaryRoads = [];
const buildings = [];

for (const st of stations) {
  const random = rng(hashSeed(st.id));
  const angle = (Math.round(random() * 3) * Math.PI) / 8 + (random() - 0.5) * 0.16;
  const radius = 56 + random() * 32;
  const spacing = 26 + random() * 10;

  for (let i = -2; i <= 2; i++) {
    const off = i * spacing + (random() - 0.5) * 8;
    secondaryRoads.push(localStreet(st.x, st.y, -radius, off, radius, off, angle, 'street minor'));
    secondaryRoads.push(localStreet(st.x, st.y, off, -radius, off, radius, angle, 'street minor'));
  }

  for (let gx = -2; gx <= 1; gx++) {
    for (let gy = -2; gy <= 1; gy++) {
      if (random() < 0.2) continue;
      const x = st.x + gx * spacing + 6 + random() * 4;
      const y = st.y + gy * spacing + 6 + random() * 4;
      const w = spacing - 12 - random() * 6;
      const h = spacing - 12 - random() * 6;
      const center = rotatePoint(st.x, st.y, x + w / 2, y + h / 2, angle);
      if (inCollapse(center[0], center[1])) continue;
      const terrain = terrainAt(center[0], center[1]);
      if (terrain === 'hill' || terrain === 'river' || terrain === 'empty') continue;
      if (terrain === 'suburb' && random() < 0.38) continue;
      const terrainClass = terrain === 'factory' ? ' factory'
        : terrain === 'center' ? ' center'
        : terrain === 'suburb' ? ' suburb'
        : '';
      const cls = (random() > 0.82 ? 'building dark' : random() > 0.52 ? 'building mid' : 'building') + terrainClass;
      buildings.push(buildingBlock(st.x, st.y, x, y, Math.max(8, w), Math.max(8, h), angle, cls));
    }
  }
}

const riverPaths = paths.filter(p => p.isRiver);
const railPaths = paths.filter(p => !p.isRiver);

const majorRoads = railPaths.map(p => pathEl(p.d, `class="street major${p.dashed ? ' broken' : ''}"`));
const avenueCasing = railPaths.map(p => pathEl(p.d, `class="street-casing${p.dashed ? ' broken' : ''}"`));

const hillOuter = [
  [374, -166], [512, -174], [660, -52], [716, 102], [703, 232],
  [629, 290], [544, 265], [488, 164], [412, 82], [348, -18],
];
const hillMid = [
  [430, -112], [548, -110], [638, -22], [674, 98], [648, 188],
  [572, 225], [505, 185], [454, 98], [394, 30],
];
const hillSouth = [
  [-514, 198], [-432, 103], [-336, 84], [-264, 143], [-266, 244],
  [-354, 318], [-470, 304],
];

const collapse = [
  [402, 288], [440, 238], [520, 222], [591, 266], [622, 334], [594, 414],
  [514, 461], [428, 432], [378, 360],
];
const collapseCore = [
  [459, 309], [492, 271], [548, 286], [573, 337], [549, 389], [494, 405], [449, 369],
];

const cracks = [
  'M 425 296 L 474 326 L 463 363 L 504 392 L 492 436',
  'M 529 246 L 515 300 L 565 336 L 601 327',
  'M 391 352 L 447 345 L 487 375',
  'M 548 399 L 566 443',
  'M 454 241 L 479 286',
];

const gridRivers = terrainCellPolys('~').map(points => poly(points, 'class="river-cell"')).join('\n    ');
const gridCollapse = terrainCellPolys('X').map(points => poly(points, 'class="collapse-cell"')).join('\n    ');

const svg = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" id="longsan-city-base" viewBox="${viewBox}" width="2400" height="${Math.round(2400 * height / width)}">
  <defs>
    <filter id="softShadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="1.4" stdDeviation="1.6" flood-color="#9ca3af" flood-opacity="0.28"/>
    </filter>
    <pattern id="collapseHatch" width="12" height="12" patternUnits="userSpaceOnUse" patternTransform="rotate(38)">
      <line x1="0" y1="0" x2="0" y2="12" stroke="#7c5f55" stroke-width="2" opacity="0.26"/>
    </pattern>
  </defs>
  <style>
    #longsan-city-base { background: #f4f1ea; }
    .land { fill: #f4f1ea; }
    .terrain { stroke: none; opacity: 0.36; }
    .hill-grid { fill: #d5deb5; }
    .river-grid { fill: #bce8f5; opacity: 0.45; }
    .suburb-grid { fill: #eee7d1; opacity: 0.22; }
    .center-grid { fill: #dedbd3; opacity: 0.32; }
    .factory-grid { fill: #d4c0a5; opacity: 0.34; }
    .collapse-grid { fill: #c9a69a; opacity: 0.38; }
    .empty-grid { fill: #f4f1ea; opacity: 0; }
    .water { fill: none; stroke: #9fd8ed; stroke-width: 34; stroke-linecap: round; stroke-linejoin: round; opacity: 0.78; }
    .water-edge { fill: none; stroke: #d6eef7; stroke-width: 42; stroke-linecap: round; stroke-linejoin: round; opacity: 0.72; }
    .river-cell { fill: #a8dff0; stroke: none; opacity: 0.34; }
    .hill { fill: #d9dfbd; stroke: #b8c18d; stroke-width: 2; }
    .hill-mid { fill: none; stroke: #aeb783; stroke-width: 2.2; opacity: 0.8; }
    .hill-contour { fill: none; stroke: #9fa66f; stroke-width: 1.2; opacity: 0.62; }
    .street-casing { fill: none; stroke: #c9c5bb; stroke-width: 23; stroke-linecap: round; stroke-linejoin: round; opacity: 0.82; }
    .street.major { fill: none; stroke: #fffdfa; stroke-width: 15; stroke-linecap: round; stroke-linejoin: round; }
    .street.minor { stroke: #fffdfa; stroke-width: 6.8; stroke-linecap: round; opacity: 0.94; }
    .broken { stroke-dasharray: 22 14; opacity: 0.72; }
    .building { fill: #d9d6ce; stroke: #c5c0b7; stroke-width: 0.9; }
    .building.mid { fill: #ccc8bf; }
    .building.dark { fill: #bcb7ad; }
    .building.suburb { fill: #d6cfbb; stroke: #c4bca8; }
    .building.center { fill: #bfc2c4; stroke: #aeb2b5; }
    .building.factory { fill: #a98767; stroke: #8f6d4f; }
    .collapse { fill: #c8afa4; stroke: #9e796e; stroke-width: 2.2; opacity: 0.86; }
    .collapse-core { fill: url(#collapseHatch); stroke: #7f6259; stroke-width: 1.8; opacity: 0.9; }
    .collapse-cell { fill: #b98276; stroke: none; opacity: 0.22; }
    .crack { fill: none; stroke: #584943; stroke-width: 3.2; stroke-linecap: round; stroke-linejoin: round; opacity: 0.75; }
    .overpass { fill: none; stroke: #b6b0a5; stroke-width: 2; stroke-linecap: round; stroke-dasharray: 5 6; opacity: 0.55; }
  </style>
  <rect class="land" x="${minX - 12}" y="${minY - 12}" width="${width + 24}" height="${height + 24}"/>

  <g id="terrain-grid">
    ${terrainRects()}
  </g>

  <g id="terrain">
    ${poly(hillOuter, 'class="hill"')}
    ${poly(hillMid, 'class="hill-mid"')}
    ${poly([[468,-64],[548,-68],[607,-5],[628,86],[596,151],[525,149],[479,74],[436,18]], 'class="hill-contour"')}
    ${poly([[512,0],[571,10],[598,70],[582,123],[531,120],[493,62]], 'class="hill-contour"')}
    ${poly(hillSouth, 'class="hill"')}
    ${poly([[-470,206],[-410,146],[-346,134],[-306,176],[-324,238],[-390,272],[-450,258]], 'class="hill-contour"')}
  </g>

  <g id="water">
    ${gridRivers}
    ${riverPaths.map(p => pathEl(p.d, 'class="water-edge"')).join('\n    ')}
    ${riverPaths.map(p => pathEl(p.d, 'class="water"')).join('\n    ')}
  </g>

  <g id="major-road-casing">
    ${avenueCasing.join('\n    ')}
  </g>
  <g id="minor-streets">
    ${secondaryRoads.join('\n    ')}
  </g>
  <g id="major-roads">
    ${majorRoads.join('\n    ')}
  </g>

  <g id="buildings" filter="url(#softShadow)">
    ${buildings.join('\n    ')}
  </g>

  <g id="collapse-zone">
    ${gridCollapse}
    ${poly(collapse, 'class="collapse"')}
    ${poly(collapseCore, 'class="collapse-core"')}
    ${cracks.map(d => pathEl(d, 'class="crack"')).join('\n    ')}
  </g>

  <g id="expressway-hints">
    ${pathEl('M -486 -30 L -360 -30 L -252 38 L -82 38 L 36 112 L 158 112 L 282 104 L 394 150 L 514 202 L 668 252', 'class="overpass"')}
    ${pathEl('M -108 532 L -34 480 L 78 448 L 160 486 L 244 568 L 510 568', 'class="overpass"')}
  </g>
</svg>
`;

fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(out, svg, 'utf8');
console.log(out);
