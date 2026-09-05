/* ============================================================
   api/backend.js — the ONLY place the popup talks to anything
   stateful (remote REST + the extension background worker).
   Every page/component imports { api, bg } from here.
   ============================================================ */

const BASE     = 'http://127.0.0.1:8000'; // TODO: your real base URL


/* auth token lives in chrome.storage; falls back to null in a browser tab */
async function token() {
  try { return (await chrome.storage.local.get('token')).token ?? null; }
  catch { return null; }
}

async function req(action, content = {}) {

    const response = await fetch(
        `${BASE}/backend`,
        {
            method: 'POST',

            headers: {
                'Content-Type': 'application/json'
            },

            body: JSON.stringify({
                action: action,
                content: content
            })
        }
    );

    if (!response.ok) {
        throw new Error(
            `${response.status} ${await response.text()}`
        );
    }
    const data = await response.json();

    return data.content;
}

/* Bridge to the background service worker. The real timer, site
   blocking and drift scoring live there (a popup can't run them —
   it dies on focus loss). No-ops safely in a plain browser tab. */

/* TEMPORARY */   
export function bg(type, payload) {
    console.log("BG MESSAGE:", type, payload);

    return Promise.resolve();
}

/* Typed surface. Buttons call these — never fetch() directly. */
export const api = {

    createSession: (data) =>
        req('start_session', data),

    updateSession: (id, data) =>
        req('update_session', {
            session_id: id,
            ...data
        }),

    endSession: (id) =>
        req('end_session', {
            session_id: id
        }),

    getSummary: (id) =>
        req('get_session_summary', {
            session_id: id
        }),

    listSessions: () =>
        req('get_sessions'),

    getStats: () =>
        req('get_stats'),

    getSettings: () =>
        req('get_settings'),

    updateSettings: (data) =>
        req('update_settings', data),

    getBlocklist: () =>
        req('get_blocklist'),

    putBlocklist: (sites) =>
        req('update_blocklist', {
            sites: sites
        })
};


