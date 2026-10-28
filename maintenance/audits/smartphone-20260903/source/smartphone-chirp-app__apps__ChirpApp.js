import { BaseApp } from '../../smartphone-widget/scripts/apps/BaseApp.js';
import { SmartphoneWidget } from '../../smartphone-widget/scripts/smartphone-widget.js';
import { renderAuthView, attachAuthListeners } from './chirp/chirp-auth.js';
import { renderComposeView, attachComposeListeners } from './chirp/chirp-compose.js';
import { renderTimelineView, attachTimelineListeners } from './chirp/chirp-timeline.js';
import { renderDetailView, attachDetailListeners } from './chirp/chirp-detail.js';
import { renderSearchView, attachSearchListeners } from './chirp/chirp-search.js';
import { renderNotificationsView, attachNotificationsListeners } from './chirp/chirp-notifications.js';
import { renderMessagesView, attachMessagesListeners, renderConversationView, attachConversationListeners, tryAppendDM } from './chirp/chirp-dm.js';
import './chirp/chirp-poll.js';
import { renderProfileView, attachProfileListeners, renderEditProfileView, attachEditProfileListeners } from './chirp/chirp-profile.js';
import { renderFollowsView, attachFollowsListeners } from './chirp/chirp-follows.js';
import { renderTrendDetailView, attachTrendDetailListeners } from './chirp/chirp-trend-detail.js';
import { renderBookmarksView, attachBookmarksListeners } from './chirp/chirp-bookmarks.js';
import { renderGMAccountsView, attachGMAccountsListeners, renderGMSettingsView, attachGMSettingsListeners, renderGMTrendsView, attachGMTrendsListeners } from './chirp/chirp-gm.js';
import { L } from './chirp/chirp-utils.js';
import { renderIcon, renderAvatar } from './chirp/chirp-shared.js';

const MODULE_ID = 'smartphone-chirp-app';

export class ChirpApp extends BaseApp {
  static socket = null;

  static VIEWS = {
    AUTH: 'auth',
    TIMELINE: 'timeline',
    DETAIL: 'detail',
    PROFILE: 'profile',
    SEARCH: 'search',
    NOTIFICATIONS: 'notifications',
    MESSAGES: 'messages',
    CONVERSATION: 'conversation',
    COMPOSE: 'compose',
    EDIT_PROFILE: 'edit_profile',
    FOLLOWS: 'follows',
    TREND_DETAIL: 'trend_detail',
    BOOKMARKS: 'bookmarks',
    GM_ACCOUNTS: 'gm_accounts',
    GM_SETTINGS: 'gm_settings',
    GM_TRENDS: 'gm_trends',
  };

  // -------------------------------------------------------------------
  // Static lifecycle
  // -------------------------------------------------------------------

  static async registerSettings() {
    const { registerChirpSettings } = await import('./chirp/chirp-settings.js');
    registerChirpSettings();
  }

  static initialize(socket) {
    if (!socket) {
      console.error('[ChirpApp] No socket provided');
      return false;
    }

    ChirpApp.socket = socket;

    ChirpApp.registerSettings();

    SmartphoneWidget.registerBadgeUpdater('chirp', async () => {
      const instance = (await SmartphoneWidget.getInstance())?.apps.get('chirp');
      if (instance?.state?.me) {
        return instance.state.notifications?.filter(n => !n.read)?.length || 0;
      }
      try {
        const wm = await SmartphoneWidget.getInstance();
        const phoneId = wm?.currentPhoneId;
        if (!phoneId) return 0;
        const states = game.settings.get(MODULE_ID, 'chirp-login-states') || {};
        const socialId = states[phoneId];
        if (!socialId) return 0;
        const notifs = game.settings.get(MODULE_ID, 'chirp-notifications') || {};
        return notifs[socialId]?.filter(n => !n.read)?.length || 0;
      } catch { return 0; }
    });

    socket.register('updateChirp', async (data) => {
      const widgetManager = await SmartphoneWidget.getInstance();
      if (!widgetManager) return;
      const instance = widgetManager.apps.get('chirp');
      if (!instance) return;
      if (data?.deleted && data?.chirpId) {
        instance.state.posts.delete(data.chirpId);
      } else if (data?.chirp) {
        instance.state.posts.set(data.chirp.id, data.chirp);
      }
      if (widgetManager.currentApp === 'chirp') {
        instance.renderAfterRealtimeUpdate();
      }
    });

    socket.register('updateProfile', async (data) => {
      const instance = (await SmartphoneWidget.getInstance())?.apps.get('chirp');
      if (!instance) return;
      if (data?.account) {
        instance.state.accounts.set(data.socialId, data.account);
      } else if (data?.socialId) {
        instance.state.accounts.delete(data.socialId);
      }
      if (instance.widget.currentApp === 'chirp') {
        instance.renderAfterRealtimeUpdate();
      }
    });

    socket.register('updateNotifications', async (data) => {
      const widgetManager = await SmartphoneWidget.getInstance();
      if (!widgetManager) return;
      const instance = widgetManager.apps.get('chirp');

      const mySocialId = instance?.state?.me
        || (() => { try { const states = game.settings.get(MODULE_ID, 'chirp-login-states') || {}; return states[widgetManager.currentPhoneId] ?? null; } catch { return null; } })();

      if (!mySocialId) return;
      if (data?.targetSocialId && data.targetSocialId !== mySocialId) return;

      const oldCount = instance?.state?.notifications?.length || 0;

      if (instance && data?.notifications) {
        instance.state.notifications = data.notifications;
      }

      const newNotifs = data?.notifications || [];
      if (newNotifs.length > oldCount) {
        const latest = newNotifs[0];
        if (latest && !latest.read) {
          let fromName = '?';
          let fromIcon = 'icons/svg/mystery-man.svg';
          try {
            const accounts = game.settings.get(MODULE_ID, 'chirp-accounts') || {};
            const fromAcc = accounts[latest.fromSocialId];
            fromName = fromAcc?.name || '?';
            fromIcon = fromAcc?.profileImage || fromIcon;
          } catch {}

          const typeMessages = {
            like: game.i18n.localize('CHIRP.likedYourChirp'),
            rechirp: game.i18n.localize('CHIRP.rechirpedYourChirp'),
            reply: game.i18n.localize('CHIRP.repliedToYourChirp'),
            follow: game.i18n.localize('CHIRP.followedYou'),
            mention: game.i18n.localize('CHIRP.mentionedYou'),
            alert: game.i18n.localize('CHIRP.sentAlert'),
          };
          const body = `${fromName} ${typeMessages[latest.type] || ''}`;

          const isViewingNotifs = widgetManager.currentApp === 'chirp' && instance?.currentView === ChirpApp.VIEWS.NOTIFICATIONS;
          if (!isViewingNotifs) {
            widgetManager.showToastNotification(`<i class="fa-solid fa-feather" style="margin-right:6px"></i>${body}`);
          }

          widgetManager.addNotification({
            id: `chirp_${latest.timestamp || Date.now()}`,
            icon: fromIcon,
            title: 'Chirp',
            body,
            onClick: () => {
              widgetManager.switchApp('chirp');
              const inst = widgetManager.apps.get('chirp');
              if (inst) setTimeout(() => inst.switchView?.(ChirpApp.VIEWS.NOTIFICATIONS), 100);
            },
          });
        }
      }

      SmartphoneWidget.updateBadge('chirp');

      if (instance && widgetManager.currentApp === 'chirp') {
        instance.renderAfterRealtimeUpdate();
      }
    });

    socket.register('updateDMs', async (data) => {
      const instance = (await SmartphoneWidget.getInstance())?.apps.get('chirp');
      if (!instance) return;
      if (data?.key && data?.messages) {
        instance.state.dms[data.key] = data.messages;
      }
      if (instance.widget.currentApp !== 'chirp') return;
      if (instance.currentView === ChirpApp.VIEWS.CONVERSATION && data?.key) {
        if (tryAppendDM(instance, data.key, data.messages)) return;
      }
      instance.renderAfterRealtimeUpdate();
    });

    socket.register('updateTrends', async (data) => {
      const instance = (await SmartphoneWidget.getInstance())?.apps.get('chirp');
      if (!instance) return;
      if (data?.trends) {
        instance.state.trends = data.trends;
      }
      if (instance.widget.currentApp === 'chirp') {
        instance.renderAfterRealtimeUpdate();
      }
    });

    socket.register('showChirpNotification', async (data) => {
      const widgetInstance = await SmartphoneWidget.getInstance();
      if (!widgetInstance) return;
      const message = data?.message ?? '';
      if (widgetInstance.element) {
        widgetInstance.showToastNotification(message);
      } else {
        ui.notifications.info(message);
      }
    });

    socket.register('chirp_accountsUpdated', async () => {
      const widgetManager = await SmartphoneWidget.getInstance();
      if (!widgetManager) return;
      const instance = widgetManager.apps.get('chirp');
      if (!instance) return;
      await instance.loadAccounts();
      if (widgetManager.currentApp === 'chirp') instance.renderAfterRealtimeUpdate();
    });

    socket.register('chirp_loginStateChanged', async ({ phoneId, socialId }) => {
      const widgetManager = await SmartphoneWidget.getInstance();
      if (!widgetManager) return;
      const instance = widgetManager.apps.get('chirp');
      if (!instance || instance.phoneId !== phoneId) return;
      instance.state.me = socialId;
      instance.state.loginState = socialId;
      if (socialId) {
        await instance.loadAccounts();
        await instance.loadPosts();
        await instance.loadTrends();
        await instance.loadNotifications();
        await instance.loadDMs();
        const myAccount = instance.state.accounts.get(socialId);
        instance.state.following = myAccount?.following ?? [];
        instance.switchView(ChirpApp.VIEWS.TIMELINE);
      } else {
        instance.switchView(ChirpApp.VIEWS.AUTH);
      }
    });

    return true;
  }

  // -------------------------------------------------------------------
  // Instance
  // -------------------------------------------------------------------

  constructor(widget) {
    super(widget);

    this.state = {
      me: null,
      accounts: new Map(),
      posts: new Map(),
      dms: {},
      notifications: [],
      trends: [],
      postState: {},
      following: [],
      loginState: null,
    };

    this.currentView = ChirpApp.VIEWS.AUTH;
    this.viewParams = {};
    this.viewHistory = [];
    this._hasDeferredRealtimeRender = false;
    this._deferredRealtimeFlushArmed = false;
  }

  get socket() {
    return ChirpApp.socket;
  }

  renderAfterRealtimeUpdate() {
    if (this.shouldDeferRealtimeRender()) {
      this.deferRealtimeRender();
      return;
    }
    this._hasDeferredRealtimeRender = false;
    this.render();
  }

  deferRealtimeRender() {
    this._hasDeferredRealtimeRender = true;
    this.armDeferredRealtimeRenderFlush();
  }

  armDeferredRealtimeRenderFlush() {
    if (this._deferredRealtimeFlushArmed) return;

    const root = this.element ?? this.widget?.element?.querySelector('.chirp-app');
    if (!root) return;

    this._deferredRealtimeFlushArmed = true;
    const flushSoon = () => {
      setTimeout(() => {
        this._deferredRealtimeFlushArmed = false;
        this.flushDeferredRealtimeRender();
      }, 0);
    };

    root.addEventListener('focusout', flushSoon, { once: true });
    root.addEventListener('change', flushSoon, { once: true });
  }

  flushDeferredRealtimeRender() {
    if (!this._hasDeferredRealtimeRender) return false;
    if (this.shouldDeferRealtimeRender()) {
      this.armDeferredRealtimeRenderFlush();
      return false;
    }

    this._hasDeferredRealtimeRender = false;
    this.render();
    return true;
  }

  clearDeferredRealtimeRenderIfSafe() {
    if (!this._hasDeferredRealtimeRender || this.shouldDeferRealtimeRender()) return;
    this._hasDeferredRealtimeRender = false;
    this._deferredRealtimeFlushArmed = false;
  }

  shouldDeferRealtimeRender() {
    const root = this.element ?? this.widget?.element?.querySelector('.chirp-app');
    const inputLockViews = new Set([
      ChirpApp.VIEWS.COMPOSE,
      ChirpApp.VIEWS.EDIT_PROFILE,
    ]);

    if (inputLockViews.has(this.currentView)) return true;
    if (!root) return false;
    if (root.querySelector('.gm-edit-overlay, .fake-counts-overlay')) return true;

    const active = document.activeElement;
    if (active && root.contains(active) && active.matches?.('input, textarea, select, [contenteditable="true"]')) {
      return true;
    }

    if (this.currentView === ChirpApp.VIEWS.CONVERSATION && (this._pendingDMAttached || this._pendingDMImage)) {
      return true;
    }

    return this.hasDirtyFormFields(root);
  }

  hasDirtyFormFields(root) {
    const ignoredTypes = new Set(['button', 'submit', 'reset', 'hidden', 'file']);
    const fields = root.querySelectorAll('input, textarea, select');

    for (const field of fields) {
      const type = (field.type ?? '').toLowerCase();
      if (ignoredTypes.has(type)) continue;

      if (type === 'checkbox' || type === 'radio') {
        if (field.checked !== field.defaultChecked) return true;
        continue;
      }

      if (field.tagName === 'SELECT') {
        const changed = [...field.options].some(option => option.selected !== option.defaultSelected);
        if (changed) return true;
        continue;
      }

      if (field.value !== field.defaultValue) return true;
    }

    return false;
  }

  // -------------------------------------------------------------------
  // Data loading
  // -------------------------------------------------------------------

  async loadPosts() {
    const raw = (await game.settings.get(MODULE_ID, 'chirp-posts')) || {};
    this.state.posts.clear();
    for (const [id, chirp] of Object.entries(raw)) {
      this.state.posts.set(id, foundry.utils.deepClone(chirp));
    }
  }

  async loadAccounts() {
    const raw = (await game.settings.get(MODULE_ID, 'chirp-accounts')) || {};
    this.state.accounts.clear();
    for (const [id, account] of Object.entries(raw)) {
      this.state.accounts.set(id, foundry.utils.deepClone(account));
    }
  }

  async loadTrends() {
    const raw = (await game.settings.get(MODULE_ID, 'chirp-trends')) || [];
    this.state.trends = Array.isArray(raw) ? raw : [];
  }

  async loadNotifications() {
    const raw = (await game.settings.get(MODULE_ID, 'chirp-notifications')) || {};
    const socialId = this.state.me;
    this.state.notifications = socialId && raw[socialId]
      ? raw[socialId]
      : [];
  }

  async loadDMs() {
    this.state.dms = (await game.settings.get(MODULE_ID, 'chirp-dms')) || {};
    this.state.dmRead = (await game.settings.get(MODULE_ID, 'chirp-dm-read')) || {};
  }

  async getLoginState(phoneId) {
    const states = (await game.settings.get(MODULE_ID, 'chirp-login-states')) || {};
    const socialId = states[phoneId] ?? null;
    this.state.loginState = socialId;
    this.state.me = socialId;
    return socialId;
  }

  // -------------------------------------------------------------------
  // App lifecycle (called by smartphone-widget framework)
  // -------------------------------------------------------------------

  async onShow() {
    this.phoneId = this.widget.currentPhoneId;

    await this.loadAccounts();
    await this.loadPosts();
    await this.loadTrends();

    const login = await this.getLoginState(this.phoneId);

    if (login) {
      await this.loadNotifications();
      await this.loadDMs();

      const myAccount = this.state.accounts.get(login);
      this.state.following = myAccount?.following ?? [];

      this.switchView(ChirpApp.VIEWS.TIMELINE);
    } else {
      this.switchView(ChirpApp.VIEWS.AUTH);
    }
  }

  async show(...args) {
    const returnArgs = args[0];
    if (returnArgs?.view === 'edit_profile') {
      if (this._editProfileReturning) return;
      this._editProfileReturning = true;
      this.phoneId = this.widget.currentPhoneId;
      await this.loadAccounts();
      await this.loadPosts();
      await this.getLoginState(this.phoneId);
      this.switchView(ChirpApp.VIEWS.EDIT_PROFILE, {
        socialId: returnArgs.socialId || this.state.me,
        preservedData: returnArgs.preservedData || null,
      });
      this._editProfileReturning = false;
      return;
    }
    if (returnArgs?.view === 'compose') {
      if (this._composeReturning) return;
      this._composeReturning = true;
      this.phoneId = this.widget.currentPhoneId;
      await this.loadAccounts();
      await this.loadPosts();
      await this.getLoginState(this.phoneId);
      this.switchView(ChirpApp.VIEWS.COMPOSE, {
        quoteChirpId: returnArgs.preservedData?.quoteChirpId || null,
        editChirpId: returnArgs.preservedData?.editChirpId || null,
        editReturnView: returnArgs.preservedData?.editReturnView || null,
        editReturnParams: returnArgs.preservedData?.editReturnParams || null,
        preservedData: returnArgs.preservedData || null,
      });
      this._composeReturning = false;
      return;
    }
    if (returnArgs?.view === 'conversation') {
      if (this._conversationReturning) return;
      this._conversationReturning = true;
      this.phoneId = this.widget.currentPhoneId;
      await this.loadAccounts();
      await this.loadPosts();
      await this.loadDMs();
      await this.getLoginState(this.phoneId);
      const preservedData = { ...(returnArgs.preservedData || {}) };
      if (this._pendingDMImage) {
        preservedData.pendingImage = this._pendingDMImage;
        this._pendingDMImage = null;
      }
      this.switchView(ChirpApp.VIEWS.CONVERSATION, {
        otherSocialId: returnArgs.otherSocialId,
        preservedData,
      });
      this._conversationReturning = false;
      return;
    }
    await this.onShow();
  }

  onHide() {
    this.viewParams = {};
    this.viewHistory = [];
  }

  hide() {
    this.onHide();
    super.hide();
  }

  cleanup() {
    super.removeAllListeners();

    this.currentView = ChirpApp.VIEWS.AUTH;
    this.viewParams = {};
    this.viewHistory = [];

    this.state.me = null;
    this.state.loginState = null;
    this.state.postState = {};
    this.state.following = [];
    this.state.accounts = new Map();
    this.state.posts = new Map();
    this.state.dms = {};
    this.state.notifications = [];
    this.state.trends = [];
    this._hasDeferredRealtimeRender = false;
    this._deferredRealtimeFlushArmed = false;
  }

  // -------------------------------------------------------------------
  // View routing
  // -------------------------------------------------------------------

  switchView(viewName, params = {}) {
    if (this.currentView) {
      this.viewHistory.push({
        view: this.currentView,
        params: { ...this.viewParams },
      });
    }

    this._viewChanged = true;
    this.currentView = viewName;
    this.viewParams = params;
    this.render();
  }

  goBack() {
    const prev = this.viewHistory.pop();
    if (prev) {
      this.currentView = prev.view;
      this.viewParams = prev.params;
      this.render();
    } else {
      this.currentView = this.state.me
        ? ChirpApp.VIEWS.TIMELINE
        : ChirpApp.VIEWS.AUTH;
      this.viewParams = {};
      this.render();
    }
  }

  handleBack() {
    if (this.viewHistory.length > 0) {
      this.goBack();
    } else {
      this.widget.switchApp('home');
    }
  }

  // -------------------------------------------------------------------
  // Rendering — shared shell at App level, views supply inner content
  // -------------------------------------------------------------------

  render() {
    const preserveScroll = !this._viewChanged;
    this._viewChanged = false;
    const prevScroll = preserveScroll ? (this.widget?.element?.querySelector('.chirp-main')?.scrollTop ?? 0) : 0;

    const { me, accounts, notifications } = this.state;
    const myAccount = accounts.get(me);
    const view = this.currentView;
    const VIEWS = ChirpApp.VIEWS;

    // Views that use the shared topbar (avatar + title + logo)
    const sharedTopbarViews = [VIEWS.TIMELINE, VIEWS.SEARCH, VIEWS.NOTIFICATIONS, VIEWS.MESSAGES];
    const useSharedTopbar = sharedTopbarViews.includes(view);

    // Views that show bottom nav
    const bottomNavViews = [VIEWS.TIMELINE, VIEWS.SEARCH, VIEWS.NOTIFICATIONS, VIEWS.MESSAGES, VIEWS.PROFILE];
    const showBottomNav = bottomNavViews.includes(view);

    // Views that show FAB
    const showFAB = sharedTopbarViews.includes(view);

    // Page title per view
    const titles = {
      [VIEWS.TIMELINE]: L('home'),
      [VIEWS.SEARCH]: L('explore'),
      [VIEWS.NOTIFICATIONS]: L('notifications'),
      [VIEWS.MESSAGES]: L('messages'),
    };

    // Get inner content from the view-specific renderer
    const innerContent = this._renderView();

    // Nav active state
    const navActive = (name) => {
      const map = { timeline: VIEWS.TIMELINE, search: VIEWS.SEARCH, notifications: VIEWS.NOTIFICATIONS, messages: VIEWS.MESSAGES, profile: VIEWS.PROFILE };
      return map[name] === view ? ' active' : '';
    };

    const unreadNotifs = notifications.filter(n => !n.read).length;

    // Full-screen views (auth, compose, edit-profile, detail, conversation, GM) — no shared shell
    if (!useSharedTopbar && !showBottomNav) {
      this.updateContent(innerContent + `<div class="chirp-lightbox hidden" id="chirp-lightbox"><img /><button class="lb-close" aria-label="close">${renderIcon('close','','width:20px;height:20px')}</button></div>`);
      const mainEl = this.widget?.element?.querySelector('.chirp-main');
      if (mainEl) mainEl.scrollTop = prevScroll;
      this.clearDeferredRealtimeRenderIfSafe();
      return;
    }

    const gmBtnHtml = game.user.isGM ? `<button class="gm-panel-btn" data-action="open-gm-panel">${renderIcon('gear', '', 'width:16px;height:16px')}</button>` : '';

    // View-specific class on the wrapper (e.g. chirp-profile needs CSS hooks)
    const viewClass = view === VIEWS.PROFILE ? ' chirp-view chirp-profile' : '';

    const html = `
<div class="chirp-app${viewClass}">
  ${useSharedTopbar ? `
  <div class="chirp-topbar">
    <button class="avatar-btn" data-action="open-own-profile">
      ${renderAvatar(myAccount, 'sm')}
    </button>
    <div class="page-title">${titles[view] || ''}</div>
    <div class="topbar-right">
      ${gmBtnHtml}
      <div class="chirp-logo">${renderIcon('logo')}</div>
    </div>
  </div>` : ''}
  <div class="chirp-main">
    ${innerContent}
  </div>
  ${showFAB ? `<button class="chirp-fab" id="chirp-fab" aria-label="compose">${renderIcon('feather')}</button>` : ''}
  ${showBottomNav ? `
  <div class="chirp-bottomnav">
    <button class="nav-btn${navActive('timeline')}" data-nav="timeline">${renderIcon(view === VIEWS.TIMELINE ? 'homeFill' : 'home')}</button>
    <button class="nav-btn${navActive('search')}" data-nav="search">${renderIcon('search')}</button>
    <button class="nav-btn${navActive('notifications')}" data-nav="notifications">${renderIcon(view === VIEWS.NOTIFICATIONS ? 'bellFill' : 'bell')}${unreadNotifs ? `<span class="badge">${unreadNotifs}</span>` : ''}</button>
    <button class="nav-btn${navActive('messages')}" data-nav="messages">${renderIcon('mail')}</button>
    <button class="nav-btn${navActive('profile')}" data-nav="profile">${renderIcon('user')}</button>
  </div>` : ''}
  <div class="chirp-toast" id="chirp-toast"></div>
  <div class="chirp-lightbox hidden" id="chirp-lightbox"><img /><button class="lb-close" aria-label="close">${renderIcon('close','','width:20px;height:20px')}</button></div>
</div>`;

    this.updateContent(html);
    const mainEl = this.widget?.element?.querySelector('.chirp-main');
    if (mainEl) mainEl.scrollTop = prevScroll;
    this.clearDeferredRealtimeRenderIfSafe();
  }

  _renderView() {
    switch (this.currentView) {
      case ChirpApp.VIEWS.AUTH: return renderAuthView(this);
      case ChirpApp.VIEWS.TIMELINE: return renderTimelineView(this);
      case ChirpApp.VIEWS.DETAIL: return renderDetailView(this);
      case ChirpApp.VIEWS.PROFILE: return renderProfileView(this);
      case ChirpApp.VIEWS.SEARCH: return renderSearchView(this);
      case ChirpApp.VIEWS.NOTIFICATIONS: return renderNotificationsView(this);
      case ChirpApp.VIEWS.MESSAGES: return renderMessagesView(this);
      case ChirpApp.VIEWS.CONVERSATION: return renderConversationView(this);
      case ChirpApp.VIEWS.COMPOSE: return renderComposeView(this);
      case ChirpApp.VIEWS.EDIT_PROFILE: return renderEditProfileView(this);
      case ChirpApp.VIEWS.FOLLOWS: return renderFollowsView(this);
      case ChirpApp.VIEWS.TREND_DETAIL: return renderTrendDetailView(this);
      case ChirpApp.VIEWS.BOOKMARKS: return renderBookmarksView(this);
      case ChirpApp.VIEWS.GM_ACCOUNTS: return renderGMAccountsView(this);
      case ChirpApp.VIEWS.GM_SETTINGS: return renderGMSettingsView(this);
      case ChirpApp.VIEWS.GM_TRENDS: return renderGMTrendsView(this);
       default: return `<div class="chirp-app"><div class="chirp-empty">${L('loading')}</div></div>`;
    }
  }

  setupListeners() {
    const container = this.element;
    if (!container) return;

    // View-specific listeners
    switch (this.currentView) {
      case ChirpApp.VIEWS.AUTH: attachAuthListeners(this, container); break;
      case ChirpApp.VIEWS.TIMELINE: attachTimelineListeners(this, container); break;
      case ChirpApp.VIEWS.DETAIL: attachDetailListeners(this, container); break;
      case ChirpApp.VIEWS.PROFILE: attachProfileListeners(this, container); break;
      case ChirpApp.VIEWS.COMPOSE: attachComposeListeners(this, container); break;
      case ChirpApp.VIEWS.EDIT_PROFILE: attachEditProfileListeners(this, container); break;
      case ChirpApp.VIEWS.FOLLOWS: attachFollowsListeners(this, container); break;
      case ChirpApp.VIEWS.TREND_DETAIL: attachTrendDetailListeners(this, container); break;
      case ChirpApp.VIEWS.BOOKMARKS: attachBookmarksListeners(this, container); break;
      case ChirpApp.VIEWS.SEARCH: attachSearchListeners(this, container); break;
      case ChirpApp.VIEWS.NOTIFICATIONS: attachNotificationsListeners(this, container); break;
      case ChirpApp.VIEWS.MESSAGES: attachMessagesListeners(this, container); break;
      case ChirpApp.VIEWS.CONVERSATION: attachConversationListeners(this, container); break;
      case ChirpApp.VIEWS.GM_ACCOUNTS: attachGMAccountsListeners(this, container); break;
      case ChirpApp.VIEWS.GM_SETTINGS: attachGMSettingsListeners(this, container); break;
      case ChirpApp.VIEWS.GM_TRENDS: attachGMTrendsListeners(this, container); break;
    }

    // Shared shell listeners (topbar avatar, FAB, GM button, bottom nav)
    container.querySelector('[data-action="open-own-profile"]')?.addEventListener('click', () => {
      this.switchView(ChirpApp.VIEWS.PROFILE, { handle: this.state.me });
    });
    container.querySelector('#chirp-fab')?.addEventListener('click', () => {
      this.switchView(ChirpApp.VIEWS.COMPOSE);
    });
    container.querySelector('[data-action="open-gm-panel"]')?.addEventListener('click', () => {
      if (game.user.isGM) this.switchView(ChirpApp.VIEWS.GM_ACCOUNTS);
    });
    container.querySelectorAll('[data-nav]').forEach(btn => {
      btn.addEventListener('click', () => {
        const navMap = {
          timeline: ChirpApp.VIEWS.TIMELINE,
          search: ChirpApp.VIEWS.SEARCH,
          notifications: ChirpApp.VIEWS.NOTIFICATIONS,
          messages: ChirpApp.VIEWS.MESSAGES,
          profile: ChirpApp.VIEWS.PROFILE,
        };
        const view = navMap[btn.dataset.nav];
        if (view) this.switchView(view, btn.dataset.nav === 'profile' ? { handle: this.state.me } : {});
      });
    });

    // Lightbox — image full-view on click
    const lightbox = this.widget?.element?.querySelector('#chirp-lightbox');
    if (lightbox) {
      const lbImg = lightbox.querySelector('img');
      const closeLb = () => lightbox.classList.add('hidden');
      lightbox.querySelector('.lb-close')?.addEventListener('click', (e) => { e.stopPropagation(); closeLb(); });
      lightbox.addEventListener('click', closeLb);
      lbImg?.addEventListener('click', (e) => e.stopPropagation());

      container.querySelectorAll('.media .m img[data-full-src], .msg-bubble.image img[data-full-src]').forEach(img => {
        img.addEventListener('click', (e) => {
          e.stopPropagation();
          lbImg.src = img.dataset.fullSrc;
          lightbox.classList.remove('hidden');
        });
      });
    }

    container.querySelectorAll('.tag').forEach(el => {
      el.addEventListener('click', (e) => {
        e.stopPropagation();
        const tag = el.textContent.trim().replace(/^#/, '');
        if (tag) this.switchView(ChirpApp.VIEWS.TREND_DETAIL, { trendName: `#${tag}` });
      });
    });

    container.querySelectorAll('.mention').forEach(el => {
      el.addEventListener('click', (e) => {
        e.stopPropagation();
        const handle = el.textContent.trim().replace(/^@/, '');
        if (handle) this.switchView(ChirpApp.VIEWS.PROFILE, { handle });
      });
    });
  }

  // -------------------------------------------------------------------
  // Toast
  // -------------------------------------------------------------------

  showToast(message, duration = 2000) {
    if (this.widget?.showToastNotification) {
      this.widget.showToastNotification(message, duration);
    } else {
      ui.notifications.info(message);
    }
  }
}
