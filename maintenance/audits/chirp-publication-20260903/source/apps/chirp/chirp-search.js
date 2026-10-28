import { renderIcon, renderAvatar } from './chirp-shared.js';
import { renderContent, L } from './chirp-utils.js';

export function renderSearchView(app) {
  const q = app.viewParams.q || '';
  const { accounts, posts, trends } = app.state;

  let resultsHtml = '';
  if (q.trim()) {
    const qq = q.toLowerCase();
    const matchedUsers = Array.from(accounts.values()).filter(a =>
      a.name.toLowerCase().includes(qq) || a.handle.toLowerCase().includes(qq)
    );
    const matchedPosts = Array.from(posts.values()).filter(p =>
      (p.content || '').toLowerCase().includes(qq)
    );

    if (matchedUsers.length === 0 && matchedPosts.length === 0) {
      resultsHtml = `<div class="chirp-empty">${L('noResults', {q})}</div>`;
    } else {
      if (matchedUsers.length > 0) {
         resultsHtml += `<div class="chirp-trends"><div class="section-head">${L('people')}</div></div>`;
        resultsHtml += matchedUsers.map(u => `
<div class="chirp-post" data-action="open-profile" data-handle="${u.socialId}" style="grid-template-columns:36px 1fr;align-items:center;cursor:pointer">
  ${renderAvatar(u)}
  <div>
    <div style="font-weight:700;font-size:13px">${u.name}${u.verified ? ` ${renderIcon('verified', 'verified', 'width:12px;height:12px')}` : ''}</div>
    <div style="color:var(--text-dim);font-size:11px">@${u.handle}</div>
    ${u.bio ? `<div style="font-size:11px;margin-top:2px">${u.bio}</div>` : ''}
  </div>
</div>`).join('');
      }
      if (matchedPosts.length > 0) {
         resultsHtml += `<div class="chirp-trends"><div class="section-head">${L('chirps')}</div></div>`;
        resultsHtml += matchedPosts.map(p => {
          const author = accounts.get(p.authorSocialId);
          if (!author) return '';
          return `
<div class="chirp-post" data-chirp-id="${p.id}" style="cursor:pointer;display:grid;grid-template-columns:36px 1fr;gap:10px;padding:12px;border-bottom:1px solid var(--border-soft)">
  <div data-action="open-profile" data-handle="${author.socialId}">${renderAvatar(author)}</div>
  <div>
    <div style="font-weight:700;font-size:13px">${author.name}</div>
    <div style="font-size:11px;color:var(--text-dim)">@${author.handle}</div>
    <div style="font-size:13px;margin-top:4px">${renderContent(p.content || '')}</div>
  </div>
</div>`;
        }).join('');
      }
    }
  } else {
    if (trends.length > 0) {
       resultsHtml = `
 <div class="chirp-trends">
   <div class="section-head">${L('trendsForYou')}</div>
  ${trends.map((t, i) => `
  <div class="trend" data-trend-idx="${i}">
    <div class="cat">${t.cat || ''}</div>
    <div class="name">${t.name}</div>
    <div class="count">${t.count || ''}</div>
  </div>`).join('')}
</div>`;
    } else {
       resultsHtml = `<div class="chirp-empty">${L('noTrends')}</div>`;
    }
  }

  return `
    <div class="chirp-search-bar">
      <div class="wrap">
        ${renderIcon('search')}
         <input type="text" class="field" id="search-input" placeholder="${L('searchChirp')}" value="${q}" />
      </div>
    </div>
    <div id="search-results">${resultsHtml}</div>`;
}

export function attachSearchListeners(app, container) {
  const VIEWS = app.constructor.VIEWS;

  let debounceTimer;
  container.querySelector('#search-input')?.addEventListener('input', (e) => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      app.switchView(VIEWS.SEARCH, { q: e.target.value });
    }, 200);
  });

  container.querySelectorAll('[data-action="open-profile"]').forEach(el => {
    el.addEventListener('click', (e) => {
      e.stopPropagation();
      app.switchView(VIEWS.PROFILE, { handle: el.dataset.handle });
    });
  });

  container.querySelectorAll('[data-chirp-id]').forEach(card => {
    card.addEventListener('click', () => {
      app.switchView(VIEWS.DETAIL, { chirpId: card.dataset.chirpId });
    });
  });

  container.querySelectorAll('.trend[data-trend-idx]').forEach(el => {
    el.addEventListener('click', () => {
      const idx = parseInt(el.dataset.trendIdx);
      const trend = app.state.trends[idx];
      if (trend) app.switchView(VIEWS.TREND_DETAIL, { trend });
    });
  });
}
