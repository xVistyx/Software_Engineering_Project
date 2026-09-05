/* ============================================================
   components/Timer.js — the running-session countdown dial.
   Factory returns { el, start, pause, resume, stop, setScore,
   elapsed, remaining }. SessionPage drives it.

   NOTE: in production the timer should live in the background
   service worker (survives popup close) and push TICK/SCORE
   messages; this local interval is the prototype fallback.
   ============================================================ */

const node = (html) => {
  const t = document.createElement('template');
  t.innerHTML = html.trim();
  return t.content.firstElementChild;
};

export function Timer({ seconds, onComplete }) {
  let remaining = seconds;
  let score     = 100;
  let tick      = null;

  const el = node(`
    <div class="dial grow" style="justify-content:center">
      <div class="time-label">Time remaining</div>
      <div class="time-big" data-clock>00:00</div>
      <div class="score-row">🔥 Focus score <b data-score>100</b></div>
    </div>`);

  const clockEl = el.querySelector('[data-clock]');
  const scoreEl = el.querySelector('[data-score]');

  const fmt   = (s) => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
  const paint = () => { clockEl.textContent = fmt(remaining); scoreEl.textContent = score; };

  const start = () => {
    clearInterval(tick);
    tick = setInterval(() => {
      if (remaining > 0) { remaining--; paint(); }
      else { clearInterval(tick); onComplete?.(); }
    }, 1000);
  };
  const pause = () => clearInterval(tick);
  const stop  = () => clearInterval(tick);

  paint();

  return {
    el, start, pause, resume: start, stop,
    setScore: (s) => { score = s; paint(); },     // called from background SCORE msgs
    elapsed:  ()  => seconds - remaining,
    get remaining() { return remaining; },
  };
}
