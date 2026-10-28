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
      throw new Error("Usage: node record-qa.mjs --run-dir <dir> --decision <pass|fail> --note <text>");
    }
    args[key.slice(2)] = value;
  }
  return args;
}

function sha256(filePath) {
  return crypto.createHash("sha256").update(fs.readFileSync(filePath)).digest("hex");
}

const args = parseArgs(process.argv);
if (!args["run-dir"] || !["pass", "fail"].includes(args.decision) || !args.note) {
  throw new Error("Required: --run-dir, --decision pass|fail, --note");
}

const here = path.dirname(fileURLToPath(import.meta.url));
const productionRoot = path.resolve(here, "..");
const runDir = path.resolve(args["run-dir"]);
const manifestPath = path.resolve(runDir, "manifest.json");
const request = JSON.parse(fs.readFileSync(path.resolve(runDir, "request.json"), "utf8"));
const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
const result = JSON.parse(fs.readFileSync(path.resolve(runDir, manifest.resultFile), "utf8"));
const rawPath = path.resolve(runDir, manifest.rawAssets[0]);
if (!fs.existsSync(rawPath)) throw new Error(`Missing raw image: ${rawPath}`);
if (sha256(rawPath) !== result.sha256) throw new Error("Raw image hash mismatch");
manifest.qa ??= { technical: "pending", visual: "pending", notes: [] };
manifest.qa.notes ??= [];
manifest.qa.notes.push(args.note);

if (args.decision === "pass") {
  const safeName = request.meta.characterName.replace(/[\\/:*?"<>|]/g, "-");
  const candidateName = `${request.meta.characterId}-${safeName}-${request.meta.runId}-seed-${result.apiSeed}.png`;
  const candidatePath = path.resolve(productionRoot, "assets", "candidates", candidateName);
  if (fs.existsSync(candidatePath)) throw new Error(`Candidate already exists: ${candidatePath}`);
  fs.copyFileSync(rawPath, candidatePath, fs.constants.COPYFILE_EXCL);
  if (sha256(candidatePath) !== result.sha256) throw new Error("Candidate hash mismatch after copy");
  manifest.status = "qa_passed";
  manifest.candidateAsset = path.relative(runDir, candidatePath).replaceAll("\\", "/");
  manifest.qa.visual = "passed";
} else {
  manifest.status = "qa_failed";
  manifest.candidateAsset = null;
  manifest.qa.visual = "failed";
}
fs.writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);

const controlPath = path.resolve(productionRoot, "control", "portrait-master.json");
const control = JSON.parse(fs.readFileSync(controlPath, "utf8"));
const character = control.characters.find((entry) => entry.id === request.meta.characterId);
if (!character) throw new Error(`Character not found in control: ${request.meta.characterId}`);
character.productionStatus = manifest.status;
character.latestRun = path.relative(productionRoot, manifestPath).replaceAll("\\", "/");
control.updatedAt = new Date().toISOString();
fs.writeFileSync(controlPath, `${JSON.stringify(control, null, 2)}\n`);
console.log(`Recorded ${request.meta.characterId} QA=${manifest.status}; candidate=${manifest.candidateAsset ?? "none"}`);
