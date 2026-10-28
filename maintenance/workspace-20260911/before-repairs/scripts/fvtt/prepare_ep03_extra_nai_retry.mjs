import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

const root = process.cwd();
const batchRoot = path.join(root, 'records/prep/ep03-fvtt-20260903/portraits/extras-vehicles-20260904/nai-20260904');
const sourceRun = path.join(batchRoot, 'runs/20260904-ep03-extra-drone-nai-v1');
const runId = '20260904-ep03-extra-drone-nai-v2';
const targetRun = path.join(batchRoot, 'runs', runId);
const seed = crypto.createHash('sha256').update(runId).digest().readUInt32BE(0) & 0x7fffffff;
const request = JSON.parse(fs.readFileSync(path.join(sourceRun, 'request.json'), 'utf8'));
request.meta.runId = runId;
request.meta.retryOf = '20260904-ep03-extra-drone-nai-v1';
request.meta.retryReason = 'Remove fake shell marking and duplicate cast-shadow silhouette.';
request.meta.humanInitiatedAt = new Date().toISOString();
request.payload.parameters.seed = seed;
const caption = request.payload.parameters.v4_prompt.caption.char_captions[0];
caption.char_caption = caption.char_caption
  .replace(', reflection, shiny, circle, surveillance, outline', '')
  .replace(', shadow, flat color.', ', flat color.')
  .replace(
    'Clean game-token silhouette; no human pilot, gun, cannon, missile, logo, readable text, or supernatural glow.',
    'One isolated object only on an empty transparent background. The shell is completely blank and unmarked, with no badge, icon, letters, numbers, cast shadow, duplicate silhouette, human pilot, gun, cannon, missile, or supernatural glow.'
  );
const negative = request.payload.parameters.negative_prompt;
request.payload.parameters.negative_prompt = `${negative}, shadow, reflection`;
request.payload.parameters.v4_negative_prompt.caption.base_caption = request.payload.parameters.negative_prompt;

fs.mkdirSync(targetRun, { recursive: false });
fs.writeFileSync(path.join(targetRun, 'request.json'), JSON.stringify(request, null, 2) + '\n', { flag: 'wx' });
fs.writeFileSync(path.join(targetRun, 'manifest.json'), JSON.stringify({
  schemaVersion: 1,
  runId,
  characterId: request.meta.characterId,
  characterName: request.meta.characterName,
  actorId: request.meta.actorId,
  retryOf: request.meta.retryOf,
  status: 'queued',
  requestFile: 'request.json',
  resultFile: null,
  rawAssets: [],
  candidateAsset: null,
  qa: { technical: 'pending', visual: 'pending', notes: [request.meta.retryReason] }
}, null, 2) + '\n', { flag: 'wx' });
console.log(JSON.stringify({ runId, seed, targetRun }, null, 2));
