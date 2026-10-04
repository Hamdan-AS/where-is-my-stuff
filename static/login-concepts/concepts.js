document.querySelector('.reveal').addEventListener('click', function () {
  const input = document.querySelector('#password');
  const visible = input.type === 'password';
  input.type = visible ? 'text' : 'password';
  this.textContent = visible ? 'Hide' : 'Show';
  this.setAttribute('aria-pressed', String(visible));
  this.setAttribute('aria-label', visible ? 'Hide password' : 'Show password');
});
document.querySelectorAll('[data-tab]').forEach(button => button.addEventListener('click', () => {
  const register = button.dataset.tab === 'register';
  document.querySelectorAll('[data-tab]').forEach(tab => {
    tab.classList.toggle('active', tab === button);
    tab.setAttribute('aria-pressed', String(tab === button));
  });
  document.querySelector('#account-heading').textContent = register ? 'Create an account' : 'Welcome back';
  document.querySelector('.form-intro').textContent = register ? 'Registration styling preview. The live app also asks for your name.' : 'Sign in to manage your reports and QR labels.';
  document.querySelector('.submit').textContent = register ? 'Register' : 'Log in';
  document.querySelector('#password').autocomplete = register ? 'new-password' : 'current-password';
}));
document.querySelector('form').addEventListener('submit', event => {
  event.preventDefault();
  const status = document.querySelector('.status');
  status.hidden = false;
  status.textContent = 'Design preview only. No information was submitted.';
});
