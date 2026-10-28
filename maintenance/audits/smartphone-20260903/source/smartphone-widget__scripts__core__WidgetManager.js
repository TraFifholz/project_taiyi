import { SmartphoneWidget } from "../smartphone-widget.js";
import { LockScreen } from "./lock/LockScreen.js";
import { SmartphoneTime } from "./SmartphoneTime.js";
import { TimeOfDayLighting } from "./TimeOfDayLighting.js";
import { BatteryManager } from "./BatteryManager.js";
import { ChargingZoneManager } from "./ChargingZoneManager.js";
import { GmTimeControllerDialog } from "./dialogs/GmTimeControllerDialog.js";
import { WidgetDragHandler } from "./widget/WidgetDragHandler.js";
import { WidgetResizeHandler, normalizeWidgetScale } from "./widget/WidgetResizeHandler.js";
import { WidgetControlCenter } from "./widget/WidgetControlCenter.js";
import { FirstTimeSetupWizard } from "./dialogs/FirstTimeSetupWizard.js";
import { PhoneSelectorDialog } from "./dialogs/PhoneSelectorDialog.js";
import { WidgetNavigation } from "./widget/WidgetNavigation.js";
import { WidgetClock } from "./widget/WidgetClock.js";
import { SignalManager } from "./SignalManager.js";
import { frameImageCssUrl } from "../utils/frame-image-url.js";
import {
  escapeMessageHtml,
  sanitizeMessageAssetUrl,
} from "../utils/messageHtml.js";

const safeAssetAttribute = (value) =>
  escapeMessageHtml(sanitizeMessageAssetUrl(value));

function renderSafeShareAvatar(item) {
  if (!item?.avatarHtml) {
    return `<img src="${safeAssetAttribute(item?.avatar)}" alt="${escapeMessageHtml(item?.name)}">`;
  }

  const source = document.createElement("template");
  source.innerHTML = String(item.avatarHtml);
  const avatars = [...source.content.querySelectorAll("img")]
    .slice(0, 4)
    .map((image) => sanitizeMessageAssetUrl(image.getAttribute("src")));
  if (avatars.length === 0) {
    return `<img src="${safeAssetAttribute(item?.avatar)}" alt="${escapeMessageHtml(item?.name)}">`;
  }

  const overflowText = source.content.querySelector(".member-count")?.textContent || "";
  const overflowCount = Number.parseInt(overflowText.replace(/\D/g, ""), 10);
  return `
    <div class="group-avatar-stack member-count-${avatars.length}">
      ${avatars.map((avatar) => `
        <img src="${safeAssetAttribute(avatar)}" class="member-avatar" alt="${escapeMessageHtml(item?.name)}">
      `).join("")}
      ${Number.isFinite(overflowCount) && overflowCount > 0
        ? `<span class="member-count">+${overflowCount}</span>`
        : ""}
    </div>
  `;
}

const { ApplicationV2, HandlebarsApplicationMixin } = foundry.applications.api;

export class WidgetManager extends HandlebarsApplicationMixin(ApplicationV2) {
  constructor(options = {}) {
    super(options);

    this.ID = SmartphoneWidget.ID;
    this.apps = new Map();
    this.currentApp = null;
    this.isDragging = false;
    this.dragOffset = { x: 0, y: 0 };
    this.currentTheme = "light";
    this.currentPhoneId = null;
    this.currentActorId = null;
    this.listeners = new Map();
    this.notifications = new Map();
    this.currentLayerMode = 'normal';
    this._lockScreen = new LockScreen(this);

    this.updateClockDisplay = this.updateClockDisplay.bind(this);
    this._handleWindowClick = this._handleWindowClick.bind(this);
    this._boundUpdateFlashlightStatus = this._updateFlashlightStatus.bind(this);
  }

  /**
   * ApplicationV2 설정
   */
  static DEFAULT_OPTIONS = {
    tag: "div",
    id: "smartphone-widget-app", // 고유 ID
    classes: ["phone-widget-container"], // 기존 CSS 클래스 유지
    window: {
      frame: false,      // 창 틀(헤더, 배경) 제거 -> 투명 위젯 구현의 핵심
      positioned: true,  // 위치 관리 활성화 (Foundry가 top/left 관리)
      resizable: false,
      controls: []
    },
    position: {
      width: 320,  // CSS scale에 따라 시각적 크기는 달라질 수 있음
      height: 650,
      top: 20,
      left: 20
    }
  };

  /**
   * HTML 템플릿 지정
   */
  static PARTS = {
    content: { 
      template: "modules/smartphone-widget/templates/smartphone-shell.hbs",
      scrollable: [] 
    }
  };

  static initialize(socketlib) {
    console.log("[WidgetManager] Initializing with socketlib:", socketlib);
    if (!socketlib) {
      console.error("[WidgetManager] No socketlib provided");
      return false;
    }
    this.socket = socketlib;
    return true;
  }

  /**
   * 렌더링 데이터 준비 (현재는 특별히 넘길 데이터 없음)
   */
  async _prepareContext(options) {
    return { isGM: game.user?.isGM ?? false };
  }

  /**
   * 렌더링 완료 후 호출 (기존 createWidget 로직 이식)
   */
  _onRender(context, options) {
    super._onRender(context, options);

    const container = this.element; // 실제 DOM 요소

    // 1. 소유자 표시 동적 추가 (템플릿 외부에 띄우는 느낌을 위해 prepend)
    if (!container.querySelector('.phone-owner-indicator')) {
        const ownerInd = document.createElement('div');
        ownerInd.className = 'phone-owner-indicator';
        ownerInd.innerHTML = `<i class="fas fa-mobile-alt"></i><span class="owner-name">${game.i18n.localize("SMARTPHONE.ui.myPhone")}</span>`;
        container.prepend(ownerInd);
    }

    // 2. 설정 버튼 리스너
    const settingsBtn = container.querySelector(".phone-settings-btn");
    if(settingsBtn) settingsBtn.addEventListener("click", () => this.showSettings());

    // 2-1. 팝아웃 버튼
    const popoutBtn = container.querySelector(".popout-btn");
    if (popoutBtn) {
      if (typeof this.detachWindow !== "function") {
        popoutBtn.style.display = "none";
      } else {
        popoutBtn.addEventListener("click", (e) => {
          e.stopPropagation();
          const isDetached = this.element?.ownerDocument !== globalThis.document;
          if (isDetached) {
            this.attachWindow();
            popoutBtn.querySelector("i").className = "fas fa-up-right-from-square";
          } else {
            this.detachWindow();
            popoutBtn.querySelector("i").className = "fas fa-down-left-and-up-right-to-center";
          }
        });
      }
    }

    // 3. 배터리 아이콘 (배터리 시스템 활성 시 상태 표시, 비활성 시 기존 닫기 버튼)
    const batteryIcon = container.querySelector(".battery-icon-clickable");
    if (batteryIcon) {
      batteryIcon.style.cursor = "pointer";

      if (BatteryManager.isEnabled) {
        batteryIcon.title = game.i18n.localize("SMARTPHONE.battery.statusTitle");
        this.addListener(batteryIcon, "click", (e) => {
          e.stopPropagation();
          if (game.user.isGM && this.currentPhoneId && this.currentPhoneId !== 'gm-master-phone') {
            this._showBatteryControlPanel();
          } else if (this.currentPhoneId && ChargingZoneManager.isInChargingZone(this.currentPhoneId)
            && !BatteryManager.isCharging(this.currentPhoneId)) {
            ChargingZoneManager.startChargingFromZone(this.currentPhoneId);
          } else {
            const level = BatteryManager.getBatteryLevel(this.currentPhoneId);
            this.showToastNotification(
              game.i18n.format("SMARTPHONE.battery.statusToast", { level })
            );
          }
        });
        this._initBatteryDisplay();
      } else {
        batteryIcon.title = "Close Widget";
        this.addListener(batteryIcon, "click", (e) => {
          e.stopPropagation();
          game.settings.set(SmartphoneWidget.ID, "showWidget", false);
        });
        this.addListener(batteryIcon, "mouseenter", () => {
          batteryIcon.style.color = "#ff3b30";
        });
        this.addListener(batteryIcon, "mouseleave", () => {
          batteryIcon.style.color = "var(--sw-icon-color)";
        });
      }
    }

    // 4. 시계 영역 리스너 (GM용 시간 조작)
    const timeElement = container.querySelector(".status-bar .time");
    if (game.user.isGM && timeElement) {
      timeElement.style.cursor = "pointer";
      this.addListener(timeElement, "click", () => this._showGmTimeController());
    }

    // 5. 초기 상태 업데이트
    this.updateOwnerName();
    this.startClock();
    
    // CSS 변수 설정 (크기 조절)
    const scale = game.settings.get(this.ID, "widgetScale") || 1.0;
    this.applyWidgetScale(scale);

    // 6. 핸들러 등록
    this.setupDragHandlers(container);
    this.setupResizeHandlers(container);
    this.setupNavigationHandlers(container);
    this.setupControlCenter(container);
    this.setupKeypad(container); // 키패드 리스너 분리 호출
    this.renderNotifications();
    this.setupGlobalClick();
    this.setupDropHandlers(container); // 드래그 앤 드롭 핸들러

    // 7. 프레임 및 홈 버튼 설정
    const frame = container.querySelector(".smartphone-frame");
    const showHomeBtn = game.settings.get(this.ID, "showPersistentHomeButton");
    if (frame) frame.classList.toggle("show-persistent-home", showHomeBtn);

    // 8. 레이어 모드 복구
    this.updateLayerMode(game.settings.get(this.ID, "widgetLayerMode"));

    SignalManager._updateStatusBarIcon();

    // 9. 앱 화면 복구 (재렌더링 시 내용 유지)
    if (this.currentPhoneId) {
        this.applyWallpaper();
        this.applyFrame();
    }
    if (this.currentApp && this.apps.has(this.currentApp)) {
        const app = this.apps.get(this.currentApp);
        app.render(); 
        this.updateNavigationBar();
    }
  }

  _onDetach(from, to) {
    this._resizeHandler?.cancel();
    if (this._dragHandler) {
      this._dragHandler.isDragging = false;
    }
    this.element.style.cursor = "";
    this.setPosition({ left: 10, top: 10 });

    this._rebindAfterDocumentChange();
  }

  _onAttach(from, to) {
    this._resizeHandler?.cancel();
    if (this._dragHandler) {
      this._dragHandler.isDragging = false;
    }

    const saved = game.settings.get(SmartphoneWidget.ID, "widgetPosition");
    if (saved) {
      this.setPosition({
        left: parseInt(saved.left) || 20,
        top: parseInt(saved.top) || 20
      });
    }

    this._rebindAfterDocumentChange();
  }

  _rebindAfterDocumentChange() {
    const container = this.element;
    if (!container) return;

    this._clearDocumentListeners();
    this._windowClickListenerAdded = false;

    this.setupControlCenter(container);
    this.setupNavigationHandlers(container);
    this.setupGlobalClick();

    if (this._dragHandler) {
      const widget = container.querySelector(".smartphone-frame") ?? container;
      this._dragHandler.setup(widget);
    }
    this.setupResizeHandlers(container);

    this.applyWallpaper();
    this.applyFrame();
  }

  _clearDocumentListeners() {
    const toRemove = [];
    for (const [element, eventMap] of this.listeners) {
      if (element instanceof Document) {
        for (const [eventType, handlers] of eventMap) {
          for (const handler of handlers) {
            element.removeEventListener(eventType, handler);
          }
        }
        toRemove.push(element);
      }
    }
    for (const el of toRemove) this.listeners.delete(el);
  }

  /* ----------------------------------------------------------------------- */
  /*                            Event Handlers                               */
  /* ----------------------------------------------------------------------- */

  setupDragHandlers(widget) {
    if (!this._dragHandler) {
      this._dragHandler = new WidgetDragHandler(this);
    }
    this._dragHandler.setup(widget);
  }

  setupResizeHandlers(container) {
    if (!this._resizeHandler) {
      this._resizeHandler = new WidgetResizeHandler(this);
    }
    this._resizeHandler.setup(container);
  }

  applyWidgetScale(value) {
    const scale = normalizeWidgetScale(value);
    const container = this.element;
    if (!container) return scale;

    container.style.setProperty("--smartphone-scale-factor", scale);

    const scaleSlider = container.querySelector("#widget-scale-slider");
    if (scaleSlider) scaleSlider.value = String(scale);

    const scaleLabel = container.querySelector("#widget-scale-label");
    if (scaleLabel) scaleLabel.textContent = `${Math.round(scale * 100)}%`;

    const resizeHandle = container.querySelector(".widget-resize-handle");
    if (resizeHandle) {
      const percent = Math.round(scale * 100);
      resizeHandle.setAttribute("aria-valuenow", String(percent));
      resizeHandle.setAttribute("aria-valuetext", `${percent}%`);
    }

    return scale;
  }

  setupDropHandlers(container) {
    if (!this._dragHandler) {
      this._dragHandler = new WidgetDragHandler(this);
    }
    this._dragHandler.setupDropHandlers(container);
  }

  setupControlCenter(container) {
    if (!this._controlCenter) {
      this._controlCenter = new WidgetControlCenter(this);
    }
    this._controlCenter.setup(container);
  }

  setupKeypad(container) {
    if (!this._navigation) {
      this._navigation = new WidgetNavigation(this);
    }
    this._navigation.setupKeypad(container);
  }

  setupNavigationHandlers(container) {
    if (!this._navigation) {
      this._navigation = new WidgetNavigation(this);
    }
    this._navigation.setupNavigationHandlers(container);
  }

  setupGlobalClick() {
      const doc = this.element?.ownerDocument ?? document;
      if (this._windowClickListenerDoc && this._windowClickListenerDoc !== doc) {
          this._windowClickListenerDoc.removeEventListener("mousedown", this._handleWindowClick, { capture: true });
          this._windowClickListenerAdded = false;
      }
      if (!this._windowClickListenerAdded) {
          doc.addEventListener("mousedown", this._handleWindowClick, { capture: true });
          this._windowClickListenerAdded = true;
          this._windowClickListenerDoc = doc;
      }
      this.element.addEventListener("mousedown", () => this.bringToFront());
  }

  /* ----------------------------------------------------------------------- */
  /*                            Core Logic                                   */
  /* ----------------------------------------------------------------------- */

  registerApp(name, app) {
    this.apps.set(name, app);
  }

  switchApp(appName, ...args) {
    const previousAppName = this.currentApp;
    const previousApp = previousAppName ? this.apps.get(previousAppName) : null;

    if (previousApp) {
      previousApp.hide();
    }

    const app = this.apps.get(appName);
    if (!app) {
      if (previousAppName && previousApp) {
        this.currentApp = previousAppName;
        previousApp.show();
        this.updateNavigationBar();
      }
      return;
    }

    this.currentApp = appName;

    try {
      app.show(...args);
      this.updateNavigationBar();
    } catch (err) {
      console.error(`Smartphone Widget | Failed to open app '${appName}'.`, err);

      if (previousAppName && previousApp) {
        try {
          this.currentApp = previousAppName;
          previousApp.show();
          this.updateNavigationBar();
          return;
        } catch (restoreErr) {
          console.error(`Smartphone Widget | Failed to restore previous app '${previousAppName}'.`, restoreErr);
        }
      }

      const homeApp = this.apps.get("home");
      if (homeApp) {
        try {
          this.currentApp = "home";
          homeApp.show();
          this.updateNavigationBar();
        } catch (homeErr) {
          console.error("Smartphone Widget | Failed to recover to home app.", homeErr);
        }
      }
    }
  }

  updateNavigationBar() {
    if (!this.element) return;
    const backBtn = this.element.querySelector(".navigation-bar > .back-btn");
    if(backBtn) backBtn.style.display = "block";
  }

  async show(options = {}) {
    let isInitialOpen = false;
    // 1. ApplicationV2 렌더링 (닫혀있다면 켬)
    if (!this.rendered) {
        isInitialOpen = true;
        const savedPos = game.settings.get(this.ID, "widgetPosition");
        const left = parseInt(savedPos.left) || 20;
        const top = parseInt(savedPos.top) || 20;
        
        await this.render({ force: true, position: { left, top } });
    } else {
        this.bringToFront();
    }

    if (isInitialOpen && this.element && this.currentPhoneId) {
        this._playBootAnimation();
    }

    // 2. 초기화 로직 (렌더링 후 DOM이 존재함)
    Hooks.on("controlToken", this._boundUpdateFlashlightStatus);
    this._updateFlashlightStatus();

    const messagesApp = this.apps.get("messages");
    if (messagesApp) await messagesApp.loadInitialUnreadCounts();

    if (options.firstTime) {
        this._renderFirstTimeSetup_Step1();
        return true;
    }

    if (!this.currentPhoneId) {
        await this.showSettings();
        return true;
    }

    // 소셜 로그인 상태 복구
    const socialApp = this.apps.get("social");
    if (socialApp) {
        const allLoginStates = (await game.settings.get("smartphone-widget", "social-login-states")) || {};
        const phoneLoginState = allLoginStates[this.currentPhoneId] || { isLoggedIn: false };
        socialApp.isLoggedIn = phoneLoginState.isLoggedIn;
        socialApp.currentSocialId = phoneLoginState.currentSocialId;
        socialApp.currentAccount = phoneLoginState.currentAccount;
    }

    await this.updateOwnerName();
    await this.applyWallpaper();
    await this.applyFrame();
    await this.applyCrackedEffect();

    if (isInitialOpen) {
        await this._lockScreen.gate(this.currentPhoneId);
    }

    const appToShow = this.currentApp || "home";
    this.switchApp(appToShow);

    this._setupGestureHints();

    return true;
  }

  _setupGestureHints() {
    if (!this.element || !this.currentPhoneId) return;
    const container = this.element.querySelector(".gesture-hints");
    if (!container) return;

    const stored = game.settings.get(this.ID, "gestureHintsCompleted") ?? {};
    this._gestureHintState = { top: stored.top === true, bottom: stored.bottom === true };
    const { top: topDone, bottom: bottomDone } = this._gestureHintState;

    const topHint = container.querySelector(".gesture-hint-top");
    const bottomHint = container.querySelector(".gesture-hint-bottom");

    if (topDone && bottomDone) {
      container.classList.remove("active");
      topHint?.classList.remove("visible");
      bottomHint?.classList.remove("visible");
      return;
    }

    container.classList.add("active");
    if (topHint) topHint.classList.toggle("visible", !topDone);
    if (bottomHint) bottomHint.classList.toggle("visible", !bottomDone);
  }

  _dismissGestureHint(which) {
    if (!this.element) return;

    const hint = this.element.querySelector(`.gesture-hint-${which}`);
    hint?.classList.remove("visible");

    if (!this._gestureHintState) {
      const stored = game.settings.get(this.ID, "gestureHintsCompleted") ?? {};
      this._gestureHintState = { top: stored.top === true, bottom: stored.bottom === true };
    }
    if (this._gestureHintState[which] === true) return;

    this._gestureHintState[which] = true;
    game.settings.set(this.ID, "gestureHintsCompleted", { ...this._gestureHintState });

    if (this._gestureHintState.top && this._gestureHintState.bottom) {
      this.element.querySelector(".gesture-hints")?.classList.remove("active");
    }
  }

async hide() {
    if (this.currentPhoneId) this._lockScreen.lock(this.currentPhoneId);

    if (this.element) {
        const screen = this.element.querySelector(".smartphone-screen");
        if (screen && !screen.classList.contains("shutting-down")) {
            screen.classList.add("shutting-down");
            await new Promise(resolve => setTimeout(resolve, 500));
        }
    }

    await this.close({ animate: false });

    const messagesApp = this.apps.get("messages");
    if (messagesApp) messagesApp.updateTotalBadge();

    if (this.currentApp && this.apps.has(this.currentApp)) {
        this.apps.get(this.currentApp).hide();
    }

    if (this._clock) {
        this._clock.stop();
    }
    
    Hooks.off("controlToken", this._boundUpdateFlashlightStatus);
    
    this.currentApp = null;
  }

    async shutdownAndClose() {
        if (this.element) {
            const screen = this.element.querySelector(".smartphone-screen");
            if (screen && !screen.classList.contains("shutting-down")) {
                screen.classList.add("shutting-down");
                await new Promise(resolve => setTimeout(resolve, 500));
            }
        }
        await game.settings.set(this.ID, "showWidget", false);
    }

    // --- 기존의 Helper 메서드들 (DOM 접근 시 this.element 사용) ---

  async updateOwnerName() {
    if (!this.element) return;
    const ownerNameEl = this.element.querySelector(".owner-name");
    if (!ownerNameEl) return;

    if (this.currentPhoneId === 'gm-master-phone') {
        ownerNameEl.textContent = game.i18n.localize("SMARTPHONE.ui.masterPhone");
        return;
    }

    let newName = game.i18n.localize("SMARTPHONE.ui.myPhone");
    if (this.currentPhoneId) {
        const devices = (await game.settings.get(this.ID, "smartphone-devices")) || {};
        const phone = devices[this.currentPhoneId];
        if (phone) {
            if (phone.name) {
                newName = phone.name;
            } else {
                const owner = phone.ownerId ? game.actors.get(phone.ownerId) || game.users.get(phone.ownerId) : null;
                newName = owner ? game.i18n.format("SMARTPHONE.ui.phoneOf", { name: owner.name }) : game.i18n.localize("SMARTPHONE.ui.ownerlessPhone");
            }
        } else {
            newName = game.i18n.localize("SMARTPHONE.ui.ownerlessPhone");
        }
    }
    ownerNameEl.textContent = newName;
  }

  async startClock() {
    if (!this._clock) {
      this._clock = new WidgetClock(this);
    }
    await this._clock.start();
  }

  updateClockDisplay() {
    if (this._clock) {
      this._clock.updateClockDisplay();
    }
  }

  handleTimeUpdate() {
    if (this._clock) {
      this._clock.handleTimeUpdate();
    }
  }

  async showSettings() {
    if (!this._phoneSelectorDialog) {
      this._phoneSelectorDialog = new PhoneSelectorDialog(this);
    }
    await this._phoneSelectorDialog.show();
  }

  async switchPhone(phoneId) {
      if (this.currentPhoneId === phoneId) {
          await this._renderDisplay();
          return;
      }
      this.currentPhoneId = phoneId;
      if (phoneId) {
          const devices = (await game.settings.get(SmartphoneWidget.ID, "smartphone-devices")) || {};
          const phone = devices[phoneId];
          this.currentActorId = phone ? phone.ownerId : null;
      } else {
          this.currentActorId = null;
      }

      SignalManager._updateSignalState();

      const messagesApp = this.apps.get("messages");
      if (messagesApp) await messagesApp.loadInitialUnreadCounts();

      for (const app of this.apps.values()) {
          if (typeof app.onActorChanged === "function") await app.onActorChanged(this.currentActorId);
          if (typeof app.onPhoneChanged === "function") await app.onPhoneChanged();
      }

      this.currentApp = "home";
      await this._renderDisplay();
  }

  async _renderDisplay() {
      if(!this.element) return;
      const settingsScreen = this.element.querySelector(".settings-screen");
      if (settingsScreen) settingsScreen.remove();

      this._updateFlashlightStatus();
      await this.updateOwnerName();
      await this.applyFrame();
      await this.applyWallpaper();
      await this.applyCrackedEffect();
      this._initBatteryDisplay();

      const appToShow = this.currentApp || "home";
      this.switchApp(appToShow);
  }

  // --- Display Helpers ---

  async applyWallpaper() {
      if (!this.element || !this.currentPhoneId) return;
      const backgroundContainer = this.element.querySelector(".widget-background");
      const frame = this.element.querySelector(".smartphone-frame");
      const allWallpapers = (await game.settings.get(this.ID, "smartphone-wallpapers")) || {};
      const wallpaperData = allWallpapers[this.currentPhoneId];
      const wallpaperFit = wallpaperData?.fit || "cover";
      let finalPath = wallpaperData?.path || "modules/smartphone-widget/assets/default_wallpaper.png";

      backgroundContainer.innerHTML = "";
      backgroundContainer.style.backgroundImage = "";
      backgroundContainer.classList.remove("background-cover", "background-contain");
      frame.classList.remove("has-wallpaper");

      const isVideo = ["mp4", "webm", "mov"].some((ext) => finalPath.toLowerCase().endsWith(ext));

      if (isVideo) {
          const videoElement = document.createElement("video");
          videoElement.classList.add("wallpaper-video", wallpaperFit === "cover" ? "fit-cover" : "fit-contain");
          videoElement.autoplay = true;
          videoElement.loop = true;
          videoElement.muted = true;
          videoElement.playsInline = true;
          videoElement.src = finalPath;
          videoElement.addEventListener("canplay", () => frame.classList.add("has-wallpaper"));
          backgroundContainer.appendChild(videoElement);
      } else {
          backgroundContainer.classList.add(wallpaperFit === "cover" ? "background-cover" : "background-contain");
          backgroundContainer.style.backgroundImage = `url(${finalPath})`;
          frame.classList.add("has-wallpaper");
      }
  }

  async applyFrame() {
      if (!this.element || !this.currentPhoneId) return;
      const frameElement = this.element.querySelector(".smartphone-frame");
      const allFrames = (await game.settings.get(this.ID, "smartphone-frames")) || {};
      let frameStyle = allFrames[this.currentPhoneId];
      const frameClasses = Array.from(frameElement.classList).filter((c) => c.startsWith("frame-"));
      frameElement.classList.remove(...frameClasses);

      frameElement.style.removeProperty("--sw-time-color");
      frameElement.style.removeProperty("--sw-icon-color");
      frameElement.style.removeProperty("--sw-statusbar-bg");

      frameElement.style.removeProperty("--sw-custom-frame-image");
      frameElement.style.removeProperty("--sw-custom-frame-padding");
      frameElement.style.removeProperty("--sw-custom-frame-radius");
      frameElement.style.removeProperty("--sw-custom-screen-radius");
      frameElement.style.removeProperty("--sw-custom-frame-offset-x");
      frameElement.style.removeProperty("--sw-custom-frame-offset-y");

      if (frameStyle === "frame-custom") {
          await this._migrateOldCustomTheme();
          const updatedFrames = (await game.settings.get(this.ID, "smartphone-frames")) || {};
          frameStyle = updatedFrames[this.currentPhoneId] || "default";
      }

      if (frameStyle) frameElement.classList.add(frameStyle.startsWith("frame-custom-") ? "frame-custom" : frameStyle);

      if (frameStyle && frameStyle.startsWith("frame-custom-")) {
          const themeId = frameStyle.replace("frame-custom-", "");
          const customThemes = game.settings.get(this.ID, "smartphone-custom-themes") || {};
          const themeData = customThemes[themeId];
          if (themeData) {
              if (themeData.timeColor) frameElement.style.setProperty("--sw-time-color", themeData.timeColor);
              if (themeData.iconColor) frameElement.style.setProperty("--sw-icon-color", themeData.iconColor);
              if (themeData.statusBarBg) frameElement.style.setProperty("--sw-statusbar-bg", themeData.statusBarBg);

              const imageUrl = frameImageCssUrl(themeData.frameImage);
              if (imageUrl) frameElement.style.setProperty("--sw-custom-frame-image", imageUrl);
              const padding = themeData.framePadding ?? 0;
              if (padding > 0) {
                  frameElement.style.setProperty("--sw-custom-frame-padding", `${padding}px`);
              }
              const radius = themeData.frameRadius ?? 25;
              frameElement.style.setProperty("--sw-custom-frame-radius", `${radius}px`);
              frameElement.style.setProperty("--sw-custom-screen-radius", `${Math.max(0, radius - 2)}px`);
              const offsetX = themeData.frameOffsetX ?? 0;
              const offsetY = themeData.frameOffsetY ?? 0;
              frameElement.style.setProperty("--sw-custom-frame-offset-x", `${offsetX}px`);
              frameElement.style.setProperty("--sw-custom-frame-offset-y", `${offsetY}px`);
          }
      }
  }

  async _migrateOldCustomTheme() {
      const customThemes = foundry.utils.deepClone(game.settings.get(this.ID, "smartphone-custom-themes") || {});
      const oldData = customThemes[this.currentPhoneId];
      if (!oldData || oldData.name) return;

      const newThemeId = `custom-${foundry.utils.randomID(8)}`;
      const migratedTheme = {
          name: "Custom (Migrated)",
          frameImage: oldData.frameImage || "",
          timeColor: oldData.timeColor || "#ffffff",
          iconColor: oldData.iconColor || "#00e0ff",
          statusBarBg: oldData.statusBarBg || "transparent",
          framePadding: oldData.framePadding ?? 0,
          frameRadius: oldData.frameRadius ?? 25,
          frameOffsetX: oldData.frameOffsetX ?? 0,
          frameOffsetY: oldData.frameOffsetY ?? 0,
      };

      delete customThemes[this.currentPhoneId];
      customThemes[newThemeId] = migratedTheme;
      await game.settings.set(this.ID, "smartphone-custom-themes", customThemes);

      const allFrames = foundry.utils.deepClone((await game.settings.get(this.ID, "smartphone-frames")) || {});
      allFrames[this.currentPhoneId] = `frame-custom-${newThemeId}`;
      await game.settings.set(this.ID, "smartphone-frames", allFrames);
  }

  updateLayerMode(mode) {
      if (!this.element) return;
      this.currentLayerMode = mode;
      this.element.classList.remove("layer-top", "layer-normal");
      this.element.style.zIndex = "";
      if (mode === "normal") {
          this.element.classList.add("layer-normal");
          this.bringToFront();
      } else {
          this.element.classList.add("layer-top");
      }
  }

  bringToFront() {
      if (this.currentLayerMode !== 'normal' || !this.element) return;
      const otherWindows = document.querySelectorAll('.app.window, .application');
      let maxZ = 100;
      otherWindows.forEach(el => {
          if (el === this.element) return;
          const z = parseInt(window.getComputedStyle(el).zIndex);
          if (!isNaN(z) && z > maxZ) maxZ = z;
      });
      this.element.style.zIndex = maxZ + 1;
  }

  _handleWindowClick(event) {
      if (this.currentLayerMode !== 'normal' || !this.element) return;
      if (this.element.contains(event.target)) return;
      const clickedApp = event.target.closest('.app.window, .application');
      if (clickedApp) {
          setTimeout(() => {
              if (!this.element) return;
              const appZ = parseInt(window.getComputedStyle(clickedApp).zIndex);
              const phoneZ = parseInt(window.getComputedStyle(this.element).zIndex);
              if (!isNaN(appZ) && !isNaN(phoneZ) && phoneZ >= appZ) {
                  this.element.style.zIndex = Math.max(1, appZ - 1);
              }
          }, 10);
      }
  }

  // --- Utils ---

  handleBackNavigation() {
      if (this.currentApp) {
          this.apps.get(this.currentApp).handleBack();
      }
  }

  navigateToHome() {
      if (this.currentApp !== "home") {
          this.switchApp("home");
      }
  }

  toggleMenu() { /* 메뉴 토글 구현 예정 */ }

  showBadge(appId, count) {
      const homeApp = this.apps.get("home");
      if (homeApp) {
          homeApp.showBadge(appId, count);
      }
  }

  showToastNotification(htmlContent, options = {}) {
      if (!this.element) return;
      const existingToast = this.element.querySelector(".smartphone-toast");
      if (existingToast) existingToast.remove();

      const toast = document.createElement("div");
      toast.className = "smartphone-toast";
      toast.innerHTML = htmlContent;

      const screen = this.element.querySelector(".smartphone-screen");
      if (screen) {
          screen.appendChild(toast);
          const hideTimer = setTimeout(() => {
              if (toast.parentElement) {
                  toast.classList.add("fade-out");
                  toast.addEventListener("animationend", () => toast.remove());
              }
          }, 3000);

          toast.addEventListener("click", () => {
              clearTimeout(hideTimer);
              if (options.onClick && typeof options.onClick === "function") options.onClick();
              if (toast.parentElement) toast.remove();
          });
      }
  }

  async toggleFlashlight(buttonElement) {
      const controlledTokens = canvas.tokens.controlled;
      if (controlledTokens.length === 0) {
          this.showToastNotification(game.i18n.localize("SMARTPHONE.notifications.selectTokenForFlashlight"));
          return;
      }
      const token = controlledTokens[0];
      const isFlashlightOn = token.document.getFlag("smartphone-widget", "flashlightOn");

      if (isFlashlightOn) {
          await token.document.unsetFlag("smartphone-widget", "flashlightOn");
          await token.document.update({ "light.bright": 0, "light.dim": 0, "light.angle": 360 });
          buttonElement.classList.remove("active");
      } else {
          await token.document.setFlag("smartphone-widget", "flashlightOn", true);
          await token.document.update({
              light: { bright: 20, dim: 40, angle: 60, color: "#000000", alpha: 0.7, luminosity: 0.7, rotation: token.document.rotation }
          });
          buttonElement.classList.add("active");
      }
  }

  _updateFlashlightStatus() {
      if (!this.element) return;
      const flashlightButton = this.element.querySelector('.control-item[data-action="toggle-flashlight"]');
      if (!flashlightButton) return;
      const controlled = canvas.tokens.controlled;
      if (controlled.length === 1) {
          const isFlashlightOn = controlled[0].document.getFlag("smartphone-widget", "flashlightOn");
          flashlightButton.classList.toggle("active", !!isFlashlightOn);
      } else {
          flashlightButton.classList.remove("active");
      }
  }

  updateContent(htmlContent) {
      if (!this.element) return;
      const widgetContent = this.element.querySelector(".widget-content");
      if (widgetContent) widgetContent.innerHTML = htmlContent;
  }

  resetPosition() {
      if (!this.element) return;
      const initialPosition = { left: "20px", top: "20px" };
      game.settings.set(SmartphoneWidget.ID, "widgetPosition", initialPosition);
      this.setPosition(initialPosition);
  }

  showNoDeviceScreen() {
      if (!this.element) return; 
      // 이 메서드는 보통 최초 로드 시 호출됨. 
      // 이미 show()를 통해 렌더링된 상태에서 내용을 교체하는 방식
      
      const content = `
          <div class="no-device-screen">
              <i class="fas fa-mobile-slash"></i>
              <h3>${game.i18n.localize("SMARTPHONE.ui.noDeviceAssigned")}</h3>
              <p>${game.i18n.localize("SMARTPHONE.ui.noDeviceHint")}</p>
          </div>
          <style>
              .no-device-screen {
                  display: flex; flex-direction: column; align-items: center; justify-content: center;
                  height: 100%; text-align: center; padding: 20px; color: #868e96; background: #f8f9fa;
              }
              .no-device-screen i { font-size: 4em; margin-bottom: 20px; opacity: 0.5; }
              .no-device-screen h3 { font-size: 1.2em; color: #495057; margin: 0 0 10px 0; }
              .no-device-screen p { font-size: 0.9em; line-height: 1.5; }
          </style>
      `;
      this.updateContent(content);

      const statusBar = this.element.querySelector('.status-bar');
      const navBar = this.element.querySelector('.navigation-bar');
      const ownerIndicator = this.element.querySelector('.phone-owner-indicator');
      if (statusBar) statusBar.querySelector('.status-icons').style.display = 'none';
      if (navBar) navBar.style.display = 'none';
      if (ownerIndicator) ownerIndicator.style.display = 'none';
  }

  // --- 알림, 리스너 유틸 ---
  addNotification(notification) {
      this.notifications.set(notification.id, notification);
      this.renderNotifications();
  }
  removeNotification(notificationId) {
      if (this.notifications.has(notificationId)) {
          this.notifications.delete(notificationId);
          this.renderNotifications();
      }
  }
  renderNotifications() {
      if (!this.element) return;
      const list = this.element.querySelector(".notification-list");
      const noNotifications = this.element.querySelector(".no-notifications");
      if (!list || !noNotifications) return;

      list.innerHTML = "";
      if (this.notifications.size === 0) {
          noNotifications.style.display = "flex";
      } else {
          noNotifications.style.display = "none";
          this.notifications.forEach((notif) => {
              const item = document.createElement("div");
              item.className = "notification-item";
              let iconElement;
              if (notif.iconClass) {
                  iconElement = document.createElement("i");
                  const safeClasses = String(notif.iconClass)
                      .split(/\s+/)
                      .filter((className) => /^[a-z0-9_-]+$/i.test(className));
                  iconElement.classList.add(...safeClasses);
                  iconElement.classList.add("notification-icon", "notification-symbol-icon");
              } else if (notif.icon) {
                  iconElement = document.createElement("img");
                  const rawIcon = String(notif.icon).trim();
                  const isSafeAbsoluteUrl = /^(?:https?:|blob:)/i.test(rawIcon);
                  const isSafeRasterDataUrl = /^data:image\/(?:png|jpe?g|gif|webp|avif);base64,/i.test(rawIcon);
                  const isRelativeAssetPath = rawIcon && !/^[a-z][a-z0-9+.-]*:/i.test(rawIcon);
                  iconElement.src =
                      isSafeAbsoluteUrl || isSafeRasterDataUrl || isRelativeAssetPath
                          ? rawIcon
                          : "icons/svg/mystery-man.svg";
                  iconElement.alt = "";
                  iconElement.className = "notification-icon";
              } else {
                  iconElement = document.createElement("i");
                  iconElement.className = "fas fa-bell notification-icon notification-symbol-icon";
              }

              const content = document.createElement("div");
              content.className = "notification-content";
              const title = document.createElement("div");
              title.className = "notification-title";
              title.textContent = String(notif.title ?? "");
              const body = document.createElement("div");
              body.className = "notification-body";
              body.textContent = String(notif.body ?? "");
              content.append(title, body);
              item.append(iconElement, content);
              item.addEventListener("click", (event) => {
                  event.stopPropagation();
                  const hasAction = typeof notif.onClick === "function";
                  if (hasAction) notif.onClick();
                  else this.removeNotification(notif.id);

                  const shouldClose = notif.closeControlCenterOnClick ?? hasAction;
                  if (shouldClose) {
                      this.element.querySelector(".control-center")?.classList.remove("visible");
                  }
              });
              list.appendChild(item);
          });
      }
  }

  addListener(element, eventType, handler, options) {
      if (!element) return;
      element.addEventListener(eventType, handler, options);
      if (!this.listeners.has(element)) {
          this.listeners.set(element, new Map());
      }
      const eventMap = this.listeners.get(element);
      if (!eventMap.has(eventType)) {
          eventMap.set(eventType, new Set());
      }
      eventMap.get(eventType).add(handler);
  }

  removeListener(element, eventType) {
      if (!this.listeners.has(element)) return;
      const eventMap = this.listeners.get(element);
      const handlers = eventMap.get(eventType);
      if (handlers) {
          for (const handler of handlers) {
              element.removeEventListener(eventType, handler);
          }
          eventMap.delete(eventType);
      }
      if (eventMap.size === 0) {
          this.listeners.delete(element);
      }
  }

  removeAllListeners() {
      for (const [element, eventMap] of this.listeners) {
          for (const [eventType, handlers] of eventMap) {
              for (const handler of handlers) {
                  element.removeEventListener(eventType, handler);
              }
          }
      }
      this.listeners.clear();
  }

  cleanup() {
      this.removeAllListeners();
  }

  _showGmTimeController() {
    if (!this._gmTimeControllerDialog) {
      this._gmTimeControllerDialog = new GmTimeControllerDialog(this);
    }
    this._gmTimeControllerDialog.show();
  }

  _renderFirstTimeSetup_Step1() {
    if (!this._firstTimeSetupWizard) {
      this._firstTimeSetupWizard = new FirstTimeSetupWizard(this);
    }
    this._firstTimeSetupWizard.renderStep1();
  }
  
  _renderFirstTimeSetup_Step2(targetActorTypes) {
    if (!this._firstTimeSetupWizard) {
      this._firstTimeSetupWizard = new FirstTimeSetupWizard(this);
    }
    this._firstTimeSetupWizard.renderStep2(targetActorTypes);
  }

  async selectChatRecipient(title, onSelect, options = {}) {
      const messagesApp = this.apps.get("messages");
      const contactsApp = this.apps.get("contacts");
      
      if (!messagesApp || !contactsApp) return;

      // 1. 데이터 로드 (연락처 및 최근 대화)
      await contactsApp.loadContacts();
      const recentConversations = options.hideRecents ? [] : await messagesApp._getRecentConversations();
      const allContacts = contactsApp.contacts || [];

      // 2. HTML 구조
      const dialogHTML = `
          <div class="contact-share-full-view">
              <div class="share-header">
                  <span>${escapeMessageHtml(title)}</span>
                  <button class="share-close-btn">${game.i18n.localize("SMARTPHONE.ui.cancel")}</button>
              </div>
              
              <div class="share-body">
                  <div class="share-tabs" ${options.hideRecents ? 'style="display:none"' : ''}>
                      ${options.hideRecents ? '' : `<div class="share-tab active" data-target="recents">${game.i18n.localize("SMARTPHONE.ui.recents")}</div>`}
                      <div class="share-tab ${options.hideRecents ? 'active' : ''}" data-target="contacts">${game.i18n.localize("SMARTPHONE.apps.contacts.title")}</div>
                  </div>
                  <div class="share-search-box">
                      <input type="text" placeholder="${game.i18n.localize("SMARTPHONE.apps.contacts.searchPlaceholder")}">
                  </div>
                  <div class="share-recipient-list" id="common-recipient-list"></div>
              </div>

              <div class="share-footer">
                  <button class="share-send-btn" disabled>
                      <i class="fas fa-check"></i> ${game.i18n.localize("SMARTPHONE.ui.confirm") || "확인"}
                  </button>
              </div>
          </div>
      `;

      const viewElement = document.createElement("div");
      viewElement.innerHTML = dialogHTML;
      const dialogNode = viewElement.firstElementChild;
      
      this.element.querySelector(".widget-content").appendChild(dialogNode);

      // 3. 로직 변수
      let selectedRecipient = null;
      let currentTab = options.hideRecents ? 'contacts' : 'recents';
      
      const listContainer = dialogNode.querySelector('#common-recipient-list');
      const confirmBtn = dialogNode.querySelector('.share-send-btn');
      const searchInput = dialogNode.querySelector('.share-search-box input');

      // 4. 리스트 렌더링 함수
      const renderList = () => {
          const query = searchInput.value.toLowerCase();
          let items = currentTab === 'recents' ? recentConversations : allContacts;

          if (query) {
              items = items.filter(item => String(item?.name || "").toLowerCase().includes(query));
          }

          if (items.length === 0) {
              listContainer.innerHTML = `<div class="empty-message" style="padding:40px; text-align:center; color:#999;">${game.i18n.localize("SMARTPHONE.apps.social.noSearchResults") || "결과 없음"}</div>`;
          } else {
              listContainer.innerHTML = items.map(item => {
                  const id = String(item?.id || "");
                  const isSelected = selectedRecipient === id;
                  const imgHtml = renderSafeShareAvatar(item);

                  return `
                      <div class="share-item ${isSelected ? 'selected' : ''}" data-id="${escapeMessageHtml(id)}">
                          ${imgHtml}
                          <span class="name">${escapeMessageHtml(item?.name)}</span>
                          <i class="fas fa-check-circle check-icon"></i>
                      </div>
                  `;
              }).join('');
          }

          listContainer.querySelectorAll('.share-item').forEach(el => {
              el.addEventListener('click', () => {
                  listContainer.querySelectorAll('.share-item').forEach(i => { i.classList.remove('selected'); });
                  el.classList.add('selected');
                  selectedRecipient = el.dataset.id;
                  confirmBtn.disabled = false;
              });
          });
      };

      // 5. 이벤트 리스너
      dialogNode.querySelector('.share-close-btn').addEventListener('click', () => dialogNode.remove());

      dialogNode.querySelectorAll('.share-tab').forEach(tab => {
          tab.addEventListener('click', (e) => {
              dialogNode.querySelectorAll('.share-tab').forEach(t => { t.classList.remove('active'); });
              e.currentTarget.classList.add('active');
              currentTab = e.currentTarget.dataset.target;
              renderList();
          });
      });

      searchInput.addEventListener('input', renderList);

      confirmBtn.addEventListener('click', () => {
          if (selectedRecipient) {
              onSelect(selectedRecipient);
              dialogNode.remove();
          }
      });

      renderList();
  }

    async applyCrackedEffect() {
        if (!this.element || !this.currentPhoneId) return;
        
        const devices = (await game.settings.get(this.ID, "smartphone-devices")) || {};
        const phoneData = devices[this.currentPhoneId];
        const overlay = this.element.querySelector('.cracked-overlay');
        
        if (overlay) {
            overlay.style.display = phoneData?.isCracked ? 'block' : 'none';
        }
    }

    _initBatteryDisplay() {
        if (!this.currentPhoneId || !BatteryManager.isEnabled) return;

        if (!BatteryManager.isBatteryActiveForPhone(this.currentPhoneId)) {
            this.updateBatteryDisplay(100);
            return;
        }

        const level = BatteryManager.getBatteryLevel(this.currentPhoneId);
        this.updateBatteryDisplay(level);
        if (level <= 0) this.showDeadScreen();

        const inZone = ChargingZoneManager.isInChargingZone(this.currentPhoneId);
        this.updateChargingZoneIndicator(inZone);
    }

    updateChargingZoneIndicator(inZone) {
        if (!this.element) return;

        this._updateDeadScreenState();

        const batteryIcon = this.element.querySelector(".battery-icon-clickable");
        if (!batteryIcon) return;

        const existing = this.element.querySelector(".charging-zone-indicator");

        if (inZone && !BatteryManager.isCharging(this.currentPhoneId)) {
            if (!existing) {
                const indicator = document.createElement("i");
                indicator.className = "fas fa-plug charging-zone-indicator";
                indicator.style.cssText = "color: #34c759; cursor: pointer; font-size: 0.7em; animation: sw-zone-pulse 1.5s ease-in-out infinite;";
                indicator.title = game.i18n.localize("SMARTPHONE.chargingZone.tapToCharge");
                indicator.addEventListener("click", (e) => {
                    e.stopPropagation();
                    if (this.currentPhoneId) {
                        ChargingZoneManager.startChargingFromZone(this.currentPhoneId);
                    }
                });
                batteryIcon.parentElement.insertBefore(indicator, batteryIcon);
            }
        } else if (existing) {
            existing.remove();
        }
    }

    updateBatteryDisplay(level, charging) {
        if (!this.element) return;
        const batteryIcon = this.element.querySelector(".battery-icon-clickable");
        if (!batteryIcon) return;

        if (!BatteryManager.isEnabled) return;

        const isCharging = charging ?? BatteryManager.isCharging(this.currentPhoneId);
        const { icon, color } = BatteryManager.getBatteryIconData(level);

        batteryIcon.className = `fas ${icon} battery-icon-clickable`;
        batteryIcon.style.color = isCharging ? "#34c759" : color;
        batteryIcon.classList.toggle("battery-charging", isCharging);
        batteryIcon.title = isCharging
            ? game.i18n.format("SMARTPHONE.battery.chargingToast", { level })
            : game.i18n.format("SMARTPHONE.battery.statusToast", { level });

        const bolt = this.element.querySelector(".battery-charging-bolt");
        if (isCharging && !bolt) {
            const boltEl = document.createElement("i");
            boltEl.className = "fas fa-bolt battery-charging-bolt";
            boltEl.style.cursor = "pointer";
            boltEl.title = game.i18n.localize("SMARTPHONE.battery.tapToStopCharging");
            boltEl.addEventListener("click", (e) => {
                e.stopPropagation();
                this._stopCharging();
            });
            batteryIcon.parentElement.insertBefore(boltEl, batteryIcon.nextSibling);
        } else if (!isCharging && bolt) {
            bolt.remove();
        }
    }

    showDeadScreen() {
        if (!this.element) return;
        const screen = this.element.querySelector(".smartphone-screen");
        if (!screen || screen.querySelector(".battery-dead-overlay")) return;

        const overlay = document.createElement("div");
        overlay.className = "battery-dead-overlay";
        overlay.innerHTML = `
            <div class="battery-dead-content">
                <i class="fas fa-battery-empty battery-dead-icon"></i>
            </div>
        `;
        overlay.addEventListener("click", (e) => e.stopPropagation());
        overlay.addEventListener("mousedown", (e) => e.stopPropagation());

        if (game.user.isGM) {
            const gmBtn = document.createElement("button");
            gmBtn.className = "battery-dead-gm-peek";
            gmBtn.innerHTML = `<i class="fas fa-eye"></i>`;
            gmBtn.title = game.i18n.localize("SMARTPHONE.battery.gmPeek");
            gmBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                overlay.remove();
            });
            overlay.appendChild(gmBtn);
        }

        screen.appendChild(overlay);
        this._updateDeadScreenState();
    }

    _updateDeadScreenState() {
        if (!this.element || !this.currentPhoneId) return;
        const overlay = this.element.querySelector(".battery-dead-overlay");
        if (!overlay) return;

        const icon = overlay.querySelector(".battery-dead-icon");
        const isCharging = BatteryManager.isCharging(this.currentPhoneId);
        const inZone = ChargingZoneManager.isInChargingZone(this.currentPhoneId);

        if (isCharging && icon) {
            icon.className = "fas fa-bolt battery-dead-icon charging";
        } else if (icon) {
            icon.className = "fas fa-battery-empty battery-dead-icon";
        }

        const existingChargeBtn = overlay.querySelector(".battery-dead-charge-btn");
        if (inZone && !isCharging) {
            if (!existingChargeBtn) {
                const chargeBtn = document.createElement("button");
                chargeBtn.className = "battery-dead-charge-btn";
                chargeBtn.innerHTML = `<i class="fas fa-plug"></i> ${game.i18n.localize("SMARTPHONE.battery.deadCharge")}`;
                chargeBtn.addEventListener("click", (e) => {
                    e.stopPropagation();
                    ChargingZoneManager.startChargingFromZone(this.currentPhoneId);
                });
                overlay.querySelector(".battery-dead-content").appendChild(chargeBtn);
            }
        } else if (existingChargeBtn) {
            existingChargeBtn.remove();
        }

        const existingPowerBtn = overlay.querySelector(".battery-dead-power-btn");
        if (isCharging) {
            if (!existingPowerBtn) {
                const circumference = 2 * Math.PI * 27;
                const powerBtn = document.createElement("div");
                powerBtn.className = "battery-dead-power-btn";
                powerBtn.innerHTML = `
                    <svg class="power-ring" viewBox="0 0 60 60">
                        <circle class="power-ring-bg" cx="30" cy="30" r="27" />
                        <circle class="power-ring-progress" cx="30" cy="30" r="27"
                            stroke-dasharray="${circumference}" stroke-dashoffset="${circumference}" />
                    </svg>
                    <i class="fas fa-power-off"></i>
                `;
                powerBtn.title = game.i18n.localize("SMARTPHONE.battery.holdToBootHint");

                let holdTimer = null;
                const ring = powerBtn.querySelector(".power-ring-progress");

                const startHold = (e) => {
                    e.stopPropagation();
                    ring.style.transition = "none";
                    ring.setAttribute("stroke-dashoffset", circumference);
                    requestAnimationFrame(() => {
                        ring.style.transition = "stroke-dashoffset 1.2s linear";
                        ring.setAttribute("stroke-dashoffset", "0");
                    });
                    powerBtn.classList.add("holding");

                    holdTimer = setTimeout(() => {
                        powerBtn.classList.remove("holding");
                        this.hideDeadScreen();
                    }, 1200);
                };

                const cancelHold = (e) => {
                    e.stopPropagation();
                    if (holdTimer) {
                        clearTimeout(holdTimer);
                        holdTimer = null;
                    }
                    powerBtn.classList.remove("holding");
                    ring.style.transition = "stroke-dashoffset 0.2s ease-out";
                    ring.setAttribute("stroke-dashoffset", circumference);
                };

                powerBtn.addEventListener("mousedown", startHold);
                powerBtn.addEventListener("mouseup", cancelHold);
                powerBtn.addEventListener("mouseleave", cancelHold);
                powerBtn.addEventListener("touchstart", startHold, { passive: false });
                powerBtn.addEventListener("touchend", cancelHold);
                powerBtn.addEventListener("touchcancel", cancelHold);

                overlay.querySelector(".battery-dead-content").appendChild(powerBtn);
            }
        } else if (existingPowerBtn) {
            existingPowerBtn.remove();
        }
    }

    hideDeadScreen() {
        if (!this.element) return;
        const overlay = this.element.querySelector(".battery-dead-overlay");
        if (!overlay) return;
        this._playBootAnimation();
        overlay.remove();
    }

    _playBootAnimation() {
        if (!this.element || !this.currentPhoneId) return;
        const screen = this.element.querySelector(".smartphone-screen");
        if (!screen) return;

        const existing = screen.querySelector(".boot-screen-overlay");
        if (existing) existing.remove();

        const bootLogos = game.settings.get(this.ID, "smartphone-boot-logos") || {};
        const bootLogoData = bootLogos[this.currentPhoneId];

        const overlay = document.createElement("div");
        overlay.className = "boot-screen-overlay";

        const logoPath = bootLogoData?.path
            || game.settings.get(this.ID, "default-boot-logo")
            || "";

        const fadeOut = () => {
            if (overlay.parentElement) {
                overlay.classList.add("fade-out");
                setTimeout(() => {
                    if (overlay.parentElement) overlay.remove();
                }, 500);
            }
        };

        if (logoPath) {
            const ext = logoPath.split(".").pop().toLowerCase();
            const videoExts = ["webm", "mp4", "m4v", "ogg"];

            if (videoExts.includes(ext)) {
                const video = document.createElement("video");
                video.src = logoPath;
                video.className = "boot-logo";
                video.autoplay = true;
                video.muted = false;
                video.playsInline = true;
                video.addEventListener("ended", fadeOut, { once: true });
                setTimeout(fadeOut, 15000);
                overlay.appendChild(video);
            } else {
                overlay.innerHTML = `<img src="${logoPath}" class="boot-logo" />`;
                setTimeout(fadeOut, 1500);
            }
        } else {
            overlay.innerHTML = `<div class="boot-logo-text">SMARTPHONE</div>`;
            setTimeout(fadeOut, 1500);
        }

        screen.appendChild(overlay);
    }

    async _stopCharging() {
        if (!this.currentPhoneId) return;
        if (!BatteryManager.isCharging(this.currentPhoneId)) return;

        await SmartphoneWidget.SOCKET?.executeAsGM("stopCharging", {
            phoneId: this.currentPhoneId,
        });
        const msg = game.i18n.localize("SMARTPHONE.battery.chargingStopped");
        this.showToastNotification(msg);
    }

    _showBatteryControlPanel() {
        if (!this.element || !this.currentPhoneId) return;

        const existing = this.element.querySelector(".battery-control-panel");
        if (existing) { existing.remove(); return; }

        const level = BatteryManager.getBatteryLevel(this.currentPhoneId);
        const isCharging = BatteryManager.isCharging(this.currentPhoneId);
        const panel = document.createElement("div");
        panel.className = "battery-control-panel";
        panel.innerHTML = `
            <div class="battery-control-header">
                <span>${game.i18n.localize("SMARTPHONE.battery.gmControlTitle")}</span>
                <button class="battery-control-close"><i class="fas fa-times"></i></button>
            </div>
            <div class="battery-control-body">
                <div class="battery-control-level">${level}%</div>
                <input type="range" class="battery-slider" min="0" max="100" value="${level}" step="5">
                <div class="battery-control-actions">
                    <button class="battery-btn-set">${game.i18n.localize("SMARTPHONE.battery.gmSetLevel")}</button>
                    ${isCharging ? `<button class="battery-btn-stop-charging"><i class="fas fa-plug-circle-xmark"></i> ${game.i18n.localize("SMARTPHONE.battery.stopCharging")}</button>` : ""}
                </div>
            </div>
        `;

        const screen = this.element.querySelector(".smartphone-screen");
        screen.appendChild(panel);

        const slider = panel.querySelector(".battery-slider");
        const levelDisplay = panel.querySelector(".battery-control-level");
        const phoneId = this.currentPhoneId;

        slider.addEventListener("input", () => {
            levelDisplay.textContent = `${slider.value}%`;
        });

        panel.querySelector(".battery-btn-set").addEventListener("click", async () => {
            await SmartphoneWidget.SOCKET?.executeAsGM("setBatteryLevel", {
                phoneId,
                level: parseInt(slider.value),
            });
            panel.remove();
        });

        const stopBtn = panel.querySelector(".battery-btn-stop-charging");
        if (stopBtn) {
            stopBtn.addEventListener("click", async () => {
                await this._stopCharging();
                panel.remove();
            });
        }

        panel.querySelector(".battery-control-close").addEventListener("click", () => {
            panel.remove();
        });

        panel.addEventListener("click", (e) => e.stopPropagation());
    }
}
