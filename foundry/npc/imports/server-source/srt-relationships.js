import {
  DEFAULT_MAX_RANK,
  DEFAULT_RANK_STEPS,
  FLAG_KEY,
  FLAG_SCOPE,
  GIFT_CONSUME_MODES,
  GIFT_MATCH_MODES,
  GIFT_PREFERENCE_VISIBILITY,
  GIFT_PREFERENCE_VISIBILITY_VALUES,
  GIFT_PROFILE_DEFAULTS,
  GIFT_PROFILE_MODES,
  GIFT_PROFILE_SOURCES,
  GIFT_REACTION_CONSUME_MODES,
  GIFT_REACTION_AUDIENCE_VALUES,
  GIFT_REACTION_DISPLAY_MODE_VALUES,
  GIFT_REACTION_DISPLAY_MODES,
  GIFT_REACTIONS,
  GIFT_SETTINGS_DEFAULTS,
  GIFT_TARGET_KINDS,
  GIFT_UNMATCHED_GIFT_MODES,
  EVENT_RANK_CHANGES,
  MODULE_ID,
  RELATIONSHIP_POLARITIES,
  RELATIONSHIP_SYNC_MODES
} from "./constants.js";
import {
  canUnlockRelationshipWithGift,
  cloneStorageValue,
  createDefaultRelationshipData,
  generateEventId,
  generateRelationshipId,
  getTargetActorGiftProfile,
  migrateRelationshipData,
  normalizeEvent,
  normalizeEventRankChangePatch,
  normalizeRelationship,
  normalizeRelationshipData
} from "./data-model.js";
import {
  consumeEmbeddedGiftItem,
  getEmbeddedGiftItem,
  getGiftItemMatchMetadata,
  getGiftItemMaxQuantity,
  isGiftItemEligible,
  rollbackConsumedGiftItem
} from "./gift-items.js";
import {
  SETTING_GIFT_DEFAULT_CONSUME_MODE,
  SETTING_GIFT_DEFAULT_MAX_QUANTITY_PER_GIFT,
  SETTING_GIFT_DEFAULT_REACTION_AUDIENCE,
  SETTING_GIFT_DEFAULT_REACTION_DISPLAY_MODE
} from "./permissions.js";
import {
  mergeIdArrayDrafts,
  mergeStoragePatchFromBaseline
} from "./three-way-merge.js";
export { mergeStoragePatchFromBaseline } from "./three-way-merge.js";
import { executeCrossedRankMacroTriggers } from "./rank-macro-triggers.js";
import {
  applyRelationshipAxisDelta,
  isNegativeRelationship,
  relationshipEffectivePolarity,
  relationshipMagnitudeState,
  relationshipSignedRank
} from "./relationship-polarity.js";
import {
  enqueueRelationshipActorMutation,
  enqueueSerialMutation,
  relationshipActorMutationKey
} from "./relationship-mutation-queue.js";
import {
  applySharedRelationshipSnapshot,
  enqueueRelationshipSyncGroupMutation,
  findRelationshipSyncGroup,
  isRelationshipSyncMember,
  mutateRelationshipSyncGroup,
  readRelationshipSyncRegistry,
  removeRelationshipSyncMember,
  updateRelationshipSyncGroupFromRelationship
} from "./relationship-sync-store.js";
import { resolveWorldProfileDefaults } from "./profile-defaults.js";

const GIFT_MATCH_PRIORITY = Object.freeze([
  GIFT_MATCH_MODES.SOURCE_UUID,
  GIFT_MATCH_MODES.UUID,
  GIFT_MATCH_MODES.NAME,
  GIFT_MATCH_MODES.TYPE,
  GIFT_MATCH_MODES.TAG
]);

const WORLD_CONSUME_MODE_VALUES = Object.freeze([
  GIFT_CONSUME_MODES.CONSUME,
  GIFT_CONSUME_MODES.KEEP
]);

// Item consumption and the relationship/event write form one logical Gift
// transaction. Keep that entire sequence exclusive per giver Item so a second
// Gift cannot consume from a stale quantity while the first one is still being
// persisted or rolled back.
const GIFT_ITEM_MUTATION_QUEUES = new Map();
const RANK_MACRO_EFFECT_QUEUES = new Map();

export async function getRelationshipData(actor) {
  const resolved = await getRelationshipStorageData(actor);
  return {
    ...resolved,
    profile: resolveWorldProfileDefaults(resolved.profile)
  };
}

/** Read the Actor-owned profile without applying the optional world display overlay. */
export async function getRelationshipStorageData(actor) {
  const ownerActor = assertRelationshipActor(actor);
  const stored = getStoredRelationshipData(ownerActor);
  return resolveRelationshipSyncSnapshots(stored, ownerActor);
}

/** Read the complete Actor-owned snapshot without consulting the GM registry. */
function getStoredRelationshipData(ownerActor) {
  const rawData = ownerActor.getFlag(FLAG_SCOPE, FLAG_KEY);
  if (rawData === undefined) return createDefaultRelationshipData(ownerActor);
  return migrateRelationshipData(rawData, ownerActor);
}

/**
 * GM clients can overlay the latest canonical values immediately, even if a
 * prior best-effort fan-out left one Actor snapshot a revision behind. Players
 * intentionally stay on the complete Actor snapshot they are permitted to see;
 * the hidden registry is never part of their read path.
 */
async function resolveRelationshipSyncSnapshots(data, ownerActor) {
  const relationships = Array.isArray(data?.relationships) ? data.relationships : [];
  if (globalThis.game?.user?.isGM !== true || !relationships.some((entry) => entry?.sync?.groupId)) {
    return data;
  }
  try {
    const registry = await readRelationshipSyncRegistry();
    let changed = false;
    const resolved = relationships.map((relationship) => {
      const group = findRelationshipSyncGroup(registry, relationship?.sync?.groupId);
      if (!group || !isRelationshipSyncMember(group, {
        ownerActorUuid: ownerActor?.uuid,
        relationshipId: relationship.id
      })) return relationship;
      changed = true;
      return applySharedRelationshipSnapshot(relationship, group, { mode: group.mode });
    });
    return changed ? normalizeRelationshipData({ ...data, relationships: resolved }) : data;
  } catch (error) {
    console.warn(`${MODULE_ID} | Could not resolve canonical relationship synchronization snapshots`, error);
    return data;
  }
}

export async function setRelationshipData(actor, data) {
  const ownerActor = assertRelationshipActor(actor);
  return enqueueRelationshipActorMutation(ownerActor, () => (
    setRelationshipDataUnlocked(ownerActor, data)
  ));
}

async function setRelationshipDataUnlocked(ownerActor, data) {
  assertActiveGmCommitAuthority();
  const normalized = normalizeRelationshipData(data, ownerActor);
  await ownerActor.setFlag(FLAG_SCOPE, FLAG_KEY, normalized);
  notifyRelationshipDataChanged(ownerActor, normalized);
  return normalized;
}

function assertActiveGmCommitAuthority() {
  const user = globalThis.game?.user;
  if (user && user.isGM !== true) {
    throw new Error("Only the active GM can commit relationship data.");
  }
  const activeGM = globalThis.game?.users?.activeGM;
  const activeIsCurrent = activeGM?.isSelf === true || (!!activeGM?.id && activeGM.id === user?.id);
  if (user?.isGM === true && activeGM && !activeIsCurrent) {
    throw new Error("The active GM changed before the relationship update could commit. Please try again.");
  }
}

export async function patchRelationshipData(actor, patchFn, { rankMacroSource = "relationship-update" } = {}) {
  if (typeof patchFn !== "function") {
    throw new Error("patchRelationshipData requires a patch function.");
  }

  const ownerActor = assertRelationshipActor(actor);
  const { current, saved } = await patchRelationshipDataCore(ownerActor, patchFn);
  // Macro code is user-controlled and may call back into this API. Run it after
  // releasing the Actor queue to avoid a re-entrant mutation deadlock.
  scheduleCrossedRankMacroTriggers({
    ownerActor,
    previousData: current,
    nextData: saved,
    source: rankMacroSource
  });
  return saved;
}

async function patchRelationshipDataCore(ownerActor, patchFn, { afterSave = null } = {}) {
  return enqueueRelationshipActorMutation(ownerActor, async () => {
    const current = await getRelationshipStorageData(ownerActor);
    const draft = cloneStorageValue(current);
    const patched = await patchFn(draft);
    const candidate = patched === undefined ? draft : patched;
    const saved = await setRelationshipDataUnlocked(ownerActor, candidate);
    try {
      const afterSaveResult = typeof afterSave === "function"
        ? await afterSave({ current, saved })
        : null;
      return { current, saved, afterSaveResult };
    } catch (error) {
      // The canonical registry and Actor snapshot form one logical write. If
      // publishing the canonical value fails, restore the initiating Actor
      // while its mutation lock is still held.
      try {
        await setRelationshipDataUnlocked(ownerActor, current);
      } catch (rollbackError) {
        throw new Error(`${error?.message ?? "Relationship synchronization failed."} Actor rollback also failed: ${rollbackError?.message ?? rollbackError}`);
      }
      throw error;
    }
  });
}

export async function createRelationship(actor, payload, { authorize = null } = {}) {
  let relationshipId = null;
  const data = await patchRelationshipData(actor, (draft) => {
    if (typeof authorize === "function") authorize(draft);
    const maximum = Math.max(1, Number(draft.profile?.maxRelationshipSlots) || 1);
    if (draft.relationships.length >= maximum) {
      throw new Error(`Relationship limit reached (${maximum}).`);
    }
    const relationship = normalizeRelationship({
      ...(payload && typeof payload === "object" ? payload : {}),
      id: generateRelationshipId()
    });
    while (draft.relationships.some(entry => entry.id === relationship.id)) {
      relationship.id = generateRelationshipId();
    }
    relationshipId = relationship.id;
    draft.relationships.push(relationship);
    return draft;
  });
  return data.relationships.find((relationship) => relationship.id === relationshipId) ?? null;
}

export async function updateRelationship(actor, relationshipId, patch, options = {}) {
  return updateRelationshipFromCurrent(actor, relationshipId, () => patch, options);
}

export async function updateRelationshipFromCurrent(actor, relationshipId, buildPatch, options = {}) {
  if (typeof buildPatch !== "function") throw new Error("A relationship patch builder is required.");
  const ownerActor = assertRelationshipActor(actor);
  return withRelationshipSyncGroupMutation(ownerActor, relationshipId, async ({ queued, verifiedMember }) => {
    let autoUnlockedIds = [];
    let canonicalGroup = null;
    const { current, saved } = await patchRelationshipDataCore(ownerActor, (draft) => {
      const index = findRelationshipIndex(draft, relationshipId);
      const currentRelationship = draft.relationships[index];
      let sourcePatch = cloneStorageValue(buildPatch(cloneStorageValue(currentRelationship)) ?? {});
      if (options.relationshipBaseline && typeof options.relationshipBaseline === "object") {
        sourcePatch = mergeStoragePatchFromBaseline(currentRelationship, sourcePatch, options.relationshipBaseline, {
          excludedKeys: ["events"]
        });
      }
      if (Array.isArray(sourcePatch.events) && Array.isArray(options.eventBaseline)) {
        sourcePatch.events = mergeRelationshipEventDrafts(
          options.eventBaseline,
          sourcePatch.events,
          currentRelationship.events
        );
      }
      if (typeof options.sanitizeMergedPatch === "function") {
        sourcePatch = cloneStorageValue(
          options.sanitizeMergedPatch(sourcePatch, currentRelationship) ?? {}
        );
      }
      draft.relationships[index] = normalizeRelationship({
        ...currentRelationship,
        ...sourcePatch,
        id: currentRelationship.id
      });
      if (options.applyAutoUnlocks === true) {
        const excludedIds = options.preserveUpdatedRelationshipLock === true
          && draft.relationships[index]?.locked === true
          ? [relationshipId]
          : [];
        autoUnlockedIds = applyAutoUnlocksToDraft(draft, { excludedIds });
      }
      return draft;
    }, {
      afterSave: async ({ saved: nextData }) => {
        canonicalGroup = await publishCanonicalRelationshipMutation(nextData, relationshipId, {
          ownerActor,
          queued,
          verifiedMember
        });
      }
    });

    const materialized = canonicalGroup
      ? await materializeCanonicalRelationshipGroup(canonicalGroup, { sourceActor: ownerActor })
      : null;
    const finalData = materialized?.sourceData ?? saved;
    if (options.executeRankMacros !== false) {
      scheduleCrossedRankMacroTriggers({
        ownerActor,
        previousData: current,
        nextData: finalData,
        source: options.rankMacroSource ?? "relationship-update"
      });
    }
    if (typeof options.onAutoUnlocked === "function") options.onAutoUnlocked([...autoUnlockedIds]);
    return finalData.relationships.find((relationship) => relationship.id === relationshipId) ?? null;
  });
}

export function mergeRelationshipEventDrafts(previousStored, previousDraft, nextStored) {
  return mergeIdArrayDrafts(previousStored, previousDraft, nextStored);
}

export async function deleteRelationship(actor, relationshipId, { authorize = null } = {}) {
  const ownerActor = assertRelationshipActor(actor);
  return withRelationshipSyncGroupMutation(ownerActor, relationshipId, async ({ queued, groupId, verifiedMember }) => {
    const { saved } = await patchRelationshipDataCore(ownerActor, (draft) => {
      const index = findRelationshipIndex(draft, relationshipId);
      if (typeof authorize === "function") authorize(draft.relationships[index]);
      draft.relationships.splice(index, 1);
      return draft;
    }, {
      afterSave: async () => {
        if (!groupId || !verifiedMember) return;
        await mutateRelationshipSyncGroup(groupId, (group) => (
          removeRelationshipSyncMember(group, {
            ownerActorUuid: ownerActor.uuid,
            relationshipId
          })
        ), { assumeGroupQueue: queued, deleteIfEmpty: true });
      }
    });
    return saved;
  });
}

export async function createEvent(actor, relationshipId, payload, { authorize = null, buildPayload = null } = {}) {
  let eventId = null;
  const relationship = await updateRelationshipFromCurrent(actor, relationshipId, (current) => {
    if (typeof authorize === "function") authorize(current);
    const source = typeof buildPayload === "function"
      ? buildPayload(cloneStorageValue(current))
      : payload;
    const event = normalizeEvent({
      ...(source && typeof source === "object" ? source : {}),
      id: generateEventId()
    });
    while (current.events.some(entry => entry.id === event.id)) {
      event.id = generateEventId();
    }
    eventId = event.id;
    return { events: [...current.events, event] };
  });
  return relationship?.events.find((event) => event.id === eventId) ?? null;
}

export async function updateEvent(actor, relationshipId, eventId, patch, { authorize = null, buildPatch = null } = {}) {
  const relationship = await updateRelationshipFromCurrent(actor, relationshipId, (currentRelationship) => {
    if (typeof authorize === "function") authorize(currentRelationship);
    const events = cloneStorageValue(currentRelationship.events);
    const index = findEventIndex(currentRelationship, eventId);
    const current = currentRelationship.events[index];
    const sourcePatch = typeof buildPatch === "function"
      ? buildPatch(cloneStorageValue(currentRelationship), cloneStorageValue(current))
      : patch;
    events[index] = normalizeEvent({
      ...current,
      ...normalizeEventRankChangePatch(sourcePatch),
      id: current.id
    });
    return { events };
  });
  return relationship?.events.find((event) => event.id === eventId) ?? null;
}

export async function deleteEvent(actor, relationshipId, eventId, { authorize = null } = {}) {
  const ownerActor = assertRelationshipActor(actor);
  await updateRelationshipFromCurrent(ownerActor, relationshipId, (relationship) => {
    const events = cloneStorageValue(relationship.events);
    const index = findEventIndex(relationship, eventId);
    if (typeof authorize === "function") authorize(relationship, relationship.events[index]);
    events.splice(index, 1);
    return { events };
  });
  return getRelationshipData(ownerActor);
}

export async function moveEvent(actor, relationshipId, eventId, direction, { authorize = null } = {}) {
  const step = Number(direction) < 0 ? -1 : 1;
  return updateRelationshipFromCurrent(actor, relationshipId, (relationship) => {
    const events = cloneStorageValue(relationship.events);
    const index = findEventIndex(relationship, eventId);
    if (typeof authorize === "function") authorize(relationship, relationship.events[index]);
    const target = index + step;
    if (target < 0 || target >= events.length) return {};
    const [moved] = events.splice(index, 1);
    events.splice(target, 0, moved);
    return { events };
  });
}

export async function giveGift(actor, relationshipId, payload, { authorize = null } = {}) {
  const ownerActor = assertRelationshipActor(actor);
  const gift = normalizeGiftPayload(payload);
  const giverActor = await resolveGiverActor(ownerActor, gift.giverActorUuid);
  const result = await withRelationshipSyncGroupMutation(ownerActor, relationshipId, async ({ queued, verifiedMember }) => {
    const localResult = await enqueueSerialMutation(
      GIFT_ITEM_MUTATION_QUEUES,
      giftItemMutationKey(giverActor, gift.itemId),
      () => giveGiftWithinItemMutation(ownerActor, relationshipId, gift, giverActor, authorize, {
        queued,
        verifiedMember
      })
    );
    if (!localResult.canonicalGroup) return localResult;
    const materialized = await materializeCanonicalRelationshipGroup(localResult.canonicalGroup, {
      sourceActor: ownerActor
    });
    if (materialized?.sourceData) {
      localResult.relationship = materialized.sourceData.relationships.find((entry) => entry.id === relationshipId)
        ?? localResult.relationship;
      if (localResult.rankMacroTransition) {
        localResult.rankMacroTransition.nextData = materialized.sourceData;
      }
    }
    return localResult;
  });
  const { rankMacroTransition, canonicalGroup: _canonicalGroup, ...publicResult } = result;
  if (rankMacroTransition) {
    scheduleCrossedRankMacroTriggers({
      ownerActor,
      previousData: rankMacroTransition.previousData,
      nextData: rankMacroTransition.nextData,
      source: "gift"
    });
  }
  return publicResult;
}

async function giveGiftWithinItemMutation(ownerActor, relationshipId, gift, giverActor, authorize, syncContext) {
  // Keep the relationship snapshot, item mutation, relationship write, and any
  // rollback under the same Actor mutation lock. Lock ordering is always
  // giver-item first, owner-relationship second, while non-Gift mutations only
  // take the latter, so there is no inverse acquisition path.
  return enqueueRelationshipActorMutation(ownerActor, () => (
    giveGiftWithinRelationshipMutation(ownerActor, relationshipId, gift, giverActor, authorize, syncContext)
  ));
}

async function giveGiftWithinRelationshipMutation(ownerActor, relationshipId, gift, giverActor, authorize, syncContext = {}) {
  const current = await getRelationshipStorageData(ownerActor);
  const currentRelationship = findRelationship(current, relationshipId);
  if (typeof authorize === "function") authorize(currentRelationship, giverActor);
  if (gift.approvalRequestId) {
    const existingEvent = currentRelationship.events?.find((event) => (
      event?.eventType === "gift" && event?.gift?.approvalRequestId === gift.approvalRequestId
    ));
    if (existingEvent) {
      return {
        relationship: currentRelationship,
        event: existingEvent,
        consumed: existingEvent.gift?.consumed === true,
        // A committed retry must not replay the original rank cut-in. The
        // event's rankChange marker describes the original axis movement.
        rankIncreased: false,
        oldRank: currentRelationship.rank,
        oldPolarity: currentRelationship.polarity,
        newRank: currentRelationship.rank,
        newPolarity: currentRelationship.polarity,
        reaction: null,
        autoUnlockedIds: [],
        duplicate: true
      };
    }
  }
  if (currentRelationship.entryType === "organization") throw new Error("Organizations do not accept Gifts.");
  if (currentRelationship.locked === true && !canUnlockRelationshipWithGift(currentRelationship)) {
    throw new Error("Cannot give gifts to a locked relationship.");
  }

  const target = await resolveGiftTarget(currentRelationship);
  const profileResolution = resolveGiftProfile(currentRelationship, target);
  const profile = profileResolution.profile;
  if (profile?.enabled !== true) throw new Error("Gift giving is disabled for this relationship.");

  const stage = selectGiftStage(profile, isNegativeRelationship(currentRelationship) ? 0 : currentRelationship.rank);
  const item = getEmbeddedGiftItem(giverActor, gift.itemId);
  if (!item) throw new Error(`Gift item not found: ${gift.itemId}`);
  if (!isGiftItemEligible(item, gift)) {
    throw new Error("This Item type cannot be given as a Gift in the current game system.");
  }

  const worldMaxQuantity = getWorldDefaultMaxQuantity();
  const quantity = resolveGiftQuantity(item, gift, profile, worldMaxQuantity);
  const matchMetadata = getGiftItemMatchMetadata(item, giverActor);
  const rule = matchGiftRule(stage, matchMetadata);
  const outcome = resolveGiftOutcome(profile, stage, rule);
  const currentIsMaxRank = isRelationshipAtMaxRank(currentRelationship);
  if (currentIsMaxRank && profile.allowMaxRankGifts !== true) {
    throw new Error("This Gift Profile blocks gifts at max rank.");
  }

  const consumeMode = resolveGiftConsumeMode(profile, outcome.reaction);
  const rawTotalProgressDelta = outcome.unitProgressDelta * quantity;
  const receipt = await consumeEmbeddedGiftItem(giverActor, {
    itemId: gift.itemId,
    quantity,
    consumeMode,
    maxQuantityPerGift: profile.maxQuantityPerGift,
    worldMaxQuantity,
    systemId: gift.systemId
  });
  let eventId = null;
  let oldRank = currentRelationship.rank;
  let oldPolarity = currentRelationship.polarity;
  let rankIncreased = false;
  let appliedTotalProgressDelta = currentIsMaxRank ? 0 : rawTotalProgressDelta;
  let reactionPayload = null;
  try {
    const previousData = current;
    const draft = cloneStorageValue(current);
    const relationship = findRelationship(draft, relationshipId);
    if (relationship.locked === true && !canUnlockRelationshipWithGift(relationship)) {
      throw new Error("Cannot give gifts to a locked relationship.");
    }

    const isMaxRank = isRelationshipAtMaxRank(relationship);
    if (isMaxRank && profile.allowMaxRankGifts !== true) {
      throw new Error("This Gift Profile blocks gifts at max rank.");
    }
    appliedTotalProgressDelta = isMaxRank ? 0 : rawTotalProgressDelta;
    const progress = computeGiftRankProgress(relationship, appliedTotalProgressDelta);

    oldRank = relationship.rank;
    oldPolarity = relationship.polarity;
    const oldSignedRank = relationshipSignedRank(relationship);
    rankIncreased = progress.positiveRankIncreased;
    relationship.polarity = progress.polarity;
    relationship.rank = progress.rank;
    relationship.rankProgress = progress.progress;
    const signedRankIncreased = relationshipSignedRank(relationship) > oldSignedRank;
    reactionPayload = buildGiftReactionPayload(profile, profileResolution, stage, outcome, appliedTotalProgressDelta);

    const event = normalizeEvent({
      eventType: "gift",
      day: gift.day,
      text: gift.eventText || buildGiftEventText(receipt, outcome),
      rankLabel: outcome.reactionLabel.toUpperCase(),
      rankChange: signedRankIncreased ? EVENT_RANK_CHANGES.UP : EVENT_RANK_CHANGES.NONE,
      gift: {
        giverActorUuid: receipt.sourceActorUuid,
        targetActorUuid: target.targetActorUuid,
        targetLabel: target.targetLabel,
        targetKind: target.targetKind,
        relationshipId: relationship.id,
        itemId: receipt.itemId,
        itemUuid: receipt.itemUuid,
        sourceItemUuid: receipt.sourceItemUuid,
        itemName: receipt.itemName,
        itemImg: receipt.itemImg,
        quantity: receipt.quantity,
        consumed: receipt.consumed,
        consumeMode: receipt.consumeMode,
        profileSource: profileResolution.profileSource,
        stageId: stage.id,
        reaction: outcome.reaction,
        reactionLabel: outcome.reactionLabel,
        unitProgressDelta: outcome.unitProgressDelta,
        totalProgressDelta: appliedTotalProgressDelta,
        ruleId: outcome.ruleId,
        approvalRequestId: gift.approvalRequestId
      }
    });
    eventId = event.id;
    relationship.events.push(event);
    const giftUnlocked = canUnlockRelationshipWithGift(relationship);
    if (giftUnlocked) {
      relationship.locked = false;
      relationship.unlockOnGift = false;
      relationship.unlockRule = null;
    }
    const autoUnlockedIds = [...new Set([
      ...(giftUnlocked ? [relationship.id] : []),
      ...applyAutoUnlocksToDraft(draft)
    ])];
    const data = await setRelationshipDataUnlocked(ownerActor, draft);
    let canonicalGroup = null;
    try {
      canonicalGroup = await publishCanonicalRelationshipMutation(data, relationshipId, {
        ownerActor,
        queued: syncContext?.queued === true,
        verifiedMember: syncContext?.verifiedMember === true
      });
    } catch (error) {
      // Gift consumption, the local event, and the canonical party progress are
      // one transaction. Restore the Actor before rolling the Item back.
      try {
        await setRelationshipDataUnlocked(ownerActor, previousData);
      } catch (rollbackError) {
        throw new Error(`${error?.message ?? "Gift relationship synchronization failed."} Actor rollback also failed: ${rollbackError?.message ?? rollbackError}`);
      }
      throw error;
    }
    const storedRelationship = data.relationships.find((stored) => stored.id === relationshipId) ?? null;
    const storedEvent = storedRelationship?.events.find((stored) => stored.id === eventId) ?? null;
    return {
      relationship: storedRelationship,
      event: storedEvent,
      consumed: receipt.consumed,
      rankIncreased,
      oldRank,
      oldPolarity,
      newRank: storedRelationship?.rank ?? oldRank,
      newPolarity: storedRelationship?.polarity ?? oldPolarity,
      reaction: reactionPayload,
      giftUnlocked,
      autoUnlockedIds,
      rankMacroTransition: { previousData, nextData: data },
      canonicalGroup
    };
  } catch (error) {
    try {
      await rollbackConsumedGiftItem(giverActor, receipt);
    } catch (rollbackError) {
      throw new Error(`${error?.message ?? "Gift relationship update failed."} Gift item rollback also failed: ${rollbackError?.message ?? rollbackError}`);
    }
    throw error;
  }
}

export async function previewGift(actor, relationshipId, payload, { authorize = null } = {}) {
  const ownerActor = assertRelationshipActor(actor);
  const gift = normalizeGiftPayload(payload);
  const current = await getRelationshipData(ownerActor);
  const currentRelationship = findRelationship(current, relationshipId);
  if (currentRelationship.entryType === "organization") throw new Error("Organizations do not accept Gifts.");
  const unlocksWithGift = canUnlockRelationshipWithGift(currentRelationship);
  if (currentRelationship.locked === true && !unlocksWithGift) {
    throw new Error("Cannot preview gifts for a locked relationship.");
  }

  const giverActor = await resolveGiverActor(ownerActor, gift.giverActorUuid);
  if (typeof authorize === "function") authorize(currentRelationship, giverActor);
  const target = await resolveGiftTarget(currentRelationship);
  const profile = resolveGiftProfile(currentRelationship, target).profile;
  if (profile?.enabled !== true) throw new Error("Gift giving is disabled for this relationship.");

  const visibility = unlocksWithGift
    ? GIFT_PREFERENCE_VISIBILITY.HIDDEN
    : resolveGiftPreviewVisibility(profile);
  if (visibility === GIFT_PREFERENCE_VISIBILITY.HIDDEN) {
    return buildGiftPreviewPayload(profile, { visibility });
  }

  const stage = selectGiftStage(profile, isNegativeRelationship(currentRelationship) ? 0 : currentRelationship.rank);
  const item = getEmbeddedGiftItem(giverActor, gift.itemId);
  if (!item) throw new Error(`Gift item not found: ${gift.itemId}`);
  if (!isGiftItemEligible(item, gift)) {
    throw new Error("This Item type cannot be given as a Gift in the current game system.");
  }

  const worldMaxQuantity = getWorldDefaultMaxQuantity();
  const quantity = resolveGiftQuantity(item, gift, profile, worldMaxQuantity);
  const currentIsMaxRank = isRelationshipAtMaxRank(currentRelationship);
  if (currentIsMaxRank && profile.allowMaxRankGifts !== true) {
    throw new Error("This Gift Profile blocks gifts at max rank.");
  }
  const matchMetadata = getGiftItemMatchMetadata(item, giverActor);
  const rule = matchGiftRule(stage, matchMetadata);
  let outcome = null;
  let blocked = false;
  try {
    outcome = resolveGiftOutcome(profile, stage, rule);
  } catch (error) {
    if (!rule && profile?.unmatchedGift?.mode === GIFT_UNMATCHED_GIFT_MODES.BLOCK) {
      blocked = true;
    } else {
      throw error;
    }
  }

  const totalProgressDelta = outcome && !currentIsMaxRank
    ? outcome.unitProgressDelta * quantity
    : 0;
  return buildGiftPreviewPayload(profile, { visibility, outcome, totalProgressDelta, blocked });
}

export function computeRankProgress(relationship, direction) {
  return applyRelationshipAxisDelta(relationship, Math.sign(Number(direction) || 0));
}

export function computeGiftRankProgress(relationship, delta = 1) {
  const state = relationshipMagnitudeState(relationship);
  const gain = Math.max(0, Math.min(9999, Math.round(Number(delta) || 0)));
  if (gain <= 0) return applyRelationshipAxisDelta(relationship, 0);

  // Gifts always improve the visible relationship axis. Existing positive
  // relationships retain the legacy one-rank-per-gift cap, while a hostile
  // relationship can consume the full gain to reconcile across zero.
  if (state.polarity === RELATIONSHIP_POLARITIES.NEGATIVE) {
    return applyRelationshipAxisDelta(relationship, gain);
  }
  if (state.rank >= state.maxRank) return applyRelationshipAxisDelta(relationship, 0);
  const cappedGain = state.rankProgress + gain >= state.rankSteps
    ? state.rankSteps - state.rankProgress
    : gain;
  return applyRelationshipAxisDelta(relationship, cappedGain);
}

export async function changeRelationshipRank(actor, relationshipId, direction, {
  rankMacroSource = "rank-control",
  authorize = null
} = {}) {
  const ownerActor = assertRelationshipActor(actor);
  const result = await withRelationshipSyncGroupMutation(ownerActor, relationshipId, async ({ queued, verifiedMember }) => {
    let canonicalGroup = null;
    const localResult = await enqueueRelationshipActorMutation(ownerActor, async () => {
        const previousData = await getRelationshipStorageData(ownerActor);
        const draft = cloneStorageValue(previousData);
        const relationship = findRelationship(draft, relationshipId);
        if (typeof authorize === "function") authorize(relationship);
        const oldRank = relationship.rank;
        const oldPolarity = relationship.polarity;
        const progress = computeRankProgress(relationship, direction);
        if (!progress.changed) {
          return {
            changed: false,
            rankIncreased: false,
            oldRank,
            oldPolarity,
            newPolarity: oldPolarity,
            relationship: cloneStorageValue(relationship),
            autoUnlockedIds: [],
            previousData,
            nextData: previousData
          };
        }
        relationship.polarity = progress.polarity;
        relationship.rank = progress.rank;
        relationship.rankProgress = progress.progress;
        const autoUnlockedIds = applyAutoUnlocksToDraft(draft);
        const nextData = await setRelationshipDataUnlocked(ownerActor, draft);
        try {
          canonicalGroup = await publishCanonicalRelationshipMutation(nextData, relationshipId, {
            ownerActor,
            queued,
            verifiedMember
          });
        } catch (error) {
          try {
            await setRelationshipDataUnlocked(ownerActor, previousData);
          } catch (rollbackError) {
            throw new Error(`${error?.message ?? "Relationship synchronization failed."} Actor rollback also failed: ${rollbackError?.message ?? rollbackError}`);
          }
          throw error;
        }
        return {
          changed: true,
          rankIncreased: progress.positiveRankIncreased,
          oldRank,
          oldPolarity,
          newPolarity: progress.polarity,
          relationship: nextData.relationships.find(entry => entry.id === relationshipId) ?? null,
          autoUnlockedIds,
          previousData,
          nextData
        };
      });
    if (!localResult.changed || !canonicalGroup) return localResult;
    const materialized = await materializeCanonicalRelationshipGroup(canonicalGroup, { sourceActor: ownerActor });
    if (materialized?.sourceData) {
      localResult.nextData = materialized.sourceData;
      localResult.relationship = materialized.sourceData.relationships.find(entry => entry.id === relationshipId)
        ?? localResult.relationship;
    }
    return localResult;
  });
  if (result.changed) {
    scheduleCrossedRankMacroTriggers({
      ownerActor,
      previousData: result.previousData,
      nextData: result.nextData,
      source: rankMacroSource
    });
  }
  const { previousData, nextData, ...publicResult } = result;
  return publicResult;
}

export function evaluateAutoUnlockIds(relationships, { excludedIds = [] } = {}) {
  const rels = Array.isArray(relationships) ? relationships : [];
  const excluded = new Set(Array.isArray(excludedIds) ? excludedIds : []);
  const unlocking = new Set();
  const isOpen = (rel) => rel.locked !== true || unlocking.has(rel.id);
  let changed = true;
  let guard = rels.length + 1;
  while (changed && guard-- > 0) {
    changed = false;
    const rankOf = (rel, polarity = RELATIONSHIP_POLARITIES.POSITIVE) => (
      relationshipEffectivePolarity(rel) === polarity
        ? Math.min(Number(rel.rank) || 0, Number(rel.maxRank) || 0)
        : 0
    );
    const byId = new Map(rels.map(rel => [rel.id, rel]));
    for (const rel of rels) {
      if (isOpen(rel)) continue;
      if (excluded.has(rel.id)) continue;
      const rule = rel.unlockRule;
      if (!rule) continue;
      const polarity = rule.polarity === RELATIONSHIP_POLARITIES.NEGATIVE
        ? RELATIONSHIP_POLARITIES.NEGATIVE
        : RELATIONSHIP_POLARITIES.POSITIVE;
      const polarityTotal = rels.reduce(
        (sum, candidate) => isOpen(candidate) ? sum + rankOf(candidate, polarity) : sum,
        0
      );
      const target = rule.type === "relationshipRankAtLeast" ? byId.get(rule.relationshipId) : null;
      const qualifies = rule.type === "totalRankAtLeast"
        ? polarityTotal >= (Number(rule.value) || 0)
        : !!target && isOpen(target) && rankOf(target, polarity) >= (Number(rule.value) || 0);
      if (qualifies) {
        unlocking.add(rel.id);
        changed = true;
      }
    }
  }
  return [...unlocking];
}

export async function applyAutoUnlocks(actor) {
  const ownerActor = assertRelationshipActor(actor);
  return enqueueRelationshipActorMutation(ownerActor, async () => {
    const current = await getRelationshipStorageData(ownerActor);
    const draft = cloneStorageValue(current);
    const ids = applyAutoUnlocksToDraft(draft);
    if (ids.length === 0) return [];
    await setRelationshipDataUnlocked(ownerActor, draft);
    return ids;
  });
}

function applyAutoUnlocksToDraft(draft, { excludedIds = [] } = {}) {
  const ids = evaluateAutoUnlockIds(draft?.relationships, { excludedIds });
  if (ids.length === 0) return [];
  const unlock = new Set(ids);
  for (const rel of draft.relationships) {
    if (!unlock.has(rel.id)) continue;
    rel.locked = false;
    rel.unlockRule = null;
  }
  return ids;
}

/**
 * Acquire the shared-group lock before any Item or Actor mutation lock. This
 * makes rank changes from different party members observe one canonical state
 * and establishes the global lock order `group -> item -> actor` for Gifts.
 */
async function withRelationshipSyncGroupMutation(ownerActor, relationshipId, operation) {
  const stored = getStoredRelationshipData(ownerActor);
  const relationship = stored.relationships.find((entry) => entry.id === relationshipId) ?? null;
  const groupId = asString(relationship?.sync?.groupId).trim();
  if (!groupId) return operation({ queued: false, groupId: "", verifiedMember: false });
  return enqueueRelationshipSyncGroupMutation(groupId, async () => {
    const registry = await readRelationshipSyncRegistry();
    const group = findRelationshipSyncGroup(registry, groupId);
    const verifiedMember = isRelationshipSyncMember(group, {
      ownerActorUuid: ownerActor?.uuid,
      relationshipId
    });
    if (verifiedMember && (
      relationship.sync?.appliedRevision !== group.revision
      || relationship.sync?.mode !== group.mode
    )) {
      // Repair a lagging initiating member before building its mutation. This
      // commonly happens after a prior best-effort fan-out failure or a
      // membership-only revision bump. The exact registry membership has
      // already been verified, and the normal Actor queue prevents clobbering
      // another local write while local-only fields remain preserved.
      await enqueueRelationshipActorMutation(ownerActor, async () => {
        const current = getStoredRelationshipData(ownerActor);
        const index = current.relationships.findIndex((entry) => entry.id === relationshipId);
        if (index < 0 || current.relationships[index]?.sync?.groupId !== groupId) {
          throw new Error("The synchronized Relationship changed before its canonical snapshot could be repaired.");
        }
        const draft = cloneStorageValue(current);
        draft.relationships[index] = applySharedRelationshipSnapshot(
          current.relationships[index],
          group,
          { mode: group.mode }
        );
        applyAutoUnlocksToDraft(draft);
        await setRelationshipDataUnlocked(ownerActor, draft);
      });
    }
    return operation({ queued: true, groupId, verifiedMember });
  });
}

/** Publish the initiating member's allowlisted values while its group is held. */
async function publishCanonicalRelationshipMutation(data, relationshipId, {
  ownerActor = null,
  queued = false,
  verifiedMember = false
} = {}) {
  const relationship = data?.relationships?.find((entry) => entry.id === relationshipId) ?? null;
  const groupId = asString(relationship?.sync?.groupId).trim();
  if (!groupId || verifiedMember !== true) return null;
  return updateRelationshipSyncGroupFromRelationship(groupId, relationship, {
    mode: relationship.sync?.mode ?? RELATIONSHIP_SYNC_MODES.CONTENT,
    ownerActorUuid: ownerActor?.uuid,
    relationshipId,
    expectedRevision: relationship.sync?.appliedRevision,
    assumeGroupQueue: queued === true
  });
}

/**
 * Fan the canonical revision back into complete Actor-owned snapshots. Missing
 * or inaccessible members are left stale for later Manager reconciliation;
 * canonical success is never undone merely because one follower Actor failed.
 */
async function materializeCanonicalRelationshipGroup(group, { sourceActor = null } = {}) {
  const groupId = asString(group?.id).trim();
  if (!groupId) return { sourceData: null, failures: [] };
  const failures = [];
  let sourceData = null;
  const sourceUuid = asString(sourceActor?.uuid);

  for (const member of Array.isArray(group.members) ? group.members : []) {
    const ownerActorUuid = asString(member?.ownerActorUuid).trim();
    const relationshipId = asString(member?.relationshipId).trim();
    if (!ownerActorUuid || !relationshipId) continue;
    try {
      const memberActor = sourceUuid && ownerActorUuid === sourceUuid
        ? sourceActor
        : await resolveActorDocument(ownerActorUuid);
      if (!memberActor) throw new Error(`Relationship synchronization Actor could not be resolved: ${ownerActorUuid}`);
      const saved = await enqueueRelationshipActorMutation(memberActor, async () => {
          const data = getStoredRelationshipData(memberActor);
          const index = data.relationships.findIndex((entry) => entry.id === relationshipId);
          if (index < 0) throw new Error(`Relationship synchronization member is missing: ${relationshipId}`);
          const local = data.relationships[index];
          if (local?.sync?.groupId !== groupId) {
            throw new Error(`Relationship synchronization member no longer belongs to ${groupId}.`);
          }
          const draft = cloneStorageValue(data);
          draft.relationships[index] = applySharedRelationshipSnapshot(local, group, { mode: group.mode });
          applyAutoUnlocksToDraft(draft);
          return setRelationshipDataUnlocked(memberActor, draft);
        });
      if (ownerActorUuid === sourceUuid) sourceData = saved;
    } catch (error) {
      failures.push({ ownerActorUuid, relationshipId, error });
      console.warn(`${MODULE_ID} | Could not materialize synchronized relationship member`, {
        groupId,
        ownerActorUuid,
        relationshipId,
        error
      });
    }
  }
  return { sourceData, failures };
}

function assertRelationshipActor(actor) {
  if (!actor || typeof actor.getFlag !== "function" || typeof actor.setFlag !== "function") {
    throw new Error("A valid owner Actor is required for relationship data.");
  }
  return actor;
}

function giftItemMutationKey(actor, itemId) {
  return `${relationshipActorMutationKey(actor)}\u0000${asString(itemId)}`;
}

function scheduleCrossedRankMacroTriggers(options) {
  // The relationship mutation is already committed at this point. A user
  // Macro may legitimately open a dialog, wait on animation, or never settle;
  // do not keep the authoritative socket request pending and tempt the client
  // to retry an operation that has already consumed an Item or changed rank.
  const key = relationshipActorMutationKey(options?.ownerActor);
  const previous = RANK_MACRO_EFFECT_QUEUES.get(key) ?? Promise.resolve();
  const execution = previous.then(
    () => executeCrossedRankMacroTriggers(options),
    () => executeCrossedRankMacroTriggers(options)
  );
  const tail = execution.then(() => undefined, () => undefined);
  RANK_MACRO_EFFECT_QUEUES.set(key, tail);
  void execution
    .catch((error) => {
      console.error(`${MODULE_ID} | Failed to schedule crossed rank Macro triggers`, error);
    })
    .finally(() => {
      if (RANK_MACRO_EFFECT_QUEUES.get(key) === tail) RANK_MACRO_EFFECT_QUEUES.delete(key);
    });
}

export async function waitForRankMacroEffects(actor = null) {
  const key = actor ? relationshipActorMutationKey(actor) : null;
  if (key) {
    while (RANK_MACRO_EFFECT_QUEUES.has(key)) await RANK_MACRO_EFFECT_QUEUES.get(key);
    return;
  }
  while (RANK_MACRO_EFFECT_QUEUES.size > 0) {
    await Promise.all([...RANK_MACRO_EFFECT_QUEUES.values()]);
  }
}

function normalizeGiftPayload(payload) {
  const source = payload && typeof payload === "object" ? payload : {};
  const itemId = asString(source.itemId);
  if (!itemId) throw new Error("Gift item id is required.");
  return {
    itemId,
    quantity: positiveInteger(source.quantity, 1, 999),
    giverActorUuid: asString(source.giverActorUuid),
    day: asString(source.day).trim(),
    eventText: asString(source.eventText || source.text).trim(),
    systemId: asString(source.systemId),
    approvalRequestId: asString(source.approvalRequestId)
  };
}

function buildGiftEventText(receipt, outcome) {
  const line = asString(outcome?.line).trim();
  if (line) return line;
  const itemName = asString(receipt?.itemName) || "Item";
  return `Gave ${itemName} x${receipt?.quantity ?? 1}.`;
}

async function resolveGiverActor(ownerActor, giverActorUuid) {
  if (!giverActorUuid || giverActorUuid === ownerActor.uuid) return ownerActor;
  const giverActor = await resolveActorDocument(giverActorUuid);
  if (!giverActor) throw new Error(`Gift giver Actor could not be resolved: ${giverActorUuid}`);
  return giverActor;
}

async function resolveGiftTarget(relationship) {
  const targetUuid = asString(relationship?.targetUuid);
  if (relationship?.entryType === "actor" && targetUuid) {
    const targetActor = await resolveActorDocument(targetUuid);
    return {
      targetKind: GIFT_TARGET_KINDS.ACTOR,
      targetActor,
      targetActorUuid: targetUuid,
      targetLabel: asString(targetActor?.name) || asString(relationship.customName) || targetUuid
    };
  }

  return {
    targetKind: GIFT_TARGET_KINDS.CUSTOM,
    targetActor: null,
    targetActorUuid: "",
    targetLabel: asString(relationship?.customName) || asString(relationship?.customRole) || "Custom Target"
  };
}

function resolveGiftProfile(relationship, target) {
  if (relationship.giftProfileMode === GIFT_PROFILE_MODES.DISABLED) {
    throw new Error("Gift giving is disabled for this relationship.");
  }

  if (target.targetKind === GIFT_TARGET_KINDS.CUSTOM || relationship.giftProfileMode === GIFT_PROFILE_MODES.RELATIONSHIP_OVERRIDE) {
    if (!relationship.giftProfile) throw new Error("Gift Profile setup error: relationship profile is missing.");
    return {
      profile: relationship.giftProfile,
      profileSource: GIFT_PROFILE_SOURCES.RELATIONSHIP_OVERRIDE
    };
  }

  if (!target.targetActor) {
    throw new Error(`Gift Profile setup error: target Actor could not be resolved for ${relationship.targetUuid}.`);
  }
  return {
    profile: getTargetActorGiftProfile(target.targetActor),
    profileSource: GIFT_PROFILE_SOURCES.TARGET_ACTOR
  };
}

function selectGiftStage(profile, rank) {
  const currentRank = Math.max(0, Math.round(Number(rank) || 0));
  const stages = Array.isArray(profile?.stages) ? profile.stages : [];
  const stage = stages.find((candidate) => {
    const min = Math.max(0, Math.round(Number(candidate?.rankMin) || 0));
    const max = Math.max(min, Math.round(Number(candidate?.rankMax) || min));
    return currentRank >= min && currentRank <= max;
  }) ?? stages.find((candidate) => candidate?.id === "default" || candidate?.id === "rank-0");
  if (!stage) throw new Error(`Gift Profile setup error: no stage is configured for rank ${currentRank}.`);
  return stage;
}

function resolveGiftQuantity(item, gift, profile, worldMaxQuantity) {
  const maxQuantity = getGiftItemMaxQuantity(item, {
    maxQuantityPerGift: profile.maxQuantityPerGift,
    worldMaxQuantity,
    systemId: gift.systemId
  });
  if (maxQuantity < 1) throw new Error("Gift item has no available quantity.");
  const quantity = Math.min(gift.quantity, maxQuantity);
  if (!Number.isFinite(quantity) || quantity < 1) throw new Error("Gift quantity must be at least 1.");
  return quantity;
}

function matchGiftRule(stage, metadata) {
  const rules = Array.isArray(stage?.rules) ? stage.rules : [];
  for (const mode of GIFT_MATCH_PRIORITY) {
    const rule = rules.find((candidate) => candidate?.match?.mode === mode && giftRuleMatches(candidate, metadata));
    if (rule) return rule;
  }
  return null;
}

function giftRuleMatches(rule, metadata) {
  const mode = rule?.match?.mode;
  const value = asString(rule?.match?.value).trim();
  if (!value) return false;
  switch (mode) {
    case GIFT_MATCH_MODES.SOURCE_UUID:
      return asString(metadata?.sourceUuid) === value;
    case GIFT_MATCH_MODES.UUID:
      return asString(metadata?.uuid) === value;
    case GIFT_MATCH_MODES.NAME:
      return normalizeGiftText(metadata?.name) === normalizeGiftText(value);
    case GIFT_MATCH_MODES.TYPE:
      return asString(metadata?.type).trim() === value;
    case GIFT_MATCH_MODES.TAG:
      return Array.isArray(metadata?.tags) && metadata.tags.includes(normalizeGiftText(value));
    default:
      return false;
  }
}

function resolveGiftOutcome(profile, stage, rule) {
  if (!rule) {
    if (profile?.unmatchedGift?.mode === GIFT_UNMATCHED_GIFT_MODES.BLOCK) {
      throw new Error("This Gift Profile blocks unmatched gifts.");
    }
    const reaction = resolveProfileReactionId(profile, profile?.unmatchedGift?.reactionId);
    const reactionConfig = getStageReaction(stage, reaction);
    return {
      reaction,
      reactionLabel: getProfileReactionLabel(profile, reaction),
      line: reactionConfig.line,
      previewHintLine: reactionConfig.previewHintLine,
      previewResultLine: reactionConfig.previewResultLine,
      cutinImage: reactionConfig.cutinImage,
      sfx: reactionConfig.sfx,
      cutinScale: reactionConfig.cutinScale,
      cutinOffsetX: reactionConfig.cutinOffsetX,
      cutinOffsetY: reactionConfig.cutinOffsetY,
      unitProgressDelta: nonNegativeInteger(profile?.unmatchedGift?.progressDelta, 0, 99),
      ruleId: ""
    };
  }

  const reaction = resolveProfileReactionId(profile, rule.reaction);
  const reactionConfig = getStageReaction(stage, reaction);
  return {
    reaction,
    reactionLabel: getProfileReactionLabel(profile, reaction),
    line: reactionConfig.line,
    previewHintLine: reactionConfig.previewHintLine,
    previewResultLine: reactionConfig.previewResultLine,
    cutinImage: reactionConfig.cutinImage,
    sfx: reactionConfig.sfx,
    cutinScale: reactionConfig.cutinScale,
    cutinOffsetX: reactionConfig.cutinOffsetX,
    cutinOffsetY: reactionConfig.cutinOffsetY,
    unitProgressDelta: reactionConfig.progressDelta,
    ruleId: asString(rule.id)
  };
}

function getStageReaction(stage, reaction) {
  const source = stage?.reactions?.[reaction] ?? {};
  return {
    progressDelta: nonNegativeInteger(source.progressDelta, 0, 99),
    line: asString(source.line),
    previewHintLine: asString(source.previewHintLine),
    previewResultLine: asString(source.previewResultLine),
    cutinImage: asString(source.cutinImage),
    sfx: asString(source.sfx),
    cutinScale: finiteNumber(source.cutinScale, 1),
    cutinOffsetX: finiteNumber(source.cutinOffsetX, 0),
    cutinOffsetY: finiteNumber(source.cutinOffsetY, 0)
  };
}

function resolveProfileReactionId(profile, reactionId) {
  const id = asString(reactionId).trim();
  if (getProfileReaction(profile, id)) return id;
  const fallback = asString(profile?.defaultReactionId).trim();
  if (getProfileReaction(profile, fallback)) return fallback;
  return profile?.reactions?.[0]?.id ?? GIFT_REACTIONS.NEUTRAL;
}

function getProfileReaction(profile, reactionId) {
  const id = asString(reactionId).trim();
  return Array.isArray(profile?.reactions)
    ? profile.reactions.find((reaction) => reaction?.id === id) ?? null
    : null;
}

function getProfileReactionLabel(profile, reactionId) {
  const reaction = getProfileReaction(profile, reactionId);
  return asString(reaction?.label).trim() || asString(reactionId).trim();
}

function resolveGiftConsumeMode(profile, reaction) {
  const reactionConfig = getProfileReaction(profile, reaction);
  if (reactionConfig?.consumeMode === GIFT_REACTION_CONSUME_MODES.CONSUME) return GIFT_CONSUME_MODES.CONSUME;
  if (reactionConfig?.consumeMode === GIFT_REACTION_CONSUME_MODES.KEEP) return GIFT_CONSUME_MODES.KEEP;
  if (profile.consumeMode === GIFT_CONSUME_MODES.WORLD_DEFAULT) return getWorldDefaultConsumeMode();
  return profile.consumeMode === GIFT_CONSUME_MODES.KEEP ? GIFT_CONSUME_MODES.KEEP : GIFT_CONSUME_MODES.CONSUME;
}

function buildGiftReactionPayload(profile, profileResolution, stage, outcome, totalProgressDelta) {
  const configuredDisplayMode = getGiftReactionDisplayMode(profile.reactionDisplayMode);
  const displayMode = configuredDisplayMode === GIFT_REACTION_DISPLAY_MODES.AUTO
    ? (outcome.cutinImage ? GIFT_REACTION_DISPLAY_MODES.CUTIN : GIFT_REACTION_DISPLAY_MODES.DIALOG)
    : configuredDisplayMode;
  return {
    reaction: outcome.reaction,
    reactionLabel: outcome.reactionLabel,
    line: outcome.line,
    cutinImage: outcome.cutinImage,
    sfx: outcome.sfx,
    cutinScale: outcome.cutinScale,
    cutinOffsetX: outcome.cutinOffsetX,
    cutinOffsetY: outcome.cutinOffsetY,
    displayMode,
    audience: getGiftReactionAudience(profile.reactionAudience),
    preferenceVisibility: profile.preferenceVisibility,
    profileSource: profileResolution.profileSource,
    stageId: stage.id,
    ruleId: outcome.ruleId,
    unitProgressDelta: outcome.unitProgressDelta,
    totalProgressDelta
  };
}

function buildGiftPreviewPayload(profile, { visibility = resolveGiftPreviewVisibility(profile), outcome = null, totalProgressDelta = 0, blocked = false } = {}) {
  const base = {
    visibility,
    blocked: blocked === true
  };
  if (visibility === GIFT_PREFERENCE_VISIBILITY.HIDDEN) return base;
  if (blocked === true) {
    return withGiftPreviewLabel(
      { ...base, category: "blocked" },
      giftPreviewLabel({ visibility, blocked: true })
    );
  }
  const category = giftPreviewCategory(outcome?.reaction);
  if (visibility === GIFT_PREFERENCE_VISIBILITY.HINT) {
    return withGiftPreviewLabel(
      { ...base, category },
      giftPreviewLabel({ visibility, outcome, totalProgressDelta })
    );
  }
  return withGiftPreviewLabel({
    ...base,
    category,
    reaction: asString(outcome?.reaction),
    reactionLabel: asString(outcome?.reactionLabel),
    unitProgressDelta: nonNegativeInteger(outcome?.unitProgressDelta, 0, 99),
    totalProgressDelta: nonNegativeInteger(totalProgressDelta, 0, 99999)
  }, giftPreviewLabel({ visibility, outcome, totalProgressDelta }));
}

function withGiftPreviewLabel(payload, label) {
  const text = asString(label).trim();
  return text ? { ...payload, label: text } : payload;
}

function giftPreviewLabel({ visibility, outcome = null, totalProgressDelta = 0, blocked = false } = {}) {
  if (visibility === GIFT_PREFERENCE_VISIBILITY.HINT) {
    if (blocked === true) return "";
    return asString(outcome?.previewHintLine).trim();
  }
  if (visibility !== GIFT_PREFERENCE_VISIBILITY.FULL) return "";
  if (blocked === true) return "";
  const template = asString(outcome?.previewResultLine).trim();
  if (!template) return "";
  return formatGiftPreviewMessage(template, {
    reaction: asString(outcome?.reactionLabel) || asString(outcome?.reaction),
    progress: nonNegativeInteger(totalProgressDelta, 0, 99999)
  });
}

function formatGiftPreviewMessage(template, data) {
  return template
    .replaceAll("{reaction}", asString(data.reaction))
    .replaceAll("{progress}", String(nonNegativeInteger(data.progress, 0, 99999)));
}

function giftPreviewCategory(reaction) {
  switch (reaction) {
    case GIFT_REACTIONS.FAVORITE:
    case GIFT_REACTIONS.LIKED:
      return "positive";
    case GIFT_REACTIONS.DISLIKED:
    case GIFT_REACTIONS.REJECTED:
      return "negative";
    case GIFT_REACTIONS.NEUTRAL:
      return "neutral";
    default:
      return "unknown";
  }
}

function resolveGiftPreviewVisibility(profile) {
  return GIFT_PREFERENCE_VISIBILITY_VALUES.includes(profile?.preferenceVisibility)
    ? profile.preferenceVisibility
    : GIFT_PROFILE_DEFAULTS.preferenceVisibility;
}

function isRelationshipAtMaxRank(relationship) {
  const state = relationshipMagnitudeState(relationship);
  return !isNegativeRelationship(relationship) && state.rank >= state.maxRank;
}

async function resolveActorDocument(uuid) {
  const actorUuid = asString(uuid);
  if (!actorUuid) return null;
  if (typeof globalThis.fromUuid === "function") {
    const document = await resolveActorDocumentFromUuid(actorUuid);
    if (document) return document;
  }

  return resolveActorDocumentFromCollection(actorUuid);
}

async function resolveActorDocumentFromUuid(actorUuid) {
  try {
    return await globalThis.fromUuid(actorUuid);
  } catch (_error) {
    return null;
  }
}

function resolveActorDocumentFromCollection(actorUuid) {
  const actorId = actorUuid.split(".").at(-1);
  const actors = globalThis.game?.actors;
  if (typeof actors?.get === "function") return actors.get(actorId) ?? actors.get(actorUuid) ?? null;
  if (typeof actors?.values === "function") {
    return Array.from(actors.values()).find((actor) => actor?.uuid === actorUuid || actor?.id === actorId) ?? null;
  }
  if (Array.isArray(actors)) return actors.find((actor) => actor?.uuid === actorUuid || actor?.id === actorId) ?? null;
  return null;
}

function getWorldDefaultConsumeMode() {
  return getStringSetting(
    SETTING_GIFT_DEFAULT_CONSUME_MODE,
    GIFT_SETTINGS_DEFAULTS.defaultConsumeMode,
    WORLD_CONSUME_MODE_VALUES
  );
}

function getWorldDefaultMaxQuantity() {
  return getPositiveIntegerSetting(
    SETTING_GIFT_DEFAULT_MAX_QUANTITY_PER_GIFT,
    GIFT_SETTINGS_DEFAULTS.defaultMaxQuantityPerGift,
    999
  );
}

function getGiftReactionAudience(profileValue) {
  if (GIFT_REACTION_AUDIENCE_VALUES.includes(profileValue)) return profileValue;
  return getStringSetting(
    SETTING_GIFT_DEFAULT_REACTION_AUDIENCE,
    GIFT_SETTINGS_DEFAULTS.defaultReactionAudience,
    GIFT_REACTION_AUDIENCE_VALUES
  );
}

function getGiftReactionDisplayMode(profileValue) {
  if (GIFT_REACTION_DISPLAY_MODE_VALUES.includes(profileValue)) return profileValue;
  return getStringSetting(
    SETTING_GIFT_DEFAULT_REACTION_DISPLAY_MODE,
    GIFT_SETTINGS_DEFAULTS.defaultReactionDisplayMode,
    GIFT_REACTION_DISPLAY_MODE_VALUES
  );
}

function getStringSetting(key, fallback, allowedValues) {
  if (typeof game === "undefined" || typeof game.settings?.get !== "function") return fallback;
  try {
    const value = game.settings.get(MODULE_ID, key);
    return allowedValues.includes(value) ? value : fallback;
  } catch (_error) {
    return fallback;
  }
}

function getPositiveIntegerSetting(key, fallback, max) {
  if (typeof game === "undefined" || typeof game.settings?.get !== "function") return positiveInteger(fallback, 1, max);
  try {
    return positiveInteger(game.settings.get(MODULE_ID, key), fallback, max);
  } catch (_error) {
    return positiveInteger(fallback, 1, max);
  }
}

function positiveInteger(value, fallback, max) {
  const number = Number(value);
  if (!Number.isFinite(number)) return fallback;
  return Math.max(1, Math.min(max, Math.round(number)));
}

function nonNegativeInteger(value, fallback, max) {
  const number = Number(value);
  if (!Number.isFinite(number)) return fallback;
  return Math.max(0, Math.min(max, Math.round(number)));
}

function finiteNumber(value, fallback) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function normalizeGiftText(value) {
  return String(value ?? "").trim().toLocaleLowerCase();
}

function asString(value) {
  return typeof value === "string" ? value : "";
}

function findRelationship(data, relationshipId) {
  const index = findRelationshipIndex(data, relationshipId);
  return data.relationships[index];
}

function findRelationshipIndex(data, relationshipId) {
  const index = data.relationships.findIndex((relationship) => relationship.id === relationshipId);
  if (index < 0) throw new Error(`Relationship not found: ${relationshipId}`);
  return index;
}

function findEventIndex(relationship, eventId) {
  const index = relationship.events.findIndex((event) => event.id === eventId);
  if (index < 0) throw new Error(`Relationship event not found: ${eventId}`);
  return index;
}

function notifyRelationshipDataChanged(actor, data) {
  if (typeof Hooks !== "undefined" && typeof Hooks.callAll === "function") {
    Hooks.callAll(`${MODULE_ID}.relationshipDataChanged`, actor, data);
  }
}
