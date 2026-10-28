import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const read = p => fs.readFileSync(path.resolve(root, p), "utf8").replace(/^\uFEFF/, "").replace(/\r\n/g, "\n");
const errors = [];
const check = (ok, message) => { if (!ok) errors.push(message); };
const storyDir = "campaign/npcs/stories";
const stories = fs.readdirSync(path.resolve(root, storyDir)).filter(p => p.endsWith(".md")).map(p => storyDir + "/" + p);
check(stories.length === 25, "Expected 25 independent stories");
const storyIndex = read("campaign/npcs/stories.md");
for (const p of stories) {
  const s = read(p);
  check(storyIndex.includes(path.basename(p)), "Missing story index link: " + p);
  for (const chapter of ["第一章", "第二章", "第三章", "第四章", "第五章"]) check(s.includes(chapter), p + ": missing " + chapter);
}

const episodeFiles = [];
const episodeStats = [];
for (let ch = 1; ch <= 5; ch++) {
  const dir = "campaign/episodes/chapter-" + String(ch).padStart(2, "0");
  const files = fs.readdirSync(path.resolve(root, dir)).filter(p => /^\d\d-.*\.md$/.test(p)).sort();
  check(files.length === 4, dir + ": expected 4 episodes");
  for (const name of files) {
    const file = dir + "/" + name;
    episodeFiles.push(file);
    const s = read(file), n = Number(name.slice(0, 2));
    const people = s.split("## 主要人物")[1]?.split("## 各方冲突")[0]?.split("\n").filter(l => /^\| .+ \| .+ \|$/.test(l) && !l.startsWith("| 人物 ")).map(l => l.split("|")[1].trim()) ?? [];
    const organizations = s.match(/主要组织：([^\n]+?)。/)?.[1].split("、") ?? [];
    check(people.length >= 5, file + ": fewer than 5 named main actors");
    check(organizations.length >= 2, file + ": fewer than 2 main organizations");
    check(new Set(people).size === people.length, file + ": duplicate main actors");
    if (organizations.length > 3) check([3, 7, 14, 18].includes(n), file + ": unexplained organization exception");
    episodeStats.push({ episode: n, mainPeople: people.length, mainOrganizations: organizations.length, history: n < 3 });
  }
}
check(episodeStats.map(x => x.episode).join(",") === Array.from({length:20}, (_, i) => i + 1).join(","), "Episodes are not exactly 1..20");

const placement = read("campaign/npcs/roster/NPC出场安排.md");
const placementRows = placement.split("\n").filter(l => /^\| LS-NPC-/.test(l)).map(l => l.split("|").slice(1, -1).map(c => c.trim()));
const ids = placementRows.map(r => r[0]);
check(ids.length === 93 && new Set(ids).size === 93, "Placement must contain 93 unique IDs");
const productionRoot = "assets/npc/production";
const control = JSON.parse(read(productionRoot + "/control/portrait-master.json"));
check(ids.slice().sort().join() === control.characters.map(c => c.id).sort().join(), "Placement/control ID mismatch");
const retired = JSON.parse(read(productionRoot + "/control/retired-characters.json")).characters.map(c => c.id);
const removed = ["007","010","016","020","023","028","032","036","042","047","064","071","084","087"].map(n => "LS-NPC-" + n);
check(ids.every(id => !retired.includes(id) && !removed.includes(id)), "Deleted/retired ID in current roster");
const outline = read("campaign/episodes/20-episode-outline.md") + "\n" + episodeFiles.map(read).join("\n");
const uncovered = [];
for (const row of placementRows) {
  check(row.length === 6 && row.every(Boolean), "Empty placement field: " + row[0]);
  const display = row[1].split("；")[0];
  const aliases = display.replace(/（[^）]*）/g, "").split(/[／/]/);
  if (!aliases.some(name => outline.includes(name))) uncovered.push(row[0] + " " + display);
}
check(uncovered.length === 0, "No outline/interlude appearance: " + uncovered.join(", "));

const mainDocs = [
  "campaign/episodes/20-episode-outline.md",
  "campaign/decisions/二十话重整-设计定案.md",
  "campaign/archive/reviews-20260903/二十话重整-审阅记录.md",
  "campaign/archive/reviews-20260903/二十话大纲与NPC故事重整计划.md",
  "campaign/episodes/campaign-outline-notes.md",
  "campaign/episodes/dark-lines.md",
  "campaign/episodes/第一季-删不掉的路与第二季归城布局.md",
  "campaign/npcs/stories.md", "campaign/npcs/roster/NPC出场安排.md",
  "campaign/npcs/roster/全城NPC名单.md", "campaign/npcs/NPC工作总控.md",
  "campaign/npcs/reference/NPC最终意见版.md", "campaign/npcs/reference/NPC立绘设定终稿.md",
  "campaign/npcs/reference/核心NPC.md", "campaign/npcs/reference/关键NPC.md", "campaign/npcs/index.md",
  "campaign/world/06-核心谜团.md", "campaign/world/11-玩家角色与主线驱动.md",
  "campaign/world/13-框架总览.md", "campaign/README.md"
];
if (fs.existsSync(path.resolve(root, "campaign/archive/reviews-20260903/二十话重整-验收.md"))) mainDocs.push("campaign/archive/reviews-20260903/二十话重整-验收.md");
const mdFiles = [...new Set([...stories, ...episodeFiles, ...mainDocs])];
let localLinks = 0;
const fence = String.fromCharCode(96).repeat(3);
for (const file of mdFiles) {
  const s = read(file);
  check(!/^- \[ \]/m.test(s), "Unchecked task in active deliverable: " + file);
  const prose = s.replace(new RegExp(fence + "[\\s\\S]*?" + fence, "g"), "");
  for (const match of prose.matchAll(/!?\[[^\]]*\]\(([^)\n]+)\)/g)) {
    let target = match[1].trim().replace(/^<|>$/g, "");
    if (/^(https?:|mailto:|data:|codex:)/.test(target) || target.startsWith("#")) continue;
    target = decodeURIComponent(target.split("#")[0]);
    if (!target) continue;
    localLinks++;
    check(fs.existsSync(path.resolve(root, path.dirname(file), target)), file + ": broken local link " + target);
  }
}
const activeProse = [...stories, ...episodeFiles, "campaign/npcs/stories.md", "campaign/npcs/roster/NPC出场安排.md"].map(read).join("\n");
check(!/待\s*GM\s*(?:确认|决定|审批)|姓名待定|待统一|随后安排/.test(activeProse), "Unresolved GM design gate in active story/outline");
for (const [id, name] of [["LS-NPC-080","许承钧"],["LS-NPC-103","朱蘅"],["LS-NPC-107","韩星"]]) {
  check(control.characters.find(c => c.id === id)?.name === name, "Canonical control name mismatch: " + id);
}
let verifiedAssets = 0;
for (const c of control.characters) {
  if (!c.approvedAsset) continue;
  const asset = path.resolve(root, productionRoot, c.approvedAsset);
  check(fs.existsSync(asset), "Missing approved asset: " + c.id);
  if (fs.existsSync(asset) && c.approvedSha256) {
    const actual = crypto.createHash("sha256").update(fs.readFileSync(asset)).digest("hex");
    check(actual === c.approvedSha256, "Approved asset hash mismatch: " + c.id);
    verifiedAssets++;
  }
}
const result = { status: errors.length ? "FAIL" : "PASS", stories: stories.length, episodes: episodeFiles.length, retainedNPCs: ids.length, outlineCoverage: ids.length - uncovered.length, markdownFiles: mdFiles.length, localLinks, verifiedApprovedAssets: verifiedAssets, episodeStats, errors };
console.log(JSON.stringify(result, null, 2));
process.exitCode = errors.length ? 1 : 0;

