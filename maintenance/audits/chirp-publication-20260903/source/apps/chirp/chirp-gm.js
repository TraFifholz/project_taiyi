import { renderIcon, renderAvatar } from './chirp-shared.js';
import { MODULE_ID, chirpNow, L, getCustomLogoIcon, clearShareTermCache, clearLogoIconCache } from './chirp-utils.js';

function gmGuard(app) {
  if (!game.user.isGM) {
    return `<div class="chirp-app"><div class="chirp-empty">${L('gmOnly')}</div></div>`;
  }
  return null;
}

function renderGMNav(activeView) {
  return `
<div class="gm-nav">
<button class="gm-nav-btn${activeView === 'gm_accounts' ? ' active' : ''}" data-gm-view="gm_accounts">${L('accounts')}</button>
<button class="gm-nav-btn${activeView === 'gm_trends' ? ' active' : ''}" data-gm-view="gm_trends">${L('trends')}</button>
<button class="gm-nav-btn${activeView === 'gm_settings' ? ' active' : ''}" data-gm-view="gm_settings">${L('settings')}</button>
</div>`;
}

export function renderGMAccountsView(app) {
  const guard = gmGuard(app);
  if (guard) return guard;

  const { accounts } = app.state;
  const searchQuery = (app.viewParams._gmAccountSearch || '').toLowerCase();
  const accountList = Array.from(accounts.values()).filter(acc => {
    if (!searchQuery) return true;
    return acc.handle.toLowerCase().includes(searchQuery) || acc.name.toLowerCase().includes(searchQuery);
  });
  const totalCount = accounts.size;

  const loggedInSocialId = app.state.me;

  const listHtml = accountList.map(acc => {
    const isLoggedIn = acc.socialId === loggedInSocialId;
    return `
<div class="gm-account-row" data-social-id="${acc.socialId}">
  ${renderAvatar(acc, 'sm')}
  <div class="gm-acc-info">
    <div class="gm-acc-name">${acc.name}${acc.verified ? ' ✓' : ''}${isLoggedIn ? ` <span class="gm-logged-in-badge">${L('loggedIn')}</span>` : ''}</div>
    <div class="gm-acc-handle">@${acc.handle} ${acc.ownerActorId ? `(${L('player')})` : `(GM)`}</div>
  </div>
  <div class="gm-acc-actions">
    <button class="gm-btn${isLoggedIn ? '' : ' primary'}" data-action="gm-login-account" data-social-id="${acc.socialId}">${isLoggedIn ? L('logout') : L('logIn')}</button>
    <button class="gm-btn" data-action="gm-edit-account" data-social-id="${acc.socialId}">${L('edit')}</button>
    <button class="gm-btn danger" data-action="gm-delete-account" data-social-id="${acc.socialId}">${L('del')}</button>
  </div>
</div>`;
  }).join('') || `<div class="chirp-empty">${L('nothingHereYet')}</div>`;

  return `
<div class="chirp-app">
  <div class="chirp-topbar">
    <button class="back" id="gm-back">${renderIcon('back')}</button>
    <div class="page-title">${L('gmPanel')}</div>
    <div></div>
  </div>
  <div class="chirp-main">
    ${renderGMNav('gm_accounts')}
    <div class="gm-search-bar">
      <div class="gm-search-wrap">
        ${renderIcon('search', '', 'width:14px;height:14px')}
        <input type="text" id="gm-account-search" class="gm-search-input" placeholder="${L('searchAccounts')}" value="${app.viewParams._gmAccountSearch || ''}" />
      </div>
    </div>
    <div class="gm-section-head">
      ${searchQuery ? `${accountList.length} / ${totalCount}` : `Accounts (${totalCount})`}
      <button class="gm-btn primary" id="gm-create-npc">+ ${L('createAccountBtn')}</button>
    </div>
    <div id="gm-accounts-list">${listHtml}</div>
  </div>
</div>`;
}

export function attachGMAccountsListeners(app, container) {
  const VIEWS = app.constructor.VIEWS;

  container.querySelector('#gm-back')?.addEventListener('click', () => app.goBack());

  container.querySelectorAll('[data-gm-view]').forEach(btn => {
    btn.addEventListener('click', () => {
      const viewMap = {
        gm_accounts: VIEWS.GM_ACCOUNTS,
        gm_trends: VIEWS.GM_TRENDS,
        gm_settings: VIEWS.GM_SETTINGS,
      };
      app.switchView(viewMap[btn.dataset.gmView]);
    });
  });

  const searchInput = container.querySelector('#gm-account-search');
  let searchTimer = null;
  searchInput?.addEventListener('input', () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      app.viewParams._gmAccountSearch = searchInput.value.trim();
      app.render();
    }, 200);
  });
  searchInput?.focus();
  if (searchInput) {
    const val = searchInput.value;
    searchInput.setSelectionRange(val.length, val.length);
  }

  container.querySelectorAll('[data-action="gm-login-account"]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const { socialId } = btn.dataset;
      const phoneId = app.phoneId;
      if (!phoneId) { app.showToast(L('noPhoneId')); return; }
      const isLoggedIn = socialId === app.state.me;
      const targetSocialId = isLoggedIn ? null : socialId;
      const result = await app.socket.executeAsGM('chirp_updateLoginState', { phoneId, socialId: targetSocialId });
      if (result?.success) {
        const acc = app.state.accounts.get(socialId);
        app.showToast(isLoggedIn ? L('loggedOut') : L('loggedInAs', { handle: acc?.handle || '?' }));
      }
    });
  });

  container.querySelector('#gm-create-npc')?.addEventListener('click', () => {
    showCreateAccountOverlay(app);
  });

  container.querySelectorAll('[data-action="gm-delete-account"]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const { socialId } = btn.dataset;
      const result = await app.socket.executeAsGM('chirp_gmDeleteAccount', { socialId });
      if (result?.success) {
        await app.loadAccounts();
        await app.loadPosts();
        app.showToast(L('accountDeleted'));
        app.switchView(VIEWS.GM_ACCOUNTS);
      }
    });
  });

  container.querySelectorAll('[data-action="gm-edit-account"]').forEach(btn => {
    btn.addEventListener('click', () => {
      const acc = app.state.accounts.get(btn.dataset.socialId);
      if (!acc) return;
      showEditAccountOverlay(app, acc);
    });
  });
}

function showCreateAccountOverlay(app) {
  const existing = app.widget?.element?.querySelector('.gm-edit-overlay');
  if (existing) existing.remove();

  const overlay = document.createElement('div');
  overlay.className = 'gm-edit-overlay fake-counts-overlay';
  overlay.innerHTML = `
    <div class="fake-counts-editor gm-edit-form-panel">
      <div class="fake-editor-title">${L('createAccountTitle')}</div>
      <div class="gm-field"><label>Handle</label><input type="text" data-create="handle" placeholder="${L('accountHandle')}" /></div>
      <div class="gm-field"><label>${L('displayName')}</label><input type="text" data-create="name" placeholder="${L('accountName')}" /></div>
      <div class="gm-field"><label>${L('password')}</label><input type="password" data-create="password" placeholder="••••••••" /></div>
      <div class="gm-field"><label>Bio</label><textarea data-create="bio" rows="2" placeholder="${L('characterBio')}"></textarea></div>
      <div class="gm-field"><label>${L('joinedDate')}</label><input type="text" data-create="joinedDate" placeholder="${L('joinedDatePlaceholder')}" /></div>
      <label class="gm-check"><input type="checkbox" data-create="verified" /> ${L('verified')}</label>
      <div class="fake-editor-btns">
        <button class="gm-btn" data-create-action="cancel">${L('cancel')}</button>
        <button class="gm-btn primary" data-create-action="submit">${L('create')}</button>
      </div>
    </div>`;

  const appEl = app.widget?.element?.querySelector('.chirp-app') || app.widget?.element;
  appEl?.appendChild(overlay);

  overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });
  overlay.querySelector('[data-create-action="cancel"]').addEventListener('click', () => overlay.remove());

  overlay.querySelector('[data-create-action="submit"]').addEventListener('click', async () => {
    const handle = overlay.querySelector('[data-create="handle"]').value.trim();
    const name = overlay.querySelector('[data-create="name"]').value.trim();
    const password = overlay.querySelector('[data-create="password"]').value;
    const bio = overlay.querySelector('[data-create="bio"]').value.trim();
    const joinedDate = overlay.querySelector('[data-create="joinedDate"]').value.trim();
    const verified = overlay.querySelector('[data-create="verified"]').checked;

    if (!handle || !name || !password) { app.showToast(L('handleNamePasswordRequired')); return; }

    const result = await app.socket.executeAsGM('chirp_gmCreateAccount', { handle, name, bio, verified, password, joinedDate });
    overlay.remove();
    if (result?.success) {
      await app.loadAccounts();
      app.showToast(L('accountCreated', { handle }));
      app.render();
    } else {
      app.showToast(result?.error || L('failedToCreate'));
    }
  });
}

function showEditAccountOverlay(app, acc) {
  const existing = app.widget?.element?.querySelector('.gm-edit-overlay');
  if (existing) existing.remove();

  const overlay = document.createElement('div');
  overlay.className = 'gm-edit-overlay fake-counts-overlay';
  overlay.innerHTML = `
    <div class="fake-counts-editor gm-edit-form-panel">
      <div class="fake-editor-title">${L('editAccountTitle')}</div>
      <div class="gm-field"><label>Handle</label><input type="text" data-edit="handle" value="${acc.handle}" /></div>
      <div class="gm-field"><label>${L('displayName')}</label><input type="text" data-edit="name" value="${acc.name}" /></div>
      <div class="gm-field"><label>Bio</label><textarea data-edit="bio" rows="2">${acc.bio || ''}</textarea></div>
      <div class="gm-field"><label>${L('joinedDate')}</label><input type="text" data-edit="joinedDate" value="${acc.joinedDate || ''}" placeholder="${L('joinedDatePlaceholder')}" /></div>
      <div class="gm-field"><label>${L('newPassword')}</label><input type="password" data-edit="password" placeholder="${L('newPasswordPlaceholder')}" /></div>
      <label class="gm-check"><input type="checkbox" data-edit="verified" ${acc.verified ? 'checked' : ''} /> ${L('verified')}</label>
      <div class="fake-counts-grid">
        <div class="fake-field"><label>${L('fakeFollowers')}</label><input type="number" data-edit="fakeFollowers" min="0" value="${acc.fakeFollowers || 0}" /></div>
        <div class="fake-field"><label>${L('fakeFollowing')}</label><input type="number" data-edit="fakeFollowing" min="0" value="${acc.fakeFollowing || 0}" /></div>
      </div>
      <div class="fake-editor-btns">
        <button class="gm-btn" data-edit-action="cancel">${L('cancel')}</button>
        <button class="gm-btn primary" data-edit-action="save">${L('save')}</button>
      </div>
    </div>`;

  const appEl = app.widget?.element?.querySelector('.chirp-app') || app.widget?.element;
  appEl?.appendChild(overlay);

  overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });
  overlay.querySelector('[data-edit-action="cancel"]').addEventListener('click', () => overlay.remove());

  overlay.querySelector('[data-edit-action="save"]').addEventListener('click', async () => {
    const patch = {
      handle: overlay.querySelector('[data-edit="handle"]').value.trim(),
      name: overlay.querySelector('[data-edit="name"]').value.trim(),
      bio: overlay.querySelector('[data-edit="bio"]').value.trim(),
      joinedDate: overlay.querySelector('[data-edit="joinedDate"]').value.trim(),
      verified: overlay.querySelector('[data-edit="verified"]').checked,
      fakeFollowers: parseInt(overlay.querySelector('[data-edit="fakeFollowers"]').value) || 0,
      fakeFollowing: parseInt(overlay.querySelector('[data-edit="fakeFollowing"]').value) || 0,
    };
    const newPassword = overlay.querySelector('[data-edit="password"]').value || null;

    if (!patch.handle || !patch.name) { app.showToast(L('handleNamePasswordRequired')); return; }

    const result = await app.socket.executeAsGM('chirp_gmEditAccount', { socialId: acc.socialId, patch, newPassword });
    overlay.remove();
    if (result?.success) {
      await app.loadAccounts();
      app.showToast(L('accountUpdated'));
      app.render();
    } else {
      app.showToast(result?.error || L('failedToCreate'));
    }
  });

}

export function renderGMSettingsView(app) {
  const guard = gmGuard(app);
  if (guard) return guard;

  const shareTerm = (() => { try { return game.settings.get(MODULE_ID, 'chirp-share-term') || ''; } catch { return ''; } })();
  const logoIcon = (() => { try { return game.settings.get(MODULE_ID, 'chirp-logo-icon') || ''; } catch { return ''; } })();

  return `
<div class="chirp-app">
  <div class="chirp-topbar">
    <button class="back" id="gm-back">${renderIcon('back')}</button>
    <div class="page-title">${L('gmPanel')}</div>
    <div></div>
  </div>
  <div class="chirp-main">
    ${renderGMNav('gm_settings')}

    <div class="gm-tool-section">
      <div class="gm-section-head">${L('customize')}</div>
      <div class="gm-field">
        <label>${L('shareTermLabel')}</label>
        <input type="text" id="gm-share-term" placeholder="Rechirp" value="${shareTerm}" />
      </div>
      <div class="gm-field">
        <label>${L('logoIconLabel')}</label>
        <input type="text" id="gm-logo-icon" placeholder="fa-solid fa-feather" value="${logoIcon}" />
      </div>
      <button class="gm-btn primary" id="gm-apply-customize">${L('applyCustomize')}</button>
    </div>
  </div>
</div>`;
}

export function attachGMSettingsListeners(app, container) {
  const VIEWS = app.constructor.VIEWS;

  container.querySelector('#gm-back')?.addEventListener('click', () => app.goBack());
  container.querySelectorAll('[data-gm-view]').forEach(btn => {
    btn.addEventListener('click', () => {
      const vm = { gm_accounts: VIEWS.GM_ACCOUNTS, gm_trends: VIEWS.GM_TRENDS, gm_settings: VIEWS.GM_SETTINGS };
      app.switchView(vm[btn.dataset.gmView]);
    });
  });

  container.querySelector('#gm-apply-customize')?.addEventListener('click', async () => {
    const shareTerm = container.querySelector('#gm-share-term')?.value?.trim() || '';
    const logoIcon = container.querySelector('#gm-logo-icon')?.value?.trim() || '';
    await game.settings.set(MODULE_ID, 'chirp-share-term', shareTerm);
    await game.settings.set(MODULE_ID, 'chirp-logo-icon', logoIcon);
    clearShareTermCache();
    clearLogoIconCache();
    app.showToast(L('customizeApplied'));
    app.render();
  });
}

export function renderGMTrendsView(app) {
  const guard = gmGuard(app);
  if (guard) return guard;

  const { trends } = app.state;

  const trendsList = trends.map((t, i) => `
<div class="gm-trend-row">
  <div class="gm-trend-info">
    <div class="gm-trend-name">${t.name}</div>
    <div class="gm-trend-meta">${t.cat || ''} · ${t.count || ''}</div>
  </div>
  <button class="gm-btn danger" data-action="remove-trend" data-index="${i}">×</button>
</div>`).join('') || `<div class="chirp-empty">${L('nothingHereYet')}</div>`;

  return `
<div class="chirp-app">
  <div class="chirp-topbar">
    <button class="back" id="gm-back">${renderIcon('back')}</button>
    <div class="page-title">${L('gmPanel')}</div>
    <div></div>
  </div>
  <div class="chirp-main">
    ${renderGMNav('gm_trends')}

    <div class="gm-section-head">
      Trends (${trends.length})
      <button class="gm-btn primary" id="gm-add-trend-btn">+ ${L('addTrend')}</button>
    </div>
    <div id="gm-trends-list">${trendsList}</div>
  </div>
</div>`;
}

function showAddTrendOverlay(app) {
  const existing = app.widget?.element?.querySelector('.gm-edit-overlay');
  if (existing) existing.remove();

  const overlay = document.createElement('div');
  overlay.className = 'gm-edit-overlay fake-counts-overlay';
  overlay.innerHTML = `
    <div class="fake-counts-editor gm-edit-form-panel">
      <div class="fake-editor-title">${L('addTrend')}</div>
      <div class="gm-field"><label>${L('trendName')}</label><input type="text" data-trend="name" placeholder="${L('trendNamePlaceholder')}" /></div>
      <div class="gm-field"><label>${L('trendCategory')}</label><input type="text" data-trend="cat" placeholder="${L('trendCategoryDefault')}" /></div>
      <div class="gm-field"><label>${L('trendCount')}</label><input type="text" data-trend="count" placeholder="${L('trendCountPlaceholder')}" /></div>
      <div class="fake-editor-btns">
        <button class="gm-btn" data-trend-action="cancel">${L('cancel')}</button>
        <button class="gm-btn primary" data-trend-action="add">${L('addTrend')}</button>
      </div>
    </div>`;

  const appEl = app.widget?.element?.querySelector('.chirp-app') || app.widget?.element;
  appEl?.appendChild(overlay);

  overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });
  overlay.querySelector('[data-trend-action="cancel"]').addEventListener('click', () => overlay.remove());

  overlay.querySelector('[data-trend-action="add"]').addEventListener('click', async () => {
    const name = overlay.querySelector('[data-trend="name"]').value.trim();
    const cat = overlay.querySelector('[data-trend="cat"]').value.trim() || L('trendCategoryDefault');
    const count = overlay.querySelector('[data-trend="count"]').value.trim();
    if (!name) { app.showToast(L('enterTrendName')); return; }
    const result = await app.socket.executeAsGM('chirp_gmAddTrend', { trend: { name, cat, count } });
    overlay.remove();
    if (result?.success) {
      await app.loadTrends();
      app.showToast(L('trendAdded'));
      app.render();
    }
  });
}

export function attachGMTrendsListeners(app, container) {
  const VIEWS = app.constructor.VIEWS;

  container.querySelector('#gm-back')?.addEventListener('click', () => app.goBack());
  container.querySelectorAll('[data-gm-view]').forEach(btn => {
    btn.addEventListener('click', () => {
      const vm = { gm_accounts: VIEWS.GM_ACCOUNTS, gm_trends: VIEWS.GM_TRENDS, gm_settings: VIEWS.GM_SETTINGS };
      app.switchView(vm[btn.dataset.gmView]);
    });
  });

  container.querySelector('#gm-add-trend-btn')?.addEventListener('click', () => {
    showAddTrendOverlay(app);
  });

  container.querySelectorAll('[data-action="remove-trend"]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const index = parseInt(btn.dataset.index);
      const result = await app.socket.executeAsGM('chirp_gmRemoveTrend', { index });
      if (result?.success) {
        await app.loadTrends();
        app.showToast(L('trendRemoved'));
        app.switchView(VIEWS.GM_TRENDS);
      }
    });
  });
}
