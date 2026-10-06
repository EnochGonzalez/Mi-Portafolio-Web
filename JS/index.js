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

/* ===== Propio de Inicio: buscador en vivo ===== */
function initSearch() {
  var input = document.getElementById('post-search');
  var rows = document.querySelectorAll('.post-row');
  var emptyState = document.getElementById('empty-state');
  if (!input || !rows.length) return;

  input.addEventListener('input', function () {
    var query = input.value.trim().toLowerCase();
    var visible = 0;

    rows.forEach(function (row) {
      var haystack = row.getAttribute('data-search') || '';
      var show = !query || haystack.indexOf(query) !== -1;
      row.hidden = !show;
      if (show) visible += 1;
    });

    if (emptyState) emptyState.hidden = visible !== 0;
  });
}


/* ===== Certificados: abrir el certificado en pantalla (modal) ===== */
function initCertModal() {
  var modal = document.getElementById('cert-modal');
  var links = document.querySelectorAll('.cert-link');
  if (!modal || !links.length || typeof modal.showModal !== 'function') return;

  var title = document.getElementById('cert-modal-title');
  var img = document.getElementById('cert-modal-img');
  var pdf = document.getElementById('cert-modal-pdf');

  function openCert(link) {
    var name = link.getAttribute('data-cert-title');
    var org = link.getAttribute('data-cert-org');
    title.textContent = name + ' · ' + org;
    img.classList.remove('is-zoomed');
    img.src = link.getAttribute('data-cert-img');
    img.alt = 'Certificado de ' + name + ' (' + org + ')';
    pdf.href = link.getAttribute('href');
    document.body.style.overflow = 'hidden';
    modal.showModal();
  }

  links.forEach(function (link) {
    link.addEventListener('click', function (e) {
      // Con Ctrl/Cmd/Shift se deja abrir el PDF normalmente en otra pestaña
      if (e.ctrlKey || e.metaKey || e.shiftKey || e.altKey || e.button !== 0) return;
      e.preventDefault();
      openCert(link);
    });
  });

  modal.querySelector('.cert-modal__close').addEventListener('click', function () { modal.close(); });
  modal.addEventListener('click', function (e) { if (e.target === modal) modal.close(); });
  img.addEventListener('click', function () { img.classList.toggle('is-zoomed'); });
  modal.addEventListener('close', function () { document.body.style.overflow = ''; });
}

document.addEventListener('DOMContentLoaded', function () {
  initMobileNav();
  initBackToTop();
  initSearch();
  initCertModal();
});
