import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

function parseArgs(argv) {
  const args = {};
  for (let i = 2; i < argv.length; i += 2) {
    const key = argv[i];
    const value = argv[i + 1];
    if (!key?.startsWith("--") || value === undefined) {
      throw new Error("Usage: node prepare-run.mjs --prompt-file <json> --run-id <id> --human-initiated-at <iso8601>");
    }
    args[key.slice(2)] = value;
  }
  return args;
}

function writeJson(filePath, value, flag) {
  fs.writeFileSync(filePath, `${JSON.stringify(value, null, 2)}\n`, flag ? { flag } : undefined);
}

const args = parseArgs(process.argv);
for (const required of ["prompt-file", "run-id", "human-initiated-at"]) {
  if (!args[required]) throw new Error(`Missing --${required}`);
}

const here = path.dirname(fileURLToPath(import.meta.url));
const productionRoot = path.resolve(here, "..");
const profile = JSON.parse(fs.readFileSync(path.resolve(productionRoot, "control", "api-profile.json"), "utf8"));
const verified = JSON.parse(fs.readFileSync(path.resolve(productionRoot, "control", "verified-tags.json"), "utf8"));
const controlPath = path.resolve(productionRoot, "control", "portrait-master.json");
const control = JSON.parse(fs.readFileSync(controlPath, "utf8"));
const promptPath = path.resolve(args["prompt-file"]);
const promptSpec = JSON.parse(fs.readFileSync(promptPath, "utf8"));
const character = control.characters.find((item) => item.id === promptSpec.characterId);
if (!character) throw new Error(`Character is not in control: ${promptSpec.characterId}`);
if (character.name !== promptSpec.characterName) throw new Error(`Character name mismatch: ${character.name} vs ${promptSpec.characterName}`);
if (!Array.isArray(promptSpec.tags) || promptSpec.tags.length === 0) throw new Error("Prompt tags are empty");

const duplicateTags = [...new Set(promptSpec.tags.filter((tag, index) => promptSpec.tags.indexOf(tag) !== index))];
if (duplicateTags.length) throw new Error(`Duplicate prompt tags: ${duplicateTags.join(", ")}`);
const unverifiedTags = promptSpec.tags.filter((tag) => !verified.tags[tag]);
if (unverifiedTags.length) throw new Error(`Unverified prompt tags: ${unverifiedTags.join(", ")}`);
const countZeroTags = promptSpec.tags.filter((tag) => verified.tags[tag]?.count === 0 && verified.tags[tag]?.source !== "user_locked");
if (countZeroTags.length) throw new Error(`Danbooru count-zero tags are forbidden: ${countZeroTags.join(", ")}`);
const negativeAdditions = promptSpec.negativeAdditions ?? [];
const unverifiedNegativeTags = negativeAdditions.filter((tag) => !verified.tags[tag]);
if (unverifiedNegativeTags.length) throw new Error(`Unverified negative tags: ${unverifiedNegativeTags.join(", ")}`);
const countZeroNegativeTags = negativeAdditions.filter((tag) => verified.tags[tag]?.count === 0 && verified.tags[tag]?.source !== "user_locked");
if (countZeroNegativeTags.length) throw new Error(`Danbooru count-zero negative tags are forbidden: ${countZeroNegativeTags.join(", ")}`);
if (!promptSpec.tags.includes("transparent_background")) throw new Error("Character prompt must include transparent_background");

const naturalDetail = promptSpec.naturalLanguageDetail?.trim();
if (!naturalDetail) throw new Error("Exactly one natural-language detail sentence is required");
const sentenceEndings = (naturalDetail.match(/[.!?](?:\s|$)/g) ?? []).length;
if (sentenceEndings !== 1 || !/[.!?]$/.test(naturalDetail)) {
  throw new Error("naturalLanguageDetail must be exactly one sentence ending in punctuation");
}

const characterPrompt = `${promptSpec.tags.map((tag) => tag.replaceAll("_", " ")).join(", ")}. ${naturalDetail}`;
const seedBytes = crypto.createHash("sha256").update(`${promptSpec.characterId}:v${promptSpec.version}`).digest();
const seed = promptSpec.seed ?? (seedBytes.readUInt32BE(0) & 0x7fffffff);
const negativePrompt = [profile.negativePrompt, ...negativeAdditions.map((tag) => tag.replaceAll("_", " "))].filter(Boolean).join(", ");
const runDir = path.resolve(productionRoot, "runs", args["run-id"]);
if (fs.existsSync(runDir)) throw new Error(`Run directory already exists: ${runDir}`);
fs.mkdirSync(runDir, { recursive: true });

const condition = {
  caption: {
    base_caption: profile.basePrompt,
    char_captions: [{ char_caption: characterPrompt, centers: [{ x: 0.5, y: 0.5 }] }]
  },
  use_coords: false,
  use_order: true,
  legacy_uc: false
};
const negativeCondition = {
  caption: {
    base_caption: negativePrompt,
    char_captions: [{ char_caption: "", centers: [{ x: 0.5, y: 0.5 }] }]
  },
  use_coords: false,
  use_order: false,
  legacy_uc: false
};

const request = {
  meta: {
    schemaVersion: 1,
    runId: args["run-id"],
    characterId: promptSpec.characterId,
    characterName: promptSpec.characterName,
    promptVersion: promptSpec.version,
    designStatus: promptSpec.designStatus,
    designAssumptions: promptSpec.designAssumptions ?? [],
    humanInitiated: true,
    humanInitiatedAt: args["human-initiated-at"],
    apiSpec: "https://image.novelai.net/docs/doc.json",
    templateUse: "metadata-import-only",
    templateSha256: "b9e7060cb53ec6a372239fc17682c62ffbfbabaff7f4f623247baabe7fb24fc0",
    promptFile: path.relative(productionRoot, promptPath).replaceAll("\\", "/"),
    credentialPolicy: "runtime-only; never logged"
  },
  payload: {
    action: "generate",
    input: profile.basePrompt,
    model: profile.model,
    parameters: {
      ...profile.parameters,
      seed,
      negative_prompt: negativePrompt,
      prompt: profile.basePrompt,
      v4_prompt: condition,
      v4_negative_prompt: negativeCondition
    }
  }
};
const manifest = {
  schemaVersion: 1,
  runId: args["run-id"],
  characterId: promptSpec.characterId,
  characterName: promptSpec.characterName,
  designStatus: promptSpec.designStatus,
  status: "queued",
  requestFile: "request.json",
  resultFile: null,
  rawAssets: [],
  candidateAsset: null,
  qa: { technical: "pending", visual: "pending", notes: [] }
};
writeJson(path.resolve(runDir, "request.json"), request, "wx");
writeJson(path.resolve(runDir, "manifest.json"), manifest, "wx");

character.promptStatus = "verified";
character.productionStatus = "queued";
character.latestRun = path.relative(productionRoot, path.resolve(runDir, "manifest.json")).replaceAll("\\", "/");
control.updatedAt = new Date().toISOString();
writeJson(controlPath, control);
console.log(`Prepared ${promptSpec.characterId} ${promptSpec.characterName}; tags=${promptSpec.tags.length}; seed=${seed}; run=${args["run-id"]}`);
