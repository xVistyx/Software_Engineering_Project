/* ============================================================
   pages/StartPage.js — home + new-session setup.
   (merges prototype screens 1 Welcome, 2 Start, 6 Past)
   ctx = { navigate, state, api, bg }
   ============================================================ */

import { NavigationBar } from '../components/NavigationBar.js';

const node = (html) => {
  const t = document.createElement('template');
  t.innerHTML = html.trim();
  return t.content.firstElementChild;
};

export function StartPage(ctx) {
  const { navigate, state, api, bg } = ctx;
  let minutes = state.settings?.defaultMinutes ?? 45;

  const page = node(`<section class="screen active"></section>`);
  page.append(NavigationBar({ onNavigate: navigate }));

  page.append(node(`
    <div style="margin:16px 0 22px">
      <div class="eyebrow">🌿 Grove</div>
      <h1>Ready to focus?</h1>
      <p class="sub">Start a session and I'll block the noise while you work.</p>
    </div>`));

  /* --- topic (required) --- */
  const topicBlock = node(`
    <div>
      <label class="field">What are you working on? <span style="color:var(--accent)">*</span></label>
      <input class="input" data-topic placeholder="Be specific — e.g. Calculus revision" />
      <div class="field-error" data-topic-err>Add a specific topic to start your session.</div>
    </div>`);
  const topicInput = topicBlock.querySelector('[data-topic]');
  const topicErr   = topicBlock.querySelector('[data-topic-err]');
  topicInput.addEventListener('input', () => {
    if (topicInput.value.trim()) { topicInput.classList.remove('invalid'); topicErr.classList.remove('show'); }
  });

  /* --- length chips + custom --- */
  const lenBlock = node(`
    <div style="margin-top:14px">
      <label class="field">Session length</label>
      <div class="chips" data-chips>
        ${[45, 60, 75, 90].map((m) => `<div class="timechip" data-min="${m}">${m}m</div>`).join('')}
      </div>
      <input class="input custominput" data-custom type="number" min="1"
             placeholder="Or enter your own time (minutes)" style="margin-top:10px" />
    </div>`);
  const chips  = [...lenBlock.querySelectorAll('.timechip')];
  const custom = lenBlock.querySelector('[data-custom]');
  const selectChip = (chosen) => {
    chips.forEach((c) => c.classList.remove('sel'));
    custom.classList.remove('sel');
    if (chosen === custom) { custom.classList.add('sel'); }
    else { chosen.classList.add('sel'); minutes = +chosen.dataset.min; }
  };
  chips.forEach((c) => c.addEventListener('click', () => selectChip(c)));
  custom.addEventListener('input', () => { selectChip(custom); const v = +custom.value; if (v > 0) minutes = v; });
  (chips.find((c) => +c.dataset.min === minutes) || chips[0]).classList.add('sel');

  page.append(node(`<div class="stack"></div>`));
  page.querySelector('.stack').append(topicBlock, lenBlock);

  /* --- start --- */
  const startBtn = node(`<button class="btn btn-primary" style="margin-top:18px">Start session</button>`);
  startBtn.addEventListener('click', async () => {
    const topic = topicInput.value.trim();
    if (!topic) { topicInput.classList.add('invalid'); topicErr.classList.add('show'); topicInput.focus(); return; }
    startBtn.disabled = true; startBtn.textContent = 'Starting…';
    try {
      const s = await api.createSession({ topic, minutes });
      await bg('SESSION_START', { sessionId: s.id, seconds: minutes * 60 });
      state.session = { id: s.id, topic, minutes, seconds: minutes * 60 };
      navigate('session');
    } catch (error) {
    console.error("START SESSION ERROR:", error);

    startBtn.disabled = false;
    startBtn.textContent = 'Start session';
    alert('Could not start session. Check console.');
}
  });
  page.append(startBtn);

  /* --- recent progress (was screen 6) --- */
  const recent = node(`<div style="margin-top:26px"><p class="sub"><b>Your progress</b></p></div>`);
  page.append(recent);
  Promise.all([api.getStats(), api.listSessions()]).then(([stats, sessions]) => {
    recent.append(node(`
      <div class="stat-grid">
        <div class="stat"><div class="num">${stats.total}</div><div class="cap">Sessions total</div></div>
        <div class="stat good"><div class="num">${stats.thisWeek}</div><div class="cap">This week</div></div>
        <div class="stat"><div class="num">${stats.focusedHours}h</div><div class="cap">Focused time</div></div>
        <div class="stat warn"><div class="num">${stats.peakDriftHour}</div><div class="cap">Peak drift hour</div></div>
      </div>`));
    const rows = node(`<div style="margin-top:14px"></div>`);
    sessions.forEach((s) => rows.append(node(`<div class="listrow">${s.topic} <span>${s.minutes}m · ${s.score}</span></div>`)));
    recent.append(rows);
  });

  return page;
}
