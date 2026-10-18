/* Registration presentation only: the existing POST and server CSRF are authoritative. */
(function () {
  'use strict';
  var form = document.getElementById('reg-form');
  var password = document.getElementById('password');
  var confirm = document.getElementById('confirm');
  var hint = document.getElementById('confirm-hint');
  function checkConfirm() {
    var mismatch = confirm.value && confirm.value !== password.value;
    confirm.setCustomValidity(mismatch ? '两次输入的密码不一致。' : '');
    confirm.setAttribute('aria-invalid', mismatch ? 'true' : 'false');
    hint.textContent = !confirm.value ? '' : mismatch ? '两次密码不一致，请检查。' : '两次密码一致。';
    hint.className = 'fl-confirm-hint' + (mismatch ? ' is-error' : '');
  }
  password.addEventListener('input', function () {
    var value = password.value;
    var level = Number(value.length >= 8) + Number(value.length >= 12) +
      Number(/[A-Za-z]/.test(value) && /[0-9]/.test(value)) + Number(/[^A-Za-z0-9]/.test(value));
    document.getElementById('pw-strength').hidden = !value.length;
    document.getElementById('pw-strength-meter').value = level;
    document.getElementById('pw-strength-text').textContent = '密码强度提示：' +
      (['较弱', '一般', '较强', '强'][Math.max(0, level - 1)]) + '；请勿重复使用其他网站的密码。';
    checkConfirm();
  });
  confirm.addEventListener('input', checkConfirm);
  document.querySelectorAll('[data-password-target]').forEach(function (button) {
    button.addEventListener('click', function () {
      var input = document.getElementById(button.dataset.passwordTarget);
      var show = input.type === 'password';
      input.type = show ? 'text' : 'password';
      button.textContent = show ? '隐藏' : '显示';
      button.setAttribute('aria-pressed', String(show));
      button.setAttribute('aria-label', (show ? '隐藏' : '显示') + (input === confirm ? '确认密码' : '密码'));
    });
  });
  form.addEventListener('submit', function (event) {
    checkConfirm();
    if (!form.checkValidity()) {
      event.preventDefault();
      form.reportValidity();
    }
  });
})();
