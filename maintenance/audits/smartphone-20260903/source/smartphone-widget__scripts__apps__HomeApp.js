import { BaseApp } from "./BaseApp.js";
import { SmartphoneWidget } from "../smartphone-widget.js";
import { CalendarWidget } from "../widgets/CalendarWidget.js";
import { WeatherWidget } from "../widgets/WeatherWidget.js"; 
import { ClockWidget } from "../widgets/ClockWidget.js";
import { BioMonitorWidget } from "../widgets/BioMonitorWidget.js";
import { BankCardWidget } from "../widgets/BankCardWidget.js"; 
import { SearchWidget } from "../widgets/SearchWidget.js"; 
import { PhotoFrameWidget } from "../widgets/PhotoFrameWidget.js";
import { ActorSheetWidget } from "../widgets/ActorSheetWidget.js";

import { initializeSocket } from "./home/home-socket.js";
import { createDefinitionMethods } from "./home/home-definitions.js";
import { createRenderMethods } from "./home/home-render.js";
import { createListenerMethods } from "./home/home-listeners.js";
import { createContextMenuMethods } from "./home/home-context-menus.js";
import { createLayoutMethods } from "./home/home-layout.js";
import { createDragDropMethods } from "./home/home-drag-drop.js";
import { createWidgetMethods } from "./home/home-widgets.js";
import { createPageMethods } from "./home/home-pages.js";
import { createSearchMethods } from "./home/home-search.js";
import { createHookMethods } from "./home/home-hooks.js";

export class HomeApp extends BaseApp {
  constructor(widget) {
    super(widget);
    this.currentPage = 0;
    this.pages = [[]];
    this.draggedElement = null;
    this.draggedAppId = null;
    this.isSliding = false;
    this.pointerDown = false;
    this.isAppIconDragging = false;
    this.cols = 4;
    this.rows = 6;
    this.maxSlots = this.cols * this.rows;

    const internalWidgets = [
      CalendarWidget,
      WeatherWidget,
      ClockWidget, 
      BioMonitorWidget,
      BankCardWidget,
      SearchWidget,
      PhotoFrameWidget,
      ActorSheetWidget
    ];

    const externalWidgets = SmartphoneWidget.registeredWidgetClasses || [];
    this._initWidgetDefinitions(internalWidgets, externalWidgets);
    this.defaultApps = this._getDefaultApps();
  }
}

initializeSocket(HomeApp);

Object.assign(HomeApp.prototype, createDefinitionMethods(HomeApp));
Object.assign(HomeApp.prototype, createRenderMethods(HomeApp));
Object.assign(HomeApp.prototype, createListenerMethods(HomeApp));
Object.assign(HomeApp.prototype, createContextMenuMethods(HomeApp));
Object.assign(HomeApp.prototype, createLayoutMethods(HomeApp));
Object.assign(HomeApp.prototype, createDragDropMethods(HomeApp));
Object.assign(HomeApp.prototype, createWidgetMethods(HomeApp));
Object.assign(HomeApp.prototype, createPageMethods(HomeApp));
Object.assign(HomeApp.prototype, createSearchMethods(HomeApp));
Object.assign(HomeApp.prototype, createHookMethods(HomeApp));
