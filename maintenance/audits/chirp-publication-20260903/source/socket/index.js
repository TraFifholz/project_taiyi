// =======================================================================
// Socket Handler Index — smartphone-chirp-app
// =======================================================================
// Central hub that imports all domain handler registration functions
// and exposes a single registerAllChirpHandlers(socket) entry point.
// smartphone-chirp-app's main.js calls only this function.
// =======================================================================

import { registerAuthHandlers } from './authHandlers.js';
import { registerPostHandlers } from './postHandlers.js';
import { registerProfileHandlers } from './profileHandlers.js';
import { registerDmHandlers } from './dmHandlers.js';
import { registerNotifHandlers } from './notifHandlers.js';
import { registerGmHandlers } from './gmHandlers.js';

export function registerAllChirpHandlers(socket) {
  registerAuthHandlers(socket);
  registerPostHandlers(socket);
  registerProfileHandlers(socket);
  registerDmHandlers(socket);
  registerNotifHandlers(socket);
  registerGmHandlers(socket);
}
