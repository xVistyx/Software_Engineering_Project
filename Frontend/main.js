/* ============================================================
   main.js — app entry point.
   Owns app state, the router, and mounting. Every page is a
   function that takes ctx = { navigate, state, api, bg } and
   returns a <section class="screen active"> element.
   ============================================================ */

import { api, bg }       from './api/backend.js';
import { StartPage }     from './pages/StartPage.js';
import { SessionPage }   from './pages/SessionPage.js';
import { BlockListPage } from './pages/BlockListPage.js';
import { SettingsPage }  from './pages/SettingsPage.js';

const PAGES = {
  start:     StartPage,
  session:   SessionPage,
  blocklist: BlockListPage,
  settings:  SettingsPage,
};

const state = {
  page: 'start',
  session: null,          // { id, topic, minutes, seconds }
  settings: null,         // loaded before first render
};

const mount = document.getElementById('app');

function navigate(page) {
  // guard: can't open the session page without an active session
  if (page === 'session' && !state.session) page = 'start';
  state.page = page;
  render();
}

function render() {
  mount.innerHTML = '';
  const ctx = { navigate, state, api, bg };
  mount.append(PAGES[state.page](ctx));
}

/* hydrate settings once, then boot */
(async () => {
  try { state.settings = await api.getSettings(); }
  catch { state.settings = { defaultMinutes: 45, breakReminders: true, sounds: true, strictMode: false }; }
  render();
})();
