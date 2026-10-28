import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const master = JSON.parse(fs.readFileSync(path.join(root, "control", "portrait-master.json"), "utf8"));

const cyber = {
  "LS-NPC-001": ["corporate-prosthesis", "polished modular left-hand prosthesis and asymmetric smart tailoring", ["cyberpunk", "techwear", "science_fiction", "buckle"]],
  "LS-NPC-004": ["industrial-prosthesis", "exposed military right arm and a fitted five-fingered dark heat-resistant glove on the normal left hand", ["cyberpunk", "techwear", "science_fiction", "robot_joints"]],
  "LS-NPC-006": ["corporate-interface", "a visible behind-ear maintenance jack and layered slate technical workwear", ["cyberpunk", "techwear", "science_fiction", "snap-fit_buckle"]],
  "LS-NPC-008": ["street-tech", "an oversized color-block streetwear jacket and a conspicuous modular call-center headset", ["cyberpunk", "streetwear", "headset", "oversized_clothes"]],
  "LS-NPC-009": ["corporate-interface", "one restrained mechanical eye and severe charcoal data-security clothing", ["cyberpunk", "techwear", "mechanical_eyes", "science_fiction"]],
  "LS-NPC-012": ["street-tech", "a sharp cropped jacket, cargo trousers and an aftermarket test-device harness", ["cyberpunk", "streetwear", "punk", "cargo_pants", "harness"]],
  "LS-NPC-014": ["courier-prosthesis", "a weathered below-knee courier prosthesis integrated with bright reflective riding gear", ["cyberpunk", "techwear", "cyborg", "prosthetic_leg", "sportswear"]],
  "LS-NPC-017": ["corporate-interface", "a precision inspection ocular implant paired with a clean short technical jacket", ["cyberpunk", "techwear", "mechanical_eyes", "science_fiction"]],
  "LS-NPC-018": ["industrial-prosthesis", "two articulated conductive prosthetic fingertips visible around the pen and an asymmetric lab jacket", ["cyberpunk", "techwear", "cyborg", "prosthetic_hand", "science_fiction"]],
  "LS-NPC-022": ["industrial-interface", "a rugged drone-control port behind one ear and layered airfield utility gear", ["cyberpunk", "techwear", "cyborg", "utility_vest", "cargo_pants"]],
  "LS-NPC-024": ["flight-interface", "the old neck synchronization interface rendered as a deliberate segmented port beneath a fitted flight harness", ["cyberpunk", "techwear", "science_fiction", "harness", "chest_harness"]],
  "LS-NPC-027": ["industrial-prosthesis", "a scarred industrial lower-leg prosthesis beneath high-visibility tunneling equipment", ["cyberpunk", "techwear", "cyborg", "prosthetic_leg", "orange_vest"]],
  "LS-NPC-034": ["driver-interface", "a compact auditory driving interface behind the ear and a vivid night-driver bomber jacket", ["cyberpunk", "streetwear", "cyborg", "bomber_jacket", "headset"]],
  "LS-NPC-040": ["media-tech", "a half mask, audio harness and asymmetrical underground broadcast streetwear", ["cyberpunk", "streetwear", "punk", "half_mask", "harness"]],
  "LS-NPC-041": ["creative-tech", "layered game-studio streetwear with metal badges, thigh strap and portable coordinate terminal", ["cyberpunk", "streetwear", "techwear", "thigh_strap", "multiple_earrings"]],
  "LS-NPC-043": ["street-tech", "a loose hoodie under a bright track jacket with large noise-cancelling headphones", ["cyberpunk", "streetwear", "hoodie", "track_jacket", "headset"]],
  "LS-NPC-048": ["security-interface", "a visible subdermal vault-authentication port at the temple and angular security armor", ["cyberpunk", "techwear", "cyborg", "body_armor", "science_fiction"]],
  "LS-NPC-049": ["tactical-tech", "modular matte armor with contrasting straps and a compact command interface", ["cyberpunk", "techwear", "body_armor", "thigh_strap", "snap-fit_buckle"]],
  "LS-NPC-052": ["tactical-tech", "an austere sensor eyepatch integrated into asymmetrical special-action armor", ["cyberpunk", "techwear", "body_armor", "half_mask", "science_fiction"]],
  "LS-NPC-053": ["tactical-tech", "lean segmented armor with a predictive sensor collar and offset harness", ["cyberpunk", "techwear", "body_armor", "harness", "snap-fit_buckle"]],
  "LS-NPC-054": ["institutional-interface", "the restraint-network connector made clearly visible behind the ear above an old severe long coat", ["cyberpunk", "techwear", "cyborg", "science_fiction", "long_coat"]],
  "LS-NPC-055": ["corporate-interface", "a discreet memory-assist temple port beneath an immaculate asymmetric intelligence uniform", ["cyberpunk", "techwear", "cyborg", "buckle", "science_fiction"]],
  "LS-NPC-057": ["street-prosthesis", "only the right hand below the wrist replaced by a battered old prosthesis, paired with layered red streetwear", ["cyberpunk", "streetwear", "punk", "prosthetic_hand", "cyborg"]],
  "LS-NPC-061": ["clinic-punk", "seven matte ear studs, a calibration headset and dense pocketed clinic techwear", ["cyberpunk", "punk", "techwear", "ear_piercing", "multiple_earrings"]],
  "LS-NPC-062": ["hacker-punk", "a fitted black suit broken by a data-knife harness, multiple ear piercings and street-tech buckles", ["cyberpunk", "punk", "techwear", "multiple_earrings", "harness"]],
  "LS-NPC-065": ["port-street-tech", "a tailored bomber jacket over port utility streetwear with the hidden eagle mark retained", ["cyberpunk", "streetwear", "bomber_jacket", "cargo_pants", "buckle"]],
  "LS-NPC-066": ["port-punk", "refined dockside streetwear that exposes the forearm tattoo through asymmetrical rolled sleeves", ["cyberpunk", "streetwear", "punk", "arm_tattoo", "multiple_earrings"]],
  "LS-NPC-067": ["dock-punk", "a sleeveless armored dock jacket, heavy cargo trousers and the full right-arm tattoo", ["cyberpunk", "punk", "streetwear", "body_armor", "arm_tattoo"]],
  "LS-NPC-069": ["arcade-punk", "bright layered arcade streetwear with a crop top, bomber jacket and multiple ear piercings", ["cyberpunk", "punk", "streetwear", "crop_top", "bomber_jacket"]],
  "LS-NPC-072": ["fugitive-tech", "anonymous layered technical clothing with a mouth mask and isolated terminal harness", ["cyberpunk", "techwear", "mouth_mask", "hoodie", "harness"]],
  "LS-NPC-073": ["institutional-tech", "numbered sampling gear built from a utility vest, sealed pouches and snap-fit buckles", ["cyberpunk", "techwear", "utility_vest", "pouch", "snap-fit_buckle"]],
  "LS-NPC-081": ["lab-interface", "a small experimental neural port at the nape beneath a carelessly layered laboratory outfit", ["cyberpunk", "techwear", "cyborg", "science_fiction", "lab_coat"]],
  "LS-NPC-085": ["research-tech", "a server-room harness and dense technical layers replacing the generic checked-shirt silhouette", ["cyberpunk", "techwear", "harness", "utility_vest", "snap-fit_buckle"]],
  "LS-NPC-086": ["containment-tech", "a severe high-collar technical uniform with a biometric wrist connector and modular buckles", ["cyberpunk", "techwear", "science_fiction", "buckle", "snap-fit_buckle"]],
  "LS-NPC-088": ["anomalous-prosthesis", "the reconstructed right hand clearly visible against a loose asymmetrical long coat", ["cyberpunk", "techwear", "prosthetic_hand", "cyborg", "long_coat"]],
  "LS-NPC-095": ["rehabilitation-prosthesis", "the integrated spinal column and both articulated prosthetic legs paired with vivid athletic streetwear", ["cyberpunk", "streetwear", "cyborg", "prosthetic_leg", "mechanical_legs"]],
  "LS-NPC-096": ["broker-punk", "an asymmetric hooded streetwear silhouette with concealed utility straps and mismatched earrings", ["cyberpunk", "punk", "streetwear", "hoodie", "multiple_earrings"]],
  "LS-NPC-098": ["scrapyard-tech", "patched industrial techwear with goggles at the neck, tool pouches and the damaged robot dog", ["cyberpunk", "techwear", "utility_vest", "cargo_pants", "robot"]]
};

const diverseGroups = {
  "color-industrial": ["LS-NPC-003", "LS-NPC-005", "LS-NPC-013", "LS-NPC-025", "LS-NPC-070", "LS-NPC-093"],
  "sport-casual": ["LS-NPC-015", "LS-NPC-031", "LS-NPC-033", "LS-NPC-060", "LS-NPC-079", "LS-NPC-089", "LS-NPC-091"],
  "soft-knit": ["LS-NPC-019", "LS-NPC-026", "LS-NPC-038", "LS-NPC-075", "LS-NPC-N2"],
  "expressive-fashion": ["LS-NPC-039", "LS-NPC-046", "LS-NPC-080", "LS-NPC-104"],
  "heritage-hybrid": ["LS-NPC-056", "LS-NPC-058", "LS-NPC-059", "LS-NPC-063", "LS-NPC-068", "LS-NPC-101"],
  "everyday-color": ["LS-NPC-082", "LS-NPC-092", "LS-NPC-094", "LS-NPC-097", "LS-NPC-099", "LS-NPC-100"]
};

const diverseTags = {
  "color-industrial": ["jumpsuit", "cargo_pants", "work_boots", "utility_belt", "fingerless_gloves"],
  "sport-casual": ["sportswear", "track_jacket", "t-shirt", "sneakers"],
  "soft-knit": ["sweater", "cardigan", "long_sleeves"],
  "expressive-fashion": ["asymmetrical_hair", "oversized_clothes", "purple_jacket", "earrings"],
  "heritage-hybrid": ["long_coat", "waistcoat", "boots", "jewelry"],
  "everyday-color": ["green_jacket", "red_sweater", "blue_shirt", "brown_pants"]
};

const diverseOverrides = {
  "LS-NPC-003": ["blue-jumpsuit", "a faded blue maintenance jumpsuit with rolled sleeves, caliper pocket and heavy work boots", ["blue_jumpsuit", "sleeves_rolled_up", "tool_belt", "work_boots"]],
  "LS-NPC-005": ["layered-lab-workwear", "a pale lab coat layered over a grey-blue industrial jumpsuit with restrained metal fasteners", ["lab_coat", "blue_jumpsuit", "buckle", "work_boots"]],
  "LS-NPC-013": ["patched-field-repair", "a sun-faded orange utility vest over patched work clothes and a visibly overstuffed cable bag", ["orange_vest", "cargo_pants", "tool_belt", "work_boots"]],
  "LS-NPC-025": ["high-visibility-construction", "a dusty high-visibility vest, blue work shirt, helmet and mismatched construction gloves", ["orange_vest", "blue_shirt", "work_gloves", "work_boots"]],
  "LS-NPC-070": ["muddy-rural-workwear", "a moss-green field jacket over mud-stained work clothes with an old canvas tool belt", ["green_jacket", "cargo_pants", "tool_belt", "work_boots"]],
  "LS-NPC-093": ["repair-shop-overalls", "a brown repair-shop jumpsuit tied at the waist over a faded shirt with oil-stained gloves", ["jumpsuit", "brown_pants", "work_gloves", "tool_belt"]],
  "LS-NPC-015": ["night-shift-sportswear", "a bright track jacket over a loose shirt and practical sneakers, with a dispatch headset", ["sportswear", "track_jacket", "t-shirt", "sneakers", "headset"]],
  "LS-NPC-031": ["young-trainee-knit", "a neat blue sweater vest over a pale shirt with comfortable trousers and a trainee badge", ["blue_cardigan", "sweater_vest", "blue_shirt", "pants"]],
  "LS-NPC-033": ["driver-representative-casual", "a weathered bomber jacket over practical driver sportswear with a folded route map", ["bomber_jacket", "sportswear", "t-shirt", "sneakers"]],
  "LS-NPC-060": ["young-fighter-street", "a red hoodie under a short jacket with loose cargo trousers and worn sneakers", ["hoodie", "red_jacket", "cargo_pants", "sneakers"]],
  "LS-NPC-079": ["optimistic-civic-casual", "a vivid blue track jacket and clean sneakers instead of another office suit", ["track_jacket", "sportswear", "blue_jacket", "sneakers"]],
  "LS-NPC-089": ["family-work-casual", "a loose green T-shirt, utility trousers and fingerless work gloves", ["t-shirt", "green_shirt", "cargo_pants", "fingerless_gloves"]],
  "LS-NPC-091": ["slouchy-front-desk", "an oversized hoodie beneath an unbuttoned work shirt with casual sneakers", ["hoodie", "oversized_clothes", "open_clothes", "sneakers"]],
  "LS-NPC-019": ["medical-retail-knit", "a soft blue cardigan over a clean clinic shirt with a small blank badge", ["blue_cardigan", "cardigan", "blue_shirt", "long_sleeves"]],
  "LS-NPC-026": ["archive-knit", "a brown sweater vest over rolled shirt sleeves with a long practical skirt", ["brown_cardigan", "sweater_vest", "long_skirt", "sleeves_rolled_up"]],
  "LS-NPC-038": ["lecturer-knit", "a grey turtleneck sweater and soft long coat with a worn phone in hand", ["turtleneck_sweater", "grey_sweater", "long_coat", "pants"]],
  "LS-NPC-075": ["teacher-cardigan", "a warm brown cardigan over a pale shirt with relaxed trousers and a tea cup", ["brown_cardigan", "cardigan", "brown_pants", "long_sleeves"]],
  "LS-NPC-N2": ["school-office-knit", "a muted blue cardigan and long skirt with a simple teacher badge and attendance folder", ["blue_cardigan", "cardigan", "long_skirt", "long_sleeves"]],
  "LS-NPC-039": ["media-fashion", "a sharply tailored purple jacket, pencil skirt and coordinated jewelry", ["purple_jacket", "pencil_skirt", "jewelry", "earrings"]],
  "LS-NPC-046": ["minimalist-auditor", "an oversized pale coat with asymmetrical fasteners and a compact document case", ["oversized_clothes", "white_coat", "buckle", "asymmetrical_hair"]],
  "LS-NPC-080": ["professor-modernist", "a dark turtleneck sweater under a long structured coat with understated jewelry", ["turtleneck_sweater", "long_coat", "jewelry", "boots"]],
  "LS-NPC-104": ["art-director-expressive", "an oversized striped jacket, asymmetrical haircut and boldly layered studio clothing", ["striped_jacket", "oversized_clothes", "asymmetrical_hair", "earrings"]],
  "LS-NPC-056": ["hall-embroidered-jacket", "a restrained red jacket with the white-tiger hall embroidery visible only at one rolled cuff", ["red_jacket", "sleeves_rolled_up", "black_shirt", "brown_pants"]],
  "LS-NPC-058": ["old-accountant-knit", "a washed brown cardigan and sweater vest surrounding the floating account screen", ["brown_cardigan", "sweater_vest", "brown_pants", "glasses"]],
  "LS-NPC-059": ["swordsman-hybrid", "a charcoal kimono beneath a weathered black long coat, tied with the old red hair cord", ["grey_kimono", "kimono", "black_coat", "long_coat"]],
  "LS-NPC-063": ["matriarch-kimono-coat", "a formal black kimono beneath a severe long coat with one restrained metal ornament", ["black_kimono", "kimono", "long_coat", "jewelry"]],
  "LS-NPC-068": ["port-religious-dress", "a severe long black dress with an eagle pendant and a weathered port coat", ["black_dress", "long_dress", "black_coat", "necklace"]],
  "LS-NPC-101": ["vintage-mechanical", "a worn trench coat over a waistcoat and rolled work shirt with an old mechanical part", ["trench_coat", "waistcoat", "sleeves_rolled_up", "work_boots"]],
  "LS-NPC-082": ["field-student-color", "an orange field vest over a blue hoodie with a safety helmet and folded plans", ["orange_vest", "blue_hoodie", "hoodie", "work_boots"]],
  "LS-NPC-092": ["tea-house-warm", "a warm red apron over a soft brown cardigan with practical dark skirt", ["red_apron", "brown_cardigan", "cardigan", "long_skirt"]],
  "LS-NPC-094": ["boxing-venue-smart", "a dark waistcoat over a rolled blue shirt with the small paper flower retained", ["waistcoat", "blue_shirt", "sleeves_rolled_up", "brown_pants"]],
  "LS-NPC-097": ["noodle-shop-everyday", "a faded black apron over a warm red sweater with sleeves rolled for kitchen work", ["black_apron", "red_sweater", "sleeves_rolled_up", "brown_pants"]],
  "LS-NPC-099": ["street-vendor-color", "a red apron over a thick green jacket and practical dark trousers", ["red_apron", "green_jacket", "brown_pants", "work_gloves"]],
  "LS-NPC-100": ["rehabilitation-doctor", "a clean white coat over a soft blue cardigan with a prosthetic rehabilitation chart", ["white_coat", "blue_cardigan", "cardigan", "blue_shirt"]]
};

const diverseById = new Map();
for (const [group, ids] of Object.entries(diverseGroups)) for (const id of ids) diverseById.set(id, group);

const entries = master.characters.map((character) => {
  if (cyber[character.id]) {
    const [targetStyle, designDirective, addTags] = cyber[character.id];
    return { id: character.id, name: character.name, organization: character.organization, layer: "cyberpunk-signal", targetStyle, refresh: true, designDirective, addTags };
  }
  const group = diverseById.get(character.id);
  if (group) {
    const [targetStyle, designDirective, addTags] = diverseOverrides[character.id] ?? [group, `replace the generic dark office or work silhouette with a distinct ${group} outfit while preserving identity anchors`, diverseTags[group]];
    return { id: character.id, name: character.name, organization: character.organization, layer: "diverse-civic", targetStyle, refresh: true, designDirective, addTags };
  }
  return { id: character.id, name: character.name, organization: character.organization, layer: "diverse-civic", targetStyle: "retain-distinctive", refresh: false, designDirective: "retain the current distinctive silhouette and identity anchor", addTags: [] };
});

const report = {
  schemaVersion: 1,
  updatedAt: new Date().toISOString(),
  targetPopulation: entries.length,
  policy: {
    cyberpunkSignalTarget: "38/95 = 40%",
    remainderTarget: "57/95 = 60%, distributed across occupational, regional, historical, athletic, formal and everyday silhouettes",
    bodyModificationPolicy: "Permanent replacements and interfaces are visible but role-specific; they do not imply supernatural powers.",
    tagPolicy: "Every addTags entry must exist in control/verified-tags.json before prompt application."
  },
  counts: {
    cyberpunkSignal: entries.filter((item) => item.layer === "cyberpunk-signal").length,
    diverseCivic: entries.filter((item) => item.layer === "diverse-civic").length,
    refresh: entries.filter((item) => item.refresh).length,
    retain: entries.filter((item) => !item.refresh).length
  },
  entries
};

fs.writeFileSync(path.join(root, "control", "visual-refresh-plan.json"), `${JSON.stringify(report, null, 2)}\n`);
console.log(JSON.stringify(report.counts));
