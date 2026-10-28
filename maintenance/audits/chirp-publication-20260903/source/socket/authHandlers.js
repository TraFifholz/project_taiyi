import { chirpNow, formatTimestamp } from '../apps/chirp/chirp-utils.js';

const MODULE_ID = 'smartphone-chirp-app';

export function registerAuthHandlers(socket) {
  socket.register('chirp_signup', async ({ handle, password, actorId, phoneId }) => {
    if (!game.user.isGM) return { error: 'Permission denied' };

    const accounts = game.settings.get(MODULE_ID, 'chirp-accounts') || {};
    const credentials = game.settings.get(MODULE_ID, 'chirp-credentials') || {};

    const handleTaken = Object.values(accounts).some(a => a.handle === handle);
    if (handleTaken) return { error: 'Handle already taken' };

    const socialId = `chirp_${foundry.utils.randomID()}`;
    const actor = game.actors.get(actorId);

    accounts[socialId] = {
      socialId,
      ownerActorId: actorId || null,
      handle,
      name: actor?.name || handle,
      bio: '',
      location: '',
      website: '',
      joinedDate: formatTimestamp(chirpNow(), 'short'),
      profilePal: ['#3a7bd5', '#0a1828'],
      bannerColor: '#1d9bf0',
      verified: false,
      followers: [],
      following: [],
      chirpIds: [],
    };
    credentials[handle] = password;

    await game.settings.set(MODULE_ID, 'chirp-accounts', accounts);
    await game.settings.set(MODULE_ID, 'chirp-credentials', credentials);

    const loginStates = game.settings.get(MODULE_ID, 'chirp-login-states') || {};
    loginStates[phoneId] = socialId;
    await game.settings.set(MODULE_ID, 'chirp-login-states', loginStates);

    socket.executeForEveryone('chirp_loginStateChanged', { phoneId, socialId });
    return { success: true, socialId, account: accounts[socialId] };
  });

  socket.register('chirp_login', async ({ handle, password, phoneId }) => {
    if (!game.user.isGM) return { error: 'Permission denied' };

    const credentials = game.settings.get(MODULE_ID, 'chirp-credentials') || {};
    const accounts = game.settings.get(MODULE_ID, 'chirp-accounts') || {};

    if (credentials[handle] !== password) return { error: 'Invalid credentials' };

    const account = Object.values(accounts).find(a => a.handle === handle);
    if (!account) return { error: 'Account not found' };

    const loginStates = game.settings.get(MODULE_ID, 'chirp-login-states') || {};
    loginStates[phoneId] = account.socialId;
    await game.settings.set(MODULE_ID, 'chirp-login-states', loginStates);

    socket.executeForEveryone('chirp_loginStateChanged', { phoneId, socialId: account.socialId });
    return { success: true, socialId: account.socialId, account };
  });

  socket.register('chirp_logout', async ({ phoneId }) => {
    if (!game.user.isGM) return { error: 'Permission denied' };

    const loginStates = game.settings.get(MODULE_ID, 'chirp-login-states') || {};
    delete loginStates[phoneId];
    await game.settings.set(MODULE_ID, 'chirp-login-states', loginStates);

    socket.executeForEveryone('chirp_loginStateChanged', { phoneId, socialId: null });
    return { success: true };
  });

  socket.register('chirp_deleteAccount', async ({ socialId, phoneId }) => {
    if (!game.user.isGM) return { error: 'Permission denied' };

    const accounts = game.settings.get(MODULE_ID, 'chirp-accounts') || {};
    const credentials = game.settings.get(MODULE_ID, 'chirp-credentials') || {};

    const account = accounts[socialId];
    if (!account) return { error: 'Account not found' };

    delete credentials[account.handle];
    delete accounts[socialId];

    const posts = game.settings.get(MODULE_ID, 'chirp-posts') || {};
    Object.keys(posts).forEach(id => {
      if (posts[id].authorSocialId === socialId) delete posts[id];
    });

    await game.settings.set(MODULE_ID, 'chirp-accounts', accounts);
    await game.settings.set(MODULE_ID, 'chirp-credentials', credentials);
    await game.settings.set(MODULE_ID, 'chirp-posts', posts);

    if (phoneId) {
      const loginStates = game.settings.get(MODULE_ID, 'chirp-login-states') || {};
      delete loginStates[phoneId];
      await game.settings.set(MODULE_ID, 'chirp-login-states', loginStates);
    }

    socket.executeForEveryone('chirp_loginStateChanged', { phoneId, socialId: null });
    socket.executeForEveryone('chirp_accountsUpdated', {});
    return { success: true };
  });

  socket.register('chirp_updateLoginState', async ({ phoneId, socialId }) => {
    if (!game.user.isGM) return { error: 'Permission denied' };

    const loginStates = game.settings.get(MODULE_ID, 'chirp-login-states') || {};
    if (socialId === null) {
      delete loginStates[phoneId];
    } else {
      loginStates[phoneId] = socialId;
    }
    await game.settings.set(MODULE_ID, 'chirp-login-states', loginStates);

    socket.executeForEveryone('chirp_loginStateChanged', { phoneId, socialId });
    return { success: true };
  });

  socket.register('chirp_loginStateChanged', ({ phoneId, socialId }) => {
  });
}
