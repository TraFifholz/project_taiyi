import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const productionRoot = path.resolve(here, "..");
const sourcePath = path.resolve(productionRoot, "../../../campaign/npcs/reference/NPC立绘设定终稿.md");
const outputPath = path.resolve(productionRoot, "control", "portrait-master.json");

if (fs.existsSync(outputPath)) {
  throw new Error(`Refusing to overwrite existing control file: ${outputPath}`);
}

const source = fs.readFileSync(sourcePath, "utf8");
const rows = source
  .split(/\r?\n/)
  .filter((line) => /^\| LS-NPC-(?:\d{3}|N[12]) \|/.test(line))
  .map((line) => line.split("|").slice(1, -1).map((cell) => cell.trim()));

const statusByGrade = {
  A: "source_ready",
  B: "needs_design",
  C: "blocked_gm"
};

const characters = rows.map((cells) => {
  const [id, gradePriority, name, organization, marker, , , , , , , unknowns, sourceLocator] = cells;
  const [grade, priority] = gradePriority.split("／");
  return {
    id,
    name,
    organization,
    marker,
    grade,
    priority,
    sourceStatus: statusByGrade[grade],
    promptStatus: "not_started",
    productionStatus: "not_started",
    approvedAsset: null,
    latestRun: null,
    unknowns,
    sourceLocator
  };
});

const control = {
  schemaVersion: 1,
  updatedAt: "2026-08-29",
  project: "龙散市 NPC NovelAI 立绘",
  targetCount: 95,
  sourceFile: "../../../campaign/npcs/reference/NPC立绘设定终稿.md",
  finalOpinionFile: "../../../campaign/npcs/reference/NPC最终意见版.md",
  model: "NAI Diffusion V5 Curated",
  mode: "Anime",
  transparentBackground: true,
  defaultResolution: { width: 832, height: 1216 },
  referenceManifest: "control/reference-manifest.json",
  stylePromptPolicy: "control/prompt-policy.md",
  pilotCharacterId: "LS-NPC-021",
  characters
};

fs.writeFileSync(outputPath, `${JSON.stringify(control, null, 2)}\n`, "utf8");
console.log(`Initialized ${characters.length} portrait records at ${outputPath}`);

