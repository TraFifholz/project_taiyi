import { pushNotification } from './notifHandlers.js';
import { chirpNow } from '../apps/chirp/chirp-utils.js';

const MODULE_ID = 'smartphone-chirp-app';

async function pushAlertNotifications(socket, accounts, chirp, socialId) {
  for (const targetSocialId of Object.keys(accounts)) {
    await pushNotification(socket, { type: 'alert', fromSocialId: socialId, targetSocialId, chirpId: chirp.id });
  }
}

export function registerPostHandlers(socket) {
  socket.register('chirp_createPost', async ({ chirp, socialId }) => {
    if (!game.user.isGM) return { error: 'Permission denied' };
    const posts = game.settings.get(MODULE_ID, 'chirp-posts') || {};
    const accounts = game.settings.get(MODULE_ID, 'chirp-accounts') || {};

    posts[chirp.id] = chirp;
    if (accounts[socialId]) {
      accounts[socialId].chirpIds = [...(accounts[socialId].chirpIds || []), chirp.id];
    }

    await game.settings.set(MODULE_ID, 'chirp-posts', posts);
    await game.settings.set(MODULE_ID, 'chirp-accounts', accounts);

    socket.executeForEveryone('updateChirp', { chirp });

    if (chirp.isAlert) {
      await pushAlertNotifications(socket, accounts, chirp, socialId);
    }

    if (chirp.replyTo) {
      const parentChirp = posts[chirp.replyTo];
      if (parentChirp && parentChirp.authorSocialId !== socialId) {
        pushNotification(socket, { type: 'reply', fromSocialId: socialId, targetSocialId: parentChirp.authorSocialId, chirpId: chirp.replyTo });
      }
    }

    return { success: true };
  });

  socket.register('chirp_deletePost', async ({ chirpId, socialId }) => {
    if (!game.user.isGM) return { error: 'Permission denied' };
    const posts = game.settings.get(MODULE_ID, 'chirp-posts') || {};
    const accounts = game.settings.get(MODULE_ID, 'chirp-accounts') || {};

    const chirp = posts[chirpId];
    if (!chirp) return { error: 'Post not found' };
    if (chirp.authorSocialId !== socialId && !game.user.isGM) return { error: 'Permission denied' };

    delete posts[chirpId];
    if (accounts[socialId]) {
      accounts[socialId].chirpIds = (accounts[socialId].chirpIds || []).filter(id => id !== chirpId);
    }

    await game.settings.set(MODULE_ID, 'chirp-posts', posts);
    await game.settings.set(MODULE_ID, 'chirp-accounts', accounts);

    socket.executeForEveryone('updateChirp', { chirp: null, chirpId, deleted: true });
    return { success: true };
  });

  socket.register('chirp_editPost', async ({ chirpId, socialId, content, media, isAlert, isGM }) => {
    if (!game.user.isGM) return { error: 'Permission denied' };
    const posts = game.settings.get(MODULE_ID, 'chirp-posts') || {};
    const chirp = posts[chirpId];
    if (!chirp) return { error: 'Post not found' };
    if (chirp.authorSocialId !== socialId && !isGM) return { error: 'Permission denied' };

    const nextContent = (content || '').trim();
    if (!nextContent) return { error: 'Content required' };

    const wasAlert = !!chirp.isAlert;
    chirp.content = nextContent;
    chirp.media = Array.isArray(media)
      ? media.filter(m => m?.src).map(m => ({ src: m.src }))
      : [];
    if (isGM) chirp.isAlert = !!isAlert;
    chirp.editedAt = chirpNow();
    chirp._editedAt = Date.now();

    await game.settings.set(MODULE_ID, 'chirp-posts', posts);
    socket.executeForEveryone('updateChirp', { chirp: posts[chirpId] });
    if (isGM && chirp.isAlert && !wasAlert) {
      const accounts = game.settings.get(MODULE_ID, 'chirp-accounts') || {};
      await pushAlertNotifications(socket, accounts, chirp, socialId);
    }
    return { success: true };
  });

  socket.register('chirp_like', async ({ chirpId, socialId }) => {
    if (!game.user.isGM) return { error: 'Permission denied' };
    const posts = game.settings.get(MODULE_ID, 'chirp-posts') || {};
    const chirp = posts[chirpId];
    if (!chirp) return { error: 'Post not found' };

    chirp.likes = chirp.likes || [];
    const idx = chirp.likes.indexOf(socialId);
    const wasLiked = idx >= 0;
    if (wasLiked) chirp.likes.splice(idx, 1);
    else chirp.likes.push(socialId);

    await game.settings.set(MODULE_ID, 'chirp-posts', posts);
    socket.executeForEveryone('updateChirp', { chirp: posts[chirpId] });
    if (!wasLiked) pushNotification(socket, { type: 'like', fromSocialId: socialId, targetSocialId: chirp.authorSocialId, chirpId });
    return { success: true };
  });

  socket.register('chirp_rechirp', async ({ chirpId, socialId }) => {
    if (!game.user.isGM) return { error: 'Permission denied' };
    const posts = game.settings.get(MODULE_ID, 'chirp-posts') || {};
    const chirp = posts[chirpId];
    if (!chirp) return { error: 'Post not found' };

    chirp.rechirps = chirp.rechirps || [];
    chirp.rechirpTimestamps = chirp.rechirpTimestamps || {};
    chirp._rechirpCreatedAt = chirp._rechirpCreatedAt || {};
    const idx = chirp.rechirps.indexOf(socialId);
    const wasRechirped = idx >= 0;
    if (wasRechirped) {
      chirp.rechirps.splice(idx, 1);
      delete chirp.rechirpTimestamps[socialId];
      delete chirp._rechirpCreatedAt[socialId];
    } else {
      chirp.rechirps.push(socialId);
      chirp.rechirpTimestamps[socialId] = chirpNow();
      chirp._rechirpCreatedAt[socialId] = Date.now();
    }

    await game.settings.set(MODULE_ID, 'chirp-posts', posts);
    socket.executeForEveryone('updateChirp', { chirp: posts[chirpId] });
    if (!wasRechirped) pushNotification(socket, { type: 'rechirp', fromSocialId: socialId, targetSocialId: chirp.authorSocialId, chirpId });
    return { success: true };
  });

  socket.register('chirp_bookmark', async ({ chirpId, socialId }) => {
    if (!game.user.isGM) return { error: 'Permission denied' };
    const posts = game.settings.get(MODULE_ID, 'chirp-posts') || {};
    const chirp = posts[chirpId];
    if (!chirp) return { error: 'Post not found' };

    chirp.bookmarks = chirp.bookmarks || [];
    const idx = chirp.bookmarks.indexOf(socialId);
    if (idx >= 0) chirp.bookmarks.splice(idx, 1);
    else chirp.bookmarks.push(socialId);

    await game.settings.set(MODULE_ID, 'chirp-posts', posts);
    socket.executeForEveryone('updateChirp', { chirp: posts[chirpId] });
    return { success: true };
  });

  socket.register('chirp_addReply', async ({ chirpId, reply, socialId: _socialId }) => {
    if (!game.user.isGM) return { error: 'Permission denied' };
    const posts = game.settings.get(MODULE_ID, 'chirp-posts') || {};
    const chirp = posts[chirpId];
    if (!chirp) return { error: 'Post not found' };

    chirp.replies = chirp.replies || [];
    chirp.replies.push(reply);

    await game.settings.set(MODULE_ID, 'chirp-posts', posts);
    socket.executeForEveryone('updateChirp', { chirp: posts[chirpId] });
    pushNotification(socket, { type: 'reply', fromSocialId: reply.authorSocialId, targetSocialId: chirp.authorSocialId, chirpId });
    return { success: true };
  });

  socket.register('chirp_pinPost', async ({ chirpId, socialId }) => {
    if (!game.user.isGM) return { error: 'Permission denied' };
    const posts = game.settings.get(MODULE_ID, 'chirp-posts') || {};
    const chirp = posts[chirpId];
    if (!chirp) return { error: 'Post not found' };
    if (chirp.authorSocialId !== socialId) return { error: 'Not your post' };
    chirp.pinned = !chirp.pinned;
    await game.settings.set(MODULE_ID, 'chirp-posts', posts);
    socket.executeForEveryone('updateChirp', { chirp: posts[chirpId] });
    return { success: true, pinned: chirp.pinned };
  });

  socket.register('chirp_votePoll', async ({ chirpId, option, socialId }) => {
    if (!game.user.isGM) return { error: 'Permission denied' };
    const posts = game.settings.get(MODULE_ID, 'chirp-posts') || {};
    const chirp = posts[chirpId];
    if (!chirp?.poll) return { error: 'Poll not found' };

    chirp.poll.votes = chirp.poll.votes || {};
    const prevVote = chirp.poll.votes[socialId];
    if (prevVote) {
      const prevOpt = chirp.poll.options.find(o => o.label === prevVote);
      if (prevOpt) prevOpt.votes = Math.max(0, (prevOpt.votes || 0) - 1);
    }
    chirp.poll.votes[socialId] = option;
    const newOpt = chirp.poll.options.find(o => o.label === option);
    if (newOpt) newOpt.votes = (newOpt.votes || 0) + 1;

    await game.settings.set(MODULE_ID, 'chirp-posts', posts);
    socket.executeForEveryone('updateChirp', { chirp: posts[chirpId] });
    return { success: true };
  });
}
