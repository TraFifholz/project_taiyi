import { DEFAULT_RANK_STEPS, EVENT_RANK_CHANGES, GIFT_PREFERENCE_VISIBILITY, MAP_VISIBILITY_MODES, MODULE_ID, MOMENT_TYPES, PROFILE_DEFAULTS } from "../core/constants.js";
import { relationshipTerminology } from "../core/terminology.js";
import { resolveActor, resolveOwnerActor, resolveRelationshipActors } from "../core/actor-resolver.js";
import { getRelationshipData } from "../core/relationships.js";
import { giveGift, previewGift, rankRelationship, unlockRelationship } from "../core/relationship-operations.js";
import { SETTING_GIFT_DEFAULT_MAX_QUANTITY_PER_GIFT, canEditRelationships, canGiveGift, canUsePlayerRankControls, canViewRelationships, sanitizeRelationshipDataForUser } from "../core/permissions.js";
import { canUnlockRelationshipWithGift, isEventRevealedAtRank } from "../core/data-model.js";
import { buildGiftEventView } from "../core/gift-rendering.js";
import { buildGiftDialogPayload, buildGiftGiverItemOptions, buildGiftItemCatalog, buildGiftPreferenceView, hasGiftableGiverItems, resolveGiftDialogPolicy, resolveGiftGiftability } from "../core/gift-dialog.js";
import { enrichHtml } from "../core/rich-text.js";
import {
  RELATIONSHIP_LIST_KINDS,
  normalizeRelationshipListKind,
  relationshipListKindFor,
  relationshipsForListKind
} from "../core/relationship-list-filter.js";
import { getRelationshipTheme } from "../core/theme-registry.js";
import { resolveWorldProfileDefaults } from "../core/profile-defaults.js";
import { applyFontOverridesToSubtree, applyThemeFontOverrides } from "../core/theme-fonts.js";
import { SFX_KEYS, playRelationshipSfx } from "../core/audio.js";
import { GiftReactionOverlay } from "./GiftReactionOverlay.js";
import { RankUpOverlay } from "./RankUpOverlay.js";
import { RELATIONSHIP_CLASSES } from "../data/relationship-classes.js";
import {
  RelationshipMapDomUpdater,
  buildRankProgressView,
  detectMapRankIncrease,
  detectMapRankProgressDelta,
  rankStrokeWidth
} from "./relationship-map-dom-updater.js";
import {
  canMoveRelationshipAxis,
  isNegativeRelationship,
  relationshipEffectivePolarity,
  relationshipPaddedRankDisplay,
  relationshipRankDisplay,
  relationshipSignedRank
} from "../core/relationship-polarity.js";
import { resolveRelationshipAccent } from "../core/relationship-appearance.js";
import {
  hasCustomMapInspectorFrame,
  hasCustomMapThumbnailFrame,
  isGeneratedMapThumbnailPath,
  normalizeMapInspectorFrame,
  normalizeMapThumbnailFrame,
  resolveRelationshipMapImage,
  resolveRelationshipMapInspectorImage
} from "../core/map-thumbnail.js";

const { ApplicationV2, HandlebarsApplicationMixin } = foundry.applications.api;

/** Single open instance tracker (Stylish Shop pattern). */
let _openInstance = null;

/** Independent fallback accent when a relationship has no valid `#RRGGBB`. */
const DEFAULT_ACCENT = "#FF2E63";

/**
 * Constellation map world layer. The pannable world is a fixed-px box ~2x the
 * visible viewport (.srt-map-area); the focus actor sits at world center, hop-1
 * relationships fan on an ellipse around it, and hop-2 nodes fan outward from
 * their hop-1 parent. SVG link geometry uses these world coordinates; node DOM
 * positions are absolute px inside .srt-map-world.
 */
const MAP_WORLD_W = 2440;
const MAP_WORLD_H = 1680;
const MAP_FOCUS = Object.freeze({ x: MAP_WORLD_W / 2, y: MAP_WORLD_H / 2 });

/** Map zoom bounds and per-step delta for wheel/controls; default zoom is 1 (100%). */
const MAP_ZOOM_MIN = 0.6;
const MAP_ZOOM_MAX = 2.4;
const MAP_ZOOM_STEP = 0.2;

/** Hop-1 ring radii (ellipse) and hop-2 fan geometry around each parent. */
const HOP1_RADIUS_X = 600;
const HOP1_RADIUS_Y = 470;
const HOP2_RADIUS = 215;
const HOP2_FAN_DEG = 26;

const APP_VIEWS = Object.freeze({
  ARCHIVE: "archive",
  MAP: "map"
});

/** Shared constellation renderer; relationship themes only provide its entry point. */
const SHARED_MAP_THEME_ID = "archive";

const TRACKER_ACTION_SFX = Object.freeze({
  selectRelationship: SFX_KEYS.PAGE,
  selectRelationshipListTab: SFX_KEYS.SELECT,
  cyclePrev: SFX_KEYS.PAGE,
  cycleNext: SFX_KEYS.PAGE,
  toggleView: SFX_KEYS.MAP_VIEW,
  focusNode: SFX_KEYS.MAP_FOCUS,
  focusBack: SFX_KEYS.MAP_FOCUS,
  mapZoomIn: SFX_KEYS.MAP_ZOOM,
  mapZoomOut: SFX_KEYS.MAP_ZOOM,
  mapZoomReset: SFX_KEYS.MAP_ZOOM,
  openSceneRecall: SFX_KEYS.PAGE,
  closeSceneRecall: SFX_KEYS.PAGE,
  openDossier: SFX_KEYS.PAGE,
  closeDossier: SFX_KEYS.PAGE,
  selectDossierTab: SFX_KEYS.SELECT,
  openEventLog: SFX_KEYS.PAGE,
  closeEventLog: SFX_KEYS.PAGE,
  openGiftDialog: SFX_KEYS.PAGE,
  closeGiftDialog: SFX_KEYS.PAGE,
  selectGiftItem: SFX_KEYS.SELECT,
  giftPagePrev: SFX_KEYS.PAGE,
  giftPageNext: SFX_KEYS.PAGE,
  clearGiftSearch: SFX_KEYS.SELECT,
  submitGift: SFX_KEYS.SELECT,
  dismissMoment: SFX_KEYS.SELECT,
  closeApp: SFX_KEYS.SELECT,
  toggleFullscreen: SFX_KEYS.SELECT,
  rankUp: SFX_KEYS.BOND_CHANGE,
  rankDown: SFX_KEYS.BOND_CHANGE,
  unlockBond: SFX_KEYS.BOND_CHANGE
});

const BACKDROP_CLOSE_ACTIONS = new Set(["closeSceneRecall", "closeDossier", "closeEventLog", "closeGiftDialog"]);

/** Gift dialog disabled-reason -> existing editor.gift.* hint i18n suffix. */
const GIFT_DISABLED_HINT_KEYS = Object.freeze({
  deny: "denyHint",
  locked: "lockedHint",
  disabled: "disabledHint",
  max: "maxHint",
  noItems: "noItems"
});
const GIFT_CATALOG_PAGE_SIZE = 8;
const GIFT_SEARCH_RENDER_DELAY_MS = 140;
const GIFT_PREVIEW_DELAY_MS = 180;
const OVERLAY_PANEL_SELECTOR = ".srt-scene-panel, .srt-dp-scene-panel, .srt-jr-scene-panel, .srt-ag-scene-panel, .srt-sl-scene-panel, .srt-al-scene-panel, .srt-dossier-panel, .srt-dp-dossier-panel, .srt-jr-dossier-panel, .srt-ag-dossier-panel, .srt-sl-dossier-panel, .srt-al-dossier-panel, .srt-eventlog-panel, .srt-dp-eventlog-panel, .srt-jr-eventlog-panel, .srt-ag-eventlog-panel, .srt-sl-eventlog-panel, .srt-al-eventlog-panel, .srt-gift-panel";

/**
 * Owner-scoped, never-persisted draft injected for live preview (Stylish Shop pattern).
 * @type {{ownerActorUuid: string, data: {profile: object, relationships: object[]}}|null}
 */
let _previewOverride = null;

/** Convert a #rrggbb hex to a soft rgba wash string (prototype hexToSoft). */
function hexToSoft(hex, alpha = 0.22) {
  const safe = /^#[0-9a-fA-F]{6}$/.test(hex) ? hex : "#FF2E63";
  const n = parseInt(safe.slice(1), 16);
  const r = (n >> 16) & 0xff;
  const g = (n >> 8) & 0xff;
  const b = n & 0xff;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

export class RelationshipTrackerApp extends HandlebarsApplicationMixin(ApplicationV2) {

  /** @type {{classes: object[], relationships: object[], profile: object}} */
  #data = { classes: RELATIONSHIP_CLASSES, profile: { ...PROFILE_DEFAULTS }, relationships: [] };

  #ownerActor = null;

  #ownerActorUuid = null;

  #missingActorWarned = false;

  /** @type {string|null} */
  #activeRelationshipId = null;

  /** @type {"people"|"organizations"} */
  #relationshipListKind = RELATIONSHIP_LIST_KINDS.PEOPLE;

  /** Map focus actor (defaults to owner). When moved, the map re-centers here. @type {string|null} */
  #focusActorUuid = null;

  /** @type {object|null} */
  #focusActor = null;

  /** Previous focus actor UUIDs for the back control. @type {string[]} */
  #focusStack = [];

  /** Selected relationship id within a non-owner focus dataset. @type {string|null} */
  #mapFocusActiveId = null;

  /** Resolved relationships of the current map focus actor (owner data when not moved). @type {object[]} */
  #focusRelationships = [];

  /** Actor the map controls act on (the focus actor). @type {object|null} */
  #mapControlActor = null;

  /** Pan offset of .srt-map-world in unscaled world px; updated on drag without re-render. */
  #mapPan = { x: 0, y: 0 };

  /** Map zoom multiplier applied to .srt-map-world via a CSS var; 1 = 100%. */
  #mapZoom = 1;

  /** True after a pan drag so the synthetic click is suppressed (click-vs-drag guard). */
  #mapDragMoved = false;

  /** @type {object|null} */
  #mapPointerHandlers = null;

  /** @type {{relationshipId: string, eventId: string}|null} */
  #sceneRecall = null;

  /** @type {{type: string, relationshipId: string, oldRank: number, newRank: number}|null} */
  #moment = null;

  /** Map-local rank-up FX target, separate from the global rank-up cut-in. @type {{relationshipId: string, at: number}|null} */
  #mapFx = null;

  /** @type {number|null} */
  #mapFxTimer = null;

  #fontFitRequestId = 0;

  /**
   * True while a local rankRelationship(...) call is persisting. The module fires
   * its relationshipDataChanged hook mid-persistence, so this guard lets the
   * hook-driven syncExternalDataChange skip the duplicate pass the local action
   * already handles itself (DOM patch in map view, render elsewhere).
   */
  #localRankChangeInProgress = false;

  #externalSyncPromise = null;

  #externalSyncQueued = false;

  #externalSyncQueuedData = null;

  /** Whether the dossier note overlay is open for the active relationship. */
  #dossierOpen = false;

  /** Selected dossier tab key ("player" | "gm"), validated against the active relationship each render. */
  #dossierTab = null;

  #eventLogOpen = false;

  /** Whether the player-facing Give Gift dialog is open for the active relationship. */
  #giftDialogOpen = false;

  #giftPreview = null;

  #giftPreviewPendingKey = null;

  #giftPreviewRequestId = 0;

  #giftPreviewTimer = null;

  #giftDraft = null;

  #giftItemQuery = "";

  #giftItemPage = 1;

  #giftSearchTimer = null;

  #giftInventoryRenderTimer = null;

  #deferredFocusSelector = null;

  #giftItemOptionsCache = null;

  #giftSubmitting = false;

  /** Active view layout: APP_VIEWS.ARCHIVE (list/detail) or APP_VIEWS.MAP (constellation). */
  #view = APP_VIEWS.ARCHIVE;

  /** Whether the next render should play the directional-wipe transition. */
  #animateNext = true;

  /** Whether the next render plays the Scene Recall entry; set only on explicit open so manager preview rerenders do not replay the slam. */
  #animateSceneNext = false;

  /** @type {boolean} */
  #isFullscreen = true;

  /** @type {ResizeObserver|null} */
  #resizeObserver = null;

  /** @type {MutationObserver|null} */
  #fontObserver = null;

  /** @type {Object<string, string>} */
  #activeFontOverrideMap = {};

  /** @type {Function|null} */
  #keydownHandler = null;

  #clickSfxHandler = null;

  /** @type {number|null} */
  #momentTimer = null;

  /** @override */
  static DEFAULT_OPTIONS = {
    id: "srt-relationship-tracker",
    classes: ["srt-app"],
    tag: "div",
    window: {
      frame: false,
      positioned: true,
      resizable: false,
      minimizable: false
    },
    position: {
      width: window.innerWidth,
      height: window.innerHeight,
      left: 0,
      top: 0
    },
    actions: {
      selectRelationship: RelationshipTrackerApp.#onSelectRelationship,
      selectRelationshipListTab: RelationshipTrackerApp.#onSelectRelationshipListTab,
      cyclePrev: RelationshipTrackerApp.#onCyclePrev,
      cycleNext: RelationshipTrackerApp.#onCycleNext,
      rankUp: RelationshipTrackerApp.#onRankUp,
      rankDown: RelationshipTrackerApp.#onRankDown,
      unlockBond: RelationshipTrackerApp.#onUnlockBond,
      openSceneRecall: RelationshipTrackerApp.#onOpenSceneRecall,
      closeSceneRecall: RelationshipTrackerApp.#onCloseSceneRecall,
      dismissMoment: RelationshipTrackerApp.#onDismissMoment,
      openDossier: RelationshipTrackerApp.#onOpenDossier,
      closeDossier: RelationshipTrackerApp.#onCloseDossier,
      selectDossierTab: RelationshipTrackerApp.#onSelectDossierTab,
      openEventLog: RelationshipTrackerApp.#onOpenEventLog,
      closeEventLog: RelationshipTrackerApp.#onCloseEventLog,
      openGiftDialog: RelationshipTrackerApp.#onOpenGiftDialog,
      closeGiftDialog: RelationshipTrackerApp.#onCloseGiftDialog,
      selectGiftItem: RelationshipTrackerApp.#onSelectGiftItem,
      giftPagePrev: RelationshipTrackerApp.#onGiftPagePrev,
      giftPageNext: RelationshipTrackerApp.#onGiftPageNext,
      clearGiftSearch: RelationshipTrackerApp.#onClearGiftSearch,
      submitGift: RelationshipTrackerApp.#onSubmitGift,
      closeApp: RelationshipTrackerApp.#onCloseApp,
      toggleFullscreen: RelationshipTrackerApp.#onToggleFullscreen,
      toggleView: RelationshipTrackerApp.#onToggleView,
      openManager: RelationshipTrackerApp.#onOpenManager,
      focusNode: RelationshipTrackerApp.#onFocusNode,
      focusBack: RelationshipTrackerApp.#onFocusBack,
      mapZoomIn: RelationshipTrackerApp.#onMapZoomIn,
      mapZoomOut: RelationshipTrackerApp.#onMapZoomOut,
      mapZoomReset: RelationshipTrackerApp.#onMapZoomReset
    }
  };

  /** @override */
  static PARTS = {};

  constructor(options = {}) {
    const { ownerActor = null, ...applicationOptions } = options;
    super(applicationOptions);
    this.#ownerActor = ownerActor;
    this.#ownerActorUuid = ownerActor?.uuid ?? null;
  }

  #currentTheme(themeId = this.#data?.profile?.themeId) {
    return getRelationshipTheme(themeId);
  }

  #themeContext(theme) {
    return {
      id: theme.id,
      labelKey: theme.labelKey,
      stageClass: theme.stageClass,
      capabilities: theme.capabilities ?? {},
      designWidth: theme.designWidth,
      designHeight: theme.designHeight
    };
  }

  /* ---------------------------------------------------------------- */
  /*  Selection helpers                                               */
  /* ---------------------------------------------------------------- */

  #relationships() {
    return this.#data.relationships;
  }

  #listRelationships() {
    return relationshipsForListKind(this.#relationships(), this.#relationshipListKind);
  }

  #syncRelationshipListKind() {
    const rels = this.#relationships();
    const active = rels.find(rel => rel.id === this.#activeRelationshipId);
    if (active) this.#relationshipListKind = relationshipListKindFor(active);

    let filtered = relationshipsForListKind(rels, this.#relationshipListKind);
    if (filtered.length > 0 || rels.length === 0) return filtered;

    this.#relationshipListKind = this.#relationshipListKind === RELATIONSHIP_LIST_KINDS.ORGANIZATIONS
      ? RELATIONSHIP_LIST_KINDS.PEOPLE
      : RELATIONSHIP_LIST_KINDS.ORGANIZATIONS;
    filtered = relationshipsForListKind(rels, this.#relationshipListKind);
    return filtered;
  }

  #buildRelationshipListContext(rels) {
    const people = relationshipsForListKind(rels, RELATIONSHIP_LIST_KINDS.PEOPLE);
    const organizations = relationshipsForListKind(rels, RELATIONSHIP_LIST_KINDS.ORGANIZATIONS);
    const current = relationshipsForListKind(rels, this.#relationshipListKind);
    const isOrganization = this.#relationshipListKind === RELATIONSHIP_LIST_KINDS.ORGANIZATIONS;
    const suffix = isOrganization ? "organizations" : "people";
    return {
      kind: this.#relationshipListKind,
      isOrganization,
      title: this.#localize(`STYLISH_RELATIONSHIP_TRACKER.list.${suffix}Title`),
      subtitle: this.#localize(`STYLISH_RELATIONSHIP_TRACKER.list.${suffix}Subtitle`),
      activeLabel: this.#localize(`STYLISH_RELATIONSHIP_TRACKER.list.${suffix}Active`),
      emptyTitle: this.#localize(`STYLISH_RELATIONSHIP_TRACKER.list.${suffix}Empty`),
      emptyHint: this.#localize(`STYLISH_RELATIONSHIP_TRACKER.list.${suffix}EmptyHint`),
      count: current.length,
      unlockedCount: current.filter(rel => !rel.locked).length,
      tabs: [
        {
          value: RELATIONSHIP_LIST_KINDS.PEOPLE,
          label: this.#localize("STYLISH_RELATIONSHIP_TRACKER.list.peopleTab"),
          count: people.length,
          active: !isOrganization,
          disabled: people.length === 0,
          isOrganization: false
        },
        {
          value: RELATIONSHIP_LIST_KINDS.ORGANIZATIONS,
          label: this.#localize("STYLISH_RELATIONSHIP_TRACKER.list.organizationsTab"),
          count: organizations.length,
          active: isOrganization,
          disabled: organizations.length === 0,
          isOrganization: true
        }
      ]
    };
  }

  #activeId() {
    const rels = this.#listRelationships();
    if (this.#activeRelationshipId && rels.some(r => r.id === this.#activeRelationshipId)) {
      return this.#activeRelationshipId;
    }
    const firstUnlocked = rels.find(r => !r.locked) ?? rels[0];
    return firstUnlocked?.id ?? null;
  }

  /** Raw relationship list backing the current view (focus actor in moved map, else owner). */
  #viewRelationships() {
    return this.#mapControlsActive() ? (this.#focusRelationships ?? []) : this.#relationships();
  }

  #viewActiveId() {
    return this.#mapControlsActive() ? this.#mapFocusActiveId : this.#activeId();
  }

  #viewActiveRelationship() {
    const id = this.#viewActiveId();
    return this.#viewRelationships().find(r => r.id === id) ?? null;
  }

  #categoryOf(rel) {
    return {
      categoryLabel: rel.categoryLabel || "",
      categoryLabelEn: rel.categoryLabelEn || ""
    };
  }

  #resolveAccent(rel) {
    return resolveRelationshipAccent(rel, DEFAULT_ACCENT);
  }

  #displayName(rel, category) {
    if (rel.customName) return rel.customName;
    if (rel.entryType === "actor" && rel._targetActorName) return rel._targetActorName;
    if (rel.entryType === "actor" && rel._targetActorMissing) return "???";
    return category.categoryLabel || "???";
  }

  #relationshipRole(rel) {
    return rel.customRole || "";
  }

  #relationshipPortrait(rel) {
    return rel.portrait || (rel.entryType === "actor" ? rel._targetActorImage : "") || "";
  }

  #relationshipListPortrait(rel) {
    return rel.listImage
      || rel.portrait
      || (rel.entryType === "actor" ? rel._targetTokenImage : "")
      || "";
  }

  #relationshipMapPortrait(rel) {
    return resolveRelationshipMapImage(rel, {
      portrait: this.#relationshipPortrait(rel),
      useThumbnails: this.#data.profile?.mapUseThumbnails !== false
    });
  }

  #relationshipMapInspectorPortrait(rel) {
    return resolveRelationshipMapInspectorImage(rel, {
      portrait: this.#relationshipPortrait(rel)
    });
  }

  /* ---------------------------------------------------------------- */
  /*  Context                                                         */
  /* ---------------------------------------------------------------- */

  /** @override */
  async _prepareContext(_options) {
    await this.#loadActorData();

    const profile = this.#localizedProfile(this.#data.profile);
    const terminology = this.#terminology(profile);
    const selectedTheme = this.#currentTheme(profile.themeId);
    const theme = this.#view === APP_VIEWS.MAP
      ? this.#currentTheme(SHARED_MAP_THEME_ID)
      : selectedTheme;
    const rels = this.#relationships();
    this.#syncRelationshipListKind();
    const activeId = this.#activeId();
    this.#activeRelationshipId = activeId;

    const unlockedRels = rels.filter(r => !r.locked);
    const totalRanks = unlockedRels.reduce(
      (sum, r) => sum + relationshipSignedRank(r),
      0
    );
    const maxRankTotal = unlockedRels.reduce(
      (sum, r) => sum + (Number(r.maxRank) || 0),
      0
    );
    const activeBondCount = unlockedRels.length;
    const maxRelationshipSlots = Math.max(1, Number(profile.maxRelationshipSlots) || rels.length || 1);

    const allRelationshipViews = await Promise.all(rels.map(r => this.#buildRelationshipView(r, r.id === activeId)));
    const relationships = relationshipsForListKind(allRelationshipViews, this.#relationshipListKind);
    const ownerActive = allRelationshipViews.find(r => r.id === activeId) ?? relationships[0] ?? null;

    const playTransition = this.#animateNext;
    this.#animateNext = false;
    const ownerCanManage = this.#canManage();

    const sceneRecall = this.#buildSceneRecallView();
    if (sceneRecall) sceneRecall.animate = this.#animateSceneNext;
    this.#animateSceneNext = false;

    let viewActive = ownerActive;
    let viewCanManage = ownerCanManage;
    let viewCanOpenManager = this.#canOpenManager();
    let map = null;
    if (this.#view === APP_VIEWS.MAP) {
      map = await this.#buildMapGraph({
        ownerRelationships: rels,
        ownerViews: allRelationshipViews,
        ownerActive,
        playInspectorEnter: playTransition
      });
      map.skinThemeId = selectedTheme.id;
      viewActive = map.activeView ?? ownerActive;
      viewCanManage = map.canManage;
      viewCanOpenManager = map.canOpenManager;
    }

    const context = {
      theme: this.#themeContext(theme),
      profile,
      terminology,
      totalRanks,
      maxRankTotal,
      activeBondCount,
      relationshipCount: maxRelationshipSlots,
      relationships,
      entryList: this.#buildRelationshipListContext(rels),
      active: viewActive,
      playTransition,
      canManage: viewCanManage,
      canOpenManager: viewCanOpenManager,
      isFullscreen: this.#isFullscreen,
      isMapView: this.#view === APP_VIEWS.MAP,
      map,
      fontScalePercent: Math.round((profile.fontScale ?? 1) * 100),
      guideText: viewActive?.locked
        ? game.i18n.localize(viewActive.firstGiftUnlockAvailable
          ? "STYLISH_RELATIONSHIP_TRACKER.guide.firstGiftUnlock"
          : "STYLISH_RELATIONSHIP_TRACKER.guide.locked")
        : game.i18n.localize("STYLISH_RELATIONSHIP_TRACKER.guide.default"),
      sceneRecall,
      moment: this.#view === APP_VIEWS.MAP ? null : this.#buildMomentView(),
      dossier: this.#buildDossierView(viewActive),
      eventLog: this.#buildEventLogView(viewActive),
      gift: this.#buildGiftView(viewActive, this.#relationships().find(r => r.id === activeId) ?? null)
    };
    return theme.adapter.buildContext(context, { app: this, theme });
  }

  /**
   * Build enriched dossier note views for a relationship. GM-only notes are
   * already stripped for non-GM viewers by sanitizeRelationshipDataForUser; the
   * visibility filter here is a defensive second gate so a GM body can never
   * leak even if an unsanitized relationship reaches this path (e.g. DEMO mode).
   */
  async #buildNoteViews(rel) {
    const isGM = typeof game !== "undefined" && game.user?.isGM === true;
    const source = Array.isArray(rel.notes) ? rel.notes : [];
    const views = [];
    for (const note of source) {
      const isGmNote = note?.visibility === "gm";
      if (isGmNote && !isGM) continue;
      const bodyHtml = await enrichHtml(typeof note?.body === "string" ? note.body : "");
      const title = typeof note?.title === "string" && note.title.trim() !== ""
        ? note.title
        : this.#localize("STYLISH_RELATIONSHIP_TRACKER.detail.noteUntitled");
      views.push({
        id: note?.id ?? "",
        title,
        isGm: isGmNote,
        bodyHtml,
        hasBody: bodyHtml.trim().length > 0
      });
    }
    return views;
  }

  /**
   * Build the dossier overlay context for the active relationship. Validates the
   * stored open/tab state against the current active relationship so a stale tab
   * or a stale-open flag can never surface another relationship's note body. One
   * left-rail tab is created per visible note that has a non-empty enriched body.
   *
   * @param {object|null} active Active relationship view (from #buildRelationshipView).
   * @returns {{open: boolean, accent: string, label: string, tabs: object[], activeTab: string|null, activeTitle: string, activeIsGm: boolean, activeBodyHtml: string}}
   */
  #buildDossierView(active) {
    const empty = {
      open: false,
      accent: DEFAULT_ACCENT,
      label: this.#localize("STYLISH_RELATIONSHIP_TRACKER.detail.dossier"),
      tabs: [],
      activeTab: null,
      activeTitle: "",
      activeIsGm: false,
      activeBodyHtml: ""
    };

    const notes = (Array.isArray(active?.notes) ? active.notes : []).filter(note => note.hasBody);
    if (!active || active.locked || notes.length === 0) {
      this.#dossierOpen = false;
      this.#dossierTab = null;
      return empty;
    }

    let current = this.#dossierTab;
    if (!notes.some(note => note.id === current)) current = notes[0]?.id ?? null;
    this.#dossierTab = current;

    const activeNote = notes.find(note => note.id === current) ?? notes[0];

    return {
      open: this.#dossierOpen,
      accent: active.accent,
      label: this.#localize("STYLISH_RELATIONSHIP_TRACKER.detail.dossier"),
      tabs: notes.map(note => ({
        key: note.id,
        isGm: note.isGm,
        active: note.id === current,
        label: note.title
      })),
      activeTab: current,
      activeTitle: activeNote?.title ?? "",
      activeIsGm: activeNote?.isGm === true,
      activeBodyHtml: activeNote?.bodyHtml ?? ""
    };
  }

  /** Close the dossier overlay and clear the selected tab. */
  #resetDossier() {
    this.#dossierOpen = false;
    this.#dossierTab = null;
  }

  /** Close the dossier overlay (keeping no stale tab) and re-render. */
  #closeDossierNow() {
    this.#resetDossier();
    this.render({ force: false });
  }

  #buildEventLogView(active) {
    const empty = {
      open: false,
      accent: DEFAULT_ACCENT,
      name: "",
      events: [],
      shownCount: 0,
      totalCount: 0
    };

    const events = Array.isArray(active?.allEvents) ? active.allEvents : [];
    if (!active || active.locked || events.length === 0) {
      this.#eventLogOpen = false;
      return empty;
    }

    return {
      open: this.#eventLogOpen,
      accent: active.accent,
      name: active.displayName,
      events,
      shownCount: Math.min(3, events.length),
      totalCount: events.length
    };
  }

  #resetEventLog() {
    this.#eventLogOpen = false;
  }

  #closeEventLogNow() {
    this.#resetEventLog();
    this.render({ force: false });
  }

  /**
   * Build the player-facing Gift dialog context for the active archive
   * relationship. The relationship-window giver is always the archive owner
   * Actor, so item options come from the owner's own inventory and never the
   * target's. Gating combines the authoritative canGiveGift permission with
     * resolveGiftGiftability, so a disallowed, locked, hidden, disabled,
     * max-rank-blocked, no-item, or non-owner viewer state yields a closed,
     * unusable panel.
    */
  #buildGiftView(activeView, rawRel) {
    const closed = { available: false, canGift: false, open: false, items: [], hasItems: false };
    const user = typeof game !== "undefined" ? game.user : null;
    const isGM = user?.isGM === true;
    if (this.#view !== APP_VIEWS.ARCHIVE || !activeView || !rawRel) {
      this.#giftDialogOpen = false;
      return closed;
    }

    const giverActor = this.#ownerActor;
    const unlocksWithGift = canUnlockRelationshipWithGift(rawRel);
    const targetName = unlocksWithGift ? "???" : activeView.displayName;
    const canGivePermission = !!giverActor && canGiveGift(user, giverActor, rawRel, giverActor);

    const itemOptions = {
      worldMaxQuantity: this.#giftWorldMaxQuantity(),
      profileMaxQuantity: this.#giftProfileMaxQuantity(rawRel)
    };
    const items = this.#giftDialogOpen
      ? (this.#giftItemOptionsCache ??= buildGiftGiverItemOptions(giverActor, itemOptions).map(item => ({
        ...item,
        quantityLabel: item.singleUse ? this.#localize("editor.gift.singleUse") : String(item.quantity)
      })))
      : [];
    const hasGiftableItems = this.#giftDialogOpen
      ? items.some(item => item.disabled !== true)
      : hasGiftableGiverItems(giverActor, itemOptions);

    const gate = resolveGiftGiftability(rawRel, { canGivePermission, hasGiftableItems });
    const canOpenGift = canGivePermission === true && (gate.canGift || isGM);
    if (!canOpenGift) {
      this.#giftDialogOpen = false;
      this.#giftItemOptionsCache = null;
    }

    const preference = buildGiftPreferenceView(rawRel);
    const hintSuffix = gate.disabledReason ? GIFT_DISABLED_HINT_KEYS[gate.disabledReason] : null;
    if (!this.#giftDialogOpen || !canOpenGift) {
      return {
        ...closed,
        available: canOpenGift,
        canGift: gate.canGift,
        accent: activeView.accent,
        targetName,
        giverName: giverActor?.name ?? "",
        hasGiftableItems,
        disabledReason: gate.disabledReason,
        disabledHint: hintSuffix ? this.#localize(`editor.gift.${hintSuffix}`) : ""
      };
    }
    const draft = this.#giftDialogOpen && canOpenGift ? this.#giftDraftFor(rawRel, items) : null;
    const viewItems = items.map(item => ({
      ...item,
      hasImage: typeof item.img === "string" && item.img.trim() !== "",
      selected: item.id === draft?.itemId
    }));
    const selectedItem = viewItems.find(item => item.selected) ?? null;
    const catalog = buildGiftItemCatalog(viewItems, {
      query: this.#giftItemQuery,
      page: this.#giftItemPage,
      pageSize: GIFT_CATALOG_PAGE_SIZE
    });
    catalog.items = catalog.items.map((item, index) => ({ ...item, catalogIndex: catalog.rangeStart + index }));
    this.#giftItemPage = catalog.page;

    return {
      available: canOpenGift,
      canGift: gate.canGift && !this.#giftSubmitting,
      open: this.#giftDialogOpen && canOpenGift,
      accent: activeView.accent,
      targetName,
      giverName: giverActor?.name ?? "",
      items: viewItems,
      selectedItem,
      catalog,
      hasItems: viewItems.length > 0,
      hasGiftableItems,
      submitting: this.#giftSubmitting,
      disabledReason: gate.disabledReason,
      disabledHint: hintSuffix ? this.#localize(`editor.gift.${hintSuffix}`) : "",
      preferenceVisibility: preference.visibility,
      preview: this.#giftPreviewView(rawRel, preference.visibility),
      quantity: draft?.quantity ?? 1,
      eventText: draft?.eventText ?? "",
      day: draft?.day ?? ""
    };
  }

  #resetGiftDialog() {
    this.#giftDialogOpen = false;
    this.#giftDraft = null;
    this.#giftItemQuery = "";
    this.#giftItemPage = 1;
    this.#deferredFocusSelector = null;
    this.#giftItemOptionsCache = null;
    this.#giftSubmitting = false;
    if (this.#giftSearchTimer) {
      clearTimeout(this.#giftSearchTimer);
      this.#giftSearchTimer = null;
    }
    if (this.#giftInventoryRenderTimer) {
      clearTimeout(this.#giftInventoryRenderTimer);
      this.#giftInventoryRenderTimer = null;
    }
    this.#clearGiftPreview();
  }

  #giftDraftFor(rawRel, items) {
    const relationshipId = rawRel?.id ?? "";
    const fallbackItem = items.find(item => item.disabled !== true) ?? null;
    const current = this.#giftDraft?.relationshipId === relationshipId ? this.#giftDraft : null;
    const currentItem = current?.itemId
      ? items.find(item => item.id === current.itemId && item.disabled !== true) ?? null
      : null;
    const item = currentItem ?? fallbackItem;
    const quantity = this.#clampGiftDraftQuantity(current?.quantity ?? 1, item?.maxQuantity);
    const draft = {
      relationshipId,
      itemId: item?.id ?? "",
      quantity,
      eventText: current?.eventText ?? "",
      day: current?.day ?? ""
    };
    this.#giftDraft = draft;
    return draft;
  }

  #clampGiftDraftQuantity(value, maxQuantity = null) {
    const number = Number(value);
    const max = Number(maxQuantity);
    const upper = Number.isFinite(max) && max > 0 ? Math.round(max) : 999;
    return Math.max(1, Math.min(upper, Number.isFinite(number) ? Math.round(number) : 1));
  }

  #clearGiftPreview() {
    if (this.#giftPreviewTimer) {
      clearTimeout(this.#giftPreviewTimer);
      this.#giftPreviewTimer = null;
    }
    this.#giftPreview = null;
    this.#giftPreviewPendingKey = null;
    this.#giftPreviewRequestId += 1;
  }

  #giftPreviewView(rawRel, visibility) {
    if (visibility === GIFT_PREFERENCE_VISIBILITY.HIDDEN) return { visible: false, visibility, tone: "hidden", label: "" };
    if (!this.#giftPreview || this.#giftPreview.relationshipId !== rawRel?.id) {
      return { visible: false, visibility, tone: "unknown", label: "" };
    }
    return this.#giftPreview;
  }

  #giftWorldMaxQuantity() {
    if (typeof game === "undefined" || typeof game.settings?.get !== "function") return null;
    try {
      const value = Number(game.settings.get(MODULE_ID, SETTING_GIFT_DEFAULT_MAX_QUANTITY_PER_GIFT));
      return Number.isFinite(value) && value > 0 ? Math.round(value) : null;
    } catch (_error) {
      return null;
    }
  }

  #giftProfileMaxQuantity(rawRel) {
    const value = Number(resolveGiftDialogPolicy(rawRel)?.maxQuantityPerGift);
    return Number.isFinite(value) && value > 0 ? Math.round(value) : null;
  }

  /** Whether the active archive relationship currently exposes a usable Gift action for this user. */
  #canOpenGiftDialog() {
    if (this.#view !== APP_VIEWS.ARCHIVE) return false;
    const rel = this.#viewActiveRelationship();
    const giverActor = this.#ownerActor;
    const user = typeof game !== "undefined" ? game.user : null;
    const isGM = user?.isGM === true;
    if (!rel || !giverActor) return false;
    const canGivePermission = canGiveGift(user, giverActor, rel, giverActor);
    if (!canGivePermission) return false;
    const hasGiftableItems = hasGiftableGiverItems(giverActor, {
      worldMaxQuantity: this.#giftWorldMaxQuantity(),
      profileMaxQuantity: this.#giftProfileMaxQuantity(rel)
    });
    const gate = resolveGiftGiftability(rel, { canGivePermission, hasGiftableItems });
    return gate.canGift || isGM;
  }

  #localizedProfile(profile) {
    const localized = { ...profile };
    const terminology = this.#terminology(profile);
    if (localized.title === PROFILE_DEFAULTS.title && terminology.singular !== PROFILE_DEFAULTS.bondLabel) {
      localized.title = terminology.singular;
    }
    if (localized.subtitle === PROFILE_DEFAULTS.subtitle) {
      localized.subtitle = terminology.singular === PROFILE_DEFAULTS.bondLabel
        ? this.#localize("STYLISH_RELATIONSHIP_TRACKER.profile.subtitle")
        : terminology.record;
    }
    if (localized.archiveLabel === PROFILE_DEFAULTS.archiveLabel) {
      localized.archiveLabel = this.#localize("STYLISH_RELATIONSHIP_TRACKER.profile.archiveLabel");
    }
    if (localized.sessionLabel === PROFILE_DEFAULTS.sessionLabel) {
      localized.sessionLabel = this.#localize("STYLISH_RELATIONSHIP_TRACKER.profile.sessionLabel");
    }
    if (localized.calendarLabel === PROFILE_DEFAULTS.calendarLabel) {
      localized.calendarLabel = this.#localize("STYLISH_RELATIONSHIP_TRACKER.profile.calendarLabel");
    }
    return localized;
  }

  #localize(key) {
    const fullKey = key.startsWith("STYLISH_RELATIONSHIP_TRACKER.")
      ? key
      : `STYLISH_RELATIONSHIP_TRACKER.${key}`;
    return typeof game !== "undefined" && typeof game.i18n?.localize === "function"
      ? game.i18n.localize(fullKey)
      : fullKey;
  }

  #formatLocalize(key, data = {}) {
    const fullKey = key.startsWith("STYLISH_RELATIONSHIP_TRACKER.")
      ? key
      : `STYLISH_RELATIONSHIP_TRACKER.${key}`;
    if (typeof game !== "undefined" && typeof game.i18n?.format === "function") {
      return game.i18n.format(fullKey, data);
    }
    return Object.entries(data).reduce(
      (text, [name, value]) => text.replaceAll(`{${name}}`, String(value)),
      this.#localize(fullKey)
    );
  }

  #terminology(profile = this.#data.profile) {
    return relationshipTerminology(profile, (key, data) => this.#formatLocalize(key, data));
  }

  #canManage(actor = this.#ownerActor) {
    return canEditRelationships(typeof game !== "undefined" ? game.user : null, actor);
  }

  #canUnlock(actor = this.#ownerActor) {
    return !!actor && typeof game !== "undefined" && game.user?.isGM === true;
  }

  #canOpenManager() {
    return !!this.#ownerActor && this.#canManage();
  }

  async #loadActorData() {
    if (!this.#ownerActor && this.#ownerActorUuid) {
      try {
        this.#ownerActor = await resolveOwnerActor(this.#ownerActorUuid);
      } catch (error) {
        console.warn(`${MODULE_ID} | ${error.message}`);
      }
    }

    if (!this.#ownerActor) {
      if (!this.#missingActorWarned && typeof ui !== "undefined") {
        ui.notifications.warn("Relationship owner Actor could not be resolved.");
        this.#missingActorWarned = true;
      }
      this.#data = { classes: RELATIONSHIP_CLASSES, profile: { ...PROFILE_DEFAULTS }, relationships: [] };
      return;
    }

    const override = _previewOverride && _previewOverride.ownerActorUuid === this.#ownerActor.uuid
      ? _previewOverride.data
      : null;
    const storedData = override ?? await getRelationshipData(this.#ownerActor);
    const viewerData = sanitizeRelationshipDataForUser(
      typeof game !== "undefined" ? game.user : null,
      this.#ownerActor,
      storedData
    );
    const resolvedData = await resolveRelationshipActors(viewerData);
    this.#ownerActorUuid = resolvedData.ownerActorUuid || this.#ownerActor.uuid;
    this.#data = {
      classes: RELATIONSHIP_CLASSES,
      profile: resolveWorldProfileDefaults(resolvedData.profile),
      relationships: resolvedData.relationships
    };
  }

  async #buildRelationshipView(rel, isActive, canManage = this.#canManage(), ownerActor = this.#ownerActor) {
    const category = this.#categoryOf(rel);
    const accent = this.#resolveAccent(rel);
    const isOrganization = rel.entryType === "organization";
    const terminology = this.#terminology();
    const displayName = this.#displayName(rel, category);
    const role = this.#relationshipRole(rel);
    const portrait = this.#relationshipPortrait(rel);
    const listPortrait = this.#relationshipListPortrait(rel);
    const noteViews = await this.#buildNoteViews(rel);
    const hasNotes = noteViews.some(note => note.hasBody);

    const events = (Array.isArray(rel.events) ? rel.events : [])
      .filter(event => isEventRevealedAtRank(event, isNegativeRelationship(rel) ? 0 : rel.rank));
    const eventViews = events.map((e, i) => {
      const gift = buildGiftEventView(e);
      const text = e.text ?? "";
      const isRankDown = e.rankChange === EVENT_RANK_CHANGES.DOWN;
      const rankLabel = e.rankLabel ?? "";
      return {
        eventId: this.#eventId(rel.id, i, e),
        seq: i + 1,
        day: e.day ?? "",
        text,
        displayText: gift ? [text, gift.summary].filter(Boolean).join(" | ") : text,
        rankLabel,
        displayRankLabel: isRankDown ? ["\u2193", rankLabel].filter(Boolean).join(" ") : rankLabel,
        isRankUp: e.isRankUp === true,
        isRankDown,
        isMax: e.rankLabel === "MAX",
        hasQuote: String(e.quote || "").trim().length > 0,
        hasRecollection: String(e.recollection || "").trim().length > 0,
        gift
      };
    });
    const allEvents = eventViews.slice().reverse();
    const recentEvents = eventViews
      .slice(-3)
      .reverse()
      .map((e, i) => ({ ...e, delayMs: 150 + i * 70 }));

    const mapRankUpFx = this.#mapFx?.relationshipId === rel.id && !isNegativeRelationship(rel);
    const progressView = buildRankProgressView(rel);
    const { isMax, isNegative, isNegativeMax, segments: progress } = progressView;
    const effectivePolarity = relationshipEffectivePolarity(rel);
    const canRank = canManage && canUsePlayerRankControls(
      typeof game !== "undefined" ? game.user : null,
      ownerActor,
      rel
    );

    return {
      id: rel.id,
      entryType: rel.entryType,
      isOrganization,
      entryBadge: isOrganization ? this.#localize("STYLISH_RELATIONSHIP_TRACKER.organization.badgeShort") : "",
      rankLabel: this.#localize(isOrganization
        ? "STYLISH_RELATIONSHIP_TRACKER.organization.rank"
        : "STYLISH_RELATIONSHIP_TRACKER.list.rank"),
      currentRankLabel: isNegative
        ? this.#localize("STYLISH_RELATIONSHIP_TRACKER.polarity.hostileRank")
        : this.#localize(isOrganization
          ? "STYLISH_RELATIONSHIP_TRACKER.organization.currentRank"
          : "STYLISH_RELATIONSHIP_TRACKER.map.currentRank"),
      maxRankLabel: isNegative
        ? this.#localize("STYLISH_RELATIONSHIP_TRACKER.polarity.maxHostility")
        : (isOrganization
          ? this.#localize("STYLISH_RELATIONSHIP_TRACKER.organization.maxRank")
          : terminology.maxLabel),
      rankUpLabel: isNegative
        ? this.#localize("STYLISH_RELATIONSHIP_TRACKER.polarity.reconcile")
        : (isOrganization
          ? this.#localize("STYLISH_RELATIONSHIP_TRACKER.organization.increase")
          : terminology.deepen),
      rankDownLabel: isNegative
        ? this.#localize("STYLISH_RELATIONSHIP_TRACKER.polarity.deepenHostility")
        : this.#localize(isOrganization
          ? "STYLISH_RELATIONSHIP_TRACKER.organization.rankDown"
          : "STYLISH_RELATIONSHIP_TRACKER.controls.rankDown"),
      rankCompleteLabel: isNegative
        ? this.#localize("STYLISH_RELATIONSHIP_TRACKER.polarity.hostileLimit")
        : (isOrganization
          ? this.#localize("STYLISH_RELATIONSHIP_TRACKER.organization.complete")
          : terminology.complete),
      classId: rel.classId,
      categoryLabel: category.categoryLabel,
      categoryLabelEn: category.categoryLabelEn,
      bgLetter: category.categoryLabelEn || category.categoryLabel || "",
      accent,
      rowAccent: rel.locked ? "#6B6B78" : accent,
      accentSoft: hexToSoft(accent),
      displayName,
      displayNameRoman: rel.nameRoman || displayName,
      role,
      rank: rel.rank,
      rankDisplay: relationshipRankDisplay(rel),
      signedRank: relationshipSignedRank(rel),
      polarity: rel.polarity,
      polarityLabel: this.#localize(isNegative
        ? "STYLISH_RELATIONSHIP_TRACKER.polarity.negative"
        : (effectivePolarity === "neutral"
          ? "STYLISH_RELATIONSHIP_TRACKER.polarity.neutral"
          : "STYLISH_RELATIONSHIP_TRACKER.polarity.positive")),
      isNegative,
      isNeutral: effectivePolarity === "neutral",
      isNegativeMax,
      maxRank: rel.maxRank,
      rankPadded: relationshipPaddedRankDisplay(rel),
      isMax,
      locked: rel.locked === true,
      firstGiftUnlockAvailable: canUnlockRelationshipWithGift(rel),
      rowName: rel.locked ? this.#localize("STYLISH_RELATIONSHIP_TRACKER.detail.lockedName") : (role ? `${displayName} · ${role}` : displayName),
      isActive,
      portrait,
      listPortrait,
      portraitPresentation: rel.portraitPresentation,
      portraitTag: rel.portraitTag || displayName || "NO IMAGE",
      portraitStyle: this.#portraitStyle(rel),
      mapInspectorPortrait: this.#relationshipMapInspectorPortrait(rel),
      mapInspectorStyle: this.#mapInspectorStyle(rel),
      hasCustomMapInspectorFrame: hasCustomMapInspectorFrame(rel),
      bio: rel.bio || "",
      bioLines: String(rel.bio || "").split("\n"),
      notes: noteViews,
      hasNotes,
      stats: (Array.isArray(rel.stats) ? rel.stats : []).map((s, i) => ({
        key: s.key ?? "",
        value: s.value ?? "",
        accent: s.accent === true,
        delayMs: i * 60
      })),
      mapRankUpFx,
      recentEvents,
      allEvents,
      eventCount: eventViews.length,
      recentCount: Math.min(3, eventViews.length),
      hasMoreEvents: eventViews.length > 3,
      progress,
      unlockable: rel.locked === true && typeof game !== "undefined" && game.user?.isGM === true,
      rankUpDisabled: rel.locked || !canMoveRelationshipAxis(rel, 1) || !canRank,
      rankDownDisabled: rel.locked || !canMoveRelationshipAxis(rel, -1) || !canRank
    };
  }

  #portraitStyle(rel) {
    const scale = Number(rel.portraitScale) || 1;
    const x = Number(rel.portraitOffset?.x) || 0;
    const y = Number(rel.portraitOffset?.y) || 0;
    return `right:${x}px; bottom:${y}px; --srt-portrait-x:${x}px; --srt-portrait-y:${y}px; --srt-portrait-scale:${scale};`;
  }

  #mapInspectorStyle(rel) {
    const frame = normalizeMapInspectorFrame(rel);
    return `--srt-map-inspector-image-scale:${frame.scale}; --srt-map-inspector-image-x:${frame.x}%; --srt-map-inspector-image-y:${frame.y}%;`;
  }

  static updatePortraitTransform(ownerActorUuid, { scale, x, y } = {}) {
    if (!_openInstance) return;
    if (_openInstance.#ownerActorUuid !== ownerActorUuid) return;
    const img = _openInstance.element?.querySelector("[data-srt-artwork-foreground]");
    if (!img) return;
    img.style.right = `${Number(x) || 0}px`;
    img.style.bottom = `${Number(y) || 0}px`;
    img.style.setProperty("--srt-portrait-x", `${Number(x) || 0}px`);
    img.style.setProperty("--srt-portrait-y", `${Number(y) || 0}px`);
    img.style.setProperty("--srt-portrait-scale", String(Number(scale) || 1));
  }

  static updateSceneStillTransform(ownerActorUuid, { relationshipId, eventId, scale, x, y } = {}) {
    if (!_openInstance) return;
    if (_openInstance.#ownerActorUuid !== ownerActorUuid) return;
    const recall = _openInstance.#sceneRecall;
    if (!recall || recall.relationshipId !== relationshipId || recall.eventId !== eventId) return;
    const img = _openInstance.element?.querySelector(".srt-scene-still-img, .srt-dp-scene-img, .srt-jr-scene-img, .srt-ag-scene-img, .srt-sl-scene-img, .srt-al-scene-img");
    if (!img) return;
    img.style.transform = `translate(${Number(x) || 0}px, ${Number(y) || 0}px) scale(${Number(scale) || 1})`;
  }

  #eventId(relId, index, event = null) {
    return event?.id || `${relId}::evt::${index}`;
  }

  #buildSceneRecallView() {
    if (!this.#sceneRecall) return null;
    const rel = this.#viewRelationships().find(r => r.id === this.#sceneRecall.relationshipId);
    if (!rel) return null;
    const events = Array.isArray(rel.events) ? rel.events : [];
    const idx = events.findIndex((e, i) => this.#eventId(rel.id, i, e) === this.#sceneRecall.eventId);
    const event = events[idx];
    if (!event) return null;
    if (!isEventRevealedAtRank(event, isNegativeRelationship(rel) ? 0 : rel.rank)) return null;

    const category = this.#categoryOf(rel);
    const accent = this.#resolveAccent(rel);
    const displayName = this.#displayName(rel, category);
    const quoteClean = String(event.quote || "").replace(/^[“"]|[”"]$/g, "");

    return {
      accent,
      entryType: rel.entryType,
      isOrganization: rel.entryType === "organization",
      rankLabel: this.#localize(rel.entryType === "organization"
        ? "STYLISH_RELATIONSHIP_TRACKER.organization.rank"
        : "STYLISH_RELATIONSHIP_TRACKER.list.rank"),
      maxRankLabel: rel.entryType === "organization"
        ? this.#localize("STYLISH_RELATIONSHIP_TRACKER.organization.maxRank")
        : this.#terminology().maxLabel,
      usesRelationshipPortrait: !event.image,
      classId: rel.classId,
      categoryLabelEn: category.categoryLabelEn,
      displayName,
      role: this.#relationshipRole(rel),
      portrait: event.image || this.#relationshipPortrait(rel),
      imageStyle: this.#sceneStillStyle(event),
      portraitTag: rel.portraitTag || displayName,
      day: event.day ?? "",
      rankLabel: event.rankLabel ?? "",
      isMax: event.rankLabel === "MAX",
      text: event.text ?? "",
      recollection: event.recollection || this.#localize("STYLISH_RELATIONSHIP_TRACKER.scene.emptyRecollection"),
      hasQuote: quoteClean.length > 0,
      quoteClean
    };
  }

  /** Scene Recall still transform. Event framing (imageScale/imageOffsetX/imageOffsetY) applies whether the still shows the event image or the relationship-portrait fallback. */
  #sceneStillStyle(event) {
    const scale = Number(event.imageScale) || 1;
    const x = Number(event.imageOffsetX) || 0;
    const y = Number(event.imageOffsetY) || 0;
    return `transform: translate(${x}px, ${y}px) scale(${scale});`;
  }

  #buildMomentView() {
    if (!this.#moment) return null;
    const rel = this.#relationships().find(r => r.id === this.#moment.relationshipId);
    if (!rel) return null;
    const category = this.#categoryOf(rel);
    const accent = this.#resolveAccent(rel);
    const isMax = this.#moment.type === MOMENT_TYPES.MAX;
    const isRankDown = this.#moment.type === MOMENT_TYPES.RANK_DOWN;

    const shards = [];
    for (let i = 0; i < 18; i++) {
      const angle = (360 / 18) * i + (Math.random() * 14 - 7);
      const dist = 280 + Math.random() * 220;
      const palette = isMax ? ["#FFC42E", "#0B0B10", "#F1E7D3"] : [accent, "#0B0B10", "#F1E7D3"];
      const color = palette[i % palette.length];
      const w = 14 + Math.random() * 22;
      const h = 5 + Math.random() * 7;
      const delay = (Math.random() * 0.1).toFixed(3);
      shards.push({
        style: `--a:${angle.toFixed(1)}deg; --d:${dist.toFixed(0)}px; background:${color}; width:${w.toFixed(0)}px; height:${h.toFixed(0)}px; animation-delay:${delay}s;`
      });
    }

    return {
      type: this.#moment.type,
      isMax,
      isRankDown,
      isRankUp: this.#moment.type === MOMENT_TYPES.RANK_UP,
      entryType: rel.entryType,
      isOrganization: rel.entryType === "organization",
      rankLabel: this.#localize(rel.entryType === "organization"
        ? "STYLISH_RELATIONSHIP_TRACKER.organization.rank"
        : "STYLISH_RELATIONSHIP_TRACKER.list.rank"),
      rankCompleteLabel: rel.entryType === "organization"
        ? this.#localize("STYLISH_RELATIONSHIP_TRACKER.organization.complete")
        : this.#terminology().complete,
      accent,
      displayName: this.#displayName(rel, category),
      classId: rel.classId,
      categoryLabelEn: category.categoryLabelEn,
      oldRank: this.#moment.oldRank,
      newRank: this.#moment.newRank,
      shards
    };
  }

  #showGiftReaction(rel, result, { releaseRankCutins } = {}) {
    const release = typeof releaseRankCutins === "function" ? releaseRankCutins : () => {};
    const reactionPayload = result?.reaction;
    if (!rel || !reactionPayload) {
      release();
      return;
    }
    const revealedRelationship = result?.relationship?.locked === false ? result.relationship : rel;
    const resultingRelationship = {
      ...revealedRelationship,
      polarity: result?.newPolarity ?? revealedRelationship.polarity,
      rank: result?.newRank ?? revealedRelationship.rank
    };
    const category = this.#categoryOf(revealedRelationship);
    const eventGift = result?.event?.gift ?? {};
    const payload = {
      themeId: this.#currentTheme().id,
      bondLabel: this.#terminology().singular,
      bondLabelPlural: this.#terminology().plural,
      accent: this.#resolveAccent(resultingRelationship),
      targetName: this.#displayName(revealedRelationship, category),
      categoryLabel: category.categoryLabel ?? revealedRelationship.categoryLabel ?? "",
      categoryLabelEn: category.categoryLabelEn ?? revealedRelationship.categoryLabelEn ?? "",
      itemName: eventGift.itemName ?? "",
      itemImage: eventGift.itemImg ?? "",
      quantity: eventGift.quantity ?? 1,
      rankIncreased: result?.rankIncreased === true,
      oldRank: result?.oldRank,
      oldPolarity: result?.oldPolarity,
      newRank: result?.newRank,
      newPolarity: result?.newPolarity,
      isMax: !isNegativeRelationship(resultingRelationship)
        && Number(result?.newRank) >= Math.max(1, Number(revealedRelationship.maxRank) || 1),
      reaction: reactionPayload
    };
    // The Gift caused the rank change, so its response must land first. Rank
    // notices broadcast during giveGift stay held until the reaction queue has
    // completely left the screen, then resume in their original order.
    const shown = GiftReactionOverlay.show(payload);
    if (!shown) {
      release();
      return;
    }
    void GiftReactionOverlay.whenIdle().finally(release);
  }

  /* ---------------------------------------------------------------- */
  /*  Constellation map view                                          */
  /* ---------------------------------------------------------------- */

  #focusIsOwner() {
    return !this.#focusActorUuid || this.#focusActorUuid === this.#ownerActorUuid;
  }

  #resetFocusToOwner() {
    this.#focusActorUuid = null;
    this.#focusActor = null;
    this.#focusStack = [];
    this.#mapFocusActiveId = null;
    this.#resetMapViewport();
  }

  /** Reset pan and zoom together so a fresh focus/view starts centered at 100%. */
  #resetMapViewport() {
    this.#mapPan = { x: 0, y: 0 };
    this.#mapZoom = 1;
  }

  /** Whether the map controls (rank/manager) act on a non-owner focus actor. */
  #mapControlsActive() {
    return this.#view === APP_VIEWS.MAP && !this.#focusIsOwner();
  }

  /** Load another actor's relationships, gated and sanitized for the current user. */
  async #loadActorRelationships(actor) {
    if (!actor) return null;
    const user = typeof game !== "undefined" ? game.user : null;
    if (!canViewRelationships(user, actor)) return null;
    const stored = await getRelationshipData(actor);
    const viewerData = sanitizeRelationshipDataForUser(user, actor, stored);
    const resolved = await resolveRelationshipActors(viewerData);
    return Array.isArray(resolved.relationships) ? resolved.relationships : [];
  }

  #focusActiveId(rels) {
    if (this.#mapFocusActiveId && rels.some(r => r.id === this.#mapFocusActiveId)) return this.#mapFocusActiveId;
    const firstUnlocked = rels.find(r => !r.locked) ?? rels[0];
    return firstUnlocked?.id ?? null;
  }

  #mapVisibilityMode() {
    const mode = this.#data.profile?.mapVisibilityMode;
    return Object.values(MAP_VISIBILITY_MODES).includes(mode) ? mode : PROFILE_DEFAULTS.mapVisibilityMode;
  }

  #mapDepthLimit() {
    const configured = this.#clampMapInteger(this.#data.profile?.mapMaxDepth, PROFILE_DEFAULTS.mapMaxDepth, 1, 4);
    const mode = this.#mapVisibilityMode();
    if (mode === MAP_VISIBILITY_MODES.DIRECT) return 1;
    if (mode === MAP_VISIBILITY_MODES.NETWORK) return configured;
    return Math.min(configured, 2);
  }

  #mapNodeLimit() {
    return this.#clampMapInteger(this.#data.profile?.mapMaxNodes, PROFILE_DEFAULTS.mapMaxNodes, 1, 200);
  }

  #clampMapInteger(value, fallback, min, max) {
    const number = Math.round(Number(value));
    const safe = Number.isFinite(number) ? number : fallback;
    return Math.max(min, Math.min(max, safe));
  }

  /** Minimal node shape for hop-2 leaves (no inspector / selection). */
  #mapNodeBasics(rel) {
    const category = this.#categoryOf(rel);
    const accent = this.#resolveAccent(rel);
    const progressView = buildRankProgressView(rel);
    const mapThumbnailFrame = normalizeMapThumbnailFrame(rel);
    const mapUseThumbnails = this.#data.profile?.mapUseThumbnails !== false;
    const mapThumbnail = typeof rel.mapThumbnail === "string" ? rel.mapThumbnail.trim() : "";
    const isActorLinked = rel.entryType === "actor" && !!rel.targetUuid && rel._targetActorMissing !== true;
    return {
      id: rel.id,
      entryType: rel.entryType,
      isOrganization: rel.entryType === "organization",
      entryBadge: rel.entryType === "organization"
        ? this.#localize("STYLISH_RELATIONSHIP_TRACKER.organization.badgeShort")
        : "",
      rankLabel: this.#localize(rel.entryType === "organization"
        ? "STYLISH_RELATIONSHIP_TRACKER.organization.rank"
        : "STYLISH_RELATIONSHIP_TRACKER.list.rank"),
      maxRankLabel: rel.entryType === "organization"
        ? this.#localize("STYLISH_RELATIONSHIP_TRACKER.organization.maxRank")
        : this.#terminology().maxLabel,
      accent,
      accentSoft: hexToSoft(accent),
      locked: rel.locked === true,
      isMax: progressView.isMax,
      isNegative: progressView.isNegative,
      isNegativeMax: progressView.isNegativeMax,
      polarity: rel.polarity,
      rank: Number(rel.rank) || 0,
      rankDisplay: relationshipRankDisplay(rel),
      signedRank: relationshipSignedRank(rel),
      classId: rel.classId,
      categoryLabelEn: category.categoryLabelEn,
      displayName: this.#displayName(rel, category),
      portrait: this.#relationshipMapPortrait(rel),
      mapThumbnailScale: mapThumbnailFrame.scale,
      mapThumbnailOffsetX: mapThumbnailFrame.x,
      mapThumbnailOffsetY: mapThumbnailFrame.y,
      hasCustomMapThumbnailFrame: hasCustomMapThumbnailFrame(rel),
      usesAutomaticMapThumbnail: mapUseThumbnails && (!mapThumbnail || isGeneratedMapThumbnailPath(mapThumbnail)),
      isActorLinked,
      targetUuid: isActorLinked ? rel.targetUuid : ""
    };
  }

  #hop1Position(i, n) {
    const count = Math.max(1, n);
    const deg = -90 + (360 / count) * i;
    const a = deg * Math.PI / 180;
    return {
      x: Number((MAP_FOCUS.x + Math.cos(a) * HOP1_RADIUS_X).toFixed(1)),
      y: Number((MAP_FOCUS.y + Math.sin(a) * HOP1_RADIUS_Y).toFixed(1)),
      angleDeg: deg
    };
  }

  #hop2Position(px, py, parentDeg, j, k) {
    const off = (j - (k - 1) / 2) * HOP2_FAN_DEG;
    const a = (parentDeg + off) * Math.PI / 180;
    return {
      x: Number((px + Math.cos(a) * HOP2_RADIUS).toFixed(1)),
      y: Number((py + Math.sin(a) * HOP2_RADIUS).toFixed(1))
    };
  }

  async #buildMapGraph({ ownerRelationships, ownerViews, ownerActive, playInspectorEnter }) {
    const focusIsOwner = this.#focusIsOwner();

    let focusActor = this.#ownerActor;
    let focusRels = ownerRelationships;
    let focusViews = ownerViews;
    let canManageFocus = this.#canManage(this.#ownerActor);
    let focusActiveId = this.#activeId();
    let focusName = this.#ownerActor?.name || this.#localize("STYLISH_RELATIONSHIP_TRACKER.map.protagonistName");

    if (!focusIsOwner) {
      focusActor = this.#focusActor ?? await resolveActor(this.#focusActorUuid);
      const rels = focusActor ? await this.#loadActorRelationships(focusActor) : null;
      if (!focusActor || rels === null) {
        this.#resetFocusToOwner();
        return this.#buildMapGraph({ ownerRelationships, ownerViews, ownerActive, playInspectorEnter });
      }
      this.#focusActor = focusActor;
      focusRels = rels;
      canManageFocus = this.#canManage(focusActor);
      focusActiveId = this.#focusActiveId(rels);
      this.#mapFocusActiveId = focusActiveId;
      focusViews = await Promise.all(rels.map(r => this.#buildRelationshipView(r, r.id === focusActiveId, canManageFocus, focusActor)));
      focusName = focusActor.name || focusName;
    }

    this.#focusRelationships = focusRels;
    this.#mapControlActor = focusActor;

    const activeView = focusViews.find(v => v.id === focusActiveId) ?? focusViews[0] ?? null;

    const depthLimit = this.#mapDepthLimit();
    const maxNodes = this.#mapNodeLimit();
    const focusPairs = focusViews
      .map((v, i) => ({ v, raw: focusRels[i] }))
      .slice(0, maxNodes);
    const n = focusPairs.length;
    const shown = new Set();
    if (focusActor?.uuid) shown.add(focusActor.uuid);

    const nodes = focusPairs.map(({ v, raw }, i) => {
      const pos = this.#hop1Position(i, n);
      const basics = this.#mapNodeBasics(raw);
      const targetUuid = basics.targetUuid;
      if (targetUuid) shown.add(targetUuid);
      return {
        ...basics,
        x: pos.x,
        y: pos.y,
        angleDeg: pos.angleDeg,
        isActive: v.isActive === true,
        fxRankup: v.mapRankUpFx === true,
        portraitTag: v.portraitTag,
        strokeWidth: rankStrokeWidth(raw),
        canFocus: basics.isActorLinked && !!targetUuid,
        mx: Number(((MAP_FOCUS.x + pos.x) / 2).toFixed(1)),
        my: Number(((MAP_FOCUS.y + pos.y) / 2 - 8).toFixed(1))
      };
    });

    const hop2 = [];
    const hop2Links = [];
    const expansionQueue = nodes.map(node => ({ node, depth: 1 }));
    for (let i = 0; i < expansionQueue.length; i++) {
      if (nodes.length + hop2.length >= maxNodes) break;
      const { node, depth } = expansionQueue[i];
      if (depth >= depthLimit) continue;
      if (!node.canFocus || node.locked) continue;
      const targetActor = await resolveActor(node.targetUuid);
      if (!targetActor) continue;
      const targetRels = await this.#loadActorRelationships(targetActor);
      if (!targetRels) continue;

      const children = [];
      for (const childRel of targetRels) {
        if (nodes.length + hop2.length + children.length >= maxNodes) break;
        const childActorLinked = childRel.entryType === "actor" && !!childRel.targetUuid;
        const childUuid = childActorLinked ? childRel.targetUuid : "";
        if (childUuid) {
          if (shown.has(childUuid)) continue;
          shown.add(childUuid);
        }
        children.push(childRel);
      }

      const k = children.length;
      children.forEach((childRel, j) => {
        const pos = this.#hop2Position(node.x, node.y, node.angleDeg, j, k);
        const basics = this.#mapNodeBasics(childRel);
        const angleDeg = node.angleDeg + (j - (k - 1) / 2) * HOP2_FAN_DEG;
        const leaf = {
          ...basics,
          x: pos.x,
          y: pos.y,
          angleDeg,
          parentId: node.id,
          canFocus: basics.isActorLinked && !!basics.targetUuid
        };
        hop2.push({
          ...leaf
        });
        if (leaf.canFocus && !leaf.locked && depth + 1 < depthLimit) expansionQueue.push({ node: leaf, depth: depth + 1 });
        hop2Links.push({
          x1: node.x,
          y1: node.y,
          x2: pos.x,
          y2: pos.y,
          accent: basics.accent,
          locked: basics.locked
        });
      });
    }

    const focusPortrait = focusActor?.img || focusActor?.prototypeToken?.texture?.src || "";

    return {
      world: { w: MAP_WORLD_W, h: MAP_WORLD_H },
      pan: { x: this.#mapPan.x, y: this.#mapPan.y },
      zoom: this.#mapZoom,
      zoomPercent: Math.round(this.#mapZoom * 100),
      focus: { x: MAP_FOCUS.x, y: MAP_FOCUS.y, name: focusName, isOwner: focusIsOwner, portrait: focusPortrait },
      rings: [
        { r: 180, dashArray: "" },
        { r: 320, dashArray: "2 6" },
        { r: 470, dashArray: "" }
      ],
      cross: {
        hx1: MAP_FOCUS.x - 620,
        hx2: MAP_FOCUS.x + 700,
        hy: MAP_FOCUS.y,
        vx: MAP_FOCUS.x,
        vy1: MAP_FOCUS.y - 520,
        vy2: MAP_FOCUS.y + 580
      },
      nodes,
      hop2,
      hop2Links,
      back: { show: !focusIsOwner, current: focusName },
      nodeCount: n,
      hop2Count: hop2.length,
      playInspectorEnter,
      activeView,
      canManage: canManageFocus,
      canOpenManager: !!focusActor && canManageFocus
    };
  }

  async syncExternalDataChange(data = null) {
    if (this.#externalSyncPromise) {
      this.#externalSyncQueued = true;
      if (data) this.#externalSyncQueuedData = data;
      return this.#externalSyncPromise;
    }

    this.#externalSyncPromise = (async () => {
      let nextData = data;
      do {
        this.#externalSyncQueued = false;
        this.#externalSyncQueuedData = null;
        await this.#syncExternalDataChangeNow(nextData);
        nextData = this.#externalSyncQueuedData;
      } while (this.#externalSyncQueued);
    })();
    try {
      await this.#externalSyncPromise;
    } finally {
      this.#externalSyncPromise = null;
    }
  }

  async #syncExternalDataChangeNow(data = null) {
    if (this.#localRankChangeInProgress) return;

    if (this.#giftDialogOpen && !this.#giftSubmitting) {
      this.#rememberGiftFocus();
      this.#giftItemOptionsCache = null;
      this.#clearGiftPreview();
    } else if (this.#giftDialogOpen) {
      this.#rememberGiftFocus(".srt-gift-submit");
    }

    const updater = this.#mapDomUpdater();
    if (updater) {
      const delta = detectMapRankProgressDelta(this.#data, data);
      if (delta) {
        this.#applyExternalMapDelta(data.relationships, delta, updater);
        return;
      }
    }

    const rankUpId = detectMapRankIncrease(this.#relationships(), data?.relationships, this.#activeRelationshipId ?? this.#activeId());
    if (rankUpId) this.#setMapRankUpFx(rankUpId);
    await this.render({ force: false });
  }

  #mapDomUpdater() {
    if (this.#view !== APP_VIEWS.MAP || !this.#focusIsOwner() || !RelationshipMapDomUpdater.canPatch(this.element)) return null;
    const activeRelationship = this.#relationships().find(relationship => relationship.id === this.#activeId());
    return new RelationshipMapDomUpdater(this.element, {
      relationships: this.#relationships(),
      activeRelationshipId: this.#activeId(),
      canManage: canUsePlayerRankControls(
        typeof game !== "undefined" ? game.user : null,
        this.#ownerActor,
        activeRelationship
      ),
      localize: key => this.#localize(key),
      bondLabel: this.#terminology().singular,
      maxBondLabel: this.#terminology().maxLabel
    });
  }

  #applyExternalMapDelta(nextRelationships, delta, updater) {
    const nextById = new Map(nextRelationships.map(next => [next.id, next]));
    for (const id of delta.changedIds) {
      const rel = this.#relationships().find(r => r.id === id);
      const next = nextById.get(id);
      if (!rel || !next) continue;
      rel.rank = Number(next.rank) || 0;
      rel.rankProgress = Number(next.rankProgress) || 0;
    }

    let fxId = null;
    if (delta.rankUpIds.length > 0) {
      const activeId = this.#activeRelationshipId ?? this.#activeId();
      fxId = delta.rankUpIds.includes(activeId) ? activeId : delta.rankUpIds[0];
      this.#setMapRankUpFx(fxId);
    }
    updater.patchDelta(delta, { rankUpId: fxId });
  }

  /* ---------------------------------------------------------------- */
  /*  Render lifecycle                                                */
  /* ---------------------------------------------------------------- */

  /** @override */
  async _renderHTML(context, _options) {
    const theme = this.#currentTheme(context?.theme?.id ?? context?.profile?.themeId);
    const rendered = await renderTemplate(theme.template, context);
    const wrapper = document.createElement("div");
    wrapper.innerHTML = rendered;
    return wrapper;
  }

  /** @override */
  async _replaceHTML(result, content, _options) {
    content.innerHTML = result.innerHTML;
  }

  /** @override */
  async _onRender(_context, options) {
    const theme = this.#currentTheme(_context?.theme?.id);
    this.element.dataset.srtTheme = theme.id;
    this.element.style.setProperty("--srt-stage-w", `${theme.designWidth}px`);
    this.element.style.setProperty("--srt-stage-h", `${theme.designHeight}px`);
    this.#activeFontOverrideMap = applyThemeFontOverrides(
      this.element,
      _context?.profile?.themeId ?? theme.id
    );
    this.#observeDynamicFontTargets();

    if (options.isFirstRender) {
      this.#setupStageScaler();
    }
    this.#fitStage();
    const fitText = () => {
      this.#fitNameplate();
      this.#fitWipeShout();
    };
    if (typeof globalThis.requestAnimationFrame === "function") {
      globalThis.requestAnimationFrame(fitText);
    } else {
      setTimeout(fitText, 0);
    }
    const fontFitRequestId = ++this.#fontFitRequestId;
    const fontsReady = globalThis.document?.fonts?.ready;
    if (fontsReady && typeof fontsReady.then === "function") {
      void fontsReady.then(() => {
        if (fontFitRequestId !== this.#fontFitRequestId || !this.element?.isConnected) return;
        fitText();
      });
    }

    if (this.#keydownHandler) {
      this.element.removeEventListener("keydown", this.#keydownHandler);
    }
    this.#keydownHandler = this.#handleKeydown.bind(this);
    this.element.addEventListener("keydown", this.#keydownHandler);
    if (!this.element.hasAttribute("tabindex")) {
      this.element.setAttribute("tabindex", "-1");
    }
    this.#bindActionSfx();
    this.#bindGiftDialog();
    this.#bindListImageFallbacks();

    // Skip focus only when this render IS the manager's live preview for the
    // same owner actor; otherwise stealing focus would bury the manager under
    // the fullscreen preview (mirrors Stylish Shop ShopApp._onRender). A stale
    // override for a different actor must not suppress a normal open's focus.
    const isPreviewOverrideActiveForThisActor =
      !!_previewOverride &&
      _previewOverride.ownerActorUuid === this.#ownerActor?.uuid;
    if (!isPreviewOverrideActiveForThisActor && !this.#giftDialogOpen) {
      this.element.focus({ preventScroll: true });
    }
    this.#restoreDeferredFocus();

    this.#teardownMapPan();
    if (this.#view === APP_VIEWS.MAP) this.#setupMapPan();

    // Auto-dismiss the moment overlay, mirroring the prototype timing.
    if (this.#momentTimer) {
      clearTimeout(this.#momentTimer);
      this.#momentTimer = null;
    }
    if (this.#moment) {
      this.#momentTimer = setTimeout(() => {
        this.#momentTimer = null;
        this.#moment = null;
        this.render({ force: false });
      }, 2200);
    }

  }

  #bindListImageFallbacks() {
    for (const image of this.element.querySelectorAll("[data-srt-list-image]")) {
      const frame = image.closest("[data-srt-list-image-frame]");
      const revealCode = () => {
        image.remove();
        frame?.classList.remove("has-portrait");
      };
      image.addEventListener("error", revealCode, { once: true });
      if (image.complete && image.naturalWidth === 0) revealCode();
    }
  }

  #setupStageScaler() {
    if (this.#resizeObserver) return;
    this.#resizeObserver = new ResizeObserver(() => {
      this.#fitStage();
      this.#fitNameplate();
      this.#fitWipeShout();
    });
    this.#resizeObserver.observe(this.element);
  }

  #observeDynamicFontTargets() {
    if (typeof globalThis.MutationObserver !== "function" || !this.element) return;
    this.#fontObserver ??= new MutationObserver(mutations => {
      if (Object.keys(this.#activeFontOverrideMap).length === 0) return;
      for (const mutation of mutations) {
        for (const node of mutation.addedNodes) {
          if (!(node instanceof Element) || !node.isConnected) continue;
          applyFontOverridesToSubtree(node, this.#activeFontOverrideMap);
        }
      }
    });
    this.#fontObserver.disconnect();
    this.#fontObserver.observe(this.element, { childList: true, subtree: true });
  }

  #bindActionSfx() {
    if (this.#clickSfxHandler) {
      this.element.removeEventListener("click", this.#clickSfxHandler, true);
    }
    this.#clickSfxHandler = (event) => {
      const actionEl = event.target?.closest?.("[data-action]");
      if (!actionEl || !this.element.contains(actionEl)) return;
      if (actionEl.disabled === true || actionEl.getAttribute("aria-disabled") === "true") return;
      const soundKey = this.#soundKeyForAction(actionEl.dataset.action, actionEl);
      if (!soundKey || this.#isPanelInteriorCloseClick(actionEl, event)) return;
      const themeId = this.#currentTheme().id;
      playRelationshipSfx(soundKey, { themeId });
    };
    this.element.addEventListener("click", this.#clickSfxHandler, true);
  }

  /**
   * Keep the gift quantity input bounded by the selected item's max, which the
   * gift-dialog helper already clamped to the lowest of held/world/profile limits.
   * ApplicationV2 replaces the panel DOM each render, so the listener attaches to
   * the fresh element and needs no manual teardown.
   */
  #bindGiftDialog() {
    const select = this.element?.querySelector(".srt-gift-item");
    const qty = this.element?.querySelector(".srt-gift-qty");
    const text = this.element?.querySelector(".srt-gift-text");
    const day = this.element?.querySelector(".srt-gift-day");
    const search = this.element?.querySelector(".srt-gift-search");
    const selectedCard = this.element?.querySelector(".srt-gift-selected");
    if (!select && !search && !qty) return;
    const queue = typeof globalThis.queueMicrotask === "function"
      ? globalThis.queueMicrotask.bind(globalThis)
      : (fn) => setTimeout(fn, 0);
    const applyMax = () => {
      if (!qty) return;
      const option = select?.options?.[select.selectedIndex];
      const max = Number(option?.dataset?.maxQuantity ?? selectedCard?.dataset?.maxQuantity);
      if (Number.isFinite(max) && max > 0) {
        qty.max = String(max);
        if (Number(qty.value) > max) qty.value = String(max);
      }
      if (!Number.isFinite(Number(qty.value)) || Number(qty.value) < 1) qty.value = "1";
    };
    const captureDraft = () => this.#captureGiftDraftFromDialog();
    const refreshPreview = () => {
      captureDraft();
      if (this.#giftPreviewTimer) clearTimeout(this.#giftPreviewTimer);
      this.#giftPreviewPendingKey = null;
      this.#giftPreviewRequestId += 1;
      this.#giftPreviewTimer = setTimeout(() => {
        this.#giftPreviewTimer = null;
        void this.#refreshGiftPreviewFromDialog();
      }, GIFT_PREVIEW_DELAY_MS);
    };
    applyMax();
    select?.addEventListener("change", () => {
      applyMax();
      refreshPreview();
    });
    qty?.addEventListener("input", () => {
      applyMax();
      refreshPreview();
    });
    text?.addEventListener("input", captureDraft);
    day?.addEventListener("input", captureDraft);

    search?.addEventListener("input", () => {
      captureDraft();
      const nextQuery = search.value;
      if (this.#giftSearchTimer) clearTimeout(this.#giftSearchTimer);
      this.#giftSearchTimer = setTimeout(() => {
        this.#giftSearchTimer = null;
        if (!this.#giftDialogOpen || nextQuery === this.#giftItemQuery) return;
        this.#giftItemQuery = nextQuery;
        this.#giftItemPage = 1;
        this.#deferredFocusSelector = ".srt-gift-search";
        this.render({ force: false });
      }, GIFT_SEARCH_RENDER_DELAY_MS);
    });
    queue(() => void this.#refreshGiftPreviewFromDialog());
  }

  #patchGiftSelectionDom(card, item) {
    const root = this.element;
    const selected = root?.querySelector(".srt-gift-selected");
    if (!root || !card || !item || !selected) return false;

    for (const candidate of root.querySelectorAll("[data-gift-item-id]")) {
      const isSelected = candidate === card;
      candidate.classList.toggle("is-selected", isSelected);
      candidate.setAttribute("aria-pressed", isSelected ? "true" : "false");
    }

    const selectedImage = selected.querySelector('[class*="gift-selected-image"]');
    const cardImage = card.querySelector('[class*="gift-card-image"]');
    if (selectedImage && cardImage) {
      selectedImage.replaceChildren(...Array.from(cardImage.childNodes, node => node.cloneNode(true)));
    }

    const selectedCopy = selected.querySelector('[class*="gift-selected-copy"]');
    const type = selectedCopy?.querySelector("small");
    const name = selectedCopy?.querySelector("b");
    const quantity = selectedCopy?.querySelector(":scope > span");
    const fallbackType = {
      "arcane-grimoire": "OFFERING",
      "stellar-link": "CARGO PACKET",
      "adventurers-ledger": "FIELD SUPPLY"
    }[this.#currentTheme().id] ?? "ITEM";
    if (type) type.textContent = item.type || fallbackType;
    if (name) name.textContent = item.name || "";
    if (quantity) {
      quantity.textContent = item.singleUse
        ? this.#localize("editor.gift.archive.singleUseDetail")
        : `${this.#localize("editor.gift.archive.owned")} ${item.quantityLabel}`;
    }

    selected.dataset.maxQuantity = String(item.maxQuantity ?? 1);
    const qty = root.querySelector(".srt-gift-qty");
    if (qty) {
      qty.max = String(item.maxQuantity ?? 1);
      qty.value = String(this.#clampGiftDraftQuantity(qty.value, item.maxQuantity));
    }
    card.focus({ preventScroll: true });
    return true;
  }

  #patchGiftPreviewDom(preview) {
    const panel = this.element?.querySelector(".srt-gift-panel");
    const previewElement = panel?.querySelector([
      ".srt-gift-preview",
      ".srt-dp-gift-preview",
      ".srt-jr-gift-preview",
      ".srt-ag-gift-preview",
      ".srt-sl-gift-preview",
      ".srt-al-gift-preview"
    ].join(", "));
    if (!previewElement) return false;

    const baseClass = Array.from(previewElement.classList).find(className =>
      /^(?:srt-gift-preview|srt-(?:dp|jr|ag|sl|al)-gift-preview)$/.test(className)
    );
    if (!baseClass) return false;
    for (const className of Array.from(previewElement.classList)) {
      if (className.startsWith(`${baseClass}-`)) previewElement.classList.remove(className);
    }
    if (preview?.visibility) previewElement.classList.add(`${baseClass}-${preview.visibility}`);
    if (preview?.tone) previewElement.classList.add(`${baseClass}-${preview.tone}`);
    previewElement.hidden = preview?.visible !== true;

    const text = previewElement.querySelector('[class$="gift-preview-text"]');
    if (text) text.textContent = preview?.label ?? "";
    return true;
  }

  #rememberGiftFocus(fallback = "") {
    if (!this.#giftDialogOpen || !this.element) return;
    const active = document.activeElement;
    let selector = "";
    if (active && this.element.contains(active)) {
      if (active.matches?.(".srt-gift-search")) selector = ".srt-gift-search";
      else if (active.matches?.(".srt-gift-qty")) selector = ".srt-gift-qty";
      else if (active.matches?.(".srt-gift-text")) selector = ".srt-gift-text";
      else if (active.matches?.(".srt-gift-day")) selector = ".srt-gift-day";
      else if (active.closest?.(".srt-gift-card")) selector = ".srt-gift-card.is-selected";
      else {
        const action = active.closest?.("[data-action]")?.dataset?.action;
        if (["giftPagePrev", "giftPageNext", "clearGiftSearch", "submitGift", "closeGiftDialog"].includes(action)) {
          selector = `[data-action="${action}"]`;
        }
      }
    }
    this.#deferredFocusSelector = selector || fallback;
  }

  #restoreDeferredFocus() {
    const selector = this.#deferredFocusSelector;
    this.#deferredFocusSelector = null;
    if (!selector) return;
    const focus = () => {
      let target = this.element?.querySelector(selector);
      if ((!target || target.disabled) && this.#giftDialogOpen) {
        target = this.element?.querySelector(".srt-gift-search, .srt-gift-panel");
      }
      if (!target || target.disabled) return;
      target.focus({ preventScroll: true });
      if (target.matches?.("input, textarea")) {
        const end = String(target.value ?? "").length;
        target.setSelectionRange?.(end, end);
      }
    };
    if (typeof globalThis.requestAnimationFrame === "function") globalThis.requestAnimationFrame(focus);
    else setTimeout(focus, 0);
  }

  #trapGiftDialogFocus(event) {
    const panel = this.element?.querySelector(".srt-gift-panel");
    if (!panel) return;
    const focusable = Array.from(panel.querySelectorAll('button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'))
      .filter(element => !element.closest("[inert]"));
    if (focusable.length === 0) {
      event.preventDefault();
      panel.focus({ preventScroll: true });
      return;
    }
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    const active = document.activeElement;
    if (!panel.contains(active)) {
      event.preventDefault();
      (event.shiftKey ? last : first).focus({ preventScroll: true });
    } else if (event.shiftKey && active === first) {
      event.preventDefault();
      last.focus({ preventScroll: true });
    } else if (!event.shiftKey && active === last) {
      event.preventDefault();
      first.focus({ preventScroll: true });
    }
  }

  #captureGiftDraftFromDialog() {
    const rel = this.#viewActiveRelationship();
    const root = this.element;
    if (!rel || !root) return null;
    const select = root.querySelector(".srt-gift-item");
    const qty = root.querySelector(".srt-gift-qty");
    const option = select?.options?.[select.selectedIndex];
    const selectedCard = root.querySelector(".srt-gift-selected");
    const itemId = select?.value ?? this.#giftDraft?.itemId ?? "";
    const maxQuantity = option?.dataset?.maxQuantity ?? selectedCard?.dataset?.maxQuantity;
    const quantity = this.#clampGiftDraftQuantity(qty?.value ?? this.#giftDraft?.quantity ?? 1, maxQuantity);
    const draft = {
      relationshipId: rel.id,
      itemId,
      quantity,
      eventText: root.querySelector(".srt-gift-text")?.value ?? this.#giftDraft?.eventText ?? "",
      day: root.querySelector(".srt-gift-day")?.value ?? this.#giftDraft?.day ?? ""
    };
    this.#giftDraft = draft;
    return draft;
  }

  async #refreshGiftPreviewFromDialog() {
    if (this.#giftSubmitting || !this.#giftDialogOpen || this.#view !== APP_VIEWS.ARCHIVE) return;
    const rel = this.#viewActiveRelationship();
    const giverActor = this.#ownerActor;
    const draft = this.#captureGiftDraftFromDialog() ?? this.#giftDraft;
    if (!rel || !giverActor || !draft?.itemId) return;

    const preference = buildGiftPreferenceView(rel);
    if (preference.visibility === GIFT_PREFERENCE_VISIBILITY.HIDDEN) {
      if (this.#giftPreview || this.#giftPreviewPendingKey) this.#clearGiftPreview();
      this.#patchGiftPreviewDom({ visible: false, visibility: preference.visibility, tone: "hidden", label: "" });
      return;
    }

    const payload = buildGiftDialogPayload({ itemId: draft.itemId, quantity: draft.quantity, giverActorUuid: giverActor.uuid });
    const selectionKey = [
      rel.id,
      payload.giverActorUuid,
      payload.itemId,
      payload.quantity,
      rel.rank,
      rel.rankProgress,
      rel.maxRank,
      preference.visibility
    ].join("|");
    if (this.#giftPreviewPendingKey === selectionKey || this.#giftPreview?.selectionKey === selectionKey) return;

    const requestId = this.#giftPreviewRequestId + 1;
    this.#giftPreviewRequestId = requestId;
    this.#giftPreviewPendingKey = selectionKey;
    this.#giftPreview = this.#giftPreviewLoadingView(rel.id, selectionKey, preference.visibility);
    if (!this.#patchGiftPreviewDom(this.#giftPreview)) {
      this.#rememberGiftFocus();
      await this.render({ force: false });
    }

    let result = null;
    try {
      result = await previewGift(giverActor, rel.id, payload);
    } catch (error) {
      console.warn(`${MODULE_ID} | Failed to preview gift`, error);
      result = { visibility: preference.visibility, error: true };
    }

    if (requestId !== this.#giftPreviewRequestId || this.#giftPreviewPendingKey !== selectionKey) return;
    this.#giftPreviewPendingKey = null;
    this.#giftPreview = this.#giftPreviewResultView(rel.id, selectionKey, result, preference.visibility);
    if (!this.#patchGiftPreviewDom(this.#giftPreview)) {
      this.#rememberGiftFocus();
      await this.render({ force: false });
    }
  }

  syncGiftInventoryChange(actor) {
    if (!this.#giftDialogOpen || this.#giftSubmitting || actor?.uuid !== this.#ownerActorUuid) return;
    this.#giftItemOptionsCache = null;
    this.#clearGiftPreview();
    if (this.#giftInventoryRenderTimer) clearTimeout(this.#giftInventoryRenderTimer);
    this.#giftInventoryRenderTimer = setTimeout(() => {
      this.#giftInventoryRenderTimer = null;
      if (!this.#giftDialogOpen || this.#giftSubmitting || actor?.uuid !== this.#ownerActorUuid) return;
      this.#rememberGiftFocus();
      void this.render({ force: false });
    }, 50);
  }

  syncGiftItemFilterChange() {
    if (this.#giftSubmitting) return;
    this.#giftItemOptionsCache = null;
    this.#giftItemPage = 1;
    this.#clearGiftPreview();
    if (this.#giftInventoryRenderTimer) clearTimeout(this.#giftInventoryRenderTimer);
    this.#giftInventoryRenderTimer = setTimeout(() => {
      this.#giftInventoryRenderTimer = null;
      if (this.#giftSubmitting) return;
      if (this.#giftDialogOpen) this.#rememberGiftFocus();
      void this.render({ force: false });
    }, 25);
  }

  #giftPreviewLoadingView(relationshipId, selectionKey, visibility) {
    return {
      relationshipId,
      selectionKey,
      visible: true,
      visibility,
      tone: "loading",
      label: this.#localize("editor.gift.archive.preview.loading")
    };
  }

  #giftPreviewResultView(relationshipId, selectionKey, result, fallbackVisibility) {
    const visibility = result?.visibility || fallbackVisibility;
    if (visibility === GIFT_PREFERENCE_VISIBILITY.HIDDEN) return { relationshipId, selectionKey, visible: false, visibility, tone: "hidden", label: "" };
    if (result?.error === true) {
      return { relationshipId, selectionKey, visible: true, visibility, tone: "unknown", label: this.#localize("editor.gift.archive.preview.error") };
    }
    const category = result?.blocked === true ? "blocked" : (result?.category || "unknown");
    const serverLabel = typeof result?.label === "string" ? result.label.trim() : "";
    if (visibility === GIFT_PREFERENCE_VISIBILITY.HINT) {
      return {
        relationshipId,
        selectionKey,
        visible: true,
        visibility,
        tone: category,
        label: serverLabel || this.#localize(`editor.gift.archive.preview.hint.${category}`)
      };
    }
    if (result?.blocked === true) {
      return { relationshipId, selectionKey, visible: true, visibility, tone: "blocked", label: serverLabel || this.#localize("editor.gift.archive.preview.full.blocked") };
    }
    const reaction = result?.reactionLabel || this.#localize("editor.gift.archive.preview.full.unknownReaction");
    const progress = Number.isFinite(Number(result?.totalProgressDelta)) ? Number(result.totalProgressDelta) : 0;
    return {
      relationshipId,
      selectionKey,
      visible: true,
      visibility,
      tone: category,
      label: serverLabel || this.#formatLocalize("editor.gift.archive.preview.full.result", { reaction, progress })
    };
  }

  /** A selectRelationship click inside the map area routes to MAP_NODE; every non-map selectRelationship keeps PAGE. */
  #soundKeyForAction(action, actionEl = null) {
    if (action === "selectRelationship" && actionEl?.closest?.(".srt-map-area")) {
      return SFX_KEYS.MAP_NODE;
    }
    return TRACKER_ACTION_SFX[action];
  }

  #isPanelInteriorCloseClick(actionEl, event) {
    if (!BACKDROP_CLOSE_ACTIONS.has(actionEl.dataset.action)) return false;
    if (event.target === actionEl || event.target?.closest?.("button")) return false;
    return !!event.target?.closest?.(OVERLAY_PANEL_SELECTOR);
  }

  #fitStage() {
    const wrap = this.element?.querySelector(".srt-stage-wrap");
    const stage = this.element?.querySelector(".srt-stage");
    if (!wrap || !stage) return;
    const w = wrap.clientWidth;
    const h = wrap.clientHeight;
    if (!w || !h) return;
    const theme = this.#currentTheme(stage.dataset.theme);
    const scale = Math.min(w / theme.designWidth, h / theme.designHeight);
    stage.style.transform = `translate(-50%, -50%) scale(${scale})`;
  }

  /**
   * Shared measured-shrink for bold two-line type blocks. Mirrors Stylish Shop
   * ShopApp._fitWalletAmount(): reset the size custom properties, measure the
   * bounded box, step the primary and secondary font sizes down together until
   * the content fits, and restore the CSS defaults when no shrink is needed.
   *
   * @param {object} cfg
   * @param {string} cfg.box      Bounded measuring element selector.
   * @param {string} cfg.main     Primary line selector inside the box.
   * @param {string} cfg.sub      Secondary line selector inside the box.
   * @param {string} cfg.mainVar  Custom property driving the primary size.
   * @param {string} cfg.subVar   Custom property driving the secondary size.
   * @param {number} cfg.mainBase Fallback primary size when uncomputable.
   * @param {number} cfg.subBase  Fallback secondary size when uncomputable.
   * @param {number} cfg.minScale Lower bound for the shrink ratio.
   */
  #fitMeasuredText({ box, main, sub, mainVar, subVar, mainBase, subBase, minScale }) {
    const boxEl = this.element?.querySelector(box);
    if (!boxEl) return;
    const mainEl = boxEl.querySelector(main);
    if (!mainEl) return;
    const subEl = boxEl.querySelector(sub);

    boxEl.style.removeProperty(mainVar);
    boxEl.style.removeProperty(subVar);

    if (boxEl.clientWidth <= 0) return;

    const computedMain = parseFloat(getComputedStyle(mainEl).fontSize) || mainBase;
    const computedSub = subEl ? (parseFloat(getComputedStyle(subEl).fontSize) || subBase) : 0;

    let scale = 1;
    let guard = 200;
    while (
      guard-- > 0
      && scale > minScale
      && (boxEl.scrollWidth > boxEl.clientWidth + 1 || boxEl.scrollHeight > boxEl.clientHeight + 1)
    ) {
      scale -= 0.02;
      boxEl.style.setProperty(mainVar, `${(computedMain * scale).toFixed(2)}px`);
      if (subEl) {
        boxEl.style.setProperty(subVar, `${(computedSub * scale).toFixed(2)}px`);
      }
    }

    if (scale >= 1) {
      boxEl.style.removeProperty(mainVar);
      boxEl.style.removeProperty(subVar);
    }
  }

  #fitNameplate() {
    this.#fitMeasuredText({
      box: ".srt-nameplate .srt-big",
      main: ".srt-ko",
      sub: ".srt-en",
      mainVar: "--srt-name-main-size",
      subVar: "--srt-name-roman-size",
      mainBase: 56,
      subBase: 24,
      minScale: 0.4,
    });
  }

  #fitWipeShout() {
    this.#fitMeasuredText({
      box: ".srt-wipe-shout",
      main: ".srt-wipe-main",
      sub: "small",
      mainVar: "--srt-wipe-main-size",
      subVar: "--srt-wipe-sub-size",
      mainBase: 180,
      subBase: 38,
      minScale: 0.3,
    });
  }

  /* ---------------------------------------------------------------- */
  /*  Map panning                                                     */
  /* ---------------------------------------------------------------- */

  /**
   * Drag the empty map area to pan the larger .srt-map-world, and wheel over it to
   * zoom. Pointer deltas are converted from screen px to world px via the stage
   * scale and the current map zoom, clamped so the scaled world always covers the
   * viewport, and written to CSS custom properties so pointermove never
   * re-renders. A small drag threshold flags a real drag so the synthetic click
   * that follows is suppressed (click-vs-drag guard) and node selection / focus is
   * not triggered by a pan.
   */
  #setupMapPan() {
    const area = this.element?.querySelector(".srt-map-area");
    const world = this.element?.querySelector(".srt-map-world");
    if (!area || !world) return;
    world.style.setProperty("--srt-map-zoom", String(this.#mapZoom));
    this.#applyMapPan(world, area);
    this.#syncMapZoomControls();

    const DRAG_THRESHOLD = 5;
    let dragging = false;
    let moved = false;
    let startX = 0;
    let startY = 0;
    let baseX = 0;
    let baseY = 0;
    let scale = 1;

    const onDown = (ev) => {
      if (ev.button !== 0) return;
      if (ev.target?.closest?.("[data-action], button, a, .srt-map-node, .srt-map-player, .srt-map-focusbar")) return;
      dragging = true;
      moved = false;
      startX = ev.clientX;
      startY = ev.clientY;
      baseX = this.#mapPan.x;
      baseY = this.#mapPan.y;
      const rect = area.getBoundingClientRect();
      scale = area.offsetWidth ? rect.width / area.offsetWidth : 1;
      area.classList.add("is-panning");
      area.setPointerCapture?.(ev.pointerId);
    };
    const onMove = (ev) => {
      if (!dragging) return;
      const dxs = ev.clientX - startX;
      const dys = ev.clientY - startY;
      if (!moved && Math.hypot(dxs, dys) > DRAG_THRESHOLD) moved = true;
      const zoom = this.#mapZoom || 1;
      this.#mapPan.x = baseX + dxs / ((scale || 1) * zoom);
      this.#mapPan.y = baseY + dys / ((scale || 1) * zoom);
      this.#applyMapPan(world, area);
    };
    const onUp = (ev) => {
      if (!dragging) return;
      dragging = false;
      area.classList.remove("is-panning");
      area.releasePointerCapture?.(ev.pointerId);
      this.#mapDragMoved = moved;
    };
    const onClickCapture = (ev) => {
      if (!this.#mapDragMoved) return;
      ev.stopPropagation();
      ev.preventDefault();
      this.#mapDragMoved = false;
    };
    const onWheel = (ev) => {
      if (ev.target?.closest?.("[data-action], button, a, .srt-map-node, .srt-map-player, .srt-map-focusbar, .srt-map-zoom")) return;
      ev.preventDefault();
      const direction = ev.deltaY < 0 ? 1 : -1;
      this.#setMapZoom(this.#mapZoom + direction * MAP_ZOOM_STEP);
    };

    area.addEventListener("pointerdown", onDown);
    area.addEventListener("pointermove", onMove);
    area.addEventListener("pointerup", onUp);
    area.addEventListener("pointercancel", onUp);
    area.addEventListener("click", onClickCapture, true);
    area.addEventListener("wheel", onWheel, { passive: false });
    this.#mapPointerHandlers = { area, onDown, onMove, onUp, onClickCapture, onWheel };
  }

  #applyMapPan(world, area) {
    const zoom = this.#mapZoom || 1;
    const scaledMaxX = Math.max(0, ((world.offsetWidth || 0) * zoom - (area?.offsetWidth || 0)) / 2);
    const scaledMaxY = Math.max(0, ((world.offsetHeight || 0) * zoom - (area?.offsetHeight || 0)) / 2);
    const maxX = scaledMaxX / zoom;
    const maxY = scaledMaxY / zoom;
    this.#mapPan.x = Math.max(-maxX, Math.min(maxX, this.#mapPan.x));
    this.#mapPan.y = Math.max(-maxY, Math.min(maxY, this.#mapPan.y));
    world.style.setProperty("--srt-map-pan-x", `${(this.#mapPan.x * zoom).toFixed(1)}px`);
    world.style.setProperty("--srt-map-pan-y", `${(this.#mapPan.y * zoom).toFixed(1)}px`);
  }

  #teardownMapPan() {
    const handlers = this.#mapPointerHandlers;
    if (!handlers) return;
    const { area, onDown, onMove, onUp, onClickCapture, onWheel } = handlers;
    area.removeEventListener("pointerdown", onDown);
    area.removeEventListener("pointermove", onMove);
    area.removeEventListener("pointerup", onUp);
    area.removeEventListener("pointercancel", onUp);
    area.removeEventListener("click", onClickCapture, true);
    if (onWheel) area.removeEventListener("wheel", onWheel);
    this.#mapPointerHandlers = null;
  }

  static #onMapZoomIn() {
    this.#setMapZoom(this.#mapZoom + MAP_ZOOM_STEP);
  }

  static #onMapZoomOut() {
    this.#setMapZoom(this.#mapZoom - MAP_ZOOM_STEP);
  }

  static #onMapZoomReset() {
    this.#setMapZoom(1);
  }

  /** Apply a clamped zoom to .srt-map-world via CSS vars and re-clamp the pan, without a re-render. */
  #setMapZoom(nextZoom) {
    const raw = Math.max(MAP_ZOOM_MIN, Math.min(MAP_ZOOM_MAX, Number(nextZoom) || 1));
    this.#mapZoom = Math.round(raw * 100) / 100;
    const world = this.element?.querySelector(".srt-map-world");
    const area = this.element?.querySelector(".srt-map-area");
    if (!world) return;
    world.style.setProperty("--srt-map-zoom", String(this.#mapZoom));
    if (area) this.#applyMapPan(world, area);
    this.#syncMapZoomControls();
  }

  /** Mirror the current zoom into the control label and disable the +/- buttons at the bounds. */
  #syncMapZoomControls() {
    const root = this.element;
    if (!root) return;
    const label = root.querySelector(".srt-map-zoom-label");
    if (label) label.textContent = `${Math.round(this.#mapZoom * 100)}%`;
    const zoomOut = root.querySelector('[data-action="mapZoomOut"]');
    const zoomIn = root.querySelector('[data-action="mapZoomIn"]');
    if (zoomOut) zoomOut.disabled = this.#mapZoom <= MAP_ZOOM_MIN + 1e-6;
    if (zoomIn) zoomIn.disabled = this.#mapZoom >= MAP_ZOOM_MAX - 1e-6;
  }

  /* ---------------------------------------------------------------- */
  /*  Keyboard                                                        */
  /* ---------------------------------------------------------------- */

  #handleKeydown(event) {
    if (event.repeat) return;

    if (this.#giftDialogOpen && event.key === "Tab") {
      this.#trapGiftDialogFocus(event);
      return;
    }

    const isFormControl = event.target?.matches?.("input, textarea, select");
    if (isFormControl && !(this.#giftDialogOpen && event.key === "Escape")) return;

    // Overlays capture keys first: Enter/Space/Escape dismiss them.
    if (this.#sceneRecall) {
      if (event.key === "Enter" || event.key === " " || event.key === "Escape") {
        event.preventDefault();
        this.#sceneRecall = null;
        this.render({ force: false });
      }
      return;
    }
    if (this.#moment) {
      if (event.key === "Enter" || event.key === " " || event.key === "Escape") {
        event.preventDefault();
        this.#dismissMomentNow();
      }
      return;
    }
    // Dossier captures keys: Escape closes; all others return so arrows/A do not cycle behind it.
    if (this.#dossierOpen) {
      if (event.key === "Escape") {
        event.preventDefault();
        this.#closeDossierNow();
      }
      return;
    }
    if (this.#eventLogOpen) {
      if (event.key === "Escape") {
        event.preventDefault();
        this.#closeEventLogNow();
      }
      return;
    }
    if (this.#giftDialogOpen) {
      if (this.#giftSubmitting) return;
      if (event.key === "Escape" || event.key === "b" || event.key === "B") {
        event.preventDefault();
        this.#resetGiftDialog();
        this.#deferredFocusSelector = '[data-action="openGiftDialog"]';
        this.render({ force: false });
      } else if (event.key === "g" || event.key === "G") {
        event.preventDefault();
        void this.#submitGift();
      }
      return;
    }

    switch (event.key) {
      case "ArrowUp":
        event.preventDefault();
        this.#cycle(-1);
        break;
      case "ArrowDown":
        event.preventDefault();
        this.#cycle(1);
        break;
      case "a":
      case "A": {
        event.preventDefault();
        if (this.#mapControlsActive()) {
          const focusRel = (this.#focusRelationships ?? []).find(r => r.id === this.#mapFocusActiveId);
          if (focusRel?.locked === true) void this.#triggerFocusUnlock();
          else void this.#triggerFocusRank(1);
          break;
        }
        const keyRel = this.#relationships().find(r => r.id === this.#activeId());
        if (keyRel?.locked === true && this.#canUnlock()) void this.#triggerUnlock();
        else void this.#triggerRankUp();
        break;
      }
      case "Escape":
        event.preventDefault();
        if (this.#mapControlsActive()) void this.#focusBack();
        else this.close();
        break;
      default:
        break;
    }
  }

  #cycle(direction) {
    if (this.#mapControlsActive()) return this.#cycleFocus(direction);
    const ids = this.#listRelationships().map(r => r.id);
    if (ids.length === 0) return;
    const current = this.#activeId();
    const idx = Math.max(0, ids.indexOf(current));
    const next = (idx + direction + ids.length) % ids.length;
    this.#activeRelationshipId = ids[next];
    this.#animateNext = true;
    this.#resetDossier();
    this.#resetEventLog();
    this.#resetGiftDialog();
    this.render({ force: false });
  }

  #cycleFocus(direction) {
    const ids = (this.#focusRelationships ?? []).map(r => r.id);
    if (ids.length === 0) return;
    const idx = Math.max(0, ids.indexOf(this.#mapFocusActiveId));
    this.#mapFocusActiveId = ids[(idx + direction + ids.length) % ids.length];
    this.render({ force: false });
  }

  async #triggerRankUp() {
    if (this.#localRankChangeInProgress) return;
    if (this.#mapControlsActive()) return void this.#triggerFocusRank(1);
    const rel = this.#relationships().find(r => r.id === this.#activeId());
    if (!canUsePlayerRankControls(typeof game !== "undefined" ? game.user : null, this.#ownerActor, rel)) return;
    if (!rel || rel.locked || !canMoveRelationshipAxis(rel, 1)) return;
    const oldPositiveRank = relationshipEffectivePolarity(rel) === "positive" ? rel.rank : 0;

    if (!this.#ownerActor) return;
    const previousData = JSON.parse(JSON.stringify(this.#data));
    let didRankUp = false;
    let freshData = null;
    this.#localRankChangeInProgress = true;
    try {
      const updatedRelationship = await rankRelationship(this.#ownerActor, rel.id, 1);
      if (!updatedRelationship) return;
      rel.polarity = updatedRelationship.polarity;
      rel.rank = updatedRelationship.rank;
      rel.maxRank = updatedRelationship.maxRank;
      rel.rankProgress = updatedRelationship.rankProgress;
      didRankUp = relationshipEffectivePolarity(updatedRelationship) === "positive"
        && updatedRelationship.rank > oldPositiveRank;
      freshData = await getRelationshipData(this.#ownerActor);
    } catch (error) {
      console.error(`${MODULE_ID} | Failed to persist relationship rank change`, error);
      if (typeof ui !== "undefined") ui.notifications.error(this.#localize("notify.saveFailed"));
      return;
    } finally {
      this.#localRankChangeInProgress = false;
    }
    const updater = this.#mapDomUpdater();
    if (updater) {
      const delta = detectMapRankProgressDelta(previousData, freshData);
      if (delta) {
        this.#applyExternalMapDelta(freshData.relationships, delta, updater);
        return;
      }
    }
    // rankRelationship broadcasts the cut-in only on an actual rank-up, so the local
    // #moment overlay is skipped here to avoid a duplicate celebration. A preview
    // override shadows fresh storage, so rendering would repaint a stale snapshot.
    if (didRankUp) this.#setMapRankUpFx(rel.id);
    if (!this.#hasActivePreviewOverride()) await this.render({ force: false });
  }

  #setMapRankUpFx(relationshipId) {
    if (this.#mapFxTimer) {
      clearTimeout(this.#mapFxTimer);
      this.#mapFxTimer = null;
    }
    this.#mapFx = { relationshipId, at: Date.now() };
    this.#mapFxTimer = setTimeout(() => {
      this.#mapFxTimer = null;
      this.#mapFx = null;
      const updater = this.#mapDomUpdater();
      if (updater) updater.clearRankUpFx();
      else this.render({ force: false });
    }, 1700);
  }

  static #onUnlockBond() {
    if (this.#mapControlsActive()) void this.#triggerFocusUnlock();
    else void this.#triggerUnlock();
  }

  async #triggerUnlock() {
    if (this.#mapControlsActive()) return void this.#triggerFocusUnlock();
    if (!this.#canUnlock()) return;
    const rel = this.#relationships().find(r => r.id === this.#activeId());
    if (!rel || rel.locked !== true) return;

    if (!this.#ownerActor) return;
    try {
      const updated = await unlockRelationship(this.#ownerActor, rel.id);
      if (!updated) return;
      rel.locked = false;
    } catch (error) {
      console.error(`${MODULE_ID} | Failed to unlock relationship`, error);
      if (typeof ui !== "undefined") ui.notifications.error(this.#localize("notify.saveFailed"));
      return;
    }
    this.#animateNext = true;
    if (!this.#hasActivePreviewOverride()) await this.render({ force: false });
  }

  #dismissMomentNow() {
    if (this.#momentTimer) {
      clearTimeout(this.#momentTimer);
      this.#momentTimer = null;
    }
    this.#moment = null;
    this.render({ force: false });
  }

  /* ---------------------------------------------------------------- */
  /*  Action handlers                                                 */
  /* ---------------------------------------------------------------- */

  static #onSelectRelationship(_event, target) {
    const id = target.closest("[data-relationship-id]")?.dataset.relationshipId;
    if (!id) return;

    if (this.#mapControlsActive()) {
      const rel = (this.#focusRelationships ?? []).find(r => r.id === id);
      if (!rel) return;
      if (rel.locked && !this.#canManage(this.#mapControlActor)) return;
      if (id === this.#mapFocusActiveId) return;
      this.#mapFocusActiveId = id;
      if (this.#focusIsOwner()) {
        this.#activeRelationshipId = id;
        this.#relationshipListKind = relationshipListKindFor(rel);
      }
      this.render({ force: false });
      return;
    }

    const rel = this.#relationships().find(r => r.id === id);
    if (!rel) return;
    if (rel.locked && !canUnlockRelationshipWithGift(rel) && !this.#canManage()) return;
    if (id === this.#activeRelationshipId) return;
    this.#relationshipListKind = relationshipListKindFor(rel);
    this.#activeRelationshipId = id;
    this.#animateNext = true;
    this.#resetDossier();
    this.#resetEventLog();
    this.#resetGiftDialog();
    this.render({ force: false });
  }

  static #onFocusNode(event, target) {
    void this.#focusOnNode(event, target);
  }

  async #focusOnNode(_event, target) {
    const uuid = target.closest("[data-focus-uuid]")?.dataset.focusUuid;
    if (!uuid || uuid === this.#focusActorUuid) return;
    if (this.#focusIsOwner() && uuid === this.#ownerActorUuid) return;
    const actor = await resolveActor(uuid);
    const user = typeof game !== "undefined" ? game.user : null;
    if (!actor || !canViewRelationships(user, actor)) {
      if (typeof ui !== "undefined") ui.notifications?.warn?.(this.#localize("STYLISH_RELATIONSHIP_TRACKER.map.focusDenied"));
      return;
    }
    this.#focusStack.push(this.#focusActorUuid || this.#ownerActorUuid);
    this.#focusActorUuid = uuid;
    this.#focusActor = actor;
    this.#mapFocusActiveId = null;
    this.#resetMapViewport();
    this.#resetViewOverlays();
    await this.render({ force: false });
  }

  /** Close any active per-relationship overlay so a focus change cannot leave a stale one open. */
  #resetViewOverlays() {
    this.#sceneRecall = null;
    this.#resetDossier();
    this.#resetEventLog();
    this.#resetGiftDialog();
  }

  static #onFocusBack() {
    void this.#focusBack();
  }

  async #focusBack() {
    const prev = this.#focusStack.pop();
    if (!prev || prev === this.#ownerActorUuid) {
      this.#focusActorUuid = null;
      this.#focusActor = null;
    } else {
      const actor = await resolveActor(prev);
      const user = typeof game !== "undefined" ? game.user : null;
      if (actor && canViewRelationships(user, actor)) {
        this.#focusActorUuid = prev;
        this.#focusActor = actor;
      } else {
        this.#focusActorUuid = null;
        this.#focusActor = null;
        this.#focusStack = [];
      }
    }
    this.#mapFocusActiveId = null;
    this.#resetMapViewport();
    this.#resetViewOverlays();
    await this.render({ force: false });
  }

  static #onCyclePrev() {
    this.#cycle(-1);
  }

  static #onCycleNext() {
    this.#cycle(1);
  }

  static #onRankUp() {
    void this.#triggerRankUp();
  }

  static #onOpenSceneRecall(_event, target) {
    const eventEl = target.closest("[data-event-id]");
    const eventId = eventEl?.dataset.eventId;
    const relationshipId = eventEl?.dataset.relationshipId ?? this.#viewActiveId();
    if (!eventId || !relationshipId) return;
    this.#sceneRecall = { relationshipId, eventId };
    this.#animateSceneNext = true;
    this.render({ force: false });
  }

  static #onCloseSceneRecall(event, _target) {
    const isCloseButton = !!event.target?.closest?.(".srt-scene-close, .srt-dp-scene-close, .srt-jr-scene-close, .srt-al-scene-close");
    if (!isCloseButton) {
      const panel = event.target?.closest?.(".srt-scene-panel, .srt-dp-scene-panel, .srt-jr-scene-panel, .srt-al-scene-panel");
      if (panel) return;
    }
    this.#sceneRecall = null;
    this.render({ force: false });
  }

  static #onDismissMoment() {
    this.#dismissMomentNow();
  }

  static #onOpenDossier() {
    const active = this.#viewActiveRelationship();
    if (!active || active.locked === true) return;
    this.#dossierOpen = true;
    this.render({ force: false });
  }

  static #onCloseDossier(event, _target) {
    const isCloseButton = !!event.target?.closest?.(".srt-dossier-close, .srt-dp-dossier-close, .srt-jr-dossier-close, .srt-al-dossier-close");
    if (!isCloseButton) {
      const panel = event.target?.closest?.(".srt-dossier-panel, .srt-dp-dossier-panel, .srt-jr-dossier-panel, .srt-al-dossier-panel");
      if (panel) return;
    }
    this.#closeDossierNow();
  }

  static #onSelectDossierTab(_event, target) {
    const key = target.closest("[data-dossier-tab]")?.dataset.dossierTab;
    if (!key) return;
    this.#dossierTab = key;
    this.render({ force: false });
  }

  static #onOpenEventLog() {
    const active = this.#viewActiveRelationship();
    if (!active || active.locked === true) return;
    const events = Array.isArray(active.events) ? active.events : [];
    if (events.length === 0) return;
    this.#eventLogOpen = true;
    this.render({ force: false });
  }

  static #onCloseEventLog(event, _target) {
    const isCloseButton = !!event.target?.closest?.(".srt-eventlog-close, .srt-dp-eventlog-close, .srt-jr-eventlog-close, .srt-al-eventlog-close");
    if (!isCloseButton) {
      const panel = event.target?.closest?.(".srt-eventlog-panel, .srt-dp-eventlog-panel, .srt-jr-eventlog-panel, .srt-al-eventlog-panel");
      if (panel) return;
    }
    this.#closeEventLogNow();
  }

  static #onOpenGiftDialog() {
    if (!this.#canOpenGiftDialog()) return;
    this.#giftDraft = null;
    this.#giftItemQuery = "";
    this.#giftItemPage = 1;
    this.#deferredFocusSelector = ".srt-gift-search";
    this.#giftItemOptionsCache = null;
    this.#giftSubmitting = false;
    this.#clearGiftPreview();
    this.#giftDialogOpen = true;
    this.render({ force: false });
  }

  static #onSelectRelationshipListTab(_event, target) {
    const requested = target.closest("[data-relationship-list-kind]")?.dataset.relationshipListKind;
    if (!Object.values(RELATIONSHIP_LIST_KINDS).includes(requested)) return;
    const kind = normalizeRelationshipListKind(requested);
    const rels = relationshipsForListKind(this.#relationships(), kind);
    if (kind === this.#relationshipListKind || rels.length === 0) return;

    this.#relationshipListKind = kind;
    const next = rels.find(rel => !rel.locked) ?? rels[0] ?? null;
    this.#activeRelationshipId = next?.id ?? null;
    this.#animateNext = true;
    this.#resetDossier();
    this.#resetEventLog();
    this.#resetGiftDialog();
    this.render({ force: false });
  }

  static #onCloseGiftDialog(event, _target) {
    if (this.#giftSubmitting) return;
    const isCloseButton = !!event.target?.closest?.(".srt-gift-close");
    if (!isCloseButton) {
      const panel = event.target?.closest?.(".srt-gift-panel");
      if (panel) return;
    }
    this.#resetGiftDialog();
    this.#deferredFocusSelector = '[data-action="openGiftDialog"]';
    this.render({ force: false });
  }

  static #onSelectGiftItem(_event, target) {
    if (this.#giftSubmitting) return;
    const card = target.closest?.("[data-gift-item-id]");
    const itemId = card?.dataset?.giftItemId ?? "";
    if (!itemId || card?.disabled === true) return;
    const rel = this.#viewActiveRelationship();
    if (!rel) return;
    const current = this.#captureGiftDraftFromDialog() ?? this.#giftDraft ?? {};
    this.#giftDraft = {
      relationshipId: rel.id,
      itemId,
      quantity: this.#clampGiftDraftQuantity(current.quantity ?? 1, card.dataset.maxQuantity),
      eventText: current.eventText ?? "",
      day: current.day ?? ""
    };
    this.#clearGiftPreview();
    const item = this.#giftItemOptionsCache?.find(candidate => candidate.id === itemId) ?? null;
    if (!this.#patchGiftSelectionDom(card, item)) {
      this.#deferredFocusSelector = ".srt-gift-card.is-selected";
      this.render({ force: false });
      return;
    }
    void this.#refreshGiftPreviewFromDialog();
  }

  static #onGiftPagePrev() {
    if (this.#giftSubmitting) return;
    this.#captureGiftDraftFromDialog();
    this.#giftItemPage = Math.max(1, this.#giftItemPage - 1);
    this.#deferredFocusSelector = '[data-action="giftPagePrev"]';
    this.render({ force: false });
  }

  static #onGiftPageNext() {
    if (this.#giftSubmitting) return;
    this.#captureGiftDraftFromDialog();
    this.#giftItemPage += 1;
    this.#deferredFocusSelector = '[data-action="giftPageNext"]';
    this.render({ force: false });
  }

  static #onClearGiftSearch() {
    if (this.#giftSubmitting) return;
    this.#captureGiftDraftFromDialog();
    if (this.#giftSearchTimer) {
      clearTimeout(this.#giftSearchTimer);
      this.#giftSearchTimer = null;
    }
    this.#giftItemQuery = "";
    this.#giftItemPage = 1;
    this.#deferredFocusSelector = ".srt-gift-search";
    this.render({ force: false });
  }

  static #onSubmitGift() {
    void this.#submitGift();
  }

  async #submitGift() {
    if (this.#giftSubmitting) return;
    if (!this.#canOpenGiftDialog()) {
      this.#giftItemOptionsCache = null;
      this.#clearGiftPreview();
      if (typeof ui !== "undefined") ui.notifications?.warn?.(this.#localize("notify.giftNoItem"));
      await this.render({ force: false });
      return;
    }
    const rel = this.#viewActiveRelationship();
    const giverActor = this.#ownerActor;
    const draft = this.#captureGiftDraftFromDialog();
    const itemId = draft?.itemId ?? "";
    if (!itemId) {
      if (typeof ui !== "undefined") ui.notifications?.warn?.(this.#localize("notify.giftNoItem"));
      return;
    }
    const payload = buildGiftDialogPayload({
      itemId,
      quantity: draft?.quantity,
      giverActorUuid: giverActor.uuid,
      eventText: draft?.eventText ?? "",
      day: draft?.day ?? ""
    });

    this.#giftSubmitting = true;
    if (this.#giftPreviewTimer) {
      clearTimeout(this.#giftPreviewTimer);
      this.#giftPreviewTimer = null;
    }
    if (this.#giftSearchTimer) {
      clearTimeout(this.#giftSearchTimer);
      this.#giftSearchTimer = null;
    }
    const submitButton = this.element?.querySelector(".srt-gift-submit");
    const giftPanel = this.element?.querySelector(".srt-gift-panel");
    if (submitButton) {
      submitButton.disabled = true;
      submitButton.setAttribute("aria-busy", "true");
    }
    giftPanel?.classList.add("is-submitting");
    giftPanel?.setAttribute("aria-busy", "true");
    giftPanel?.querySelector(".srt-gift-body")?.setAttribute("inert", "");
    const closeButton = giftPanel?.querySelector(".srt-gift-close");
    if (closeButton) closeButton.disabled = true;
    giftPanel?.focus({ preventScroll: true });

    const releaseRankCutins = RankUpOverlay.hold();
    let result = null;
    try {
      result = await giveGift(giverActor, rel.id, payload);
    } catch (error) {
      releaseRankCutins();
      this.#giftSubmitting = false;
      this.#giftItemOptionsCache = null;
      if (submitButton?.isConnected) {
        submitButton.disabled = false;
        submitButton.removeAttribute("aria-busy");
      }
      console.error(`${MODULE_ID} | Failed to give gift`, error);
      if (typeof ui !== "undefined") ui.notifications?.error?.(this.#localize("notify.giftFailed"));
      this.#deferredFocusSelector = ".srt-gift-submit";
      await this.render({ force: false });
      return;
    }

    if (result?.approvalStatus === "pending") {
      releaseRankCutins();
      const alreadyPending = result.alreadyPending === true;
      this.#resetGiftDialog();
      if (typeof ui !== "undefined" && ui.notifications) {
        const key = alreadyPending
          ? "STYLISH_RELATIONSHIP_TRACKER.giftApproval.alreadyPendingPlayer"
          : "STYLISH_RELATIONSHIP_TRACKER.giftApproval.pendingPlayer";
        ui.notifications.info(game.i18n.localize(key));
      }
      await this.render({ force: false });
      this.element?.querySelector('[data-action="openGiftDialog"]')?.focus({ preventScroll: true });
      return;
    }

    this.#resetGiftDialog();
    const itemName = result?.event?.gift?.itemName || this.#localize("editor.gift.genericItem");
    if (typeof ui !== "undefined" && ui.notifications) {
      const message = typeof game !== "undefined" && typeof game.i18n?.format === "function"
        ? game.i18n.format("STYLISH_RELATIONSHIP_TRACKER.notify.giftGiven", { name: itemName })
        : itemName;
      ui.notifications.info(message);
    }
    try {
      await this.render({ force: false });
      this.element?.querySelector('[data-action="openGiftDialog"]')?.focus({ preventScroll: true });
      this.#showGiftReaction(rel, result, { releaseRankCutins });
    } catch (error) {
      releaseRankCutins();
      throw error;
    }
  }

  static async #onCloseApp() {
    await this.close();
  }

  static async #onToggleFullscreen() {
    this.#isFullscreen = !this.#isFullscreen;

    const vw = window.innerWidth;
    const vh = window.innerHeight;
    if (this.#isFullscreen) {
      this.setPosition({ width: vw, height: vh, left: 0, top: 0 });
      this.element.classList.remove("srt-windowed");
    } else {
      this.setPosition({
        width: Math.max(960, Math.min(1280, vw - 100)),
        height: Math.max(540, Math.min(720, vh - 100)),
        left: Math.round(vw * 0.1),
        top: Math.round(vh * 0.1)
      });
      this.element.classList.add("srt-windowed");
    }

    this.#fitStage();
    await this.render({ force: false });
  }

  static #onToggleView() {
    this.#view = this.#view === APP_VIEWS.MAP ? APP_VIEWS.ARCHIVE : APP_VIEWS.MAP;
    this.#sceneRecall = null;
    this.#resetDossier();
    this.#resetEventLog();
    this.#resetGiftDialog();
    this.#resetFocusToOwner();
    this.#animateNext = false;
    this.render({ force: false });
  }

  static #onRankDown() {
    void this.#triggerRankDown();
  }

  async #triggerRankDown() {
    if (this.#localRankChangeInProgress) return;
    if (this.#mapControlsActive()) return void this.#triggerFocusRank(-1);
    const rel = this.#relationships().find(r => r.id === this.#activeId());
    if (!canUsePlayerRankControls(typeof game !== "undefined" ? game.user : null, this.#ownerActor, rel)) return;
    if (!rel || rel.locked || !canMoveRelationshipAxis(rel, -1)) return;
    if (!this.#ownerActor) return;
    this.#localRankChangeInProgress = true;
    try {
      const updated = await rankRelationship(this.#ownerActor, rel.id, -1);
      if (!updated) return;
      rel.polarity = updated.polarity;
      rel.rank = updated.rank;
      rel.maxRank = updated.maxRank;
      rel.rankProgress = updated.rankProgress;
    } catch (error) {
      console.error(`${MODULE_ID} | Failed to persist relationship rank change`, error);
      if (typeof ui !== "undefined") ui.notifications.error(this.#localize("notify.saveFailed"));
      return;
    } finally {
      this.#localRankChangeInProgress = false;
    }
    await this.render({ force: false });
  }

  /**
   * Rank a relationship on a non-owner focus actor. The owner fast path keeps
   * its in-place DOM patch; a foreign focus actor simply re-renders the graph.
   */
  async #triggerFocusRank(direction) {
    if (this.#localRankChangeInProgress) return;
    const actor = this.#mapControlActor;
    const rel = (this.#focusRelationships ?? []).find(r => r.id === this.#mapFocusActiveId);
    if (!actor || !canUsePlayerRankControls(typeof game !== "undefined" ? game.user : null, actor, rel)) return;
    if (!rel) return;
    if (rel.locked || !canMoveRelationshipAxis(rel, direction)) return;
    const oldPositiveRank = relationshipEffectivePolarity(rel) === "positive" ? rel.rank : 0;
    this.#localRankChangeInProgress = true;
    try {
      const updated = await rankRelationship(actor, rel.id, direction);
      if (!updated) return;
      rel.polarity = updated.polarity;
      rel.rank = updated.rank;
      rel.maxRank = updated.maxRank;
      rel.rankProgress = updated.rankProgress;
      if (
        direction > 0
        && relationshipEffectivePolarity(updated) === "positive"
        && updated.rank > oldPositiveRank
      ) this.#setMapRankUpFx(rel.id);
    } catch (error) {
      console.error(`${MODULE_ID} | Failed to persist relationship rank change`, error);
      if (typeof ui !== "undefined") ui.notifications.error(this.#localize("notify.saveFailed"));
      return;
    } finally {
      this.#localRankChangeInProgress = false;
    }
    await this.render({ force: false });
  }

  async #triggerFocusUnlock() {
    const actor = this.#mapControlActor;
    if (!actor || !this.#canUnlock(actor)) return;
    const rel = (this.#focusRelationships ?? []).find(r => r.id === this.#mapFocusActiveId);
    if (!rel || rel.locked !== true) return;
    try {
      const updated = await unlockRelationship(actor, rel.id);
      if (!updated) return;
      rel.locked = false;
    } catch (error) {
      console.error(`${MODULE_ID} | Failed to unlock relationship`, error);
      if (typeof ui !== "undefined") ui.notifications.error(this.#localize("notify.saveFailed"));
      return;
    }
    await this.render({ force: false });
  }

  /* ---------------------------------------------------------------- */
  /*  Manager hand-off                                                */
  /* ---------------------------------------------------------------- */

  static async #onOpenManager() {
    const targetActor = this.#mapControlsActive() ? this.#mapControlActor : this.#ownerActor;
    if (!targetActor || !this.#canManage(targetActor)) return;
    const { RelationshipManagerApp } = await import("./RelationshipManagerApp.js");
    const focusId = this.#mapControlsActive() ? this.#mapFocusActiveId : this.#activeId();
    await RelationshipManagerApp.open(targetActor, { focusRelationshipId: focusId });
  }

  /* ---------------------------------------------------------------- */
  /*  Lifecycle teardown                                              */
  /* ---------------------------------------------------------------- */

  /** @override */
  async close(options = {}) {
    this.#teardownMapPan();
    if (this.#resizeObserver) {
      this.#resizeObserver.disconnect();
      this.#resizeObserver = null;
    }
    if (this.#fontObserver) {
      this.#fontObserver.disconnect();
      this.#fontObserver = null;
    }
    this.#activeFontOverrideMap = {};
    if (this.#keydownHandler && this.element) {
      this.element.removeEventListener("keydown", this.#keydownHandler);
      this.#keydownHandler = null;
    }
    if (this.#clickSfxHandler && this.element) {
      this.element.removeEventListener("click", this.#clickSfxHandler, true);
      this.#clickSfxHandler = null;
    }
    if (this.#momentTimer) {
      clearTimeout(this.#momentTimer);
      this.#momentTimer = null;
    }
    if (this.#mapFxTimer) {
      clearTimeout(this.#mapFxTimer);
      this.#mapFxTimer = null;
    }
    this.#mapFx = null;
    this.#resetGiftDialog();
    if (_openInstance === this) _openInstance = null;
    return super.close(options);
  }

  /* ---------------------------------------------------------------- */
  /*  Static factory                                                  */
  /* ---------------------------------------------------------------- */

  static open(actorOrUuid) {
    if (!actorOrUuid) throw new Error("RelationshipTrackerApp.open requires an Actor or UUID.");
    return RelationshipTrackerApp.openForActor(actorOrUuid);
  }

  static async openForActor(actorOrUuid, options = {}) {
    const focusRelationshipId = options.focusRelationshipId ?? null;
    const playOpenSfx = options.playOpenSfx !== false;
    const ownerActor = await resolveOwnerActor(actorOrUuid);
    const user = typeof game !== "undefined" ? game.user : null;
    if (!canViewRelationships(user, ownerActor)) {
      throw new Error("User cannot view relationships for this Actor.");
    }
    if (_openInstance && _openInstance.#ownerActorUuid === ownerActor.uuid) {
      if (focusRelationshipId && _openInstance.#activeRelationshipId !== focusRelationshipId) {
        _openInstance.#activeRelationshipId = focusRelationshipId;
        _openInstance.#animateNext = true;
      }
      await _openInstance.render({ force: true });
      if (playOpenSfx) playRelationshipSfx(SFX_KEYS.OPEN, { themeId: _openInstance.#data?.profile?.themeId });
      return _openInstance;
    }

    await RelationshipTrackerApp.#closeOpenInstanceAsync();
    const app = new RelationshipTrackerApp({ ownerActor });
    if (focusRelationshipId) app.#activeRelationshipId = focusRelationshipId;
    _openInstance = app;
    await app.render({
      force: true,
      position: { width: window.innerWidth, height: window.innerHeight, left: 0, top: 0 }
    });
    if (playOpenSfx) playRelationshipSfx(SFX_KEYS.OPEN, { themeId: app.#data?.profile?.themeId });
    return app;
  }

  static setPreviewOverride(ownerActorUuid, data) {
    if (!ownerActorUuid || !data) {
      _previewOverride = null;
      return;
    }
    _previewOverride = { ownerActorUuid, data };
    if (_openInstance?.#ownerActorUuid === ownerActorUuid && _openInstance.#giftDialogOpen && !_openInstance.#giftSubmitting) {
      _openInstance.#rememberGiftFocus();
      _openInstance.#giftItemOptionsCache = null;
      _openInstance.#clearGiftPreview();
    }
  }

  static clearPreviewOverride() {
    _previewOverride = null;
    if (_openInstance?.#giftDialogOpen && !_openInstance.#giftSubmitting) {
      _openInstance.#rememberGiftFocus();
      _openInstance.#giftItemOptionsCache = null;
      _openInstance.#clearGiftPreview();
    }
  }

  static getOpenInstance() {
    return _openInstance;
  }

  static hasOpenActorArchive() {
    return !!_openInstance;
  }

  static shouldShowGlobalRankUpOverlay(payload = null) {
    if (!_openInstance || _openInstance.#view !== APP_VIEWS.MAP) return true;
    const ownerActorUuid = typeof payload?.ownerActorUuid === "string" ? payload.ownerActorUuid : "";
    if (!ownerActorUuid) return true;
    const displayedActorUuid = _openInstance.#focusActorUuid || _openInstance.#ownerActorUuid;
    if (ownerActorUuid !== displayedActorUuid) return true;
    const relationshipId = typeof payload?.relationshipId === "string" ? payload.relationshipId : "";
    if (!relationshipId) return false;
    const displayedRelationships = _openInstance.#focusIsOwner()
      ? _openInstance.#relationships()
      : (_openInstance.#focusRelationships ?? []);
    return !displayedRelationships.some((relationship) => relationship?.id === relationshipId);
  }

  isForActor(actor) {
    return this.#ownerActorUuid === actor?.uuid;
  }

  isShowingActor(actor) {
    const uuid = actor?.uuid ?? actor;
    if (!uuid) return false;
    return uuid === this.#ownerActorUuid || uuid === this.#focusActorUuid;
  }

  referencesActor(actor) {
    const uuid = actor?.uuid ?? actor;
    if (!uuid) return false;
    if (this.isShowingActor(uuid)) return true;
    const ownerRelationships = this.#relationships();
    const focusRelationships = Array.isArray(this.#focusRelationships) ? this.#focusRelationships : [];
    return [...ownerRelationships, ...focusRelationships]
      .some((relationship) => relationship?.targetUuid === uuid);
  }

  #hasActivePreviewOverride() {
    return !!_previewOverride && _previewOverride.ownerActorUuid === this.#ownerActor?.uuid;
  }

  static #closeOpenInstance() {
    if (!_openInstance) return;
    const app = _openInstance;
    _openInstance = null;
    void app.close();
  }

  static async #closeOpenInstanceAsync() {
    if (!_openInstance) return;
    const app = _openInstance;
    _openInstance = null;
    await app.close();
  }
}
