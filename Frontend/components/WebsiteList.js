/* ============================================================
   components/WebsiteList.js — editable list of blocked domains.
   Props:
     sites      : string[]
     onChange(sites)   fired after every add/remove (page persists)
   ============================================================ */

const node = (html) => {
  const t = document.createElement('template');
  t.innerHTML = html.trim();
  return t.content.firstElementChild;
};

export function WebsiteList({ sites = [], onChange }) {
  let list = [...sites];

  const el = node(`
    <div>
      <div class="chips" style="margin-bottom:12px">
        <input class="input" data-add placeholder="Add a site to block (e.g. youtube.com)" />
        <button class="btn btn-primary" data-addbtn style="width:auto;padding:14px 18px">Add</button>
      </div>
      <div data-rows></div>
    </div>`);

  const rows  = el.querySelector('[data-rows]');
  const input = el.querySelector('[data-add]');

  const clean = (v) => v.trim().toLowerCase().replace(/^https?:\/\//, '').replace(/\/.*$/, '');

  function commit() { onChange?.([...list]); }

  function render() {
    rows.innerHTML = '';
    if (!list.length) {
      rows.append(node(`<p class="sub" style="padding:8px 4px">No sites yet — add one above.</p>`));
      return;
    }
    list.forEach((site, i) => {
      const row = node(`<div class="listrow">${site}<span data-x="${i}" style="cursor:pointer;color:var(--accent)">Remove</span></div>`);
      row.querySelector('[data-x]').addEventListener('click', () => {
        list.splice(i, 1); render(); commit();
      });
      rows.append(row);
    });
  }

  function add() {
    const v = clean(input.value);
    if (v && !list.includes(v)) { list.push(v); render(); commit(); }
    input.value = '';
    input.focus();
  }

  el.querySelector('[data-addbtn]').addEventListener('click', add);
  input.addEventListener('keydown', (e) => { if (e.key === 'Enter') add(); });

  render();
  return el;
}
