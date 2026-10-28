import { renderIcon } from './chirp-shared.js';
import { L } from './chirp-utils.js';

export function renderAuthView(app) {
  const mode = app.viewParams.mode || 'login';
  const error = app.viewParams.error || '';

  if (mode === 'signup') {
    return `
<div class="chirp-app chirp-auth">
  <div class="auth-header">
    <div class="auth-logo">${renderIcon('logo')}</div>
    <h2 class="auth-title">${L('joinChirp')}</h2>
  </div>
  <div class="auth-body">
    ${error ? `<div class="auth-error">${error}</div>` : ''}
     <div class="auth-field">
       <label>${L('handle')}</label>
       <input type="text" class="auth-input" id="chirp-handle" placeholder="your_handle" autocomplete="off" />
     </div>
     <div class="auth-field">
       <label>${L('password')}</label>
       <input type="password" class="auth-input" id="chirp-password" placeholder="••••••••" />
     </div>
     <div class="auth-field">
       <label>${L('confirmPassword')}</label>
       <input type="password" class="auth-input" id="chirp-password2" placeholder="••••••••" />
     </div>
     <button class="auth-btn" id="chirp-submit">${L('createAccount')}</button>
     <button class="auth-link" id="chirp-switch-login">${L('switchToLogin')}</button>
  </div>
</div>`;
  }

  return `
<div class="chirp-app chirp-auth">
  <div class="auth-header">
    <div class="auth-logo">${renderIcon('logo')}</div>
    <h2 class="auth-title">${L('signIn')}</h2>
  </div>
  <div class="auth-body">
    ${error ? `<div class="auth-error">${error}</div>` : ''}
     <div class="auth-field">
       <label>${L('handle')}</label>
       <input type="text" class="auth-input" id="chirp-handle" placeholder="your_handle" autocomplete="off" />
     </div>
     <div class="auth-field">
       <label>${L('password')}</label>
       <input type="password" class="auth-input" id="chirp-password" placeholder="••••••••" />
     </div>
     <button class="auth-btn" id="chirp-submit">${L('logIn')}</button>
     <button class="auth-link" id="chirp-switch-signup">${L('switchToSignup')}</button>
  </div>
</div>`;
}

export function attachAuthListeners(app, container) {
  const mode = app.viewParams.mode || 'login';
  const phoneId = app.phoneId;
  const actorId = game.user.character?.id || null;

  container.querySelector('#chirp-switch-login')?.addEventListener('click', () => {
    app.switchView(app.constructor.VIEWS.AUTH, { mode: 'login' });
  });
  container.querySelector('#chirp-switch-signup')?.addEventListener('click', () => {
    app.switchView(app.constructor.VIEWS.AUTH, { mode: 'signup' });
  });

  container.querySelector('#chirp-submit')?.addEventListener('click', async () => {
    const handle = container.querySelector('#chirp-handle')?.value?.trim();
    const password = container.querySelector('#chirp-password')?.value;

     if (!handle || !password) {
       app.switchView(app.constructor.VIEWS.AUTH, { mode, error: L('fillAllFields') });
       return;
     }

    if (mode === 'signup') {
      const password2 = container.querySelector('#chirp-password2')?.value;
       if (password !== password2) {
         app.switchView(app.constructor.VIEWS.AUTH, { mode: 'signup', error: L('passwordsMismatch') });
         return;
       }
      const result = await app.socket.executeAsGM('chirp_signup', { handle, password, actorId, phoneId });
      if (result?.error) {
        app.switchView(app.constructor.VIEWS.AUTH, { mode: 'signup', error: result.error });
      }
    } else {
      const result = await app.socket.executeAsGM('chirp_login', { handle, password, phoneId });
      if (result?.error) {
        app.switchView(app.constructor.VIEWS.AUTH, { mode: 'login', error: result.error });
      }
    }
  });

  container.querySelector('#chirp-handle')?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') container.querySelector('#chirp-submit')?.click();
  });
  container.querySelector('#chirp-password')?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') container.querySelector('#chirp-submit')?.click();
  });
}
