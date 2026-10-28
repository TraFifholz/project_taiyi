const appId = "smartphone-browser-app";

import { BrowserApp } from "./classes/BrowserApp.js";

let smartphoneAPI;

Hooks.once('setup', () => {

    game.settings.register(appId, "journalName", {
        name: "Journal Name",
        hint: "What should the name of the Journal that keeps your WWW be called?",
        scope: "world",
        config: true,
        type: String,
        default: "browserapp",
        requiresReload: true
    });

    game.settings.register(appId, "theme", {
        name: "Display Theme",
        hint: "What theme should pages be displayed in?",
        scope: "world",
        config: true,
        type: String,
        choices: {
            "cyberpunk": "Cyberpunk",
            "neon": "Neon",
            "retrowave": "Retrowave",
            "modern-dark": "Modern: Dark",
            "modern-light": "Modern: Light",
            "vampire": "Vampire"
        },
        default: "cyberpunk"
    });

    game.settings.register(appId, "useSignalSystem", {
        name: "Use Signal System",
        hint: "Use Smartphone Signal when accessing the browser.",
        scope: "world",
        config: true, 
        type: Boolean,
        default :true
    });

    smartphoneAPI = game.modules.get('smartphone-widget')?.api;
    if (!smartphoneAPI) {
        ui.notifications.error("BrowserApp requires the 'Smartphone Widget' module to be active.");
        return;
    }

    smartphoneAPI.registerApp({
        id: 'browserapp',
        name: "Browser",
        icon: 'fas fa-globe',
        color: 'rgb(114, 30, 250)',
        category: 'utility',
        appClass: BrowserApp
    });
});

Hooks.once('ready', () => {
    const SmartphoneSocket = game.modules.get('smartphone-widget')?.api?.SmartphoneSocket;

    if (!SmartphoneSocket) {
        console.error("Browser Addon | Smartphone Widget Core module is missing or API is not ready.");
        return;
    }

    const socket = new SmartphoneSocket(appId);
    BrowserApp.initialize(socket);
});