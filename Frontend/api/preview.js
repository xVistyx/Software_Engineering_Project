// Local, opt-in UI preview. Nothing is sent to the Python API or browser worker.
// State lasts for this browser tab; reloading starts a fresh preview.
export function createPreviewApi() {
  const settings = { defaultMinutes: 45, breakReminders: true, sounds: false, strictMode: false };
  let sites = ['youtube.com', 'reddit.com', 'instagram.com'];
  const sessions = [
    { id: 'sample-1', topic: 'Calculus revision', minutes: 45, score: 94 },
    { id: 'sample-2', topic: 'Project research', minutes: 60, score: 88 },
  ];
  let active = null;
  let lastTick = 0;
  const summaries = new Map();
  function finish() {
    if (!active) return;
    const focusedSeconds = active.time - active.time_remaining;
    summaries.set(active.id, { focusedSeconds, pausedSeconds: 0, browserActiveSeconds: 0,
      unattributedSeconds: focusedSeconds, visitCount: 0, pauseCount: 0, domains: [], score: null });
    sessions.unshift({ id: active.id, topic: active.topic, minutes: focusedSeconds / 60,
      start_time: active.start_time, status: 'completed' });
    active = null;
  }
  function sync() {
    if (active?.is_running) {
      const now = Date.now();
      const elapsed = Math.floor((now - lastTick) / 1000);
      active.time_remaining = Math.max(0, active.time_remaining - elapsed);
      lastTick += elapsed * 1000;
      if (active.time_remaining === 0) finish();
    }
  }
  return {
    getSettings: async () => ({ ...settings }),
    updateSettings: async patch => Object.assign(settings, patch),
    getBlocklist: async () => ({ sites: [...sites] }),
    putBlocklist: async next => { sites = [...next]; return { sites }; },
    getStats: async () => ({ total: 24 + summaries.size, thisWeek: 5 + summaries.size, focusedHours: 18, peakDriftHour: '15:00' }),
    listSessions: async () => sessions.map(session => ({ ...session })),
    createSession: async ({ topic, minutes }) => {
      active = { id: `preview-${Date.now()}`, topic, minutes, time: minutes * 60, time_remaining: minutes * 60, is_running: true, status: 'running', start_time: new Date().toISOString() };
      lastTick = Date.now();
      return { ...active };
    },
    getActiveSession: async () => { sync(); return active ? { ...active } : null; },
    updateSession: async (id, patch) => {
      sync();
      if (!active || active.id !== id) throw new Error('Session not found');
      Object.assign(active, patch, { is_running: patch.status === 'running' });
      lastTick = Date.now();
      return { ...active };
    },
    endSession: async id => {
      sync();
      if (active?.id === id) {
        finish();
      }
      return {};
    },
    getSummary: async id => ({ ...summaries.get(id) }),
    getSessionDetails: async id => {
      const sample = sessions.find(session => session.id === id);
      if (!sample) throw new Error('Sample session not found');
      return { session: { id, topic: sample.topic, status: sample.status ?? 'sample', started_at: sample.start_time,
        events: [], website_visits: [] }, summary: summaries.get(id) ?? { focusedSeconds: sample.minutes * 60,
        pausedSeconds: 0, browserActiveSeconds: 0, unattributedSeconds: sample.minutes * 60, domains: [] } };
    },
    exportActivity: async () => ({ sample_data: true, sessions }),
  };
}
