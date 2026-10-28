/**
 * SCALING NOTE: game.settings stores data as JSON in the world document.
 * This is sufficient for typical TRPG sessions (50-200 chirps).
 * If data grows large (hundreds of posts, many DMs), consider migrating
 * to file-based storage in a future version. Keep chirp objects LEAN.
 */

const MODULE_ID = 'smartphone-chirp-app';

/**
 * Data Schemas (for documentation — not enforced at runtime):
 *
 * Chirp: { id, authorSocialId, content, image, timestamp, likes: [], rechirps: [],
 *   bookmarks: [], replies: [], replyTo, quoteChirpId, poll, pinned, isHidden,
 *   publishTimestamp, fakeLikes: 0, fakeRechirps: 0, fakeBookmarks: 0, fakeReplies: 0 }
 *   NOTE: likes/rechirps/bookmarks are arrays of socialIds.
 *   Display count = array.length + fakeXxx. Do NOT embed account data.
 *
 * Account: { socialId, ownerActorId, handle, name, bio, location, website,
 *   joinedDate, profilePal: [color1, color2], bannerColor, verified,
 *   followers: [], following: [], chirpIds: [] }
 *
 * Notification: { id, type, fromSocialId, targetSocialId, chirpId, timestamp, read }
 *   NOTE: do NOT embed chirp content strings in notifications. Resolve at render time.
 *
 * DM Conversation (value in chirp-dms[handle]): [{ id, fromSocialId, text, timestamp }]
 *
 * Trend: { cat, name, count }  (cat = "Trending in...", count = "12.4K chirps")
 */

export function registerChirpSettings() {
  game.settings.register(MODULE_ID, 'chirp-posts', {
    scope: 'world', type: Object, default: {}, config: false,
  });
  game.settings.register(MODULE_ID, 'chirp-accounts', {
    scope: 'world', type: Object, default: {}, config: false,
  });
  game.settings.register(MODULE_ID, 'chirp-credentials', {
    scope: 'world', type: Object, default: {}, config: false,
  });
  game.settings.register(MODULE_ID, 'chirp-login-states', {
    scope: 'world', type: Object, default: {}, config: false,
  });
  game.settings.register(MODULE_ID, 'chirp-dms', {
    scope: 'world', type: Object, default: {}, config: false,
  });
  game.settings.register(MODULE_ID, 'chirp-trends', {
    scope: 'world', type: Array, default: [], config: false,
  });
  game.settings.register(MODULE_ID, 'chirp-notifications', {
    scope: 'world', type: Object, default: {}, config: false,
  });
  game.settings.register(MODULE_ID, 'chirp-dm-read', {
    scope: 'world', type: Object, default: {}, config: false,
  });
  game.settings.register(MODULE_ID, 'chirp-share-term', {
    scope: 'world', type: String, default: '', config: false,
  });
  game.settings.register(MODULE_ID, 'chirp-logo-icon', {
    scope: 'world', type: String, default: '', config: false,
  });
}
