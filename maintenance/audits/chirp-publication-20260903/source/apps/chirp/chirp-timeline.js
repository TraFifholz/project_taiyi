import { renderIcon, renderAvatar, renderByline, renderActionBar, renderMediaGrid, renderQuoteCard, renderPollDisplay, renderAlertLabel, computeReplyCounts, sortFeedItems } from './chirp-shared.js';
import { renderContent, L } from './chirp-utils.js';
import { handleInteraction } from './chirp-interactions.js';

const PAGE_SIZE = 20;

export function renderTimelineView(app) {
  const { posts, accounts, following, me, postState } = app.state;
  const tab = app.viewParams.tab || 'forYou';
  const displayCount = app.viewParams._displayCount || PAGE_SIZE;

  const allPosts = Array.from(posts.values());
  const feedItems = [];

  for (const p of allPosts) {
    if (p.replyTo) continue;
    feedItems.push({ post: p, rechirpedBy: null });
  }

  for (const p of allPosts) {
    if (p.replyTo || !p.rechirps?.length) continue;
    for (const rid of p.rechirps) {
      if (rid === p.authorSocialId) continue;
      feedItems.push({ post: p, rechirpedBy: rid });
    }
  }

  const myAccount = accounts.get(me);
  const mutedUsers = myAccount?.muted || [];
  const blockedUsers = myAccount?.blocked || [];
  const mutedConvos = myAccount?.mutedConvos || [];

  const filtered = feedItems.filter(item => {
    if (mutedUsers.includes(item.post.authorSocialId) || blockedUsers.includes(item.post.authorSocialId)) return false;
    if (mutedConvos.includes(item.post.id)) return false;
    if (item.rechirpedBy && (mutedUsers.includes(item.rechirpedBy) || blockedUsers.includes(item.rechirpedBy))) return false;
    return true;
  });

  sortFeedItems(filtered);

  const seen = new Set();
  const deduped = filtered.filter(item => {
    const key = item.rechirpedBy ? `rt_${item.rechirpedBy}_${item.post.id}` : item.post.id;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });

  const visible = tab === 'following'
    ? deduped.filter(item => {
        const authorMatch = following.includes(item.post.authorSocialId) || item.post.authorSocialId === me;
        const rtMatch = item.rechirpedBy && (following.includes(item.rechirpedBy) || item.rechirpedBy === me);
        return authorMatch || rtMatch;
      })
    : deduped;

  const page = visible.slice(0, displayCount);
  const hasMore = visible.length > displayCount;

  const replyCounts = computeReplyCounts(posts);

  const postsHtml = page.length === 0
    ? `<div class="chirp-empty">${L('timelineEmpty')}</div>`
    : page.map((item, i) => renderPostCard(item.post, accounts, me, i === 0, null, item.rechirpedBy, replyCounts, posts)).join('');

  return `
    <div class="chirp-tabs">
      <button class="chirp-tab ${tab === 'forYou' ? 'active' : ''}" data-tab="forYou">${L('forYou')}</button>
      <button class="chirp-tab ${tab === 'following' ? 'active' : ''}" data-tab="following">${L('following')}</button>
    </div>
    <div id="chirp-posts-list">${postsHtml}</div>
    ${hasMore ? '<div class="chirp-load-more" id="chirp-sentinel"></div>' : ''}`;
}

export function renderPostCard(post, accounts, mySocialId, isFirst = false, unused = null, rechirpedBy = null, replyCounts = {}, posts = null) {
  const author = accounts.get(post.authorSocialId);
  if (!author) return '';

  const rechirpHeader = rechirpedBy
    ? `<div class="chirp-rechirp-header">${renderIcon('rechirp')}<span>${L('rechirped', {name: accounts.get(rechirpedBy)?.name || rechirpedBy})}</span></div>`
    : '';
  const pinnedHeader = post.pinned && !post.rechirpedBy
    ? `<div class="chirp-rechirp-header">${renderIcon('pin', '', 'width:11px;height:11px')}<span>${L('pinned')}</span></div>`
    : '';

  return `
${rechirpHeader}${pinnedHeader}
<div class="chirp-post${isFirst ? ' first' : ''}${post.isAlert ? ' alert' : ''}" data-chirp-id="${post.id}"${rechirpedBy ? ' data-rechirped="true"' : ''}>
  <div class="avatar-col" data-action="open-profile" data-handle="${author.handle}">
    ${renderAvatar(author)}
  </div>
  <div class="body-col">
    ${post.isAlert ? renderAlertLabel() : ''}
    ${renderByline(author, post.timestamp, true)}
    ${post.prefix ? `<div class="content">${renderContent(post.prefix)}</div>` : ''}
    ${post.content ? `<div class="content">${renderContent(post.content)}</div>` : ''}
    ${post.editedAt ? `<div class="chirp-edited">${L('edited')}</div>` : ''}
    ${post.media?.length ? renderMediaGrid(post.media) : ''}
    ${post.quoteChirpId ? renderQuoteCard(post.quoteChirpId, posts, accounts) : ''}
    ${post.poll ? renderPollDisplay(post.poll, mySocialId, post.id) : ''}
    ${renderActionBar(post, mySocialId, post.id, replyCounts[post.id] || 0)}
  </div>
</div>`;
}

export function attachTimelineListeners(app, container) {
  const VIEWS = app.constructor.VIEWS;

  container.querySelectorAll('.chirp-tab[data-tab]').forEach(btn => {
    btn.addEventListener('click', () => {
      app.switchView(VIEWS.TIMELINE, { tab: btn.dataset.tab });
    });
  });

  container.querySelectorAll('[data-action="open-profile"]').forEach(el => {
    el.addEventListener('click', (e) => {
      e.stopPropagation();
      app.switchView(VIEWS.PROFILE, { handle: el.dataset.handle });
    });
  });

  container.querySelectorAll('.chirp-post[data-chirp-id]').forEach(card => {
    card.addEventListener('click', () => {
      app.switchView(VIEWS.DETAIL, { chirpId: card.dataset.chirpId });
    });
  });

  container.querySelectorAll('[data-action][data-chirp-id]').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const { action, chirpId } = btn.dataset;
      if (!app.state.me) return;

      if (action === 'reply') {
        app.switchView(VIEWS.DETAIL, { chirpId });
        return;
      }
      if (action === 'share') { app.showToast(L('linkCopied')); return; }

      if (action === 'rechirp') {
        showRechirpMenu(app, btn, chirpId);
        return;
      }

      await handleInteraction(app, action, chirpId);
    });
  });

  container.querySelectorAll('[data-action="more"]').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const postEl = btn.closest('.chirp-post[data-chirp-id]');
      if (!postEl) return;
      showMoreMenu(app, btn, postEl.dataset.chirpId, postEl.dataset.rechirped === 'true');
    });
  });

  container.querySelectorAll('.quote[data-chirp-id]').forEach(q => {
    q.addEventListener('click', (e) => {
      e.stopPropagation();
      app.switchView(VIEWS.DETAIL, { chirpId: q.dataset.chirpId });
    });
  });

  container.querySelectorAll('[data-poll-option]').forEach(opt => {
    opt.addEventListener('click', async (e) => {
      e.stopPropagation();
      const { chirpId, pollOption } = opt.dataset;
      await app.socket.executeAsGM('chirp_votePoll', { chirpId, option: pollOption, socialId: app.state.me });
    });
  });

  const sentinel = container.querySelector('#chirp-sentinel');
  if (sentinel) {
    const scrollArea = app.widget?.element?.querySelector('.chirp-main');
    if (scrollArea) {
      const observer = new IntersectionObserver((entries) => {
        if (entries[0].isIntersecting) {
          observer.disconnect();
          app.viewParams._displayCount = (app.viewParams._displayCount || PAGE_SIZE) + PAGE_SIZE;
          app.render();
        }
      }, { root: scrollArea, threshold: 0 });
      observer.observe(sentinel);
    }
  }
}

export function showMoreMenu(app, anchorBtn, chirpId, isRechirpContext = false) {
  const existing = app.widget?.element?.querySelector('.chirp-more-menu');
  if (existing) { existing.remove(); return; }

  const post = app.state.posts.get(chirpId);
  if (!post) return;
  const me = app.state.me;
  const myAccount = app.state.accounts.get(me);
  const isOwn = post.authorSocialId === me;
  const isGM = game.user.isGM;
  const author = app.state.accounts.get(post.authorSocialId);
  const handle = author?.handle || post.authorSocialId;

  const items = [];

  if ((isOwn || isGM) && !isRechirpContext) {
    items.push({ label: L('editPost'), icon: 'feather', action: 'edit' });
  }

  if (isOwn && !isRechirpContext) {
    items.push({ label: post.pinned ? L('unpinFromProfile') : L('pinToProfile'), icon: 'pin', action: 'pin' });
    items.push({ label: L('delete'), icon: 'close', action: 'delete', danger: true });
  } else {
    const isFollowing = app.state.following?.includes(post.authorSocialId);
    items.push({ label: isFollowing ? L('unfollowUser', {handle}) : L('followUser', {handle}), icon: 'user', action: 'follow' });

    const isMuted = myAccount?.muted?.includes(post.authorSocialId);
    items.push({ label: isMuted ? L('unmuteUser', {handle}) : L('muteUser', {handle}), icon: 'bell', action: 'mute' });

    const isBlocked = myAccount?.blocked?.includes(post.authorSocialId);
    items.push({ label: isBlocked ? L('unblockUser', {handle}) : L('blockUser', {handle}), icon: 'close', action: 'block' });

    const isConvoMuted = myAccount?.mutedConvos?.includes(chirpId);
    items.push({ label: isConvoMuted ? L('unmuteConvo') : L('muteConvo'), icon: 'bell', action: 'muteConvo' });

    if (isGM) {
      items.push({ label: L('editFakeCounts'), icon: 'gear', action: 'fakecounts' });
      items.push({ label: L('delete'), icon: 'close', action: 'delete', danger: true });
    }
  }

  if (isOwn && isGM) {
    items.push({ label: L('editFakeCounts'), icon: 'gear', action: 'fakecounts' });
  }

  const menu = document.createElement('div');
  menu.className = 'chirp-more-menu';
  menu.innerHTML = items.map(it =>
    `<button class="more-opt${it.danger ? ' danger' : ''}" data-more-action="${it.action}">${renderIcon(it.icon,'','width:15px;height:15px')} ${it.label}</button>`
  ).join('');

  const byline = anchorBtn.closest('.byline') || anchorBtn.closest('.byline-big');
  if (byline) { byline.style.position = 'relative'; byline.appendChild(menu); }
  else { anchorBtn.parentElement.style.position = 'relative'; anchorBtn.parentElement.appendChild(menu); }

  menu.querySelectorAll('[data-more-action]').forEach(opt => {
    opt.addEventListener('click', async (e) => {
      e.stopPropagation();
      menu.remove();
      const act = opt.dataset.moreAction;
      await executeMoreAction(app, act, chirpId, post);
    });
  });

  setTimeout(() => {
    const dismiss = (e) => {
      if (menu.contains(e.target)) return;
      if (anchorBtn.contains(e.target)) return;
      menu.remove();
      document.removeEventListener('click', dismiss, true);
    };
    document.addEventListener('click', dismiss, true);
  }, 0);
}

async function executeMoreAction(app, action, chirpId, post) {
  const me = app.state.me;
  const socket = app.socket;

  switch (action) {
    case 'pin':
      await socket.executeAsGM('chirp_pinPost', { chirpId, socialId: me });
      break;
    case 'delete':
      await socket.executeAsGM('chirp_deletePost', { chirpId, socialId: me });
      break;
    case 'edit':
      app.switchView(app.constructor.VIEWS.COMPOSE, {
        editChirpId: chirpId,
        editReturnView: app.currentView,
        editReturnParams: { ...app.viewParams },
      });
      return;
    case 'follow':
      await socket.executeAsGM('chirp_toggleFollow', { fromSocialId: me, toSocialId: post.authorSocialId });
      break;
    case 'mute':
      await socket.executeAsGM('chirp_muteUser', { fromSocialId: me, targetSocialId: post.authorSocialId });
      break;
    case 'block':
      await socket.executeAsGM('chirp_blockUser', { fromSocialId: me, targetSocialId: post.authorSocialId });
      break;
    case 'muteConvo':
      await socket.executeAsGM('chirp_muteConvo', { socialId: me, chirpId });
      break;
    case 'fakecounts':
      showFakeCountsEditor(app, chirpId, post);
      return;
  }

  await app.loadPosts();
  await app.loadAccounts();
  app.render();
}

function showFakeCountsEditor(app, chirpId, post) {
  const existing = app.widget?.element?.querySelector('.fake-counts-overlay');
  if (existing) existing.remove();

  const overlay = document.createElement('div');
  overlay.className = 'fake-counts-overlay';
  overlay.innerHTML = `
    <div class="fake-counts-editor">
      <div class="fake-editor-title">${L('editFakeCounts')}</div>
      <div class="fake-counts-grid">
        <div class="fake-field"><label>${L('fakeLikes')}</label><input type="number" data-fc="likes" min="0" value="${post.fakeLikes || 0}" /></div>
        <div class="fake-field"><label>${L('fakeRechirps')}</label><input type="number" data-fc="rechirps" min="0" value="${post.fakeRechirps || 0}" /></div>
        <div class="fake-field"><label>${L('fakeBookmarks')}</label><input type="number" data-fc="bookmarks" min="0" value="${post.fakeBookmarks || 0}" /></div>
        <div class="fake-field"><label>${L('fakeReplies')}</label><input type="number" data-fc="replies" min="0" value="${post.fakeReplies || 0}" /></div>
      </div>
      <div class="fake-editor-btns">
        <button class="gm-btn" data-fc-action="cancel">${L('cancel')}</button>
        <button class="gm-btn primary" data-fc-action="apply">${L('applyCounts')}</button>
      </div>
    </div>`;

  const appEl = app.widget?.element?.querySelector('.chirp-app') || app.widget?.element;
  appEl?.appendChild(overlay);

  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) overlay.remove();
  });

  overlay.querySelector('[data-fc-action="cancel"]').addEventListener('click', () => overlay.remove());

  overlay.querySelector('[data-fc-action="apply"]').addEventListener('click', async () => {
    const fakeLikes = parseInt(overlay.querySelector('[data-fc="likes"]').value) || 0;
    const fakeRechirps = parseInt(overlay.querySelector('[data-fc="rechirps"]').value) || 0;
    const fakeBookmarks = parseInt(overlay.querySelector('[data-fc="bookmarks"]').value) || 0;
    const fakeReplies = parseInt(overlay.querySelector('[data-fc="replies"]').value) || 0;
    const result = await app.socket.executeAsGM('chirp_gmSetFakeCounts', { chirpId, fakeLikes, fakeRechirps, fakeBookmarks, fakeReplies });
    overlay.remove();
    if (result?.success) {
      await app.loadPosts();
      app.showToast(L('fakeCountsApplied'));
      app.render();
    }
  });
}

function showRechirpMenu(app, anchorBtn, chirpId) {
  const VIEWS = app.constructor.VIEWS;
  const existing = app.widget?.element?.querySelector('.chirp-rt-menu');
  if (existing) { existing.remove(); return; }

  const post = app.state.posts.get(chirpId);
  const isRechirped = post?.rechirps?.includes(app.state.me);

  const menu = document.createElement('div');
  menu.className = 'chirp-rt-menu';

  if (isRechirped) {
    menu.innerHTML = `
      <button class="rt-opt" data-rt-action="undo">${renderIcon('rechirp','','width:16px;height:16px')} ${L('undoRechirp')}</button>
      <button class="rt-opt" data-rt-action="quote">${renderIcon('feather','','width:16px;height:16px')} ${L('quote')}</button>`;
  } else {
    menu.innerHTML = `
      <button class="rt-opt" data-rt-action="rechirp">${renderIcon('rechirp','','width:16px;height:16px')} ${L('rechirp')}</button>
      <button class="rt-opt" data-rt-action="quote">${renderIcon('feather','','width:16px;height:16px')} ${L('quote')}</button>`;
  }

  anchorBtn.closest('.chirp-actions')?.appendChild(menu);

  menu.querySelector('[data-rt-action="rechirp"]')?.addEventListener('click', async (e) => {
    e.stopPropagation();
    menu.remove();
    await handleInteraction(app, 'rechirp', chirpId);
  });
  menu.querySelector('[data-rt-action="undo"]')?.addEventListener('click', async (e) => {
    e.stopPropagation();
    menu.remove();
    await handleInteraction(app, 'rechirp', chirpId);
  });
  menu.querySelector('[data-rt-action="quote"]')?.addEventListener('click', (e) => {
    e.stopPropagation();
    menu.remove();
    app.switchView(VIEWS.COMPOSE, { quoteChirpId: chirpId });
  });

  setTimeout(() => {
    const dismiss = (e) => {
      if (!menu.contains(e.target)) { menu.remove(); document.removeEventListener('click', dismiss, true); }
    };
    document.addEventListener('click', dismiss, true);
  }, 0);
}
