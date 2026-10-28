import { renderIcon, renderAvatar, renderActionBar, renderMediaGrid, computeReplyCounts } from './chirp-shared.js';
import { renderContent, L } from './chirp-utils.js';
import { renderPostCard } from './chirp-timeline.js';

export function renderTrendDetailView(app) {
  const trend = app.viewParams.trend || (app.viewParams.trendName ? { name: app.viewParams.trendName, cat: '', count: '' } : null);
  if (!trend) return `<div class="chirp-app"><div class="chirp-empty">${L('chirpNotFound')}</div></div>`;

  const tab = app.viewParams.trendTab || 'top';
  const { posts, accounts, me } = app.state;
  const allPosts = Array.from(posts.values());
  const needle = trend.name.replace(/^#/, '').toLowerCase();
  const matched = allPosts.filter(p => p.content && p.content.toLowerCase().includes(needle));

  const replyCounts = computeReplyCounts(posts);
  const postState = app.state.postState;

  let feedHtml = '';

  if (tab === 'people') {
    const people = Array.from(accounts.values()).filter(a => a.socialId !== me).slice(0, 10);
    feedHtml = people.length === 0
      ? `<div class="chirp-empty">${L('noOneHereYet')}</div>`
      : people.map(u => `
        <div class="td-person" data-action="open-profile" data-handle="${u.socialId}">
          ${renderAvatar(u)}
          <div class="tp-body">
            <div class="tp-name">
              ${u.name}
              ${u.verified ? renderIcon('verified', 'verified', 'width:11px;height:11px') : ''}
            </div>
            <div class="tp-handle">@${u.handle}</div>
            ${u.bio ? `<div class="tp-bio">${u.bio}</div>` : ''}
          </div>
        </div>`).join('');
  } else if (tab === 'media') {
    const mediaPosts = matched.filter(p => p.media?.length);
    feedHtml = mediaPosts.length === 0
      ? `<div class="chirp-empty">${L('nothingHereYet')}</div>`
      : `<div class="td-media-grid">${mediaPosts.map(p => `
          <div class="td-media-cell" data-chirp-id="${p.id}">
            <img src="${p.media[0].src}" style="width:100%;height:100%;object-fit:cover" />
          </div>`).join('')}</div>`;
  } else {
    const sorted = tab === 'latest'
      ? [...matched].sort((a, b) => b.timestamp - a.timestamp)
      : [...matched].sort((a, b) => (b.likes?.length || 0) - (a.likes?.length || 0));
    feedHtml = sorted.length === 0
      ? `<div class="chirp-empty">${L('nothingHereYet')}</div>`
      : sorted.map((p, i) => renderPostCard(p, accounts, me, i === 0, null, null, replyCounts, posts)).join('');
  }

  return `
<div class="chirp-app chirp-trend-detail">
  <div class="td-header">
    <button class="back" data-action="back" aria-label="back">${renderIcon('back')}</button>
    <div class="td-head-body">
      <div class="td-label">${L('trendingTopic')}</div>
      <div class="td-name">${trend.name}</div>
    </div>
  </div>
  <div class="td-hero">
    <div class="td-hero-cat">${trend.cat || ''}</div>
    <div class="td-hero-title">${trend.name}</div>
    <div class="td-hero-count">${trend.count || ''}</div>
  </div>
  <div class="td-tabs">
    <button class="tt${tab === 'top' ? ' active' : ''}" data-trend-tab="top">${L('top')}</button>
    <button class="tt${tab === 'latest' ? ' active' : ''}" data-trend-tab="latest">${L('latest')}</button>
    <button class="tt${tab === 'people' ? ' active' : ''}" data-trend-tab="people">${L('people')}</button>
    <button class="tt${tab === 'media' ? ' active' : ''}" data-trend-tab="media">${L('media')}</button>
  </div>
  <div class="td-feed">
    ${feedHtml}
  </div>
</div>`;
}

export function attachTrendDetailListeners(app, container) {
  const VIEWS = app.constructor.VIEWS;

  container.querySelector('[data-action="back"]')?.addEventListener('click', () => app.goBack());

  container.querySelectorAll('[data-trend-tab]').forEach(btn => {
    btn.addEventListener('click', () => {
      app.viewParams.trendTab = btn.dataset.trendTab;
      app.render();
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

  container.querySelectorAll('.td-media-cell[data-chirp-id]').forEach(cell => {
    cell.addEventListener('click', () => {
      app.switchView(VIEWS.DETAIL, { chirpId: cell.dataset.chirpId });
    });
  });
}
