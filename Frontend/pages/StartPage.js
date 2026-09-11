import { NavigationBar } from '../components/NavigationBar.js';

const node = (html) => {
  const t = document.createElement('template');
  t.innerHTML = html.trim();
  return t.content.firstElementChild;
};

export function StartPage({ navigate, state, api, bg }) {
  let minutes = state.settings?.defaultMinutes ?? 45;
  const page = node('<section class="screen active"></section>');
  page.append(NavigationBar({ onNavigate: navigate }));
  page.append(node(`<header class="intro">
    <p class="eyebrow">New session</p>
    <h1>Ready to focus?</h1>
    <p class="sub">Choose a task. Give it your full attention.</p>
  </header>`));
  const form = node(`<form novalidate>
    <label class="field" for="session-topic">What are you working on?</label>
    <input class="input" id="session-topic" name="topic" placeholder="e.g. Calculus revision" required maxlength="160" aria-describedby="topic-error" autocomplete="off" />
    <p class="field-error" id="topic-error" role="alert">Add a topic to start your session.</p>
    <fieldset class="length-field">
      <legend class="field">Session length</legend>
      <div class="chips" aria-label="Preset durations">
        ${[45, 60, 75, 90].map(m => `<button type="button" class="timechip" data-min="${m}" aria-pressed="false" aria-label="${m} minutes">${m}<small>min</small></button>`).join('')}
      </div>
      <div class="custom-length">
        <label for="custom-minutes">Or set your own</label>
        <div class="custom-control"><input class="input custominput" id="custom-minutes" type="number" min="1" max="480" step="1" placeholder="—" aria-describedby="duration-error" /><span>min</span></div>
      </div>
      <p class="field-error" id="duration-error" role="alert">Enter a whole number from 1 to 480 minutes.</p>
    </fieldset>
    <button class="btn btn-primary start-button" type="submit"><span>Start session</span><svg class="icon" viewBox="0 0 20 20" aria-hidden="true"><path d="M3 10h13m-5-5 5 5-5 5"/></svg></button>
    <p class="field-error" data-request-error role="alert"></p>
  </form>`);
  const topic = form.querySelector('#session-topic');
  const topicError = form.querySelector('#topic-error');
  const custom = form.querySelector('#custom-minutes');
  const durationError = form.querySelector('#duration-error');
  const chips = [...form.querySelectorAll('[data-min]')];
  const paintDuration = () => {
    chips.forEach(chip => {
      const selected = custom.value === '' && +chip.dataset.min === minutes;
      chip.classList.toggle('sel', selected);
      chip.setAttribute('aria-pressed', String(selected));
    });
    custom.classList.toggle('sel', custom.value !== '');
  };
  if (![45, 60, 75, 90].includes(minutes)) custom.value = minutes;
  paintDuration();
  chips.forEach(chip => chip.addEventListener('click', () => {
    minutes = +chip.dataset.min;
    custom.value = '';
    custom.removeAttribute('aria-invalid');
    durationError.classList.remove('show');
    paintDuration();
  }));
  custom.addEventListener('input', () => {
    minutes = custom.value === '' ? (state.settings?.defaultMinutes ?? 45) : +custom.value;
    paintDuration();
    durationError.classList.remove('show');
    custom.removeAttribute('aria-invalid');
  });
  topic.addEventListener('input', () => {
    topic.classList.remove('invalid');
    topic.removeAttribute('aria-invalid');
    topicError.classList.remove('show');
  });
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (!topic.value.trim()) {
      topic.classList.add('invalid');
      topic.setAttribute('aria-invalid', 'true');
      topicError.classList.add('show');
      topic.focus();
      return;
    }
    if (!Number.isInteger(minutes) || minutes < 1 || minutes > 480) {
      durationError.classList.add('show');
      custom.setAttribute('aria-invalid', 'true');
      custom.focus();
      return;
    }
    const button = form.querySelector('[type="submit"]');
    const label = button.querySelector('span');
    const error = form.querySelector('[data-request-error]');
    error.classList.remove('show');
    button.disabled = true;
    label.textContent = 'Starting…';
    try {
      const session = await api.createSession({ topic: topic.value.trim(), minutes });
      await bg('SESSION_START', { sessionId: session.id, seconds: minutes * 60 });
      state.session = { id: session.id, topic: topic.value.trim(), minutes, seconds: minutes * 60 };
      navigate('session');
    } catch {
      error.textContent = 'Could not start the session. Check your connection and try again.';
      error.classList.add('show');
      button.disabled = false;
      label.textContent = 'Start session';
    }
  });
  page.append(form);
  const recent = node(`<section class="progress-section" aria-label="Your progress">
    <div class="section-heading"><h2>Your progress</h2><span>At a glance</span></div>
    <p class="empty-state" data-loading>Loading your progress…</p>
  </section>`);
  page.append(recent);
  Promise.all([api.getStats(), api.listSessions()]).then(([stats, sessions]) => {
    recent.querySelector('[data-loading]').remove();
    if (!Array.isArray(sessions) || typeof stats?.total !== 'number') throw new Error('Progress unavailable');
    const grid = node('<div class="stat-grid"></div>');
    [[stats.total, 'Sessions total'], [stats.thisWeek, 'This week'], [`${stats.focusedHours}h`, 'Session time'], [stats.trackedSites ?? '—', 'Websites visited']].forEach(([value, caption]) => {
      const stat = node('<div class="stat"><div class="num"></div><div class="cap"></div></div>');
      stat.querySelector('.num').textContent = value ?? '—';
      stat.querySelector('.cap').textContent = caption;
      grid.append(stat);
    });
    recent.append(grid);
    const history = node('<div class="history"><div class="section-heading"><h2>Recent sessions</h2><span>Session time</span></div></div>');
    if (!sessions.length) history.append(node('<p class="empty-state">Your completed sessions will appear here.</p>'));
    sessions.slice(0, 3).forEach(session => {
      const row = node('<div class="listrow"><span></span><span class="session-meta"><span data-minutes></span><span class="score-value"></span></span></div>');
      row.firstElementChild.textContent = session.topic;
      row.querySelector('[data-minutes]').textContent = `${session.minutes} min`;
      row.querySelector('.score-value').remove();
      history.append(row);
    });
    recent.append(history);
  }).catch(() => {
    recent.querySelector('[data-loading]')?.remove();
    recent.append(node('<p class="empty-state">Your progress is unavailable right now. You can still start a session.</p>'));
  });
  return page;
}
