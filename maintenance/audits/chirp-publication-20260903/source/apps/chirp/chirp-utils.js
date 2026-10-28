import { SmartphoneTime } from '../../../smartphone-widget/scripts/core/SmartphoneTime.js';

export const MODULE_ID = 'smartphone-chirp-app';
export const MAX_CHIRP_LENGTH = 280;

let _shareTerm = null;

function getShareTerm() {
  if (_shareTerm !== null) return _shareTerm;
  try { _shareTerm = game.settings.get(MODULE_ID, 'chirp-share-term') || ''; } catch { _shareTerm = ''; }
  return _shareTerm;
}

export function clearShareTermCache() { _shareTerm = null; }

const SHARE_TERM_KEYS = {
  rechirp: (t) => t,
  rechirped: (t, data) => {
    const past = t.toLowerCase().endsWith('e') ? `${t.toLowerCase()}d` : `${t.toLowerCase()}ed`;
    return `${data.name} ${past}`;
  },
  rechirpedYourChirp: (t) => {
    const past = t.toLowerCase().endsWith('e') ? `${t.toLowerCase()}d` : `${t.toLowerCase()}ed`;
    return `${past} your chirp`;
  },
  undoRechirp: (t) => `Undo ${t.toLowerCase()}`,
  fakeRechirps: (t) => `Fake ${t}s`,
};

export function L(key, data) {
  const term = getShareTerm();
  if (term && SHARE_TERM_KEYS[key]) return SHARE_TERM_KEYS[key](term, data);
  if (data) return game.i18n.format(`CHIRP.${key}`, data);
  return game.i18n.localize(`CHIRP.${key}`);
}
let _logoIcon = null;

export function getCustomLogoIcon() {
  if (_logoIcon !== null) return _logoIcon;
  try { _logoIcon = game.settings.get(MODULE_ID, 'chirp-logo-icon') || ''; } catch { _logoIcon = ''; }
  return _logoIcon;
}

export function clearLogoIconCache() { _logoIcon = null; }

const SW_ID = 'smartphone-widget';

export function useGameTime() {
  try { return game.settings.get(SW_ID, 'useGameTime'); } catch { return false; }
}

export function chirpNow() {
  return useGameTime() ? SmartphoneTime.now() : Date.now();
}

export function timeAgo(ts) {
  const now = chirpNow();
  const s = Math.floor((now - ts) / 1000);
  if (s < 60) return `${s}s`;
  if (s < 3600) return `${Math.floor(s / 60)}m`;
  if (s < 86400) return `${Math.floor(s / 3600)}h`;
  if (s < 604800) return `${Math.floor(s / 86400)}d`;
  return formatTimestamp(ts, 'short');
}

export function formatTimestamp(ts, style = 'short') {
  if (useGameTime()) {
    return style === 'full'
      ? SmartphoneTime.format(ts, 'YYYY.MM.DD HH:mm')
      : SmartphoneTime.format(ts, 'MM.DD');
  }
  const dt = new Date(ts);
  if (style === 'full') {
    return dt.toLocaleString([], { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
  }
  return `${dt.toLocaleString('en-US', { month: 'short' })} ${dt.getDate()}`;
}

export function formatTime(ts) {
  if (useGameTime()) return SmartphoneTime.format(ts, 'HH:mm');
  return new Date(ts).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
}

export function formatCount(n) {
  if (n == null) return '';
  if (n < 1000) return String(n);
  if (n < 10000) return (n / 1000).toFixed(1).replace(/\.0$/, '') + 'K';
  if (n < 1000000) return Math.floor(n / 1000) + 'K';
  return (n / 1000000).toFixed(1).replace(/\.0$/, '') + 'M';
}

export function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

export function renderContent(text) {
  if (!text) return '';
  const safe = escapeHtml(text);
  const re = /(#[\w\p{L}]+|@[\w]+|https?:\/\/\S+|[a-z0-9-]+\.[a-z]{2,}(?:\/\S*)?)/giu;
  return safe.replace(re, (token) => {
    const cls = token.startsWith('#') ? 'tag' : token.startsWith('@') ? 'mention' : 'link';
    return `<span class="${cls}">${token}</span>`;
  });
}
