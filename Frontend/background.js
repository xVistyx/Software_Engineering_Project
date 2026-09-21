import { api } from './api/backend.js';


// ============================================================
// EVENT QUEUE
// ============================================================

let queue = Promise.resolve();


function enqueue(task) {

  queue = queue
    .then(task)
    .catch(error => {
      console.warn(
        'Activity tracking unavailable:',
        error.message
      );
    });

  return queue;
}


// ============================================================
// SESSION CHECK
// ============================================================

async function getRunningSession() {

  const session =
    await api.getActiveSession();


  if (
    !session?.id ||
    !session.is_running
  ) {
    return null;
  }


  return session;
}


// ============================================================
// SEND WEBSITE EVENT
// ============================================================

async function sendTabObservation(
  tab,
  session,
  reason,
  state = 'active'
) {

  if (!tab) return;

  if (tab.incognito) return;

  if (
    !/^https?:\/\//i.test(
      tab.url ?? ''
    )
  ) {
    return;
  }


  const observation = {

    event_id:
      crypto.randomUUID(),

    session_id:
      session.id,

    timestamp:
      new Date().toISOString(),

    state,

    reason,

    tab_id:
      tab.id,

    window_id:
      tab.windowId,

    url:
      tab.url,

    title:
      tab.title ?? '',

    favicon:
      tab.favIconUrl ?? '',

    audible:
      !!tab.audible,

    pinned:
      !!tab.pinned
  };


  await api.logWebsiteMetadata(
    observation
  );
}


// ============================================================
// DYNAMIC WEBPAGE CONTENT
// ============================================================

async function handleDynamicContent(
  message,
  sender
) {

  /*
    Dynamic content should only be evaluated
    while a focus session is running.
  */

  const session =
    await getRunningSession();


  if (!session) {
    return {
      error:
        'No active focus session.'
    };
  }


  /*
    Content scripts do not need to know their
    own Chrome tab ID.

    Chrome provides it through sender.tab.id.
  */

  const tabId =
    sender.tab?.id;


  if (!tabId) {

    return {
      error:
        'Could not determine tab ID.'
    };

  }


  const payload =
    message.payload;


  /*
    Expected structure:

    {
      page_type: "...",
      primary_content: {...},
      recommended_content: [...]
    }
  */

  if (
    !payload ||
    typeof payload !== 'object'
  ) {

    return {
      error:
        'Invalid dynamic content payload.'
    };

  }


  const primaryContent =
    payload.primary_content ?? null;


  const recommendedContent =
    Array.isArray(
      payload.recommended_content
    )
      ? payload.recommended_content
      : [];


  /*
    If there is nothing to evaluate,
    don't contact the backend.
  */

  if (
    !primaryContent &&
    recommendedContent.length === 0
  ) {

    return {
      primary_content: null,
      recommended_content: []
    };

  }


  /*
    Add information that the content script
    itself shouldn't need to provide.
  */

  const data = {

    tab_id:
      tabId,

    session_id:
      session.id,

    page_type:
      payload.page_type ??
      'dynamic_page',

    primary_content:
      primaryContent,

    recommended_content:
      recommendedContent

  };


  /*
    IMPORTANT:

    logDynamicContent() needs to RETURN the
    backend response.

    Example backend response:

    {
      primary_content: {...},
      recommended_content: [...]
    }

    That result gets sent back to youtube.js.
  */

  return await api.logDynamicContent(
    data
  );
}


// ============================================================
// TAB ACTIVATED
// ============================================================

async function handleTabActivated(
  activeInfo
) {

  const session =
    await getRunningSession();


  if (!session) return;


  let tab;


  try {

    tab = await chrome.tabs.get(
      activeInfo.tabId
    );

  } catch {

    return;

  }


  await sendTabObservation(
    tab,
    session,
    'tab_activated',
    'active'
  );
}


// ============================================================
// PAGE UPDATED
// ============================================================

async function handlePageUpdated(
  tabId,
  changeInfo,
  tab
) {

  /*
    Only care about the active tab.
  */

  if (!tab.active) {
    return;
  }


  /*
    Ignore Chrome updates that don't contain
    useful website metadata.
  */

  const meaningfulUpdate = (

    changeInfo.url !== undefined ||

    changeInfo.title !== undefined ||

    changeInfo.status ===
      'complete' ||

    changeInfo.audible !== undefined

  );


  if (!meaningfulUpdate) {
    return;
  }


  const session =
    await getRunningSession();


  if (!session) {
    return;
  }


  await sendTabObservation(
    tab,
    session,
    'page_updated',
    'active'
  );
}


// ============================================================
// TAB CLOSED
// ============================================================

async function handleTabClosed(
  tabId
) {

  const session =
    await getRunningSession();


  if (!session) {
    return;
  }


  /*
    The tab no longer exists.

    The backend already knows its URL/title
    from previous observations.

    We only need to tell it which tab closed.
  */

  await api.logWebsiteMetadata({

    event_id:
      crypto.randomUUID(),

    session_id:
      session.id,

    timestamp:
      new Date().toISOString(),

    state:
      'closed',

    reason:
      'tab_closed',

    tab_id:
      tabId

  });
}


// ============================================================
// WINDOW FOCUS
// ============================================================

async function handleWindowFocusChanged(
  windowId
) {

  const session =
    await getRunningSession();


  if (!session) {
    return;
  }


  /*
    Chrome lost focus entirely.
  */

  if (
    windowId ===
    chrome.windows.WINDOW_ID_NONE
  ) {

    await api.logWebsiteMetadata({

      event_id:
        crypto.randomUUID(),

      session_id:
        session.id,

      timestamp:
        new Date().toISOString(),

      state:
        'unfocused',

      reason:
        'window_focus_changed'

    });


    return;
  }


  /*
    Chrome gained focus.
  */

  let tabs;


  try {

    tabs =
      await chrome.tabs.query({

        active: true,

        windowId

      });

  } catch {

    return;

  }


  const tab =
    tabs[0];


  if (!tab) {
    return;
  }


  await sendTabObservation(
    tab,
    session,
    'window_focus_changed',
    'active'
  );
}


// ============================================================
// IDLE STATE
// ============================================================

async function handleIdleStateChanged(
  newState
) {

  const session =
    await getRunningSession();


  if (!session) {
    return;
  }


  /*
    User became idle or locked.
  */

  if (
    newState !==
    'active'
  ) {

    await api.logWebsiteMetadata({

      event_id:
        crypto.randomUUID(),

      session_id:
        session.id,

      timestamp:
        new Date().toISOString(),

      state:
        newState,

      reason:
        'idle_state_changed'

    });


    return;
  }


  /*
    User returned.

    Find the active tab in the focused
    Chrome window.
  */

  const windows =
    await chrome.windows.getAll({

      windowTypes:
        ['normal']

    });


  const focused =
    windows.find(
      window =>
        window.focused
    );


  if (!focused) {
    return;
  }


  const tabs =
    await chrome.tabs.query({

      active:
        true,

      windowId:
        focused.id

    });


  const tab =
    tabs[0];


  if (!tab) {
    return;
  }


  await sendTabObservation(
    tab,
    session,
    'idle_state_changed',
    'active'
  );
}


// ============================================================
// HEARTBEAT
// ============================================================

async function handleHeartbeat() {

  const session =
    await getRunningSession();


  if (!session) {
    return;
  }


  /*
    Heartbeat doesn't send the entire website
    metadata again.

    It simply tells the backend that the session
    is still alive and what the idle state is.
  */

  const idle =
    await chrome.idle.queryState(
      60
    );


  await api.logWebsiteMetadata({

    event_id:
      crypto.randomUUID(),

    session_id:
      session.id,

    timestamp:
      new Date().toISOString(),

    state:
      idle,

    reason:
      'heartbeat'

  });
}


// ============================================================
// CHROME EVENTS
// ============================================================

chrome.tabs.onActivated.addListener(
  activeInfo => {

    enqueue(
      () =>
        handleTabActivated(
          activeInfo
        )
    );

  }
);


chrome.tabs.onUpdated.addListener(
  (
    tabId,
    changeInfo,
    tab
  ) => {

    enqueue(
      () =>
        handlePageUpdated(
          tabId,
          changeInfo,
          tab
        )
    );

  }
);


chrome.tabs.onRemoved.addListener(
  tabId => {

    enqueue(
      () =>
        handleTabClosed(
          tabId
        )
    );

  }
);


chrome.windows.onFocusChanged.addListener(
  windowId => {

    enqueue(
      () =>
        handleWindowFocusChanged(
          windowId
        )
    );

  }
);


chrome.idle.onStateChanged.addListener(
  newState => {

    enqueue(
      () =>
        handleIdleStateChanged(
          newState
        )
    );

  }
);


// ============================================================
// DYNAMIC CONTENT MESSAGES
// ============================================================

chrome.runtime.onMessage.addListener(
  (
    message,
    sender,
    sendResponse
  ) => {

    /*
      Only handle dynamic-content messages here.
    */

    if (
      message.type !==
      'DYNAMIC_CONTENT'
    ) {
      return;
    }


    /*
      Only accept messages coming from this
      Chrome extension.
    */

    if (
      sender.id !==
      chrome.runtime.id
    ) {

      sendResponse({
        error:
          'Invalid extension sender.'
      });

      return;

    }


    /*
      IMPORTANT:

      We DON'T put this through the normal
      activity queue.

      The content script is waiting for the
      backend response so it can immediately
      blur/allow the YouTube cards.
    */

    handleDynamicContent(
      message,
      sender
    )
      .then(result => {

        sendResponse(
          result
        );

      })
      .catch(error => {

        console.error(
          'Dynamic content error:',
          error
        );


        sendResponse({

          error:
            error.message

        });

      });


    /*
      Keeps the Chrome message channel open
      while the async backend request runs.
    */

    return true;
  }
);


// ============================================================
// SESSION EVENTS
// ============================================================

chrome.runtime.onMessage.addListener(
  (
    message,
    sender,
    respond
  ) => {

    if (
      sender.id !==
      chrome.runtime.id
    ) {
      return;
    }


    const allowed = [

      'SESSION_START',

      'SESSION_PAUSE',

      'SESSION_RESUME',

      'SESSION_END'

    ];


    if (
      !allowed.includes(
        message.type
      )
    ) {
      return;
    }


    enqueue(
      async () => {

        const session =
          await getRunningSession();


        if (!session) {
          return;
        }


        await api.logWebsiteMetadata({

          event_id:
            crypto.randomUUID(),

          session_id:
            session.id,

          timestamp:
            new Date()
              .toISOString(),

          state:
            'session',

          reason:
            message.type
              .toLowerCase()

        });

      }
    ).then(
      () => {

        respond({
          ok: true
        });

      }
    );


    return true;
  }
);


// ============================================================
// IDLE SETTINGS
// ============================================================

chrome.idle.setDetectionInterval(
  60
);


// ============================================================
// HEARTBEAT ALARM
// ============================================================

chrome.alarms
  .get(
    'activity-heartbeat'
  )
  .then(
    alarm => {

      if (!alarm) {

        return chrome.alarms.create(
          'activity-heartbeat',
          {
            periodInMinutes:
              0.5
          }
        );

      }

    }
  )
  .catch(
    error => {

      console.warn(
        'Could not schedule activity heartbeat:',
        error.message
      );

    }
  );


chrome.alarms.onAlarm.addListener(
  alarm => {

    if (
      alarm.name !==
      'activity-heartbeat'
    ) {
      return;
    }


    enqueue(
      handleHeartbeat
    );

  }
);