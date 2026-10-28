import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const designs = {
  "LS-NPC-008": {
    tags: ["cyborg", "science_fiction", "mechanical_ears", "mechanical_neck", "robot_joints", "techwear"],
    remove: [],
    detail: "A visibly exhausted twenty-four-year-old Chinese night customer-service agent with a dark-grey low ponytail touches one integrated mechanical ear while a segmented synthetic voice module runs visibly along her throat, wearing an oversized teal and cream color-block technical jacket under soft even frontal studio light; the strict cowboy shot ends at mid-thigh."
  },
  "LS-NPC-009": {
    tags: ["cyborg", "science_fiction", "mechanical_eyes", "prosthetic_hand", "robot_joints"],
    remove: [],
    detail: "A pale twenty-nine-year-old Chinese digital-security engineer with one fully mechanical eye, an exposed charcoal temple plate and one articulated skeletal prosthetic hand taps an absent keyboard in empty air while wearing severe layered data-security techwear under soft even frontal studio light; the strict cowboy shot ends at mid-thigh."
  },
  "LS-NPC-030": {
    tags: [],
    remove: ["smile", "light_smile"],
    detail: "A slightly overweight forty-one-year-old Chinese station attendant with tired watchful eyes and one loose uniform button grips a scratched old metal thermos while counting floor tiles with a guarded unsmiling expression under soft even frontal studio light; the strict cowboy shot ends at mid-thigh."
  },
  "LS-NPC-033": {
    tags: ["cyborg", "science_fiction", "prosthetic_arm", "mechanical_arms", "robot_joints", "techwear"],
    remove: [],
    detail: "A sturdy sun-tanned forty-six-year-old Chinese former driver with grey-threaded hair and an unsentimental stare crosses one rugged exposed left forearm prosthesis over a thick blank appeal folder, wearing a weathered brown bomber jacket and practical driver techwear under soft even frontal studio light; the strict cowboy shot ends at mid-thigh."
  },
  "LS-NPC-039": {
    tags: ["cyberpunk", "cyborg", "science_fiction", "mechanical_eyes", "mechanical_ears", "mechanical_neck"],
    remove: [],
    detail: "An elegant thirty-year-old Chinese virtual-idol agent with matched mechanical irises, polished ear implants and a narrow segmented voice interface visible along one side of her neck pauses with a cold controlled expression, wearing a sharply tailored purple jacket and coordinated jewelry under soft even frontal studio light; the strict cowboy shot ends at mid-thigh."
  },
  "LS-NPC-046": {
    tags: [],
    remove: ["smile", "light_smile"],
    detail: "A precise thirty-one-year-old Chinese bank auditor with a severe short black bob and an unreadable exacting gaze holds a compact blank document case against an oversized pale coat with asymmetrical fasteners under soft even frontal studio light, remaining entirely human in this standard form; the strict cowboy shot ends at mid-thigh."
  },
  "LS-NPC-058": {
    tags: ["cyberpunk", "cyborg", "science_fiction", "mechanical_eyes", "prosthetic_hand", "robot_joints"],
    remove: [],
    detail: "A thin forty-eight-year-old Chinese gang accountant looks over semi-rimless glasses that expose one mechanical eye while his articulated prosthetic right hand balances a stylus above a blank teal accounting interface, surrounded by a washed old cardigan and sweater vest under soft even frontal studio light; the strict cowboy shot ends at mid-thigh."
  },
  "LS-NPC-077": {
    tags: ["cyberpunk", "cyborg", "science_fiction", "mechanical_eyes", "prosthetic_hand", "robot_joints"],
    remove: ["smile", "light_smile"],
    detail: "A coldly courteous forty-eight-year-old Chinese supervisory commissioner with greying side-parted hair, one expensive mechanical eye and one impeccably articulated prosthetic hand adjusts his muted tie cuff without smiling, wearing a conservative charcoal civil-service suit under soft even frontal studio light; the strict cowboy shot ends at mid-thigh."
  },
  "LS-NPC-092": {
    tags: [],
    remove: ["smile", "light_smile"],
    detail: "A sturdy loud forty-eight-year-old Chinese teahouse owner with a broad round face and short permed curls calls firmly across the room while holding a plain ceramic teapot, wearing a practical red apron over a brown cardigan under soft even frontal studio light; the strict cowboy shot ends at mid-thigh."
  },
  "LS-NPC-100": {
    tags: ["cyberpunk", "cyborg", "science_fiction", "mechanical_eyes", "prosthetic_arm", "mechanical_arms", "robot_joints"],
    remove: [],
    detail: "A calm thirty-five-year-old Chinese rehabilitation physician with one diagnostic mechanical eye and one exposed precision prosthetic forearm holds a blank clinical chart against a soft blue cardigan beneath an open white coat under soft even frontal studio light; the strict cowboy shot ends at mid-thigh."
  },
  "LS-NPC-107": {
    tags: ["cyberpunk", "cyborg", "science_fiction", "mechanical_eyes", "mechanical_ears", "prosthetic_hand", "robot_joints"],
    remove: ["smile", "light_smile"],
    detail: "An exceptionally handsome young East Asian male idol presents a practiced unreadable camera expression with perfectly matched mechanical eyes, polished cosmetic ear implants and one elegant articulated prosthetic hand, wearing a clean white bomber jacket over a fitted black turtleneck under soft even frontal studio light; the strict cowboy shot ends at mid-thigh without revealing whether he is human."
  }
};

const lowerBody = new Set(["full_body", "shoes", "boots", "sneakers"]);
const cropNegatives = ["full_body", "shoes", "boots", "sneakers"];
const cyberTags = ["cyborg", "science_fiction", "mechanical_eyes", "mechanical_ears", "mechanical_neck", "prosthetic_hand", "prosthetic_arm", "mechanical_arms", "robot_joints", "cyberpunk"];
for (const [id, design] of Object.entries(designs)) {
  const file = path.join(root, "prompts", `${id}.json`);
  const prompt = JSON.parse(fs.readFileSync(file, "utf8"));
  prompt.version += 1;
  prompt.designStatus = design.tags.includes("cyborg") ? "portrait-design-cyborg-review-retry" : "portrait-design-review-retry";
  prompt.designAssumptions ??= [];
  prompt.designAssumptions.push(`User-review redesign: ${design.detail}`);
  const remove = new Set([...design.remove, ...lowerBody]);
  prompt.tags = [...new Set([...prompt.tags.filter((tag) => !remove.has(tag)), ...design.tags, "cowboy_shot"] )];
  prompt.negativeAdditions = [...new Set([
    ...(prompt.negativeAdditions ?? []).filter((tag) => !design.tags.includes(tag) && !(design.tags.includes("cyborg") && cyberTags.includes(tag))),
    ...cropNegatives
  ])];
  prompt.naturalLanguageDetail = design.detail;
  fs.writeFileSync(file, `${JSON.stringify(prompt, null, 2)}\n`, "utf8");
  console.log(`${id} -> v${prompt.version}; tags=${prompt.tags.length}; cyborg=${design.tags.includes("cyborg")}`);
}
