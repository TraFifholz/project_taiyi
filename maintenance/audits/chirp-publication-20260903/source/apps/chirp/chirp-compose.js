import { renderAvatar, renderIcon } from './chirp-shared.js';
import { MAX_CHIRP_LENGTH, chirpNow, L } from './chirp-utils.js';
import { renderPollCreator, buildPollFromContainer, attachPollToggleListener } from './chirp-poll.js';

const MAX_IMAGES = 4;

function renderPreviewThumbs(images) {
  if (!images.length) return '';
  return images.map((img, i) =>
    `<div class="compose-thumb" data-idx="${i}"><img src="${img.src}" /><button class="thumb-rm" data-idx="${i}">${renderIcon('close', '', 'width:10px;height:10px')}</button></div>`
  ).join('');
}

function returnAfterEdit(app, fallbackView, fallbackParams) {
  const returnView = app.viewParams.editReturnView || fallbackView;
  const returnParams = app.viewParams.editReturnParams || fallbackParams;
  app.currentView = returnView;
  app.viewParams = { ...returnParams };
  app._viewChanged = true;
  app.render();
}

export function renderComposeView(app) {
  const { accounts, me } = app.state;
  const myAccount = accounts.get(me);
  const editChirpId = app.viewParams.editChirpId || null;
  const editingPost = editChirpId ? app.state.posts.get(editChirpId) : null;
  const isEditMode = !!editingPost;
  const quoteChirpId = isEditMode ? editingPost.quoteChirpId : app.viewParams.quoteChirpId || null;
  const quotedPost = quoteChirpId ? app.state.posts.get(quoteChirpId) : null;
  const quotedAuthor = quotedPost ? app.state.accounts.get(quotedPost.authorSocialId) : null;
  const alertChecked = app.viewParams.preservedData?.isAlert ?? editingPost?.isAlert ?? false;

  const quotePreviewHtml = quotedPost && quotedAuthor
    ? `<div class="compose-quote-preview" id="compose-quote" data-quote-id="${quoteChirpId}">
  <div class="quote">
    <div class="quote-byline">
      ${renderAvatar(quotedAuthor, 'mini')}
      <span class="q-display">${quotedAuthor.name}</span>
      <span class="q-handle">@${quotedAuthor.handle}</span>
    </div>
    <div class="q-content">${(quotedPost.content || '').slice(0, 120)}</div>
  </div>
</div>`
    : '';

  return `
<div class="chirp-app chirp-compose-view">
  <div class="compose-top">
    <button class="close-btn" id="compose-close" aria-label="close">${renderIcon('close', '', 'width:18px;height:18px')}</button>
    <button class="post-btn" id="compose-submit" disabled>${isEditMode ? L('save') : L('postChirp')}</button>
  </div>
  <div class="compose-body">
    <div class="compose-row">
      ${renderAvatar(myAccount)}
      <textarea id="compose-text" placeholder="${L('whatsHappening')}" maxlength="${MAX_CHIRP_LENGTH + 50}"></textarea>
    </div>
    ${quotePreviewHtml}
    <div class="compose-media-preview hidden" id="compose-media-preview"></div>
    ${isEditMode ? '' : renderPollCreator()}
  </div>
  ${game.user.isGM ? `
  <label class="compose-alert-toggle">
    <input type="checkbox" id="compose-alert" ${alertChecked ? 'checked' : ''} />
    <span>${renderIcon('bell', '', 'width:14px;height:14px')} ${L('sendAsAlert')}</span>
  </label>` : ''}
  ${game.user.isGM && !isEditMode ? `
  <div class="compose-fake-counts hidden" id="compose-fake-section">
    <div class="fake-counts-label">${L('fakeCounts')}</div>
    <div class="fake-counts-grid">
      <div class="fake-field"><label>${L('fakeLikes')}</label><input type="number" id="compose-fake-likes" min="0" value="0" /></div>
      <div class="fake-field"><label>${L('fakeRechirps')}</label><input type="number" id="compose-fake-rechirps" min="0" value="0" /></div>
      <div class="fake-field"><label>${L('fakeBookmarks')}</label><input type="number" id="compose-fake-bookmarks" min="0" value="0" /></div>
      <div class="fake-field"><label>${L('fakeReplies')}</label><input type="number" id="compose-fake-replies" min="0" value="0" /></div>
    </div>
  </div>` : ''}
  <div class="compose-actions">
    <button class="tool-btn" id="compose-image" aria-label="attach image">${renderIcon('image', '', 'width:16px;height:16px')}</button>
    <button class="tool-btn" aria-label="gif" disabled>${renderIcon('gif', '', 'width:16px;height:16px')}</button>
    ${isEditMode ? '' : `<button class="tool-btn" data-tool="poll" aria-label="poll">${renderIcon('poll', '', 'width:16px;height:16px')}</button>`}
    <button class="tool-btn" aria-label="emoji" disabled>${renderIcon('emoji', '', 'width:16px;height:16px')}</button>
    ${game.user.isGM && !isEditMode ? `<button class="tool-btn" data-tool="fakecounts" aria-label="fake counts">${renderIcon('gear', '', 'width:16px;height:16px')}</button>` : ''}
    <div class="counter" id="compose-counter">${MAX_CHIRP_LENGTH}</div>
  </div>
</div>`;
}

export function attachComposeListeners(app, container) {
  const VIEWS = app.constructor.VIEWS;
  const images = [];
  const editChirpId = app.viewParams.editChirpId || null;
  const editingPost = editChirpId ? app.state.posts.get(editChirpId) : null;
  const isEditMode = !!editingPost;

  attachPollToggleListener(container);

  const fakeSection = container.querySelector('#compose-fake-section');
  container.querySelector('[data-tool="fakecounts"]')?.addEventListener('click', () => {
    fakeSection?.classList.toggle('hidden');
  });

  const textarea = container.querySelector('#compose-text');
  const counter = container.querySelector('#compose-counter');
  const submitBtn = container.querySelector('#compose-submit');
  const mediaPreview = container.querySelector('#compose-media-preview');

  const preserved = app.viewParams.preservedData;
  if (preserved?.text !== undefined) {
    textarea.value = preserved.text;
  } else if (isEditMode) {
    textarea.value = editingPost.content || '';
  }
  if (preserved?.images?.length) {
    images.push(...preserved.images);
  } else if (isEditMode && editingPost.media?.length) {
    images.push(...editingPost.media.map(m => ({ src: m.src })));
  }

  if (app._pendingComposeImage) {
    images.push({ src: app._pendingComposeImage });
    app._pendingComposeImage = null;
  }

  function refreshPreview() {
    if (!images.length) {
      mediaPreview.classList.add('hidden');
      mediaPreview.innerHTML = '';
      return;
    }
    mediaPreview.classList.remove('hidden');
    mediaPreview.innerHTML = renderPreviewThumbs(images);
    mediaPreview.querySelectorAll('.thumb-rm').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        images.splice(Number(btn.dataset.idx), 1);
        refreshPreview();
      });
    });
  }

  refreshPreview();

  function updateCounter() {
    const len = textarea.value.length;
    const remaining = MAX_CHIRP_LENGTH - len;
    counter.textContent = remaining;
    counter.classList.toggle('warn', remaining <= 20 && remaining >= 0);
    counter.classList.toggle('over', remaining < 0);
    submitBtn.disabled = len === 0 || remaining < 0;
  }

  textarea.addEventListener('input', updateCounter);
  updateCounter();

  setTimeout(() => textarea.focus(), 100);

  container.querySelector('#compose-close')?.addEventListener('click', () => {
    app.goBack();
  });

   container.querySelector('#compose-image')?.addEventListener('click', () => {
     if (images.length >= MAX_IMAGES) {
       app.showToast(L('maxImages', {count: MAX_IMAGES}));
       return;
     }
    app.selectImageSource((path) => {
      app._pendingComposeImage = path;
    }, null, {
      view: 'compose',
      preservedData: {
        text: textarea.value,
        quoteChirpId: app.viewParams.quoteChirpId,
        editChirpId,
        editReturnView: app.viewParams.editReturnView || null,
        editReturnParams: app.viewParams.editReturnParams || null,
        isAlert: container.querySelector('#compose-alert')?.checked || false,
        images: [...images],
      },
    });
  });

  container.querySelector('#compose-submit')?.addEventListener('click', async () => {
    const text = textarea.value.trim();
    if (!text || text.length > MAX_CHIRP_LENGTH) return;

    if (isEditMode) {
      const result = await app.socket.executeAsGM('chirp_editPost', {
        chirpId: editChirpId,
        socialId: app.state.me,
        content: text,
        media: images.map(img => ({ src: img.src })),
        isAlert: container.querySelector('#compose-alert')?.checked || false,
        isGM: game.user.isGM,
      });
      if (result?.success) {
        await app.loadPosts();
        app.showToast(L('postUpdated'));
        returnAfterEdit(app, VIEWS.DETAIL, { chirpId: editChirpId });
      } else {
        app.showToast(result?.error || L('postFailed'));
      }
      return;
    }

    const quoteChirpId = app.viewParams.quoteChirpId || null;
    const poll = buildPollFromContainer(container);
    const fakeLikes = parseInt(container.querySelector('#compose-fake-likes')?.value) || 0;
    const fakeRechirps = parseInt(container.querySelector('#compose-fake-rechirps')?.value) || 0;
    const fakeBookmarks = parseInt(container.querySelector('#compose-fake-bookmarks')?.value) || 0;
    const fakeReplies = parseInt(container.querySelector('#compose-fake-replies')?.value) || 0;

    const chirp = {
      id: `chirp_${foundry.utils.randomID()}`,
      authorSocialId: app.state.me,
      content: text,
      media: images.map(img => ({ src: img.src })),
      timestamp: chirpNow(),
      _createdAt: Date.now(),
      likes: [],
      rechirps: [],
      bookmarks: [],
      replies: [],
      replyTo: null,
      quoteChirpId: quoteChirpId || null,
      poll: poll,
      pinned: false,
      isHidden: false,
      publishTimestamp: null,
      fakeLikes,
      fakeRechirps,
      fakeBookmarks,
      fakeReplies,
      isAlert: container.querySelector('#compose-alert')?.checked || false,
    };

     const result = await app.socket.executeAsGM('chirp_createPost', { chirp, socialId: app.state.me });
     if (result?.success) {
       await app.loadPosts();
       await app.loadAccounts();
       app.showToast(L('chirpPosted'));
       app.switchView(VIEWS.TIMELINE);
     } else {
       app.showToast(result?.error || L('postFailed'));
     }
  });
}
