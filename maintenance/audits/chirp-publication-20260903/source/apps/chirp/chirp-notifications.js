import { renderIcon, renderAvatar } from './chirp-shared.js';
import { L } from './chirp-utils.js';

const KIND_ICONS = {
  like: 'heart',
  rechirp: 'rechirp',
  follow: 'user',
  reply: 'reply',
  mention: 'reply',
  alert: 'bell',
};

export function renderNotificationsView(app) {
  const { notifications, accounts } = app.state;

   if (!notifications.length) {
     return `<div class="chirp-empty">${L('allCaughtUp')}</div>`;
  }

  const notifsHtml = notifications.slice().reverse().map(n => {
    const fromAccount = accounts.get(n.fromSocialId);
    if (!fromAccount) return '';
    const iconName = KIND_ICONS[n.type] || 'bell';

    // Resolve snippet from the chirp if applicable
    let snippetText = '';
    if (n.chirpId) {
      const chirp = app.state.posts.get(n.chirpId);
      snippetText = chirp ? (chirp.content || '').slice(0, 60) : '';
    }

     const text = n.type === 'like' ? L('likedYourChirp')
       : n.type === 'rechirp' ? L('rechirpedYourChirp')
       : n.type === 'follow' ? L('followedYou')
       : n.type === 'reply' ? L('repliedToYourChirp')
        : n.type === 'alert' ? L('sentAlert')
        : L('mentionedYou');

    return `
<div class="chirp-notif${n.read ? '' : ' unread'}" data-kind="${n.type}" data-notif-id="${n.id}" data-from="${n.fromSocialId}" ${n.chirpId ? `data-chirp-id="${n.chirpId}"` : ''}>
  <div class="icon-col">${renderIcon(iconName, '', n.type === 'like' ? 'fill:currentColor' : '')}</div>
  <div class="body-col">
    <div class="avatars-row">${renderAvatar(fromAccount, 'sm')}</div>
    <div class="text"><strong>${fromAccount.name}</strong> ${text}</div>
    ${snippetText ? `<div class="snippet">${snippetText}</div>` : ''}
  </div>
</div>`;
  }).join('');

  return notifsHtml;
}

export function attachNotificationsListeners(app, container) {
  const VIEWS = app.constructor.VIEWS;

  if (app.state.me && app.state.notifications.some(n => !n.read)) {
    app.socket.executeAsGM('chirp_markNotifsRead', { socialId: app.state.me }).then(() => {
      app.state.notifications = app.state.notifications.map(n => ({ ...n, read: true }));
      app.render();
    });
  }

  container.querySelectorAll('.chirp-notif').forEach(el => {
    el.addEventListener('click', () => {
      const { chirpId, from } = el.dataset;
      if (chirpId) app.switchView(VIEWS.DETAIL, { chirpId });
      else if (from) app.switchView(VIEWS.PROFILE, { handle: from });
    });
  });
}
