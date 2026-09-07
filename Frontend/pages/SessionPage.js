/* ============================================================
   pages/SessionPage.js — the active session.
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

  const page = node(`
    <section class="screen active">
      <p class="center">Loading session...</p>
    </section>
  `);

  let session = null;
  let timer = null;

  const strict = !!state.settings?.strictMode;

  function view(html) {
    page.innerHTML = '';
    page.append(html);
  }

  /* ==========================================================
     INITIALIZE SESSION
     ========================================================== */

  async function init() {
    try {

      // Always ask backend for the currently active session
      const backendSession = await api.getActiveSession();

      console.log("ACTIVE SESSION FROM BACKEND:", backendSession);

      if (!backendSession) {
        console.log("No active session found");
        state.session = null;
        navigate('start');
        return;
      }

      /*
       Backend stores time in MINUTES.
       Timer component expects SECONDS.
      */
      session = {
        ...backendSession,

        seconds:
          backendSession.time_remaining !== undefined
            ? backendSession.time_remaining 
            : backendSession.time 
      };

      // Rebuild frontend state
      state.session = session;

      console.log("RESTORED FRONTEND SESSION:", session);

      // Create timer only AFTER we have valid backend data
      timer = Timer({
        seconds: session.seconds,
        onComplete: () => finish()
      });

      // Check if session was paused
      if (
        session.status === 'paused' ||
        session.is_running === false
      ) {
        paused();
      } else {
        running();
        timer.start();
      }

    } catch (error) {

      console.error("Failed to restore active session:", error);

      /*
       Optional fallback:
       If state.session still exists, use it.
      */
      if (state.session && state.session.seconds !== undefined) {

        session = state.session;

        timer = Timer({
          seconds: session.seconds,
          onComplete: () => finish()
        });

        running();
        timer.start();

      } else {
        state.session = null;
        navigate('start');
      }
    }
  }


  /* ==========================================================
     RUNNING
     ========================================================== */

  function running() {

    const v = node(`
      <div class="grow"
           style="display:flex;flex-direction:column">
      </div>
    `);

    v.append(
      NavigationBar({
        title: '🌿 ' + session.topic,
        onNavigate: navigate
      })
    );

    v.append(timer.el);

    const controls = node(`<div class="stack"></div>`);

    if (!strict) {

      const pause = node(`
        <button class="btn btn-soft">
          Pause
        </button>
      `);

      const stop = node(`
        <button class="btn btn-warn">
          Stop session
        </button>
      `);

      pause.addEventListener('click', async () => {

        timer.pause();

        await api.updateSession(
          session.id,
          { status: 'paused' }
        );

        await bg('SESSION_PAUSE');

        paused();
      });

      stop.addEventListener('click', () => finish());

      controls.append(pause, stop);

    } else {

      controls.append(
        node(`
          <p class="sub center">
            Strict mode on — you can't stop early. 💪
          </p>
        `)
      );
    }

    v.append(controls);

    view(v);
  }


  /* ==========================================================
     PAUSED
     ========================================================== */

  function paused() {

    if (timer) {
      timer.pause();
    }

    const v = node(`
      <div class="grow"
           style="
             display:flex;
             flex-direction:column;
             align-items:center;
             justify-content:center;
             text-align:center;
             gap:18px
           ">

        <div class="pause-icon" aria-hidden="true"></div>

        <h2>Session paused</h2>

        <p class="sub">
          Your timer is on hold.
          Come back when you're ready.
        </p>

      </div>
    `);

    const resume = node(`
      <button
        class="btn btn-primary"
        style="width:220px">
        Resume session
      </button>
    `);

    const end = node(`
      <button
        class="btn btn-ghost"
        style="width:220px">
        End session
      </button>
    `);

    resume.addEventListener('click', async () => {

      await api.updateSession(
        session.id,
        { status: 'running' }
      );

      await bg('SESSION_RESUME');

      timer.resume();

      running();
    });

    end.addEventListener('click', () => finish());

    v.append(resume, end);

    view(v);
  }


  /* ==========================================================
     COMPLETE
     ========================================================== */

  async function finish() {

    if (timer) {
      timer.stop();
    }

    try {

      await api.endSession(session.id);

      await bg('SESSION_END');

    } catch (error) {

      console.error(
        "Failed to end session:",
        error
      );
    }

    let sum;

    try {

      sum = await api.getSummary(session.id);

    } catch {

      sum = {
        focusedSeconds: timer ? timer.elapsed() : 0,
        tabsBlocked: 0,
        driftCount: 0,
        score: 88,
        longestStreakMin: 0
      };
    }

    const v = node(`
      <section
        style="
          display:flex;
          flex-direction:column;
          flex:1
        ">

        <div
          class="center"
          style="margin:10px 0 4px">

          <div class="pause-emoji">
            🎉
          </div>

          <h2>
            Session complete
          </h2>

          <p class="sub">
            You focused for
            <b>
              ${Math.round(sum.focusedSeconds / 60)}
              minutes
            </b>.
          </p>

        </div>

        <div class="stat-grid">

          <div class="stat good">
            <div class="num">
              ${sum.tabsBlocked}
            </div>
            <div class="cap">
              Tabs blocked
            </div>
          </div>

          <div class="stat warn">
            <div class="num">
              ${sum.driftCount}
            </div>
            <div class="cap">
              Times you drifted
            </div>
          </div>

          <div class="stat">
            <div class="num">
              ${sum.score}
            </div>
            <div class="cap">
              Focus score
            </div>
          </div>

          <div class="stat">
            <div class="num">
              ${sum.longestStreakMin}m
            </div>
            <div class="cap">
              Longest streak
            </div>
          </div>

        </div>

        <div class="grow"></div>

      </section>
    `);

    const done = node(`
      <button class="btn btn-primary">
        Done
      </button>
    `);

    done.addEventListener('click', () => {

      state.session = null;

      navigate('start');
    });

    v.append(done);

    view(v);
  }


  /* ==========================================================
     START PAGE
     ========================================================== */

  init();

  return page;
}