import { api, accessKey } from '../api/backend.js';

// The popup, dashboard, and worker share one extension-local credential.
export async function connectProfile(mount) {
  mount.innerHTML = '<section class="screen active"><p class="sub" role="status">Connecting to your profile…</p></section>';
  try { await api.getSettings(); return; } catch { /* Show a recoverable connection screen. */ }
  return new Promise(resolve => {
    const page = document.createElement('section');
    page.className = 'screen active';
    page.innerHTML = `<header class="intro"><p class="eyebrow">Grove</p><h1>Connect your profile</h1>
      <p class="sub">Enter your profile access key to open your sessions on this device.</p></header>
      <form class="stack"><label class="field" for="profile-key">Access key</label>
      <input class="input" id="profile-key" type="password" autocomplete="off" required>
      <button class="btn btn-primary" type="submit">Connect</button>
      <p class="field-error show" role="alert" data-error></p></form>`;
    mount.replaceChildren(page);
    const input = page.querySelector('input');
    accessKey().then(key => { input.value = key; });
    page.querySelector('form').addEventListener('submit', async event => {
      event.preventDefault();
      const button = page.querySelector('button');
      button.disabled = true;
      const previous = await accessKey();
      try {
        await accessKey(input.value.trim());
        await api.getSettings();
        resolve();
      } catch (error) {
        await accessKey(previous);
        page.querySelector('[data-error]').textContent = error.message || 'Cannot connect. Check that the backend is running.';
      } finally { button.disabled = false; }
    });
  });
}
