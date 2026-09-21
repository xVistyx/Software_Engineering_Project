const BASE = 'http://127.0.0.1:8000';


async function registerUser() {
  const response = await fetch(`${BASE}/register`, {
    method: 'POST',
    signal: AbortSignal.timeout(8000),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      typeof data.detail === 'string'
        ? data.detail
        : 'Could not register user.'
    );
  }

  if (!data.token) {
    throw new Error(
      'Backend did not return an access token.'
    );
  }

  await chrome.storage.local.set({
    access_token: data.token,
  });

  return data.token;
}


async function getAccessToken() {
  const stored =
    await chrome.storage.local.get(
      'access_token'
    );

  if (stored.access_token) {
    return stored.access_token;
  }

  return await registerUser();
}


async function req(
  action,
  content = {}
) {
  const token =
    await getAccessToken();

  const response = await fetch(
    `${BASE}/backend`,
    {
      method: 'POST',

      headers: {
        'Content-Type':
          'application/json',

        'Authorization':
          `Bearer ${token}`,
      },

      body: JSON.stringify({
        action,
        content,
      }),

      signal:
        AbortSignal.timeout(8000),
    }
  );


  const data =
    await response.json();


  if (!response.ok) {
    throw new Error(
      typeof data.detail === 'string'
        ? data.detail
        : 'The request could not be completed.'
    );
  }


  return data.content;
}


/*
|--------------------------------------------------------------------------
| Background worker communication
|--------------------------------------------------------------------------
*/

export function bg(
  type,
  payload
) {
  if (
    typeof chrome === 'undefined' ||
    !chrome.runtime?.id
  ) {
    return Promise.resolve();
  }


  return chrome.runtime
    .sendMessage({
      type,
      payload,
    })
    .catch(error => {

      console.warn(
        'Activity worker notification failed:',
        error.message
      );

    });
}


/*
|--------------------------------------------------------------------------
| Backend API
|--------------------------------------------------------------------------
*/

export const api = {

  // ----------------------------------------------------------
  // SESSION
  // ----------------------------------------------------------

  createSession: data =>
    req(
      'start_session',
      data
    ),


  getActiveSession: () =>
    req(
      'get_active_session'
    ),


  updateSession: (
    id,
    data
  ) =>
    req(
      'update_session',
      {
        session_id: id,
        ...data,
      }
    ),


  endSession: id =>
    req(
      'end_session',
      {
        session_id: id,
      }
    ),


  // ----------------------------------------------------------
  // WEBSITE METADATA
  // ----------------------------------------------------------

  logWebsiteMetadata: data =>
    req(
      'log_meta_data',
      data
    ),


  // ----------------------------------------------------------
  // DYNAMIC WEBPAGE CONTENT
  // ----------------------------------------------------------

  /*
    Used for websites such as YouTube where
    one browser tab contains multiple separate
    pieces of content.

    Expected input:

    {
      tab_id: 123,

      session_id: 45,

      page_type:
        "youtube_watch",

      primary_content: {
        content_id:
          "abc123",

        source:
          "youtube",

        content_type:
          "video",

        title:
          "Chess Openings Explained",

        url:
          "https://youtube.com/watch?v=abc123",

        channel:
          "Chess Academy"
      },

      recommended_content: [
        {
          content_id:
            "xyz789",

          source:
            "youtube",

          content_type:
            "video",

          title:
            "Minecraft Survival Episode 52",

          url:
            "https://youtube.com/watch?v=xyz789",

          channel:
            "Gaming Channel"
        }
      ]
    }

    The backend should return the decisions
    for the primary/recommended content.

    Example:

    {
      primary_content: {
        content_id: "abc123",
        is_related: true,
        action: "allow"
      },

      recommended_content: [
        {
          content_id: "xyz789",
          is_related: false,
          action: "blur"
        }
      ]
    }
  */

  logDynamicContent: data => {

    if (
      !data ||
      typeof data !== 'object'
    ) {
      return Promise.resolve(
        null
      );
    }


    return req(
      'log_dynamic_content',
      data
    );
  },


  // ----------------------------------------------------------
  // PAST SESSIONS / SUMMARY
  // ----------------------------------------------------------

  getSummary: id =>
    req(
      'get_session_summary',
      {
        session_id: id,
      }
    ),


  getSessionDetails: id =>
    req(
      'get_session_details',
      {
        session_id: id,
      }
    ),


  exportActivity: () =>
    req(
      'export_activity'
    ),


  listSessions: () =>
    req(
      'get_sessions'
    ),


  getStats: () =>
    req(
      'get_stats'
    ),


  // ----------------------------------------------------------
  // SETTINGS
  // ----------------------------------------------------------

  getSettings: () =>
    req(
      'get_settings'
    ),


  updateSettings: data =>
    req(
      'update_settings',
      data
    ),


  // ----------------------------------------------------------
  // BLOCKLIST
  // ----------------------------------------------------------

  getBlocklist: () =>
    req(
      'get_blocklist'
    ),


  putBlocklist: sites =>
    req(
      'update_blocklist',
      {
        sites,
      }
    ),
};