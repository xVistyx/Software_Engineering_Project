/* ============================================================
   pages/BlockListPage.js — manage the blocklist.
   (was the "Blocklist ›" row inside prototype screen 5)
   ctx = { navigate, state, api, bg }
   ============================================================ */

import { NavigationBar } from '../components/NavigationBar.js';
import { WebsiteList }   from '../components/WebsiteList.js';

const node = (html) => {
  const t = document.createElement('template');
  t.innerHTML = html.trim();
  return t.content.firstElementChild;
};

export function BlockListPage(ctx) {
  const { navigate, api, bg } = ctx;

  const page = node(`<section class="screen active"></section>`);
  page.append(NavigationBar({ left: { label: 'Back to settings', page: 'settings' }, right: null, onNavigate: navigate }));
  page.append(node(`<header class="intro"><p class="eyebrow">Fewer distractions</p><h1>Blocked sites</h1><p class="sub">Manage the sites on your session blocklist.</p></header>`));

  const mount = node(`<div></div>`);
  page.append(mount);

  api.getBlocklist().then(({ sites }) => {
    if (!Array.isArray(sites)) throw new Error('Blocklist unavailable');
    mount.append(WebsiteList({
      sites,
      onChange: async (next) => {
        await api.putBlocklist(next);       // persist
        await bg('BLOCKLIST_UPDATED', next); // refresh declarativeNetRequest rules
      },
    }));
  }).catch(() => {
    mount.append(node('<p class="empty-state">Your blocklist could not be loaded. Please try again later.</p>'));
  });

  return page;
}
