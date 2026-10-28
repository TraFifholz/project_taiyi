import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const ids = ["050", "054", "055", "056", "059", "060", "063", "068", "069", "070", "072", "074", "089", "090", "095", "096", "098", "101", "103", "105", "N1", "N2"];
for (const suffix of ids) {
  const file = path.join(root, "prompts", `LS-NPC-${suffix}.json`);
  const prompt = JSON.parse(fs.readFileSync(file, "utf8"));
  prompt.naturalLanguageDetail = prompt.naturalLanguageDetail.replace(
    /\. The portrait is framed/g,
    "; the portrait is framed"
  );
  fs.writeFileSync(file, `${JSON.stringify(prompt, null, 2)}\n`, "utf8");
}
console.log(`Normalized ${ids.length} cowboy-shot details to one sentence.`);
