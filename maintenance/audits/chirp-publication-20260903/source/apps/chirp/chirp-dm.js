import { renderIcon, renderAvatar } from './chirp-shared.js';
import { timeAgo, escapeHtml, formatTime, L } from './chirp-utils.js';

const DM_KEY_SEP = '<>';

function getConvoKey(id1, id2) {
  return [id1, id2].sort().join(DM_KEY_SEP);
}

function renderMsgBubble(m) {
  const parts = [];
  if (m.image) {
    parts.push(`<div class="msg-bubble image"><img src="${m.image}" loading="lazy" data-full-src="${m.image}" /></div>`);
  }
  if (m.text) {
    parts.push(`<div class="msg-bubble">${escapeHtml(m.text)}</div>`);
  }
  return parts.join('');
}

function snippetForLast(last, mePrefix) {
  if (last.text) return `${mePrefix}${escapeHtml(last.text)}`;
  if (last.image) return `${mePrefix}📷 ${L('imageAttachment')}`;
  return mePrefix;
}

export function renderMessagesView(app) {
  const { dms, accounts, me } = app.state;
  const dmRead = app.state.dmRead || {};

  const conversations = Object.entries(dms).map(([key, msgs]) => {
    if (!msgs.length) return null;
    const [idA, idB] = key.split(DM_KEY_SEP);
    const otherSocialId = idA === me ? idB : idA;
    const acc = accounts.get(otherSocialId);
    const last = msgs[msgs.length - 1];
    const readTs = dmRead[`${key}::${me}`] || 0;
    const unread = last.fromSocialId !== me && last.timestamp > readTs;
    return { key, otherSocialId, acc, last, unread };
  }).filter(Boolean).sort((a, b) => b.last.timestamp - a.last.timestamp);

   const listHtml = conversations.length === 0
     ? `<div class="chirp-empty">${L('noMessages')}</div>`
    : conversations.map(c => {
      if (!c.acc) return '';
      return `
<div class="chirp-dm-row" data-convo-key="${c.key}" data-other-id="${c.otherSocialId}" style="cursor:pointer">
  ${renderAvatar(c.acc)}
  <div class="dm-body">
    <div class="dm-head">
      <span class="dm-name">${c.acc.name}${c.acc.verified ? ` ${renderIcon('verified','verified','width:12px;height:12px')}` : ''}</span>
      <span class="dm-handle">@${c.acc.handle}</span>
      <span class="dm-dot">&middot;</span>
      <span class="dm-time">${timeAgo(c.last.timestamp)}</span>
    </div>
     <div class="dm-snippet${c.unread ? ' unread' : ''}">${snippetForLast(c.last, c.last.fromSocialId === me ? L('youPrefix') : '')}</div>
  </div>
  ${c.unread ? '<div class="dm-unread-dot"></div>' : ''}
</div>`;
    }).join('');

  return `
    <div class="chirp-search-bar">
      <div class="wrap">
        ${renderIcon('search')}
         <input type="text" class="field" placeholder="${L('searchDMs')}" />
      </div>
    </div>
    ${listHtml}`;
}

export function attachMessagesListeners(app, container) {
  const VIEWS = app.constructor.VIEWS;

  container.querySelectorAll('.chirp-dm-row').forEach(row => {
    row.addEventListener('click', () => {
      app.switchView(VIEWS.CONVERSATION, { otherSocialId: row.dataset.otherId });
    });
  });
}

export function renderConversationView(app) {
  const { me, accounts, dms } = app.state;
  const otherSocialId = app.viewParams.otherSocialId;
  const otherAcc = accounts.get(otherSocialId);
   if (!otherAcc) return `<div class="chirp-app"><div class="chirp-empty">${L('contactNotFound')}</div></div>`;

  const key = getConvoKey(me, otherSocialId);
  const msgs = dms[key] || [];

  // Group messages by sender (5 min threshold)
  const groups = [];
  msgs.forEach(m => {
    const last = groups[groups.length - 1];
    if (last && last.fromSocialId === m.fromSocialId && (m.timestamp - last.msgs[last.msgs.length - 1].timestamp) < 5 * 60 * 1000) {
      last.msgs.push(m);
    } else {
      groups.push({ fromSocialId: m.fromSocialId, msgs: [m] });
    }
  });

  const stamp = (ts) => formatTime(ts);

  const groupsHtml = groups.map(g => {
    const isOut = g.fromSocialId === me;
    const lastTs = g.msgs[g.msgs.length - 1].timestamp;
    const bubblesHtml = g.msgs.map(m => renderMsgBubble(m)).join('');
    return `
<div class="msg-group ${isOut ? 'out' : 'in'}" data-sender="${g.fromSocialId}" data-ts="${lastTs}">
  ${bubblesHtml}
  <div class="msg-stamp">${stamp(lastTs)}</div>
</div>`;
  }).join('');

  const pendingImage = app._pendingDMImage || app.viewParams.preservedData?.pendingImage || null;
  const previewText = app.viewParams.preservedData?.text || '';

  return `
<div class="chirp-app chirp-convo">
  <div class="convo-header">
    <button class="back" id="convo-back">${renderIcon('back')}</button>
    <div class="convo-peer" data-action="open-profile" data-handle="${otherSocialId}" style="cursor:pointer">
      ${renderAvatar(otherAcc, 'sm')}
      <div class="peer-name">${otherAcc.name}${otherAcc.verified ? ` ${renderIcon('verified','verified','width:11px;height:11px')}` : ''}</div>
    </div>
    <button class="convo-info" aria-label="info">${renderIcon('more','','width:16px;height:16px')}</button>
  </div>
  <div class="convo-scroll" id="convo-scroll">
    <div class="convo-intro" data-action="open-profile" data-handle="${otherSocialId}">
      ${renderAvatar(otherAcc, 'lg')}
      <div class="intro-name">${otherAcc.name}</div>
      <div class="intro-handle">@${otherAcc.handle} · ${otherAcc.joinedDate || ''}</div>
      <div class="intro-bio">${otherAcc.bio || ''}</div>
    </div>
    ${groupsHtml}
  </div>
  <div class="convo-composer">
    <button class="c-tool" id="dm-attach" aria-label="image">${renderIcon('image','','width:16px;height:16px')}</button>
    <button class="c-tool" aria-label="gif" disabled>${renderIcon('gif','','width:16px;height:16px')}</button>
    <div class="dm-input-wrap">
      ${pendingImage ? `<div class="dm-image-preview"><img src="${pendingImage}" /><button class="dm-image-remove" id="dm-image-remove" aria-label="remove">${renderIcon('close','','width:10px;height:10px')}</button></div>` : ''}
      <input type="text" id="dm-input" placeholder="${L('startNewMessage')}" value="${escapeHtml(previewText)}" />
    </div>
    <button class="c-send" id="dm-send" ${(!previewText && !pendingImage) ? 'disabled' : ''}>${renderIcon('sendArrow','','width:15px;height:15px')}</button>
  </div>
</div>`;
}

export function tryAppendDM(app, convoKey, newMsgs) {
  const el = app.widget?.element;
  if (!el) return false;
  const scroll = el.querySelector('#convo-scroll');
  if (!scroll) return false;

  const oldCount = app._dmRenderedCount || 0;
  if (newMsgs.length <= oldCount) return false;

  const me = app.state.me;
  const stamp = (ts) => formatTime(ts);

  const wasNearBottom = scroll.scrollHeight - scroll.clientHeight <= scroll.scrollTop + 100;

  const input = el.querySelector('#dm-input');
  const inputVal = input?.value || '';
  const hadFocus = document.activeElement === input;

  const added = newMsgs.slice(oldCount);
  const lastGroup = scroll.querySelector('.msg-group:last-of-type');
  const lastGroupSender = lastGroup?.dataset?.sender;
  const lastGroupTs = parseInt(lastGroup?.dataset?.ts || '0', 10);

  added.forEach(m => {
    const isOut = m.fromSocialId === me;
    const sameGroup = lastGroupSender === m.fromSocialId && (m.timestamp - lastGroupTs) < 5 * 60 * 1000;
    const bubblesHtml = renderMsgBubble(m);

    if (sameGroup && lastGroup) {
      const stampEl = lastGroup.querySelector('.msg-stamp');
      const tmp = document.createElement('div');
      tmp.innerHTML = bubblesHtml;
      Array.from(tmp.children).forEach(b => { lastGroup.insertBefore(b, stampEl); });
      if (stampEl) stampEl.textContent = stamp(m.timestamp);
      lastGroup.dataset.ts = String(m.timestamp);
    } else {
      const groupDiv = document.createElement('div');
      groupDiv.className = `msg-group ${isOut ? 'out' : 'in'}`;
      groupDiv.dataset.sender = m.fromSocialId;
      groupDiv.dataset.ts = String(m.timestamp);
      groupDiv.innerHTML = `${bubblesHtml}<div class="msg-stamp">${stamp(m.timestamp)}</div>`;
      scroll.appendChild(groupDiv);
    }
  });

  app._dmRenderedCount = newMsgs.length;

  if (wasNearBottom || app._justSentDM) {
    scroll.scrollTop = scroll.scrollHeight;
    app._justSentDM = false;
  }

  if (input) {
    input.value = inputVal;
    if (hadFocus) input.focus();
  }

  return true;
}

export function attachConversationListeners(app, container) {
  const VIEWS = app.constructor.VIEWS;
  const otherSocialId = app.viewParams.otherSocialId;
  const me = app.state.me;
  const key = getConvoKey(me, otherSocialId);

  app._dmRenderedCount = (app.state.dms[key] || []).length;
  app._justSentDM = false;

  if (app._pendingDMImage) {
    app._pendingDMAttached = app._pendingDMImage;
    app._pendingDMImage = null;
  } else if (app.viewParams.preservedData?.pendingImage && !app._pendingDMAttached) {
    app._pendingDMAttached = app.viewParams.preservedData.pendingImage;
  }

  container.querySelector('#convo-back')?.addEventListener('click', () => app.goBack());

  container.querySelectorAll('[data-action="open-profile"]').forEach(el => {
    el.addEventListener('click', () => app.switchView(VIEWS.PROFILE, { handle: el.dataset.handle }));
  });

  const input = container.querySelector('#dm-input');
  const sendBtn = container.querySelector('#dm-send');

  const refreshSendDisabled = () => {
    if (!sendBtn) return;
    sendBtn.disabled = !input?.value.trim() && !app._pendingDMAttached;
  };

  input?.addEventListener('input', refreshSendDisabled);
  input?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && (input.value.trim() || app._pendingDMAttached)) sendBtn?.click();
  });

  container.querySelector('#dm-attach')?.addEventListener('click', () => {
    app.selectImageSource((imagePath) => {
      app._pendingDMImage = imagePath;
    }, '', {
      view: 'conversation',
      otherSocialId,
      preservedData: {
        text: input?.value || '',
      },
    });
  });

  container.querySelector('#dm-image-remove')?.addEventListener('click', (e) => {
    e.stopPropagation();
    app._pendingDMAttached = null;
    if (app.viewParams.preservedData) app.viewParams.preservedData.pendingImage = null;
    container.querySelector('.dm-image-preview')?.remove();
    refreshSendDisabled();
    input?.focus();
  });

  sendBtn?.addEventListener('click', async () => {
    const text = input.value.trim();
    const image = app._pendingDMAttached || null;
    if (!text && !image) return;
    app._justSentDM = true;
    await app.socket.executeAsGM('chirp_sendDM', { fromSocialId: me, toSocialId: otherSocialId, text, image });
    input.value = '';
    app._pendingDMAttached = null;
    if (app.viewParams.preservedData) {
      app.viewParams.preservedData.text = '';
      app.viewParams.preservedData.pendingImage = null;
    }
    container.querySelector('.dm-image-preview')?.remove();
    sendBtn.disabled = true;
    input.focus();
  });

  refreshSendDisabled();

  app.socket.executeAsGM('chirp_markDMRead', { socialId: me, otherSocialId });

  const scroll = container.querySelector('#convo-scroll');
  scroll?.addEventListener('click', (e) => {
    const target = e.target instanceof Element ? e.target : null;
    const img = target?.closest('.msg-bubble.image img[data-full-src]');
    if (!img || !scroll.contains(img)) return;
    const lightbox = app.widget?.element?.querySelector('#chirp-lightbox');
    const lbImg = lightbox?.querySelector('img');
    if (!lightbox || !lbImg) return;
    e.stopPropagation();
    lbImg.src = img.dataset.fullSrc;
    lightbox.classList.remove('hidden');
  });
  if (scroll) setTimeout(() => { scroll.scrollTop = scroll.scrollHeight; }, 50);
}
