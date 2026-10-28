import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";

const toolDir = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(toolDir, "..");
const masterPath = path.join(root, "control", "portrait-master.json");
const ledgerPath = path.join(root, "control", "verified-tags.json");
const promptsDir = path.join(root, "prompts");
const runsDir = path.join(root, "runs");

const readJson = (file) => JSON.parse(fs.readFileSync(file, "utf8"));
const sha256 = (file) => crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");
const master = readJson(masterPath);
const ledger = readJson(ledgerPath).tags;
const issues = [];
const candidateHashes = new Map();
let jsonPromptCount = 0;
let markdownPilotPromptCount = 0;
let approvedCount = 0;

for (const character of master.characters) {
  const id = character.id;
  if (character.productionStatus !== "qa_passed") issues.push(`${id}: master status ${character.productionStatus}`);
  if (character.approvedAsset) {
    approvedCount += 1;
    const approvedPath = path.resolve(root, character.approvedAsset);
    if (!fs.existsSync(approvedPath)) issues.push(`${id}: missing approved asset`);
    else if (character.approvedSha256 && sha256(approvedPath) !== character.approvedSha256) issues.push(`${id}: approved SHA-256 mismatch`);
    if (!character.approvedRun) issues.push(`${id}: approved asset missing approvedRun`);
  }

  const jsonPrompt = path.join(promptsDir, `${id}.json`);
  const markdownPrompt = path.join(promptsDir, `${id}.md`);
  if (fs.existsSync(jsonPrompt)) {
    jsonPromptCount += 1;
    const prompt = readJson(jsonPrompt);
    if (!Array.isArray(prompt.tags) || prompt.tags.length < 35) issues.push(`${id}: fewer than 35 prompt tags`);
    for (const tag of [...(prompt.tags ?? []), ...(prompt.negativeAdditions ?? [])]) {
      if (!ledger[tag]) issues.push(`${id}: unverified tag ${tag}`);
    }
  } else if (fs.existsSync(markdownPrompt)) {
    markdownPilotPromptCount += 1;
  } else {
    issues.push(`${id}: missing prompt source`);
  }

  if (!character.latestRun) {
    issues.push(`${id}: missing latestRun`);
    continue;
  }
  const manifestPath = path.resolve(root, character.latestRun);
  if (!fs.existsSync(manifestPath)) {
    issues.push(`${id}: missing manifest`);
    continue;
  }
  const runDir = path.dirname(manifestPath);
  const manifest = readJson(manifestPath);
  if (manifest.status !== "qa_passed") issues.push(`${id}: manifest status ${manifest.status}`);
  if (manifest.qa?.technical !== "passed") issues.push(`${id}: technical QA ${manifest.qa?.technical}`);
  if (!String(manifest.qa?.visual ?? "").startsWith("passed")) issues.push(`${id}: visual QA ${manifest.qa?.visual}`);

  const resultPath = path.join(runDir, manifest.resultFile ?? "result.json");
  if (!fs.existsSync(resultPath)) {
    issues.push(`${id}: missing result.json`);
    continue;
  }
  const result = readJson(resultPath);
  if (result.statusCode !== 200 || result.width !== 832 || result.height !== 1216 || result.colorType !== 6 || result.hasAlphaChannel !== true) {
    issues.push(`${id}: invalid API image metadata`);
  }

  const candidatePath = path.resolve(runDir, manifest.candidateAsset ?? "");
  if (!manifest.candidateAsset || !fs.existsSync(candidatePath)) {
    issues.push(`${id}: missing candidate asset`);
  } else {
    const hash = sha256(candidatePath);
    if (hash !== result.sha256) issues.push(`${id}: candidate SHA-256 mismatch`);
    if (candidateHashes.has(hash)) issues.push(`${id}: duplicate candidate hash with ${candidateHashes.get(hash)}`);
    candidateHashes.set(hash, id);
  }

  if (!Array.isArray(manifest.rawAssets) || manifest.rawAssets.length === 0) {
    issues.push(`${id}: no raw asset listed`);
  } else {
    for (const raw of manifest.rawAssets) {
      const rawPath = path.resolve(runDir, raw);
      if (!fs.existsSync(rawPath)) issues.push(`${id}: missing raw asset ${raw}`);
      else if (sha256(rawPath) !== result.sha256) issues.push(`${id}: raw SHA-256 mismatch ${raw}`);
    }
  }
}

let failedRunCount = 0;
let preservedFailedRawCount = 0;
for (const entry of fs.readdirSync(runsDir, { withFileTypes: true })) {
  if (!entry.isDirectory()) continue;
  const manifestPath = path.join(runsDir, entry.name, "manifest.json");
  if (!fs.existsSync(manifestPath)) continue;
  const manifest = readJson(manifestPath);
  if (manifest.status !== "qa_failed") continue;
  failedRunCount += 1;
  for (const raw of manifest.rawAssets ?? []) {
    if (fs.existsSync(path.resolve(path.dirname(manifestPath), raw))) preservedFailedRawCount += 1;
    else issues.push(`${entry.name}: failed raw asset missing ${raw}`);
  }
}

const report = {
  schemaVersion: 1,
  master: path.relative(root, masterPath).replaceAll("\\", "/"),
  targetCount: master.targetCount,
  recordCount: master.characters.length,
  qaPassedCount: master.characters.filter((entry) => entry.productionStatus === "qa_passed").length,
  approvedCount,
  uniqueCandidateCount: candidateHashes.size,
  jsonPromptCount,
  markdownPilotPromptCount,
  failedRunCount,
  preservedFailedRawCount,
  issues
};

fs.writeFileSync(path.join(root, "control", "production-audit.json"), `${JSON.stringify(report, null, 2)}\n`, "utf8");
console.log(JSON.stringify(report, null, 2));
if (issues.length) process.exitCode = 1;
