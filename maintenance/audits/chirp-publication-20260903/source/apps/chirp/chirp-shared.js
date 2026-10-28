import { timeAgo, formatCount, escapeHtml, L, getCustomLogoIcon } from './chirp-utils.js';

export const ChirpIcons = {
  logo: `<i class="fa-solid fa-feather"></i>`,
  home: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="M3 11l9-8 9 8v10a1 1 0 0 1-1 1h-5v-7h-6v7H4a1 1 0 0 1-1-1V11z"/></svg>`,
  homeFill: `<svg viewBox="0 0 24 24" fill="currentColor"><path d="M3 11l9-8 9 8v10a1 1 0 0 1-1 1h-5v-7h-6v7H4a1 1 0 0 1-1-1V11z"/></svg>`,
  search: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="10.5" cy="10.5" r="6.5"/><path d="M20 20l-4.5-4.5"/></svg>`,
  bell: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 7 3 10H3c0-3 3-3 3-10z"/><path d="M10 21a2 2 0 0 0 4 0"/></svg>`,
  bellFill: `<svg viewBox="0 0 24 24" fill="currentColor"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 7 3 10H3c0-3 3-3 3-10z"/><path d="M10 21a2 2 0 0 0 4 0" stroke="currentColor" stroke-width="2" fill="none"/></svg>`,
  mail: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/></svg>`,
  user: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 4-7 8-7s8 3 8 7"/></svg>`,
  feather: `<i class="fa-solid fa-feather"></i>`,
  plus: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>`,
  reply: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12c0 4-4 7-9 7-1.3 0-2.6-.2-3.8-.6L3 20l1.5-4C3.5 14.8 3 13.4 3 12c0-4 4-7 9-7s9 3 9 7z"/></svg>`,
  rechirp: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 3l4 4-4 4"/><path d="M21 7H7a4 4 0 0 0-4 4v2"/><path d="M7 21l-4-4 4-4"/><path d="M3 17h14a4 4 0 0 0 4-4v-2"/></svg>`,
  heart: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.8 6.6a5 5 0 0 0-7.1 0L12 8.3l-1.7-1.7a5 5 0 0 0-7.1 7.1l1.7 1.7L12 22.5l7.1-7.1 1.7-1.7a5 5 0 0 0 0-7.1z"/></svg>`,
  bookmark: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="M6 3h12v18l-6-4-6 4V3z"/></svg>`,
  share: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 12v8a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-8"/><path d="M12 3v13"/><path d="M7 8l5-5 5 5"/></svg>`,
  more: `<svg viewBox="0 0 24 24" fill="currentColor"><circle cx="5" cy="12" r="2"/><circle cx="12" cy="12" r="2"/><circle cx="19" cy="12" r="2"/></svg>`,
  verified: `<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 1l2.5 2.3 3.3-.6.6 3.3L20.8 8.5 19 12l1.8 3.5-2.4 2.4-.6 3.4-3.4-.6L12 23l-2.5-2.3-3.3.6-.6-3.3L3.2 15.5 5 12 3.2 8.5l2.4-2.4.6-3.4 3.4.6L12 1zm-1 14l6-6-1.4-1.4L11 12.2 8.4 9.6 7 11l4 4z"/></svg>`,
  close: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M5 5l14 14M19 5L5 19"/></svg>`,
  back: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 18l-6-6 6-6"/></svg>`,
  image: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="1.8"/><path d="M5 19l5-5 4 4 3-3 3 3"/></svg>`,
  gif: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="5" width="18" height="14" rx="3"/><text x="7" y="16" font-size="7" font-weight="700" fill="currentColor" stroke="none">GIF</text></svg>`,
  poll: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="3" y="11" width="4" height="10" rx="1"/><rect x="10" y="6" width="4" height="15" rx="1"/><rect x="17" y="14" width="4" height="7" rx="1"/></svg>`,
  emoji: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><circle cx="9" cy="10" r="0.8" fill="currentColor"/><circle cx="15" cy="10" r="0.8" fill="currentColor"/><path d="M8 15c1 1.3 2.4 2 4 2s3-.7 4-2"/></svg>`,
  calendar: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 10h18"/></svg>`,
  pin: `<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2l3 7h7l-5.5 4 2 8L12 17l-6.5 4 2-8L2 9h7z"/></svg>`,
  sendArrow: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg>`,
  link: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M10 14a3 3 0 0 0 4 0l3-3a3 3 0 0 0-4-4l-1 1"/><path d="M14 10a3 3 0 0 0-4 0l-3 3a3 3 0 0 0 4 4l1-1"/></svg>`,
  location: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="M12 22s7-6 7-12a7 7 0 1 0-14 0c0 6 7 12 7 12z"/><circle cx="12" cy="10" r="2.5"/></svg>`,
  gear: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>`,
};

export function renderIcon(name, extraClass = '', style = '') {
  if (name === 'logo') {
    const custom = getCustomLogoIcon();
    if (custom) return `<span class="chirp-icon ${extraClass}" style="${style}"><i class="${custom}"></i></span>`;
  }
  const svg = ChirpIcons[name] || '';
  return `<span class="chirp-icon ${extraClass}" style="${style}">${svg}</span>`;
}

export function renderAvatar(account, size = 'md') {
  if (!account) return '';
  const cls = size === 'lg' ? 'profile-avatar' : size === 'mini' ? 'mini-avatar' : size === 'sm' ? 'mini-av' : 'avatar';
  const px = size === 'lg' ? 64 : size === 'sm' ? 22 : size === 'mini' ? 16 : null;
  const sizeStyle = px ? `width:${px}px;height:${px}px;` : '';

  if (account.profileImage) {
    return `<div class="${cls}" style="background:url(${account.profileImage}) center/cover no-repeat;${sizeStyle}border-radius:50%"></div>`;
  }

  const initials = account.name.split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase();
  const [fg, bg] = account.profilePal || account.pal || ['#888', '#222'];
  const fontStyle = px ? `font-size:${Math.round(px * 0.4)}px;` : '';
  return `<div class="${cls}" style="background:linear-gradient(135deg,${fg},${bg});color:#fff;${sizeStyle}${fontStyle}">${initials}</div>`;
}

export function renderByline(account, ts, showMore = false) {
  const verifiedBadge = account.verified ? renderIcon('verified', 'verified', 'width:13px;height:13px') : '';
  const moreBtn = showMore
    ? `<button class="more-btn" data-action="more" aria-label="more">${renderIcon('more', '', 'width:14px;height:14px')}</button>`
    : '';
  return `<div class="byline"><span class="display-name">${account.name}</span>${verifiedBadge}<span class="handle">@${account.handle}</span><span class="dot">·</span><span class="time">${timeAgo(ts)}</span>${moreBtn}</div>`;
}

export function renderAlertLabel() {
  return `<div class="chirp-alert-label">${renderIcon('bell', '', 'width:12px;height:12px')}<span>${L('alertChirp')}</span></div>`;
}

export function computeReplyCounts(posts) {
  const counts = {};
  for (const p of posts.values()) {
    if (p.replyTo) counts[p.replyTo] = (counts[p.replyTo] || 0) + 1;
  }
  return counts;
}

export function renderActionBar(chirp, mySocialId, chirpId, replyCount = 0) {
  const isLiked = chirp.likes?.includes(mySocialId);
  const isRechirped = chirp.rechirps?.includes(mySocialId);
  const isBookmarked = chirp.bookmarks?.includes(mySocialId);
  const likes = (chirp.likes?.length || 0) + (chirp.fakeLikes || 0);
  const rechirps = (chirp.rechirps?.length || 0) + (chirp.fakeRechirps || 0);
  const replies = replyCount + (chirp.fakeReplies || 0);
  const id = chirpId ? `data-chirp-id="${chirpId}"` : '';
  return `<div class="chirp-actions">` +
    `<button class="reply-btn" ${id} data-action="reply">${renderIcon('reply')}<span>${formatCount(replies)}</span></button>` +
    `<button class="rt-btn${isRechirped ? ' active' : ''}" ${id} data-action="rechirp">${renderIcon('rechirp')}<span>${formatCount(rechirps)}</span></button>` +
    `<button class="like-btn${isLiked ? ' active' : ''}" ${id} data-action="like">${renderIcon('heart')}<span>${formatCount(likes)}</span></button>` +
    `<button class="bookmark-btn${isBookmarked ? ' active' : ''}" ${id} data-action="bookmark">${renderIcon('bookmark')}</button>` +
    `<button class="share-btn" ${id} data-action="share">${renderIcon('share')}</button>` +
    `</div>`;
}

export function renderMediaGrid(media) {
  if (!media?.length) return '';
  const count = Math.min(media.length, 4);
  const items = media.slice(0, 4).map(m =>
    `<div class="m"><img src="${m.src}" loading="lazy" data-full-src="${m.src}" /></div>`
  ).join('');
  return `<div class="media count-${count}">${items}</div>`;
}

export function renderQuoteCard(quoteChirpId, posts, accounts) {
  if (!quoteChirpId) return '';
  const qPost = posts instanceof Map ? posts.get(quoteChirpId) : posts?.[quoteChirpId];
   if (!qPost) return `<div class="quote"><div class="q-content" style="color:var(--text-dim)">${L('unavailableChirp')}</div></div>`;
  const a = accounts instanceof Map ? accounts.get(qPost.authorSocialId) : accounts?.[qPost.authorSocialId];
  if (!a) return '';
  const verifiedBadge = a.verified ? renderIcon('verified', 'verified', 'width:11px;height:11px') : '';
  return `<div class="quote" data-chirp-id="${quoteChirpId}">` +
    `<div class="quote-byline">` +
    `${renderAvatar(a, 'mini')}` +
    `<span class="q-display">${a.name}</span>${verifiedBadge}` +
    `<span class="q-handle">@${a.handle}</span><span class="dot">·</span><span class="q-time">${timeAgo(qPost.timestamp)}</span>` +
    `</div><div class="q-content">${(qPost.content || '').slice(0, 140)}</div>` +
    `${qPost.media?.length ? `<div class="q-media"><img src="${qPost.media[0].src}" /></div>` : ''}` +
    `</div>`;
}

export function renderPollDisplay(poll, mySocialId, chirpId) {
  const id = chirpId ? `data-chirp-id="${chirpId}"` : '';
  const votedOption = mySocialId ? poll.votes?.[mySocialId] ?? null : null;
  const total = poll.options.reduce((s, o) => s + (o.votes || 0), 0);
  const maxVotes = Math.max(...poll.options.map(o => o.votes || 0));
  const options = poll.options.map(o => {
    const votes = o.votes || 0;
    const pct = total ? (votes / total) * 100 : 0;
    const isLead = votedOption && votes === maxVotes;
    const fillBar = votedOption ? `<div class="fill" style="width:${pct}%"></div>` : '';
    const pctLabel = votedOption ? `<span class="pct">${pct.toFixed(0)}%</span>` : '';
    const check = votedOption === o.label ? ' ✓' : '';
    return `<div class="poll-option${isLead ? ' lead' : ''}" style="${votedOption ? 'cursor:default' : 'cursor:pointer'}" ${id} data-poll-option="${escapeHtml(o.label)}">${fillBar}<span class="lbl">${escapeHtml(o.label)}${check}</span>${pctLabel}</div>`;
  }).join('');
   const meta = votedOption
     ? `${L('votes', {count: formatCount(total)})} · ${L('youVoted')}`
     : `${L('votes', {count: formatCount(total)})} · ${L('closesIn', {time: poll.closesIn || '—'})}`;
   return `<div class="poll">${options}<div class="poll-meta">${meta}</div></div>`;
}

export function sortFeedItems(items) {
  for (const item of items) {
    item.sortTs = item.rechirpedBy
      ? (item.post.rechirpTimestamps?.[item.rechirpedBy] || item.post.timestamp)
      : item.post.timestamp;
    item._actionRealTime = item.rechirpedBy
      ? (item.post._rechirpCreatedAt?.[item.rechirpedBy] || 0)
      : (item.post._createdAt || 0);
  }
  items.sort((a, b) => b.sortTs - a.sortTs || b._actionRealTime - a._actionRealTime);
  return items;
}
