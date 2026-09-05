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
  page.append(NavigationBar({ left: { label: '‹ Settings', page: 'settings' }, right: null, onNavigate: navigate }));
  page.append(node(`<h2 style="margin:8px 0 6px">Blocked sites</h2>`));
  page.append(node(`<p class="sub" style="margin-bottom:16px">These are blocked while a session is running.</p>`));

  const mount = node(`<div></div>`);
  page.append(mount);

  api.getBlocklist().then(({ sites }) => {
    mount.append(WebsiteList({
      sites,
      onChange: async (next) => {
        await api.putBlocklist(next);       // persist
        await bg('BLOCKLIST_UPDATED', next); // refresh declarativeNetRequest rules
      },
    }));
  });

  return page;
}
