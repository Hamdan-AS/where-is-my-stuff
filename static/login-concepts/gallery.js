const widthSelect = document.querySelector('#phone-width');
function sizePreviews() {
  document.querySelectorAll('.viewport').forEach(viewport => {
    const iframe = viewport.querySelector('iframe');
    const phone = viewport.classList.contains('phone');
    const width = phone ? Number(widthSelect.value) : 1280;
    const height = phone ? 844 : 720;
    iframe.width = width;
    iframe.height = height;
    const scale = viewport.clientWidth / width;
    iframe.style.transform = `scale(${scale})`;
    viewport.style.height = `${height * scale}px`;
  });
  document.querySelectorAll('.phone-size').forEach(label => label.textContent = `${widthSelect.value} × 844`);
}
new ResizeObserver(sizePreviews).observe(document.querySelector('main'));
widthSelect.addEventListener('change', sizePreviews);
sizePreviews();
let selected;
try { selected = localStorage.getItem('wims-login-concept'); } catch (_) {}
function showChoice(choice) {
  const status = document.querySelector('#selection');
  const button = document.querySelector(`[data-choice="${choice}"]`);
  if (!button) return;
  document.querySelectorAll('[data-choice]').forEach(item => {
    const active = item === button;
    item.setAttribute('aria-pressed', String(active));
    item.textContent = active ? 'Selected direction' : 'Choose this direction';
  });
  status.hidden = false;
  status.textContent = `Selected: ${button.closest('.option').querySelector('h2').textContent}. Tell me this name when you are ready to apply it.`;
}
document.querySelectorAll('[data-choice]').forEach(button => button.addEventListener('click', () => {
  try { localStorage.setItem('wims-login-concept', button.dataset.choice); } catch (_) {}
  showChoice(button.dataset.choice);
}));
if (selected) showChoice(selected);
