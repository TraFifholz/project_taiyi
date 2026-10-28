import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const decisionsPath = path.join(root, "control", "review-decisions.json");
const historyPath = path.join(root, "control", "review-decision-history.jsonl");
const plan = JSON.parse(fs.readFileSync(path.join(root, "control", "visual-refresh-plan.json"), "utf8"));
const data = JSON.parse(fs.readFileSync(decisionsPath, "utf8"));
const refreshed = new Set(plan.entries.filter((entry) => entry.refresh).map((entry) => entry.id));
const removed = Object.entries(data.decisions).filter(([id]) => refreshed.has(id));

if (removed.length) {
  const archivedAt = new Date().toISOString();
  const lines = removed.map(([id, decision]) => JSON.stringify({
    archivedAt,
    reason: "superseded-by-20260829-visual-refresh",
    id,
    ...decision
  }));
  fs.appendFileSync(historyPath, `${lines.join("\n")}\n`, "utf8");
  for (const [id] of removed) delete data.decisions[id];
  data.updatedAt = archivedAt;
  fs.writeFileSync(decisionsPath, `${JSON.stringify(data, null, 2)}\n`, "utf8");
}

console.log(`Archived and reset ${removed.length} stale decisions; retained ${Object.keys(data.decisions).length}.`);
