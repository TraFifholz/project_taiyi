import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const ids = ["050", "054", "055", "056", "059", "060", "063", "068", "069", "070", "072", "074", "089", "090", "095", "096", "098", "101", "103", "105", "N1", "N2"];
const lowerBodyTags = new Set(["full_body", "shoes", "boots", "sneakers"]);
const cropNegatives = ["full_body", "shoes", "boots", "sneakers"];

for (const suffix of ids) {
  const id = `LS-NPC-${suffix}`;
  const file = path.join(root, "prompts", `${id}.json`);
  const prompt = JSON.parse(fs.readFileSync(file, "utf8"));
  prompt.version += 1;
  prompt.designAssumptions ??= [];
  prompt.designAssumptions.push("User-review crop correction: strict head-to-mid-thigh cowboy shot; lower legs and feet stay outside the image.");
  prompt.tags = [...new Set([...prompt.tags.filter((tag) => !lowerBodyTags.has(tag)), "cowboy_shot"] )];
  prompt.negativeAdditions = [...new Set([...(prompt.negativeAdditions ?? []), ...cropNegatives])];
  prompt.naturalLanguageDetail = `${prompt.naturalLanguageDetail.replace(/\s+$/, "")} The portrait is framed from head to mid-thigh in a strict cowboy shot, with lower legs and feet outside the image.`;
  fs.writeFileSync(file, `${JSON.stringify(prompt, null, 2)}\n`, "utf8");
  console.log(`${id} -> v${prompt.version}; tags=${prompt.tags.length}`);
}
