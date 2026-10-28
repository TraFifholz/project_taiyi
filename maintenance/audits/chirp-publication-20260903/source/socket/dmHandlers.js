import { chirpNow } from '../apps/chirp/chirp-utils.js';

const MODULE_ID = 'smartphone-chirp-app';

export function registerDmHandlers(socket) {
  socket.register('chirp_sendDM', async ({ fromSocialId, toSocialId, text, image }) => {
    if (!game.user.isGM) return { error: 'Permission denied' };
    if (!text && !image) return { error: 'Empty message' };
    const dms = game.settings.get(MODULE_ID, 'chirp-dms') || {};
    const key = [fromSocialId, toSocialId].sort().join('<>');
    if (!dms[key]) dms[key] = [];

    const msg = {
      id: `dm_${foundry.utils.randomID()}`,
      fromSocialId,
      text: text || '',
      image: image || null,
      timestamp: chirpNow(),
    };
    dms[key].push(msg);

    await game.settings.set(MODULE_ID, 'chirp-dms', dms);
    socket.executeForEveryone('updateDMs', { key, messages: dms[key] });
    return { success: true };
  });

  socket.register('chirp_markDMRead', async ({ socialId, otherSocialId }) => {
    if (!game.user.isGM) return { error: 'Permission denied' };
    const readState = game.settings.get(MODULE_ID, 'chirp-dm-read') || {};
    const key = [socialId, otherSocialId].sort().join('<>');
    readState[`${key}::${socialId}`] = chirpNow();
    await game.settings.set(MODULE_ID, 'chirp-dm-read', readState);
    return { success: true };
  });
}
