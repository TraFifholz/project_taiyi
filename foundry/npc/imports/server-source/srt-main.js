import { MODULE_ID, MODULE_NAME } from "./core/constants.js";
import { preloadRelationshipSfx, registerRelationshipAudioSettings } from "./core/audio.js";
import { getRelationshipThemeTemplates } from "./core/theme-registry.js";
import { RelationshipTrackerApp } from "./apps/RelationshipTrackerApp.js";
import { ActorPickerApp, registerActorPickerSettings } from "./apps/ActorPickerApp.js";
import { RelationshipManagerApp } from "./apps/RelationshipManagerApp.js";
import { QuickRelationshipPanelApp } from "./apps/QuickRelationshipPanelApp.js";
import { registerRelationshipSettingsMenu } from "./apps/RelationshipSettingsApp.js";
import { RankUpOverlay } from "./apps/RankUpOverlay.js";
import { GiftReactionOverlay } from "./apps/GiftReactionOverlay.js";
import { GiftApprovalApp } from "./apps/GiftApprovalApp.js";
import {
  canEditRelationships,
  canViewRelationships,
  registerPermissionSettings,
  runPlayerPermissionSettingsMigration
} from "./core/permissions.js";
import { registerGiftItemTypeFilterSetting } from "./core/gift-item-filter.js";
import { registerRelationshipPresetSettings } from "./core/relationship-presets.js";
import { registerRelationshipAppearanceSettings } from "./core/relationship-appearance.js";
import { registerWorldProfileDefaultSettings } from "./core/profile-defaults.js";
import { registerRankCutinTextSettings } from "./core/theme-copy.js";
import { registerThemeFontOverrideSetting } from "./core/theme-fonts.js";
import {
  adjustRelationshipProgress,
  adjustRelationshipProgressSafe,
  creditRelationshipProgress,
  getRelationshipProgress,
  listRelationshipProgress,
  RELATIONSHIP_PROGRESS_API_HOOKS
} from "./core/relationship-progress-api.js";
import {
  registerGiftApprovalCancellation,
  registerGiftApprovalPrompt,
  registerGiftApprovalResultDisplay,
  registerGiftReactionDisplay,
  registerRankUpOverlayDisplay,
  registerRelationshipSocket,
  resumePendingGiftApprovals
} from "./core/socket.js";
import {
  registerRelationshipMenuExtensionHooks,
  registerRelationshipMenuProvider
} from "./menu-extension.js";

const ARCHIVE_HEADER_ACTION = "srtOpenRelationshipArchive";
const MANAGER_HEADER_ACTION = "srtOpenRelationshipManager";
const ARCHIVE_HEADER_CLASS = `${MODULE_ID}-archive`;
const MANAGER_HEADER_CLASS = `${MODULE_ID}-manager`;
const ARCHIVE_TOOL = "open-relationship-archive";
const MANAGER_TOOL = "open-relationship-manager";
const QUICK_TOOL = "open-quick-relationship-panel";
const SELECT_TOOL = "select";
const TARGET_TOOL = "target";
const pendingActorSyncs = new Map();
const pendingRelationshipProgressNotifications = new Set();

_registerSceneControlButton();
_registerActorSheetHeaderButtons();
registerRelationshipMenuExtensionHooks();

Hooks.once("init", async () => {
  console.log(`${MODULE_NAME} | Initializing`);
  registerPermissionSettings();
  registerActorPickerSettings();
  registerRelationshipAppearanceSettings({ onChange: _syncRelationshipAppearanceChange });
  registerWorldProfileDefaultSettings({ onChange: _syncWorldProfileDefaultsChange });
  registerRankCutinTextSettings({ onChange: _syncWorldProfileDefaultsChange });
  registerThemeFontOverrideSetting({ onChange: _syncRelationshipAppearanceChange });
  registerGiftItemTypeFilterSetting({ onChange: _syncGiftItemTypeFilterChange });
  registerRelationshipAudioSettings();
  registerRelationshipPresetSettings();
  registerRelationshipSettingsMenu();
  registerRankUpOverlayDisplay((payload) => {
    if (RelationshipTrackerApp.shouldShowGlobalRankUpOverlay(payload)) RankUpOverlay.show(payload);
  });
  registerGiftReactionDisplay((payload) => {
    const releaseRankCutins = RankUpOverlay.hold();
    const shown = GiftReactionOverlay.show(payload);
    if (!shown) {
      releaseRankCutins();
      return false;
    }
    void GiftReactionOverlay.whenIdle().finally(releaseRankCutins);
    return true;
  });
  registerGiftApprovalPrompt((payload) => GiftApprovalApp.request(payload));
  registerGiftApprovalCancellation((requestId, status) => GiftApprovalApp.cancel(requestId, status));
  registerGiftApprovalResultDisplay((notice) => {
    const key = `STYLISH_RELATIONSHIP_TRACKER.giftApproval.playerResult.${notice.status}`;
    const message = game.i18n.format(key, {
      item: notice.itemName || game.i18n.localize("STYLISH_RELATIONSHIP_TRACKER.editor.gift.genericItem"),
      target: notice.targetName || "???"
    });
    const level = notice.status === "approved"
      ? "info"
      : (notice.status === "failed" ? "error" : "warn");
    ui.notifications?.[level]?.(message);
    return true;
  });
  exposeModuleApi();
  registerRelationshipMenuProvider();

  await loadTemplates([
    ...getRelationshipThemeTemplates(),
    `modules/${MODULE_ID}/templates/app/actor-picker.hbs`,
    `modules/${MODULE_ID}/templates/app/manager.hbs`,
    `modules/${MODULE_ID}/templates/app/quick-panel.hbs`,
    `modules/${MODULE_ID}/templates/app/relationship-settings.hbs`,
    `modules/${MODULE_ID}/templates/app/relationship-sync-dialog.hbs`,
    `modules/${MODULE_ID}/templates/app/gift-approval.hbs`,
    `modules/${MODULE_ID}/templates/app/note-editor-dialog.hbs`
  ]);
});

Hooks.once("ready", () => {
  registerRelationshipSocket();
  preloadRelationshipSfx();
  // World-scope writes: only a GM may convert the legacy permission settings.
  if (game.user?.isGM === true) void runPlayerPermissionSettingsMigration();
  void resumePendingGiftApprovals();
  console.log(`${MODULE_NAME} | Ready`);
});

Hooks.on("userConnected", () => {
  void resumePendingGiftApprovals();
});

function exposeModuleApi() {
  const moduleData = game.modules.get(MODULE_ID);
  if (!moduleData) return;
  moduleData.api = {
    open: (actorOrUuid = null) => actorOrUuid
      ? RelationshipTrackerApp.openForActor(actorOrUuid)
      : ActorPickerApp.open(),
    /** Open the Actor picker explicitly. */
    openPicker: () => ActorPickerApp.open(),
    /** Resolve an Actor (or UUID) and open its relationship archive directly. */
    selectActor: (actorOrUuid, options = {}) => RelationshipTrackerApp.openForActor(actorOrUuid, options),
    openForActor: (actorOrUuid, options = {}) => RelationshipTrackerApp.openForActor(actorOrUuid, options),
    /** Open the GM/admin Relationship Manager, optionally for a given Actor and relationship. */
    openManager: (actorOrUuid = null, options = {}) => RelationshipManagerApp.open(actorOrUuid, options),
    /** Whether the current user may open the Relationship Manager for this Actor. */
    canOpenManager: (actor) => actor?.documentName === "Actor"
      && canEditRelationships(game.user, actor),
    /** Open the token-target based compact interaction panel. */
    openQuickPanel: () => QuickRelationshipPanelApp.open(),
    /** Show the global rank-up cut-in overlay directly (macro/QA use). */
    showRankUp: (payload) => RankUpOverlay.show(payload),
    /** Read progress-only Relationship projections filtered for one User. */
    listRelationshipProgress,
    /** Resolve one visible Relationship progress projection by id or target. */
    getRelationshipProgress,
    /** Apply a signed progress delta. The active GM is the sole write authority. */
    adjustRelationshipProgress,
    /** Apply a signed progress delta while suppressing every Rank Macro trigger. */
    adjustRelationshipProgressSafe,
    /** Credit one absolute external source cursor idempotently. */
    creditRelationshipProgress,
    /** Payload-safe integration hooks. */
    HOOKS: RELATIONSHIP_PROGRESS_API_HOOKS,
    /** Direct access to the app classes for advanced/macro use. */
    RelationshipTrackerApp,
    ActorPickerApp,
    RelationshipManagerApp,
    QuickRelationshipPanelApp,
    GiftApprovalApp,
    RankUpOverlay
  };
}

Hooks.on(`${MODULE_ID}.relationshipDataChanged`, (actor, data) => {
  _scheduleRelationshipProgressNotification(actor);
  _scheduleActorSync(actor, data);
});

Hooks.on("updateActor", (actor, changes) => {
  const app = RelationshipTrackerApp.getOpenInstance();
  const manager = RelationshipManagerApp.getOpenInstance();
  QuickRelationshipPanelApp.getOpenInstance()?.refreshActor(actor);
  const relationshipFlagChanged = _hasRelationshipFlagChange(changes);
  if (relationshipFlagChanged) _scheduleRelationshipProgressNotification(actor);
  const referencedActorChanged = (
    app?.referencesActor?.(actor) === true
    || manager?.referencesActor?.(actor) === true
  )
    && _hasReferencedActorPresentationChange(changes);
  if (!relationshipFlagChanged && !referencedActorChanged) return;
  _scheduleActorSync(actor, null);
});

for (const hookName of ["createItem", "updateItem", "deleteItem"]) {
  Hooks.on(hookName, (item) => {
    const actor = item?.parent;
    const app = RelationshipTrackerApp.getOpenInstance();
    const manager = RelationshipManagerApp.getOpenInstance();
    if (actor?.documentName === "Actor" && app?.isShowingActor?.(actor)) {
      void app.syncGiftInventoryChange(actor);
    }
    if (actor?.documentName === "Actor" && manager?.isUsingGiftInventoryActor?.(actor)) {
      manager.syncGiftInventoryChange(actor);
    }
    if (actor?.documentName === "Actor") QuickRelationshipPanelApp.getOpenInstance()?.refreshActor(actor);
  });
}

function _syncGiftItemTypeFilterChange() {
  RelationshipTrackerApp.getOpenInstance()?.syncGiftItemFilterChange?.();
  RelationshipManagerApp.getOpenInstance()?.syncGiftItemFilterChange?.();
  QuickRelationshipPanelApp.getOpenInstance()?.refreshFromCanvas?.();
}

function _syncRelationshipAppearanceChange() {
  void RelationshipTrackerApp.getOpenInstance()?.render({ force: false });
  void RelationshipManagerApp.getOpenInstance()?.render({ force: false });
  QuickRelationshipPanelApp.getOpenInstance()?.refreshFromCanvas?.();
  GiftApprovalApp.refreshAppearance();
}

function _syncWorldProfileDefaultsChange() {
  void RelationshipTrackerApp.getOpenInstance()?.render({ force: false });
  void RelationshipManagerApp.getOpenInstance()?.syncExternalDataChange();
  void ActorPickerApp.getOpenInstance()?.render({ force: false });
  QuickRelationshipPanelApp.getOpenInstance()?.refreshFromCanvas?.();
}

Hooks.on("targetToken", (user) => {
  if (user?.id !== globalThis.game?.user?.id) return;
  QuickRelationshipPanelApp.getOpenInstance()?.adoptCanvasTarget();
});
Hooks.on("controlToken", (token, controlled) => {
  if (controlled) {
    const actor = token?.actor ?? token?.document?.actor ?? null;
    QuickRelationshipPanelApp.rememberOwnerActor(actor);
  }
  const app = QuickRelationshipPanelApp.getOpenInstance();
  if (controlled) app?.adoptCanvasOwner();
  else app?.refreshFromCanvas();
});
Hooks.on("canvasReady", () => QuickRelationshipPanelApp.resetRememberedOwner());

function _activeSceneControlName() {
  const controls = globalThis.ui?.controls;
  const active = controls?.control ?? controls?.activeControl ?? null;
  return typeof active === "string" ? active : active?.name;
}

async function _activateRelationshipTokenLayer(event, active) {
  if (active === false) return;
  const tokenLayer = globalThis.canvas?.tokens;
  const sceneControls = globalThis.ui?.controls;
  try {
    if (tokenLayer && tokenLayer.active !== true) await tokenLayer.activate();
    if (_activeSceneControlName() === MODULE_ID) return;
    if (typeof sceneControls?.activate === "function") {
      await sceneControls.activate({ control: MODULE_ID, tool: SELECT_TOOL, event });
    }
  } catch (error) {
    console.warn(`${MODULE_ID} | Could not activate relationship token selection`, error);
  }
}

function _scheduleActorSync(actor, data = null) {
  const actorUuid = actor?.uuid;
  if (!actorUuid) return;
  const existing = pendingActorSyncs.get(actorUuid);
  if (existing) {
    if (data) existing.data = data;
    return;
  }

  const pending = { actor, data };
  pendingActorSyncs.set(actorUuid, pending);
  setTimeout(() => {
    const queued = pendingActorSyncs.get(actorUuid);
    if (!queued) return;
    pendingActorSyncs.delete(actorUuid);

    const manager = RelationshipManagerApp.getOpenInstance();
    if (manager?.isForActor?.(queued.actor) || manager?.referencesActor?.(queued.actor)) {
      void manager.syncExternalDataChange();
    }

    const app = RelationshipTrackerApp.getOpenInstance();
    const isOwner = app?.isForActor?.(queued.actor) === true;
    if (isOwner || app?.referencesActor?.(queued.actor) === true) {
      void app.syncExternalDataChange(isOwner ? queued.data : null);
    }
  }, 0);
}

/**
 * Coalesce the private local write hook and Foundry's cross-client updateActor
 * hook into one payload-safe invalidation per Actor per event-loop turn.
 */
function _scheduleRelationshipProgressNotification(actor) {
  const ownerActorUuid = actor?.uuid;
  if (!ownerActorUuid || pendingRelationshipProgressNotifications.has(ownerActorUuid)) return;
  pendingRelationshipProgressNotifications.add(ownerActorUuid);
  setTimeout(() => {
    pendingRelationshipProgressNotifications.delete(ownerActorUuid);
    Hooks.callAll(
      RELATIONSHIP_PROGRESS_API_HOOKS.RELATIONSHIP_PROGRESS_CHANGED,
      { ownerActorUuid }
    );
  }, 0);
}

function _hasRelationshipFlagChange(changes) {
  if (!changes || typeof changes !== "object") return false;
  const path = `flags.${MODULE_ID}.relationshipData`;
  if (Object.prototype.hasOwnProperty.call(changes, path)) return true;
  if (globalThis.foundry?.utils?.hasProperty?.(changes, path)) return true;
  const scoped = changes.flags?.[MODULE_ID];
  return !!scoped && (
    Object.prototype.hasOwnProperty.call(scoped, "relationshipData")
    || Object.prototype.hasOwnProperty.call(scoped, "-=relationshipData")
  );
}

function _hasReferencedActorPresentationChange(changes) {
  if (!changes || typeof changes !== "object") return false;
  const directKeys = ["name", "img", "prototypeToken", "prototypeToken.texture.src"];
  if (directKeys.some((key) => Object.prototype.hasOwnProperty.call(changes, key))) return true;
  if (changes.prototypeToken?.texture?.src !== undefined) return true;
  const flagPath = `flags.${MODULE_ID}`;
  if (Object.keys(changes).some((key) => key === flagPath || key.startsWith(`${flagPath}.`))) return true;
  return !!changes.flags?.[MODULE_ID];
}

function _registerSceneControlButton() {
  Hooks.on("getSceneControlButtons", (controls) => {
    if (Array.isArray(controls)) {
      _registerLegacySceneControlButton(controls);
      return;
    }

    if (controls[MODULE_ID]) return;

    const tokenControl = controls.tokens ?? null;
    const nativeSelectTool = tokenControl?.tools?.select ?? {};
    const nativeTargetTool = tokenControl?.tools?.target ?? {};

    const controlOrder = Math.max(
      0,
      ...Object.values(controls).map((control) => Number(control.order) || 0)
    ) + 1;

    controls[MODULE_ID] = {
      name: MODULE_ID,
      title: game.i18n.localize("STYLISH_RELATIONSHIP_TRACKER.sidebar.quickPanelSelect"),
      icon: "fas fa-heart",
      order: controlOrder,
      activeTool: SELECT_TOOL,
      onChange: _activateRelationshipTokenLayer,
      onToolChange: tokenControl?.onToolChange,
      tools: {
        [SELECT_TOOL]: {
          ...nativeSelectTool,
          name: SELECT_TOOL,
          title: game.i18n.localize("STYLISH_RELATIONSHIP_TRACKER.sidebar.quickPanelOwnerSelect"),
          icon: "fas fa-user-check",
          order: 0,
          active: true,
          button: false
        },
        [TARGET_TOOL]: {
          ...nativeTargetTool,
          name: TARGET_TOOL,
          title: game.i18n.localize("STYLISH_RELATIONSHIP_TRACKER.sidebar.quickPanelTargetSelect"),
          icon: "fas fa-bullseye",
          order: 1,
          button: false
        },
        [ARCHIVE_TOOL]: {
          name: ARCHIVE_TOOL,
          title: game.i18n.localize("STYLISH_RELATIONSHIP_TRACKER.sidebar.relationshipArchive"),
          icon: "fas fa-heart",
          button: true,
          order: 2,
          onChange: (_event, active) => {
            if (active === false) return;
            ActorPickerApp.open();
          }
        },
        [QUICK_TOOL]: {
          name: QUICK_TOOL,
          title: game.i18n.localize("STYLISH_RELATIONSHIP_TRACKER.sidebar.quickPanel"),
          icon: "fas fa-bolt",
          button: true,
          order: 3,
          onChange: (_event, active) => {
            if (active === false) return;
            QuickRelationshipPanelApp.open();
          }
        }
      }
    };

    if (game.user?.isGM === true) {
      controls[MODULE_ID].tools[MANAGER_TOOL] = {
        name: MANAGER_TOOL,
        title: game.i18n.localize("STYLISH_RELATIONSHIP_TRACKER.sidebar.relationshipManager"),
        icon: "fas fa-sliders",
        button: true,
        order: 4,
        onChange: (_event, active) => {
          if (active === false) return;
          RelationshipManagerApp.open();
        }
      };
    }
  });
}

function _registerLegacySceneControlButton(controls) {
  if (controls.some(control => control.name === MODULE_ID)) return;

  const tools = [{
    name: SELECT_TOOL,
    title: game.i18n.localize("STYLISH_RELATIONSHIP_TRACKER.sidebar.quickPanelOwnerSelect"),
    icon: "fas fa-user-check"
  }, {
    name: TARGET_TOOL,
    title: game.i18n.localize("STYLISH_RELATIONSHIP_TRACKER.sidebar.quickPanelTargetSelect"),
    icon: "fas fa-bullseye"
  }, {
    name: ARCHIVE_TOOL,
    title: game.i18n.localize("STYLISH_RELATIONSHIP_TRACKER.sidebar.relationshipArchive"),
    icon: "fas fa-heart",
    button: true,
    onClick: () => ActorPickerApp.open()
  }, {
    name: QUICK_TOOL,
    title: game.i18n.localize("STYLISH_RELATIONSHIP_TRACKER.sidebar.quickPanel"),
    icon: "fas fa-bolt",
    button: true,
    onClick: () => QuickRelationshipPanelApp.open()
  }];

  if (game.user?.isGM === true) {
    tools.push({
      name: MANAGER_TOOL,
      title: game.i18n.localize("STYLISH_RELATIONSHIP_TRACKER.sidebar.relationshipManager"),
      icon: "fas fa-sliders",
      button: true,
      onClick: () => RelationshipManagerApp.open()
    });
  }

  controls.push({
    name: MODULE_ID,
    title: game.i18n.localize("STYLISH_RELATIONSHIP_TRACKER.sidebar.quickPanelSelect"),
    icon: "fas fa-heart",
    layer: "TokenLayer",
    activeTool: SELECT_TOOL,
    tools
  });
}

function _registerActorSheetHeaderButtons() {
  Hooks.on("getActorSheetHeaderButtons", (app, buttons) => {
    const actor = _getActorFromSheet(app);
    if (!actor || actor.documentName !== "Actor") return;

    const user = typeof game !== "undefined" ? game.user : null;
    if (canEditRelationships(user, actor) && !buttons.some(button => button.class === MANAGER_HEADER_CLASS)) {
      buttons.unshift({
        class: MANAGER_HEADER_CLASS,
        icon: "fas fa-sliders",
        label: game.i18n.localize("STYLISH_RELATIONSHIP_TRACKER.sidebar.relationshipManager"),
        onclick: () => RelationshipManagerApp.open(actor)
      });
    }

    if (!canViewRelationships(user, actor)) return;
    if (buttons.some(button => button.class === ARCHIVE_HEADER_CLASS)) return;
    buttons.unshift({
      class: ARCHIVE_HEADER_CLASS,
      icon: "fas fa-heart",
      label: game.i18n.localize("STYLISH_RELATIONSHIP_TRACKER.sidebar.relationshipArchive"),
      onclick: () => RelationshipTrackerApp.openForActor(actor)
    });
  });

  Hooks.on("getHeaderControlsApplicationV2", (app, controls) => {
    const actor = _getActorFromSheet(app);
    if (!actor || actor.documentName !== "Actor") return;
    if (!Array.isArray(controls)) return;

    const user = typeof game !== "undefined" ? game.user : null;
    app.options.actions ??= {};

    if (canEditRelationships(user, actor) && !controls.some(control => control.action === MANAGER_HEADER_ACTION)) {
      app.options.actions[MANAGER_HEADER_ACTION] ??= function () {
        return RelationshipManagerApp.open(_getActorFromSheet(this));
      };
      controls.unshift({
        action: MANAGER_HEADER_ACTION,
        icon: "fas fa-sliders",
        label: game.i18n.localize("STYLISH_RELATIONSHIP_TRACKER.sidebar.relationshipManager")
      });
    }

    if (!canViewRelationships(user, actor) || controls.some(control => control.action === ARCHIVE_HEADER_ACTION)) return;
    app.options.actions[ARCHIVE_HEADER_ACTION] ??= function () {
      return RelationshipTrackerApp.openForActor(_getActorFromSheet(this));
    };
    controls.unshift({
      action: ARCHIVE_HEADER_ACTION,
      icon: "fas fa-heart",
      label: game.i18n.localize("STYLISH_RELATIONSHIP_TRACKER.sidebar.relationshipArchive")
    });
  });
}

function _getActorFromSheet(app) {
  return app?.document ?? app?.actor ?? null;
}
