import { renderIcon, renderAvatar, renderByline, renderMediaGrid, renderQuoteCard, renderPollDisplay, renderActionBar, renderAlertLabel, computeReplyCounts } from './chirp-shared.js';
import { renderContent, formatCount, chirpNow, formatTimestamp, formatTime, L } from './chirp-utils.js';
import { handleInteraction } from './chirp-interactions.js';
import { showMoreMenu } from './chirp-timeline.js';

export function renderDetailView(app) {
  const chirpId = app.viewParams.chirpId;
  const { posts, accounts, me } = app.state;
  const post = posts.get(chirpId);
  if (!post) {
    return `<div class="chirp-app"><div class="chirp-empty">${L('chirpNotFound')}</div></div>`;
  }

  const author = accounts.get(post.authorSocialId);
  if (!author) return `<div class="chirp-app"><div class="chirp-empty">${L('authorNotFound')}</div></div>`;

  const stamp = `${formatTime(post.timestamp)} · ${formatTimestamp(post.timestamp, 'full')}`;
  const replyCounts = computeReplyCounts(posts);

  const likeCount = (post.likes?.length || 0) + (post.fakeLikes || 0);
  const rechirpCount = (post.rechirps?.length || 0) + (post.fakeRechirps || 0);
  const bookmarkCount = (post.bookmarks?.length || 0) + (post.fakeBookmarks || 0);
  const replyCount = (replyCounts[chirpId] || 0) + (post.fakeReplies || 0);
  const isLiked = post.likes?.includes(me);
  const isRechirped = post.rechirps?.includes(me);
  const isBookmarked = post.bookmarks?.includes(me);

  const myAccount = accounts.get(me);

  const replyPosts = Array.from(posts.values())
    .filter(p => p.replyTo === chirpId)
    .sort((a, b) => a.timestamp - b.timestamp);

  const repliesHtml = replyPosts.map(r => {
    const rAuthor = accounts.get(r.authorSocialId);
    if (!rAuthor) return '';
    return `
<div class="chirp-post${r.isAlert ? ' alert' : ''}" data-chirp-id="${r.id}" data-reply>
  <div class="avatar-col" data-action="open-profile" data-handle="${rAuthor.socialId}">${renderAvatar(rAuthor)}</div>
  <div class="body-col">
    ${r.isAlert ? renderAlertLabel() : ''}
    ${renderByline(rAuthor, r.timestamp, true)}
    <div class="content">${renderContent(r.content)}</div>
    ${r.editedAt ? `<div class="chirp-edited">${L('edited')}</div>` : ''}
    ${r.media?.length ? renderMediaGrid(r.media) : ''}
    ${renderActionBar(r, app.state.me, r.id, replyCounts[r.id] || 0)}
  </div>
</div>`;
  }).join('');

  const ancestors = [];
  let walkId = post.replyTo;
  while (walkId) {
    const ancestor = posts.get(walkId);
    if (!ancestor) break;
    ancestors.unshift(ancestor);
    walkId = ancestor.replyTo;
  }


  const parentHtml = ancestors.map(a => {
    const aAuthor = accounts.get(a.authorSocialId);
    if (!aAuthor) return '';
    return `
<div class="chirp-post reply-parent${a.isAlert ? ' alert' : ''}" data-chirp-id="${a.id}">
  <div class="avatar-col">
    ${renderAvatar(aAuthor)}
    <div class="thread-line"></div>
  </div>
  <div class="body-col">
    ${a.isAlert ? renderAlertLabel() : ''}
    ${renderByline(aAuthor, a.timestamp)}
    ${a.content ? `<div class="content">${renderContent(a.content)}</div>` : ''}
    ${a.editedAt ? `<div class="chirp-edited">${L('edited')}</div>` : ''}
    ${a.media?.length ? renderMediaGrid(a.media) : ''}
  </div>
</div>`;
  }).join('');

  return `
<div class="chirp-app chirp-detail">
  <div class="detail-header">
    <button class="back" id="detail-back" aria-label="back">${renderIcon('back')}</button>
    <div class="title">${L('chirp')}</div>
  </div>
  <div class="chirp-main">
    ${parentHtml}
    <div class="main-post${post.isAlert ? ' alert' : ''}">
      <div class="byline-big">
        <div class="author-avatar" data-action="open-profile" data-handle="${author.socialId}" style="cursor:pointer">
          ${renderAvatar(author, 'md')}
        </div>
        <div class="name-block">
          <div class="display-name">
            ${author.name}
            ${author.verified ? renderIcon('verified', 'verified', 'width:13px;height:13px') : ''}
          </div>
          <div class="handle">@${author.handle}</div>
        </div>
        <button class="more-btn" aria-label="more">${renderIcon('more', '', 'width:16px;height:16px')}</button>
      </div>
      ${post.isAlert ? renderAlertLabel() : ''}
      ${post.replyTo ? `<div class="reply-context">${L('replyingTo')} <span class="mention">@${accounts.get(posts.get(post.replyTo)?.authorSocialId)?.handle || '...'}</span></div>` : ''}
      ${post.prefix ? `<div class="content">${renderContent(post.prefix)}</div>` : ''}
      ${post.content ? `<div class="content">${renderContent(post.content)}</div>` : ''}
      ${post.editedAt ? `<div class="chirp-edited">${L('edited')}</div>` : ''}
      ${post.media?.length ? renderMediaGrid(post.media) : ''}
      ${post.quoteChirpId ? renderQuoteCard(post.quoteChirpId, posts, accounts) : ''}
      ${post.poll ? renderPollDisplay(post.poll, me, chirpId) : ''}
      <div class="stamp">${stamp}</div>
      <div class="stats-row">
        <div class="stat"><strong>${formatCount(replyCount)}</strong> <span>${L('replies')}</span></div>
        <div class="stat"><strong>${formatCount(rechirpCount)}</strong> <span>Rechirps</span></div>
        <div class="stat"><strong>${formatCount(likeCount)}</strong> <span>${L('likes')}</span></div>
        <div class="stat"><strong>${formatCount(bookmarkCount)}</strong> <span>${L('bookmarks')}</span></div>
      </div>
      <div class="big-actions">
        <button data-action="reply" data-chirp-id="${chirpId}">${renderIcon('reply')}</button>
        <button class="rt-btn${isRechirped ? ' active' : ''}" data-action="rechirp" data-chirp-id="${chirpId}">${renderIcon('rechirp')}</button>
        <button class="like-btn${isLiked ? ' active' : ''}" data-action="like" data-chirp-id="${chirpId}">${renderIcon('heart')}</button>
        <button class="bookmark-btn${isBookmarked ? ' active' : ''}" data-action="bookmark" data-chirp-id="${chirpId}">${renderIcon('bookmark')}</button>
        <button data-action="share" data-chirp-id="${chirpId}">${renderIcon('share')}</button>
      </div>
    </div>
    <div class="reply-composer">
      ${renderAvatar(myAccount, 'sm')}
      <input type="text" id="reply-input" placeholder="${L('chirpYourReply')}" />
      <button class="send" id="reply-send" disabled>${renderIcon('sendArrow', '', 'width:14px;height:14px')}</button>
    </div>
    <div id="reply-thread">
      ${repliesHtml || `<div class="chirp-empty" style="padding:20px">${L('noRepliesYet')}</div>`}
    </div>
  </div>
</div>`;
}

export function attachDetailListeners(app, container) {
  const VIEWS = app.constructor.VIEWS;
  const chirpId = app.viewParams.chirpId;
  const socialId = app.state.me;

  container.querySelector('#detail-back')?.addEventListener('click', () => app.goBack());

  container.querySelector('.main-post .more-btn')?.addEventListener('click', (e) => {
    e.stopPropagation();
    showMoreMenu(app, e.currentTarget, chirpId);
  });

  container.querySelectorAll('[data-action="open-profile"]').forEach(el => {
    el.addEventListener('click', (e) => {
      e.stopPropagation();
      app.switchView(VIEWS.PROFILE, { handle: e.currentTarget.dataset.handle });
    });
  });

  container.querySelectorAll('.chirp-post[data-chirp-id]').forEach(card => {
    card.addEventListener('click', () => {
      app.switchView(VIEWS.DETAIL, { chirpId: card.dataset.chirpId });
    });
  });

  container.querySelectorAll('.chirp-post [data-action="more"]').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const postEl = btn.closest('.chirp-post[data-chirp-id]');
      if (!postEl) return;
      showMoreMenu(app, btn, postEl.dataset.chirpId);
    });
  });

  container.querySelectorAll('[data-action][data-chirp-id]').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const { action, chirpId: cid } = btn.dataset;
      if (action === 'share') { app.showToast(L('linkCopied')); return; }
      if (action === 'reply') {
        container.querySelector('#reply-input')?.focus();
        return;
      }
      if (action === 'rechirp') {
        showDetailRechirpMenu(app, btn, cid);
        return;
      }
      await handleInteraction(app, action, cid);
    });
  });

  container.querySelectorAll('.quote[data-chirp-id]').forEach(q => {
    q.addEventListener('click', (e) => {
      e.stopPropagation();
      app.switchView(VIEWS.DETAIL, { chirpId: q.dataset.chirpId });
    });
  });

  const replyInput = container.querySelector('#reply-input');
  const replySend = container.querySelector('#reply-send');

  replyInput?.addEventListener('input', () => {
    replySend.disabled = !replyInput.value.trim();
  });

  replyInput?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && replyInput.value.trim()) {
      replySend?.click();
    }
  });

  replySend?.addEventListener('click', async () => {
    const text = replyInput.value.trim();
    if (!text) return;

    const reply = {
      id: `chirp_${foundry.utils.randomID()}`,
      authorSocialId: socialId,
      content: text,
      media: [],
      timestamp: chirpNow(),
      _createdAt: Date.now(),
      likes: [],
      rechirps: [],
      bookmarks: [],
      replies: [],
      replyTo: chirpId,
      quoteChirpId: null,
      poll: null,
      pinned: false,
      isHidden: false,
      publishTimestamp: null,
      fakeLikes: 0,
      fakeRechirps: 0,
      fakeBookmarks: 0,
      fakeReplies: 0,
    };

    const result = await app.socket.executeAsGM('chirp_createPost', { chirp: reply, socialId });
    if (result?.success) {
      await app.loadPosts();
      replyInput.value = '';
      replySend.disabled = true;
      app.showToast(L('replyChirped'));
      app.switchView(VIEWS.DETAIL, { chirpId });
    }
  });
}

function showDetailRechirpMenu(app, anchorBtn, chirpId) {
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

  const actionsBar = anchorBtn.closest('.big-actions') || anchorBtn.closest('.chirp-actions');
  if (actionsBar) {
    actionsBar.style.position = 'relative';
    menu.style.bottom = 'auto';
    menu.style.top = '100%';
    menu.style.left = '50%';
    menu.style.transform = 'translateX(-50%)';
    actionsBar.appendChild(menu);
  }

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
