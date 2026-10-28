import {
  DEFAULT_MAX_RANK,
  DEFAULT_RANK_STEPS,
  EVENT_RANK_CHANGES,
  EVENT_RANK_CHANGE_VALUES,
  FLAG_SCOPE,
  GIFT_CONSUME_MODE_VALUES,
  GIFT_MATCH_MODE_VALUES,
  GIFT_PROFILE_DEFAULTS,
  GIFT_PROFILE_FLAG_KEY,
  GIFT_PROFILE_MODES,
  GIFT_PROFILE_SOURCES,
  GIFT_PROFILE_VERSION,
  GIFT_REACTION_AUDIENCE_VALUES,
  GIFT_REACTION_CONSUME_MODE_VALUES,
  GIFT_REACTION_CONSUME_MODES,
  GIFT_REACTION_DEFAULTS,
  GIFT_REACTION_DISPLAY_MODE_VALUES,
  GIFT_REACTION_PRESETS,
  GIFT_REACTION_VALUES,
  GIFT_REACTIONS,
  GIFT_REJECTED_CONSUME_MODE_VALUES,
  GIFT_TARGET_KIND_VALUES,
  GIFT_TARGET_KINDS,
  GIFT_UNMATCHED_GIFT_MODE_VALUES,
  GIFT_PREFERENCE_VISIBILITY_VALUES,
  MAP_VISIBILITY_VALUES,
  PORTRAIT_PRESENTATIONS,
  PORTRAIT_PRESENTATION_VALUES,
  PROFILE_DEFAULTS,
  RANK_MACRO_DIRECTIONS,
  RANK_MACRO_DIRECTION_VALUES,
  RELATIONSHIP_POLARITIES,
  RELATIONSHIP_POLARITY_VALUES,
  RELATIONSHIP_SYNC_MODE_VALUES,
  SCHEMA_VERSION
} from "./constants.js";
import { normalizeMapInspectorFrame, normalizeMapThumbnailFrame } from "./map-thumbnail.js";
import { mergeStorageValue } from "./three-way-merge.js";

const ENTRY_TYPES = new Set(["actor", "custom", "organization"]);
const VISIBILITY_VALUES = new Set(["gm", "owner", "players"]);
const NOTE_VISIBILITY_VALUES = new Set(["players", "gm"]);
const EVENT_TYPES = new Set(["note", "gift"]);
const TARGET_GIFT_PROFILE_MUTATION_QUEUES = new Map();
const TARGET_GIFT_PROFILE_FALLBACK_KEYS = new WeakMap();
const TARGET_GIFT_PROFILE_WRITE_TOKEN_FIELD = "_srtWriteToken";
let nextTargetGiftProfileFallbackKey = 1;
const PROFILE_LEGACY_FIELDS = new Set(["baseTone"]);
const FORBIDDEN_GIFT_REACTION_IDS = new Set(["__proto__", "prototype", "constructor"]);
const CUSTOM_GIFT_REACTION_DEFAULT = Object.freeze({
  progressDelta: 0,
  line: "",
  previewHintLine: "",
  previewResultLine: "",
  cutinImage: "",
  sfx: "",
  cutinScale: 1,
  cutinOffsetX: 0,
  cutinOffsetY: 0
});

/** Stable ids/titles used when migrating the legacy single-field notes model. */
const LEGACY_PLAYER_NOTE_ID = "note_player";
const LEGACY_GM_NOTE_ID = "note_gm";
const LEGACY_PLAYER_NOTE_TITLE = "Notes";
const LEGACY_GM_NOTE_TITLE = "GM Notes";

const DATA_RENDER_ONLY_FIELDS = new Set([
  "classes", "active", "relationshipsView", "totalRanks", "maxRanks", "maxClasses", "maxRankTotal",
  "activeBondCount", "relationshipCount", "playTransition", "fontScalePercent",
  "guideText", "sceneRecall", "moment"
]);

const RELATIONSHIP_RENDER_ONLY_FIELDS = new Set([
  "displayName", "displayNameRoman", "role", "canView", "canEdit", "isRedacted", "firstGiftUnlockAvailable",
  "recentEvents", "rowAccent", "accentSoft", "rowName", "isActive", "isMax",
  "rankPadded", "portraitStyle", "bioLines", "progress", "rankUpDisabled", "rankDownDisabled",
  "isOrganization", "entryBadge", "rankLabel", "currentRankLabel", "maxRankLabel",
  "rankUpLabel", "rankDownLabel", "rankCompleteLabel", "mapRankUpFx", "hasNotes",
  "rankDisplay", "signedRank", "polarityLabel", "isNegative", "isNeutral", "isNegativeMax",
  "allEvents", "eventCount", "recentCount", "hasMoreEvents", "unlockable",
  "listPortrait", "mapInspectorPortrait", "mapInspectorStyle", "hasCustomMapInspectorFrame",
  "_targetActorName", "_targetActorImage", "_targetTokenImage", "_targetActorMissing"
]);

const STAT_RENDER_ONLY_FIELDS = new Set(["delayMs"]);
const EVENT_RENDER_ONLY_FIELDS = new Set(["eventId", "delayMs", "displayRankLabel", "isRankDown"]);

export function cloneStorageValue(value) {
  if (value === undefined) return undefined;
  if (typeof structuredClone === "function") return structuredClone(value);
  return JSON.parse(JSON.stringify(value));
}

export function createDefaultRelationshipData(ownerActorOrUuid = null) {
  return {
    version: SCHEMA_VERSION,
    ownerActorUuid: actorUuidOf(ownerActorOrUuid),
    profile: normalizeProfile({}),
    relationships: []
  };
}

export function migrateRelationshipData(data, ownerActorOrUuid = null) {
  const source = isPlainObject(data) ? data : {};
  const migrated = stripRenderOnlyFields(source, DATA_RENDER_ONLY_FIELDS);

  migrated.version = SCHEMA_VERSION;
  migrated.ownerActorUuid = actorUuidOf(ownerActorOrUuid) || asString(source.ownerActorUuid);
  migrated.profile = normalizeProfile(source.profile);
  migrated.relationships = normalizeRelationships(source.relationships);

  return migrated;
}

export const normalizeRelationshipData = migrateRelationshipData;

export function normalizeProfile(profile) {
  const source = isPlainObject(profile) ? profile : {};
  const normalized = stripRenderOnlyFields(source, PROFILE_LEGACY_FIELDS);

  normalized.title = asString(source.title, PROFILE_DEFAULTS.title);
  normalized.bondLabel = asString(source.bondLabel, PROFILE_DEFAULTS.bondLabel).trim().slice(0, 40) || PROFILE_DEFAULTS.bondLabel;
  normalized.bondLabelPlural = asString(source.bondLabelPlural, PROFILE_DEFAULTS.bondLabelPlural).trim().slice(0, 40) || PROFILE_DEFAULTS.bondLabelPlural;
  normalized.subtitle = asString(source.subtitle, PROFILE_DEFAULTS.subtitle);
  normalized.lozenge = asString(source.lozenge, PROFILE_DEFAULTS.lozenge);
  normalized.archiveLabel = asString(source.archiveLabel, PROFILE_DEFAULTS.archiveLabel);
  normalized.sessionLabel = asString(source.sessionLabel, PROFILE_DEFAULTS.sessionLabel);
  normalized.calendarLabel = asString(source.calendarLabel, PROFILE_DEFAULTS.calendarLabel);
  normalized.showBgLetter = asBoolean(source.showBgLetter, PROFILE_DEFAULTS.showBgLetter);
  normalized.showNameRoman = asBoolean(source.showNameRoman, PROFILE_DEFAULTS.showNameRoman);
  normalized.fontScale = clamp(asNumber(source.fontScale, PROFILE_DEFAULTS.fontScale), 0.85, 1.15);
  normalized.maxRelationshipSlots = asInteger(source.maxRelationshipSlots, PROFILE_DEFAULTS.maxRelationshipSlots, 1, 99);
  normalized.mapVisibilityMode = MAP_VISIBILITY_VALUES.includes(source.mapVisibilityMode)
    ? source.mapVisibilityMode
    : PROFILE_DEFAULTS.mapVisibilityMode;
  normalized.mapMaxDepth = asInteger(source.mapMaxDepth, PROFILE_DEFAULTS.mapMaxDepth, 1, 4);
  normalized.mapMaxNodes = asInteger(source.mapMaxNodes, PROFILE_DEFAULTS.mapMaxNodes, 1, 200);
  normalized.mapUseThumbnails = asBoolean(source.mapUseThumbnails, PROFILE_DEFAULTS.mapUseThumbnails);
  normalized.themeId = asString(source.themeId, PROFILE_DEFAULTS.themeId) || PROFILE_DEFAULTS.themeId;

  delete normalized.useWorldTitle;
  delete normalized.useWorldTheme;

  return normalized;
}

export function normalizeRelationship(relationship) {
  const source = isPlainObject(relationship) ? relationship : {};
  const migrated = { ...source };

  if (!migrated.portrait && typeof migrated.customImage === "string") {
    migrated.portrait = migrated.customImage;
  }

  const notes = normalizeNotes(migrated);

  const normalized = stripRenderOnlyFields(migrated, RELATIONSHIP_RENDER_ONLY_FIELDS);
  delete normalized.customImage;
  delete normalized.playerNotes;
  delete normalized.gmNotes;

  const entryType = ENTRY_TYPES.has(migrated.entryType)
    ? migrated.entryType
    : (asString(migrated.targetUuid) ? "actor" : "custom");
  const maxRank = asInteger(migrated.maxRank, DEFAULT_MAX_RANK, 1, 99);

  normalized.id = asString(migrated.id) || generateRelationshipId();
  normalized.entryType = entryType;
  normalized.targetUuid = entryType === "actor" ? asString(migrated.targetUuid) : "";
  normalized.customName = asString(migrated.customName);
  normalized.customRole = asString(migrated.customRole);
  normalized.portrait = asString(migrated.portrait);
  normalized.listImage = asString(migrated.listImage);
  // Drop the short-lived experimental organization-only fields. The stable
  // replacement is a shared manual choice for every relationship type.
  delete normalized.organizationImageMode;
  delete normalized.portraitImageMode;
  normalized.portraitPresentation = PORTRAIT_PRESENTATION_VALUES.includes(migrated.portraitPresentation)
    ? migrated.portraitPresentation
    : PORTRAIT_PRESENTATIONS.CUTOUT;
  normalized.rankCutinRankUpImage = asString(migrated.rankCutinRankUpImage);
  normalized.rankCutinMaxImage = asString(migrated.rankCutinMaxImage);
  normalized.rankCutinRankDownImage = asString(migrated.rankCutinRankDownImage);
  normalized.rankCutinUnlockImage = asString(migrated.rankCutinUnlockImage);
  normalized.mapThumbnail = asString(migrated.mapThumbnail);
  const mapThumbnailFrame = normalizeMapThumbnailFrame(migrated);
  normalized.mapThumbnailScale = mapThumbnailFrame.scale;
  normalized.mapThumbnailOffset = { x: mapThumbnailFrame.x, y: mapThumbnailFrame.y };
  normalized.mapInspectorImage = asString(migrated.mapInspectorImage);
  const mapInspectorFrame = normalizeMapInspectorFrame(migrated);
  normalized.mapInspectorScale = mapInspectorFrame.scale;
  normalized.mapInspectorOffset = { x: mapInspectorFrame.x, y: mapInspectorFrame.y };
  normalized.portraitTag = asString(migrated.portraitTag, "NO IMAGE");
  normalized.portraitScale = asNumber(migrated.portraitScale, 1);
  normalized.portraitOffset = normalizePortraitOffset(migrated.portraitOffset);
  normalized.rankCutinScale = clamp(asNumber(migrated.rankCutinScale, 1), 0.1, 3);
  normalized.rankCutinOffsetX = clamp(asNumber(migrated.rankCutinOffsetX, 0), -999, 999);
  normalized.rankCutinOffsetY = clamp(asNumber(migrated.rankCutinOffsetY, 0), -999, 999);
  normalized.nameRoman = asString(migrated.nameRoman);
  normalized.classId = asString(migrated.classId);
  normalized.categoryId = asString(migrated.categoryId);
  normalized.categoryLabel = asString(migrated.categoryLabel);
  normalized.categoryLabelEn = asString(migrated.categoryLabelEn);
  normalized.maxRank = maxRank;
  normalized.rankSteps = asInteger(migrated.rankSteps, DEFAULT_RANK_STEPS, 1, 99);
  const storedRank = asInteger(migrated.rank, 0, 0, maxRank);
  const storedProgress = asInteger(migrated.rankProgress, 0, 0, normalized.rankSteps);
  const rankCarry = storedProgress >= normalized.rankSteps ? 1 : 0;
  normalized.rank = Math.min(maxRank, storedRank + rankCarry);
  normalized.rankProgress = normalized.rank >= maxRank
    ? 0
    : (rankCarry > 0 ? 0 : storedProgress);
  normalized.polarity = normalized.rank > 0 || normalized.rankProgress > 0
    ? (RELATIONSHIP_POLARITY_VALUES.includes(migrated.polarity)
      ? migrated.polarity
      : RELATIONSHIP_POLARITIES.POSITIVE)
    : RELATIONSHIP_POLARITIES.POSITIVE;
  normalized.rankMacroTriggers = normalizeRankMacroTriggers(migrated.rankMacroTriggers);
  normalized.accent = asString(migrated.accent);
  normalized.bio = asString(migrated.bio);
  normalized.notes = notes;
  normalized.locked = asBoolean(migrated.locked, false);
  normalized.unlockOnGift = entryType !== "organization"
    && normalized.locked === true
    && asBoolean(migrated.unlockOnGift, false);
  normalized.unlockRule = migrated.unlockRule === undefined ? null : cloneStorageValue(migrated.unlockRule);
  if (isPlainObject(normalized.unlockRule)) {
    normalized.unlockRule.polarity = RELATIONSHIP_POLARITY_VALUES.includes(normalized.unlockRule.polarity)
      ? normalized.unlockRule.polarity
      : RELATIONSHIP_POLARITIES.POSITIVE;
  }
  normalized.visibility = VISIBILITY_VALUES.has(migrated.visibility) ? migrated.visibility : "players";
  normalized.playerEditable = asBoolean(migrated.playerEditable, true);
  normalized.stats = normalizeStats(migrated.stats);
  normalized.events = normalizeEvents(migrated.events);
  normalized.giftProfileMode = normalizeGiftProfileMode(migrated.giftProfileMode, entryType);
  normalized.giftProfile = normalizeRelationshipGiftProfile(migrated.giftProfile, normalized.giftProfileMode, entryType);
  normalized.sync = normalizeRelationshipSync(migrated.sync);

  return normalized;
}

/** Whether this locked relationship accepts one committed Gift as its unlock trigger. */
export function canUnlockRelationshipWithGift(relationship) {
  return relationship?.locked === true
    && relationship?.entryType !== "organization"
    && (relationship?.unlockOnGift === true || relationship?.firstGiftUnlockAvailable === true);
}

/**
 * Normalize the lightweight synchronization pointer kept with an Actor's full
 * Relationship snapshot. Invalid or incomplete pointers become `null`, so
 * legacy schema-v1 flags require no special migration pass.
 */
export function normalizeRelationshipSync(sync) {
  if (!isPlainObject(sync)) return null;
  const groupId = asString(sync.groupId).trim().slice(0, 160);
  if (!groupId || !RELATIONSHIP_SYNC_MODE_VALUES.includes(sync.mode)) return null;
  return {
    groupId,
    mode: sync.mode,
    appliedRevision: asInteger(sync.appliedRevision, 0, 0, Number.MAX_SAFE_INTEGER)
  };
}

export function normalizeGiftProfileMode(mode, entryType = "custom") {
  if (mode === GIFT_PROFILE_MODES.DISABLED) return GIFT_PROFILE_MODES.DISABLED;
  // Organizations are reputation targets rather than item recipients. Keep the
  // existing Gift subsystem out of this first organization phase so a saved
  // organization can never accidentally inherit a custom entry's Gift profile.
  if (entryType === "organization") return GIFT_PROFILE_MODES.DISABLED;
  if (entryType === "custom") return GIFT_PROFILE_MODES.RELATIONSHIP_OVERRIDE;
  if (mode === GIFT_PROFILE_MODES.RELATIONSHIP_OVERRIDE) return GIFT_PROFILE_MODES.RELATIONSHIP_OVERRIDE;
  return GIFT_PROFILE_MODES.TARGET_ACTOR;
}

function normalizeRelationshipGiftProfile(giftProfile, mode, entryType = "custom") {
  if (entryType === "organization") return null;
  if (mode === GIFT_PROFILE_MODES.TARGET_ACTOR) return null;
  if (mode === GIFT_PROFILE_MODES.DISABLED && giftProfile == null) return null;
  return normalizeGiftProfile(giftProfile);
}

export function createDefaultGiftProfile() {
  return normalizeGiftProfile({});
}

export function normalizeGiftProfile(profile) {
  const source = isPlainObject(profile) ? profile : {};
  const reactions = normalizeGiftReactionDefinitions(source);
  const reactionIds = reactions.map((reaction) => reaction.id);
  const defaultReactionId = normalizeProfileReactionId(source.defaultReactionId, reactionIds, GIFT_PROFILE_DEFAULTS.defaultReactionId);
  return {
    version: asInteger(source.version, GIFT_PROFILE_VERSION, 1, 99),
    enabled: asBoolean(source.enabled, GIFT_PROFILE_DEFAULTS.enabled),
    consumeMode: enumValue(source.consumeMode, GIFT_CONSUME_MODE_VALUES, GIFT_PROFILE_DEFAULTS.consumeMode),
    maxQuantityPerGift: asInteger(source.maxQuantityPerGift, GIFT_PROFILE_DEFAULTS.maxQuantityPerGift, 1, 999),
    allowMaxRankGifts: asBoolean(source.allowMaxRankGifts, GIFT_PROFILE_DEFAULTS.allowMaxRankGifts),
    preferenceVisibility: enumValue(source.preferenceVisibility, GIFT_PREFERENCE_VISIBILITY_VALUES, GIFT_PROFILE_DEFAULTS.preferenceVisibility),
    reactionAudience: enumValue(source.reactionAudience, GIFT_REACTION_AUDIENCE_VALUES, GIFT_PROFILE_DEFAULTS.reactionAudience),
    reactionDisplayMode: enumValue(source.reactionDisplayMode, GIFT_REACTION_DISPLAY_MODE_VALUES, GIFT_PROFILE_DEFAULTS.reactionDisplayMode),
    reactions,
    defaultReactionId,
    unmatchedGift: normalizeUnmatchedGift(source.unmatchedGift, reactionIds, defaultReactionId),
    rejectedConsumeMode: normalizeLegacyRejectedConsumeMode(source.rejectedConsumeMode, reactions),
    stages: normalizeGiftStages(source.stages, reactions, defaultReactionId)
  };
}

export function getTargetActorGiftProfile(actor, fallbackProfile = null) {
  const stored = typeof actor?.getFlag === "function" ? actor.getFlag(FLAG_SCOPE, GIFT_PROFILE_FLAG_KEY) : undefined;
  return normalizeGiftProfile(stored === undefined ? fallbackProfile ?? {} : stored);
}

export function captureTargetActorGiftProfileState(actor) {
  const stored = typeof actor?.getFlag === "function" ? actor.getFlag(FLAG_SCOPE, GIFT_PROFILE_FLAG_KEY) : undefined;
  return {
    exists: stored !== undefined,
    profile: stored === undefined ? null : cloneStorageValue(stored)
  };
}

export async function setTargetActorGiftProfile(actor, profile, options = {}) {
  const transaction = await writeTargetActorGiftProfile(actor, profile, options);
  return transaction.profile;
}

export async function writeTargetActorGiftProfile(actor, profile, { baseline = null } = {}) {
  if (typeof actor?.setFlag !== "function") throw new Error("Target Actor cannot store Gift Profile flags.");
  return enqueueTargetGiftProfileMutation(actor, async () => {
    const previousState = captureTargetActorGiftProfileState(actor);
    const localProfile = normalizeGiftProfile(profile);
    const normalized = baseline && typeof baseline === "object"
      ? normalizeGiftProfile(mergeStorageValue(
        normalizeGiftProfile(baseline),
        localProfile,
        normalizeGiftProfile(previousState.exists ? previousState.profile : {})
      ))
      : localProfile;
    const writeToken = randomToken();
    assertActiveGmFlagCommitAuthority();
    await actor.setFlag(FLAG_SCOPE, GIFT_PROFILE_FLAG_KEY, {
      ...normalized,
      [TARGET_GIFT_PROFILE_WRITE_TOKEN_FIELD]: writeToken
    });
    return { profile: normalized, previousState, writeToken };
  });
}

export async function restoreTargetActorGiftProfile(actor, { expectedProfile, expectedWriteToken, previousState } = {}) {
  if (typeof actor?.getFlag !== "function" || typeof actor?.setFlag !== "function") {
    throw new Error("Target Actor cannot restore Gift Profile flags.");
  }
  return enqueueTargetGiftProfileMutation(actor, async () => {
    const current = actor.getFlag(FLAG_SCOPE, GIFT_PROFILE_FLAG_KEY);
    const token = asString(expectedWriteToken).trim();
    if (token) {
      if (current?.[TARGET_GIFT_PROFILE_WRITE_TOKEN_FIELD] !== token) return false;
    } else if (!giftProfilesEqual(current, expectedProfile)) return false;
    if (previousState?.exists === true) {
      assertActiveGmFlagCommitAuthority();
      await actor.setFlag(FLAG_SCOPE, GIFT_PROFILE_FLAG_KEY, cloneStorageValue(previousState.profile));
      return true;
    }
    if (typeof actor.unsetFlag !== "function") {
      throw new Error("Target Actor cannot restore a missing Gift Profile flag.");
    }
    assertActiveGmFlagCommitAuthority();
    await actor.unsetFlag(FLAG_SCOPE, GIFT_PROFILE_FLAG_KEY);
    return true;
  });
}

function normalizeGiftReactionDefinitions(profileSource) {
  const source = isPlainObject(profileSource) ? profileSource : {};
  const explicitEntries = giftReactionDefinitionEntries(source.reactions);
  const entries = explicitEntries ?? legacyGiftReactionPresetEntries(source.rejectedConsumeMode);
  const normalized = [];
  const seen = new Set();
  for (const entry of entries) addGiftReactionDefinition(normalized, seen, entry);
  for (const id of inferGiftReactionIds(source)) {
    addGiftReactionDefinition(normalized, seen, { id, label: giftReactionPreset(id)?.label ?? id });
  }
  if (normalized.length === 0) addGiftReactionDefinition(normalized, seen, giftReactionPreset(GIFT_REACTIONS.NEUTRAL));
  return normalized;
}

function giftReactionDefinitionEntries(reactions) {
  if (Array.isArray(reactions)) return reactions;
  if (!isPlainObject(reactions)) return null;
  return Object.entries(reactions).map(([id, value]) => ({ ...(isPlainObject(value) ? value : {}), id }));
}

function legacyGiftReactionPresetEntries(rejectedConsumeMode) {
  const legacyRejectedMode = enumValue(rejectedConsumeMode, GIFT_REJECTED_CONSUME_MODE_VALUES, GIFT_PROFILE_DEFAULTS.rejectedConsumeMode);
  return GIFT_REACTION_PRESETS.map((preset) => {
    if (preset.id !== GIFT_REACTIONS.REJECTED) return preset;
    return {
      ...preset,
      consumeMode: legacyRejectedMode === "consume"
        ? GIFT_REACTION_CONSUME_MODES.CONSUME
        : GIFT_REACTION_CONSUME_MODES.KEEP
    };
  });
}

function inferGiftReactionIds(profileSource) {
  const ids = [];
  const add = (value) => {
    const id = sanitizeGiftReactionId(value);
    if (id) ids.push(id);
  };
  add(profileSource.defaultReactionId);
  add(profileSource.unmatchedGift?.reactionId);
  add(profileSource.unmatchedGift?.reaction);
  for (const stage of Array.isArray(profileSource.stages) ? profileSource.stages : []) {
    if (!isPlainObject(stage)) continue;
    for (const rule of Array.isArray(stage.rules) ? stage.rules : []) add(rule?.reaction);
    if (isPlainObject(stage.reactions)) {
      for (const key of Object.keys(stage.reactions)) add(key);
    }
  }
  return ids;
}

function addGiftReactionDefinition(out, seen, definition) {
  const source = isPlainObject(definition) ? definition : {};
  const id = sanitizeGiftReactionId(source.id ?? source.key ?? source.reaction);
  if (!id || seen.has(id)) return;
  const preset = giftReactionPreset(id);
  out.push({
    id,
    label: asString(source.label, preset?.label ?? id).trim() || preset?.label || id,
    consumeMode: enumValue(source.consumeMode, GIFT_REACTION_CONSUME_MODE_VALUES, preset?.consumeMode ?? GIFT_REACTION_CONSUME_MODES.INHERIT)
  });
  seen.add(id);
}

function giftReactionPreset(id) {
  return GIFT_REACTION_PRESETS.find((preset) => preset.id === id) ?? null;
}

function normalizeProfileReactionId(value, reactionIds, fallback) {
  const safeFallback = reactionIds.includes(fallback) ? fallback : reactionIds[0];
  const id = sanitizeGiftReactionId(value);
  return reactionIds.includes(id) ? id : safeFallback;
}

function normalizeLegacyRejectedConsumeMode(value, reactions) {
  const rejected = reactions.find((reaction) => reaction.id === GIFT_REACTIONS.REJECTED);
  if (rejected?.consumeMode === GIFT_REACTION_CONSUME_MODES.CONSUME) return "consume";
  if (rejected?.consumeMode === GIFT_REACTION_CONSUME_MODES.KEEP) return "keep";
  return enumValue(value, GIFT_REJECTED_CONSUME_MODE_VALUES, GIFT_PROFILE_DEFAULTS.rejectedConsumeMode);
}

function normalizeUnmatchedGift(unmatchedGift, reactionIds, defaultReactionId) {
  const source = isPlainObject(unmatchedGift) ? unmatchedGift : {};
  return {
    mode: enumValue(source.mode, GIFT_UNMATCHED_GIFT_MODE_VALUES, GIFT_PROFILE_DEFAULTS.unmatchedGift.mode),
    reactionId: normalizeProfileReactionId(source.reactionId ?? source.reaction, reactionIds, defaultReactionId),
    progressDelta: asInteger(source.progressDelta, GIFT_PROFILE_DEFAULTS.unmatchedGift.progressDelta, 0, 99)
  };
}

function normalizeGiftStages(stages, reactions, defaultReactionId) {
  const sourceStages = Array.isArray(stages) ? stages : GIFT_PROFILE_DEFAULTS.stages;
  const normalized = sourceStages
    .filter((stage) => isPlainObject(stage))
    .map((stage, index) => normalizeGiftStage(stage, index, reactions, defaultReactionId));
  return normalized.length > 0
    ? normalized
    : GIFT_PROFILE_DEFAULTS.stages.map((stage, index) => normalizeGiftStage(stage, index, reactions, defaultReactionId));
}

function normalizeGiftStage(stage, index, reactions, defaultReactionId) {
  const fallback = GIFT_PROFILE_DEFAULTS.stages[0];
  const rankMin = asInteger(stage.rankMin, fallback.rankMin, 0, 99);
  const rankMax = asInteger(stage.rankMax, rankMin, rankMin, 99);
  const reactionIds = reactions.map((reaction) => reaction.id);
  return {
    id: asString(stage.id) || (index === 0 ? fallback.id : `rank-${rankMin}`),
    label: asString(stage.label) || `Rank ${rankMin}`,
    rankMin,
    rankMax,
    rules: normalizeGiftRules(stage.rules, reactionIds, defaultReactionId),
    reactions: normalizeGiftReactions(stage.reactions, reactions)
  };
}

function normalizeGiftRules(rules, reactionIds, defaultReactionId) {
  if (!Array.isArray(rules)) return [];
  return rules
    .filter((rule) => isPlainObject(rule))
    .map((rule, index) => normalizeGiftRule(rule, index, reactionIds, defaultReactionId));
}

function normalizeGiftRule(rule, index, reactionIds, defaultReactionId) {
  return {
    id: asString(rule.id) || `gift_rule_${index + 1}`,
    label: asString(rule.label),
    match: normalizeGiftRuleMatch(rule.match),
    reaction: normalizeProfileReactionId(rule.reaction, reactionIds, defaultReactionId)
  };
}

function normalizeGiftRuleMatch(match) {
  const source = isPlainObject(match) ? match : {};
  return {
    mode: enumValue(source.mode, GIFT_MATCH_MODE_VALUES, "name"),
    value: asString(source.value).trim()
  };
}

function normalizeGiftReactions(reactions, reactionDefinitions) {
  const source = isPlainObject(reactions) ? reactions : {};
  const normalized = {};
  for (const reaction of reactionDefinitions) {
    normalized[reaction.id] = normalizeGiftReaction(source[reaction.id], giftReactionConfigFallback(reaction.id));
  }
  return normalized;
}

function giftReactionConfigFallback(reactionId) {
  return GIFT_REACTION_DEFAULTS[reactionId] ?? CUSTOM_GIFT_REACTION_DEFAULT;
}

function normalizeGiftReaction(reaction, fallback) {
  const source = isPlainObject(reaction) ? reaction : {};
  return {
    progressDelta: asInteger(source.progressDelta, fallback.progressDelta, 0, 99),
    line: asString(source.line, fallback.line),
    previewHintLine: asString(source.previewHintLine, fallback.previewHintLine),
    previewResultLine: asString(source.previewResultLine, fallback.previewResultLine),
    cutinImage: asString(source.cutinImage, fallback.cutinImage),
    sfx: asString(source.sfx, fallback.sfx),
    cutinScale: clamp(asNumber(source.cutinScale, fallback.cutinScale), 0.1, 3),
    cutinOffsetX: clamp(asNumber(source.cutinOffsetX, fallback.cutinOffsetX), -999, 999),
    cutinOffsetY: clamp(asNumber(source.cutinOffsetY, fallback.cutinOffsetY), -999, 999)
  };
}

export function normalizeStats(stats) {
  if (!Array.isArray(stats)) return [];
  return stats.map((stat) => normalizeStat(stat));
}

export function normalizeStat(stat) {
  const source = isPlainObject(stat) ? stat : {};
  const normalized = stripRenderOnlyFields(source, STAT_RENDER_ONLY_FIELDS);

  normalized.key = asString(source.key);
  normalized.value = asString(source.value);
  normalized.accent = source.accent === true;

  return normalized;
}

export function normalizeEvents(events) {
  if (!Array.isArray(events)) return [];
  return ensureUniqueNormalizedIds(events.map((event) => normalizeEvent(event)));
}

function normalizeRelationships(relationships) {
  if (!Array.isArray(relationships)) return [];
  return ensureUniqueNormalizedIds(
    relationships.map((relationship) => normalizeRelationship(relationship))
  );
}

function ensureUniqueNormalizedIds(entries) {
  const used = new Set();
  return entries.map((entry) => {
    const normalized = entry;
    const baseId = asString(normalized?.id) || "entry";
    let id = baseId;
    let suffix = 2;
    while (used.has(id)) id = `${baseId}~${suffix++}`;
    normalized.id = id;
    used.add(id);
    return normalized;
  });
}

export function normalizeEvent(event) {
  const source = isPlainObject(event) ? event : {};
  const normalized = stripRenderOnlyFields(source, EVENT_RENDER_ONLY_FIELDS);

  normalized.id = asString(source.id) || generateEventId();
  normalized.eventType = EVENT_TYPES.has(source.eventType) ? source.eventType : "note";
  normalized.day = asString(source.day);
  normalized.text = asString(source.text);
  normalized.rankLabel = asString(source.rankLabel);
  // `0` means the entry is always visible. Positive values are a player-view
  // reveal threshold and remain independent from the display-only rankLabel.
  normalized.revealAtRank = asInteger(source.revealAtRank, 0, 0, 99);
  normalized.quote = asString(source.quote);
  normalized.recollection = asString(source.recollection);
  normalized.image = asString(source.image);
  normalized.imageScale = asNumber(source.imageScale, 1);
  normalized.imageOffsetX = asNumber(source.imageOffsetX, 0);
  normalized.imageOffsetY = asNumber(source.imageOffsetY, 0);
  normalized.rankChange = normalizeEventRankChange(source);
  // Keep the established alias for integrations that still read isRankUp.
  normalized.isRankUp = normalized.rankChange === EVENT_RANK_CHANGES.UP;
  if (normalized.eventType === "gift") {
    normalized.gift = normalizeGiftMetadata(source.gift);
  } else {
    delete normalized.gift;
  }

  return normalized;
}

/** Whether an Event Log entry has reached its configured player-view rank. */
export function isEventRevealedAtRank(event, relationshipRank = 0) {
  const requiredRank = asInteger(event?.revealAtRank, 0, 0, 99);
  if (requiredRank === 0) return true;
  const currentRank = asInteger(relationshipRank, 0, 0, 99);
  return currentRank >= requiredRank;
}

export function normalizeGiftMetadata(gift) {
  const source = isPlainObject(gift) ? gift : {};
  if (!isModernGiftMetadata(source)) return normalizeLegacyGiftMetadata(source);
  return {
    giverActorUuid: asString(source.giverActorUuid),
    targetActorUuid: asString(source.targetActorUuid),
    targetLabel: asString(source.targetLabel),
    targetKind: enumValue(source.targetKind, GIFT_TARGET_KIND_VALUES, GIFT_TARGET_KINDS.CUSTOM),
    relationshipId: asString(source.relationshipId),
    itemId: asString(source.itemId),
    itemUuid: asString(source.itemUuid),
    sourceItemUuid: asString(source.sourceItemUuid),
    itemName: asString(source.itemName),
    itemImg: asString(source.itemImg),
    quantity: asInteger(source.quantity, 1, 1, 999),
    consumed: asBoolean(source.consumed, false),
    consumeMode: enumValue(source.consumeMode, GIFT_CONSUME_MODE_VALUES, GIFT_PROFILE_DEFAULTS.consumeMode),
    profileSource: source.profileSource,
    stageId: asString(source.stageId),
    reaction: sanitizeGiftReactionId(source.reaction) || GIFT_PROFILE_DEFAULTS.defaultReactionId,
    reactionLabel: asString(source.reactionLabel),
    unitProgressDelta: asInteger(source.unitProgressDelta, 0, 0, 99),
    totalProgressDelta: asInteger(source.totalProgressDelta, 0, 0, 9999),
    ruleId: asString(source.ruleId),
    approvalRequestId: asString(source.approvalRequestId)
  };
}

function isModernGiftMetadata(source) {
  return (source.profileSource === GIFT_PROFILE_SOURCES.TARGET_ACTOR || source.profileSource === GIFT_PROFILE_SOURCES.RELATIONSHIP_OVERRIDE)
    && GIFT_TARGET_KIND_VALUES.includes(source.targetKind)
    && sanitizeGiftReactionId(source.reaction) !== ""
    && GIFT_CONSUME_MODE_VALUES.includes(source.consumeMode)
    && typeof source.consumed === "boolean"
    && asString(source.relationshipId) !== ""
    && asString(source.itemName) !== ""
    && source.unitProgressDelta !== undefined
    && source.totalProgressDelta !== undefined;
}

function normalizeLegacyGiftMetadata(source) {
  const metadata = {
    giverActorUuid: asString(source.giverActorUuid) || asString(source.sourceActorUuid),
    targetActorUuid: asString(source.targetActorUuid),
    targetLabel: asString(source.targetLabel),
    targetKind: enumValue(source.targetKind, GIFT_TARGET_KIND_VALUES, GIFT_TARGET_KINDS.CUSTOM),
    relationshipId: asString(source.relationshipId),
    itemId: asString(source.itemId),
    itemUuid: asString(source.itemUuid),
    sourceItemUuid: asString(source.sourceItemUuid),
    itemName: asString(source.itemName),
    itemImg: asString(source.itemImg),
    quantity: asInteger(source.quantity, 1, 1, 999),
    consumed: asBoolean(source.consumed, false),
    consumeMode: enumValue(source.consumeMode, GIFT_CONSUME_MODE_VALUES, GIFT_PROFILE_DEFAULTS.consumeMode),
    profileSource: GIFT_PROFILE_SOURCES.LEGACY,
    legacy: true
  };
  const sourceActorUuid = asString(source.sourceActorUuid);
  if (sourceActorUuid) metadata.sourceActorUuid = sourceActorUuid;
  if (source.rankProgressDelta !== undefined) {
    metadata.rankProgressDelta = asInteger(source.rankProgressDelta, 0, 0, 99);
  }
  return metadata;
}

export function normalizeNotes(source) {
  const raw = source?.notes;
  if (Array.isArray(raw)) {
    return raw.map((note) => normalizeNote(note));
  }
  return migrateLegacyNotes(source);
}

export function normalizeNote(note) {
  const source = isPlainObject(note) ? note : {};
  return {
    id: asString(source.id) || generateNoteId(),
    title: asString(source.title),
    visibility: NOTE_VISIBILITY_VALUES.has(source.visibility) ? source.visibility : "players",
    body: asString(source.body)
  };
}

function migrateLegacyNotes(source) {
  const legacyString = typeof source?.notes === "string" ? source.notes : "";
  const playerBody = asString(source?.playerNotes) || legacyString;
  const gmBody = asString(source?.gmNotes);
  const notes = [];
  if (playerBody.trim() !== "") {
    notes.push({ id: LEGACY_PLAYER_NOTE_ID, title: LEGACY_PLAYER_NOTE_TITLE, visibility: "players", body: playerBody });
  }
  if (gmBody.trim() !== "") {
    notes.push({ id: LEGACY_GM_NOTE_ID, title: LEGACY_GM_NOTE_TITLE, visibility: "gm", body: gmBody });
  }
  return notes;
}

export function generateRelationshipId() {
  return `rel_${randomToken()}`;
}

export function generateEventId() {
  return `evt_${randomToken()}`;
}

export function generateNoteId() {
  return `note_${randomToken()}`;
}

export function generateRankMacroTriggerId() {
  return `rmt_${randomToken()}`;
}

export function normalizeRankMacroTriggers(triggers) {
  const source = Array.isArray(triggers) ? triggers : [];
  const normalized = [];
  const ids = new Set();
  const pairs = new Set();
  for (const entry of source) {
    if (!isPlainObject(entry)) continue;
    const macroUuid = asString(entry.macroUuid).trim().slice(0, 500);
    if (!macroUuid) continue;
    const rank = asInteger(entry.rank, 1, 1, 99);
    const polarity = RELATIONSHIP_POLARITY_VALUES.includes(entry.polarity)
      ? entry.polarity
      : RELATIONSHIP_POLARITIES.POSITIVE;
    const defaultDirection = polarity === RELATIONSHIP_POLARITIES.NEGATIVE
      ? RANK_MACRO_DIRECTIONS.DOWN
      : RANK_MACRO_DIRECTIONS.UP;
    const direction = RANK_MACRO_DIRECTION_VALUES.includes(entry.direction)
      ? entry.direction
      : defaultDirection;
    const pair = `${polarity}::${direction}::${rank}::${macroUuid}`;
    if (pairs.has(pair)) continue;
    pairs.add(pair);
    let id = asString(entry.id).trim().slice(0, 100);
    if (!id || ids.has(id)) id = generateRankMacroTriggerId();
    ids.add(id);
    normalized.push({ id, polarity, direction, rank, macroUuid });
  }
  return normalized.sort((left, right) => (
    left.polarity.localeCompare(right.polarity)
      || left.rank - right.rank
      || left.direction.localeCompare(right.direction)
  ));
}

/** Resolve the canonical three-state Event Log rank marker. */
export function normalizeEventRankChange(event) {
  const source = isPlainObject(event) ? event : {};
  if (EVENT_RANK_CHANGE_VALUES.includes(source.rankChange)) return source.rankChange;
  return source.isRankUp === true ? EVENT_RANK_CHANGES.UP : EVENT_RANK_CHANGES.NONE;
}

/** Translate legacy isRankUp-only event patches before merging with canonical data. */
export function normalizeEventRankChangePatch(patch) {
  const source = isPlainObject(patch) ? cloneStorageValue(patch) : {};
  if (
    !Object.prototype.hasOwnProperty.call(source, "rankChange")
    && Object.prototype.hasOwnProperty.call(source, "isRankUp")
  ) {
    source.rankChange = source.isRankUp === true
      ? EVENT_RANK_CHANGES.UP
      : EVENT_RANK_CHANGES.NONE;
  }
  return source;
}

function normalizePortraitOffset(offset) {
  const source = isPlainObject(offset) ? offset : {};
  return {
    x: asNumber(source.x, 0),
    y: asNumber(source.y, 0)
  };
}

function stripRenderOnlyFields(source, renderOnlyFields) {
  const clean = {};
  for (const [key, value] of Object.entries(source)) {
    if (key.startsWith("_") || renderOnlyFields.has(key)) continue;
    clean[key] = cloneStorageValue(value);
  }
  return clean;
}

function actorUuidOf(actorOrUuid) {
  if (typeof actorOrUuid === "string") return actorOrUuid;
  return asString(actorOrUuid?.uuid);
}

function isPlainObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function asString(value, fallback = "") {
  return typeof value === "string" ? value : fallback;
}

function sanitizeGiftReactionId(value) {
  const text = asString(value).trim();
  if (!text) return "";
  const id = text
    .replace(/[^A-Za-z0-9_-]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 64);
  if (!id || FORBIDDEN_GIFT_REACTION_IDS.has(id)) return "";
  return id;
}

function asBoolean(value, fallback) {
  return typeof value === "boolean" ? value : fallback;
}

function asNumber(value, fallback) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function enumValue(value, allowedValues, fallback) {
  return allowedValues.includes(value) ? value : fallback;
}

function asInteger(value, fallback, min, max) {
  return Math.round(clamp(asNumber(value, fallback), min, max));
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function giftProfilesEqual(left, right) {
  return JSON.stringify(normalizeGiftProfile(left)) === JSON.stringify(normalizeGiftProfile(right));
}

function assertActiveGmFlagCommitAuthority() {
  const user = globalThis.game?.user;
  if (user && user.isGM !== true) {
    throw new Error("Only the active GM can commit shared Gift Profile data.");
  }
  const activeGM = globalThis.game?.users?.activeGM;
  const activeIsCurrent = activeGM?.isSelf === true || (!!activeGM?.id && activeGM.id === user?.id);
  if (user?.isGM === true && activeGM && !activeIsCurrent) {
    throw new Error("The active GM changed before the Gift Profile update could commit. Please try again.");
  }
}

function targetGiftProfileMutationKey(actor) {
  const stable = asString(actor?.uuid).trim() || asString(actor?.id).trim();
  if (stable) return stable;
  if (!actor || (typeof actor !== "object" && typeof actor !== "function")) return "unknown-target-actor";
  let fallback = TARGET_GIFT_PROFILE_FALLBACK_KEYS.get(actor);
  if (!fallback) {
    fallback = `anonymous-target-actor-${nextTargetGiftProfileFallbackKey++}`;
    TARGET_GIFT_PROFILE_FALLBACK_KEYS.set(actor, fallback);
  }
  return fallback;
}

async function enqueueTargetGiftProfileMutation(actor, operation) {
  const key = targetGiftProfileMutationKey(actor);
  const previous = TARGET_GIFT_PROFILE_MUTATION_QUEUES.get(key) ?? Promise.resolve();
  const result = previous.then(operation, operation);
  const tail = result.then(() => undefined, () => undefined);
  TARGET_GIFT_PROFILE_MUTATION_QUEUES.set(key, tail);
  try {
    return await result;
  } finally {
    if (TARGET_GIFT_PROFILE_MUTATION_QUEUES.get(key) === tail) {
      TARGET_GIFT_PROFILE_MUTATION_QUEUES.delete(key);
    }
  }
}

function randomToken() {
  if (typeof foundry !== "undefined" && typeof foundry.utils?.randomID === "function") {
    return foundry.utils.randomID(16);
  }
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID().replaceAll("-", "").slice(0, 16);
  }
  return `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 10)}`;
}
