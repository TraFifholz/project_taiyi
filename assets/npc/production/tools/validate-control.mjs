import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const productionRoot = path.resolve(here, "..");
const control = JSON.parse(fs.readFileSync(path.resolve(productionRoot, "control", "portrait-master.json"), "utf8"));
const retired = JSON.parse(fs.readFileSync(path.resolve(productionRoot, "control", "retired-characters.json"), "utf8"));
const reference = JSON.parse(fs.readFileSync(path.resolve(productionRoot, "control", "reference-manifest.json"), "utf8"));
const referencePath = path.resolve(productionRoot, reference.localCopy);
const errors = [];
const forbidden = new Set(["007", "010", "016", "020", "023", "028", "032", "036", "042", "047", "064", "071", "084", "087"]);
const imageRequestFields = ["image", "reference_image", "reference_image_multiple", "director_reference_images"];

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function sha256(filePath) {
  return crypto.createHash("sha256").update(fs.readFileSync(filePath)).digest("hex");
}

const expectedHistoricalCount = 96;
const expectedActiveCount = expectedHistoricalCount - retired.characters.length;
if (control.targetCount !== expectedActiveCount) errors.push(`targetCount=${control.targetCount}, expected ${expectedActiveCount}`);
if (control.characters.length !== expectedActiveCount) errors.push(`characters=${control.characters.length}, expected ${expectedActiveCount}`);
if (retired.characters.length !== 3) errors.push(`retired=${retired.characters.length}, expected 3`);

const ids = control.characters.map((item) => item.id);
const duplicates = [...new Set(ids.filter((id, index) => ids.indexOf(id) !== index))];
if (duplicates.length) errors.push(`duplicate ids: ${duplicates.join(", ")}`);

const leaked = ids.filter((id) => forbidden.has(id.replace("LS-NPC-", "")));
if (leaked.length) errors.push(`deleted ids leaked into control: ${leaked.join(", ")}`);
const retiredIds = new Set(retired.characters.map((item) => item.id));
const retiredLeaked = ids.filter((id) => retiredIds.has(id));
if (retiredLeaked.length) errors.push(`retired ids leaked into active control: ${retiredLeaked.join(", ")}`);

for (const required of ["LS-NPC-N1", "LS-NPC-N2", "LS-NPC-046", "LS-NPC-049", "LS-NPC-054"]) {
  if (!ids.includes(required)) errors.push(`missing required id: ${required}`);
}

if (!fs.existsSync(referencePath)) {
  errors.push(`missing reference: ${referencePath}`);
} else {
  const hash = sha256(referencePath);
  if (hash !== reference.sha256) errors.push(`reference hash mismatch: ${hash}`);
}
if (reference.intendedUse !== "metadata-import-only" || reference.requestAttachment !== "none") {
  errors.push("reference manifest must enforce metadata-import-only with no request attachment");
}

const gradeCounts = control.characters.reduce((acc, item) => {
  acc[item.grade] = (acc[item.grade] ?? 0) + 1;
  return acc;
}, {});
const retiredGradeCounts = retired.characters.reduce((acc, item) => {
  acc[item.grade] = (acc[item.grade] ?? 0) + 1;
  return acc;
}, {});
// Wen Sheng (LS-NPC-N3) was promoted from a provisional B card to a formal A card.
const expectedGrades = { A: 67 - (retiredGradeCounts.A ?? 0), B: 22 - (retiredGradeCounts.B ?? 0), C: 7 - (retiredGradeCounts.C ?? 0) };
if (gradeCounts.A !== expectedGrades.A || gradeCounts.B !== expectedGrades.B || gradeCounts.C !== expectedGrades.C) {
  errors.push(`grade counts=${JSON.stringify(gradeCounts)}, expected A${expectedGrades.A}/B${expectedGrades.B}/C${expectedGrades.C}`);
}

const pilot = control.characters.find((item) => item.id === control.pilotCharacterId);
if (!pilot) {
  errors.push(`missing pilot character: ${control.pilotCharacterId}`);
} else if (pilot.latestRun) {
  const manifestPath = path.resolve(productionRoot, pilot.latestRun);
  if (!fs.existsSync(manifestPath)) {
    errors.push(`missing pilot manifest: ${manifestPath}`);
  } else {
    const runDir = path.dirname(manifestPath);
    const manifest = readJson(manifestPath);
    if (manifest.status !== pilot.productionStatus) {
      errors.push(`pilot status mismatch: control=${pilot.productionStatus}, manifest=${manifest.status}`);
    }
    const requestPath = path.resolve(runDir, manifest.requestFile);
    if (!fs.existsSync(requestPath)) {
      errors.push(`missing pilot request: ${requestPath}`);
    } else {
      const request = readJson(requestPath);
      if (request.meta?.humanInitiated !== true) errors.push("pilot request lacks human initiation evidence");
      if (request.meta?.templateUse !== "metadata-import-only") errors.push("pilot request template use is not metadata-only");
      if (request.payload?.model !== "nai-diffusion-5-curated") errors.push(`pilot model=${request.payload?.model}`);
      if (request.payload?.parameters?.n_samples !== 1) errors.push("pilot request must generate exactly one image");
      for (const field of imageRequestFields) {
        if (field in (request.payload?.parameters ?? {})) errors.push(`pilot request contains forbidden image field: ${field}`);
      }
    }
    if (manifest.resultFile) {
      const resultPath = path.resolve(runDir, manifest.resultFile);
      if (!fs.existsSync(resultPath)) {
        errors.push(`missing pilot result: ${resultPath}`);
      } else {
        const result = readJson(resultPath);
        const rawPath = path.resolve(runDir, manifest.rawAssets?.[0] ?? "");
        if (!fs.existsSync(rawPath)) {
          errors.push(`missing pilot raw asset: ${rawPath}`);
        } else if (sha256(rawPath) !== result.sha256) {
          errors.push("pilot raw asset hash does not match result.json");
        }
        if (manifest.candidateAsset) {
          const candidatePath = path.resolve(runDir, manifest.candidateAsset);
          if (!fs.existsSync(candidatePath)) errors.push(`missing pilot candidate: ${candidatePath}`);
          else if (sha256(candidatePath) !== result.sha256) errors.push("pilot candidate hash does not match result.json");
        }
      }
    }
  }
}

if (errors.length) {
  console.error(errors.join("\n"));
  process.exit(1);
}

console.log(`Portrait control OK: ${control.characters.length} unique records; A${gradeCounts.A}/B${gradeCounts.B}/C${gradeCounts.C}; reference SHA-256 verified.`);
