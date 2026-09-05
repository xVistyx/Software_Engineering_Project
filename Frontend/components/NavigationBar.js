/* ============================================================
   components/NavigationBar.js — the topbar every page mounts.
   Props:
     left    : { label, page } | null   (Back / Home chip)
     right   : { label, page } | null   (Settings gear, default)
     title   : string | null            (center label, e.g. topic)
     onNavigate(page)                    (router from main.js)
   ============================================================ */

const node = (html) => {
  const t = document.createElement('template');
  t.innerHTML = html.trim();
  return t.content.firstElementChild;
};

export function NavigationBar({ left = null, right = { label: '⚙', page: 'settings' }, title = null, onNavigate }) {
  const el = node(`<div class="topbar"></div>`);

  if (left) {
    const c = node(`<div class="chip">${left.label}</div>`);
    c.addEventListener('click', () => onNavigate(left.page));
    el.append(c);
  } else if (title) {
    el.append(node(`<div class="chip">${title}</div>`));
  }

  el.append(node(`<div class="spacer"></div>`));

  if (right) {
    const g = node(`<div class="chip">${right.label}</div>`);
    g.addEventListener('click', () => onNavigate(right.page));
    el.append(g);
  }

  return el;
}
