import { api, accessKey } from './api/backend.js';
import { connectProfile } from './components/ProfileConnection.js';
import { HistoryPage } from './pages/HistoryPage.js';

const root = document.getElementById('dashboard');
await connectProfile(root);
root.innerHTML = `<header class="dashboard-header"><div class="brand"><span class="brand-mark" aria-hidden="true">g</span>Grove</div>
  <div class="chips"><button class="chip" data-refresh>Refresh</button><button class="chip" data-disconnect>Disconnect profile</button></div></header>
  <header class="intro"><p class="eyebrow">Your activity</p><h1>Past Sessions</h1><p class="sub">Look back at your goals, time, and session results.</p></header>
  <div class="dashboard-layout"><aside class="session-sidebar" aria-label="Previous sessions">
    <label class="field" for="session-search">Find a session</label><input class="input" type="search" id="session-search" placeholder="Search by goal or topic">
    <p class="sub" data-count aria-live="polite"></p><div data-sessions></div></aside>
    <section class="dashboard-detail" aria-label="Selected session" aria-live="polite"></section></div>`;
const list = root.querySelector('[data-sessions]');
const detail = root.querySelector('.dashboard-detail');
const search = root.querySelector('input');
let sessions = [];
let selected = null;
let view = null;
let generation = 0;

function emptyDetail() {
  view?.dispose?.();
  selected = null;
  detail.innerHTML = '<div class="dashboard-placeholder"><p class="eyebrow">Session details</p><h2>A little perspective on your progress</h2><p class="sub">Choose a session to review its summary, website activity, and analysis.</p></div>';
  renderList();
}

function openSession(id) {
  selected = id;
  view?.dispose?.();
  view = HistoryPage({ api, state: { historySessionId: id }, dashboard: true,
    navigate: emptyDetail, onBackToList: emptyDetail });
  detail.replaceChildren(view);
  renderList();
}

function renderList() {
  const query = search.value.trim().toLowerCase();
  const visible = sessions.filter(session => session.topic.toLowerCase().includes(query));
  root.querySelector('[data-count]').textContent = `${visible.length} ${visible.length === 1 ? 'session' : 'sessions'}`;
  list.replaceChildren();
  if (!visible.length) {
    const message = document.createElement('p');
    message.className = 'empty-state';
    message.textContent = query ? 'No sessions match your search.' : 'No past sessions yet. Finish a focus session and it will appear here automatically.';
    list.append(message);
  }
  for (const session of visible) {
    const button = document.createElement('button');
    button.className = 'history-row dashboard-session';
    button.setAttribute('aria-pressed', String(session.id === selected));
    button.innerHTML = '<span><strong></strong><small></small></span><span data-state></span>';
    button.querySelector('strong').textContent = session.topic;
    const seconds = Math.round(session.minutes * 60);
    const duration = session.duration_known === false ? 'Duration unknown'
      : seconds < 60 ? `${seconds}s` : `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
    button.querySelector('small').textContent = `${session.start_time ? new Date(session.start_time).toLocaleString() : 'Date unknown'} · ${duration}`;
    button.querySelector('[data-state]').textContent = session.storage_status === 'pending' ? 'Save pending' : session.status;
    button.addEventListener('click', () => openSession(session.id));
    list.append(button);
  }
}

async function refresh() {
  const request = ++generation;
  const button = root.querySelector('[data-refresh]');
  button.disabled = true;
  list.innerHTML = '<p class="empty-state" role="status">Loading sessions…</p>';
  try {
    sessions = await api.listPastSessions();
    if (request !== generation) return;
    if (selected && sessions.some(session => session.id === selected)) openSession(selected);
    else emptyDetail();
    renderList();
  } catch (error) {
    if (request !== generation) return;
    list.innerHTML = '<p class="field-error show" role="alert"></p><button class="btn btn-soft">Retry</button>';
    list.querySelector('p').textContent = error.message || 'Sessions could not be loaded.';
    list.querySelector('button').addEventListener('click', refresh);
  } finally { if (request === generation) button.disabled = false; }
}

search.addEventListener('input', renderList);
root.querySelector('[data-refresh]').addEventListener('click', refresh);
root.querySelector('[data-disconnect]').addEventListener('click', async () => { await accessKey(''); location.reload(); });
// Also remove old profile data if a different extension page changes the key.
if (typeof chrome !== 'undefined' && chrome.storage?.onChanged) {
  chrome.storage.onChanged.addListener(changes => { if (changes.groveAccessKey) location.reload(); });
} else {
  window.addEventListener('storage', event => { if (event.key === 'groveAccessKey') location.reload(); });
}
emptyDetail();
await refresh();
