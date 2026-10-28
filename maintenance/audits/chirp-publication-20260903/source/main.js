import { ChirpApp } from './apps/ChirpApp.js';
import { registerAllChirpHandlers } from './socket/index.js';
import './apps/chirp/chirp-auth.js';
import './apps/chirp/chirp-compose.js';
import './apps/chirp/chirp-timeline.js';
import './apps/chirp/chirp-detail.js';
import './apps/chirp/chirp-interactions.js';
import './apps/chirp/chirp-profile.js';
import './apps/chirp/chirp-search.js';
import './apps/chirp/chirp-notifications.js';
import './apps/chirp/chirp-dm.js';
import './apps/chirp/chirp-poll.js';
import './apps/chirp/chirp-gm.js';

Hooks.once('setup', () => {
    const api = game.modules.get('smartphone-widget')?.api;

    if (api && typeof api.registerApp === 'function') {
        api.registerApp({
            id: 'chirp',
            name: game.i18n.localize('CHIRP.AppName'),
            icon: 'fa-solid fa-feather',
            color: '#1d9bf0',
            category: 'social',
            appClass: ChirpApp
        });
    }
});

Hooks.once('ready', () => {
    const SmartphoneSocket = game.modules.get('smartphone-widget')?.api?.SmartphoneSocket;

    if (!SmartphoneSocket) {
        ui.notifications.error("Smartphone Chirp App requires the 'Smartphone Widget' module to be active.");
        return;
    }

    const socket = new SmartphoneSocket('smartphone-chirp-app');
    
    registerAllChirpHandlers(socket);
    ChirpApp.initialize(socket);
    
    const module = game.modules.get('smartphone-chirp-app');
    if (module) {
        module.api = { socket: socket };
    }
});
