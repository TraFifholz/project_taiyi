import { SmartphoneWidget } from "./SmartphoneWidget.js";
import { SmartphoneTime } from "./SmartphoneTime.js";
import { SocialApp } from "../apps/SocialApp.js";
import { SmartphoneSocket } from "../lib/SmartphoneSocket.js";
import { createBankingApi } from "../api/banking.js";

export function exposeModuleAPI() {
    console.log("Smartphone Widget | Registering API...");
    game.modules.get("smartphone-widget").api = {
        SmartphoneTime: SmartphoneTime,
        SocialApp: SocialApp,
        SmartphoneSocket: SmartphoneSocket,
        registerApp: SmartphoneWidget.registerApp.bind(SmartphoneWidget),
        registerAppTheme: SmartphoneWidget.registerAppTheme.bind(SmartphoneWidget),
        registerWidget: SmartphoneWidget.registerWidget.bind(SmartphoneWidget),
        showBadge: SmartphoneWidget.showBadge.bind(SmartphoneWidget),
        registerBadgeUpdater: SmartphoneWidget.registerBadgeUpdater.bind(SmartphoneWidget),
        updateBadge: SmartphoneWidget.updateBadge.bind(SmartphoneWidget),
        showToastNotification: SmartphoneWidget.showToastNotification.bind(SmartphoneWidget),
        getAllPhones: SmartphoneWidget.getAllPhones.bind(SmartphoneWidget),
        getPhoneForActor: SmartphoneWidget.getPhoneForActor.bind(SmartphoneWidget),
        getCurrentPhone: SmartphoneWidget.getCurrentPhone.bind(SmartphoneWidget),
        sendSystemMessage: SmartphoneWidget.sendSystemMessage.bind(SmartphoneWidget),
        sendMessage: SmartphoneWidget.sendMessage.bind(SmartphoneWidget),
        selectChatRecipient: SmartphoneWidget.selectChatRecipient.bind(SmartphoneWidget),
        banking: createBankingApi(() => SmartphoneWidget.SOCKET)
    };
}
