import { renderIcon, renderAvatar } from './chirp-shared.js';
import { formatCount, L } from './chirp-utils.js';

export function renderFollowsView(app) {
  const handle = app.viewParams.handle;
  const tab = app.viewParams.followsTab || 'followers';

  const account = app.state.accounts.get(handle)
    || Array.from(app.state.accounts.values()).find(a => a.handle === handle || a.socialId === handle);

   if (!account) {
     return `<div class="chirp-app chirp-follows"><div class="chirp-empty">${L('accountNotFound')}</div></div>`;
   }

  const followersList = (account.followers || []).map(id => app.state.accounts.get(id)).filter(Boolean);
  const followingList = (account.following || []).map(id => app.state.accounts.get(id)).filter(Boolean);
  const list = tab === 'followers' ? followersList : followingList;

   const listHtml = list.length === 0
     ? `<div class="chirp-empty">${L('noOneHereYet')}</div>`
     : list.map(u => {
        const isMe = u.socialId === app.state.me;
        const isFollowing = app.state.following.includes(u.socialId);
         const followBtn = isMe ? '' : `
           <button class="fr-follow${isFollowing ? ' following' : ''}"
                   data-action="toggle-follow" data-social-id="${u.socialId}">
             ${isFollowing ? L('following') : L('follow')}
           </button>`;

        return `
        <div class="follow-row" data-social-id="${u.socialId}">
          ${renderAvatar(u)}
          <div class="fr-body">
            <div class="fr-head">
              <span class="fr-name">
                ${u.name}
                ${u.verified ? renderIcon('verified', 'verified', 'width:11px;height:11px') : ''}
              </span>
              ${followBtn}
            </div>
            <div class="fr-handle">@${u.handle}</div>
            ${u.bio ? `<div class="fr-bio">${u.bio}</div>` : ''}
          </div>
        </div>`;
      }).join('');

  return `
<div class="chirp-app chirp-follows">
  <div class="follows-header">
    <button class="back" data-action="back" aria-label="back">${renderIcon('back')}</button>
    <div class="follows-peer">
      <div class="follows-name">
        ${account.name}
        ${account.verified ? renderIcon('verified', 'verified', 'width:12px;height:12px') : ''}
      </div>
      <div class="follows-handle">@${account.handle}</div>
    </div>
  </div>
  <div class="follows-tabs">
     <button class="ft${tab === 'followers' ? ' active' : ''}" data-follows-tab="followers">
       <span class="n">${formatCount((account.followers?.length || 0) + (account.fakeFollowers || 0))}</span>
       <span class="l">${L('followers')}</span>
     </button>
     <button class="ft${tab === 'following' ? ' active' : ''}" data-follows-tab="following">
       <span class="n">${formatCount((account.following?.length || 0) + (account.fakeFollowing || 0))}</span>
       <span class="l">${L('following')}</span>
     </button>
  </div>
  <div class="follows-list">
    ${listHtml}
  </div>
</div>`;
}

export function attachFollowsListeners(app, container) {
  const VIEWS = app.constructor.VIEWS;

  container.querySelector('[data-action="back"]')?.addEventListener('click', () => {
    app.goBack();
  });

  container.querySelectorAll('[data-follows-tab]').forEach(btn => {
    btn.addEventListener('click', () => {
      app.viewParams.followsTab = btn.dataset.followsTab;
      app.render();
    });
  });

  container.querySelectorAll('[data-action="toggle-follow"]').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const socialId = btn.dataset.socialId;
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
  });

  container.querySelectorAll('.follow-row').forEach(row => {
    row.addEventListener('click', () => {
      app.switchView(VIEWS.PROFILE, { handle: row.dataset.socialId });
    });
  });
}
