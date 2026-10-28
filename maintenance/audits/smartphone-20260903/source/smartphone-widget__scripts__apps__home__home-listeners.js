import { BioMonitorWidget } from "../../widgets/BioMonitorWidget.js";
import { PhotoFrameWidget } from "../../widgets/PhotoFrameWidget.js";
import { ActorSheetWidget } from "../../widgets/ActorSheetWidget.js";

export const createListenerMethods = (HomeApp) => ({
  _attachWidgetListeners() {
    this.element.querySelectorAll('.bio-settings-btn:not([data-listening])').forEach(btn => {
      btn.dataset.listening = "true";
      this.addListener(btn, "pointerdown", (e) => e.stopPropagation());
      this.addListener(btn, "click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation(); 
        BioMonitorWidget.showSettings(this);
      });
    });

    this.element.querySelectorAll('.bio-editable:not([data-listening])').forEach(el => {
      el.dataset.listening = "true";
      this.addListener(el, "pointerdown", (e) => e.stopPropagation());
      this.addListener(el, "click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation();
        const path = e.currentTarget.dataset.path;
        if (path) {
          BioMonitorWidget.editValue(this, path);
        }
      });
    });

    this.element.querySelectorAll('.photo-settings-btn:not([data-listening])').forEach(btn => {
      btn.dataset.listening = "true";
      this.addListener(btn, "pointerdown", (e) => e.stopPropagation());
      this.addListener(btn, "click", (e) => {
        e.preventDefault(); e.stopPropagation(); e.stopImmediatePropagation();
        PhotoFrameWidget.showSettings(this);
      });
    });

    this.element.querySelectorAll('.photo-frame-widget[data-action="next-photo"]:not([data-listening])').forEach(el => {
      el.dataset.listening = "true";
      this.addListener(el, "click", (e) => {
        if (e.target.closest('.photo-settings-btn')) return;
        e.preventDefault(); e.stopPropagation();
        PhotoFrameWidget.nextPhoto(this);
      });
    });
  },

  setupListeners() {
    this.removeAllListeners();

    const homeScreen = this.element.querySelector('.home-screen');
    const homePagesContainer = this.element.querySelector('.home-pages-container');

    this._setupAppIconListeners();
    this._setupWidgetListeners();
    this._setupPaginationListeners();
    this._setupSlideGestureListeners(homeScreen, homePagesContainer);
    this._setupHomeScreenListeners(homeScreen);
    this._attachWidgetListeners();
  },

  _setupAppIconListeners() {
    const icons = this.element.querySelectorAll(".app-icon");
    icons.forEach(icon => {
      const appId = icon.dataset.app;
      if (!appId) return;

      let pressTimer;
      let longPressTriggered = false;
      let startX = 0;
      let startY = 0;

      this.addListener(icon, 'dragstart', (e) => {
        if (longPressTriggered) { e.preventDefault(); return; }
        clearTimeout(pressTimer);
        this.handleDragStart(e, icon);
      });

      const defaultAppIds = this.getDefaultInstalledAppIds();
      if (!defaultAppIds.includes(appId)) {
        const handleContextMenu = (e) => {
          e.preventDefault(); e.stopPropagation(); clearTimeout(pressTimer);
          longPressTriggered = true;
          this._showAppContextMenu(e, appId);
        };

        this.addListener(icon, "pointerdown", (e) => {
          if (e.button !== 0) return;
          startX = e.clientX;
          startY = e.clientY;
          longPressTriggered = false;
          pressTimer = setTimeout(() => {
            if (navigator.vibrate) navigator.vibrate(50);
            longPressTriggered = true;
            const newEvent = new MouseEvent("contextmenu", { bubbles: true, cancelable: true, clientX: e.clientX, clientY: e.clientY });
            icon.dispatchEvent(newEvent);
          }, 500);
        });

        this.addListener(icon, "pointermove", (e) => {
          if (pressTimer && (Math.abs(e.clientX - startX) > 5 || Math.abs(e.clientY - startY) > 5)) {
            clearTimeout(pressTimer);
          }
        });

        this.addListener(icon, "contextmenu", handleContextMenu);
      }

      this.addListener(icon, "pointerup", async (e) => {
        clearTimeout(pressTimer);
        if (e.button === 0 && !longPressTriggered && !this.isAppIconDragging) {
          const iconWrapper = e.currentTarget.querySelector('.app-icon-wrapper') || e.currentTarget;
          iconWrapper.classList.add("app-launch");
          await new Promise((resolve) => setTimeout(resolve, 300));

          if (appId.startsWith('macro-')) {
            if (!game.modules.get("smartphone-macro-app")?.active) {
              this.widget.showToastNotification(game.i18n.localize("SMARTPHONE.notifications.macroAppNotInstalled"));
            } else {
              const macroId = appId.replace('macro-', '');
              const macro = game.macros.get(macroId);
              if (macro) macro.execute();
              else this.widget.showToastNotification(game.i18n.localize("SMARTPHONE.notifications.macroNotFound"));
            }
          } else {
            this.widget.switchApp(appId);
          }
          iconWrapper.classList.remove("app-launch");
        }
        longPressTriggered = false;
      });

      const cancelLongPress = () => clearTimeout(pressTimer);
      this.addListener(icon, "pointerleave", cancelLongPress);
      this.addListener(icon, "pointercancel", cancelLongPress);
    });
  },

  _setupWidgetListeners() {
    const widgets = this.element.querySelectorAll(".app-slot.widget-container");
    widgets.forEach(widgetEl => {
      const widgetId = widgetEl.dataset.widget;
      let pressTimer = null;
      let startX = 0;
      let startY = 0;
      let longPressTriggered = false;

      this.addListener(widgetEl, "click", (e) => {
        if (this.isAppIconDragging || longPressTriggered) {
          longPressTriggered = false;
          return; 
        }

        if (widgetId === 'widget-calendar') {
          this.widget.switchApp('calendar');
        }
        else if (widgetId === 'widget-bank-card') {
          this.widget.switchApp('banking', { startView: 'transferForm' });
        }
        else if (widgetId === 'widget-search-bar') {
          this.showGlobalSearch();
        }
        else if (widgetId === 'widget-actor-sheet' || widgetId === 'widget-actor-sheet-wide') {
          ActorSheetWidget.openSheet(this);
        }

        longPressTriggered = false;
      });

      this.addListener(widgetEl, "pointerdown", (e) => {
        if (e.button !== 0) return;
        startX = e.clientX;
        startY = e.clientY;
        longPressTriggered = false; 

        pressTimer = setTimeout(() => {
          longPressTriggered = true; 
          if (navigator.vibrate) navigator.vibrate(50);
          this._showWidgetContextMenu(e, widgetId);
        }, 600);
      });

      this.addListener(widgetEl, "pointermove", (e) => {
        if (pressTimer) {
          if (Math.abs(e.clientX - startX) > 5 || Math.abs(e.clientY - startY) > 5) {
            clearTimeout(pressTimer);
            pressTimer = null;
          }
        }
      });

      const cancelTimer = () => { if (pressTimer) clearTimeout(pressTimer); };
      this.addListener(widgetEl, "pointerup", cancelTimer);
      this.addListener(widgetEl, "pointerleave", cancelTimer);

      this.addListener(widgetEl, "dragstart", (e) => {
        if (longPressTriggered) { e.preventDefault(); return; }
        cancelTimer();
        e.stopPropagation();

        this.isAppIconDragging = true;
        this.draggedElement = widgetEl;
        this.draggedAppId = widgetId;

        const rect = widgetEl.getBoundingClientRect();
        const widgetDef = this.widgets[widgetId];
        const wSize = widgetDef ? widgetDef.size.w : 1;
        const hSize = widgetDef ? widgetDef.size.h : 1;

        const slotWidth = rect.width / wSize;
        const slotHeight = rect.height / hSize;

        this.dragOffset = {
          col: Math.floor((e.clientX - rect.left) / slotWidth),
          row: Math.floor((e.clientY - rect.top) / slotHeight)
        };

        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', widgetId);

        this.draggedOriginPage = parseInt(widgetEl.dataset.page);
        this.draggedOriginSlot = parseInt(widgetEl.dataset.slot);

        setTimeout(() => widgetEl.classList.add('dragging'), 0);
      });

      this.addListener(widgetEl, "dragend", (e) => {
        e.preventDefault(); e.stopPropagation();
        this.isAppIconDragging = false;
        widgetEl.classList.remove('dragging');
        this.dragOffset = null;
        this._removeWidgetGhost();
        this.element.querySelectorAll('.drag-over, .drag-invalid').forEach(el =>
          el.classList.remove('drag-over', 'drag-invalid')
        );
      });

      this.addListener(widgetEl, "contextmenu", (e) => {
        e.preventDefault(); e.stopPropagation();
        cancelTimer();
        this._showWidgetContextMenu(e, widgetId);
      });
    });
  },

  _setupPaginationListeners() {
    const dots = this.element.querySelectorAll(".home-pagination .dot");
    dots.forEach(dot => {
      this.addListener(dot, 'click', (e) => {
        const pageIndex = parseInt(e.currentTarget.dataset.page, 10);
        if (this.currentPage !== pageIndex) {
          this.currentPage = pageIndex;
          this.render();
        }
      });
    });
  },

  _setupSlideGestureListeners(homeScreen, homePagesContainer) {
    if (!homeScreen) return;

    let startX = 0;
    let isSliding = false;
    const slideThreshold = 50;

    const handlePointerDown = (e) => {
      if (e.target.closest('.app-icon[draggable="true"], .widget-container[draggable="true"]')) return;
      this.pointerDown = true;
      isSliding = false;
      startX = e.clientX;
    };

    const handlePointerMove = (e) => {
      if (!this.pointerDown || this.widget.isDragging) {
        if (this.widget.isDragging) this.cancelSlideGesture();
        return;
      }
      const diffX = e.clientX - startX;
      if (!isSliding && Math.abs(diffX) > 10) {
        isSliding = true;
        this.isSliding = true;
        homeScreen.setPointerCapture(e.pointerId);
        homeScreen.style.cursor = 'grabbing';
        if (homePagesContainer) homePagesContainer.style.transition = 'none';
      }
      if (isSliding) {
        e.preventDefault();
        const w = homeScreen.offsetWidth;
        const translate = -this.currentPage * w + diffX;
        if (homePagesContainer) homePagesContainer.style.transform = `translateX(${translate}px)`;
      }
    };

    const handlePointerUp = (e) => {
      if (!this.pointerDown) return;
      this.pointerDown = false;
      if (isSliding) {
        isSliding = false;
        this.isSliding = false;
        homeScreen.releasePointerCapture(e.pointerId);
        homeScreen.style.cursor = 'default';
        if (homePagesContainer) {
          homePagesContainer.style.transition = 'transform 0.3s ease-out';
          const diffX = e.clientX - startX;
          if (Math.abs(diffX) > slideThreshold) {
            if (diffX < 0 && this.currentPage < this.pages.length - 1) this.currentPage++;
            else if (diffX > 0 && this.currentPage > 0) this.currentPage--;
          }
          homePagesContainer.style.setProperty('--current-page', this.currentPage);
          homePagesContainer.style.transform = '';
          this.updatePaginationDots();
        }
      }
    };

    this.addListener(homeScreen, 'pointerdown', handlePointerDown);
    this.addListener(homeScreen, 'pointermove', handlePointerMove);
    this.addListener(homeScreen, 'pointerup', handlePointerUp);
    this.addListener(homeScreen, 'pointercancel', handlePointerUp);
  },

  _setupHomeScreenListeners(homeScreen) {
    if (!homeScreen) return;

    this.addListener(homeScreen, "contextmenu", (e) => {
      const slot = e.target.closest(".app-slot.empty");
      if (!slot || this.isAppIconDragging) return;
      e.preventDefault(); e.stopPropagation();
      this._showAddWidgetMenu(e, parseInt(slot.dataset.page), parseInt(slot.dataset.slot));
    });

    this.addListener(homeScreen, 'dragover', (e) => {
      if (this.isAppIconDragging) {
        e.preventDefault();
        e.stopPropagation();

        const rect = homeScreen.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const edgeThreshold = 50;

        if (!this.pageChangeTimeout) {
          if (x > rect.width - edgeThreshold && (this.currentPage < this.pages.length - 1 || this.isAppIconDragging)) {
            if (this.currentPage === this.pages.length - 1 && this.isAppIconDragging) {
              this.createNewPageWithDraggedApp();
            } else {
              this.switchPage(1);
            }
            return;
          }
          else if (x < edgeThreshold && this.currentPage > 0) {
            this.switchPage(-1);
            return;
          }
        }

        const pos = this._calculateGridPosition(e.clientX, e.clientY);

        if (!pos || pos.col < 0 || pos.col >= this.cols || pos.row < 0 || pos.row >= this.rows) {
          this._updateWidgetGhost(null, true);
          return;
        }

        if (this.draggedAppId && this.draggedAppId.startsWith('widget-')) {
          const offsetC = this.dragOffset ? this.dragOffset.col : 0;
          const offsetR = this.dragOffset ? this.dragOffset.row : 0;
          const startRow = pos.row - offsetR;
          const startCol = pos.col - offsetC;
          const startSlotIndex = startRow * this.cols + startCol;

          const targetSlots = this._getWidgetTargetSlots(startSlotIndex, pos.pageIndex, this.draggedAppId, true);

          let isBlocked = false;
          if (!targetSlots || targetSlots.length === 0) {
            isBlocked = true;
          } else {
            const originIndices = this._getSelfIndices(this.draggedOriginSlot, this.draggedAppId);
            isBlocked = targetSlots.some(s => {
              const sIdx = parseInt(s.dataset.slot);
              if (pos.pageIndex === this.draggedOriginPage && originIndices.includes(sIdx)) return false;

              const wId = s.dataset.widget;
              const isOccupied = s.classList.contains('occupied');
              return (s.classList.contains('widget-container') && wId !== this.draggedAppId) || isOccupied;
            });
          }
          this._updateWidgetGhost(targetSlots, isBlocked);
        }
        else {
          this._removeWidgetGhost();
          this.element.querySelectorAll('.drag-over').forEach(el => el.classList.remove('drag-over'));

          const slotIdx = pos.row * this.cols + pos.col;
          const slot = this.element.querySelector(`.app-slot[data-page="${pos.pageIndex}"][data-slot="${slotIdx}"]`);

          if (slot && !slot.classList.contains('widget-container') && !slot.classList.contains('occupied')) {
            slot.classList.add('drag-over');
          }
        }
      }
    });

    this.addListener(homeScreen, 'dragleave', (e) => {
      if (!homeScreen.contains(e.relatedTarget)) {
        this._removeWidgetGhost();
        this.element.querySelectorAll('.drag-over').forEach(el => el.classList.remove('drag-over'));
      }
    });

    this.addListener(homeScreen, 'drop', async (e) => {
      this._removeWidgetGhost();
      this.element.querySelectorAll('.drag-over').forEach(el => el.classList.remove('drag-over'));

      const pos = this._calculateGridPosition(e.clientX, e.clientY);
      if (!pos) return;

      const targetSlotIndex = pos.row * this.cols + pos.col;
      const realTargetSlot = this.element.querySelector(`.app-slot[data-page="${pos.pageIndex}"][data-slot="${targetSlotIndex}"]`);

      if (realTargetSlot) {
        this.handleDropOnSlot(e, realTargetSlot);
      }
    });
  }
});
