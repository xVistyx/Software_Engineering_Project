import { NavigationBar } from '../components/NavigationBar.js';
import { Timer } from '../components/Timer.js';

const node = html => {
  const template = document.createElement('template');
  template.innerHTML = html.trim();
  return template.content.firstElementChild;
};

export function SessionPage({ navigate, state, api, bg }) {
  const page = node('<section class="screen active"><p class="sub">Loading session…</p></section>');
  let session = state.session;
  let timer = null;
  let disposed = false;
  let busy = false;
  let poll = null;
  page.dispose = () => { disposed = true; timer?.stop(); clearInterval(poll); };

  function showError(error) {
    page.querySelector('[data-error]')?.remove();
    const message = node('<p class="field-error show" data-error role="alert"></p>');
    message.textContent = error.message || 'Could not connect. Please try again.';
    page.append(message);
  }

  async function transition(action) {
    if (busy) return;
    busy = true;
    page.querySelectorAll('button').forEach(button => { button.disabled = true; });
    try {
      if (action === 'end') {
        const endResult = await api.endSession(session.id);
        const summary = endResult?.content ?? endResult;
        console.log('END SESSION SUMMARY:', summary);
        state.completedSessionSummary = summary;
        await bg('SESSION_END');
        await complete();
      } else {
        session = { ...session, ...await api.updateSession(session.id, { status: action }) };
        state.session = session;
        await bg(action === 'paused' ? 'SESSION_PAUSE' : 'SESSION_RESUME');
        renderSession();
      }
    } catch (error) { if (!disposed) showError(error); }
    finally {
      busy = false;
      page.querySelectorAll('button').forEach(button => { button.disabled = false; });
    }
  }

  function renderSession() {
    if (disposed) return;
    timer?.stop();
    page.replaceChildren();
    const paused = session.status === 'paused';
    page.append(NavigationBar({ title: session.topic, onNavigate: navigate }));
    if (paused) {
      const body = node('<div class="paused-body grow"><div class="pause-icon" aria-hidden="true"></div><h2>Session paused</h2><p class="sub">The timer and website tracking are paused.</p></div>');
      page.append(body);
      const resume = node('<button class="btn btn-primary">Resume session</button>');
      resume.addEventListener('click', () => transition('running'));
      page.append(resume);
    } else {
      timer = Timer({ seconds: session.time_remaining ?? session.time ?? session.seconds,
                      onComplete: sync });
      page.append(timer.el);
      timer.start();
      if (!(session.strict_mode ?? state.settings?.strictMode)) {
        const pause = node('<button class="btn btn-soft">Pause</button>');
        pause.addEventListener('click', () => transition('paused'));
        page.append(pause);
      } else {
        page.append(node('<p class="sub center">Strict mode is on. Your session ends when the timer finishes.</p>'));
      }
    }
    if (!(session.strict_mode ?? state.settings?.strictMode)) {
      const end = node(`<button class="btn btn-warn" style="margin-top:10px">${paused ? 'End session' : 'Stop session'}</button>`);
      end.addEventListener('click', () => transition('end'));
      page.append(end);
    }
  }

  async function complete() {
    timer?.stop();
    clearInterval(poll);
    if (disposed) return;

    // Preserve the completed id before clearing the active-session state.
    // SessionCompletePage owns fetching and rendering the final summary.
    state.completedSessionId = session.id;
    state.session = null;
    navigate('sessionComplete');
  }

  async function sync() {
    if (busy || disposed) return;
    busy = true;
    try {
      const latest = await api.getActiveSession();
      if (disposed) return;
      if (!latest?.id || latest.id !== session.id) { await complete(); return; }
      const changed = latest.status !== session.status;
      session = latest;
      state.session = latest;
      if (changed || !timer) renderSession();
      else timer.setRemaining(latest.time_remaining ?? latest.time);
      page.querySelector('[data-error]')?.remove();
    } catch (error) { if (!disposed) showError(error); }
    finally { busy = false; }
  }

  async function init() {
    try {
      const latest = await api.getActiveSession();
      if (disposed) return;
      if (!latest?.id) { navigate('start'); return; }
      session = latest;
      state.session = session;
      renderSession();
      poll = setInterval(sync, 5000);
    } catch (error) {
      if (disposed) return;
      page.replaceChildren(NavigationBar({ left: { label: 'Back to home', page: 'start' }, right: null, onNavigate: navigate }));
      showError(error);
      const retry = node('<button class="btn btn-soft">Retry</button>');
      retry.addEventListener('click', init);
      page.append(retry);
    }
  }
  init();
  return page;
}
