import { pushNotification } from './notifHandlers.js';

const MODULE_ID = 'smartphone-chirp-app';

export function registerProfileHandlers(socket) {
  socket.register('chirp_toggleFollow', async ({ fromSocialId, toSocialId }) => {
    if (!game.user.isGM) return { error: 'Permission denied' };
    const accounts = game.settings.get(MODULE_ID, 'chirp-accounts') || {};
    const fromAcc = accounts[fromSocialId];
    const toAcc = accounts[toSocialId];
    if (!fromAcc || !toAcc) return { error: 'Account not found' };

    fromAcc.following = fromAcc.following || [];
    toAcc.followers = toAcc.followers || [];

    const isFollowing = fromAcc.following.includes(toSocialId);
    if (isFollowing) {
      fromAcc.following = fromAcc.following.filter(id => id !== toSocialId);
      toAcc.followers = toAcc.followers.filter(id => id !== fromSocialId);
    } else {
      fromAcc.following.push(toSocialId);
      toAcc.followers.push(fromSocialId);
    }

    await game.settings.set(MODULE_ID, 'chirp-accounts', accounts);
    socket.executeForEveryone('updateProfile', { socialId: fromSocialId, account: fromAcc });
    socket.executeForEveryone('updateProfile', { socialId: toSocialId, account: toAcc });
    if (!isFollowing) pushNotification(socket, { type: 'follow', fromSocialId, targetSocialId: toSocialId });
    return { success: true, nowFollowing: !isFollowing };
  });

  socket.register('chirp_muteUser', async ({ fromSocialId, targetSocialId }) => {
    if (!game.user.isGM) return { error: 'Permission denied' };
    const accounts = game.settings.get(MODULE_ID, 'chirp-accounts') || {};
    const acc = accounts[fromSocialId];
    if (!acc) return { error: 'Account not found' };
    acc.muted = acc.muted || [];
    const idx = acc.muted.indexOf(targetSocialId);
    if (idx >= 0) acc.muted.splice(idx, 1);
    else acc.muted.push(targetSocialId);
    await game.settings.set(MODULE_ID, 'chirp-accounts', accounts);
    socket.executeForEveryone('updateProfile', { socialId: fromSocialId, account: accounts[fromSocialId] });
    return { success: true, muted: idx < 0 };
  });

  socket.register('chirp_blockUser', async ({ fromSocialId, targetSocialId }) => {
    if (!game.user.isGM) return { error: 'Permission denied' };
    const accounts = game.settings.get(MODULE_ID, 'chirp-accounts') || {};
    const fromAcc = accounts[fromSocialId];
    const toAcc = accounts[targetSocialId];
    if (!fromAcc) return { error: 'Account not found' };
    fromAcc.blocked = fromAcc.blocked || [];
    const idx = fromAcc.blocked.indexOf(targetSocialId);
    if (idx >= 0) {
      fromAcc.blocked.splice(idx, 1);
    } else {
      fromAcc.blocked.push(targetSocialId);
      fromAcc.following = (fromAcc.following || []).filter(id => id !== targetSocialId);
      if (toAcc) {
        toAcc.followers = (toAcc.followers || []).filter(id => id !== fromSocialId);
        toAcc.following = (toAcc.following || []).filter(id => id !== fromSocialId);
        fromAcc.followers = (fromAcc.followers || []).filter(id => id !== targetSocialId);
      }
    }
    await game.settings.set(MODULE_ID, 'chirp-accounts', accounts);
    socket.executeForEveryone('chirp_accountsUpdated');
    return { success: true, blocked: idx < 0 };
  });

  socket.register('chirp_muteConvo', async ({ socialId, chirpId }) => {
    if (!game.user.isGM) return { error: 'Permission denied' };
    const accounts = game.settings.get(MODULE_ID, 'chirp-accounts') || {};
    const acc = accounts[socialId];
    if (!acc) return { error: 'Account not found' };
    acc.mutedConvos = acc.mutedConvos || [];
    const idx = acc.mutedConvos.indexOf(chirpId);
    if (idx >= 0) acc.mutedConvos.splice(idx, 1);
    else acc.mutedConvos.push(chirpId);
    await game.settings.set(MODULE_ID, 'chirp-accounts', accounts);
    socket.executeForEveryone('updateProfile', { socialId, account: accounts[socialId] });
    return { success: true, muted: idx < 0 };
  });

  socket.register('chirp_updateProfile', async ({ socialId, patch }) => {
    if (!game.user.isGM) return { error: 'Permission denied' };
    const accounts = game.settings.get(MODULE_ID, 'chirp-accounts') || {};
    if (!accounts[socialId]) return { error: 'Account not found' };

    Object.assign(accounts[socialId], patch);
    await game.settings.set(MODULE_ID, 'chirp-accounts', accounts);

    socket.executeForEveryone('updateProfile', { socialId, account: accounts[socialId] });
    return { success: true };
  });
}
