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
  { key: 'breakReminders', t: 'Break reminders', d: 'A reminder when it is time to rest' },
  { key: 'sounds',         t: 'Sounds',          d: 'Chime when a session ends' },
  { key: 'strictMode',     t: 'Strict mode',     d: 'Keep sessions running until the end' },
];

export function SettingsPage(ctx) {
  const { navigate, state, api } = ctx;
  const s = state.settings ?? (state.settings = {});

  const page = node(`<section class="screen active"></section>`);
  page.append(NavigationBar({ left: { label: state.session ? 'Back to session' : 'Back to home', page: state.session ? 'session' : 'start' }, right: null, onNavigate: navigate }));
  page.append(node(`<header class="intro"><p class="eyebrow">Preferences</p><h1>Settings</h1><p class="sub">Make room for the way you work.</p></header>`));

  const wrap = node(`<div></div>`);

  /* blocklist → its own page */
  const blockRow = node(`
    <div class="setting">
      <div><div class="t">Blocklist</div><div class="d">Sites to block during a session</div></div>
      <button type="button" class="chip" aria-label="Edit blocked sites">Edit</button>
    </div>`);
  blockRow.querySelector('.chip').addEventListener('click', () => navigate('blocklist'));
  wrap.append(blockRow);

  /* default length (cycles 45→60→75→90) */
  const lenRow = node(`
    <div class="setting">
      <div><div class="t">Default length</div><div class="d">Pre-selected on new sessions</div></div>
      <button type="button" class="chip" data-len aria-label="Change default session length">${s.defaultMinutes ?? 45} min</button>
    </div>`);
  const lenChip = lenRow.querySelector('[data-len]');
  lenChip.addEventListener('click', async () => {
    const opts = [45, 60, 75, 90];
    s.defaultMinutes = opts[(opts.indexOf(s.defaultMinutes ?? 45) + 1) % opts.length];
    lenChip.textContent = `${s.defaultMinutes} min`;
    await api.updateSettings({ defaultMinutes: s.defaultMinutes });
  });
  wrap.append(lenRow);

  /* toggles */
  TOGGLES.forEach(({ key, t, d }) => {
    const row = node(`
      <div class="setting">
        <div><div class="t">${t}</div><div class="d">${d}</div></div>
        <button type="button" class="toggle${s[key] ? ' on' : ''}" data-toggle role="switch" aria-label="${t}" aria-checked="${!!s[key]}"></button>
      </div>`);
    const tog = row.querySelector('[data-toggle]');
    tog.addEventListener('click', async () => {
      tog.classList.toggle('on');
      s[key] = tog.classList.contains('on');
      try { await api.updateSettings({ [key]: s[key] }); }
      catch { tog.classList.toggle('on'); s[key] = !s[key]; }  // revert on failure
      tog.setAttribute('aria-checked', String(!!s[key]));
    });
    wrap.append(row);
  });

  page.append(wrap);
  return page;
}
