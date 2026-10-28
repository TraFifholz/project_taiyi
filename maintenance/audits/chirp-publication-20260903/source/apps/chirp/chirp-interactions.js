import { MODULE_ID, L } from './chirp-utils.js';

export function isLiked(app, chirpId) {
  return app.state.posts.get(chirpId)?.likes?.includes(app.state.me) ?? false;
}

export function isRechirped(app, chirpId) {
  return app.state.posts.get(chirpId)?.rechirps?.includes(app.state.me) ?? false;
}

export function isBookmarked(app, chirpId) {
  return app.state.posts.get(chirpId)?.bookmarks?.includes(app.state.me) ?? false;
}

export function optimisticLike(app, chirpId) {
  const chirp = app.state.posts.get(chirpId);
  if (!chirp) return;
  chirp.likes = chirp.likes || [];
  const idx = chirp.likes.indexOf(app.state.me);
  if (idx >= 0) chirp.likes.splice(idx, 1);
  else chirp.likes.push(app.state.me);
}

export function optimisticRechirp(app, chirpId) {
  const chirp = app.state.posts.get(chirpId);
  if (!chirp) return;
  chirp.rechirps = chirp.rechirps || [];
  const idx = chirp.rechirps.indexOf(app.state.me);
  if (idx >= 0) chirp.rechirps.splice(idx, 1);
  else chirp.rechirps.push(app.state.me);
}

export function optimisticBookmark(app, chirpId) {
  const chirp = app.state.posts.get(chirpId);
  if (!chirp) return;
  chirp.bookmarks = chirp.bookmarks || [];
  const idx = chirp.bookmarks.indexOf(app.state.me);
  if (idx >= 0) chirp.bookmarks.splice(idx, 1);
  else chirp.bookmarks.push(app.state.me);
}

export async function handleInteraction(app, action, chirpId) {
  if (!app.state.me) return;
  const phoneId = app.phoneId;
  const socialId = app.state.me;

  if (action === 'like') optimisticLike(app, chirpId);
  else if (action === 'rechirp') optimisticRechirp(app, chirpId);
  else if (action === 'bookmark') {
    optimisticBookmark(app, chirpId);
    const isNowBookmarked = app.state.posts.get(chirpId)?.bookmarks?.includes(socialId);
     app.showToast(isNowBookmarked ? L('addedToBookmarks') : L('removedFromBookmarks'));
  }

  app.render();

  const socketAction = action === 'like' ? 'chirp_like'
    : action === 'rechirp' ? 'chirp_rechirp'
    : 'chirp_bookmark';

  await app.socket.executeAsGM(socketAction, { chirpId, socialId, phoneId });
}
