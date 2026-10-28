import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const ids = new Set(["LS-NPC-097", "LS-NPC-099", "LS-NPC-102"]);
const read = (name) => JSON.parse(fs.readFileSync(path.join(root, "control", name), "utf8"));
const write = (name, data) => fs.writeFileSync(path.join(root, "control", name), `${JSON.stringify(data, null, 2)}\n`, "utf8");
const master = read("portrait-master.json");
const plan = read("visual-refresh-plan.json");
const review = read("review-decisions.json");
const retiredPath = path.join(root, "control", "retired-characters.json");
const retired = fs.existsSync(retiredPath)
  ? JSON.parse(fs.readFileSync(retiredPath, "utf8"))
  : { schemaVersion: 1, updatedAt: null, characters: [] };
const retiredById = new Map(retired.characters.map((item) => [item.id, item]));

for (const character of master.characters.filter((item) => ids.has(item.id))) {
  retiredById.set(character.id, {
    ...character,
    retirementReason: "One-shot NPC; user confirmed no future appearance is planned.",
    retiredAt: new Date().toISOString(),
    lastReviewDecision: review.decisions?.[character.id] ?? null,
    promptEvidence: `prompts/${character.id}.json`
  });
}
master.characters = master.characters.filter((item) => !ids.has(item.id));
master.targetCount = master.characters.length;
master.updatedAt = new Date().toISOString();

plan.entries = plan.entries.filter((item) => !ids.has(item.id));
plan.targetPopulation = plan.entries.length;
plan.counts = {
  cyberpunkSignal: plan.entries.filter((item) => item.layer === "cyberpunk-signal").length,
  diverseCivic: plan.entries.filter((item) => item.layer === "diverse-civic").length,
  refresh: plan.entries.filter((item) => item.refresh).length,
  retain: plan.entries.filter((item) => !item.refresh).length
};
plan.policy.cyberpunkSignalTarget = `${plan.counts.cyberpunkSignal}/${plan.targetPopulation}; target will be raised during rejected-character cyborg revisions`;
plan.policy.remainderTarget = `${plan.counts.diverseCivic}/${plan.targetPopulation}; maintain diverse non-cyber silhouettes`;
plan.updatedAt = new Date().toISOString();

for (const id of ids) delete review.decisions[id];
review.updatedAt = new Date().toISOString();
retired.characters = [...retiredById.values()].sort((a, b) => a.id.localeCompare(b.id));
retired.updatedAt = new Date().toISOString();

write("portrait-master.json", master);
write("visual-refresh-plan.json", plan);
write("review-decisions.json", review);
fs.writeFileSync(retiredPath, `${JSON.stringify(retired, null, 2)}\n`, "utf8");
console.log(`Retired ${ids.size} one-shot characters; active roster=${master.targetCount}. Historical prompts/runs/assets preserved.`);
