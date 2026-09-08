import { api } from './api/backend.js';

// Serialize observations so rapid tab/window events retain their order.
let queue = Promise.resolve();
function enqueue(reason) {
  queue = queue.then(() => observe(reason)).catch(error => {
    console.warn('Activity tracking unavailable:', error.message);
  });
  return queue;
}

async function observe(reason) {
  const session = await api.getActiveSession();
  if (!session?.id || !session.is_running) return;

  const windows = await chrome.windows.getAll({ windowTypes: ['normal'] });
  const focused = windows.find(window => window.focused);
  const idle = await chrome.idle.queryState(60);
  let state = idle !== 'active' ? idle : focused ? 'active' : 'unfocused';
  let tab = null;
  if (state === 'active') {
    [tab] = await chrome.tabs.query({ active: true, windowId: focused.id });
    if (!tab || tab.incognito || !/^https?:\/\//i.test(tab.url ?? '')) state = 'unsupported';
  }

  const observation = {
    event_id: crypto.randomUUID(), session_id: session.id,
    timestamp: new Date().toISOString(), state, reason,
  };
  // Never send website details outside a running session or from private tabs.
  if (state === 'active') Object.assign(observation, {
    tab_id: tab.id, window_id: tab.windowId, url: tab.url, title: tab.title ?? '',
    favicon: tab.favIconUrl ?? '', audible: !!tab.audible, pinned: !!tab.pinned,
  });
  await api.logWebsiteMetadata(observation);
}

chrome.tabs.onActivated.addListener(() => enqueue('tab_activated'));
chrome.tabs.onUpdated.addListener((id, change, tab) => {
  if (tab.active && (change.url || change.title || change.status === 'complete' || change.audible !== undefined)) enqueue('page_updated');
});
chrome.tabs.onRemoved.addListener(() => enqueue('tab_closed'));
chrome.windows.onFocusChanged.addListener(() => enqueue('window_focus_changed'));
chrome.idle.onStateChanged.addListener(() => enqueue('idle_state_changed'));
chrome.alarms.onAlarm.addListener(alarm => {
  if (alarm.name === 'activity-heartbeat') enqueue('heartbeat');
});
chrome.runtime.onMessage.addListener((message, sender, respond) => {
  if (sender.id !== chrome.runtime.id || !['SESSION_START', 'SESSION_PAUSE', 'SESSION_RESUME', 'SESSION_END'].includes(message.type)) return;
  enqueue(message.type.toLowerCase()).then(() => respond({ ok: true }));
  return true;
});

chrome.idle.setDetectionInterval(60);
// Recreate missing alarms whenever the service worker starts.
chrome.alarms.get('activity-heartbeat').then(alarm => {
  if (!alarm) return chrome.alarms.create('activity-heartbeat', { periodInMinutes: 0.5 });
}).catch(error => console.warn('Could not schedule activity heartbeat:', error.message));
enqueue('worker_started');
