import { renderIcon, computeReplyCounts, sortFeedItems } from './chirp-shared.js';
import { renderPostCard, showMoreMenu } from './chirp-timeline.js';
import { handleInteraction } from './chirp-interactions.js';
import { L } from './chirp-utils.js';

const PAGE_SIZE = 20;

export function renderBookmarksView(app) {
  const { posts, accounts, me } = app.state;

  const bookmarked = Array.from(posts.values())
    .filter(p => p.bookmarks?.includes(me))
    .map(p => ({ post: p, rechirpedBy: null }));

  sortFeedItems(bookmarked);

  const displayCount = app.viewParams._bookmarksDisplayCount || PAGE_SIZE;
  const page = bookmarked.slice(0, displayCount);
  const hasMore = bookmarked.length > displayCount;
  const replyCounts = computeReplyCounts(posts);

  const postsHtml = page.length === 0
    ? `<div class="chirp-empty">${L('noBookmarks')}</div>`
    : page.map((item, i) => renderPostCard(item.post, accounts, me, i === 0, null, item.rechirpedBy, replyCounts, posts)).join('');

  return `
<div class="chirp-app chirp-bookmarks">
  <div class="detail-header">
    <button class="back" data-action="back" aria-label="back">${renderIcon('back')}</button>
    <div style="display:flex;flex-direction:column">
      <div style="font-weight:700;font-size:13px">${L('bookmarksTitle')}</div>
      <div style="font-size:10px;color:var(--text-dim)">${bookmarked.length} chirps</div>
    </div>
  </div>
  <div class="chirp-main">
    <div id="chirp-bookmarks-list">${postsHtml}</div>
    ${hasMore ? '<div class="chirp-load-more" id="chirp-bookmarks-sentinel"></div>' : ''}
  </div>
</div>`;
}

export function attachBookmarksListeners(app, container) {
  const VIEWS = app.constructor.VIEWS;

  container.querySelector('[data-action="back"]')?.addEventListener('click', () => app.goBack());

  container.querySelectorAll('.chirp-post[data-chirp-id]').forEach(card => {
    card.addEventListener('click', () => {
      app.switchView(VIEWS.DETAIL, { chirpId: card.dataset.chirpId });
    });
  });

  container.querySelectorAll('[data-action="open-profile"]').forEach(el => {
    el.addEventListener('click', (e) => {
      e.stopPropagation();
      app.switchView(VIEWS.PROFILE, { handle: el.dataset.handle });
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
      await handleInteraction(app, action, chirpId);
    });
  });

  container.querySelectorAll('.quote[data-chirp-id]').forEach(q => {
    q.addEventListener('click', (e) => {
      e.stopPropagation();
      app.switchView(VIEWS.DETAIL, { chirpId: q.dataset.chirpId });
    });
  });

  const sentinel = container.querySelector('#chirp-bookmarks-sentinel');
  if (sentinel) {
    const scrollArea = app.widget?.element?.querySelector('.chirp-main') || app.widget?.element;
    if (scrollArea) {
      const observer = new IntersectionObserver((entries) => {
        if (entries[0].isIntersecting) {
          observer.disconnect();
          app.viewParams._bookmarksDisplayCount = (app.viewParams._bookmarksDisplayCount || PAGE_SIZE) + PAGE_SIZE;
          app.render();
        }
      }, { root: scrollArea, threshold: 0 });
      observer.observe(sentinel);
    }
  }
}
