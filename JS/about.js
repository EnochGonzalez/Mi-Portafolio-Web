/* ===== Base compartida: nav móvil, volver arriba, toast ===== */

function initMobileNav() {
  var toggle = document.querySelector('.nav-toggle');
  var links = document.querySelector('.nav-links');
  if (!toggle || !links) return;
  toggle.addEventListener('click', function () {
    var isOpen = links.classList.toggle('open');
    toggle.setAttribute('aria-expanded', String(isOpen));
  });
  links.querySelectorAll('a').forEach(function (a) {
    a.addEventListener('click', function () {
      links.classList.remove('open');
      toggle.setAttribute('aria-expanded', 'false');
    });
  });
}

function initBackToTop() {
  var btn = document.querySelector('.back-to-top');
  if (!btn) return;
  document.addEventListener('scroll', function () {
    btn.classList.toggle('visible', window.scrollY > 600);
  }, { passive: true });
  btn.addEventListener('click', function () {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
}

var toastTimer;
function showToast(message) {
  var toast = document.querySelector('.toast');
  if (!toast) return;
  toast.textContent = message;
  toast.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(function () { toast.classList.remove('show'); }, 1800);
}

/* ===== Propio de Acerca: por ahora solo usa el comportamiento base ===== */
document.addEventListener('DOMContentLoaded', function () {
  initMobileNav();
  initBackToTop();
});
