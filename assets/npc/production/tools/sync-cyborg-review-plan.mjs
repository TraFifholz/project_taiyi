import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const file = path.join(root, "control", "visual-refresh-plan.json");
const plan = JSON.parse(fs.readFileSync(file, "utf8"));
const updates = {
  "LS-NPC-008": ["integrated-service-cyborg", "integrated mechanical ears and a segmented synthetic voice module"],
  "LS-NPC-009": ["data-security-cyborg", "one full mechanical eye, exposed temple plate and articulated prosthetic hand"],
  "LS-NPC-033": ["driver-prosthesis", "a rugged exposed forearm prosthesis crossed over the drivers' appeal folder"],
  "LS-NPC-039": ["media-cyborg-fashion", "matched mechanical irises, polished ear implants and a visible voice interface"],
  "LS-NPC-058": ["accountant-cyborg", "one mechanical eye and an articulated accounting hand inside worn old knitwear"],
  "LS-NPC-077": ["bureaucrat-cyborg", "an expensive mechanical eye and impeccably articulated prosthetic hand behind a cold public image"],
  "LS-NPC-100": ["rehabilitation-doctor-cyborg", "one diagnostic mechanical eye and one exposed precision prosthetic forearm"],
  "LS-NPC-107": ["idol-cyborg", "matched mechanical eyes, cosmetic ear implants and one elegant prosthetic hand"]
};

for (const entry of plan.entries) {
  const update = updates[entry.id];
  if (!update) continue;
  entry.layer = "cyberpunk-signal";
  entry.targetStyle = update[0];
  entry.designDirective = update[1];
  entry.refresh = true;
}
plan.counts = {
  cyberpunkSignal: plan.entries.filter((entry) => entry.layer === "cyberpunk-signal").length,
  diverseCivic: plan.entries.filter((entry) => entry.layer === "diverse-civic").length,
  refresh: plan.entries.filter((entry) => entry.refresh).length,
  retain: plan.entries.filter((entry) => !entry.refresh).length
};
plan.policy.cyberpunkSignalTarget = `${plan.counts.cyberpunkSignal}/${plan.targetPopulation} = ${(100 * plan.counts.cyberpunkSignal / plan.targetPopulation).toFixed(1)}% after user-review cyborg increase`;
plan.policy.remainderTarget = `${plan.counts.diverseCivic}/${plan.targetPopulation} = ${(100 * plan.counts.diverseCivic / plan.targetPopulation).toFixed(1)}%, preserving varied non-cyber silhouettes`;
plan.updatedAt = new Date().toISOString();
fs.writeFileSync(file, `${JSON.stringify(plan, null, 2)}\n`, "utf8");
console.log(`Cyborg layer=${plan.counts.cyberpunkSignal}/${plan.targetPopulation}; diverse=${plan.counts.diverseCivic}.`);
