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

  const session = await api.getActiveSession();

  if (!session?.id || !session.is_running) {
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

  if (!/^https?:\/\//i.test(tab.url ?? '')) return;


  const observation = {

    event_id: crypto.randomUUID(),

    session_id: session.id,

    timestamp: new Date().toISOString(),

    state,

    reason,

    tab_id: tab.id,

    window_id: tab.windowId,

    url: tab.url,

    title: tab.title ?? '',

    favicon: tab.favIconUrl ?? '',

    audible: !!tab.audible,

    pinned: !!tab.pinned
  };


  await api.logWebsiteMetadata(
    observation
  );
}


// ============================================================
// TAB ACTIVATED
// ============================================================

async function handleTabActivated(
  activeInfo
) {

  const session = await getRunningSession();

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

  // Only care about active tab
  if (!tab.active) return;


  // Ignore updates that don't affect useful metadata
  const meaningfulUpdate = (
    changeInfo.url !== undefined ||
    changeInfo.title !== undefined ||
    changeInfo.status === 'complete' ||
    changeInfo.audible !== undefined
  );


  if (!meaningfulUpdate) return;


  const session = await getRunningSession();

  if (!session) return;


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

  const session = await getRunningSession();

  if (!session) return;


  /*
    The tab no longer exists here.

    That's fine.

    The backend already knows this tab's metadata from previous
    events. We only need to tell it WHICH tab closed.
  */

  await api.logWebsiteMetadata({

    event_id: crypto.randomUUID(),

    session_id: session.id,

    timestamp: new Date().toISOString(),

    state: 'closed',

    reason: 'tab_closed',

    tab_id: tabId

  });
}


// ============================================================
// WINDOW FOCUS
// ============================================================

async function handleWindowFocusChanged(
  windowId
) {

  const session = await getRunningSession();

  if (!session) return;


  // Chrome lost focus entirely
  if (
    windowId === chrome.windows.WINDOW_ID_NONE
  ) {

    await api.logWebsiteMetadata({

      event_id: crypto.randomUUID(),

      session_id: session.id,

      timestamp: new Date().toISOString(),

      state: 'unfocused',

      reason: 'window_focus_changed'

    });

    return;
  }


  // Chrome gained focus
  let tabs;

  try {

    tabs = await chrome.tabs.query({
      active: true,
      windowId
    });

  } catch {

    return;
  }


  const tab = tabs[0];

  if (!tab) return;


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

  const session = await getRunningSession();

  if (!session) return;


  if (newState !== 'active') {

    await api.logWebsiteMetadata({

      event_id: crypto.randomUUID(),

      session_id: session.id,

      timestamp: new Date().toISOString(),

      state: newState,

      reason: 'idle_state_changed'

    });

    return;
  }


  // User returned
  const windows = await chrome.windows.getAll({
    windowTypes: ['normal']
  });


  const focused = windows.find(
    window => window.focused
  );


  if (!focused) return;


  const tabs = await chrome.tabs.query({
    active: true,
    windowId: focused.id
  });


  const tab = tabs[0];

  if (!tab) return;


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

  const session = await getRunningSession();

  if (!session) return;


  /*
    Important:

    Heartbeat does NOT send website metadata anymore.

    Otherwise your timer page changing its title every second
    can cause a constant stream of DB updates.

    The heartbeat is only useful for general activity state.
  */

  const idle = await chrome.idle.queryState(
    60
  );


  await api.logWebsiteMetadata({

    event_id: crypto.randomUUID(),

    session_id: session.id,

    timestamp: new Date().toISOString(),

    state: idle,

    reason: 'heartbeat'

  });
}


// ============================================================
// CHROME EVENTS
// ============================================================

chrome.tabs.onActivated.addListener(
  activeInfo => {

    enqueue(
      () => handleTabActivated(
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
      () => handlePageUpdated(
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
      () => handleTabClosed(
        tabId
      )
    );

  }
);


chrome.windows.onFocusChanged.addListener(
  windowId => {

    enqueue(
      () => handleWindowFocusChanged(
        windowId
      )
    );

  }
);


chrome.idle.onStateChanged.addListener(
  newState => {

    enqueue(
      () => handleIdleStateChanged(
        newState
      )
    );

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
      sender.id !== chrome.runtime.id
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


        if (!session) return;


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
      () => respond({
        ok: true
      })
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
            periodInMinutes: 0.5
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
      alarm.name
      !== 'activity-heartbeat'
    ) {
      return;
    }


    enqueue(
      handleHeartbeat
    );

  }
);