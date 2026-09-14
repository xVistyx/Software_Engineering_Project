const BASE = 'http://127.0.0.1:8000';

async function req(action, content = {}) {
  const response = await fetch(`${BASE}/backend`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action, content }), signal: AbortSignal.timeout(8000),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'The request could not be completed.');
  return data.content;
}

export function bg(type, payload) {
  if (typeof chrome === 'undefined' || !chrome.runtime?.id) return Promise.resolve();
  return chrome.runtime.sendMessage({ type, payload }).catch(error => {
    console.warn('Activity worker notification failed:', error.message);
  });
}

export const api = {
  createSession: data => req('start_session', data),
  getActiveSession: () => req('get_active_session'),
  updateSession: (id, data) => req('update_session', { session_id: id, ...data }),
  endSession: id => req('end_session', { session_id: id }),
  logWebsiteMetadata: data => req('log_meta_data', data),
  getSummary: id => req('get_session_summary', { session_id: id }),
  getSessionDetails: id => req('get_session_details', { session_id: id }),
  exportActivity: () => req('export_activity'),
  listSessions: () => req('get_sessions'),
  getStats: () => req('get_stats'),
  getSettings: () => req('get_settings'),
  updateSettings: data => req('update_settings', data),
  getBlocklist: () => req('get_blocklist'),
  putBlocklist: sites => req('update_blocklist', { sites }),
};
/*Add the functionality for blocking stuff a simple function should do */