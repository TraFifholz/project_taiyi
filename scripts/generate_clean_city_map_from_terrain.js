const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const outDir = path.join(root, 'assets', 'maps');
const terrainPath = path.join(outDir, 'longsan_terrain_grid.txt');
const svgPath = path.join(outDir, 'longsan_city_street_base.svg');

const terrainText = fs.readFileSync(terrainPath, 'utf8').replace(/\r/g, '').trimEnd();
const rows = terrainText.split('\n');
const gridH = rows.length;
const gridW = Math.max(...rows.map(row => row.length));

const width = 2400;
const height = 1800;
const cellW = width / gridW;
const cellH = height / gridH;

const urban = new Set(['.', '#', 'F']);
const roadable = new Set(['.', '#', 'F', '~']);
const buildable = new Set(['.', '#', 'F']);

function charAt(x, y) {
  if (x < 0 || y < 0 || x >= gridW || y >= gridH) return ' ';
  return rows[y]?.[x] || ' ';
}

function centerOf(x, y) {
  return [(x + 0.5) * cellW, (y + 0.5) * cellH];
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

function rect(x, y, w, h, cls) {
  return `<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${w.toFixed(1)}" height="${h.toFixed(1)}" class="${cls}"/>`;
}

function line(x1, y1, x2, y2, cls) {
  return `<line x1="${x1.toFixed(1)}" y1="${y1.toFixed(1)}" x2="${x2.toFixed(1)}" y2="${y2.toFixed(1)}" class="${cls}"/>`;
}

function pathEl(d, cls) {
  return `<path d="${d}" class="${cls}"/>`;
}

function poly(points, cls) {
  return `<polygon points="${points.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(' ')}" class="${cls}"/>`;
}

function terrainBackground() {
  const classes = {
    '^': 't-hill',
    '~': 't-river',
    '.': 't-suburb',
    '#': 't-center',
    F: 't-factory',
    X: 't-collapse',
    ' ': 't-empty',
  };
  const parts = [];
  for (let y = 0; y < gridH; y++) {
    let start = 0;
    let current = charAt(0, y);
    for (let x = 1; x <= gridW; x++) {
      const next = x < gridW ? charAt(x, y) : null;
      if (next === current) continue;
      parts.push(rect(start * cellW - 0.5, y * cellH - 0.5, (x - start) * cellW + 1, cellH + 1, classes[current] || 't-empty'));
      start = x;
      current = next;
    }
  }
  return parts.join('\n    ');
}

function connectedCells(target) {
  const all = [];
  const seen = new Set();
  for (let y = 0; y < gridH; y++) {
    for (let x = 0; x < gridW; x++) {
      if (charAt(x, y) !== target || seen.has(`${x},${y}`)) continue;
      const comp = [];
      const stack = [[x, y]];
      seen.add(`${x},${y}`);
      while (stack.length) {
        const [cx, cy] = stack.pop();
        comp.push([cx, cy]);
        for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
          const nx = cx + dx, ny = cy + dy;
          const key = `${nx},${ny}`;
          if (charAt(nx, ny) === target && !seen.has(key)) {
            seen.add(key);
            stack.push([nx, ny]);
          }
        }
      }
      all.push(comp);
    }
  }
  return all;
}

function traceComponent(comp) {
  const cells = new Set(comp.map(([x, y]) => `${x},${y}`));
  const neighbors = ([x, y]) => [[1, 0], [-1, 0], [0, 1], [0, -1]]
    .map(([dx, dy]) => [x + dx, y + dy])
    .filter(([nx, ny]) => cells.has(`${nx},${ny}`));
  const endpoints = comp.filter(c => neighbors(c).length <= 1);
  let current = endpoints[0] || comp[0];
  const visited = new Set();
  const ordered = [];
  while (current) {
    ordered.push(current);
    visited.add(`${current[0]},${current[1]}`);
    const next = neighbors(current).filter(([nx, ny]) => !visited.has(`${nx},${ny}`))
      .sort((a, b) => (a[1] - b[1]) || (a[0] - b[0]))[0];
    current = next;
  }
  for (const c of comp) {
    if (!visited.has(`${c[0]},${c[1]}`)) ordered.push(c);
  }
  return ordered.map(([x, y]) => centerOf(x, y));
}

function smoothPath(points) {
  if (points.length === 0) return '';
  if (points.length === 1) return `M ${points[0][0]} ${points[0][1]}`;
  let d = `M ${points[0][0].toFixed(1)} ${points[0][1].toFixed(1)}`;
  for (let i = 1; i < points.length; i++) {
    const [px, py] = points[i - 1];
    const [x, y] = points[i];
    const mx = (px + x) / 2;
    const my = (py + y) / 2;
    d += ` Q ${px.toFixed(1)} ${py.toFixed(1)} ${mx.toFixed(1)} ${my.toFixed(1)}`;
  }
  const last = points[points.length - 1];
  d += ` T ${last[0].toFixed(1)} ${last[1].toFixed(1)}`;
  return d;
}

function riverLayers() {
  const water = [];
  const edge = [];
  for (let y = 0; y < gridH; y++) {
    for (let x = 0; x < gridW; x++) {
      if (charAt(x, y) !== '~') continue;
      const x0 = x * cellW;
      const y0 = y * cellH;
      edge.push(rect(x0 - 10, y0 - 10, cellW + 20, cellH + 20, 'river-edge-cell'));
      water.push(rect(x0 - 1, y0 - 1, cellW + 2, cellH + 2, 'river-cell'));
    }
  }

  // Add a softened central current without replacing the actual water-cell shape.
  const comps = connectedCells('~').map(traceComponent).filter(points => points.length > 1);
  const current = comps.map(points => pathEl(smoothPath(points), 'river-current')).join('\n    ');
  return `${edge.join('\n    ')}\n    ${water.join('\n    ')}\n    ${current}`;
}

function arterialRoads() {
  const parts = [];
  const arterialRows = new Set([1, 4, 7, 10, 13, 16]);
  const arterialCols = new Set([2, 5, 8, 11, 14, 17, 20, 23]);
  for (let y = 0; y < gridH; y++) {
    if (!arterialRows.has(y)) continue;
    let start = null;
    let hasWater = false;
    for (let x = 0; x <= gridW; x++) {
      const ok = x < gridW && roadable.has(charAt(x, y));
      if (ok && start === null) start = x;
      if (ok && charAt(x, y) === '~') hasWater = true;
      if ((!ok || x === gridW) && start !== null) {
        if (x - start >= 2) {
          const yy = (y + 0.5) * cellH;
          parts.push(line(start * cellW + 18, yy, x * cellW - 18, yy, `road arterial casing${hasWater ? ' bridge' : ''}`));
          parts.push(line(start * cellW + 18, yy, x * cellW - 18, yy, `road arterial${hasWater ? ' bridge' : ''}`));
        }
        start = null;
        hasWater = false;
      }
    }
  }
  for (let x = 0; x < gridW; x++) {
    if (!arterialCols.has(x)) continue;
    let start = null;
    let hasWater = false;
    for (let y = 0; y <= gridH; y++) {
      const ok = y < gridH && roadable.has(charAt(x, y));
      if (ok && start === null) start = y;
      if (ok && charAt(x, y) === '~') hasWater = true;
      if ((!ok || y === gridH) && start !== null) {
        if (y - start >= 2) {
          const xx = (x + 0.5) * cellW;
          parts.push(line(xx, start * cellH + 18, xx, y * cellH - 18, `road arterial casing${hasWater ? ' bridge' : ''}`));
          parts.push(line(xx, start * cellH + 18, xx, y * cellH - 18, `road arterial${hasWater ? ' bridge' : ''}`));
        }
        start = null;
        hasWater = false;
      }
    }
  }
  return parts.join('\n    ');
}

function localRoadsAndBuildings() {
  const roads = [];
  const buildings = [];
  for (let y = 0; y < gridH; y++) {
    for (let x = 0; x < gridW; x++) {
      const t = charAt(x, y);
      if (!buildable.has(t)) continue;
      const random = rng(hashSeed(`${x},${y},${t}`));
      const x0 = x * cellW;
      const y0 = y * cellH;
      if ((x + y) % (t === '#' ? 2 : 3) === 0) {
        const rx = x0 + cellW * (0.36 + random() * 0.28);
        roads.push(line(rx, y0 + 15, rx, y0 + cellH - 15, 'road local'));
      }
      if ((x * 2 + y) % (t === '#' ? 3 : 4) === 0) {
        const ry = y0 + cellH * (0.36 + random() * 0.28);
        roads.push(line(x0 + 15, ry, x0 + cellW - 15, ry, 'road local'));
      }

      const count = t === '#' ? 5 : t === 'F' ? 2 : 3;
      for (let i = 0; i < count; i++) {
        const bw = t === 'F' ? 34 + random() * 30 : t === '#' ? 20 + random() * 22 : 16 + random() * 18;
        const bh = t === 'F' ? 34 + random() * 28 : t === '#' ? 20 + random() * 22 : 16 + random() * 18;
        const bx = x0 + 14 + random() * Math.max(1, cellW - bw - 28);
        const by = y0 + 14 + random() * Math.max(1, cellH - bh - 28);
        const cls = t === '#' ? 'building center' : t === 'F' ? 'building factory' : 'building suburb';
        buildings.push(rect(bx, by, bw, bh, cls));
      }
    }
  }
  return { roads: roads.join('\n    '), buildings: buildings.join('\n    ') };
}

function hillContours() {
  const parts = [];
  for (const comp of connectedCells('^')) {
    if (comp.length < 3) continue;
    let minCx = Infinity, minCy = Infinity, maxCx = -Infinity, maxCy = -Infinity;
    for (const [x, y] of comp) {
      minCx = Math.min(minCx, x * cellW);
      minCy = Math.min(minCy, y * cellH);
      maxCx = Math.max(maxCx, (x + 1) * cellW);
      maxCy = Math.max(maxCy, (y + 1) * cellH);
    }
    const cx = (minCx + maxCx) / 2;
    const cy = (minCy + maxCy) / 2;
    for (let i = 0; i < 3; i++) {
      const rx = (maxCx - minCx) * (0.42 - i * 0.08);
      const ry = (maxCy - minCy) * (0.38 - i * 0.07);
      if (rx < 40 || ry < 28) continue;
      parts.push(`<ellipse cx="${cx.toFixed(1)}" cy="${cy.toFixed(1)}" rx="${rx.toFixed(1)}" ry="${ry.toFixed(1)}" class="hill-contour"/>`);
    }
  }
  return parts.join('\n    ');
}

function collapseCracks() {
  const comps = connectedCells('X');
  const parts = [];
  for (const comp of comps) {
    if (comp.length < 2) continue;
    const points = comp.map(([x, y]) => centerOf(x, y));
    const cx = points.reduce((s, p) => s + p[0], 0) / points.length;
    const cy = points.reduce((s, p) => s + p[1], 0) / points.length;
    for (let i = 0; i < 7; i++) {
      const random = rng(hashSeed(`crack-${i}`));
      const angle = random() * Math.PI * 2;
      const len = 90 + random() * 140;
      const kink = 30 + random() * 45;
      const x1 = cx + Math.cos(angle) * 20;
      const y1 = cy + Math.sin(angle) * 20;
      const x2 = cx + Math.cos(angle) * len;
      const y2 = cy + Math.sin(angle) * len;
      const mx = (x1 + x2) / 2 + Math.cos(angle + Math.PI / 2) * kink * (random() > 0.5 ? 1 : -1);
      const my = (y1 + y2) / 2 + Math.sin(angle + Math.PI / 2) * kink * (random() > 0.5 ? 1 : -1);
      parts.push(pathEl(`M ${x1.toFixed(1)} ${y1.toFixed(1)} L ${mx.toFixed(1)} ${my.toFixed(1)} L ${x2.toFixed(1)} ${y2.toFixed(1)}`, 'crack'));
    }
  }
  return parts.join('\n    ');
}

const local = localRoadsAndBuildings();

const svg = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" id="longsan-city-base" viewBox="0 0 ${width} ${height}" width="${width}" height="${height}">
  <defs>
    <filter id="softShadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="1.1" stdDeviation="1.2" flood-color="#9a9285" flood-opacity="0.3"/>
    </filter>
    <filter id="softTerrain" x="-4%" y="-4%" width="108%" height="108%">
      <feGaussianBlur stdDeviation="10"/>
    </filter>
    <filter id="softWater" x="-4%" y="-4%" width="108%" height="108%">
      <feGaussianBlur stdDeviation="7"/>
    </filter>
  </defs>
  <style>
    #longsan-city-base { background: #f1ede4; }
    .land { fill: #f1ede4; }
    .t-empty { fill: #f1ede4; }
    .t-hill { fill: #dce3c7; }
    .t-suburb { fill: #eee8d9; }
    .t-center { fill: #e2e1dc; }
    .t-factory { fill: #d9c8b1; }
    .t-collapse { fill: #d4afa6; }
    .t-river { fill: #c8edf7; }
    .hill-contour { fill: none; stroke: #aab982; stroke-width: 2.2; opacity: 0.52; }
    .river-edge-cell { fill: #d8f3fa; stroke: none; opacity: 0.96; filter: url(#softWater); }
    .river-cell { fill: #86d8ed; stroke: none; opacity: 0.96; filter: url(#softWater); }
    .river-current { fill: none; stroke: #6bc8df; stroke-width: 16; stroke-linecap: round; stroke-linejoin: round; opacity: 0.22; }
    .road { fill: none; stroke-linecap: round; stroke-linejoin: round; }
    .road.arterial.casing { stroke: #c9c3b7; stroke-width: 20; opacity: 0.72; }
    .road.arterial { stroke: #fffdf8; stroke-width: 12; opacity: 0.96; }
    .road.arterial.bridge { stroke: #f8fafc; }
    .road.local { stroke: #fffdf8; stroke-width: 5.4; opacity: 0.82; }
    .building { stroke-width: 1; filter: url(#softShadow); }
    .building.suburb { fill: #cfc8b7; stroke: #b9b09e; }
    .building.center { fill: #b9bec1; stroke: #9fa6aa; }
    .building.factory { fill: #9f7857; stroke: #856346; }
    .crack { fill: none; stroke: #5b4c46; stroke-width: 5; stroke-linecap: round; stroke-linejoin: round; opacity: 0.65; }
  </style>
  <rect class="land" width="${width}" height="${height}"/>
  <g id="terrain" filter="url(#softTerrain)">
    ${terrainBackground()}
  </g>
  <g id="terrain-contours">
    ${hillContours()}
  </g>
  <g id="rivers">
    ${riverLayers()}
  </g>
  <g id="arterials">
    ${arterialRoads()}
  </g>
  <g id="local-roads">
    ${local.roads}
  </g>
  <g id="buildings">
    ${local.buildings}
  </g>
  <g id="collapse">
    ${collapseCracks()}
  </g>
</svg>
`;

fs.writeFileSync(svgPath, svg, 'utf8');
console.log(svgPath);
