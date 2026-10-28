import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const args = {};
for (let i = 2; i < process.argv.length; i += 2) {
  if (!process.argv[i]?.startsWith("--") || process.argv[i + 1] === undefined) throw new Error("Usage: node generate-novelai-i2i.mjs --request <json> --token-file <file> --output <png>");
  args[process.argv[i].slice(2)] = process.argv[i + 1];
}
for (const key of ["request", "token-file", "output"]) if (!args[key]) throw new Error(`Missing --${key}`);
const requestPath = path.resolve(args.request), runDir = path.dirname(requestPath), outputPath = path.resolve(args.output);
const document = JSON.parse(fs.readFileSync(requestPath, "utf8"));
const { meta, payload } = document;
if (meta?.humanInitiated !== true || meta?.workflow !== "img2img") throw new Error("Not a human-initiated i2i request");
if (payload?.model !== "nai-diffusion-5-curated" || payload?.action !== "img2img") throw new Error("Unexpected model/action");
if (payload.parameters?.n_samples !== 1 || payload.parameters?.straight_alpha !== true || payload.parameters?.tag_hint_transparent_background !== true) throw new Error("Required single-sample transparent controls missing");
if (payload.parameters?.strength !== 0.5 || payload.parameters?.noise !== 0.5 || !payload.parameters?.image) throw new Error("i2i must include image with strength=noise=0.5");
if (fs.existsSync(outputPath)) throw new Error(`Refusing overwrite: ${outputPath}`);
const token = fs.readFileSync(path.resolve(args["token-file"]), "utf8").trim();
if (!token) throw new Error("Token file is empty");
const correlationId = crypto.randomBytes(3).toString("hex");
const response = await fetch("https://image.novelai.net/ai/generate-image", { method: "POST", headers: { Authorization: `Bearer ${token}`, Accept: "application/json", "Content-Type": "application/json", "x-correlation-id": correlationId }, body: JSON.stringify(payload) });
const responseText = await response.text();
if (!response.ok) {
  let safe = responseText;
  try { const parsed = JSON.parse(responseText); safe = parsed.message ?? parsed.error ?? JSON.stringify(parsed); } catch {}
  throw new Error(`NovelAI HTTP ${response.status}; correlation=${correlationId}; ${safe}`);
}
const parsed = JSON.parse(responseText); const item = parsed.images?.[0] ?? parsed[0];
if (!item?.image) throw new Error("NovelAI response contains no image");
const image = Buffer.from(item.image, "base64");
if (image.subarray(0, 8).toString("hex") !== "89504e470d0a1a0a" || image.subarray(12, 16).toString("ascii") !== "IHDR") throw new Error("Response is not PNG");
const width = image.readUInt32BE(16), height = image.readUInt32BE(20), colorType = image[25], hasAlphaChannel = colorType === 4 || colorType === 6;
fs.writeFileSync(outputPath, image, { flag: "wx" });
const result = { schemaVersion: 1, runId: meta.runId, characterId: meta.characterId, model: payload.model, workflow: "img2img", denoiseStrength: payload.parameters.strength, statusCode: response.status, correlationId, apiSeed: item.seed ?? payload.parameters.seed, imageIndex: item.index ?? 0, output: path.basename(outputPath), sha256: crypto.createHash("sha256").update(image).digest("hex"), width, height, colorType, hasAlphaChannel, generatedAt: new Date().toISOString() };
fs.writeFileSync(path.resolve(runDir, "result.json"), `${JSON.stringify(result, null, 2)}\n`, { flag: "wx" });
const manifestPath = path.resolve(runDir, "manifest.json"); const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
manifest.status = "downloaded"; manifest.resultFile = "result.json"; manifest.rawAssets = [path.relative(runDir, outputPath).replaceAll("\\", "/")]; manifest.qa.technical = hasAlphaChannel && width === payload.parameters.width && height === payload.parameters.height ? "passed" : "failed"; manifest.qa.notes.push(`API PNG ${width}x${height}; colorType=${colorType}; alpha=${hasAlphaChannel}; sha256=${result.sha256}`); fs.writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);
const here = path.dirname(fileURLToPath(import.meta.url)); const root = path.resolve(here, ".."); const masterPath = path.resolve(root, "control", "portrait-master.json"); const master = JSON.parse(fs.readFileSync(masterPath, "utf8")); const character = master.characters.find((x) => x.id === meta.characterId); if (character) { character.productionStatus = "downloaded"; character.latestRun = path.relative(root, manifestPath).replaceAll("\\", "/"); master.updatedAt = new Date().toISOString(); fs.writeFileSync(masterPath, `${JSON.stringify(master, null, 2)}\n`); }
console.log(`NovelAI i2i OK: ${meta.characterId}; ${width}x${height}; alpha=${hasAlphaChannel}; strength=0.5; correlation=${correlationId}`);
