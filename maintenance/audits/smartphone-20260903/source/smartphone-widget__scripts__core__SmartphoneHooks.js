import { SmartphoneWidget } from "./SmartphoneWidget.js";
import { CurrencyManagerDialog } from "../apps/CurrencyManagerDialog.js";
import { BatteryManager } from "./BatteryManager.js";
import {
  escapeMessageHtml,
  sanitizeMessageAssetUrl,
} from "../utils/messageHtml.js";

// 임시 고아 폰 데이터를 저장할 클라이언트 측 변수
const orphanedPhones = new Map();

function _resolveSceneFromContext(context, isLegacy) {
    if (!context) return null;
    const base = isLegacy && context?.dataset ? context : (context?.currentTarget || context?.target || context?.[0] || context);
    const el = base?.closest ? base.closest("[data-document-id], [data-entry-id]") || base : base;
    const documentId = el?.dataset?.documentId || el?.dataset?.entryId;
    if (!documentId) return null;
    return game.scenes.get(documentId) || null;
}

function _pushSceneContextEntries(entries, isLegacy) {
    entries.push({
        name: game.i18n.localize("SMARTPHONE.sceneConfig.contextMenu"),
        icon: '<i class="fas fa-mobile-alt"></i>',
        condition: (context) => {
            if (!game.user.isGM) return false;
            return !!_resolveSceneFromContext(context, isLegacy);
        },
        callback: async (context) => {
            const scene = _resolveSceneFromContext(context, isLegacy);
            if (!scene) return;
            const { SceneSmartphoneConfig } = await import("./SceneSmartphoneConfig.js");
            new SceneSmartphoneConfig(scene).render(true);
        },
    });
}

export function registerInitHooks() {
  Hooks.on("getSceneDirectoryEntryContext", (html, entries) => {
    _pushSceneContextEntries(entries, true);
  });

  Hooks.on("getSceneContextOptions", (application, menuItems) => {
    _pushSceneContextEntries(menuItems, false);
  });

  Hooks.on("renderTileHUD", (hud, html, data) => {
    if (!game.user.isGM || !BatteryManager.isEnabled) return;

    const tileDoc = hud.object?.document;
    if (!tileDoc) return;

    const el = html instanceof HTMLElement ? html : html[0] ?? html;
    if (!el || typeof el.querySelector !== "function") return;

    const flag = tileDoc.getFlag(SmartphoneWidget.ID, "chargingStation") || {};
    const isActive = !!flag.enabled;

    const btn = document.createElement("div");
    btn.classList.add("control-icon");
    if (isActive) btn.classList.add("active");
    btn.dataset.action = "smartphone-charging-config";
    btn.title = game.i18n.localize("SMARTPHONE.chargingZone.tileConfigTitle");
    btn.innerHTML = `<i class="fas fa-bolt"></i>`;

    btn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      import("../apps/ChargingStationConfig.js").then(mod => {
        new mod.ChargingStationConfig(tileDoc).render(true);
      });
    });

    const col = el.querySelector(".col.right") || el.querySelector(".col.left");
    if (col) col.appendChild(btn);
  });

  CONFIG.ui.currencyManager = CurrencyManagerDialog;
}

export function registerReadyHooks() {
  const chatLog = document.getElementById("chat-log");
  if (chatLog) {
    // dragover 이벤트: 드롭이 가능한 영역임을 브라우저에 알립니다.
    chatLog.addEventListener("dragover", (e) => {
      // 스마트폰 연락처 데이터가 있는지 확인
      if (e.dataTransfer.types.includes("application/json")) {
        e.preventDefault(); // 기본 동작(드롭 방지)을 막음
        e.dataTransfer.dropEffect = "copy";
        chatLog.classList.add("smartphone-drop-target"); // 시각적 피드백
      }
    });

    // dragleave 이벤트: 드래그가 영역을 벗어났을 때 시각적 피드백 제거
    chatLog.addEventListener("dragleave", (e) => {
      chatLog.classList.remove("smartphone-drop-target");
    });

    // drop 이벤트: 실제 드롭이 발생했을 때 처리
    chatLog.addEventListener("drop", async (e) => {
      e.preventDefault();
      chatLog.classList.remove("smartphone-drop-target");

      const data = e.dataTransfer.getData("application/json");
      if (!data) return;

      try {
        const contact = JSON.parse(data);
        if (!contact || typeof contact !== "object") return;

        const name = escapeMessageHtml(
          String(contact.name || game.i18n.localize("SMARTPHONE.ui.unknown"))
            .slice(0, 200)
        );
        const phone = escapeMessageHtml(
          String(contact.phone || game.i18n.localize("SMARTPHONE.ui.noNumber"))
            .slice(0, 200)
        );
        const avatar = escapeMessageHtml(
          sanitizeMessageAssetUrl(contact.avatar)
        );

        // 예쁜 HTML 카드 형식으로 메시지 내용 생성
        const messageContent = `
                    <div style="border: 1px solid #ccc; border-radius: 8px; padding: 10px; background-color: #f9f9f9; display: flex; align-items: center; gap: 10px; color:black;">
                        <img src="${avatar}" style="width: 40px; height: 40px; border-radius: 50%;">
                        <div>
                            <strong style="display: block;">${name}</strong>
                            <span style="font-size: 0.9em; color: #555;">${phone}</span>
                        </div>
                    </div>
                `;

        // 채팅 메시지 생성
        ChatMessage.create({
          speaker: ChatMessage.getSpeaker({
            alias: game.i18n.localize("SMARTPHONE.ui.contactShare"),
          }),
          content: messageContent,
        });
      } catch (error) {
        console.warn(game.i18n.localize("SMARTPHONE.ui.dropFailed"), error);
      }
    });

    // 드롭 존 시각적 피드백을 위한 CSS 추가
    const style = document.createElement("style");
    style.innerHTML = `
            #chat-log.smartphone-drop-target {
                outline: 2px dashed #007AFF;
                outline-offset: -4px;
                background-color: rgba(0, 122, 255, 0.1);
            }
        `;
    document.head.appendChild(style);

    // 채팅 로그 전체에 단 하나의 '클릭' 이벤트 리스너를 등록합니다. (이벤트 위임)
    // 이 리스너는 채팅 로그가 새로고침되어도 절대 사라지지 않습니다.
    chatLog.addEventListener("click", async (event) => {
      // 클릭된 요소가 '.add-contact-from-chat-log' 버튼인지 확인합니다.
      const button = event.target.closest(".add-contact-from-chat-log");
      if (!button) return; // 해당 버튼이 아니면 아무것도 하지 않음

      event.preventDefault();

      // 현재 위젯 인스턴스와 연락처 앱을 가져옵니다.
      const widgetInstance = await SmartphoneWidget.getInstance(); 
      if (!widgetInstance) {
        return ui.notifications.warn(
          game.i18n.localize("SMARTPHONE.notifications.widgetNotActive")
        );
      }
      const contactsApp = widgetInstance.apps.get("contacts");
      if (!contactsApp) return;

      // 버튼에 저장된 데이터로 연락처를 추가하는 함수를 호출합니다.
      const { actorId, name, phone, avatar } = button.dataset;
      const result = await contactsApp._addContactFromCard({
        id: actorId,
        name,
        phone,
        avatar,
      });

      // 성공 시 사용자에게 피드백을 줍니다.
      if (result) {
        const safeContactName = foundry.utils.escapeHTML(
          game.actors.get(actorId)?.name || phone || ""
        );
        ui.notifications.info(
          game.i18n.format("SMARTPHONE.notifications.contactAdded", {
            name: safeContactName,
          })
        );
        button.textContent = game.i18n.localize("SMARTPHONE.ui.added");
        button.disabled = true;
      }
    });
  }
}

export function registerRuntimeHooks() {
  Hooks.on("closeGame", () => {
    SmartphoneWidget.hide();
  });

  Hooks.on("getSceneControlButtons", (controls) => {
    // --- For v12 (controls is an Array) ---
    if (Array.isArray(controls)) {
      const tokenControls = controls.find((c) => c.name === "token");
      if (
        tokenControls &&
        !tokenControls.tools.find((t) => t.name === "smartphone")
      ) {
        tokenControls.tools.push({
          name: "smartphone",
          title: game.i18n.localize("SMARTPHONE.module.title"),
          icon: "fas fa-mobile-alt",
          active: game.settings.get("smartphone-widget", "showWidget"),
          toggle: true,
          onClick: () => {
            // v12 uses onClick
            const current = game.settings.get("smartphone-widget", "showWidget");
            game.settings.set("smartphone-widget", "showWidget", !current);
          },
        });
      }
    }
    // --- For v13+ (controls is an Object) ---
    else {
      const tokenControls = controls.tokens;
      if (tokenControls && !tokenControls.tools.smartphone) {
        tokenControls.tools.smartphone = {
          name: "smartphone",
          title: game.i18n.localize("SMARTPHONE.module.title"),
          icon: "fas fa-mobile-alt",
          active: game.settings.get("smartphone-widget", "showWidget"),
          toggle: true,
          // ★★★★★ THE FIX: Accept two arguments (event, toggled) and use the second one ★★★★★
          onChange: (event, toggled) => {
            game.settings.set("smartphone-widget", "showWidget", toggled);
          },
        };
      }
    }
  });

  // 토큰 업데이트 훅
  Hooks.on("updateToken", (tokenDocument, change, options, userId) => {
    // 1. 내가 실행한 변경이고, 2. 회전 값이 변경되었고, 3. 플래시가 켜져있는 경우에만
    if (
      game.user.id === userId &&
      change.rotation !== undefined &&
      tokenDocument.getFlag("smartphone-widget", "flashlightOn")
    ) {
      // 빛의 회전 값만 토큰의 새로운 회전 값으로 업데이트
      tokenDocument.update({ "light.rotation": change.rotation });
    }
  });

  // --- v12 호환성
  Hooks.on("getItemSheetHeaderButtons", (sheet, buttons) => {
    if (sheet.constructor.name.includes("V2")) return;
    if (!game.user.isGM) {
      return;
    }

    const item = sheet.object;
    const isPhone = !!item.getFlag(SmartphoneWidget.ID, "phoneId");
    const isTemplate = !!item.getFlag(SmartphoneWidget.ID, "isPhoneTemplate");

    let buttonConfig;

    if (item.actor) {
      buttonConfig = {
        label: isPhone
          ? game.i18n.localize("SMARTPHONE.ui.unsetAsPhone")
          : game.i18n.localize("SMARTPHONE.ui.setAsPhone"),
        icon: isPhone ? "fas fa-mobile-slash" : "fas fa-mobile-alt",
        // 클릭 시 DOM 직접 조작 로직은 그대로 유지하여 즉각적인 피드백을 제공합니다.
        onclick: async (ev) => {
          const button = ev.currentTarget;
          const currentIsPhone = !!item.getFlag(SmartphoneWidget.ID, "phoneId");

          if (currentIsPhone) {
            await SmartphoneWidget.unsetDeviceFromItem(item);
          } else {
            await SmartphoneWidget.setDeviceToItem(item);
          }

          const isNowPhone = !!item.getFlag(SmartphoneWidget.ID, "phoneId");
          button.innerHTML = isNowPhone
            ? `<i class="fas fa-mobile-slash"></i> ${game.i18n.localize(
              "SMARTPHONE.ui.unsetAsPhone"
            )}`
            : `<i class="fas fa-mobile-alt"></i> ${game.i18n.localize(
              "SMARTPHONE.ui.setAsPhone"
            )}`;
        },
      };
    } else {
      buttonConfig = {
        label: isTemplate
          ? game.i18n.localize("SMARTPHONE.ui.unsetAsTemplate")
          : game.i18n.localize("SMARTPHONE.ui.setAsTemplate"),
        icon: isTemplate ? "fas fa-clone" : "far fa-clone",
        onclick: async (ev) => {
          const button = ev.currentTarget;
          const currentIsTemplate = !!item.getFlag(
            SmartphoneWidget.ID,
            "isPhoneTemplate"
          );

          const newIsTemplate = !currentIsTemplate;
          await item.setFlag(
            SmartphoneWidget.ID,
            "isPhoneTemplate",
            newIsTemplate
          );

          if (newIsTemplate) {
            button.innerHTML = `<i class="fas fa-clone"></i> ${game.i18n.localize(
              "SMARTPHONE.ui.unsetAsTemplate"
            )}`;
          } else {
            button.innerHTML = `<i class="far fa-clone"></i> ${game.i18n.localize(
              "SMARTPHONE.ui.setAsTemplate"
            )}`;
          }
        },
      };
    }

    buttons.unshift({
      class: "set-as-phone",
      ...buttonConfig,
    });
  });

  // --- v13 호환성
  Hooks.on("getHeaderControlsApplicationV2", (app, buttons) => {
    if (
      !(app.document instanceof foundry.documents.BaseItem) ||
      !game.user.isGM
    ) {
      return;
    }

    const item = app.document;

    // 이 훅은 아이템 디렉토리의 아이템에만 적용되어야 합니다.
    if (item.actor) return;

    const isTemplate = !!item.getFlag(SmartphoneWidget.ID, "isPhoneTemplate");

    const clickHandler = async () => {
      const newState = !isTemplate;
      await item.setFlag(SmartphoneWidget.ID, "isPhoneTemplate", newState);

      // --- [디버깅 A] ---
      // 버튼 클릭 직후, 플래그가 제대로 저장되었는지 확인합니다.
      const savedFlag = item.getFlag(SmartphoneWidget.ID, "isPhoneTemplate");

      app.render(true);
    };

    let newButton;
    if (item.actor) {
        const isPhone = !!item.getFlag(SmartphoneWidget.ID, "phoneId");
        newButton = {
        label: isPhone
          ? game.i18n.localize("SMARTPHONE.ui.unsetAsPhone")
          : game.i18n.localize("SMARTPHONE.ui.setAsPhone"),
        class: "set-as-phone",
        icon: isPhone ? "fas fa-mobile-slash" : "fas fa-mobile-alt",
        onclick: clickHandler, // item-piles가 두 개 다 쓰므로 우리도 똑같이 합니다.
        onClick: clickHandler,
      };
    } else {
      newButton = {
        label: isTemplate
          ? game.i18n.localize("SMARTPHONE.ui.unsetAsTemplate")
          : game.i18n.localize("SMARTPHONE.ui.setAsTemplate"),
        class: "set-as-phone-template",
        icon: isTemplate ? "fas fa-clone" : "far fa-clone",
        onclick: clickHandler,
        onClick: clickHandler,
      };
    }

    buttons.unshift(newButton);
  });

  /**
   * 아이템이 생성될 때: '이동/복사' 또는 '템플릿 개통'을 처리하는 메인 로직.
   */
  Hooks.on("createItem", async (item, options, userId) => {
    // 1. 이 로직은 아이템을 생성한 유저 본인에게만, 그리고 액터가 있는 아이템에만 적용됩니다.
    if (userId !== game.user.id || !item.actor) return;

    const phoneId = item.getFlag(SmartphoneWidget.ID, "phoneId");
    const isTemplate = item.getFlag(SmartphoneWidget.ID, "isPhoneTemplate");

    // --- 시나리오 1: 기존 폰 아이템의 이동 또는 복사 ---
    if (phoneId) {
      // 데이터베이스에서 현재 소유자 정보를 가져옵니다.
      const devices =
        game.settings.get(SmartphoneWidget.ID, "smartphone-devices") || {};
      const deviceData = devices[phoneId];

      // 데이터가 없거나, 소유자가 변경되지 않았다면(예: 게임 로드) 아무것도 하지 않습니다.
      if (!deviceData || deviceData.ownerId === item.actor.id) return;

      // 만약 이 폰이 '고아' 상태였다면, 삭제 타이머를 즉시 취소합니다. (PF2e 호환성)
      if (orphanedPhones.has(phoneId)) {
        clearTimeout(orphanedPhones.get(phoneId).timeout);
        orphanedPhones.delete(phoneId);
      }

      // GM에게 소유권 이전과 이전 아이템 정리를 모두 요청합니다.
      await SmartphoneWidget.SOCKET.executeAsGM(
        "transferPhoneOwnershipAndCleanup",
        {
          phoneId: phoneId,
          newOwnerId: item.actor.id,
          oldOwnerId: deviceData.ownerId, // DB에 저장된 이전 소유자 ID를 전달
        }
      );

      return; // 이동/복사 처리가 완료되었으므로 여기서 종료합니다.
    }

    // --- 시나리오 2: 템플릿 아이템으로 새 폰 개통 (기존 로직 유지) ---
    if (isTemplate) {

      const result = await SmartphoneWidget.SOCKET.executeAsGM(
        "activateNewPhone",
        { itemUuid: item.uuid }
      );

      if (result && result.success && result.device) {
        ui.notifications.info(
          game.i18n.format("SMARTPHONE.notifications.phoneActivationSuccess", {
            deviceName: result.device.name,
            phoneNumber: result.device.phoneNumber,
          })
        );
      } else {
        ui.notifications.error(
          game.i18n.localize("SMARTPHONE.notifications.phoneActivationFailed")
        );
      }
    }
  });

  /**
   * 아이템이 삭제될 때: '진짜 삭제'를 위한 안전장치 역할.
   * 아이템을 즉시 파괴하지 않고, 1초간 '고아' 상태로 만듭니다.
   */
  Hooks.on("deleteItem", async (item, options, userId) => {
    if (userId !== game.user.id || !item.actor) return;

    const phoneId = item.getFlag(SmartphoneWidget.ID, "phoneId");
    if (!phoneId) return;

    // createItem 훅이 이미 이 폰을 '이동'으로 처리했다면, 고아로 만들지 않습니다.
    if (orphanedPhones.has(phoneId)) return;

    const devices =
      game.settings.get(SmartphoneWidget.ID, "smartphone-devices") || {};
    const deviceData = devices[phoneId];

    // 데이터가 없거나, 삭제하는 사람이 소유자가 아니면 무시합니다.
    if (!deviceData || item.actor.id !== deviceData.ownerId) return;

    // ★★★ 핵심: 기기 데이터를 '고아' 상태로 임시 저장하고, 1초 후 삭제 타이머 설정 ★★★
    orphanedPhones.set(phoneId, {
      timeout: setTimeout(() => {
        SmartphoneWidget.SOCKET.executeAsGM("deletePhoneDevice", {
          phoneId: phoneId,
        });
        orphanedPhones.delete(phoneId);
      }, 1000),
    });
  });
}
