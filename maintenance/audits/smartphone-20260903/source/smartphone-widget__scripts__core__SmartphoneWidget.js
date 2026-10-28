import { WidgetManager } from "./WidgetManager.js";
import { SocketManager } from "./SocketManager.js";
import { PhoneNumberUtils } from "../utils/PhoneNumberUtils.js";
import { SmartphoneTime } from "./SmartphoneTime.js";
import { registerSettings, registerKeybindings, MODULE_ID } from "../config/settings.js";

// Apps for default registration
import { HomeApp } from "../apps/HomeApp.js";
import { MessagesApp } from "../apps/MessagesApp.js";
import { ContactsApp } from "../apps/ContactsApp.js";
import { CalculatorApp } from "../apps/CalculatorApp.js";
import { NotesApp } from "../apps/NotesApp.js";
import { SocialApp } from "../apps/SocialApp.js";
import { MinefinderApp } from "../apps/MinefinderApp.js";
import { CheckersApp } from "../apps/CheckersApp.js";
import { PhoneApp } from "../apps/PhoneApp.js";
import { SettingsApp } from "../apps/SettingsApp.js";
import { BankingApp } from "../apps/BankingApp.js";
import { CurrencyManagerDialog } from "../apps/CurrencyManagerDialog.js";
import { GachaApp } from "../apps/GachaApp.js";
import { DiceApp } from "../apps/DiceApp.js";
import { CalendarApp } from "../apps/CalendarApp.js";
import { AppStoreApp } from "../apps/AppStoreApp.js";
import { WalletApp } from "../apps/WalletApp.js";
import { GalleryApp } from "../apps/GalleryApp.js";
import { WeatherApp } from "../apps/WeatherApp.js"; 

export class SmartphoneWidget {
  static ID = MODULE_ID;
  static instances = new Map();
  static appDefinitions = new Map();
  static registeredWidgetClasses = []; 
  static externalAppInitializers = [];
  static badgeUpdaters = new Map();
  static activeCallTimeouts = new Map(); 
  static activeCheckersGames = new Map(); 
  static SOCKET_CACHE = null;

  static get SOCKET() {
    return SocketManager.get();
  }

  static initialize() {
    console.log("Smartphone Widget | Initializing");
    registerSettings();
    registerKeybindings();
  }

  /**
   * 외부 모듈이 새로운 스마트폰 앱을 등록할 수 있도록 API를 제공합니다.
   * @param {object} appData - 등록할 앱의 정보
   * @param {string} appData.id - 앱의 고유 ID (예: 'macros')
   * @param {string} appData.name - 앱의 기본 이름 (예: '매크로')
   * @param {string} appData.icon - Font Awesome 아이콘 클래스 (예: 'fas fa-terminal')
   * @param {string} appData.color - 홈 화면 아이콘 배경색
   * @param {string} appData.category - 앱스토어 카테고리 (예: 'game', 'social', 'utility'). 이 값은 지역화 키로 사용됩니다.
   * @param {BaseApp} appData.appClass - BaseApp을 상속받는 앱의 클래스
   * @param {boolean} [appData.defaultInstalled=false] - true인 경우, 최초 등록 시 모든 기기에 기본 앱으로 자동 설치됩니다. GM이 이후 수동으로 제거하면 다시 추가되지 않습니다.
   */
  static registerApp(appData) {
    if (!appData.id || !appData.appClass) {
      console.error("Smartphone Widget | App registration failed: id and appClass are required.", appData);
      return;
    }
    console.log(`Smartphone Widget | Registering external app: ${appData.id}`);
    this.appDefinitions.set(appData.id, appData);
  }

  static appThemeRegistry = new Map();

  /**
   * 외부 모듈이 설정 앱의 '앱 테마' 메뉴에 자체 테마 선택 항목을 등록할 수 있도록 API를 제공합니다.
   * 등록된 항목은 뱅킹 앱 테마와 같은 방식(선택 목록 + 체크 표시)으로 렌더링됩니다.
   * @param {object} def - 테마 항목 정의
   * @param {string} def.id - 고유 ID (예: 'stylishshop')
   * @param {string} def.label - 메뉴에 표시할 이름의 지역화 키
   * @param {string} [def.icon='fas fa-swatchbook'] - Font Awesome 아이콘 클래스
   * @param {string} def.namespace - 테마 설정이 등록된 game.settings 네임스페이스 (보통 모듈 ID)
   * @param {string} def.settingKey - 테마 값을 저장하는 String 설정 키
   * @param {Array<{id: string, label: string}>} def.choices - 선택지 목록 (label은 지역화 키)
   */
  static registerAppTheme(def) {
    if (!def?.id || !def.namespace || !def.settingKey || !Array.isArray(def.choices) || def.choices.length === 0) {
      console.error("Smartphone Widget | App theme registration failed: id, namespace, settingKey and choices are required.", def);
      return;
    }
    console.log(`Smartphone Widget | Registering app theme entry: ${def.id}`);
    this.appThemeRegistry.set(def.id, def);
  }

  static async _processExternalDefaultApps() {
    if (!game.user.isGM) return;

    const processed = game.settings.get(this.ID, "processed-external-defaults") || [];
    const defaultApps = game.settings.get(this.ID, "default-installed-apps") || [];
    let defaultsChanged = false;
    let processedChanged = false;

    for (const [id, def] of this.appDefinitions.entries()) {
      if (!def.defaultInstalled || processed.includes(id)) continue;

      if (!defaultApps.includes(id)) {
        defaultApps.push(id);
        defaultsChanged = true;
        console.log(`Smartphone Widget | Auto-adding '${id}' to default installed apps.`);
      }
      processed.push(id);
      processedChanged = true;
    }

    if (defaultsChanged) {
      await game.settings.set(this.ID, "default-installed-apps", defaultApps);
    }
    if (processedChanged) {
      await game.settings.set(this.ID, "processed-external-defaults", processed);
    }
  }

  /**
   * 외부 모듈에서 위젯을 등록하는 메서드
   * @param {Class} widgetClass - definitions(get)와 render(static async)를 가진 클래스
   */
  static registerWidget(widgetClass) {
    if (!widgetClass.definitions || typeof widgetClass.render !== 'function') {
      console.error("Smartphone Widget | Widget registration failed: Class must have static 'definitions' getter and 'render' method.");
      return;
    }
    console.log(`Smartphone Widget | Registering external widget: ${widgetClass.name}`);
    this.registeredWidgetClasses.push(widgetClass);
  }  

  static async getInstance() {
    if (!game.user) return null;

    const userId = game.user.id;
    if (!this.instances.has(userId)) {
      const manager = new WidgetManager();
      manager.ID = this.ID;
      manager.userId = userId;

      // 앱 등록
      manager.registerApp("home", new HomeApp(manager));
      manager.registerApp("phone", new PhoneApp(manager));
      manager.registerApp("messages", new MessagesApp(manager));
      manager.registerApp("contacts", new ContactsApp(manager));
      manager.registerApp("calculator", new CalculatorApp(manager));
      manager.registerApp("notes", new NotesApp(manager));
      manager.registerApp("social", new SocialApp(manager));
      manager.registerApp("minefinder", new MinefinderApp(manager));
      manager.registerApp("checkers", new CheckersApp(manager));
      manager.registerApp("settings", new SettingsApp(manager));
      manager.registerApp("banking", new BankingApp(manager));
      manager.registerApp("gacha", new GachaApp(manager));
      manager.registerApp("dice", new DiceApp(manager));
      manager.registerApp("calendar", new CalendarApp(manager));
      manager.registerApp("appstore", new AppStoreApp(manager));
      manager.registerApp("wallet", new WalletApp(manager));
      manager.registerApp("gallery", new GalleryApp(manager));
      manager.registerApp("weather", new WeatherApp(manager)); 

      for (const [id, def] of this.appDefinitions.entries()) {
        manager.registerApp(id, new def.appClass(manager));
      }

      await this._processExternalDefaultApps();

      this.instances.set(userId, manager);
    }

    const instance = this.instances.get(userId);

    return instance;
  }

  static initializeSocket() {
      // Delegate to SocketManager, passing context handlers
      return SocketManager.init(
          this.ID, 
          this.handleStatusUpdate.bind(this), 
          this.handleNotificationUpdate.bind(this)
      );
  }

  static async isVisible() {
    const instance = await this.getInstance();
    return instance?.element != null;
  }

  static async show(options = {}) {
    const instance = await this.getInstance();
    if (!instance) return false;

    // GM인 경우, 폰 유무와 상관없이 항상 위젯을 표시합니다. (최초 설정 등)
    if (game.user.isGM) {
      const devices = (await game.settings.get(this.ID, "smartphone-devices")) || {};
      const isFirstTime = Object.keys(devices).length === 0;

      if (isFirstTime || options.firstTime) {
        await instance.show({ firstTime: true });
      } else {
        if (!instance.currentPhoneId && Object.keys(devices).length > 0) {
          instance.currentPhoneId = Object.values(devices)[0].id;
          instance.currentActorId = Object.values(devices)[0].ownerId;
        }
        await instance.show();
      }

      const toggleBtn = document.querySelector("#smartphone-widget-toggle .toggle-btn");
      if (toggleBtn) toggleBtn.classList.add("active");
      return true;
    }

    // --- 플레이어인 경우의 로직 ---
    const devices = (await game.settings.get(this.ID, "smartphone-devices")) || {};
    const deviceList = Object.values(devices);
    const ownedActorIds = game.actors
      .filter(actor => actor.testUserPermission(game.user, CONST.DOCUMENT_OWNERSHIP_LEVELS.OWNER))
      .map(actor => actor.id);

    const accessiblePhones = deviceList.filter(
      (d) => ownedActorIds.includes(d.ownerId) || d.ownerId === game.user.id
    );

    if (accessiblePhones.length === 0) {
      // 접근 가능한 폰이 없으면, "기기 없음" 화면을 표시합니다.
      await instance.showNoDeviceScreen();

      // 토글 버튼 상태는 활성화로 유지합니다.
      const toggleBtn = document.querySelector("#smartphone-widget-toggle .toggle-btn");
      if (toggleBtn) toggleBtn.classList.add("active");
      return true; // 위젯이 (안내 화면이라도) 표시되었으므로 true를 반환합니다.
    }
    else {
      // 접근 가능한 폰이 있으면, 정상적으로 폰을 표시합니다.
      if (!instance.currentPhoneId || !accessiblePhones.some(p => p.id === instance.currentPhoneId)) {
        // 현재 선택된 폰이 없거나, 더 이상 접근할 수 없는 폰이면 목록의 첫 번째 폰을 선택합니다.
        instance.currentPhoneId = accessiblePhones[0].id;
        instance.currentActorId = accessiblePhones[0].ownerId;
      }
      await instance.show();

      const toggleBtn = document.querySelector("#smartphone-widget-toggle .toggle-btn");
      if (toggleBtn) toggleBtn.classList.add("active");
      return true;
    }
  }

  static async hide() {
    const instance = await this.getInstance();
    if (instance) {
      instance.hide();
    }
  }

  // 소켓 핸들러들
  static handleMessageUpdate(data) {
    const instance = this.getInstance(); // No await needed here if instance is cached? Actually getInstance is async.
    // However, if we call it synchronously it returns a promise.
    // The original code was synchronous: const instance = this.getInstance(); 
    // But getInstance is async in original too. 
    // Wait, let's check original getInstance.
    // Original getInstance: static async getInstance() { ... }
    // Original handleMessageUpdate: static handleMessageUpdate(data) { const instance = this.getInstance(); ... }
    // This looks like a bug in original code or I am misreading. 
    // Ah, if getInstance returns a promise, doing `if (instance)` checks the promise object (truthy).
    // Then `instance.getApp` would fail if it's a promise.
    // BUT, getInstance checks `this.instances.has(userId)`. If it has, it returns the instance (sync-like).
    // If not, it creates and sets.
    // Actually, `this.instances.get(userId)` returns the manager object.
    
    // So if the instance is already created, `getInstance` could be synchronous? 
    // No, it's marked `async`, so it ALWAYS returns a promise.
    // So `const instance = this.getInstance()` results in `instance` being a Promise.
    // Then `instance.getApp` -> `Promise.getApp` -> undefined.
    // This means the original code might have been buggy or I should use `await`.
    
    // I will use `this.instances.get(game.user.id)` directly for synchronous access if initialized.
    
    if (!game.user) return;
    const manager = this.instances.get(game.user.id);
    if (manager) {
       const messagesApp = manager.getApp("messages");
       if (messagesApp) messagesApp.handleMessageUpdate(data);
    }
  }

  static handleStatusUpdate(data) {
    if (!game.user) return;
    const manager = this.instances.get(game.user.id);
    if (manager) {
        const contactsApp = manager.getApp("contacts");
        if (contactsApp) contactsApp.handleStatusUpdate(data);
    }
  }

  static handleNotificationUpdate(data) {
    if (!game.user) return;
    const manager = this.instances.get(game.user.id);
    if (manager) {
      const { title, message, icon } = data;
      manager.showNotification(title, message, icon);
    }
  }

  static showError(message) {
    ui.notifications.error(`Smartphone Widget | ${message}`);
  }

  static generateRandomPart(format) {
    return PhoneNumberUtils.generateRandomPart(format);
  }

  static async generatePhoneNumber(pattern = null) {
      return PhoneNumberUtils.generatePhoneNumber(this.ID, pattern);
  }

  static async isValidPhoneNumber(number) {
    return PhoneNumberUtils.isValidPhoneNumber(this.ID, number);
  }

  /**
   * 아이템을 새로운 스마트폰 기기로 설정합니다. (소유자 유무에 따라 다르게 처리)
   * @param {Item} item - 폰으로 설정할 아이템
   */
  static async setDeviceToItem(item) {
    if (!item) return;

    const devices = game.settings.get(this.ID, "smartphone-devices") || {};
    const newPhoneId = foundry.utils.randomID();

    const ownerId = item.actor ? item.actor.id : null;
    const ownerName = item.actor
      ? item.actor.name
      : game.i18n.localize("SMARTPHONE.ui.ownerlessPhone");

    const newPhoneNumber = await this.generatePhoneNumber();

    const newDevice = {
      id: newPhoneId,
      ownerId: ownerId,
      phoneNumber: newPhoneNumber,
      name: `${ownerName}의 ${item.name}`,
      // 개통 시각은 여전히 유용하므로 유지합니다.
      activatedAt: Date.now(),
    };

    devices[newPhoneId] = newDevice;

    await game.settings.set(this.ID, "smartphone-devices", devices);
    await item.setFlag(this.ID, "phoneId", newPhoneId);
    await this.applyPhoneDefaults(newPhoneId);

    return newDevice;
  }

  static async applyPhoneDefaults(phoneId) {
    const defaultWallpaper = game.settings.get(this.ID, "default-wallpaper") || {};
    const defaultFrame = game.settings.get(this.ID, "default-frame") || "";

    if (defaultWallpaper.path) {
        const wallpapers = foundry.utils.deepClone(
            game.settings.get(this.ID, "smartphone-wallpapers") || {}
        );
        wallpapers[phoneId] = { path: defaultWallpaper.path, fit: defaultWallpaper.fit || "cover" };
        await game.settings.set(this.ID, "smartphone-wallpapers", wallpapers);
    }

    if (defaultFrame) {
        const frames = foundry.utils.deepClone(
            game.settings.get(this.ID, "smartphone-frames") || {}
        );
        frames[phoneId] = defaultFrame;
        await game.settings.set(this.ID, "smartphone-frames", frames);
    }
  }

  static async unsetDeviceFromItem(item) {
    const phoneId = item.getFlag(this.ID, "phoneId");
    if (phoneId) {
      await this.removeDevice(phoneId);
      // 플래그를 unset하는 것이 아니라, null이나 false로 설정하는 것이 더 안정적일 수 있습니다.
      await item.setFlag(this.ID, "phoneId", null);
    }
  }

  static async removeDevice(phoneId) {
    const devices = game.settings.get(this.ID, "smartphone-devices") || {};
    if (devices[phoneId]) {
      delete devices[phoneId];
      await game.settings.set(this.ID, "smartphone-devices", devices);
    }
  }

  /**
   * 지정된 앱 아이콘에 알림 뱃지를 표시합니다.
   * @param {string} appId - 뱃지를 표시할 앱의 ID
   * @param {number|string} count - 뱃지에 표시할 숫자 또는 문자열. 0이면 뱃지가 사라집니다.
   */
  static async showBadge(appId, count) {
    const instance = await this.getInstance();
    if (instance) {
      instance.showBadge(appId, count);
    }
  }

  /**
   * (API용) 특정 앱의 뱃지 카운트를 계산하는 로직을 등록합니다.
   * @param {string} appId - 뱃지를 등록할 앱의 ID
   * @param {function(): Promise<number>} handler - 비동기적으로 숫자를 반환하는 함수.
   */
  static registerBadgeUpdater(appId, handler) {
    if (typeof handler !== 'function') {
      console.error(`Smartphone Widget | Badge updater for '${appId}' must be a function.`);
      return;
    }
    console.log(`Smartphone Widget | Registering badge updater for: ${appId}`);
    this.badgeUpdaters.set(appId, handler);
  }

  /**
   * (API용) 등록된 로직을 사용해 특정 앱 또는 모든 앱의 뱃지를 업데이트합니다.
   * @param {string|null} appId - 업데이트할 앱의 ID. null이면 모든 앱을 업데이트합니다.
   * @param {number|null} [count=null] - (선택사항) 제공될 경우, 계산 로직을 건너뛰고 이 숫자를 즉시 뱃지에 표시합니다.
   */
  static async updateBadge(appId = null, count = null) { 
    if (appId) {
      if (typeof count === 'number') {
        // count가 제공되면, 계산 없이 즉시 뱃지를 표시합니다 (낙관적 업데이트용).
        await this.showBadge(appId, count);
        return; 
      }

      // count가 제공되지 않았을 경우에만 등록된 핸들러를 실행합니다.
      const handler = this.badgeUpdaters.get(appId);
      if (handler) {
        try {
          const handlerCount = await handler(); // 비동기 함수 실행
          await this.showBadge(appId, handlerCount);
        } catch (e) {
          console.error(`Smartphone Widget | Error updating badge for '${appId}':`, e);
        }
      }
    } else {
      // 모든 앱 업데이트 로직 (변경 없음)
      for (const [id, handler] of this.badgeUpdaters.entries()) {
        try {
          const handlerCount = await handler();
          await this.showBadge(id, handlerCount);
        } catch (e) {
          console.error(`Smartphone Widget | Error updating badge for '${id}':`, e);
        }
      }
    }
  }

  /**
   * 스마트폰 화면에 토스트 알림을 표시합니다.
   * @param {string} htmlContent - 알림에 표시할 HTML 내용
   * @param {object} options - 알림 옵션 (예: { onClick: () => { ... } })
   */
  static async showToastNotification(htmlContent, options = {}) {
    const instance = await this.getInstance();
    if (instance) {
      instance.showToastNotification(htmlContent, options);
    }
  }

  static async sendSystemMessage(targetPhoneId, content, options = {}) {
    if (!game.user.isGM) {
        ui.notifications.error(game.i18n.localize("SMARTPHONE.errors.gmOnly"));
        return;
    }

    const { senderAlias = 'SYSTEM', senderPhoneId = null, chatKey: explicitChatKey } = options;

    const allPhones = await this.getAllPhones();
    const targetPhone = allPhones.find(p => p.id === targetPhoneId);
    
    if (!targetPhone) {
        console.error(`sendSystemMessage Error: Target phone with ID '${targetPhoneId}' not found.`);
        return { success: false, error: 'Target phone not found' };
    }
    
    let senderPhoneNumber;
    let senderId;

    if (!senderPhoneId) {
        // 현재 활성화된 폰이 있는지 확인
        const currentPhone = await this.getCurrentPhone();
        
        if (currentPhone) {
            // 활성 폰이 있으면 그걸 사용
            senderPhoneNumber = currentPhone.phoneNumber;
            senderId = currentPhone.ownerId;
        } else {
            // 활성 폰도 없으면 'senderAlias'를 가상 번호로 사용 (예: "고객센터", "경비대")
            senderPhoneNumber = senderAlias;
            senderId = null; // 시스템 메시지이므로 sender ID(Actor ID)는 없음
        }
    } 
    else {
        const senderPhone = allPhones.find(p => p.id === senderPhoneId);
        if (senderPhone) {
            senderPhoneNumber = senderPhone.phoneNumber;
            senderId = senderPhone.ownerId;
        } else {
            // ID를 줬는데 못 찾은 경우 -> 에러 대신 가상 모드로 폴백
            console.warn(`Smartphone Widget | Sender phone ID '${senderPhoneId}' not found. Falling back to virtual sender '${senderAlias}'.`);
            senderPhoneNumber = senderAlias;
            senderId = null;
        }
    }

    const chatKey = explicitChatKey || [senderPhoneNumber, targetPhone.phoneNumber].sort().join('-');

    const useGameTime = game.settings.get(this.ID, "useGameTime");
    const timestamp = useGameTime ? SmartphoneTime.now() : Date.now();

    const systemMessageData = {
        id: foundry.utils.randomID(),
        content: content,
        sender: senderId, 
        senderPhoneNumber: senderPhoneNumber, // 결정된 번호(혹은 이름) 사용
        systemSenderAlias: senderAlias,
        timestamp: timestamp,
        worldTime: Date.now(),
        isSystemMessage: true,
    };

    // 소켓 호출 (Use SocketManager.get() instead of this.SOCKET)
    return await SocketManager.get().executeAsGM("createAndSaveMessage", {
        messageData: systemMessageData,
        chatLogContent: `<div class="phone-message-header">[${senderAlias}]</div>${content}`,
        flags: { "smartphone-widget": { isSmartphoneMessage: true, isSystemMessage: true } },
        isGroup: chatKey.startsWith("group-"),
        groupId: chatKey.startsWith("group-") ? chatKey : null,
        chatId: !chatKey.startsWith("group-") ? chatKey : null,
        senderUserId: game.user.id,
        // 알림은 오직 타겟 폰에게만
        notificationTargetPhoneIds: [targetPhoneId] 
    });
  }

  static async sendMessage(senderActorId, receiverId, content) {
    if (!game.user.isGM) {
      ui.notifications.error("This function can only be executed by a GM.");
      return null;
    }

    // 1. 필수 인자 확인
    if (!senderActorId || !receiverId || !content) {
      console.error("sendMessage Error: senderActorId, receiverId, and content are required.");
      return null;
    }

    const allPhones = await this.getAllPhones();

    // 2. 발신자 정보 확인
    const senderActor = game.actors.get(senderActorId);
    const senderPhone = allPhones.find(p => p.ownerId === senderActorId);
    if (!senderActor || !senderPhone) {
      console.error(`sendMessage Error: Sender with Actor ID '${senderActorId}' does not exist or has no phone.`);
      return null;
    }

    // 3. 수신자 정보 및 채팅 키 결정
    const isGroup = receiverId.startsWith("group-");
    let chatKey;
    let chatLogHeader;

    if (isGroup) {
      const groupChats = game.settings.get(this.ID, "groupChats") || {};
      const group = groupChats[receiverId];
      if (!group) {
        console.error(`sendMessage Error: Group with ID '${receiverId}' not found.`);
        return null;
      }
      chatKey = receiverId;
      chatLogHeader = game.i18n.format("SMARTPHONE.apps.messages.chatLogHeaderGroup", {
        sender: senderActor.name,
        group: group.name
      });

    } else { // 1:1 채팅
      const receiverActor = game.actors.get(receiverId);
      const receiverPhone = allPhones.find(p => p.ownerId === receiverId);
      if (!receiverActor || !receiverPhone) {
        console.error(`sendMessage Error: Receiver with Actor ID '${receiverId}' does not exist or has no phone.`);
        return null;
      }
      chatKey = [senderPhone.phoneNumber, receiverPhone.phoneNumber].sort().join('-');
      chatLogHeader = game.i18n.format("SMARTPHONE.apps.messages.chatLogHeaderDM", {
        sender: senderActor.name,
        recipient: receiverActor.name
      });
    }

    // 4. 메시지 데이터 준비
    const useGameTime = game.settings.get(this.ID, "useGameTime");
    const timestamp = useGameTime ? SmartphoneTime.now() : Date.now();

    const messageData = {
      id: foundry.utils.randomID(),
      content: content,
      sender: senderActorId,
      senderPhoneNumber: senderPhone.phoneNumber,
      timestamp: timestamp,
      worldTime: Date.now(),
      isSystemMessage: false, // 일반 메시지이므로 false
    };

    // 5. 소켓 핸들러 호출
    return await SocketManager.get().executeAsGM("createAndSaveMessage", {
      messageData: messageData,
      chatLogContent: `<div class="phone-message-header">${chatLogHeader}</div>${content}`,
      flags: { "smartphone-widget": { isSmartphoneMessage: true } },
      isGroup: isGroup,
      groupId: isGroup ? chatKey : null,
      chatId: !isGroup ? chatKey : null,
      senderUserId: game.user.id, // API를 호출한 GM의 ID
    });
  }

  /**
   * 월드에 존재하는 모든 스마트폰 기기 목록을 반환합니다.
   * @returns {Promise<object[]>}
   */
  static async getAllPhones() {
    const devices = await game.settings.get(this.ID, "smartphone-devices") || {};
    return Object.values(devices);
  }

  /**
   * 특정 액터 ID가 소유한 스마트폰 기기 정보를 반환합니다.
   * @param {string} actorId - 액터의 ID
   * @returns {Promise<object|null>}
   */
  static async getPhoneForActor(actorId) {
    const allPhones = await this.getAllPhones();
    return allPhones.find(phone => phone.ownerId === actorId) || null;
  }

  /**
   * 현재 게임을 플레이 중인 사용자의 활성화된 스마트폰 정보를 반환합니다.
   * @returns {Promise<object|null>}
   */
  static async getCurrentPhone() {
    const instance = await this.getInstance();
    if (!instance || !instance.currentPhoneId) return null;

    const allPhones = await this.getAllPhones();
    return allPhones.find(phone => phone.id === instance.currentPhoneId) || null;
  }

  /**
   * 사용자의 폰에서 연락처를 선택하는 다이얼로그를 엽니다.
   * @param {string} title - 다이얼로그 제목
   * @param {Function} onSelect - 선택 완료 시 실행될 콜백 (인자: selectedId)
   */
  static async selectChatRecipient(title, onSelect) {
    const instance = await this.getInstance();
    if (instance) {
      // 위젯이 닫혀있을 수 있으므로 강제로 엽니다.
      if (!instance.element) {
        await this.show();
      }
      // WidgetManager의 공통 함수 호출
      return instance.selectChatRecipient(title, onSelect);
    }
  }
}
