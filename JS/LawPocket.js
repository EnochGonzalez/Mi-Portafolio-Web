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

/* ===== Propio de este artículo: progreso de lectura, copiar enlace ===== */
function initProgressBar() {
  var bar = document.querySelector('.progress-bar');
  var article = document.querySelector('article.post-body');
  if (!bar || !article) return;

  function update() {
    var rect = article.getBoundingClientRect();
    var articleTop = rect.top + window.scrollY;
    var articleHeight = article.offsetHeight;
    var viewport = window.innerHeight;
    var scrolled = window.scrollY - articleTop + viewport * 0.3;
    var pct = Math.min(100, Math.max(0, (scrolled / articleHeight) * 100));
    bar.style.width = pct + '%';
  }
  document.addEventListener('scroll', update, { passive: true });
  window.addEventListener('resize', update);
  update();
}

function initShareLink() {
  var btn = document.getElementById('copy-link');
  if (!btn) return;
  btn.addEventListener('click', function () {
    var url = btn.getAttribute('data-copy-url') || window.location.href;
    navigator.clipboard.writeText(url).then(function () {
      showToast('Enlace copiado');
    }).catch(function () {
      showToast('No se pudo copiar el enlace');
    });
  });
}

document.addEventListener('DOMContentLoaded', function () {
  initMobileNav();
  initBackToTop();
  initProgressBar();
  initShareLink();
});
