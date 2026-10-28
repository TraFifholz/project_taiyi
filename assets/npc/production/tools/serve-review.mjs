import { createServer } from 'node:http';
import { readFile, writeFile, rename, stat } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const rootDir = path.resolve(scriptDir, '..');
const webDir = path.join(rootDir, 'review');
const masterFile = path.join(rootDir, 'control', 'portrait-master.json');
const decisionsFile = path.join(rootDir, 'control', 'review-decisions.json');
const host = '127.0.0.1';
const port = Number.parseInt(process.env.PORTRAIT_REVIEW_PORT || '4178', 10);

const mimeTypes = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.png': 'image/png',
};

async function readJson(file) {
  return JSON.parse(await readFile(file, 'utf8'));
}

async function loadDecisions() {
  try {
    const data = await readJson(decisionsFile);
    return data?.decisions && typeof data.decisions === 'object' ? data : { schemaVersion: 1, updatedAt: null, decisions: {} };
  } catch (error) {
    if (error.code === 'ENOENT') return { schemaVersion: 1, updatedAt: null, decisions: {} };
    throw error;
  }
}

async function saveDecisions(data) {
  data.updatedAt = new Date().toISOString();
  const temporary = `${decisionsFile}.${process.pid}.tmp`;
  await writeFile(temporary, `${JSON.stringify(data, null, 2)}\n`, 'utf8');
  await rename(temporary, decisionsFile);
}

function markdownFallback(markdown) {
  const confirmed = markdown.match(/^- 已确认：(.+)$/m)?.[1];
  const assumption = markdown.match(/^- 本轮小幅设计：(.+)$/m)?.[1];
  const concept = markdown.match(/## 完整画面构思\s+([\s\S]*?)(?=\n## |$)/)?.[1]?.trim();
  return {
    sourceFacts: confirmed ? confirmed.split('；').filter(Boolean) : [],
    designAssumptions: assumption ? assumption.split('；').filter(Boolean) : [],
    sceneConcept: concept || '',
  };
}

async function promptFor(id) {
  try {
    return await readJson(path.join(rootDir, 'prompts', `${id}.json`));
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;
    try {
      return markdownFallback(await readFile(path.join(rootDir, 'prompts', `${id}.md`), 'utf8'));
    } catch (markdownError) {
      if (markdownError.code !== 'ENOENT') throw markdownError;
      return {};
    }
  }
}

async function loadSourceCards(master) {
  const source = await readFile(path.resolve(rootDir, master.sourceFile), 'utf8');
  const cards = new Map();
  for (const line of source.split(/\r?\n/)) {
    if (!/^\|\s*LS-NPC/.test(line)) continue;
    const cells = line.split('|').slice(1, -1).map((cell) => cell.trim());
    if (cells.length < 13) continue;
    cards.set(cells[0], {
      sexAndAge: cells[5], appearance: cells[6], outfit: cells[7],
      pose: cells[8], abilityDisplay: cells[9], identityAnchor: cells[10],
    });
  }
  return cards;
}

async function loadRoster() {
  const master = await readJson(masterFile);
  const sourceCards = await loadSourceCards(master);
  const records = await Promise.all(master.characters.map(async (character) => {
    const manifestPath = path.resolve(rootDir, character.latestRun);
    const [manifest, prompt] = await Promise.all([readJson(manifestPath), promptFor(character.id)]);
    const candidatePath = path.resolve(path.dirname(manifestPath), manifest.candidateAsset);
    const sourceCard = sourceCards.get(character.id);
    const sourceFacts = sourceCard ? [
      `性别／年龄：${sourceCard.sexAndAge}`,
      `外貌：${sourceCard.appearance}`,
      `服装／装备：${sourceCard.outfit}`,
      `姿态线索：${sourceCard.pose}`,
      `身份锚点：${sourceCard.identityAnchor}`,
      `能力显现：${sourceCard.abilityDisplay}`,
    ] : (prompt.sourceFacts || []);
    return {
      ...character,
      designStatus: prompt.designStatus || manifest.designStatus || '—',
      sourceFacts,
      designAssumptions: prompt.designAssumptions || [],
      sceneConcept: prompt.sceneConcept || prompt.naturalLanguageDetail || '',
      runId: manifest.runId,
      qaNotes: manifest.qa?.notes || [],
      imageUrl: `/api/image/${encodeURIComponent(character.id)}`,
      candidatePath,
    };
  }));
  return { master, records };
}

function json(response, status, payload) {
  response.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' });
  response.end(`${JSON.stringify(payload)}\n`);
}

async function readBody(request) {
  let body = '';
  for await (const chunk of request) {
    body += chunk;
    if (body.length > 64 * 1024) throw new Error('请求内容过大');
  }
  return JSON.parse(body || '{}');
}

async function serveStatic(response, pathname) {
  const relative = pathname === '/' ? 'index.html' : pathname.replace(/^\/+/, '');
  const file = path.resolve(webDir, relative);
  if (file !== webDir && !file.startsWith(`${webDir}${path.sep}`)) return json(response, 403, { error: 'Forbidden' });
  try {
    const info = await stat(file);
    if (!info.isFile()) return json(response, 404, { error: 'Not found' });
    const content = await readFile(file);
    response.writeHead(200, { 'Content-Type': mimeTypes[path.extname(file)] || 'application/octet-stream', 'Cache-Control': 'no-store' });
    response.end(content);
  } catch (error) {
    if (error.code === 'ENOENT') return json(response, 404, { error: 'Not found' });
    throw error;
  }
}

const server = createServer(async (request, response) => {
  try {
    const url = new URL(request.url, `http://${host}:${port}`);
    if (request.method === 'GET' && url.pathname === '/api/roster') {
      const [{ master, records }, reviewData] = await Promise.all([loadRoster(), loadDecisions()]);
      const runById = new Map(records.map((record) => [record.id, record.runId]));
      const currentDecisions = Object.fromEntries(Object.entries(reviewData.decisions).filter(([id, decision]) => {
        return !decision.runId || decision.runId === runById.get(id);
      }));
      return json(response, 200, {
        project: master.project,
        updatedAt: master.updatedAt,
        records: records.map(({ candidatePath, ...record }) => record),
        decisions: currentDecisions,
      });
    }

    if (request.method === 'GET' && url.pathname.startsWith('/api/image/')) {
      const id = decodeURIComponent(url.pathname.slice('/api/image/'.length));
      const master = await readJson(masterFile);
      const character = master.characters.find((item) => item.id === id);
      if (!character) return json(response, 404, { error: '未知角色 ID' });
      const manifestPath = path.resolve(rootDir, character.latestRun);
      const manifest = await readJson(manifestPath);
      const candidatePath = path.resolve(path.dirname(manifestPath), manifest.candidateAsset);
      const content = await readFile(candidatePath);
      response.writeHead(200, { 'Content-Type': 'image/png', 'Cache-Control': 'no-store' });
      return response.end(content);
    }

    if (request.method === 'POST' && url.pathname === '/api/review') {
      const body = await readBody(request);
      const master = await readJson(masterFile);
      const character = master.characters.find((item) => item.id === body.id);
      if (!character) return json(response, 400, { error: '未知角色 ID' });
      if (!['pass', 'reject', 'pending'].includes(body.decision)) return json(response, 400, { error: '无效审核决定' });
      if (typeof body.note !== 'string' || body.note.length > 4000) return json(response, 400, { error: '备注必须是 4000 字以内的文本' });
      const data = await loadDecisions();
      const manifest = await readJson(path.resolve(rootDir, character.latestRun));
      data.decisions[body.id] = {
        decision: body.decision,
        note: body.note.trim(),
        runId: manifest.runId,
        updatedAt: new Date().toISOString()
      };
      await saveDecisions(data);
      return json(response, 200, data);
    }

    if (request.method === 'DELETE' && url.pathname.startsWith('/api/review/')) {
      const id = decodeURIComponent(url.pathname.slice('/api/review/'.length));
      const data = await loadDecisions();
      delete data.decisions[id];
      await saveDecisions(data);
      return json(response, 200, data);
    }

    if (request.method === 'GET') return serveStatic(response, url.pathname);
    return json(response, 405, { error: 'Method not allowed' });
  } catch (error) {
    console.error(error);
    return json(response, 500, { error: error.message || 'Internal server error' });
  }
});

server.listen(port, host, () => {
  console.log(`NPC portrait review: http://${host}:${port}`);
  console.log(`Decisions: ${decisionsFile}`);
});
