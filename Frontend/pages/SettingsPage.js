/* ============================================================
   pages/SettingsPage.js — preferences.
   (prototype screen 5)
   ctx = { navigate, state, api, bg }
   ============================================================ */

import { NavigationBar } from '../components/NavigationBar.js';

const node = (html) => {
  const t = document.createElement('template');
  t.innerHTML = html.trim();
  return t.content.firstElementChild;
};

const TOGGLES = [
  { key: 'breakReminders', t: 'Break reminders', d: 'Nudge you to rest' },
  { key: 'sounds',         t: 'Sounds',          d: 'Chime when a session ends' },
  { key: 'strictMode',     t: 'Strict mode',     d: "Can't stop early" },
];

export function SettingsPage(ctx) {
  const { navigate, state, api } = ctx;
  const s = state.settings ?? {};

  const page = node(`<section class="screen active"></section>`);
  page.append(NavigationBar({ left: { label: '⌂ Home', page: 'start' }, right: null, onNavigate: navigate }));
  page.append(node(`<h2 style="margin:8px 0 12px">Settings</h2>`));

  const wrap = node(`<div></div>`);

  /* blocklist → its own page */
  const blockRow = node(`
    <div class="setting">
      <div><div class="t">Blocklist</div><div class="d">Sites to block during a session</div></div>
      <div class="chip">Edit ›</div>
    </div>`);
  blockRow.querySelector('.chip').addEventListener('click', () => navigate('blocklist'));
  wrap.append(blockRow);

  /* default length (cycles 45→60→75→90) */
  const lenRow = node(`
    <div class="setting">
      <div><div class="t">Default length</div><div class="d">Pre-selected on new sessions</div></div>
      <div class="chip" data-len>${s.defaultMinutes ?? 45}m ›</div>
    </div>`);
  const lenChip = lenRow.querySelector('[data-len]');
  lenChip.addEventListener('click', async () => {
    const opts = [45, 60, 75, 90];
    s.defaultMinutes = opts[(opts.indexOf(s.defaultMinutes ?? 45) + 1) % opts.length];
    lenChip.textContent = `${s.defaultMinutes}m ›`;
    await api.updateSettings({ defaultMinutes: s.defaultMinutes });
  });
  wrap.append(lenRow);

  /* toggles */
  TOGGLES.forEach(({ key, t, d }) => {
    const row = node(`
      <div class="setting">
        <div><div class="t">${t}</div><div class="d">${d}</div></div>
        <div class="toggle${s[key] ? ' on' : ''}" data-toggle></div>
      </div>`);
    const tog = row.querySelector('[data-toggle]');
    tog.addEventListener('click', async () => {
      tog.classList.toggle('on');
      s[key] = tog.classList.contains('on');
      try { await api.updateSettings({ [key]: s[key] }); }
      catch { tog.classList.toggle('on'); s[key] = !s[key]; }  // revert on failure
    });
    wrap.append(row);
  });

  page.append(wrap);
  return page;
}
