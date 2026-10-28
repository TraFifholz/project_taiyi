import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const masterPath = path.join(root, "control", "portrait-master.json");
const planPath = path.join(root, "control", "visual-refresh-plan.json");
const master = JSON.parse(fs.readFileSync(masterPath, "utf8"));
const plan = JSON.parse(fs.readFileSync(planPath, "utf8"));
const planById = new Map(plan.entries.map((entry) => [entry.id, entry]));

for (const character of master.characters) {
  const entry = planById.get(character.id);
  if (!entry) throw new Error(`Missing visual plan entry: ${character.id}`);
  character.visualLayer = entry.layer;
  character.targetStyle = entry.targetStyle;
  character.visualDirective = entry.designDirective;
  character.visualRefresh = entry.refresh ? character.productionStatus : "retained";
}

master.visualRefreshPlan = "control/visual-refresh-plan.json";
master.visualRefreshPolicy = {
  cyberpunkSignal: plan.counts.cyberpunkSignal,
  diverseCivic: plan.counts.diverseCivic,
  refresh: plan.counts.refresh,
  retain: plan.counts.retain
};
master.updatedAt = new Date().toISOString();
fs.writeFileSync(masterPath, `${JSON.stringify(master, null, 2)}\n`, "utf8");
console.log(`Synced visual refresh evidence for ${master.characters.length} characters.`);
