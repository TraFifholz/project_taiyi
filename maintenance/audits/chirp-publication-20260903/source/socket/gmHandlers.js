import { chirpNow, formatTimestamp } from '../apps/chirp/chirp-utils.js';

const MODULE_ID = 'smartphone-chirp-app';

export function registerGmHandlers(socket) {
  socket.register('chirp_gmCreateAccount', async ({ handle, name, bio, verified, password, joinedDate }) => {
    if (!game.user.isGM) return { error: 'Permission denied' };
    if (!password) return { error: 'Password required' };
    const accounts = game.settings.get(MODULE_ID, 'chirp-accounts') || {};
    const credentials = game.settings.get(MODULE_ID, 'chirp-credentials') || {};

    const handleTaken = Object.values(accounts).some(a => a.handle === handle);
    if (handleTaken) return { error: 'Handle already taken' };

    const socialId = `chirp_gm_${foundry.utils.randomID()}`;
    accounts[socialId] = {
      socialId,
      ownerActorId: null,
      handle,
      name,
      bio: bio || '',
      location: '',
      website: '',
      joinedDate: joinedDate || formatTimestamp(chirpNow(), 'short'),
      profilePal: ['#7a5cd9', '#150e28'],
      bannerColor: '#7a5cd9',
      verified: !!verified,
      followers: [],
      following: [],
      chirpIds: [],
    };
    credentials[handle] = password;

    await game.settings.set(MODULE_ID, 'chirp-accounts', accounts);
    await game.settings.set(MODULE_ID, 'chirp-credentials', credentials);
    socket.executeForEveryone('updateProfile', { socialId, account: accounts[socialId] });
    return { success: true, socialId };
  });

  socket.register('chirp_gmEditAccount', async ({ socialId, patch, newPassword }) => {
    if (!game.user.isGM) return { error: 'Permission denied' };
    const accounts = game.settings.get(MODULE_ID, 'chirp-accounts') || {};
    if (!accounts[socialId]) return { error: 'Account not found' };

    const credentials = game.settings.get(MODULE_ID, 'chirp-credentials') || {};
    const oldHandle = accounts[socialId].handle;

    if (patch.handle && patch.handle !== oldHandle) {
      const handleTaken = Object.values(accounts).some(a => a.socialId !== socialId && a.handle === patch.handle);
      if (handleTaken) return { error: 'Handle already taken' };
      if (credentials[oldHandle] !== undefined) {
        credentials[patch.handle] = credentials[oldHandle];
        delete credentials[oldHandle];
      }
    }
    if (newPassword) {
      credentials[patch.handle || oldHandle] = newPassword;
    }

    Object.assign(accounts[socialId], patch);
    await game.settings.set(MODULE_ID, 'chirp-accounts', accounts);
    await game.settings.set(MODULE_ID, 'chirp-credentials', credentials);
    socket.executeForEveryone('updateProfile', { socialId, account: accounts[socialId] });
    return { success: true };
  });

  socket.register('chirp_gmDeleteAccount', async ({ socialId }) => {
    if (!game.user.isGM) return { error: 'Permission denied' };
    const accounts = game.settings.get(MODULE_ID, 'chirp-accounts') || {};
    if (!accounts[socialId]) return { error: 'Account not found' };
    delete accounts[socialId];
    const posts = game.settings.get(MODULE_ID, 'chirp-posts') || {};
    Object.keys(posts).forEach(id => {
      if (posts[id].authorSocialId === socialId) delete posts[id];
    });
    await game.settings.set(MODULE_ID, 'chirp-accounts', accounts);
    await game.settings.set(MODULE_ID, 'chirp-posts', posts);
    socket.executeForEveryone('chirp_accountsUpdated', {});
    return { success: true };
  });

  socket.register('chirp_gmSetFakeCounts', async ({ chirpId, fakeLikes, fakeRechirps, fakeBookmarks, fakeReplies }) => {
    if (!game.user.isGM) return { error: 'Permission denied' };
    const posts = game.settings.get(MODULE_ID, 'chirp-posts') || {};
    const chirp = posts[chirpId];
    if (!chirp) return { error: 'Chirp not found' };
    chirp.fakeLikes = fakeLikes || 0;
    chirp.fakeRechirps = fakeRechirps || 0;
    chirp.fakeBookmarks = fakeBookmarks || 0;
    chirp.fakeReplies = fakeReplies || 0;
    await game.settings.set(MODULE_ID, 'chirp-posts', posts);
    socket.executeForEveryone('updateChirp', { chirp: posts[chirpId] });
    return { success: true };
  });

  socket.register('chirp_gmPostAsNPC', async ({ chirp, socialId }) => {
    if (!game.user.isGM) return { error: 'Permission denied' };
    const posts = game.settings.get(MODULE_ID, 'chirp-posts') || {};
    const accounts = game.settings.get(MODULE_ID, 'chirp-accounts') || {};
    posts[chirp.id] = chirp;
    if (accounts[socialId]) accounts[socialId].chirpIds = [...(accounts[socialId].chirpIds || []), chirp.id];
    await game.settings.set(MODULE_ID, 'chirp-posts', posts);
    await game.settings.set(MODULE_ID, 'chirp-accounts', accounts);
    socket.executeForEveryone('updateChirp', { chirp });
    return { success: true };
  });

  socket.register('chirp_gmScheduleChirp', async ({ chirpId, publishTimestamp }) => {
    if (!game.user.isGM) return { error: 'Permission denied' };
    const posts = game.settings.get(MODULE_ID, 'chirp-posts') || {};
    if (!posts[chirpId]) return { error: 'Chirp not found' };
    posts[chirpId].isHidden = true;
    posts[chirpId].publishTimestamp = publishTimestamp;
    await game.settings.set(MODULE_ID, 'chirp-posts', posts);
    return { success: true };
  });

  socket.register('chirp_gmPublishChirp', async ({ chirpId }) => {
    if (!game.user.isGM) return { error: 'Permission denied' };
    const posts = game.settings.get(MODULE_ID, 'chirp-posts') || {};
    if (!posts[chirpId]) return { error: 'Chirp not found' };
    posts[chirpId].isHidden = false;
    await game.settings.set(MODULE_ID, 'chirp-posts', posts);
    socket.executeForEveryone('updateChirp', { chirp: posts[chirpId] });
    return { success: true };
  });

  socket.register('chirp_gmAddTrend', async ({ trend }) => {
    if (!game.user.isGM) return { error: 'Permission denied' };
    const trends = game.settings.get(MODULE_ID, 'chirp-trends') || [];
    trends.push(trend);
    await game.settings.set(MODULE_ID, 'chirp-trends', trends);
    socket.executeForEveryone('updateTrends', { trends });
    return { success: true };
  });

  socket.register('chirp_gmRemoveTrend', async ({ index }) => {
    if (!game.user.isGM) return { error: 'Permission denied' };
    const trends = game.settings.get(MODULE_ID, 'chirp-trends') || [];
    if (index < 0 || index >= trends.length) return { error: 'Invalid index' };
    trends.splice(index, 1);
    await game.settings.set(MODULE_ID, 'chirp-trends', trends);
    socket.executeForEveryone('updateTrends', { trends });
    return { success: true };
  });

  socket.register('chirp_gmSetTrends', async ({ trends }) => {
    if (!game.user.isGM) return { error: 'Permission denied' };
    await game.settings.set(MODULE_ID, 'chirp-trends', trends);
    socket.executeForEveryone('updateTrends', { trends });
    return { success: true };
  });
}
