import { NavigationBar } from '../components/NavigationBar.js';

const node = html => {
  const template = document.createElement('template');
  template.innerHTML = html.trim();
  return template.content.firstElementChild;
};
const duration = seconds => {
  const value = Math.round(seconds ?? 0);
  return value < 60 ? `${value}s` : `${Math.floor(value / 60)}m ${value % 60}s`;
};
const date = value => value ? new Date(value).toLocaleString() : 'Still active';

function download(name, content, type) {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = name;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// Quoting alone does not prevent a spreadsheet from executing cell formulas.
const csvCell = value => {
  let text = String(value ?? '');
  if (/^[\s]*[=+@-]/.test(text) || /^[\t\r\n]/.test(text)) text = "'" + text;
  return '"' + text.replaceAll('"', '""') + '"';
};

export function HistoryPage({ navigate, state, api }) {
  const page = node('<section class="screen active"></section>');
  let disposed = false;
  page.dispose = () => { disposed = true; };

  function errorMessage(error) {
    if (disposed) return;
    page.querySelector('[data-error]')?.remove();
    const message = node('<p class="field-error show" data-error role="alert"></p>');
    message.textContent = error.message || 'History could not be loaded.';
    page.append(message);
  }
  function heading(title, subtitle, back) {
    page.replaceChildren(NavigationBar({ left: back, right: null, onNavigate: destination => {
      if (destination === 'list') { state.historySessionId = null; list(); }
      else navigate(destination);
    } }));
    const intro = node('<header class="intro"><p class="eyebrow">Your activity</p><h1></h1><p class="sub"></p></header>');
    intro.querySelector('h1').textContent = title;
    intro.querySelector('.sub').textContent = subtitle;
    page.append(intro);
  }
  async function list() {
    heading('Session history', 'Review your sessions and website activity.',
      { label: state.session ? 'Back to session' : 'Back to home', page: state.session ? 'session' : 'start' });
    const exportAll = node('<button class="btn btn-soft">Export all sessions (JSON)</button>');
    exportAll.addEventListener('click', async () => {
      exportAll.disabled = true;
      try { download('grove-activity.json', JSON.stringify(await api.exportActivity(), null, 2), 'application/json'); }
      catch (error) { errorMessage(error); }
      finally { exportAll.disabled = false; }
    });
    page.append(exportAll);
    try {
      const sessions = await api.listSessions();
      if (disposed) return;
      if (!sessions.length) page.append(node('<p class="empty-state">Your new sessions will appear here. Older prototype records remain in the original database files.</p>'));
      sessions.forEach(session => {
        const row = node('<button class="history-row"><span><strong></strong><small></small></span><span data-status></span></button>');
        row.querySelector('strong').textContent = session.topic;
        row.querySelector('small').textContent = `${date(session.start_time)} · ${duration(session.minutes * 60)}`;
        row.querySelector('[data-status]').textContent = session.status ?? 'Sample';
        row.addEventListener('click', () => { state.historySessionId = session.id; details(session.id); });
        page.append(row);
      });
    } catch (error) { errorMessage(error); }
  }
  async function details(id) {
    heading('Session details', 'Loading the saved record…', { label: 'Back to history', page: 'list' });
    try {
      const data = await api.getSessionDetails(id);
      if (disposed) return;
      const { session, summary } = data;
      page.querySelector('h1').textContent = session.topic;
      page.querySelector('.intro .sub').textContent = `${session.status} · ${date(session.started_at)}`;
      const grid = node('<div class="stat-grid" style="margin-top:0"></div>');
      [[summary.focusedSeconds, 'Session time'], [summary.pausedSeconds, 'Paused'],
       [summary.browserActiveSeconds, 'Browser activity'], [summary.unattributedSeconds, 'Without a tracked site']].forEach(([value, caption]) => {
        const stat = node('<div class="stat"><div class="num"></div><div class="cap"></div></div>');
        stat.querySelector('.num').textContent = duration(value);
        stat.querySelector('.cap').textContent = caption;
        grid.append(stat);
      });
      page.append(grid);
      const actions = node('<div class="chips" style="margin-top:14px"><button class="btn btn-soft" data-json>Export JSON</button><button class="btn btn-soft" data-csv>Visits CSV</button></div>');
      actions.querySelector('[data-json]').addEventListener('click', () => download(`grove-${id}.json`, JSON.stringify(data, null, 2), 'application/json'));
      actions.querySelector('[data-csv]').addEventListener('click', () => {
        const fields = ['session_id', 'id', 'domain', 'url', 'title', 'tab_id', 'window_id', 'started_at', 'ended_at', 'duration_seconds', 'start_reason', 'end_reason', 'observation_count'];
        const rows = [fields, ...session.website_visits.map(visit => fields.map(field => visit[field]))];
        download(`grove-${id}-visits.csv`, rows.map(row => row.map(csvCell).join(',')).join('\r\n'), 'text/csv;charset=utf-8');
      });
      page.append(actions);
      const sites = node('<section class="history"><div class="section-heading"><h2>Time by website</h2><span>Observed time</span></div></section>');
      for (const domain of summary.domains ?? []) {
        const row = node('<div class="listrow"><span></span><span class="session-meta"></span></div>');
        row.firstElementChild.textContent = domain.domain;
        row.lastElementChild.textContent = `${duration(domain.seconds)} · ${domain.visits} visits`;
        sites.append(row);
      }
      if (!summary.domains?.length) sites.append(node('<p class="empty-state">No website activity was recorded.</p>'));
      page.append(sites);
      const timeline = node('<section class="history"><div class="section-heading"><h2>Timeline</h2><span>Local time</span></div><ol class="timeline"></ol></section>');
      for (const event of session.events) {
        const row = node('<li><time></time><span><strong></strong><small></small></span></li>');
        row.querySelector('time').textContent = new Date(event.timestamp).toLocaleTimeString();
        row.querySelector('strong').textContent = event.type.replaceAll('_', ' ');
        const visit = session.website_visits.find(visit => visit.id === event.visit_id);
        row.querySelector('small').textContent = visit ? `${visit.domain} · ${visit.title}` : (event.state ?? event.reason ?? '');
        timeline.querySelector('ol').append(row);
      }
      page.append(timeline);
      page.append(node('<p class="empty-state">Browser time counts observed foreground websites while the session runs. It is not a measure of attention. Short gaps may be estimated until the next activity signal.</p>'));
    } catch (error) { errorMessage(error); }
  }
  if (state.historySessionId) details(state.historySessionId);
  else list();
  return page;
}
