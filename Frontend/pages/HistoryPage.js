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
const date = value => value ? new Date(value).toLocaleString() : 'Not recorded';

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

export function HistoryPage({ navigate, state, api, onBackToList, dashboard = false }) {
  const page = node('<section class="screen active"></section>');
  let disposed = false;
  let generation = 0;
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
      if (destination === 'list') {
        if (onBackToList) { onBackToList(); return; }
        state.historySessionId = null; list();
      }
      else navigate(destination);
    } }));
    const intro = node('<header class="intro"><p class="eyebrow">Your activity</p><h1></h1><p class="sub"></p></header>');
    intro.querySelector('h1').textContent = title;
    intro.querySelector('.sub').textContent = subtitle;
    page.append(intro);
    if (!dashboard) {
      const past = node('<a class="btn btn-soft past-sessions-link" target="_blank" rel="noopener noreferrer" aria-label="Past Sessions (opens in a new tab)">Past Sessions <svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M14 3h7v7M21 3l-11 11M10 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-5"/></svg></a>');
      past.href = new URL('../past-sessions.html', import.meta.url).href;
      page.append(past);
    }
  }
  async function list() {
    const request = ++generation;
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
    const loading = node('<p class="empty-state" role="status">Loading sessions…</p>');
    page.append(loading);
    try {
      const sessions = await api.listSessions();
      if (disposed || request !== generation) return;
      loading.remove();
      if (!sessions.length) page.append(node('<p class="empty-state">Your sessions will appear here after you start one.</p>'));
      sessions.forEach(session => {
        const row = node('<button class="history-row"><span><strong></strong><small></small></span><span data-status></span></button>');
        row.querySelector('strong').textContent = session.topic;
        row.querySelector('small').textContent = `${date(session.start_time)} · ${session.duration_known === false ? 'Duration unknown' : duration(session.minutes * 60)}`;
        row.querySelector('[data-status]').textContent = session.storage_status === 'pending' ? 'Save pending' : session.status ?? 'Sample';
        row.addEventListener('click', () => { state.historySessionId = session.id; details(session.id); });
        page.append(row);
      });
    } catch (error) { if (request === generation) { loading.remove(); errorMessage(error); } }
  }
  async function details(id) {
    const request = ++generation;
    heading('Session details', 'Loading the saved record…', { label: 'Back to history', page: 'list' });
    try {
      const data = await api.getSessionDetails(id);
      if (disposed || request !== generation) return;
      const { session, summary } = data;
      const summaryOnly = session.detail_level === 'summary';
      page.querySelector('h1').textContent = session.topic;
      page.querySelector('.intro .sub').textContent = `${session.status} · ${date(session.started_at)}`;
      const description = node('<section class="history session-summary"><h2>Session summary</h2><p class="sub" data-summary></p><p class="sub" data-ended></p></section>');
      description.querySelector('[data-summary]').textContent = summaryOnly
        ? 'Session statistics recorded at completion. Detailed website visits and events are not retained for this session.'
        : summary.summaryText || 'Summary not available for this record.';
      description.querySelector('[data-ended]').textContent = `Ended: ${date(session.ended_at)}`;
      page.append(description);
      if (data.storage_status === 'pending') {
        const pending = node('<div class="stack save-pending" role="status"><p>Saving is pending. Your session data is retained and will be retried automatically.</p><button class="btn btn-soft">Retry save</button></div>');
        pending.querySelector('button').addEventListener('click', async () => {
          pending.querySelector('button').disabled = true;
          try { await api.retrySessionSaves(); await details(id); }
          catch (error) { errorMessage(error); pending.querySelector('button').disabled = false; }
        });
        page.append(pending);
      }
      const grid = node('<div class="stat-grid" style="margin-top:0"></div>');
      const metrics = summaryOnly
        ? [[summary.focusedSeconds, 'Session duration'], [summary.plannedSeconds, 'Planned duration'],
           [summary.productiveSeconds, 'Reported productive time'], [summary.browserActiveSeconds, 'Time on tabs']]
        : [[summary.focusedSeconds, 'Session time'], [summary.pausedSeconds, 'Paused'],
           [summary.browserActiveSeconds, 'Browser activity'], [summary.unattributedSeconds, 'Without a tracked site']];
      metrics.forEach(([value, caption]) => {
        const stat = node('<div class="stat"><div class="num"></div><div class="cap"></div></div>');
        stat.querySelector('.num').textContent = session.duration_known === false || value == null ? 'Unknown' : duration(value);
        stat.querySelector('.cap').textContent = caption;
        grid.append(stat);
      });
      page.append(grid);
      if (summaryOnly) {
        const facts = node('<section class="history"><h2>Session results</h2></section>');
        for (const [label, value] of [['Score', summary.score == null ? null : `${summary.score}/100`],
          ['Number of tabs', summary.tabCount], ['Most used tab', summary.mostUsedTab], ['Most often blocked', summary.mostOftenBlocked]]) {
          const row = node('<div class="listrow"><span></span><strong></strong></div>');
          row.firstElementChild.textContent = label;
          row.lastElementChild.textContent = value ?? 'Not available';
          facts.append(row);
        }
        page.append(facts);
      }
      const actions = node('<div class="chips" style="margin-top:14px"><button class="btn btn-soft" data-json>Export JSON</button><button class="btn btn-soft" data-csv>Visits CSV</button></div>');
      actions.querySelector('[data-json]').addEventListener('click', () => download(`grove-${id}.json`, JSON.stringify(data, null, 2), 'application/json'));
      if (summaryOnly) actions.querySelector('[data-csv]').textContent = 'Summary CSV';
      actions.querySelector('[data-csv]').addEventListener('click', () => {
        if (summaryOnly) {
          const fields = Object.keys(session.source_summary);
          const rows = [fields, fields.map(field => session.source_summary[field])];
          download(`grove-${id}-summary.csv`, rows.map(row => row.map(csvCell).join(',')).join('\r\n'), 'text/csv;charset=utf-8');
          return;
        }
        const fields = ['session_id', 'id', 'domain', 'url', 'title', 'tab_id', 'window_id', 'started_at', 'ended_at', 'duration_seconds', 'start_reason', 'end_reason', 'observation_count'];
        const rows = [fields, ...session.website_visits.map(visit => fields.map(field => visit[field]))];
        download(`grove-${id}-visits.csv`, rows.map(row => row.map(csvCell).join(',')).join('\r\n'), 'text/csv;charset=utf-8');
      });
      page.append(actions);
      if (!summaryOnly) {
      const sites = node('<section class="history"><div class="section-heading"><h2>Time by website</h2><span>Observed time</span></div></section>');
      for (const domain of summary.domains ?? []) {
        const row = node('<div class="listrow"><span></span><span class="session-meta"></span></div>');
        row.firstElementChild.textContent = domain.domain;
        row.lastElementChild.textContent = `${duration(domain.seconds)} · ${domain.visits} visits`;
        sites.append(row);
      }
      if (!summary.domains?.length) sites.append(node('<p class="empty-state">No website activity was recorded.</p>'));
      page.append(sites);
      const visits = node('<section class="history"><div class="section-heading"><h2>Website visits</h2><span>Recorded decisions</span></div><div class="visits-list"></div></section>');
      for (const visit of session.website_visits) {
        const row = node('<article class="visit-detail"><strong></strong><p class="sub" data-url></p><p class="sub" data-info></p></article>');
        row.querySelector('strong').textContent = visit.title || visit.domain;
        row.querySelector('[data-url]').textContent = visit.url;
        const decision = visit.decision === 'blocked' ? 'Blocked' : visit.decision === 'allowed' ? 'Allowed' : 'Decision not recorded';
        row.querySelector('[data-info]').textContent = `${duration(visit.duration_seconds)} · ${decision} · ${date(visit.started_at)}`;
        visits.querySelector('.visits-list').append(row);
      }
      if (!session.website_visits.length) visits.append(node('<p class="empty-state">No website visits were recorded.</p>'));
      page.append(visits);
      }
      const analysis = node('<section class="history ai-analysis"><div class="section-heading"><h2>AI analysis</h2><span data-state></span></div><p class="sub"></p></section>');
      analysis.querySelector('[data-state]').textContent = data.analysis ? 'Available' : 'Pending';
      analysis.querySelector('p').textContent = data.analysis?.summary || 'No AI analysis is available yet. Your session details are ready to review.';
      if (data.analysis) {
        const raw = node('<details><summary>Analysis details</summary><pre></pre></details>');
        raw.querySelector('pre').textContent = JSON.stringify(data.analysis, null, 2);
        analysis.append(raw);
      }
      page.append(analysis);
      if (!summaryOnly) {
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
      }
    } catch (error) { if (request === generation) errorMessage(error); }
  }
  if (state.historySessionId) details(state.historySessionId);
  else list();
  return page;
}
