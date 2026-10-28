/**
 * Stylish Relationship Tracker - Constants
 * @module stylish-relationship-tracker/constants
 */

export const MODULE_ID = "stylish-relationship-tracker";
export const MODULE_NAME = "Stylish Relationship Tracker";

/** Foundry flag location for per-actor relationship data (Phase 2+). */
export const FLAG_SCOPE = MODULE_ID;
export const FLAG_KEY = "relationshipData";
export const GIFT_PROFILE_FLAG_KEY = "giftProfile";

/** Stored Actor-flag data schema version. Migrations land in data-model.js. */
export const SCHEMA_VERSION = 7;

/** Stored relationship direction. Rank and progress remain non-negative magnitude. */
export const RELATIONSHIP_POLARITIES = Object.freeze({
  POSITIVE: "positive",
  NEGATIVE: "negative"
});
export const RELATIONSHIP_POLARITY_VALUES = Object.freeze(Object.values(RELATIONSHIP_POLARITIES));

/** Direction along the visible relationship axis used by Rank Macro triggers. */
export const RANK_MACRO_DIRECTIONS = Object.freeze({
  UP: "up",
  DOWN: "down"
});
export const RANK_MACRO_DIRECTION_VALUES = Object.freeze(Object.values(RANK_MACRO_DIRECTIONS));

/** Presentation marker stored on Event Log entries. */
export const EVENT_RANK_CHANGES = Object.freeze({
  NONE: "none",
  UP: "up",
  DOWN: "down"
});
export const EVENT_RANK_CHANGE_VALUES = Object.freeze(Object.values(EVENT_RANK_CHANGES));

/** Relationship synchronization modes stored on each full Actor snapshot. */
export const RELATIONSHIP_SYNC_MODES = Object.freeze({
  CONTENT: "content",
  PARTY: "party"
});
export const RELATIONSHIP_SYNC_MODE_VALUES = Object.freeze(Object.values(RELATIONSHIP_SYNC_MODES));

/**
 * Fields whose canonical values may be shared by a synchronization group.
 *
 * This is deliberately an allowlist. Per-Actor role, progress, GM notes, lock
 * state, and permission fields are never copied merely because a Relationship
 * joins a group. PARTY mode adds only the two fields in
 * RELATIONSHIP_SYNC_PARTY_STATE_FIELDS; player notes and Event Logs are governed
 * by separate, explicit group options.
 */
export const RELATIONSHIP_SYNC_CONTENT_FIELDS = Object.freeze([
  "entryType",
  "targetUuid",
  "customName",
  "portrait",
  "listImage",
  "portraitPresentation",
  "rankCutinRankUpImage",
  "rankCutinMaxImage",
  "rankCutinRankDownImage",
  "rankCutinUnlockImage",
  "mapThumbnail",
  "mapThumbnailScale",
  "mapThumbnailOffset",
  "mapInspectorImage",
  "mapInspectorScale",
  "mapInspectorOffset",
  "portraitTag",
  "portraitScale",
  "portraitOffset",
  "rankCutinScale",
  "rankCutinOffsetX",
  "rankCutinOffsetY",
  "nameRoman",
  "classId",
  "categoryId",
  "categoryLabel",
  "categoryLabelEn",
  "maxRank",
  "rankSteps",
  "rankMacroTriggers",
  "accent",
  "bio",
  "stats",
  "giftProfileMode",
  "giftProfile"
]);
export const RELATIONSHIP_SYNC_PARTY_STATE_FIELDS = Object.freeze(["polarity", "rank", "rankProgress"]);

/** GM-only JournalEntry flag used for canonical synchronization data. */
export const RELATIONSHIP_SYNC_REGISTRY_VERSION = 2;
export const RELATIONSHIP_SYNC_REGISTRY_FLAG_KEY = "relationshipSyncRegistry";
export const RELATIONSHIP_SYNC_REGISTRY_JOURNAL_NAME = ".Stylish Relationship Sync Registry";

export const DESIGN_WIDTH = 1600;
export const DESIGN_HEIGHT = 1000;

export const PORTRAIT_PRESENTATIONS = Object.freeze({
  CUTOUT: "cutout",
  FRAMED: "framed"
});
export const PORTRAIT_PRESENTATION_VALUES = Object.freeze(Object.values(PORTRAIT_PRESENTATIONS));

export const MAP_VISIBILITY_MODES = Object.freeze({
  DIRECT: "direct",
  EXPANDED: "expanded",
  NETWORK: "network"
});

export const MAP_VISIBILITY_VALUES = Object.freeze(Object.values(MAP_VISIBILITY_MODES));

export const GIFT_PROFILE_VERSION = 1;

export const GIFT_PROFILE_MODES = Object.freeze({
  TARGET_ACTOR: "targetActor",
  RELATIONSHIP_OVERRIDE: "relationshipOverride",
  DISABLED: "disabled"
});
export const GIFT_PROFILE_MODE_VALUES = Object.freeze(Object.values(GIFT_PROFILE_MODES));

export const GIFT_CONSUME_MODES = Object.freeze({
  WORLD_DEFAULT: "worldDefault",
  CONSUME: "consume",
  KEEP: "keep"
});
export const GIFT_CONSUME_MODE_VALUES = Object.freeze(Object.values(GIFT_CONSUME_MODES));

export const GIFT_REJECTED_CONSUME_MODES = Object.freeze({
  KEEP: "keep",
  CONSUME: "consume"
});
export const GIFT_REJECTED_CONSUME_MODE_VALUES = Object.freeze(Object.values(GIFT_REJECTED_CONSUME_MODES));

export const GIFT_PREFERENCE_VISIBILITY = Object.freeze({
  HIDDEN: "hidden",
  HINT: "hint",
  FULL: "full"
});
export const GIFT_PREFERENCE_VISIBILITY_VALUES = Object.freeze(Object.values(GIFT_PREFERENCE_VISIBILITY));

export const GIFT_REACTION_AUDIENCE = Object.freeze({
  GIVER_ONLY: "giverOnly",
  GIVER_AND_GM: "giverAndGm",
  ELIGIBLE_VIEWERS: "eligibleViewers"
});
export const GIFT_REACTION_AUDIENCE_VALUES = Object.freeze(Object.values(GIFT_REACTION_AUDIENCE));

export const GIFT_REACTION_DISPLAY_MODES = Object.freeze({
  AUTO: "auto",
  DIALOG: "dialog",
  CUTIN: "cutin"
});
export const GIFT_REACTION_DISPLAY_MODE_VALUES = Object.freeze(Object.values(GIFT_REACTION_DISPLAY_MODES));

export const GIFT_UNMATCHED_GIFT_MODES = Object.freeze({
  NEUTRAL: "neutral",
  BLOCK: "block"
});
export const GIFT_UNMATCHED_GIFT_MODE_VALUES = Object.freeze(Object.values(GIFT_UNMATCHED_GIFT_MODES));

export const GIFT_REACTIONS = Object.freeze({
  FAVORITE: "favorite",
  LIKED: "liked",
  NEUTRAL: "neutral",
  DISLIKED: "disliked",
  REJECTED: "rejected"
});
export const GIFT_REACTION_VALUES = Object.freeze(Object.values(GIFT_REACTIONS));

export const GIFT_REACTION_CONSUME_MODES = Object.freeze({
  INHERIT: "inherit",
  CONSUME: "consume",
  KEEP: "keep"
});
export const GIFT_REACTION_CONSUME_MODE_VALUES = Object.freeze(Object.values(GIFT_REACTION_CONSUME_MODES));

export const GIFT_REACTION_PRESETS = Object.freeze([
  Object.freeze({ id: GIFT_REACTIONS.FAVORITE, label: "Favorite", consumeMode: GIFT_REACTION_CONSUME_MODES.INHERIT }),
  Object.freeze({ id: GIFT_REACTIONS.LIKED, label: "Liked", consumeMode: GIFT_REACTION_CONSUME_MODES.INHERIT }),
  Object.freeze({ id: GIFT_REACTIONS.NEUTRAL, label: "Neutral", consumeMode: GIFT_REACTION_CONSUME_MODES.INHERIT }),
  Object.freeze({ id: GIFT_REACTIONS.DISLIKED, label: "Disliked", consumeMode: GIFT_REACTION_CONSUME_MODES.INHERIT }),
  Object.freeze({ id: GIFT_REACTIONS.REJECTED, label: "Rejected", consumeMode: GIFT_REACTION_CONSUME_MODES.KEEP })
]);

export const GIFT_MATCH_MODES = Object.freeze({
  SOURCE_UUID: "sourceUuid",
  UUID: "uuid",
  NAME: "name",
  TYPE: "type",
  TAG: "tag"
});
export const GIFT_MATCH_MODE_VALUES = Object.freeze(Object.values(GIFT_MATCH_MODES));

export const GIFT_PROFILE_SOURCES = Object.freeze({
  TARGET_ACTOR: "targetActor",
  RELATIONSHIP_OVERRIDE: "relationshipOverride",
  LEGACY: "legacy"
});
export const GIFT_PROFILE_SOURCE_VALUES = Object.freeze(Object.values(GIFT_PROFILE_SOURCES));

export const GIFT_TARGET_KINDS = Object.freeze({
  ACTOR: "actor",
  CUSTOM: "custom"
});
export const GIFT_TARGET_KIND_VALUES = Object.freeze(Object.values(GIFT_TARGET_KINDS));

export const GIFT_REACTION_DEFAULTS = Object.freeze({
  [GIFT_REACTIONS.FAVORITE]: Object.freeze({ progressDelta: 3, line: "", previewHintLine: "", previewResultLine: "", cutinImage: "", sfx: "", cutinScale: 1, cutinOffsetX: 0, cutinOffsetY: 0 }),
  [GIFT_REACTIONS.LIKED]: Object.freeze({ progressDelta: 2, line: "", previewHintLine: "", previewResultLine: "", cutinImage: "", sfx: "", cutinScale: 1, cutinOffsetX: 0, cutinOffsetY: 0 }),
  [GIFT_REACTIONS.NEUTRAL]: Object.freeze({ progressDelta: 1, line: "", previewHintLine: "", previewResultLine: "", cutinImage: "", sfx: "", cutinScale: 1, cutinOffsetX: 0, cutinOffsetY: 0 }),
  [GIFT_REACTIONS.DISLIKED]: Object.freeze({ progressDelta: 0, line: "", previewHintLine: "", previewResultLine: "", cutinImage: "", sfx: "", cutinScale: 1, cutinOffsetX: 0, cutinOffsetY: 0 }),
  [GIFT_REACTIONS.REJECTED]: Object.freeze({ progressDelta: 0, line: "", previewHintLine: "", previewResultLine: "", cutinImage: "", sfx: "", cutinScale: 1, cutinOffsetX: 0, cutinOffsetY: 0 })
});

export const GIFT_PROFILE_DEFAULTS = Object.freeze({
  version: GIFT_PROFILE_VERSION,
  enabled: true,
  consumeMode: GIFT_CONSUME_MODES.CONSUME,
  maxQuantityPerGift: 1,
  allowMaxRankGifts: true,
  preferenceVisibility: GIFT_PREFERENCE_VISIBILITY.HIDDEN,
  reactionAudience: GIFT_REACTION_AUDIENCE.GIVER_AND_GM,
  reactionDisplayMode: GIFT_REACTION_DISPLAY_MODES.AUTO,
  reactions: GIFT_REACTION_PRESETS,
  defaultReactionId: GIFT_REACTIONS.NEUTRAL,
  unmatchedGift: Object.freeze({ mode: GIFT_UNMATCHED_GIFT_MODES.NEUTRAL, reactionId: GIFT_REACTIONS.NEUTRAL, progressDelta: 1 }),
  rejectedConsumeMode: GIFT_REJECTED_CONSUME_MODES.KEEP,
  stages: Object.freeze([
    Object.freeze({
      id: "rank-0",
      label: "Rank 0",
      rankMin: 0,
      rankMax: 0,
      rules: Object.freeze([]),
      reactions: GIFT_REACTION_DEFAULTS
    })
  ])
});

export const GIFT_SETTINGS_DEFAULTS = Object.freeze({
  allowPlayerGiveGifts: true,
  requireGmApproval: false,
  defaultConsumeMode: GIFT_CONSUME_MODES.CONSUME,
  defaultMaxQuantityPerGift: 1,
  defaultUnmatchedGiftMode: GIFT_UNMATCHED_GIFT_MODES.NEUTRAL,
  defaultUnmatchedGiftProgressDelta: 1,
  defaultPreferenceVisibility: GIFT_PREFERENCE_VISIBILITY.HIDDEN,
  defaultAllowMaxRankGifts: true,
  defaultRejectedConsumeMode: GIFT_REJECTED_CONSUME_MODES.KEEP,
  defaultReactionAudience: GIFT_REACTION_AUDIENCE.GIVER_AND_GM,
  defaultReactionDisplayMode: GIFT_REACTION_DISPLAY_MODES.AUTO
});

/** Default per-actor profile values (ported from prototype TWEAK_DEFAULTS). */
export const PROFILE_DEFAULTS = Object.freeze({
  title: "BOND",
  bondLabel: "BOND",
  bondLabelPlural: "BONDS",
  subtitle: "결속의 기록",
  lozenge: "B",
  archiveLabel: "ARCHIVE / SAVE 03",
  sessionLabel: "WK 12",
  calendarLabel: "火",
  showBgLetter: true,
  showNameRoman: true,
  fontScale: 1.0,
  maxRelationshipSlots: 10,
  mapVisibilityMode: MAP_VISIBILITY_MODES.EXPANDED,
  mapMaxDepth: 2,
  mapMaxNodes: 60,
  mapUseThumbnails: true,
  themeId: "archive"
});

/** Default world maximum rank. */
export const DEFAULT_MAX_RANK = 10;

/** Default steps (bond experience) required to advance one rank. */
export const DEFAULT_RANK_STEPS = 5;

/** Transient overlay moment types. */
export const MOMENT_TYPES = Object.freeze({
  RANK_UP: "rankup",
  RANK_DOWN: "rankdown",
  MAX: "max",
  UNLOCK: "unlock"
});
