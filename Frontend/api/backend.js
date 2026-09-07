/* ============================================================
   api/backend.js
   Central API layer for communication with the Python backend.
   ============================================================ */

const BASE = 'http://127.0.0.1:8000';


/* ============================================================
   Optional token helper
   ============================================================ */

async function token() {
    try {
        return (await chrome.storage.local.get('token')).token ?? null;
    } catch {
        return null;
    }
}


/* ============================================================
   Generic request function
   ============================================================ */

async function req(action, content = {}) {

    console.log("SENDING TO PYTHON BACKEND:", {
        action: action,
        content: content
    });

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
        const errorText = await response.text();

        console.error(
            "BACKEND ERROR:",
            response.status,
            errorText
        );

        throw new Error(
            `${response.status} ${errorText}`
        );
    }

    const data = await response.json();

    console.log("PYTHON BACKEND RETURNED:", data);

    return data.content;
}


/* ============================================================
   Temporary background bridge
   ============================================================ */

export function bg(type, payload) {

    console.log(
        "BG MESSAGE:",
        type,
        payload
    );

    return Promise.resolve();
}


/* ============================================================
   API surface
   ============================================================ */

export const api = {

    /* -------------------------
       USER SESSION
       ------------------------- */

    createSession: (data) =>
        req(
            'start_session',
            data
        ),

    getActiveSession: () =>
        req(
            'get_active_session'
        ),

    updateSession: (id, data) =>
        req(
            'update_session',
            {
                session_id: id,
                ...data
            }
        ),

    endSession: (id) =>
        req(
            'end_session',
            {
                session_id: id
            }
        ),


    /* -------------------------
       WEBSITE METADATA
       ------------------------- */

    logWebsiteMetadata: (metadata) => {

        console.log(
            "LOG WEBSITE METADATA CALLED:",
            metadata
        );

        return req(
            'log_meta_data',
            metadata
        );
    },


    /* -------------------------
       PAST SESSIONS
       ------------------------- */

    getSummary: (id) =>
        req(
            'get_session_summary',
            {
                session_id: id
            }
        ),

    listSessions: () =>
        req(
            'get_sessions'
        ),

    getStats: () =>
        req(
            'get_stats'
        ),


    /* -------------------------
       SETTINGS
       ------------------------- */

    getSettings: () =>
        req(
            'get_settings'
        ),

    updateSettings: (data) =>
        req(
            'update_settings',
            data
        ),


    /* -------------------------
       BLOCKLIST
       ------------------------- */

    getBlocklist: () =>
        req(
            'get_blocklist'
        ),

    putBlocklist: (sites) =>
        req(
            'update_blocklist',
            {
                sites: sites
            }
        )
};