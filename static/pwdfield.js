/*
 * Componente reutilizável de campo de senha com botão "olho" (mostrar/ocultar).
 * Uso: marque qualquer <input> de senha com o atributo `data-pwd` e inclua este
 * script + pwdfield.css. O componente envolve o input e injeta o botão.
 *
 * Para campos criados dinamicamente, chame window.PwdField.init(container).
 */
(function () {
  var EYE_ON = '<svg width="17" height="17" viewBox="0 0 16 16" fill="none"><path d="M1 8s2.5-4.5 7-4.5S15 8 15 8s-2.5 4.5-7 4.5S1 8 1 8z" stroke="currentColor" stroke-width="1.3"/><circle cx="8" cy="8" r="2" stroke="currentColor" stroke-width="1.3"/></svg>';
  var EYE_OFF = '<svg width="17" height="17" viewBox="0 0 16 16" fill="none"><path d="M6.6 6.6a2 2 0 0 0 2.8 2.8" stroke="currentColor" stroke-width="1.3"/><path d="M3.4 4.3C1.9 5.4 1 8 1 8s2.5 4.5 7 4.5c1.3 0 2.4-.3 3.3-.8M6.6 3.6c.45-.07.9-.1 1.4-.1 4.5 0 7 4.5 7 4.5s-.6 1.1-1.8 2.3" stroke="currentColor" stroke-width="1.3"/><path d="M2 2l12 12" stroke="currentColor" stroke-width="1.3"/></svg>';

  function enhance(input) {
    if (!input || input.dataset.pwdReady) return;
    input.dataset.pwdReady = '1';
    if (input.type !== 'password') input.type = 'password';

    var wrap = document.createElement('span');
    wrap.className = 'pwdfield';
    input.parentNode.insertBefore(wrap, input);
    wrap.appendChild(input);

    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'pwdfield-eye';
    btn.tabIndex = -1;
    btn.setAttribute('aria-label', 'Mostrar/ocultar senha');
    btn.innerHTML = EYE_ON;
    btn.addEventListener('click', function () {
      var hidden = input.type === 'password';
      input.type = hidden ? 'text' : 'password';
      btn.innerHTML = hidden ? EYE_OFF : EYE_ON;
    });
    wrap.appendChild(btn);
  }

  function init(root) {
    (root || document).querySelectorAll('input[data-pwd]').forEach(enhance);
  }

  window.PwdField = { init: init, enhance: enhance };
  if (document.readyState !== 'loading') init();
  else document.addEventListener('DOMContentLoaded', function () { init(); });
})();
