import { chirpNow } from '../apps/chirp/chirp-utils.js';

const MODULE_ID = 'smartphone-chirp-app';

export async function pushNotification(socket, { type, fromSocialId, targetSocialId, chirpId }) {
  if (fromSocialId === targetSocialId) return;
  const notifications = game.settings.get(MODULE_ID, 'chirp-notifications') || {};
  if (!notifications[targetSocialId]) notifications[targetSocialId] = [];

  notifications[targetSocialId].unshift({
    id: `notif_${foundry.utils.randomID()}`,
    type,
    fromSocialId,
    targetSocialId,
    chirpId: chirpId ?? null,
    read: false,
    timestamp: chirpNow(),
  });

  if (notifications[targetSocialId].length > 50) {
    notifications[targetSocialId] = notifications[targetSocialId].slice(0, 50);
  }
  await game.settings.set(MODULE_ID, 'chirp-notifications', notifications);
  socket.executeForEveryone('updateNotifications', { targetSocialId, notifications: notifications[targetSocialId] });
}

export function registerNotifHandlers(socket) {
  socket.register('chirp_createNotification', async ({ notification }) => {
    if (!game.user.isGM) return { error: 'Permission denied' };
    const notifications = game.settings.get(MODULE_ID, 'chirp-notifications') || {};
    const { targetSocialId } = notification;
    if (!notifications[targetSocialId]) notifications[targetSocialId] = [];
    notifications[targetSocialId].unshift(notification);
    // Keep last 50 per user
    if (notifications[targetSocialId].length > 50) {
      notifications[targetSocialId] = notifications[targetSocialId].slice(0, 50);
    }
    await game.settings.set(MODULE_ID, 'chirp-notifications', notifications);
    socket.executeForEveryone('updateNotifications', { targetSocialId, notifications: notifications[targetSocialId] });
    return { success: true };
  });

  socket.register('chirp_markNotifsRead', async ({ socialId }) => {
    if (!game.user.isGM) return { error: 'Permission denied' };
    const notifications = game.settings.get(MODULE_ID, 'chirp-notifications') || {};
    if (notifications[socialId]) {
      notifications[socialId] = notifications[socialId].map(n => ({ ...n, read: true }));
      await game.settings.set(MODULE_ID, 'chirp-notifications', notifications);
    }
    return { success: true };
  });
}
