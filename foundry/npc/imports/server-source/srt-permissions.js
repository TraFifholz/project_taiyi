import {
  GIFT_CONSUME_MODES,
  GIFT_PREFERENCE_VISIBILITY_VALUES,
  GIFT_PROFILE_DEFAULTS,
  GIFT_PROFILE_MODES,
  GIFT_PREFERENCE_VISIBILITY,
  GIFT_REACTION_AUDIENCE,
  GIFT_REACTION_DISPLAY_MODES,
  GIFT_REJECTED_CONSUME_MODES,
  GIFT_SETTINGS_DEFAULTS,
  GIFT_UNMATCHED_GIFT_MODES,
  MODULE_ID,
  PORTRAIT_PRESENTATIONS
} from "./constants.js";
import { canUnlockRelationshipWithGift, cloneStorageValue, getTargetActorGiftProfile, isEventRevealedAtRank, normalizeEvent, normalizeEventRankChangePatch, normalizeGiftProfile, normalizeRelationshipData } from "./data-model.js";
import { isNegativeRelationship } from "./relationship-polarity.js";

export const SETTING_ALLOW_PLAYER_EDIT = "allowPlayerEditOwnRelationships";
export const SETTING_ALLOW_OBSERVER_VIEW = "allowObserverViewRelationships";
export const SETTING_PLAYER_EDIT_MIN_ROLE = "playerEditMinimumRole";
export const SETTING_PLAYER_EDIT_MIN_PERMISSION = "playerEditMinimumPermission";
export const SETTING_PLAYER_EDIT_BASIC_FIELDS = "playerEditBasicFields";
export const SETTING_PLAYER_EDIT_TYPE_FIELDS = "playerEditTypeFields";
export const SETTING_PLAYER_EDIT_RANK_FIELDS = "playerEditRankFields";
export const SETTING_PLAYER_USE_RANK_CONTROLS = "playerUseRankControls";
export const SETTING_PLAYER_EDIT_APPEARANCE_FIELDS = "playerEditAppearanceFields";
export const SETTING_PLAYER_EDIT_STATS = "playerEditStats";
export const SETTING_PLAYER_EDIT_NOTES = "playerEditNotes";
export const SETTING_PLAYER_EDIT_EVENTS = "playerEditEvents";
export const SETTING_PLAYER_EDIT_STRUCTURE = "playerEditStructure";
export const SETTING_PLAYER_VIEW_PERMISSION = "playerViewPermission";
export const SETTING_PLAYER_EDIT_STRUCTURE_PERMISSION = "playerEditStructurePermission";
export const SETTING_PLAYER_EDIT_BASIC_PERMISSION = "playerEditBasicPermission";
export const SETTING_PLAYER_EDIT_TYPE_PERMISSION = "playerEditTypePermission";
export const SETTING_PLAYER_EDIT_RANK_PERMISSION = "playerEditRankPermission";
export const SETTING_PLAYER_RANK_CONTROLS_PERMISSION = "playerRankControlsPermission";
export const SETTING_PLAYER_EDIT_APPEARANCE_PERMISSION = "playerEditAppearancePermission";
export const SETTING_PLAYER_EDIT_STATS_PERMISSION = "playerEditStatsPermission";
export const SETTING_PLAYER_EDIT_NOTES_PERMISSION = "playerEditNotesPermission";
export const SETTING_PLAYER_EDIT_EVENTS_PERMISSION = "playerEditEventsPermission";
export const SETTING_PLAYER_PERMISSION_SCHEMA_VERSION = "playerPermissionSchemaVersion";
export const SETTING_SHOW_LOCKED_TO_PLAYERS = "showLockedRelationshipsToPlayers";
export const SETTING_ALLOW_PLAYER_GIVE_GIFTS = "allowPlayerGiveGifts";
export const SETTING_REQUIRE_GM_GIFT_APPROVAL = "requireGmGiftApproval";
export const SETTING_PENDING_GIFT_APPROVALS = "pendingGiftApprovals";
export const SETTING_GIFT_DEFAULT_CONSUME_MODE = "giftDefaultConsumeMode";
export const SETTING_GIFT_DEFAULT_MAX_QUANTITY_PER_GIFT = "giftDefaultMaxQuantityPerGift";
export const SETTING_GIFT_DEFAULT_UNMATCHED_MODE = "giftDefaultUnmatchedGiftMode";
export const SETTING_GIFT_DEFAULT_UNMATCHED_PROGRESS_DELTA = "giftDefaultUnmatchedGiftProgressDelta";
export const SETTING_GIFT_DEFAULT_PREFERENCE_VISIBILITY = "giftDefaultPreferenceVisibility";
export const SETTING_GIFT_DEFAULT_ALLOW_MAX_RANK_GIFTS = "giftDefaultAllowMaxRankGifts";
export const SETTING_GIFT_DEFAULT_REJECTED_CONSUME_MODE = "giftDefaultRejectedConsumeMode";
export const SETTING_GIFT_DEFAULT_REACTION_AUDIENCE = "giftDefaultReactionAudience";
export const SETTING_GIFT_DEFAULT_REACTION_DISPLAY_MODE = "giftDefaultReactionDisplayMode";

// A world default must resolve to a concrete policy. `worldDefault` is valid
// inside an individual profile, but would recursively refer back to itself in
// this setting.
const GIFT_CONSUME_MODE_SET = new Set([
  GIFT_CONSUME_MODES.CONSUME,
  GIFT_CONSUME_MODES.KEEP
]);
const GIFT_UNMATCHED_MODE_SET = new Set(Object.values(GIFT_UNMATCHED_GIFT_MODES));
const GIFT_PREFERENCE_VISIBILITY_SET = new Set(GIFT_PREFERENCE_VISIBILITY_VALUES);
const GIFT_REJECTED_CONSUME_MODE_SET = new Set(Object.values(GIFT_REJECTED_CONSUME_MODES));
const GIFT_REACTION_AUDIENCE_SET = new Set(Object.values(GIFT_REACTION_AUDIENCE));
const GIFT_REACTION_DISPLAY_MODE_SET = new Set(Object.values(GIFT_REACTION_DISPLAY_MODES));

export const PLAYER_EDIT_ROLES = Object.freeze({
  PLAYER: "PLAYER",
  TRUSTED: "TRUSTED",
  ASSISTANT: "ASSISTANT"
});

export const PLAYER_EDIT_PERMISSIONS = Object.freeze({
  OWNER: "OWNER",
  OBSERVER: "OBSERVER",
  LIMITED: "LIMITED"
});

/** Per-category threshold. `OFF` is not an ownership level: it removes the
 * category from every non-GM user regardless of Actor permission. */
export const PLAYER_CATEGORY_PERMISSIONS = Object.freeze({
  OWNER: "OWNER",
  OBSERVER: "OBSERVER",
  LIMITED: "LIMITED",
  OFF: "OFF"
});

export const PLAYER_PERMISSION_SCHEMA_VERSION = 1;

/** Defaults copied into newly-created Gift Profiles. Existing profiles remain
 * stable when a world setting changes. */
export function getWorldGiftProfileDefaults() {
  return {
    consumeMode: getStringSetting(
      SETTING_GIFT_DEFAULT_CONSUME_MODE,
      GIFT_SETTINGS_DEFAULTS.defaultConsumeMode,
      GIFT_CONSUME_MODE_SET
    ),
    maxQuantityPerGift: getPositiveIntegerSetting(
      SETTING_GIFT_DEFAULT_MAX_QUANTITY_PER_GIFT,
      GIFT_SETTINGS_DEFAULTS.defaultMaxQuantityPerGift,
      999
    ),
    allowMaxRankGifts: getBooleanSetting(
      SETTING_GIFT_DEFAULT_ALLOW_MAX_RANK_GIFTS,
      GIFT_SETTINGS_DEFAULTS.defaultAllowMaxRankGifts
    ),
    preferenceVisibility: getStringSetting(
      SETTING_GIFT_DEFAULT_PREFERENCE_VISIBILITY,
      GIFT_SETTINGS_DEFAULTS.defaultPreferenceVisibility,
      GIFT_PREFERENCE_VISIBILITY_SET
    ),
    reactionAudience: getStringSetting(
      SETTING_GIFT_DEFAULT_REACTION_AUDIENCE,
      GIFT_SETTINGS_DEFAULTS.defaultReactionAudience,
      GIFT_REACTION_AUDIENCE_SET
    ),
    reactionDisplayMode: getStringSetting(
      SETTING_GIFT_DEFAULT_REACTION_DISPLAY_MODE,
      GIFT_SETTINGS_DEFAULTS.defaultReactionDisplayMode,
      GIFT_REACTION_DISPLAY_MODE_SET
    ),
    unmatchedGift: {
      ...GIFT_PROFILE_DEFAULTS.unmatchedGift,
      mode: getStringSetting(
        SETTING_GIFT_DEFAULT_UNMATCHED_MODE,
        GIFT_SETTINGS_DEFAULTS.defaultUnmatchedGiftMode,
        GIFT_UNMATCHED_MODE_SET
      ),
      progressDelta: getNonNegativeIntegerSetting(
        SETTING_GIFT_DEFAULT_UNMATCHED_PROGRESS_DELTA,
        GIFT_SETTINGS_DEFAULTS.defaultUnmatchedGiftProgressDelta,
        99
      )
    },
    rejectedConsumeMode: getStringSetting(
      SETTING_GIFT_DEFAULT_REJECTED_CONSUME_MODE,
      GIFT_SETTINGS_DEFAULTS.defaultRejectedConsumeMode,
      GIFT_REJECTED_CONSUME_MODE_SET
    )
  };
}

export function createWorldDefaultGiftProfile() {
  return normalizeGiftProfile(getWorldGiftProfileDefaults());
}

const FALLBACK_USER_ROLE_VALUES = Object.freeze({
  NONE: 0,
  PLAYER: 1,
  TRUSTED: 2,
  ASSISTANT: 3,
  GAMEMASTER: 4
});

const PLAYER_EDIT_ROLE_VALUES = new Set(Object.values(PLAYER_EDIT_ROLES));
const PLAYER_EDIT_PERMISSION_VALUES = new Set(Object.values(PLAYER_EDIT_PERMISSIONS));

export const PLAYER_EDIT_FIELD_DEFAULTS = Object.freeze({
  structure: false,
  basic: true,
  type: false,
  rank: false,
  rankControls: true,
  appearance: true,
  stats: false,
  notes: true,
  events: true
});

const PLAYER_CATEGORY_PERMISSION_VALUES = new Set(Object.values(PLAYER_CATEGORY_PERMISSIONS));

// Read-only viewing cannot be switched off here: an Actor's owner always sees
// their own records, so `OFF` would describe a state this setting cannot reach.
const PLAYER_VIEW_PERMISSION_VALUES = new Set([
  PLAYER_CATEGORY_PERMISSIONS.OWNER,
  PLAYER_CATEGORY_PERMISSIONS.OBSERVER,
  PLAYER_CATEGORY_PERMISSIONS.LIMITED
]);

/** The single source of truth for the editable categories: the world Setting
 * that carries each threshold, and the fallback used when the stored value is
 * absent or not one of the allowed values. Insertion order is the order
 * `getPlayerEditFieldPermissions` reports. */
const PLAYER_EDIT_CATEGORY_SETTINGS = Object.freeze({
  structure: Object.freeze({
    key: SETTING_PLAYER_EDIT_STRUCTURE_PERMISSION,
    fallback: PLAYER_CATEGORY_PERMISSIONS.OFF
  }),
  basic: Object.freeze({
    key: SETTING_PLAYER_EDIT_BASIC_PERMISSION,
    fallback: PLAYER_CATEGORY_PERMISSIONS.OWNER
  }),
  type: Object.freeze({
    key: SETTING_PLAYER_EDIT_TYPE_PERMISSION,
    fallback: PLAYER_CATEGORY_PERMISSIONS.OFF
  }),
  rank: Object.freeze({
    key: SETTING_PLAYER_EDIT_RANK_PERMISSION,
    fallback: PLAYER_CATEGORY_PERMISSIONS.OFF
  }),
  rankControls: Object.freeze({
    key: SETTING_PLAYER_RANK_CONTROLS_PERMISSION,
    fallback: PLAYER_CATEGORY_PERMISSIONS.OWNER
  }),
  appearance: Object.freeze({
    key: SETTING_PLAYER_EDIT_APPEARANCE_PERMISSION,
    fallback: PLAYER_CATEGORY_PERMISSIONS.OWNER
  }),
  stats: Object.freeze({
    key: SETTING_PLAYER_EDIT_STATS_PERMISSION,
    fallback: PLAYER_CATEGORY_PERMISSIONS.OFF
  }),
  notes: Object.freeze({
    key: SETTING_PLAYER_EDIT_NOTES_PERMISSION,
    fallback: PLAYER_CATEGORY_PERMISSIONS.OWNER
  }),
  events: Object.freeze({
    key: SETTING_PLAYER_EDIT_EVENTS_PERMISSION,
    fallback: PLAYER_CATEGORY_PERMISSIONS.OWNER
  })
});

const PLAYER_EDIT_CATEGORY_NAMES = Object.freeze(Object.keys(PLAYER_EDIT_CATEGORY_SETTINGS));

const PERMISSION_CHOICE_ROOT = "STYLISH_RELATIONSHIP_TRACKER.settings.editPermissionChoices";

const PLAYER_VIEW_PERMISSION_CHOICES = Object.freeze({
  [PLAYER_CATEGORY_PERMISSIONS.OWNER]: `${PERMISSION_CHOICE_ROOT}.owner`,
  [PLAYER_CATEGORY_PERMISSIONS.OBSERVER]: `${PERMISSION_CHOICE_ROOT}.observer`,
  [PLAYER_CATEGORY_PERMISSIONS.LIMITED]: `${PERMISSION_CHOICE_ROOT}.limited`
});

const PLAYER_CATEGORY_PERMISSION_CHOICES = Object.freeze({
  ...PLAYER_VIEW_PERMISSION_CHOICES,
  [PLAYER_CATEGORY_PERMISSIONS.OFF]: `${PERMISSION_CHOICE_ROOT}.off`
});

const PLAYER_BASIC_FIELDS = new Set([
  "customName",
  "customRole",
  "nameRoman",
  "bio"
]);

const PLAYER_TYPE_FIELDS = new Set([
  "classId",
  "categoryId",
  "categoryLabel",
  "categoryLabelEn"
]);

const PLAYER_RANK_FIELDS = new Set([
  "polarity",
  "rank",
  "maxRank",
  "rankSteps",
  "rankProgress"
]);

const PLAYER_APPEARANCE_FIELDS = new Set([
  "accent",
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
  "rankCutinOffsetY"
]);

const PLAYER_STATS_FIELDS = new Set(["stats"]);
const PLAYER_STAT_CARD_LIMIT = 3;

const PLAYER_NOTES_FIELDS = new Set(["notes"]);

const PLAYER_EVENT_FIELDS = new Set([
  "day",
  "text",
  "rankLabel",
  "quote",
  "recollection",
  "image",
  "imageScale",
  "imageOffsetX",
  "imageOffsetY",
  "rankChange",
  "isRankUp"
]);

const PLAYER_RELATIONSHIP_TARGET_FIELDS = Object.freeze([
  "entryType",
  "targetUuid"
]);

export function registerPermissionSettings() {
  if (typeof game === "undefined" || typeof game.settings?.register !== "function") return;

  game.settings.register(MODULE_ID, SETTING_ALLOW_OBSERVER_VIEW, {
    name: "STYLISH_RELATIONSHIP_TRACKER.settings.allowObserverView.name",
    hint: "STYLISH_RELATIONSHIP_TRACKER.settings.allowObserverView.hint",
    scope: "world",
    config: false,
    type: Boolean,
    default: false
  });

  game.settings.register(MODULE_ID, SETTING_ALLOW_PLAYER_EDIT, {
    name: "STYLISH_RELATIONSHIP_TRACKER.settings.allowPlayerEdit.name",
    hint: "STYLISH_RELATIONSHIP_TRACKER.settings.allowPlayerEdit.hint",
    scope: "world",
    config: false,
    type: Boolean,
    default: false
  });

  game.settings.register(MODULE_ID, SETTING_PLAYER_EDIT_MIN_ROLE, {
    name: "STYLISH_RELATIONSHIP_TRACKER.settings.playerEditMinimumRole.name",
    hint: "STYLISH_RELATIONSHIP_TRACKER.settings.playerEditMinimumRole.hint",
    scope: "world",
    config: false,
    type: String,
    choices: {
      [PLAYER_EDIT_ROLES.PLAYER]: "STYLISH_RELATIONSHIP_TRACKER.settings.playerEditMinimumRole.choices.player",
      [PLAYER_EDIT_ROLES.TRUSTED]: "STYLISH_RELATIONSHIP_TRACKER.settings.playerEditMinimumRole.choices.trusted",
      [PLAYER_EDIT_ROLES.ASSISTANT]: "STYLISH_RELATIONSHIP_TRACKER.settings.playerEditMinimumRole.choices.assistant"
    },
    default: PLAYER_EDIT_ROLES.TRUSTED
  });

  game.settings.register(MODULE_ID, SETTING_PLAYER_EDIT_MIN_PERMISSION, {
    name: "STYLISH_RELATIONSHIP_TRACKER.settings.playerEditMinimumPermission.name",
    hint: "STYLISH_RELATIONSHIP_TRACKER.settings.playerEditMinimumPermission.hint",
    scope: "world",
    config: false,
    type: String,
    choices: {
      [PLAYER_EDIT_PERMISSIONS.OWNER]: "STYLISH_RELATIONSHIP_TRACKER.settings.playerEditMinimumPermission.choices.owner",
      [PLAYER_EDIT_PERMISSIONS.OBSERVER]: "STYLISH_RELATIONSHIP_TRACKER.settings.playerEditMinimumPermission.choices.observer",
      [PLAYER_EDIT_PERMISSIONS.LIMITED]: "STYLISH_RELATIONSHIP_TRACKER.settings.playerEditMinimumPermission.choices.limited"
    },
    default: PLAYER_EDIT_PERMISSIONS.OWNER
  });

  registerPlayerEditFieldSetting(SETTING_PLAYER_EDIT_BASIC_FIELDS, "playerEditBasic", PLAYER_EDIT_FIELD_DEFAULTS.basic);
  registerPlayerEditFieldSetting(SETTING_PLAYER_EDIT_TYPE_FIELDS, "playerEditType", PLAYER_EDIT_FIELD_DEFAULTS.type);
  registerPlayerEditFieldSetting(SETTING_PLAYER_EDIT_RANK_FIELDS, "playerEditRank", PLAYER_EDIT_FIELD_DEFAULTS.rank);
  registerPlayerEditFieldSetting(SETTING_PLAYER_USE_RANK_CONTROLS, "playerUseRankControls", PLAYER_EDIT_FIELD_DEFAULTS.rankControls);
  registerPlayerEditFieldSetting(SETTING_PLAYER_EDIT_APPEARANCE_FIELDS, "playerEditAppearance", PLAYER_EDIT_FIELD_DEFAULTS.appearance);
  registerPlayerEditFieldSetting(SETTING_PLAYER_EDIT_STATS, "playerEditStats", PLAYER_EDIT_FIELD_DEFAULTS.stats);
  registerPlayerEditFieldSetting(SETTING_PLAYER_EDIT_NOTES, "playerEditNotes", PLAYER_EDIT_FIELD_DEFAULTS.notes);
  registerPlayerEditFieldSetting(SETTING_PLAYER_EDIT_EVENTS, "playerEditEvents", PLAYER_EDIT_FIELD_DEFAULTS.events);
  registerPlayerEditFieldSetting(SETTING_PLAYER_EDIT_STRUCTURE, "playerEditStructure", PLAYER_EDIT_FIELD_DEFAULTS.structure);

  // The legacy switches above stay registered so the one-time migration can
  // still read a world that has not been converted yet.
  game.settings.register(MODULE_ID, SETTING_PLAYER_VIEW_PERMISSION, {
    name: `STYLISH_RELATIONSHIP_TRACKER.settings.${SETTING_PLAYER_VIEW_PERMISSION}.name`,
    hint: `STYLISH_RELATIONSHIP_TRACKER.settings.${SETTING_PLAYER_VIEW_PERMISSION}.hint`,
    scope: "world",
    config: false,
    type: String,
    choices: { ...PLAYER_VIEW_PERMISSION_CHOICES },
    default: PLAYER_CATEGORY_PERMISSIONS.OWNER
  });

  for (const { key, fallback } of Object.values(PLAYER_EDIT_CATEGORY_SETTINGS)) {
    registerPlayerCategoryPermissionSetting(key, fallback);
  }

  // Internal migration cursor. `config: false` hides only the UI, so this must
  // stay a bare version number.
  game.settings.register(MODULE_ID, SETTING_PLAYER_PERMISSION_SCHEMA_VERSION, {
    scope: "world",
    config: false,
    type: Number,
    default: 0
  });

  game.settings.register(MODULE_ID, SETTING_SHOW_LOCKED_TO_PLAYERS, {
    name: "STYLISH_RELATIONSHIP_TRACKER.settings.showLocked.name",
    hint: "STYLISH_RELATIONSHIP_TRACKER.settings.showLocked.hint",
    scope: "world",
    config: false,
    type: Boolean,
    default: false
  });

  game.settings.register(MODULE_ID, SETTING_ALLOW_PLAYER_GIVE_GIFTS, {
    name: "STYLISH_RELATIONSHIP_TRACKER.settings.allowPlayerGiveGifts.name",
    hint: "STYLISH_RELATIONSHIP_TRACKER.settings.allowPlayerGiveGifts.hint",
    scope: "world",
    config: false,
    type: Boolean,
    default: GIFT_SETTINGS_DEFAULTS.allowPlayerGiveGifts
  });

  game.settings.register(MODULE_ID, SETTING_REQUIRE_GM_GIFT_APPROVAL, {
    name: "STYLISH_RELATIONSHIP_TRACKER.settings.requireGmGiftApproval.name",
    hint: "STYLISH_RELATIONSHIP_TRACKER.settings.requireGmGiftApproval.hint",
    scope: "world",
    config: false,
    type: Boolean,
    default: GIFT_SETTINGS_DEFAULTS.requireGmApproval
  });

  // Internal active-GM handoff identity. `config: false` hides only the UI, so
  // this Setting must never contain names, images, rank, or free-text details.
  game.settings.register(MODULE_ID, SETTING_PENDING_GIFT_APPROVALS, {
    scope: "world",
    config: false,
    type: Object,
    default: { version: 1, requests: [] }
  });

  game.settings.register(MODULE_ID, SETTING_GIFT_DEFAULT_CONSUME_MODE, {
    name: "STYLISH_RELATIONSHIP_TRACKER.settings.giftDefaultConsumeMode.name",
    hint: "STYLISH_RELATIONSHIP_TRACKER.settings.giftDefaultConsumeMode.hint",
    scope: "world",
    config: false,
    type: String,
    choices: {
      [GIFT_CONSUME_MODES.CONSUME]: "STYLISH_RELATIONSHIP_TRACKER.settings.giftDefaultConsumeMode.choices.consume",
      [GIFT_CONSUME_MODES.KEEP]: "STYLISH_RELATIONSHIP_TRACKER.settings.giftDefaultConsumeMode.choices.keep"
    },
    default: GIFT_SETTINGS_DEFAULTS.defaultConsumeMode
  });

  game.settings.register(MODULE_ID, SETTING_GIFT_DEFAULT_MAX_QUANTITY_PER_GIFT, {
    name: "STYLISH_RELATIONSHIP_TRACKER.settings.giftDefaultMaxQuantityPerGift.name",
    hint: "STYLISH_RELATIONSHIP_TRACKER.settings.giftDefaultMaxQuantityPerGift.hint",
    scope: "world",
    config: false,
    type: Number,
    default: GIFT_SETTINGS_DEFAULTS.defaultMaxQuantityPerGift
  });

  game.settings.register(MODULE_ID, SETTING_GIFT_DEFAULT_UNMATCHED_MODE, {
    name: "STYLISH_RELATIONSHIP_TRACKER.settings.giftDefaultUnmatchedGiftMode.name",
    hint: "STYLISH_RELATIONSHIP_TRACKER.settings.giftDefaultUnmatchedGiftMode.hint",
    scope: "world",
    config: false,
    type: String,
    choices: {
      [GIFT_UNMATCHED_GIFT_MODES.NEUTRAL]: "STYLISH_RELATIONSHIP_TRACKER.settings.giftDefaultUnmatchedGiftMode.choices.neutral",
      [GIFT_UNMATCHED_GIFT_MODES.BLOCK]: "STYLISH_RELATIONSHIP_TRACKER.settings.giftDefaultUnmatchedGiftMode.choices.block"
    },
    default: GIFT_SETTINGS_DEFAULTS.defaultUnmatchedGiftMode
  });

  game.settings.register(MODULE_ID, SETTING_GIFT_DEFAULT_UNMATCHED_PROGRESS_DELTA, {
    name: "STYLISH_RELATIONSHIP_TRACKER.settings.giftDefaultUnmatchedGiftProgressDelta.name",
    hint: "STYLISH_RELATIONSHIP_TRACKER.settings.giftDefaultUnmatchedGiftProgressDelta.hint",
    scope: "world",
    config: false,
    type: Number,
    default: GIFT_SETTINGS_DEFAULTS.defaultUnmatchedGiftProgressDelta
  });

  game.settings.register(MODULE_ID, SETTING_GIFT_DEFAULT_PREFERENCE_VISIBILITY, {
    name: "STYLISH_RELATIONSHIP_TRACKER.settings.giftDefaultPreferenceVisibility.name",
    hint: "STYLISH_RELATIONSHIP_TRACKER.settings.giftDefaultPreferenceVisibility.hint",
    scope: "world",
    config: false,
    type: String,
    choices: {
      [GIFT_PREFERENCE_VISIBILITY.HIDDEN]: "STYLISH_RELATIONSHIP_TRACKER.settings.giftDefaultPreferenceVisibility.choices.hidden",
      [GIFT_PREFERENCE_VISIBILITY.HINT]: "STYLISH_RELATIONSHIP_TRACKER.settings.giftDefaultPreferenceVisibility.choices.hint",
      [GIFT_PREFERENCE_VISIBILITY.FULL]: "STYLISH_RELATIONSHIP_TRACKER.settings.giftDefaultPreferenceVisibility.choices.full"
    },
    default: GIFT_SETTINGS_DEFAULTS.defaultPreferenceVisibility
  });

  game.settings.register(MODULE_ID, SETTING_GIFT_DEFAULT_ALLOW_MAX_RANK_GIFTS, {
    name: "STYLISH_RELATIONSHIP_TRACKER.settings.giftDefaultAllowMaxRankGifts.name",
    hint: "STYLISH_RELATIONSHIP_TRACKER.settings.giftDefaultAllowMaxRankGifts.hint",
    scope: "world",
    config: false,
    type: Boolean,
    default: GIFT_SETTINGS_DEFAULTS.defaultAllowMaxRankGifts
  });

  game.settings.register(MODULE_ID, SETTING_GIFT_DEFAULT_REJECTED_CONSUME_MODE, {
    name: "STYLISH_RELATIONSHIP_TRACKER.settings.giftDefaultRejectedConsumeMode.name",
    hint: "STYLISH_RELATIONSHIP_TRACKER.settings.giftDefaultRejectedConsumeMode.hint",
    scope: "world",
    config: false,
    type: String,
    choices: {
      [GIFT_REJECTED_CONSUME_MODES.KEEP]: "STYLISH_RELATIONSHIP_TRACKER.settings.giftDefaultRejectedConsumeMode.choices.keep",
      [GIFT_REJECTED_CONSUME_MODES.CONSUME]: "STYLISH_RELATIONSHIP_TRACKER.settings.giftDefaultRejectedConsumeMode.choices.consume"
    },
    default: GIFT_SETTINGS_DEFAULTS.defaultRejectedConsumeMode
  });

  game.settings.register(MODULE_ID, SETTING_GIFT_DEFAULT_REACTION_AUDIENCE, {
    name: "STYLISH_RELATIONSHIP_TRACKER.settings.giftDefaultReactionAudience.name",
    hint: "STYLISH_RELATIONSHIP_TRACKER.settings.giftDefaultReactionAudience.hint",
    scope: "world",
    config: false,
    type: String,
    choices: {
      [GIFT_REACTION_AUDIENCE.GIVER_ONLY]: "STYLISH_RELATIONSHIP_TRACKER.settings.giftDefaultReactionAudience.choices.giverOnly",
      [GIFT_REACTION_AUDIENCE.GIVER_AND_GM]: "STYLISH_RELATIONSHIP_TRACKER.settings.giftDefaultReactionAudience.choices.giverAndGm",
      [GIFT_REACTION_AUDIENCE.ELIGIBLE_VIEWERS]: "STYLISH_RELATIONSHIP_TRACKER.settings.giftDefaultReactionAudience.choices.eligibleViewers"
    },
    default: GIFT_SETTINGS_DEFAULTS.defaultReactionAudience
  });

  game.settings.register(MODULE_ID, SETTING_GIFT_DEFAULT_REACTION_DISPLAY_MODE, {
    name: "STYLISH_RELATIONSHIP_TRACKER.settings.giftDefaultReactionDisplayMode.name",
    hint: "STYLISH_RELATIONSHIP_TRACKER.settings.giftDefaultReactionDisplayMode.hint",
    scope: "world",
    config: false,
    type: String,
    choices: {
      [GIFT_REACTION_DISPLAY_MODES.AUTO]: "STYLISH_RELATIONSHIP_TRACKER.settings.giftDefaultReactionDisplayMode.choices.auto",
      [GIFT_REACTION_DISPLAY_MODES.DIALOG]: "STYLISH_RELATIONSHIP_TRACKER.settings.giftDefaultReactionDisplayMode.choices.dialog",
      [GIFT_REACTION_DISPLAY_MODES.CUTIN]: "STYLISH_RELATIONSHIP_TRACKER.settings.giftDefaultReactionDisplayMode.choices.cutin"
    },
    default: GIFT_SETTINGS_DEFAULTS.defaultReactionDisplayMode
  });
}

/**
 * Project one legacy permission configuration onto the per-category model.
 *
 * Pure and total: the same input always yields the same complete set of new
 * values, which is what makes the migration safe to run from more than one
 * client. The mapping is lossless — a category the legacy world allowed keeps
 * the legacy threshold, and one it forbade becomes `OFF`.
 */
export function buildMigratedPlayerPermissionValues(legacy) {
  const source = isPlainObject(legacy) ? legacy : {};
  const minimum = PLAYER_EDIT_PERMISSION_VALUES.has(source.minimumPermission)
    ? source.minimumPermission
    : PLAYER_EDIT_PERMISSIONS.OWNER;

  const values = {
    [SETTING_PLAYER_VIEW_PERMISSION]: source.allowObserverView === true
      ? PLAYER_CATEGORY_PERMISSIONS.OBSERVER
      : PLAYER_CATEGORY_PERMISSIONS.OWNER
  };
  for (const [category, descriptor] of Object.entries(PLAYER_EDIT_CATEGORY_SETTINGS)) {
    values[descriptor.key] = source[category] === true ? minimum : PLAYER_CATEGORY_PERMISSIONS.OFF;
  }
  return values;
}

/**
 * Convert a world once, then record the schema version so later loads skip it.
 * The caller must be the active GM, because these are world-scope writes.
 *
 * A partial run intentionally leaves the version at 0: every write is a plain
 * overwrite with a deterministic value, so a retry on the next load converges
 * on the same result, and two GMs converting concurrently write the same values.
 *
 * Writing the values first and the cursor last is therefore load-bearing. While
 * the cursor is 0 the runtime keeps answering from the legacy Settings, so a
 * partial run leaves the enforced policy exactly where it was.
 */
export async function runPlayerPermissionSettingsMigration() {
  if (typeof game === "undefined") return false;
  if (typeof game.settings?.get !== "function" || typeof game.settings?.set !== "function") return false;
  if (getPlayerPermissionSchemaVersion() >= PLAYER_PERMISSION_SCHEMA_VERSION) return false;

  const values = buildMigratedPlayerPermissionValues(readLegacyPlayerPermissionValues());
  try {
    for (const [key, value] of Object.entries(values)) {
      await game.settings.set(MODULE_ID, key, value);
    }
    await game.settings.set(
      MODULE_ID,
      SETTING_PLAYER_PERMISSION_SCHEMA_VERSION,
      PLAYER_PERMISSION_SCHEMA_VERSION
    );
    return true;
  } catch (error) {
    console.warn(`${MODULE_ID} | Player permission migration did not complete`, error);
    return false;
  }
}

function readLegacyPlayerPermissionValues() {
  return {
    allowObserverView: getBooleanSetting(SETTING_ALLOW_OBSERVER_VIEW, false),
    minimumPermission: getPlayerEditMinimumPermission(),
    structure: getBooleanSetting(SETTING_PLAYER_EDIT_STRUCTURE, PLAYER_EDIT_FIELD_DEFAULTS.structure),
    basic: getBooleanSetting(SETTING_PLAYER_EDIT_BASIC_FIELDS, PLAYER_EDIT_FIELD_DEFAULTS.basic),
    type: getBooleanSetting(SETTING_PLAYER_EDIT_TYPE_FIELDS, PLAYER_EDIT_FIELD_DEFAULTS.type),
    rank: getBooleanSetting(SETTING_PLAYER_EDIT_RANK_FIELDS, PLAYER_EDIT_FIELD_DEFAULTS.rank),
    rankControls: getBooleanSetting(SETTING_PLAYER_USE_RANK_CONTROLS, PLAYER_EDIT_FIELD_DEFAULTS.rankControls),
    appearance: getBooleanSetting(SETTING_PLAYER_EDIT_APPEARANCE_FIELDS, PLAYER_EDIT_FIELD_DEFAULTS.appearance),
    stats: getBooleanSetting(SETTING_PLAYER_EDIT_STATS, PLAYER_EDIT_FIELD_DEFAULTS.stats),
    notes: getBooleanSetting(SETTING_PLAYER_EDIT_NOTES, PLAYER_EDIT_FIELD_DEFAULTS.notes),
    events: getBooleanSetting(SETTING_PLAYER_EDIT_EVENTS, PLAYER_EDIT_FIELD_DEFAULTS.events)
  };
}

function getPlayerPermissionSchemaVersion() {
  if (typeof game === "undefined" || typeof game.settings?.get !== "function") return 0;
  try {
    const value = Number(game.settings.get(MODULE_ID, SETTING_PLAYER_PERMISSION_SCHEMA_VERSION));
    return Number.isFinite(value) ? value : 0;
  } catch (_error) {
    return 0;
  }
}

export function canViewRelationships(user = currentUser(), ownerActor) {
  if (!ownerActor) return false;
  if (user?.isGM === true) return true;
  return hasOwnerPermission(ownerActor, user)
    || hasPlayerViewAccess(user, ownerActor)
    || canEditRelationships(user, ownerActor);
}

/** Granted when at least one edit category resolves for this owner Actor. */
export function canEditRelationships(user = currentUser(), ownerActor) {
  if (!ownerActor) return false;
  if (user?.isGM === true) return true;
  return hasAnyPlayerEditCategory(user, ownerActor);
}

/**
 * Whether a user may use an Actor as a relationship reference target.
 *
 * This is intentionally independent from the world-wide relationship editing
 * threshold. A player who may already edit the owner Actor can reference any
 * target Actor they can identify, even when the owner's edit threshold itself
 * is configured as OWNER.
 *
 * LIMITED is the floor because Foundry already treats that level as "this
 * Actor's identity is known to you". The relationship only stores the target
 * UUID, so linking never exposes anything the LIMITED sheet keeps hidden.
 */
export function canReferenceRelationshipTarget(user = currentUser(), targetActor) {
  if (!targetActor) return false;
  if (user?.isGM === true) return true;
  return hasActorPermission(targetActor, user, PLAYER_EDIT_PERMISSIONS.LIMITED);
}

export function canManageRelationship(user = currentUser(), ownerActor, relationship) {
  if (!relationship) return false;
  if (user?.isGM === true) return true;
  return canEditRelationships(user, ownerActor)
    && canSeeRelationship(user, ownerActor, relationship)
    && relationship.locked !== true
    && relationship.playerEditable !== false;
}

/**
 * Return the field categories a user may edit on one owner Actor. GMs always
 * receive the complete policy; non-GM writes are checked against the same
 * policy again by the authoritative socket handler.
 *
 * `ownerActor` is required to resolve a non-GM: every category threshold is
 * measured against that Actor's ownership. A caller that cannot name the owner
 * therefore receives no categories at all rather than a world-wide guess.
 */
export function getPlayerEditFieldPermissions(user = currentUser(), ownerActor = null) {
  if (user?.isGM === true) return buildCategoryPermissions(() => true);
  const resolve = playerCategoryResolver(user, ownerActor);
  return buildCategoryPermissions(resolve ?? (() => false));
}

/**
 * Structural relationship changes are intentionally separate from field
 * editing. A player who may maintain Notes or Event Logs on an established
 * relationship must not automatically gain create/delete or target-linking
 * privileges.
 */
export function canManageRelationshipStructure(user = currentUser(), ownerActor, relationship = null) {
  if (!ownerActor) return false;
  if (user?.isGM === true) return relationship ? canManageRelationship(user, ownerActor, relationship) : true;
  if (relationship?.entryType === "organization") return false;
  if (!hasPlayerEditCategory(user, ownerActor, "structure")) return false;
  return relationship
    ? canManageRelationship(user, ownerActor, relationship)
    : canEditRelationships(user, ownerActor);
}

export function canEditRelationshipEvents(user = currentUser(), ownerActor, relationship) {
  return canManageRelationship(user, ownerActor, relationship)
    && hasPlayerEditCategory(user, ownerActor, "events");
}

export function canUsePlayerRankControls(user = currentUser(), ownerActor, relationship) {
  return canManageRelationship(user, ownerActor, relationship)
    && hasPlayerEditCategory(user, ownerActor, "rankControls");
}

export function canGiveGift(user = currentUser(), ownerActor, relationship, giverActor = ownerActor) {
  if (!ownerActor || !relationship || !giverActor) return false;
  if (relationship.entryType === "organization") return false;
  const unlocksWithGift = canUnlockRelationshipWithGift(relationship);
  if (relationship.locked === true && !unlocksWithGift) return false;
  if (user?.isGM === true) return true;
  if (unlocksWithGift && !getBooleanSetting(SETTING_SHOW_LOCKED_TO_PLAYERS, false)) return false;
  return isPlayerGiftEnabled()
    && (hasOwnerPermission(ownerActor, user) || canEditRelationships(user, ownerActor))
    && canSeeRelationship(user, ownerActor, relationship)
    && hasOwnerPermission(giverActor, user);
}

/** Whether this player's otherwise-valid Gift must be approved by the active GM. */
export function requiresGmGiftApproval(user = currentUser()) {
  if (!user || user.isGM === true) return false;
  return getBooleanSetting(SETTING_REQUIRE_GM_GIFT_APPROVAL, GIFT_SETTINGS_DEFAULTS.requireGmApproval);
}

export function canSeeRelationship(user = currentUser(), ownerActor, relationship) {
  if (!relationship || !canViewRelationships(user, ownerActor)) return false;
  if (user?.isGM === true) return true;

  switch (relationship.visibility) {
    case "gm":
      return false;
    case "owner":
      return hasOwnerPermission(ownerActor, user);
    case "players":
    default:
      return canViewRelationships(user, ownerActor);
  }
}

export function sanitizeRelationshipDataForUser(user = currentUser(), ownerActor, data) {
  const normalized = normalizeRelationshipData(data, ownerActor);
  if (user?.isGM === true) return normalized;
  if (!canViewRelationships(user, ownerActor)) {
    return { ...normalized, relationships: [] };
  }

  const relationships = normalized.relationships
    .map((relationship) => sanitizeRelationshipForUser(user, ownerActor, relationship))
    .filter(Boolean);

  return { ...normalized, relationships };
}

export function sanitizeRelationshipForUser(user = currentUser(), ownerActor, relationship) {
  if (!canSeeRelationship(user, ownerActor, relationship)) return null;
  if (user?.isGM === true) return cloneStorageValue(relationship);

  if (relationship.locked === true) {
    if (!getBooleanSetting(SETTING_SHOW_LOCKED_TO_PLAYERS, false)) return null;
    return {
      id: relationship.id,
      entryType: "custom",
      targetUuid: "",
      customName: "",
      customRole: "",
      portrait: "",
      listImage: "",
      portraitPresentation: PORTRAIT_PRESENTATIONS.CUTOUT,
      rankCutinRankUpImage: "",
      rankCutinMaxImage: "",
      rankCutinRankDownImage: "",
      rankCutinUnlockImage: "",
      mapThumbnail: "",
      mapThumbnailScale: 1,
      mapThumbnailOffset: { x: 0, y: 0 },
      mapInspectorImage: "",
      mapInspectorScale: 1,
      mapInspectorOffset: { x: 0, y: 0 },
      portraitTag: "NO IMAGE",
      portraitScale: 1,
      portraitOffset: { x: 0, y: 0 },
      rankCutinScale: 1,
      rankCutinOffsetX: 0,
      rankCutinOffsetY: 0,
      nameRoman: "",
      classId: relationship.classId,
      categoryId: relationship.categoryId,
      categoryLabel: relationship.categoryLabel,
      categoryLabelEn: relationship.categoryLabelEn,
      rank: 0,
      maxRank: relationship.maxRank || 1,
      accent: relationship.accent,
      bio: "",
      notes: [],
      locked: true,
      firstGiftUnlockAvailable: relationship.unlockOnGift === true,
      unlockRule: null,
      visibility: relationship.visibility,
      playerEditable: false,
      stats: [],
      events: [],
      isRedacted: true
    };
  }

  const clean = cloneStorageValue(relationship);
  clean.notes = playerVisibleNotes(clean.notes);
  clean.events = playerVisibleEvents(clean.events, isNegativeRelationship(clean) ? 0 : clean.rank);
  clean.giftProfilePolicy = buildPlayerGiftProfilePolicy(relationship);
  delete clean.giftProfile;
  delete clean.unlockOnGift;
  delete clean.firstGiftUnlockAvailable;
  delete clean.rankMacroTriggers;
  delete clean.externalProgressCredits;
  clean.unlockRule = null;
  return clean;
}

function buildPlayerGiftProfilePolicy(relationship) {
  if (relationship?.giftProfileMode === GIFT_PROFILE_MODES.DISABLED) return projectGiftProfilePolicy(null, false);
  const profile = resolvePlayerGiftProfile(relationship);
  return profile ? projectGiftProfilePolicy(profile, true) : null;
}

function resolvePlayerGiftProfile(relationship) {
  if (!relationship || typeof relationship !== "object") return null;
  if (relationship.entryType === "actor" && relationship.giftProfileMode === GIFT_PROFILE_MODES.TARGET_ACTOR) {
    const actor = resolveActorFromCollection(relationship.targetUuid);
    return actor ? getTargetActorGiftProfile(actor) : null;
  }
  return isPlainObject(relationship.giftProfile) ? relationship.giftProfile : null;
}

function projectGiftProfilePolicy(profile, modeEnabled) {
  const source = isPlainObject(profile) ? profile : {};
  return {
    enabled: modeEnabled === true && source.enabled !== false,
    maxQuantityPerGift: positiveInteger(source.maxQuantityPerGift, GIFT_PROFILE_DEFAULTS.maxQuantityPerGift, 999),
    allowMaxRankGifts: typeof source.allowMaxRankGifts === "boolean"
      ? source.allowMaxRankGifts
      : GIFT_PROFILE_DEFAULTS.allowMaxRankGifts,
    preferenceVisibility: GIFT_PREFERENCE_VISIBILITY_VALUES.includes(source.preferenceVisibility)
      ? source.preferenceVisibility
      : GIFT_PROFILE_DEFAULTS.preferenceVisibility
  };
}

function resolveActorFromCollection(actorUuid) {
  const uuid = typeof actorUuid === "string" ? actorUuid : "";
  if (!uuid) return null;
  const actorId = uuid.split(".").at(-1);
  const actors = globalThis.game?.actors;
  if (typeof actors?.get === "function") return actors.get(actorId) ?? actors.get(uuid) ?? null;
  if (typeof actors?.values === "function") {
    return Array.from(actors.values()).find((actor) => actor?.uuid === uuid || actor?.id === actorId) ?? null;
  }
  if (Array.isArray(actors)) return actors.find((actor) => actor?.uuid === uuid || actor?.id === actorId) ?? null;
  return null;
}

function positiveInteger(value, fallback, max) {
  const number = Number(value);
  if (!Number.isFinite(number)) return fallback;
  return Math.max(1, Math.min(max, Math.round(number)));
}

function playerVisibleNotes(notes) {
  if (!Array.isArray(notes)) return [];
  return notes.filter((note) => isPlainObject(note) && note.visibility !== "gm");
}

function playerVisibleEvents(events, relationshipRank = 0) {
  if (!Array.isArray(events)) return [];
  return events
    .filter((event) => isEventRevealedAtRank(event, relationshipRank))
    .map((event) => {
      const clean = cloneStorageValue(event);
      if (clean?.eventType === "gift" && isPlainObject(clean.gift)) {
        delete clean.gift.profileSource;
        delete clean.gift.stageId;
        delete clean.gift.ruleId;
        delete clean.gift.approvalRequestId;
      }
      return clean;
    });
}

function isPlainObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

export function sanitizePatchForUser(user = currentUser(), ownerActor, relationship, patch) {
  if (user?.isGM === true) return cloneStorageValue(patch);
  if (relationship && !canManageRelationship(user, ownerActor, relationship)) return null;
  if (!relationship && !canEditRelationships(user, ownerActor)) return null;
  const clean = pickAllowedFields(patch, playerRelationshipFields(user, ownerActor));
  if ("stats" in clean) clean.stats = sanitizePlayerStatCards(clean.stats);
  if ("notes" in clean) {
    clean.notes = sanitizePlayerNotesPatch(relationship, clean.notes);
  }
  return clean;
}

/**
 * Rebuild player-authored Stat Cards from the supported scalar leaves only.
 * The Manager exposes three fixed cards; this authoritative boundary mirrors
 * that shape so a forged socket payload cannot add rows or nested metadata.
 */
export function sanitizePlayerStatCards(stats) {
  if (!Array.isArray(stats)) return [];
  return stats.slice(0, PLAYER_STAT_CARD_LIMIT).map((stat) => {
    const source = isPlainObject(stat) ? stat : {};
    return {
      key: typeof source.key === "string" ? source.key : "",
      value: typeof source.value === "string" ? source.value : "",
      accent: source.accent === true
    };
  });
}

/**
 * Player relationship target fields require asynchronous document validation
 * by the active GM, so the general-purpose patch sanitizer continues to strip
 * them. This mutation-only boundary forwards the requested values to the GM
 * socket handler, where the target is resolved, permission-checked, and
 * canonicalized before storage.
 */
export function sanitizeRelationshipMutationForUser(user = currentUser(), ownerActor, relationship, patch) {
  const clean = sanitizePatchForUser(user, ownerActor, relationship, patch);
  if (!clean || user?.isGM === true) return clean;
  if (!patch || typeof patch !== "object" || Array.isArray(patch)) return clean;

  for (const field of PLAYER_RELATIONSHIP_TARGET_FIELDS) {
    if (Object.prototype.hasOwnProperty.call(patch, field)) {
      clean[field] = cloneStorageValue(patch[field]);
    }
  }
  return clean;
}

/**
 * A non-GM may only author player-visible notes. Drop any GM-only note they
 * submit, then re-attach the GM-only notes already stored on the relationship so
 * a full-array replace (updateRelationship merges patch over current) cannot
 * silently delete the GM's private notes.
 */
export function sanitizePlayerNotesPatch(relationship, submittedNotes) {
  const incoming = Array.isArray(submittedNotes) ? submittedNotes : [];
  const existing = Array.isArray(relationship?.notes) ? relationship.notes : [];
  const reservedGmIds = new Set(existing
    .filter((note) => isPlainObject(note) && note.visibility === "gm" && typeof note.id === "string")
    .map((note) => note.id));
  const usedPlayerIds = new Set();
  const playerVisible = incoming
    .filter((note) => isPlainObject(note) && note.visibility !== "gm")
    .map((note) => {
      const clean = cloneStorageValue(note);
      if (
        typeof clean.id !== "string"
        || clean.id.length === 0
        || reservedGmIds.has(clean.id)
        || usedPlayerIds.has(clean.id)
      ) {
        delete clean.id;
      } else {
        usedPlayerIds.add(clean.id);
      }
      clean.visibility = "players";
      return clean;
    });

  // Keep private notes in their existing slots while replacing only the
  // player-visible sequence. A player reorder must never reveal or silently
  // shove the GM's tabs to the end of the dossier.
  const merged = [];
  let playerIndex = 0;
  for (const note of existing) {
    if (isPlainObject(note) && note.visibility === "gm") {
      merged.push(cloneStorageValue(note));
    } else if (playerIndex < playerVisible.length) {
      merged.push(playerVisible[playerIndex]);
      playerIndex += 1;
    }
  }
  while (playerIndex < playerVisible.length) {
    merged.push(playerVisible[playerIndex]);
    playerIndex += 1;
  }
  return merged;
}

export function sanitizeEventPatchForUser(user = currentUser(), ownerActor, relationship, patch, currentEvent = null) {
  const normalizedPatch = normalizeEventRankChangePatch(patch);
  if (user?.isGM === true) return normalizedPatch;
  if (!canEditRelationshipEvents(user, ownerActor, relationship)) return null;
  // A player may never mutate a future entry by retaining or guessing its id.
  // revealAtRank itself is intentionally absent from PLAYER_EVENT_FIELDS, so
  // only a GM can define or lower the threshold.
  if (currentEvent && !canSeeRelationshipEvent(user, relationship, currentEvent)) return null;
  const allowed = pickAllowedFields(normalizedPatch, PLAYER_EVENT_FIELDS);
  if (Object.keys(allowed).length === 0) return null;
  if (currentEvent?.eventType === "gift") {
    return normalizeEvent({
      ...currentEvent,
      ...allowed,
      eventType: "gift",
      gift: cloneStorageValue(currentEvent.gift)
    });
  }
  const source = isPlainObject(currentEvent) ? currentEvent : {};
  return normalizeEvent({ ...source, ...allowed, eventType: "note" });
}

/** Player-facing Event Log visibility; GMs always retain the complete log. */
export function canSeeRelationshipEvent(user = currentUser(), relationship, event) {
  if (user?.isGM === true) return true;
  return isEventRevealedAtRank(event, isNegativeRelationship(relationship) ? 0 : relationship?.rank);
}

function pickAllowedFields(source, allowedFields) {
  const clean = {};
  if (!source || typeof source !== "object") return clean;
  for (const [key, value] of Object.entries(source)) {
    if (allowedFields.has(key)) clean[key] = cloneStorageValue(value);
  }
  return clean;
}

function playerRelationshipFields(user, ownerActor) {
  const permissions = getPlayerEditFieldPermissions(user, ownerActor);
  const fields = new Set();
  if (permissions.basic) addFields(fields, PLAYER_BASIC_FIELDS);
  if (permissions.type) addFields(fields, PLAYER_TYPE_FIELDS);
  if (permissions.rank) addFields(fields, PLAYER_RANK_FIELDS);
  if (permissions.appearance) addFields(fields, PLAYER_APPEARANCE_FIELDS);
  if (permissions.stats) addFields(fields, PLAYER_STATS_FIELDS);
  if (permissions.notes) addFields(fields, PLAYER_NOTES_FIELDS);
  return fields;
}

function addFields(target, source) {
  for (const field of source) target.add(field);
}

function hasOwnerPermission(actor, user) {
  return hasActorPermission(actor, user, PLAYER_EDIT_PERMISSIONS.OWNER);
}

/**
 * Read-only viewing is deliberately outside both the master edit switch and the
 * minimum user role: it replaces a standalone observer-view toggle that was
 * gated by neither.
 */
function hasPlayerViewAccess(user, actor) {
  return hasActorPermission(actor, user, getPlayerViewPermission());
}

/**
 * Resolve the shared preconditions for every edit category once, then hand back
 * a per-category test. Returns `null` when nothing can be granted, so callers
 * that only need "any category" can stop before touching the thresholds.
 */
function playerCategoryResolver(user, ownerActor) {
  if (!ownerActor) return null;
  if (!isPlayerEditEnabled()) return null;
  if (!hasMinimumUserRole(user, getPlayerEditMinimumRole())) return null;
  return (category) => {
    const threshold = getPlayerCategoryPermission(category);
    if (threshold === PLAYER_CATEGORY_PERMISSIONS.OFF) return false;
    return hasActorPermission(ownerActor, user, threshold);
  };
}

function hasPlayerEditCategory(user, ownerActor, category) {
  if (user?.isGM === true) return true;
  const resolve = playerCategoryResolver(user, ownerActor);
  return resolve ? resolve(category) === true : false;
}

function hasAnyPlayerEditCategory(user, ownerActor) {
  const resolve = playerCategoryResolver(user, ownerActor);
  if (!resolve) return false;
  return PLAYER_EDIT_CATEGORY_NAMES.some((category) => resolve(category) === true);
}

function buildCategoryPermissions(resolve) {
  const permissions = {};
  for (const category of PLAYER_EDIT_CATEGORY_NAMES) {
    permissions[category] = resolve(category) === true;
  }
  return permissions;
}

/** An unknown category resolves to `OFF` so a mistyped name fails closed. */
function getPlayerCategoryPermission(category) {
  const descriptor = PLAYER_EDIT_CATEGORY_SETTINGS[category];
  if (!descriptor) return PLAYER_CATEGORY_PERMISSIONS.OFF;
  return readEffectivePermissionValue(descriptor.key, descriptor.fallback, PLAYER_CATEGORY_PERMISSION_VALUES);
}

function getPlayerViewPermission() {
  return readEffectivePermissionValue(
    SETTING_PLAYER_VIEW_PERMISSION,
    PLAYER_CATEGORY_PERMISSIONS.OWNER,
    PLAYER_VIEW_PERMISSION_VALUES
  );
}

/**
 * Read one threshold through the schema cursor rather than straight from the
 * new Setting.
 *
 * Below the current schema version the world has not been converted yet, so the
 * new Settings still carry their registered defaults. Those defaults describe a
 * fresh world, not this one: a legacy world that had switched a category off
 * would silently regain it. Deriving the value from the legacy Settings instead
 * makes pre-migration behaviour identical to the legacy model, which is what
 * stops migration timing — or a migration that never completes — from changing
 * what a world enforces.
 *
 * The legacy projection is rebuilt per read on purpose. It is eleven cheap
 * Setting reads, and caching it would miss a GM changing a value at runtime.
 */
function readEffectivePermissionValue(key, fallback, allowedValues) {
  if (getPlayerPermissionSchemaVersion() >= PLAYER_PERMISSION_SCHEMA_VERSION) {
    return getStringSetting(key, fallback, allowedValues);
  }
  const derived = buildMigratedPlayerPermissionValues(readLegacyPlayerPermissionValues())[key];
  return allowedValues.has(derived) ? derived : fallback;
}

function hasActorPermission(actor, user, permission) {
  if (typeof actor?.testUserPermission === "function") {
    return actor.testUserPermission(user, documentOwnershipLevel(permission)) === true;
  }
  return actor?.isOwner === true;
}

function documentOwnershipLevel(permission) {
  return globalThis.CONST?.DOCUMENT_OWNERSHIP_LEVELS?.[permission] ?? permission;
}

function hasMinimumUserRole(user, minimumRole) {
  return userRoleValue(user?.role) >= userRoleValue(minimumRole);
}

function userRoleValue(role) {
  if (typeof role === "number") return role;
  if (typeof role === "string") {
    const foundryRole = globalThis.CONST?.USER_ROLES?.[role];
    if (typeof foundryRole === "number") return foundryRole;
    return FALLBACK_USER_ROLE_VALUES[role] ?? Number.NEGATIVE_INFINITY;
  }
  return Number.NEGATIVE_INFINITY;
}

function getPlayerEditMinimumRole() {
  return getStringSetting(
    SETTING_PLAYER_EDIT_MIN_ROLE,
    PLAYER_EDIT_ROLES.TRUSTED,
    PLAYER_EDIT_ROLE_VALUES
  );
}

function getPlayerEditMinimumPermission() {
  return getStringSetting(
    SETTING_PLAYER_EDIT_MIN_PERMISSION,
    PLAYER_EDIT_PERMISSIONS.OWNER,
    PLAYER_EDIT_PERMISSION_VALUES
  );
}

function isPlayerEditEnabled() {
  return getBooleanSetting(SETTING_ALLOW_PLAYER_EDIT, false);
}

function isPlayerGiftEnabled() {
  return getBooleanSetting(SETTING_ALLOW_PLAYER_GIVE_GIFTS, GIFT_SETTINGS_DEFAULTS.allowPlayerGiveGifts);
}

function getBooleanSetting(key, fallback) {
  if (typeof game === "undefined" || typeof game.settings?.get !== "function") return fallback;
  try {
    const value = game.settings.get(MODULE_ID, key);
    return typeof value === "boolean" ? value : fallback;
  } catch (error) {
    return fallback;
  }
}

function registerPlayerEditFieldSetting(key, localizationKey, defaultValue) {
  game.settings.register(MODULE_ID, key, {
    name: `STYLISH_RELATIONSHIP_TRACKER.settings.${localizationKey}.name`,
    hint: `STYLISH_RELATIONSHIP_TRACKER.settings.${localizationKey}.hint`,
    scope: "world",
    config: false,
    type: Boolean,
    default: defaultValue
  });
}

function registerPlayerCategoryPermissionSetting(key, defaultValue) {
  game.settings.register(MODULE_ID, key, {
    name: `STYLISH_RELATIONSHIP_TRACKER.settings.${key}.name`,
    hint: `STYLISH_RELATIONSHIP_TRACKER.settings.${key}.hint`,
    scope: "world",
    config: false,
    type: String,
    choices: { ...PLAYER_CATEGORY_PERMISSION_CHOICES },
    default: defaultValue
  });
}

function getPositiveIntegerSetting(key, fallback, max) {
  if (typeof game === "undefined" || typeof game.settings?.get !== "function") {
    return positiveInteger(fallback, 1, max);
  }
  try {
    return positiveInteger(game.settings.get(MODULE_ID, key), fallback, max);
  } catch (_error) {
    return positiveInteger(fallback, 1, max);
  }
}

function getNonNegativeIntegerSetting(key, fallback, max) {
  if (typeof game === "undefined" || typeof game.settings?.get !== "function") {
    return nonNegativeInteger(fallback, 0, max);
  }
  try {
    return nonNegativeInteger(game.settings.get(MODULE_ID, key), fallback, max);
  } catch (_error) {
    return nonNegativeInteger(fallback, 0, max);
  }
}

function getStringSetting(key, fallback, allowedValues) {
  if (typeof game === "undefined" || typeof game.settings?.get !== "function") return fallback;
  try {
    const value = game.settings.get(MODULE_ID, key);
    return allowedValues.has(value) ? value : fallback;
  } catch (error) {
    return fallback;
  }
}

function nonNegativeInteger(value, fallback, max) {
  const number = Number(value);
  if (!Number.isFinite(number)) return fallback;
  return Math.max(0, Math.min(max, Math.round(number)));
}

function currentUser() {
  return typeof game !== "undefined" ? game.user : null;
}
