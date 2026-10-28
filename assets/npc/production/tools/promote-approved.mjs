import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const masterPath = path.join(root, "control", "portrait-master.json");
const decisionsPath = path.join(root, "control", "review-decisions.json");
const approvedDir = path.join(root, "assets", "approved");
const master = JSON.parse(fs.readFileSync(masterPath, "utf8"));
const review = JSON.parse(fs.readFileSync(decisionsPath, "utf8"));
const hash = (file) => crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");
const safeName = (value) => value.replace(/[<>:"/\\|?*]/g, "_");
let promoted = 0;
let unchanged = 0;

fs.mkdirSync(approvedDir, { recursive: true });
for (const character of master.characters) {
  const decision = review.decisions?.[character.id];
  if (decision?.decision !== "pass") continue;
  const manifestPath = path.resolve(root, character.latestRun);
  const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
  if (decision.runId && decision.runId !== manifest.runId) {
    throw new Error(`${character.id}: pass decision belongs to ${decision.runId}, latest is ${manifest.runId}`);
  }
  if (manifest.status !== "qa_passed" || !manifest.candidateAsset) {
    throw new Error(`${character.id}: latest candidate is not QA-passed`);
  }
  const source = path.resolve(path.dirname(manifestPath), manifest.candidateAsset);
  const filename = `${character.id}-${safeName(character.name)}-${manifest.runId}.png`;
  const destination = path.join(approvedDir, filename);
  if (fs.existsSync(destination)) {
    if (hash(source) !== hash(destination)) throw new Error(`${character.id}: approved destination collision`);
    unchanged += 1;
  } else {
    fs.copyFileSync(source, destination, fs.constants.COPYFILE_EXCL);
    promoted += 1;
  }
  character.approvedAsset = path.relative(root, destination).replaceAll("\\", "/");
  character.approvedRun = manifest.runId;
  character.approvedSha256 = hash(destination);
  character.approvedAt = decision.updatedAt;
}

master.updatedAt = new Date().toISOString();
fs.writeFileSync(masterPath, `${JSON.stringify(master, null, 2)}\n`, "utf8");
console.log(`Approved assets: promoted=${promoted}, unchanged=${unchanged}, total=${promoted + unchanged}`);
