/* ============================================================
   main.js — app entry point.
   Owns app state, the router, and mounting.

   Every page is a function that takes:
   ctx = { navigate, state, api, bg }

   and returns:
   <section class="screen active">...</section>
   ============================================================ */

import { api as liveApi, bg } from './api/backend.js';
import { StartPage }     from './pages/StartPage.js';
import { SessionPage }   from './pages/SessionPage.js';
import { BlockListPage } from './pages/BlockListPage.js';
import { SettingsPage }  from './pages/SettingsPage.js';
import { HistoryPage } from './pages/HistoryPage.js';

// The extension always uses the real API. Sample data is opt-in on localhost.
const isPreview = ['localhost', '127.0.0.1'].includes(location.hostname)
  && new URLSearchParams(location.search).get('preview') === '1';
const api = isPreview
  ? (await import('./api/preview.js')).createPreviewApi()
  : liveApi;


/* ============================================================
   Pages
   ============================================================ */

const PAGES = {
  start:     StartPage,
  session:   SessionPage,
  blocklist: BlockListPage,
  settings:  SettingsPage,
  history: HistoryPage,
};


/* ============================================================
   Global frontend state
   ============================================================ */

const state = {
  page: 'start',

  // null if no session is currently running
  // Example:
  // {
  //   id: 123,
  //   topic: "Math",
  //   minutes: 45,
  //   seconds: 2700,
  //   is_running: true
  // }
  session: null,

  // loaded from backend when extension opens
  settings: null,
};


/* ============================================================
   Mount point
   ============================================================ */

const mount = document.getElementById('app');
let currentPage = null;

if (isPreview) {
  document.body.classList.add('preview');
  const caption = document.createElement('div');
  caption.className = 'preview-caption';
  caption.innerHTML = '<strong>Grove / Focus extension</strong><span>Interactive preview</span>';
  const footer = document.createElement('p');
  footer.className = 'preview-footer';
  footer.textContent = 'Sample data. Try a session, explore settings, or edit your blocklist. Website blocking is inactive in this preview.';
  mount.before(caption);
  mount.after(footer);
}


/* ============================================================
   Router
   ============================================================ */

function navigate(page) {

  // Don't allow the session page if there is no active session
  if (page === 'session' && !state.session) {
    page = 'start';
  }

  state.page = page;

  render();
}


/* ============================================================
   Render current page
   ============================================================ */

function render() {

  currentPage?.dispose?.();
  mount.innerHTML = '';

  const ctx = {
    navigate,
    state,
    api,
    bg,
  };

  const Page = PAGES[state.page];

  currentPage = Page(ctx);
  mount.append(currentPage);
}


/* ============================================================
   Load settings from backend
   ============================================================ */

async function loadSettings() {

  try {

    state.settings = await api.getSettings();

  } catch (error) {

    console.error('Failed to load settings:', error);

    // Fallback settings
    state.settings = {
      defaultMinutes: 45,
      breakReminders: true,
      sounds: true,
      strictMode: false,
    };
  }
}


/* ============================================================
   Check backend for currently active session
   ============================================================ */

async function loadActiveSession() {

  try {

    const activeSession = await api.getActiveSession();

    console.log('Active session response:', activeSession);

    if (activeSession && (activeSession.is_running || activeSession.status === 'paused')) {

      // Restore frontend session state
      state.session = activeSession;

      // Automatically open session page
      state.page = 'session';

    } else {

      // No session currently running
      state.session = null;
      state.page = 'start';
    }

  } catch (error) {

    console.error('Failed to load active session:', error);

    state.session = null;
    state.page = 'start';
  }
}


/* ============================================================
   App startup
   ============================================================ */

async function boot() {

  // Restore data from backend before first render
  await loadSettings();
  await loadActiveSession();

  render();
}


// Start app
boot();
