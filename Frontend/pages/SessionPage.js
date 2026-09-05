/* ============================================================
   pages/SessionPage.js — the active session.
   (merges prototype screens 3 Running, 7 Paused, 4 Overview)
   Sub-states: 'running' → 'paused' → 'running' | 'complete'.
   ctx = { navigate, state, api, bg }
   ============================================================ */

import { NavigationBar } from '../components/NavigationBar.js';
import { Timer }         from '../components/Timer.js';

const node = (html) => {
  const t = document.createElement('template');
  t.innerHTML = html.trim();
  return t.content.firstElementChild;
};

export function SessionPage(ctx) {
  const { navigate, state, api, bg } = ctx;
  const session = state.session;
  const strict  = !!state.settings?.strictMode;

  const page = node(`<section class="screen active"></section>`);

  const timer = Timer({ seconds: session.seconds, onComplete: () => finish() });

  function view(html) { page.innerHTML = ''; page.append(html); }

  /* ---- RUNNING ---- */
  function running() {
    const v = node(`<div class="grow" style="display:flex;flex-direction:column"></div>`);
    v.append(NavigationBar({ title: '🌿 ' + session.topic, onNavigate: navigate }));
    v.append(timer.el);

    const controls = node(`<div class="stack"></div>`);
    if (!strict) {
      const pause = node(`<button class="btn btn-soft">Pause</button>`);
      const stop  = node(`<button class="btn btn-warn">Stop session</button>`);
      pause.addEventListener('click', async () => {
        timer.pause(); await api.updateSession(session.id, { status: 'paused' }); await bg('SESSION_PAUSE'); paused();
      });
      stop.addEventListener('click', () => finish());
      controls.append(pause, stop);
    } else {
      controls.append(node(`<p class="sub center">Strict mode on — you can't stop early. 💪</p>`));
    }
    v.append(controls);
    view(v);
  }

  /* ---- PAUSED ---- */
  function paused() {
    const v = node(`
      <div class="grow" style="display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;gap:18px">
        <div class="pause-icon" aria-hidden="true"></div>
        <h2>Session paused</h2>
        <p class="sub">Your timer is on hold. Come back when you're ready.</p>
      </div>`);
    const resume = node(`<button class="btn btn-primary" style="width:220px">Resume session</button>`);
    const end    = node(`<button class="btn btn-ghost" style="width:220px">End session</button>`);
    resume.addEventListener('click', async () => {
      await api.updateSession(session.id, { status: 'running' }); await bg('SESSION_RESUME'); timer.resume(); running();
    });
    end.addEventListener('click', () => finish());
    v.append(resume, end);
    view(v);
  }

  /* ---- COMPLETE (overview) ---- */
  async function finish() {
    timer.stop();
    try { await api.endSession(session.id); await bg('SESSION_END'); } catch {}
    let sum;
    try { sum = await api.getSummary(session.id); }
    catch { sum = { focusedSeconds: timer.elapsed(), tabsBlocked: 0, driftCount: 0, score: timer.remaining >= 0 ? 88 : 0, longestStreakMin: 0 }; }

    const v = node(`
      <section style="display:flex;flex-direction:column;flex:1">
        <div class="center" style="margin:10px 0 4px">
          <div class="pause-emoji">🎉</div>
          <h2>Session complete</h2>
          <p class="sub">You focused for <b>${Math.round(sum.focusedSeconds / 60)} minutes</b>.</p>
        </div>
        <div class="stat-grid">
          <div class="stat good"><div class="num">${sum.tabsBlocked}</div><div class="cap">Tabs blocked</div></div>
          <div class="stat warn"><div class="num">${sum.driftCount}</div><div class="cap">Times you drifted</div></div>
          <div class="stat"><div class="num">${sum.score}</div><div class="cap">Focus score</div></div>
          <div class="stat"><div class="num">${sum.longestStreakMin}m</div><div class="cap">Longest streak</div></div>
        </div>
        <div class="grow"></div>
      </section>`);
    const done = node(`<button class="btn btn-primary">Done</button>`);
    done.addEventListener('click', () => { state.session = null; navigate('start'); });
    v.append(done);
    view(v);
  }

  /* start the clock on mount */
  running();
  timer.start();

  return page;
}
