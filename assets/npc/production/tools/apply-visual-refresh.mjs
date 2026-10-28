import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const plan = JSON.parse(fs.readFileSync(path.join(root, "control", "visual-refresh-plan.json"), "utf8"));
const ledger = JSON.parse(fs.readFileSync(path.join(root, "control", "verified-tags.json"), "utf8")).tags;
const genericDarkTags = new Set(["business_suit", "formal_clothes", "black_suit", "black_jacket", "black_pants", "black_necktie"]);
let updated = 0;

for (const entry of plan.entries.filter((item) => item.refresh)) {
  const promptPath = path.join(root, "prompts", `${entry.id}.json`);
  if (!fs.existsSync(promptPath)) throw new Error(`${entry.id}: refresh requires a JSON prompt`);
  const prompt = JSON.parse(fs.readFileSync(promptPath, "utf8"));
  const missing = entry.addTags.filter((tag) => !ledger[tag]);
  if (missing.length) throw new Error(`${entry.id}: unverified tags ${missing.join(", ")}`);

  let tags = prompt.tags.filter((tag) => tag !== "transparent_background");
  if (entry.layer === "diverse-civic") tags = tags.filter((tag) => !genericDarkTags.has(tag));
  if (entry.id === "LS-NPC-057") tags = tags.filter((tag) => !["prosthetic_arm", "single_mechanical_arm"].includes(tag));
  for (const tag of entry.addTags) if (!tags.includes(tag)) tags.push(tag);
  tags.push("transparent_background");

  const previousDetail = prompt.naturalLanguageDetail.replace(/[.!?]\s*$/, "");
  let naturalLanguageDetail = `${previousDetail}; ${entry.designDirective}.`;
  if (entry.id === "LS-NPC-004") {
    naturalLanguageDetail = "A cold thirty-seven-year-old Chinese recovery operative extends his exposed mechanical right arm in command while his normal left hand wears a fitted five-fingered dark industrial glove of ordinary human proportions under soft even frontal studio light.";
  }
  if (entry.id === "LS-NPC-057") {
    naturalLanguageDetail = "A pressured Chinese collection enforcer in layered red streetwear displays a battered old Chongli prosthesis replacing only his right hand below the wrist while both forearms remain human beneath his sleeves under soft even frontal studio light.";
  }

  prompt.version += 1;
  prompt.designStatus = entry.layer === "cyberpunk-signal" ? "portrait-design-cyberpunk-refresh" : "portrait-design-diversity-refresh";
  prompt.designAssumptions ??= [];
  prompt.designAssumptions.push(`2026-08-29 visual refresh: ${entry.designDirective}`);
  prompt.sceneConcept = `${prompt.sceneConcept} Visual refresh: ${entry.designDirective}.`;
  prompt.tags = tags;
  prompt.naturalLanguageDetail = naturalLanguageDetail;
  if (entry.id === "LS-NPC-004") prompt.negativeAdditions = [...new Set([...(prompt.negativeAdditions ?? []), "oven_mitts"])];
  if (entry.id === "LS-NPC-057") prompt.negativeAdditions = [...new Set([...(prompt.negativeAdditions ?? []), "prosthetic_arm", "single_mechanical_arm"])];
  fs.writeFileSync(promptPath, `${JSON.stringify(prompt, null, 2)}\n`);
  updated += 1;
}

console.log(`Updated ${updated} prompt specs from visual-refresh-plan.json`);
