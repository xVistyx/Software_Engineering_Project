export function NavigationBar({ left = null, right = { label: 'Settings', page: 'settings' }, title = null, onNavigate }) {
  const el = document.createElement('nav');
  el.className = 'topbar';
  el.setAttribute('aria-label', 'Main navigation');
  const link = ({ label, page }) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'chip';
    button.textContent = label;
    button.addEventListener('click', () => onNavigate(page));
    return button;
  };
  if (left) el.append(link(left));
  else if (title) {
    const heading = document.createElement('span');
    heading.className = 'nav-title';
    heading.textContent = title;
    el.append(heading);
  } else {
    const brand = document.createElement('div');
    brand.className = 'brand';
    brand.innerHTML = '<span class="brand-mark" aria-hidden="true">g</span><span>Grove</span>';
    el.append(brand);
  }
  const spacer = document.createElement('span');
  spacer.className = 'spacer';
  el.append(spacer);
  if (!left && !title) el.append(link({ label: 'History', page: 'history' }));
  if (right) el.append(link(right));
  return el;
}
