/**
 * App and widget definition methods for HomeApp
 */

import { SmartphoneWidget } from "../../smartphone-widget.js";

/**
 * Create definition-related methods
 * @param {HomeApp} HomeApp - The HomeApp class
 * @returns {Object} Methods to assign to prototype
 */
export const createDefinitionMethods = (HomeApp) => ({
  /**
   * Initialize widget definitions in constructor
   */
  _initWidgetDefinitions(internalWidgets, externalWidgets) {
    const allWidgetClasses = [...internalWidgets, ...externalWidgets];
    this.widgets = {};

    allWidgetClasses.forEach(widgetClass => {
      if (widgetClass.definitions) {
        widgetClass.definitions.forEach(def => {
          this.widgets[def.id] = {
            ...def,
            class: widgetClass,
            name: game.i18n.localize(def.name) !== def.name 
              ? game.i18n.localize(def.name) 
              : (def.defaultName || def.name)
          };
        });
      }
    });
  },

  /**
   * Get default apps array
   */
  _getDefaultApps() {
    return [
      {
        id: "phone",
        name: game.i18n.localize("SMARTPHONE.apps.home.phone"),
        icon: "fas fa-phone-alt",
        color: "#34C759",
        category: "utility", 
      },
      {
        id: "messages",
        name: game.i18n.localize("SMARTPHONE.apps.home.messages"),
        icon: "fas fa-comments",
        color: "#007AFF",
        category: "social", 
      },
      {
        id: "contacts",
        name: game.i18n.localize("SMARTPHONE.apps.home.contacts"),
        icon: "fas fa-address-book",
        color: "#4CD964",
        category: "utility", 
      },
      {
        id: "settings",
        name: game.i18n.localize("SMARTPHONE.apps.home.settings"),
        icon: "fas fa-cog",
        color: "#8E8E93",
        category: "utility", 
      },
      {
        id: "appstore",
        name: game.i18n.localize("SMARTPHONE.apps.home.appstore"),
        icon: "fas fa-store",
        color: "#007AFF",
        category: "utility", 
      },
      {
        id: "notes",
        name: game.i18n.localize("SMARTPHONE.apps.home.notes"),
        icon: "fas fa-sticky-note",
        color: "#FF9500",
        category: "utility", 
      },
      {
        id: "calculator",
        name: game.i18n.localize("SMARTPHONE.apps.home.calculator"),
        icon: "fas fa-calculator",
        color: "#FF9500",
        category: "utility", 
      },
      {
        id: "social",
        name: game.i18n.localize("SMARTPHONE.apps.home.social"),
        icon: "fas fa-images",
        color: "#E1306C",
        category: "social",
      },
      {
        id: "minefinder",
        name: game.i18n.localize("SMARTPHONE.apps.home.minefinder"),
        icon: "fas fa-bomb",
        color: "#FF4136",
        category: "game", 
      },
      {
        id: "checkers",
        name: game.i18n.localize("SMARTPHONE.apps.home.checkers"),
        icon: "fas fa-chess-board",
        color: "#1abc9c",
        category: "game", 
      },
      {
        id: "banking",
        name: game.i18n.localize("SMARTPHONE.apps.home.banking"),
        icon: "fas fa-university",
        color: "#5E5CE6",
        category: "utility",
      },
      {
        id: "wallet",
        name: game.i18n.localize("SMARTPHONE.apps.home.wallet"),
        icon: "fas fa-wallet",
        color: "#A2836E",
        category: "utility",
      },
      {
        id: "gacha",
        name: game.i18n.localize("SMARTPHONE.apps.home.gacha"),
        icon: "fas fa-gem",
        color: "#BF5AF2",
        category: "game", 
      },
      {
        id: "dice",
        name: game.i18n.localize("SMARTPHONE.apps.home.dice"),
        icon: "fas fa-dice",
        color: "#A2836E",
        category: "utility", 
      },
      {
        id: "calendar",
        name: game.i18n.localize("SMARTPHONE.apps.calendar.title"),
        icon: "fas fa-calendar-alt",
        color: "#3498DB",
        category: "utility", 
      },
      {
        id: "gallery",
        name: game.i18n.localize("SMARTPHONE.apps.gallery.title"),
        icon: "fas fa-photo-video",
        color: "linear-gradient(135deg, #A18CD1 0%, #FBC2EB 100%)",
        category: "utility",
      },
      {
        id: "weather",
        name: game.i18n.localize("SMARTPHONE.apps.weather.title"),
        icon: "fas fa-cloud-sun",
        color: "linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)", 
        category: "utility",
      }
    ];
  },

  /**
   * Get GM-configured default installed app IDs
   */
  getDefaultInstalledAppIds() {
    const configured = game.settings.get("smartphone-widget", "default-installed-apps");
    if (Array.isArray(configured)) return configured;
    return ["phone", "messages", "contacts", "settings", "appstore"];
  },

  /**
   * Get all app definitions including external, macros, and custom settings
   */
  getAllAppDefinitions() {
    const allApps = [...this.defaultApps];

    // Add external registered apps
    const externalApps = Array.from(SmartphoneWidget.appDefinitions.values());
    externalApps.forEach(extApp => {
      if (!allApps.some(app => app.id === extApp.id)) {
        allApps.push({ ...extApp });
      }
    });

    // Add macro apps if module is active
    const isMacroAppActive = game.modules.get("smartphone-macro-app")?.active;

    if (isMacroAppActive && this.pages) {
      const allIcons = this.pages.flat();
      allIcons.forEach(iconId => {
        if (iconId && iconId.startsWith('macro-')) {
          const macroId = iconId.replace('macro-', '');
          const macro = game.macros.get(macroId);

          if (macro) {
            allApps.push({
              id: iconId,
              name: macro.name,
              icon: macro.img || 'icons/svg/dice-target.svg',
              color: '#575757',
              isMacro: true,
              macroId: macroId
            });
          }
        }
      });
    }

    // Apply custom settings
    const customNames = game.settings.get("smartphone-widget", "app-names") || {};
    const customIcons = game.settings.get("smartphone-widget", "app-icons") || {};
    const transparentBg = game.settings.get("smartphone-widget", "app-transparent-bg") || {};

    for (const app of allApps) {
      if (customNames[app.id]) app.name = customNames[app.id];
      if (customIcons[app.id]) app.icon = customIcons[app.id];
      app.isTransparent = transparentBg[app.id] || false;
    }
    return allApps;
  }
});
