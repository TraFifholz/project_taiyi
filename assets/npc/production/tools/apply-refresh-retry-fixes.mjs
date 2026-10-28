import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const fixes = {
  "LS-NPC-018": {
    remove: ["prosthetic_hand", "cyborg"],
    detail: "A tall thin twenty-eight-year-old Chinese research engineer in an asymmetric lab jacket spins one plain pen between exactly two articulated metal fingertips on his left hand while every other finger and both palms remain human, with the small old palm burns and short nails visible under soft even frontal studio light."
  },
  "LS-NPC-027": {
    negative: ["mechanical_legs"],
    detail: "A thick-backed forty-six-year-old Chinese underground night-shift captain in high-visibility tunneling gear looks back while carrying a yellow hard hat, with only his left lower leg below the knee replaced by one scarred industrial prosthesis and his right leg entirely human under soft even frontal studio light."
  },
  "LS-NPC-065": {
    remove: ["business_suit", "suit", "blazer", "blue_jacket", "jacket", "open_jacket", "open_clothes", "grey_shirt", "collared_shirt", "black_pants", "brown_shoes"],
    add: ["techwear", "harness", "utility_belt", "pouch"],
    detail: "A lean thirty-two-year-old Chinese port logistics consultant with short side-parted black hair wears a tailored slate bomber jacket over asymmetric utility streetwear, cargo trousers, compact harness and hidden ultraviolet eagle mark under soft even frontal studio light."
  },
  "LS-NPC-068": {
    detail: "A tall solemn forty-year-old woman with a warm medium complexion and a low black-and-silver bun wears a modest ankle-length black dress beneath a weathered port coat and one small silver eagle pendant, her head raised and hands resting together under soft even frontal studio light."
  },
  "LS-NPC-081": {
    negative: ["white_background"],
    detail: "A tired bare-faced twenty-seven-year-old Chinese doctoral student with a messy low black ponytail wears a loosely layered laboratory outfit and visible nape interface, holding three cream sketch sheets and one wooden pencil against a genuinely transparent backdrop under soft even frontal studio light."
  }
};

for (const [id, fix] of Object.entries(fixes)) {
  const file = path.join(root, "prompts", `${id}.json`);
  const prompt = JSON.parse(fs.readFileSync(file, "utf8"));
  let tags = prompt.tags.filter((tag) => !(fix.remove ?? []).includes(tag) && tag !== "transparent_background");
  for (const tag of fix.add ?? []) if (!tags.includes(tag)) tags.push(tag);
  tags.push("transparent_background");
  prompt.tags = tags;
  prompt.negativeAdditions = [...new Set([...(prompt.negativeAdditions ?? []), ...(fix.negative ?? [])])];
  prompt.naturalLanguageDetail = fix.detail;
  prompt.version += 1;
  prompt.designAssumptions.push(`Targeted retry after visual QA: ${fix.detail}`);
  fs.writeFileSync(file, `${JSON.stringify(prompt, null, 2)}\n`);
  console.log(`${id} -> v${prompt.version}`);
}
