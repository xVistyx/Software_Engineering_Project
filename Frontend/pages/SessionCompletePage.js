const node = html => {
  const template = document.createElement('template');
  template.innerHTML = html.trim();
  return template.content.firstElementChild;
};

const formatDuration = seconds => {
  const value = Math.max(0, Math.round(Number(seconds) || 0));
  if (value < 60) return `${value}s`;
  const minutes = Math.floor(value / 60);
  const remainder = value % 60;
  return remainder ? `${minutes}m ${remainder}s` : `${minutes}m`;
};

const firstNumber = (...values) => {
  for (const value of values) {
    const number = Number(value);
    if (Number.isFinite(number)) return number;
  }
  return 0;
};

function normalizeSummary(summary = {}) {
  // Accept either the raw summary or an API envelope like { content: {...} }.
  // Some backend layers may wrap the payload more than once.
  while (summary && typeof summary === 'object' && summary.content && typeof summary.content === 'object') {
    summary = summary.content;
  }

  return {
    score: Math.max(0, Math.min(100, Math.round(firstNumber(
      summary.score,
      summary.sessionScore,
      summary.session_score,
    )))),

    // focusedSeconds is kept as a backwards-compatible fallback because the
    // current frontend already treats it as the completed session duration.
    sessionSeconds: firstNumber(
      summary.sessionTimeSeconds,
      summary.session_time_seconds,
      summary.focusedSeconds,
      summary.sessionSeconds,
    ),

    productiveSeconds: firstNumber(
      summary.productiveTimeSeconds,
      summary.productive_time_seconds,
      summary.productiveSeconds,
    ),

    distractionsBlocked: Math.max(0, Math.round(firstNumber(
      summary.distractionsBlocked,
      summary.distractions_blocked,
      summary.blockedCount,
    ))),

    tabsOpened: Math.max(0, Math.round(firstNumber(
      summary.tabsOpened,
      summary.tabs_opened,
      summary.tabCount,
    ))),
  };
}

function scoreAppearance(score) {
  if (score >= 75) {
    return { color: '#27b765', track: '#e5f5eb', message: 'Great focus!' };
  }
  if (score >= 50) {
    return { color: '#df962b', track: '#fff0d7', message: 'Solid effort' };
  }
  return { color: '#d95656', track: '#fbe7e7', message: 'Room to improve' };
}

const icons = {
  clock: '<svg class="summary-icon" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="8.5"/><path d="M12 7.5v5l3.2 2"/></svg>',
  productive: '<svg class="summary-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 17v-4M12 17V8M18 17V5"/></svg>',
  shield: '<svg class="summary-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3.5 19 6v5.3c0 4.4-2.8 7.5-7 9.2-4.2-1.7-7-4.8-7-9.2V6l7-2.5Z"/></svg>',
  tabs: '<svg class="summary-icon" viewBox="0 0 24 24" aria-hidden="true"><rect x="5" y="7" width="11" height="10" rx="1.5"/><rect x="9" y="4" width="10" height="10" rx="1.5"/></svg>',
};

function metricCard(icon, value, label) {
  const card = node(`<div class="session-summary-card">
    <span class="summary-icon-wrap">${icons[icon]}</span>
    <span class="summary-card-copy"><strong></strong><span></span></span>
  </div>`);
  card.querySelector('strong').textContent = value;
  card.querySelector('.summary-card-copy > span').textContent = label;
  return card;
}

export function SessionCompletePage({ navigate, state, api }) {
  const page = node('<section class="screen active session-complete-screen"></section>');
  let disposed = false;
  const sessionId = state.completedSessionId;

  page.dispose = () => { disposed = true; };

  const renderError = error => {
    page.replaceChildren();
    const wrap = node(`<div class="session-complete-error grow">
      <div class="complete-mark" aria-hidden="true">
        <svg class="icon" viewBox="0 0 24 24"><path d="m6 12 4 4 8-8"/></svg>
      </div>
      <h2>Session complete</h2>
      <p class="sub center">The session ended, but its summary could not be loaded.</p>
      <p class="field-error show" role="alert"></p>
      <button class="btn btn-soft" data-retry>Retry</button>
      <button class="btn btn-primary" data-done>Done</button>
    </div>`);
    wrap.querySelector('.field-error').textContent = error?.message || 'Could not load session summary.';
    wrap.querySelector('[data-retry]').addEventListener('click', load);
    wrap.querySelector('[data-done]').addEventListener('click', () => {
      state.completedSessionId = null;
      state.completedSessionSummary = null;
      navigate('start');
    });
    page.append(wrap);
  };

  const renderSummary = rawSummary => {
    const summary = normalizeSummary(rawSummary);
    const appearance = scoreAppearance(summary.score);

    page.replaceChildren();

    const top = node(`<div class="session-complete-main grow">
      <div class="session-complete-mark" aria-hidden="true">
        <svg class="icon" viewBox="0 0 24 24"><path d="m6 12 4 4 8-8"/></svg>
        <span class="spark spark-1"></span><span class="spark spark-2"></span>
        <span class="spark spark-3"></span><span class="spark spark-4"></span>
      </div>
      <header class="session-complete-heading">
        <h1>Session complete</h1>
        <p>Great work! Here’s how it went.</p>
      </header>
      <div class="session-score-ring" role="img" aria-label="Session score"></div>
      <div class="session-summary-grid"></div>
    </div>`);

    const ring = top.querySelector('.session-score-ring');
    ring.style.setProperty('--score-color', appearance.color);
    ring.style.setProperty('--score-track', appearance.track);
    ring.innerHTML = `
      <svg class="score-ring-svg" viewBox="0 0 120 120" aria-hidden="true">
        <circle class="score-ring-track" cx="60" cy="60" r="51" pathLength="100" />
        <circle class="score-ring-progress" cx="60" cy="60" r="51" pathLength="100" />
      </svg>
      <div class="score-ring-copy">
        <strong data-score></strong>
        <span>Session Score</span>
        <em data-message></em>
      </div>`;
    ring.querySelector('.score-ring-progress').style.strokeDasharray = `${summary.score} 100`;
    ring.querySelector('[data-score]').textContent = summary.score;
    ring.querySelector('[data-message]').textContent = appearance.message;

    const grid = top.querySelector('.session-summary-grid');
    grid.append(
      metricCard('clock', formatDuration(summary.sessionSeconds), 'Session time'),
      metricCard('productive', formatDuration(summary.productiveSeconds), 'Productive time'),
      metricCard('shield', summary.distractionsBlocked, 'Distractions blocked'),
      metricCard('tabs', summary.tabsOpened, 'Tabs opened'),
    );

    const details = node('<button class="btn btn-soft session-complete-details">View session details</button>');
    details.addEventListener('click', () => {
      state.historySessionId = sessionId;
      navigate('history');
    });

    const done = node('<button class="btn btn-primary session-complete-done">Done</button>');
    done.addEventListener('click', () => {
      state.completedSessionId = null;
      state.completedSessionSummary = null;
      navigate('start');
    });

    page.append(top, details, done);
  };

  async function load() {
  if (!sessionId) {
    navigate('start');
    return;
  }

  page.replaceChildren(
    node('<div class="session-complete-loading grow"><p class="sub center">Loading session summary…</p></div>')
  );

  try {
    let summary = state.completedSessionSummary;

    if (!summary) {
      summary = await api.getSummary(sessionId);
    }

    // Be tolerant of a backend response wrapped as { content: {...} }.
    while (summary && typeof summary === 'object' && summary.content && typeof summary.content === 'object') {
      summary = summary.content;
    }

    console.log('SESSION COMPLETE SUMMARY:', summary);

    if (!disposed) {
      renderSummary(summary);
    }
  } catch (error) {
    if (!disposed) {
      renderError(error);
    }
  }
}

  load();
  return page;
}
