import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

function parseArgs(argv) {
  const args = {};
  for (let i = 2; i < argv.length; i += 2) {
    const key = argv[i];
    const value = argv[i + 1];
    if (!key?.startsWith("--") || value === undefined) throw new Error("Usage: node prepare-i2i-run.mjs --prompt-file <json> --reference <png> --run-id <id> --human-initiated-at <iso8601> --strength 0.5");
    args[key.slice(2)] = value;
  }
  return args;
}
const writeJson = (p, v, flag) => fs.writeFileSync(p, `${JSON.stringify(v, null, 2)}\n`, flag ? { flag } : undefined);
const args = parseArgs(process.argv);
for (const key of ["prompt-file", "reference", "run-id", "human-initiated-at", "strength"]) if (!args[key]) throw new Error(`Missing --${key}`);
const strength = Number(args.strength);
if (strength !== 0.5) throw new Error(`This identity workflow is locked to strength 0.5, got ${args.strength}`);

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..");
const profile = JSON.parse(fs.readFileSync(path.resolve(root, "control", "api-profile.json"), "utf8"));
const verified = JSON.parse(fs.readFileSync(path.resolve(root, "control", "verified-tags.json"), "utf8"));
const masterPath = path.resolve(root, "control", "portrait-master.json");
const master = JSON.parse(fs.readFileSync(masterPath, "utf8"));
const promptPath = path.resolve(args["prompt-file"]);
const referencePath = path.resolve(args.reference);
const prompt = JSON.parse(fs.readFileSync(promptPath, "utf8"));
const character = master.characters.find((x) => x.id === prompt.characterId);
if (!character || character.name !== prompt.characterName) throw new Error("Prompt/control identity mismatch");
if (!fs.existsSync(referencePath)) throw new Error(`Missing reference ${referencePath}`);
const png = fs.readFileSync(referencePath);
if (png.subarray(0, 8).toString("hex") !== "89504e470d0a1a0a") throw new Error("i2i reference must be PNG");
const width = png.readUInt32BE(16), height = png.readUInt32BE(20);
if (width !== profile.parameters.width || height !== profile.parameters.height) throw new Error(`Reference dimensions ${width}x${height} do not match profile`);
for (const tag of [...prompt.tags, ...(prompt.negativeAdditions ?? [])]) {
  if (!verified.tags[tag]) throw new Error(`Unverified tag: ${tag}`);
  if (verified.tags[tag].count === 0 && verified.tags[tag].source !== "user_locked") throw new Error(`Count-zero tag: ${tag}`);
}
if (!prompt.tags.includes("transparent_background") || !prompt.tags.includes("cowboy_shot")) throw new Error("Required transparent_background/cowboy_shot tags missing");
const detail = prompt.naturalLanguageDetail?.trim();
if (!detail || (detail.match(/[.!?](?:\s|$)/g) ?? []).length !== 1 || !/[.!?]$/.test(detail)) throw new Error("Exactly one natural-language sentence is required");

const charPrompt = `${prompt.tags.map((t) => t.replaceAll("_", " ")).join(", ")}. ${detail}`;
const negativePrompt = [profile.negativePrompt, ...(prompt.negativeAdditions ?? []).map((t) => t.replaceAll("_", " "))].join(", ");
const condition = { caption: { base_caption: profile.basePrompt, char_captions: [{ char_caption: charPrompt, centers: [{ x: 0.5, y: 0.5 }] }] }, use_coords: false, use_order: true, legacy_uc: false };
const negativeCondition = { caption: { base_caption: negativePrompt, char_captions: [{ char_caption: "", centers: [{ x: 0.5, y: 0.5 }] }] }, use_coords: false, use_order: false, legacy_uc: false };
const runDir = path.resolve(root, "runs", args["run-id"]);
if (fs.existsSync(runDir)) throw new Error(`Run already exists: ${runDir}`);
fs.mkdirSync(runDir, { recursive: true });
const request = {
  meta: {
    schemaVersion: 1, runId: args["run-id"], characterId: prompt.characterId, characterName: prompt.characterName,
    promptVersion: prompt.version, designStatus: prompt.designStatus, designAssumptions: prompt.designAssumptions ?? [],
    humanInitiated: true, humanInitiatedAt: args["human-initiated-at"], apiSpec: "https://image.novelai.net/docs/doc.json",
    workflow: "img2img", denoiseStrength: strength,
    referenceFile: path.relative(root, referencePath).replaceAll("\\", "/"),
    referenceSha256: crypto.createHash("sha256").update(png).digest("hex"),
    credentialPolicy: "runtime-only; never logged"
  },
  payload: {
    action: "img2img", input: profile.basePrompt, model: profile.model,
    parameters: { ...profile.parameters, seed: prompt.seed, negative_prompt: negativePrompt, prompt: profile.basePrompt, v4_prompt: condition, v4_negative_prompt: negativeCondition, image: png.toString("base64"), strength, noise: strength, color_correct: true }
  }
};
const manifest = { schemaVersion: 1, runId: args["run-id"], characterId: prompt.characterId, characterName: prompt.characterName, designStatus: prompt.designStatus, status: "queued", requestFile: "request.json", resultFile: null, rawAssets: [], candidateAsset: null, qa: { technical: "pending", visual: "pending", notes: [`i2i identity reference; strength=${strength}; noise=${strength}; refSha256=${request.meta.referenceSha256}`] } };
writeJson(path.resolve(runDir, "request.json"), request, "wx");
writeJson(path.resolve(runDir, "manifest.json"), manifest, "wx");
character.promptStatus = "verified"; character.productionStatus = "queued"; character.latestRun = path.relative(root, path.resolve(runDir, "manifest.json")).replaceAll("\\", "/");
master.updatedAt = new Date().toISOString(); writeJson(masterPath, master);
console.log(`Prepared i2i ${prompt.characterId}; strength=${strength}; ref=${path.basename(referencePath)}; run=${args["run-id"]}`);

