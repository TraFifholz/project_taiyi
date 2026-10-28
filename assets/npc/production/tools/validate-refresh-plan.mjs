import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const plan = JSON.parse(fs.readFileSync(path.join(root, "control", "visual-refresh-plan.json"), "utf8"));
const ledger = JSON.parse(fs.readFileSync(path.join(root, "control", "verified-tags.json"), "utf8")).tags;
const issues = [];
for (const entry of plan.entries.filter((item) => item.refresh)) {
  const file = path.join(root, "prompts", `${entry.id}.json`);
  if (!fs.existsSync(file)) { issues.push(`${entry.id}: missing JSON prompt`); continue; }
  const prompt = JSON.parse(fs.readFileSync(file, "utf8"));
  const duplicates = prompt.tags.filter((tag, index) => prompt.tags.indexOf(tag) !== index);
  if (duplicates.length) issues.push(`${entry.id}: duplicate tags ${[...new Set(duplicates)].join(",")}`);
  for (const tag of [...prompt.tags, ...(prompt.negativeAdditions ?? [])]) if (!ledger[tag]) issues.push(`${entry.id}: unverified ${tag}`);
  if (prompt.tags.length < 35) issues.push(`${entry.id}: only ${prompt.tags.length} tags`);
  if (!prompt.tags.includes("transparent_background")) issues.push(`${entry.id}: missing transparent_background`);
  const ends = prompt.naturalLanguageDetail.match(/[.!?](?:\s|$)/g) ?? [];
  if (ends.length !== 1 || !/[.!?]$/.test(prompt.naturalLanguageDetail)) issues.push(`${entry.id}: natural detail is not exactly one sentence`);
}
const result = { target: plan.targetPopulation, cyberpunkSignal: plan.counts.cyberpunkSignal, diverseCivic: plan.counts.diverseCivic, refresh: plan.counts.refresh, issues };
console.log(JSON.stringify(result, null, 2));
if (issues.length) process.exitCode = 1;
