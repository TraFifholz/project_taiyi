import { renderIcon, renderAvatar, renderByline, renderActionBar, renderMediaGrid, renderAlertLabel, computeReplyCounts, sortFeedItems } from './chirp-shared.js';
import { formatCount, renderContent, L } from './chirp-utils.js';
import { handleInteraction } from './chirp-interactions.js';
import { showMoreMenu } from './chirp-timeline.js';

function resolveAccount(app, handle) {
  return app.state.accounts.get(handle)
    || Array.from(app.state.accounts.values()).find(a => a.handle === handle || a.socialId === handle);
}

function getTabPosts(app, account, tab) {
  const allPosts = Array.from(app.state.posts.values());
  const userPosts = allPosts.filter(p => p.authorSocialId === account.socialId);

  switch (tab) {
    case 'replies': {
      const replies = userPosts
        .filter(p => p.replyTo)
        .map(p => ({ post: p, rechirpedBy: null, parentId: p.replyTo }));
      const rts = allPosts
        .filter(p => p.rechirps?.includes(account.socialId) && p.authorSocialId !== account.socialId && !p.replyTo)
        .map(p => ({ post: p, rechirpedBy: account.socialId, parentId: null }));
      return sortFeedItems([...replies, ...rts]);
    }
    case 'media':
      return sortFeedItems(userPosts.filter(p => p.media?.length && !p.replyTo).map(p => ({ post: p, rechirpedBy: null })));
    case 'likes':
      return sortFeedItems(
        allPosts
          .filter(p => p.likes?.includes(account.socialId))
          .map(p => ({ post: p, rechirpedBy: null }))
      );
    default: {
      const own = userPosts.filter(p => !p.replyTo).map(p => ({ post: p, rechirpedBy: null }));
      const rts = allPosts
        .filter(p => p.rechirps?.includes(account.socialId) && p.authorSocialId !== account.socialId && !p.replyTo)
        .map(p => ({ post: p, rechirpedBy: account.socialId }));
      return sortFeedItems([...own, ...rts]);
    }
  }
}

function renderProfilePostCard(post, accounts, mySocialId, isFirst = false, rechirpedBy = null, replyCounts = {}, posts = null) {
  const author = accounts.get(post.authorSocialId);
  if (!author) return '';

  const rtHeader = rechirpedBy
    ? `<div class="chirp-rechirp-header">${renderIcon('rechirp')}<span>${accounts.get(rechirpedBy)?.name || rechirpedBy} rechirped</span></div>`
    : '';

  let parentHtml = '';
  if (post.replyTo && posts) {
    const ancestors = [];
    let walkId = post.replyTo;
    while (walkId) {
      const anc = posts.get(walkId);
      if (!anc) break;
      ancestors.unshift(anc);
      walkId = anc.replyTo;
    }
    parentHtml = ancestors.map(anc => {
      const aAuthor = accounts.get(anc.authorSocialId);
      if (!aAuthor) return '';
      return `
<div class="chirp-post reply-parent-card${anc.isAlert ? ' alert' : ''}" data-chirp-id="${anc.id}">
  <div class="avatar-col">
    ${renderAvatar(aAuthor)}
    <div class="thread-line"></div>
  </div>
  <div class="body-col">
    ${anc.isAlert ? renderAlertLabel() : ''}
    ${renderByline(aAuthor, anc.timestamp)}
    ${anc.content ? `<div class="content">${renderContent(anc.content)}</div>` : ''}
    ${anc.editedAt ? `<div class="chirp-edited">${L('edited')}</div>` : ''}
    ${anc.media?.length ? renderMediaGrid(anc.media) : ''}
  </div>
</div>`;
    }).join('');
  }

  return `
${rtHeader}${parentHtml}
<div class="chirp-post${isFirst && !rechirpedBy && !parentHtml ? ' first' : ''}${post.isAlert ? ' alert' : ''}" data-chirp-id="${post.id}"${rechirpedBy ? ' data-rechirped="true"' : ''}>
  <div class="avatar-col" data-action="open-profile" data-handle="${author.handle}">
    ${renderAvatar(author)}
  </div>
  <div class="body-col">
    ${post.isAlert ? renderAlertLabel() : ''}
    ${renderByline(author, post.timestamp, true)}
     ${post.replyTo ? `<div class="content" style="color:var(--text-dim);font-size:11px">${L('replyingToChirp')}</div>` : ''}
    ${post.content ? `<div class="content">${renderContent(post.content)}</div>` : ''}
    ${post.editedAt ? `<div class="chirp-edited">${L('edited')}</div>` : ''}
    ${post.media?.length ? renderMediaGrid(post.media) : ''}
    ${renderActionBar(post, mySocialId, post.id, replyCounts[post.id] || 0)}
  </div>
</div>`;
}

export function renderProfileView(app) {
  const handle = app.viewParams.handle;
  const account = resolveAccount(app, handle);
   if (!account) {
     return `<div class="chirp-app chirp-view"><div class="chirp-empty">${L('accountNotFound')}</div></div>`;
   }

  const tab = app.viewParams.profileTab || 'chirps';
  const isMe = account.socialId === app.state.me;
  const isFollowing = app.state.following.includes(account.socialId);
  const userPosts = Array.from(app.state.posts.values()).filter(p => p.authorSocialId === account.socialId);
  const tabPosts = getTabPosts(app, account, tab);
  const { accounts, postState } = app.state;

  const followersCount = (account.followers?.length || 0) + (account.fakeFollowers || 0);
  const followingCount = (account.following?.length || 0) + (account.fakeFollowing || 0);

   let followBtnLabel, followBtnClass;
   if (isMe) {
     followBtnLabel = L('editProfile');
     followBtnClass = 'follow-btn following';
   } else if (isFollowing) {
     followBtnLabel = L('following');
     followBtnClass = 'follow-btn following';
   } else {
     followBtnLabel = L('follow');
     followBtnClass = 'follow-btn';
   }

  const profilePageSize = 20;
  const displayCount = app.viewParams._profileDisplayCount || profilePageSize;
  const page = tabPosts.slice(0, displayCount);
  const hasMore = tabPosts.length > displayCount;

  const replyCounts = computeReplyCounts(app.state.posts);

   const postsHtml = page.length === 0
     ? `<div class="chirp-empty">${L('nothingHereYet')}</div>`
      : page.map((item, i) => renderProfilePostCard(item.post, accounts, app.state.me, i === 0, item.rechirpedBy, replyCounts, tab === 'replies' ? app.state.posts : null)).join('');

  const bannerStyle = account.bannerImage
    ? `background:url(${account.bannerImage}) center/cover no-repeat`
    : account.bannerColor
    ? `background:linear-gradient(135deg,${account.bannerColor},color-mix(in oklab,${account.bannerColor},black 50%))`
    : '';

  return `
  <div class="detail-header">
    <button class="back" data-action="back" aria-label="back">${renderIcon('back')}</button>
    <div style="display:flex;flex-direction:column">
      <div style="font-weight:700;font-size:13px">${account.name}</div>
      <div style="font-size:10px;color:var(--text-dim)">${formatCount(userPosts.length)} chirps</div>
    </div>
  </div>
  <div class="banner" style="${bannerStyle}"></div>
  <div class="profile-top">
    ${renderAvatar(account, 'lg')}
    <div class="profile-actions">
      ${isMe ? `<button class="dm-btn" data-action="open-bookmarks" aria-label="${L('viewBookmarks')}" title="${L('viewBookmarks')}">${renderIcon('bookmark', '', 'width:16px;height:16px')}</button>` : `<button class="dm-btn" data-action="open-dm" data-social-id="${account.socialId}" aria-label="Message">${renderIcon('mail', '', 'width:16px;height:16px')}</button>`}
      <button class="${followBtnClass}" data-action="${isMe ? 'edit-profile' : 'toggle-follow'}" data-social-id="${account.socialId}">
        ${followBtnLabel}
      </button>
    </div>
    <div class="display-name">
      ${account.name}
      ${account.verified ? renderIcon('verified', 'verified', 'width:14px;height:14px') : ''}
    </div>
    <div class="handle">@${account.handle}</div>
    ${account.bio ? `<div class="bio">${account.bio}</div>` : ''}
    <div class="meta">
      ${account.location ? `<span class="item">${renderIcon('location', '', 'width:12px;height:12px')} ${account.location}</span>` : ''}
      ${account.website ? `<span class="item">${renderIcon('link', '', 'width:12px;height:12px')} ${account.website}</span>` : ''}
      ${account.joinedDate ? `<span class="item">${renderIcon('calendar', '', 'width:12px;height:12px')} ${account.joinedDate}</span>` : ''}
    </div>
     <div class="stats">
       <span class="stat-link" data-action="open-follows" data-tab="following"><strong>${formatCount(followingCount)}</strong> ${L('following')}</span>
       <span class="stat-link" data-action="open-follows" data-tab="followers"><strong>${formatCount(followersCount)}</strong> ${L('followers')}</span>
     </div>
  </div>
   <div class="profile-tabs">
     <button class="pt ${tab === 'chirps' ? 'active' : ''}" data-profile-tab="chirps">${L('chirps')}</button>
     <button class="pt ${tab === 'replies' ? 'active' : ''}" data-profile-tab="replies">${L('replies')}</button>
     <button class="pt ${tab === 'media' ? 'active' : ''}" data-profile-tab="media">${L('media')}</button>
     <button class="pt ${tab === 'likes' ? 'active' : ''}" data-profile-tab="likes">${L('likes')}</button>
   </div>
  <div id="chirp-profile-posts">${postsHtml}</div>
  ${hasMore ? '<div class="chirp-load-more" id="chirp-profile-sentinel"></div>' : ''}`;
}

export function attachProfileListeners(app, container) {
  const VIEWS = app.constructor.VIEWS;

  container.querySelector('[data-action="back"]')?.addEventListener('click', () => {
    app.goBack();
  });

  container.querySelector('[data-action="toggle-follow"]')?.addEventListener('click', async (e) => {
    const socialId = e.currentTarget.dataset.socialId;
    const result = await app.socket.executeAsGM('chirp_toggleFollow', {
      fromSocialId: app.state.me,
      toSocialId: socialId,
    });
    if (result?.success) {
      await app.loadAccounts();
      const myAccount = app.state.accounts.get(app.state.me);
      app.state.following = myAccount?.following ?? [];
      app.render();
    }
  });

  container.querySelector('[data-action="edit-profile"]')?.addEventListener('click', () => {
    app.switchView(VIEWS.EDIT_PROFILE, { socialId: app.state.me });
  });

  container.querySelector('[data-action="open-dm"]')?.addEventListener('click', (e) => {
    const socialId = e.currentTarget.dataset.socialId;
    app.switchView(VIEWS.CONVERSATION, { otherSocialId: socialId });
  });

  container.querySelector('[data-action="open-bookmarks"]')?.addEventListener('click', () => {
    app.switchView(VIEWS.BOOKMARKS);
  });

  container.querySelectorAll('[data-action="open-follows"]').forEach(el => {
    el.addEventListener('click', () => {
      const handle = app.viewParams.handle;
      app.switchView(VIEWS.FOLLOWS, { handle, followsTab: el.dataset.tab });
    });
  });

  container.querySelectorAll('[data-profile-tab]').forEach(btn => {
    btn.addEventListener('click', () => {
      app.viewParams.profileTab = btn.dataset.profileTab;
      app.viewParams._profileDisplayCount = 20;
      app.render();
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

  container.querySelectorAll('[data-action][data-chirp-id]').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const { action, chirpId } = btn.dataset;
      if (!app.state.me) return;

      if (action === 'reply') {
        app.switchView(VIEWS.DETAIL, { chirpId });
        return;
      }
      if (action === 'share') { app.showToast('Link copied'); return; }

      await handleInteraction(app, action, chirpId);
    });
  });

  const sentinel = container.querySelector('#chirp-profile-sentinel');
  if (sentinel) {
    const scrollArea = app.widget?.element?.querySelector('.chirp-main');
    if (scrollArea) {
      const observer = new IntersectionObserver((entries) => {
        if (entries[0].isIntersecting) {
          observer.disconnect();
          app.viewParams._profileDisplayCount = (app.viewParams._profileDisplayCount || 20) + 20;
          app.render();
        }
      }, { root: scrollArea, threshold: 0 });
      observer.observe(sentinel);
    }
  }
}

const BANNER_CHOICES = ['#1d9bf0', '#3a7bd5', '#d97757', '#7a5cd9', '#4abf8a', '#d94a84', '#1a1a22'];
const AVATAR_CHOICES = [
  ['#d97757', '#2a1a0e'], ['#3a7bd5', '#0a1828'], ['#7a5cd9', '#150e28'],
  ['#d94a84', '#2a0e1d'], ['#4abf8a', '#0a1f17'], ['#d9a84a', '#282010'],
  ['#4ad0d9', '#0a2426'], ['#b84ad9', '#220e28'],
];

export function renderEditProfileView(app) {
   const socialId = app.viewParams.socialId || app.state.me;
   const acc = app.state.accounts.get(socialId);
   if (!acc) return `<div class="chirp-app"><div class="chirp-empty">${L('accountNotFound')}</div></div>`;

  const preserved = app.viewParams.preservedData || {};
  const [pal0, pal1] = acc.profilePal || ['#3a7bd5', '#0a1828'];
  const banner = acc.bannerColor || '#1d9bf0';
  const initials = acc.name.split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase();

  const currentProfileImage = preserved.profileImage || acc.profileImage;
  const currentBannerImage = preserved.bannerImage || acc.bannerImage;

  const editOverlay = `<button class="ep-avatar-edit" id="ep-change-avatar" aria-label="change avatar">${renderIcon('image', '', 'width:12px;height:12px')}</button>`;
  const avatarDisplay = currentProfileImage
    ? `<div class="ep-avatar" style="background: url(${currentProfileImage}) center/cover no-repeat">${editOverlay}</div>`
    : `<div class="ep-avatar" style="background: linear-gradient(135deg, ${pal0}, ${pal1}); color: #fff">${initials}${editOverlay}</div>`;

  const bannerDisplay = currentBannerImage
    ? `style="background: url(${currentBannerImage}) center/cover no-repeat"`
    : `style="background: linear-gradient(135deg, ${banner}, ${pal0})"`;

  const nameVal = preserved.name !== undefined ? preserved.name : (acc.name || '');
  const bioVal = preserved.bio !== undefined ? preserved.bio : (acc.bio || '');
  const locVal = preserved.location !== undefined ? preserved.location : (acc.location || '');
  const webVal = preserved.website !== undefined ? preserved.website : (acc.website || '');
  const isDirty = Object.keys(preserved).length > 0;

  return `
<div class="chirp-app chirp-editprofile">
   <div class="ep-top">
     <button class="ep-close" id="ep-close" aria-label="close">${renderIcon('close', '', 'width:18px;height:18px')}</button>
     <div class="ep-title">${L('editProfile')}</div>
     <button class="ep-save" id="ep-save" ${isDirty ? '' : 'disabled'}>${L('save')}</button>
   </div>
  <div class="ep-body">
    <div class="ep-banner" ${bannerDisplay}>
      <button class="ep-banner-edit" id="ep-change-banner" aria-label="change banner">${renderIcon('image', '', 'width:16px;height:16px')}</button>
    </div>
    <div class="ep-avatar-row">
      ${avatarDisplay}
    </div>

     <div class="ep-section">
       <div class="ep-section-title">${L('theme')}</div>
       <div class="ep-swatch-label">${L('banner')}</div>
      <div class="ep-swatches" id="ep-banner-swatches">
        ${BANNER_CHOICES.map(c => `<button class="ep-swatch${banner === c ? ' active' : ''}" data-banner="${c}" style="background:${c}"></button>`).join('')}
      </div>
       <div class="ep-swatch-label" style="margin-top:10px">${L('avatarGradient')}</div>
      <div class="ep-swatches" id="ep-avatar-swatches">
        ${AVATAR_CHOICES.map(([a, b]) => `<button class="ep-swatch${pal0 === a && pal1 === b ? ' active' : ''}" data-pal0="${a}" data-pal1="${b}" style="background: linear-gradient(135deg, ${a}, ${b})"></button>`).join('')}
      </div>
    </div>

     <div class="ep-field">
       <div class="ep-field-head">
         <label>${L('name')}</label>
         <span class="ep-count" id="ep-name-count">0 / 50</span>
       </div>
      <input type="text" id="ep-name" value="${nameVal}" maxlength="60" />
    </div>
     <div class="ep-field">
       <div class="ep-field-head">
         <label>${L('bio')}</label>
         <span class="ep-count" id="ep-bio-count">0 / 160</span>
       </div>
       <textarea id="ep-bio" rows="3" placeholder="${L('bioPlaceholder')}">${bioVal}</textarea>
     </div>
     <div class="ep-field">
       <div class="ep-field-head">
         <label>${L('location')}</label>
         <span class="ep-count" id="ep-loc-count">0 / 30</span>
       </div>
       <div class="ep-input-wrap">
         ${renderIcon('location', '', 'width:14px;height:14px')}
         <input type="text" id="ep-location" value="${locVal}" placeholder="${L('locationPlaceholder')}" maxlength="35" />
       </div>
     </div>
     <div class="ep-field">
       <div class="ep-field-head"><label>${L('website')}</label></div>
       <div class="ep-input-wrap">
         ${renderIcon('link', '', 'width:14px;height:14px')}
         <input type="text" id="ep-website" value="${webVal}" placeholder="domain.tld" />
       </div>
     </div>

     <div class="ep-section">
       <div class="ep-section-title">${L('account')}</div>
       <button class="ep-row-link">
         <span>${L('username')}</span>
         <span class="val">@${acc.handle}</span>
       </button>
       <button class="ep-row-link">
         <span>${L('verification')}</span>
         <span class="val">${acc.verified ? L('verified') : L('notVerified')}</span>
       </button>
       <button class="ep-row-link danger" id="ep-deactivate">
         <span>${L('deactivateAccount')}</span>
       </button>
     </div>
  </div>
</div>`;
}

export function attachEditProfileListeners(app, container) {
  const VIEWS = app.constructor.VIEWS;
  const socialId = app.viewParams.socialId || app.state.me;
  const acc = app.state.accounts.get(socialId);
  if (!acc) return;

  const preserved = app.viewParams.preservedData || {};
  let patch = { ...preserved };

  function markDirty() {
    container.querySelector('#ep-save').disabled = false;
  }

  function getCurrentFormData() {
    return {
      name: container.querySelector('#ep-name')?.value,
      bio: container.querySelector('#ep-bio')?.value,
      location: container.querySelector('#ep-location')?.value,
      website: container.querySelector('#ep-website')?.value,
      profileImage: patch.profileImage || undefined,
      bannerImage: patch.bannerImage || undefined,
    };
  }

  if (Object.keys(preserved).length > 0) markDirty();

  container.querySelector('#ep-close')?.addEventListener('click', () => app.goBack());

  container.querySelector('#ep-change-avatar')?.addEventListener('click', () => {
    const currentData = getCurrentFormData();
    app.selectImageSource(
      (imagePath) => {
        currentData.profileImage = imagePath;
        setTimeout(() => {
          app.switchView(app.constructor.VIEWS.EDIT_PROFILE, {
            socialId: app.viewParams.socialId || app.state.me,
            preservedData: currentData,
          });
        }, 50);
      },
      '',
      { view: 'edit_profile', socialId: app.viewParams.socialId || app.state.me, preservedData: currentData }
    );
  });

  container.querySelector('#ep-change-banner')?.addEventListener('click', () => {
    const currentData = getCurrentFormData();
    app.selectImageSource(
      (imagePath) => {
        currentData.bannerImage = imagePath;
        setTimeout(() => {
          app.switchView(app.constructor.VIEWS.EDIT_PROFILE, {
            socialId: app.viewParams.socialId || app.state.me,
            preservedData: currentData,
          });
        }, 50);
      },
      '',
      { view: 'edit_profile', socialId: app.viewParams.socialId || app.state.me, preservedData: currentData }
    );
  });

  function updateCounter(inputEl, countEl, max) {
    countEl.textContent = `${inputEl.value.length} / ${max}`;
    countEl.classList.toggle('over', inputEl.value.length > max);
    countEl.classList.toggle('warn', inputEl.value.length > max * 0.875 && inputEl.value.length <= max);
  }

  const nameInput = container.querySelector('#ep-name');
  const nameCount = container.querySelector('#ep-name-count');
  if (nameInput && nameCount) {
    updateCounter(nameInput, nameCount, 50);
    nameInput.addEventListener('input', () => {
      updateCounter(nameInput, nameCount, 50);
      patch.name = nameInput.value;
      markDirty();
    });
  }

  const bioInput = container.querySelector('#ep-bio');
  const bioCount = container.querySelector('#ep-bio-count');
  if (bioInput && bioCount) {
    updateCounter(bioInput, bioCount, 160);
    bioInput.addEventListener('input', () => {
      updateCounter(bioInput, bioCount, 160);
      patch.bio = bioInput.value;
      markDirty();
    });
  }

  const locInput = container.querySelector('#ep-location');
  const locCount = container.querySelector('#ep-loc-count');
  if (locInput && locCount) {
    updateCounter(locInput, locCount, 30);
    locInput.addEventListener('input', () => {
      updateCounter(locInput, locCount, 30);
      patch.location = locInput.value;
      markDirty();
    });
  }

  const webInput = container.querySelector('#ep-website');
  webInput?.addEventListener('input', () => {
    patch.website = webInput.value;
    markDirty();
  });

  container.querySelectorAll('#ep-banner-swatches .ep-swatch').forEach(btn => {
    btn.addEventListener('click', () => {
      container.querySelectorAll('#ep-banner-swatches .ep-swatch').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      patch.bannerColor = btn.dataset.banner;
      markDirty();
    });
  });

  container.querySelectorAll('#ep-avatar-swatches .ep-swatch').forEach(btn => {
    btn.addEventListener('click', () => {
      container.querySelectorAll('#ep-avatar-swatches .ep-swatch').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      patch.profilePal = [btn.dataset.pal0, btn.dataset.pal1];
      markDirty();
    });
  });

   container.querySelector('#ep-save')?.addEventListener('click', async () => {
     if (!Object.keys(patch).length) return;
     const result = await app.socket.executeAsGM('chirp_updateProfile', { socialId, patch });
     if (result?.success) {
       await app.loadAccounts();
       app.showToast(L('profileUpdated'));
       app.switchView(VIEWS.PROFILE, { handle: socialId });
     }
   });

  container.querySelector('#ep-deactivate')?.addEventListener('click', async () => {
    const result = await app.socket.executeAsGM('chirp_deleteAccount', { socialId, phoneId: app.phoneId });
    if (result?.success) {
      app.state.me = null;
      app.state.loginState = null;
      app.switchView(VIEWS.AUTH);
    }
  });
}
