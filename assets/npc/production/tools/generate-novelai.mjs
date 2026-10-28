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
      throw new Error("Usage: node generate-novelai.mjs --request <file> --token-file <file> --output <png>");
    }
    args[key.slice(2)] = value;
  }
  return args;
}

function inspectPng(buffer) {
  const signature = "89504e470d0a1a0a";
  if (buffer.subarray(0, 8).toString("hex") !== signature) throw new Error("Response image is not a PNG");
  if (buffer.subarray(12, 16).toString("ascii") !== "IHDR") throw new Error("PNG IHDR chunk is missing");
  const width = buffer.readUInt32BE(16);
  const height = buffer.readUInt32BE(20);
  const colorType = buffer[25];
  return { width, height, colorType, hasAlphaChannel: colorType === 4 || colorType === 6 };
}

const args = parseArgs(process.argv);
for (const required of ["request", "token-file", "output"]) {
  if (!args[required]) throw new Error(`Missing --${required}`);
}

const requestPath = path.resolve(args.request);
const runDir = path.dirname(requestPath);
const tokenPath = path.resolve(args["token-file"]);
const outputPath = path.resolve(args.output);
const requestDocument = JSON.parse(fs.readFileSync(requestPath, "utf8"));
const { meta, payload } = requestDocument;

if (meta?.humanInitiated !== true) throw new Error("Refusing request without meta.humanInitiated=true");
if (payload?.model !== "nai-diffusion-5-curated") throw new Error(`Unexpected model: ${payload?.model}`);
if (payload?.parameters?.n_samples !== 1) throw new Error("Pilot workflow requires n_samples=1");
if (payload?.parameters?.straight_alpha !== true || payload?.parameters?.tag_hint_transparent_background !== true) {
  throw new Error("Transparent background controls are not both enabled");
}
for (const forbidden of ["image", "reference_image", "reference_image_multiple", "director_reference_images"]) {
  if (forbidden in payload.parameters) throw new Error(`Metadata-only workflow forbids parameters.${forbidden}`);
}
if (fs.existsSync(outputPath)) throw new Error(`Refusing to overwrite existing output: ${outputPath}`);

const token = fs.readFileSync(tokenPath, "utf8").trim();
if (!token) throw new Error("Token file is empty");
const correlationId = crypto.randomBytes(3).toString("hex");
const response = await fetch("https://image.novelai.net/ai/generate-image", {
  method: "POST",
  headers: {
    Authorization: `Bearer ${token}`,
    Accept: "application/json",
    "Content-Type": "application/json",
    "x-correlation-id": correlationId
  },
  body: JSON.stringify(payload)
});

const responseText = await response.text();
if (!response.ok) {
  let safeMessage = responseText;
  try {
    const parsed = JSON.parse(responseText);
    safeMessage = parsed.message ?? parsed.error ?? JSON.stringify(parsed);
  } catch {}
  throw new Error(`NovelAI HTTP ${response.status}; correlation=${correlationId}; ${safeMessage}`);
}

const parsed = JSON.parse(responseText);
const item = parsed.images?.[0] ?? parsed[0];
if (!item?.image) throw new Error("NovelAI JSON response did not contain images[0].image");
const image = Buffer.from(item.image, "base64");
const png = inspectPng(image);
fs.mkdirSync(path.dirname(outputPath), { recursive: true });
fs.writeFileSync(outputPath, image, { flag: "wx" });

const result = {
  schemaVersion: 1,
  runId: meta.runId,
  characterId: meta.characterId,
  model: payload.model,
  statusCode: response.status,
  correlationId,
  apiSeed: item.seed ?? payload.parameters.seed,
  imageIndex: item.index ?? 0,
  output: path.basename(outputPath),
  sha256: crypto.createHash("sha256").update(image).digest("hex"),
  ...png,
  generatedAt: new Date().toISOString()
};
const resultPath = path.resolve(runDir, "result.json");
fs.writeFileSync(resultPath, `${JSON.stringify(result, null, 2)}\n`, { flag: "wx" });

const manifestPath = path.resolve(runDir, "manifest.json");
if (fs.existsSync(manifestPath)) {
  const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
  manifest.status = "downloaded";
  manifest.resultFile = path.relative(runDir, resultPath).replaceAll("\\", "/");
  manifest.rawAssets = [path.relative(runDir, outputPath).replaceAll("\\", "/")];
  manifest.qa ??= { technical: "pending", visual: "pending", notes: [] };
  manifest.qa.technical = png.hasAlphaChannel && png.width === payload.parameters.width && png.height === payload.parameters.height ? "passed" : "failed";
  manifest.qa.notes ??= [];
  manifest.qa.notes.push(`API PNG ${png.width}x${png.height}; colorType=${png.colorType}; alpha=${png.hasAlphaChannel}; sha256=${result.sha256}`);
  fs.writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);
}

const here = path.dirname(fileURLToPath(import.meta.url));
const productionRoot = path.resolve(here, "..");
const controlPath = path.resolve(productionRoot, "control", "portrait-master.json");
if (fs.existsSync(controlPath)) {
  const control = JSON.parse(fs.readFileSync(controlPath, "utf8"));
  const character = control.characters.find((entry) => entry.id === meta.characterId);
  if (character) {
    character.productionStatus = "downloaded";
    character.latestRun = path.relative(productionRoot, manifestPath).replaceAll("\\", "/");
    control.updatedAt = new Date().toISOString();
    fs.writeFileSync(controlPath, `${JSON.stringify(control, null, 2)}\n`);
  }
}
console.log(`NovelAI generation OK: ${png.width}x${png.height}; alpha=${png.hasAlphaChannel}; seed=${result.apiSeed}; correlation=${correlationId}`);
console.log(`Saved: ${outputPath}`);
console.log(`Result: ${resultPath}`);
