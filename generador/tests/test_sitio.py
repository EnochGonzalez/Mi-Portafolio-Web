"""Las páginas generadas: contenido, rutas relativas, datos estructurados y casos límite."""
import json
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

import sitio
from conftest import PLANTILLAS


def datos_ld(html):
    return [json.loads(m) for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)]


def indice(html, texto):
    assert texto in html, f"No aparece: {texto}"
    return html.index(texto)


# ================================================================== qué páginas salen
def test_se_genera_una_pagina_por_proyecto_mas_inicio_y_acerca(paginas):
    assert set(paginas) == {"index.html", "about.html", "proyectos/lawpocket.html", "proyectos/math-english-quest.html", "proyectos/series-de-taylor.html"}


def test_todas_las_paginas_avisan_que_estan_generadas(paginas):
    for ruta, html in paginas.items():
        assert "No lo edites a mano" in html and html.startswith("<!DOCTYPE html>"), ruta


# ================================================================== inicio
def test_inicio_lista_los_proyectos_en_orden_con_sus_enlaces(paginas):
    html = paginas["index.html"]
    assert indice(html, 'href="proyectos/lawpocket.html"') < indice(html, 'href="proyectos/math-english-quest.html"') < indice(html, 'href="proyectos/series-de-taylor.html"')
    assert "3 artículos publicados" in html
    assert '<span class="day">15</span>jul 2026' in html and '<span class="day">10</span>may 2026' in html
    assert '<span class="tag">LawPocket</span><span class="tag">Proyecto Integrador</span>' in html
    assert html.count("1 min de lectura") == 3
    assert html.count('class="post-row__link"') == 3 and 'href="https://law-pocket-integrador.vercel.app"' in html


def test_inicio_busqueda_incluye_titulo_extracto_y_etiquetas_en_minusculas(paginas):
    assert 'data-search="series de taylor visualización de cómo un polinomio de taylor' in paginas["index.html"]
    assert "cálculo proyecto de clase" in paginas["index.html"]


def test_inicio_textos_derivados_del_perfil_y_los_proyectos(paginas):
    html = paginas["index.html"]
    assert "Soy estudiante de Ingeniería en Desarrollo de Software. Aquí resumo LawPocket, Math &amp; English Quest y otros proyectos de clase." in html
    assert 'content="Bitácora de desarrollo de Santos Enoch González Pérez: LawPocket, Math &amp; English Quest y otros proyectos."' in html
    assert "<title>SEGOPE.dev — bitácora de Santos Enoch González Pérez</title>" in html
    assert "<p>Estudiante de Ingeniería en Desarrollo de Software, enfocado en aplicaciones web y móviles.</p>" in html


def test_inicio_barra_lateral_muestra_el_stack_y_los_tres_certificados_mas_recientes(paginas):
    html = paginas["index.html"]
    lateral = html[html.index('class="stack-list"'):]
    assert re.findall(r"<li>([^<]+)</li>", lateral[:lateral.index("</ul>")]) == ["Java", "C++", "JavaScript", "CSS", "HTML", "Kotlin"]
    minis = html[html.index('class="cert-mini-list"'):]
    assert re.findall(r'data-cert-title="([^"]+)"', minis) == ["Operating Systems Support", "Introduction to Internet of Things", "AWS Academy Graduate — Cloud Foundations"]
    assert 'href="PDF/InternetOfThings.pdf"' in minis and 'data-cert-img="Imagenes/Certificados/InternetOfThings.jpg"' in minis
    assert "Cisco Networking Academy · 01/12/2025" in minis


def test_inicio_usa_la_direccion_real_en_canonica_y_open_graph(paginas):
    html = paginas["index.html"]
    assert '<link rel="canonical" href="https://segope.vercel.app/index.html">' in html
    assert 'property="og:image" content="https://segope.vercel.app/Imagenes/favicon.svg"' in html
    assert "santosgonzalez.dev" not in "".join(paginas.values())              # el dominio de ejemplo ya no aparece en ningún lado


def test_el_menu_marca_la_pagina_actual(paginas):
    assert 'index.html" aria-current="page">Inicio' in paginas["index.html"]
    assert 'about.html" aria-current="page">Acerca' in paginas["about.html"]
    assert 'index.html#articulos" aria-current="page">Artículos' in paginas["proyectos/lawpocket.html"]


# ================================================================== acerca
def test_acerca_muestra_habilidades_certificados_y_contacto(paginas):
    html = paginas["about.html"]
    assert re.findall(r'<div class="skill-card"><img src="([^"]+)" alt="Logo de ([^"]+)"', html) == [
        ("Imagenes/Java.png", "Java"), ("Imagenes/C++.jpg", "C++"), ("Imagenes/JavaScript.jpg", "JavaScript"),
        ("Imagenes/Css.jpg", "CSS"), ("Imagenes/Html.jpg", "HTML"), ("Imagenes/Kotlin.png", "Kotlin")]
    assert re.findall(r'<span class="t-date">([^<]+)</span>', html) == ["16/03/2026", "01/12/2025", "26/10/2025", "26/10/2025", "25/10/2025"]
    assert html.count('class="cert-link"') == 5 and 'href="PDF/CursoCpp.pdf"' in html
    assert 'href="mailto:253390@it2id.upchiapas.edu.mx">253390@it2id.upchiapas.edu.mx</a>' in html
    assert 'href="tel:+529601177755">960-117-7755</a>' in html
    assert 'href="https://github.com/EnochGonzalez" target="_blank" rel="noopener noreferrer">github.com/EnochGonzalez</a>' in html


def test_acerca_incluye_el_modal_de_certificados_y_los_datos_estructurados(paginas):
    html = paginas["about.html"]
    assert 'id="cert-modal"' in html and 'src="JS/about.js"' in html
    persona = datos_ld(html)[0]
    assert persona["@type"] == "Person" and persona["url"] == "https://segope.vercel.app/about.html"
    assert persona["knowsAbout"] == ["Java", "C++", "JavaScript", "CSS", "HTML", "Kotlin"]
    assert 'content="Santos Enoch González Pérez, estudiante de Ingeniería en Desarrollo de Software."' in html


# ================================================================== proyecto
def test_proyecto_usa_rutas_con_prefijo_porque_vive_en_proyectos(paginas):
    html = paginas["proyectos/lawpocket.html"]
    for esperado in ('href="../CSS/proyecto.css"', 'src="../JS/proyecto.js"', 'href="../Imagenes/favicon.svg"',
                     'src="../Imagenes/Santos.jpeg"', 'href="../index.html"', 'href="../about.html"'):
        assert esperado in html, esperado
    assert 'class="progress-bar"' in html and 'id="cert-modal"' not in html


def test_proyecto_muestra_su_contenido(paginas):
    html = paginas["proyectos/lawpocket.html"]
    assert "<h1>LawPocket: gestión legal en la nube</h1>" in html
    assert '<p class="tag-line">LawPocket · Proyecto Integrador</p>' in html
    assert "<li><strong>Lenguajes:</strong> Java, SQL</li>" in html
    assert "<li><strong>Tecnologías:</strong> Figma Site, AWS (EC2), MariaDB, Postman</li>" in html
    assert '<time datetime="2026-07-15">15 de julio de 2026</time>' in html and "1 min de lectura" in html
    assert 'class="project-link" href="https://law-pocket-integrador.vercel.app"' in html and "Ver código" not in html
    assert '<button id="copy-link" data-copy-url="https://law-pocket-integrador.vercel.app">Copiar enlace del proyecto</button>' in html
    assert '<div class="post-tags"><span class="tag">LawPocket</span><span class="tag">Proyecto Integrador</span></div>' in html


def test_navegacion_entre_proyectos(paginas):
    primero, medio, ultimo = (paginas[f"proyectos/{s}.html"] for s in ("lawpocket", "math-english-quest", "series-de-taylor"))
    assert "<div></div>" in primero and 'class="prev"' not in primero and '<a href="math-english-quest.html">Math &amp; English Quest</a>' in primero
    assert '<a href="lawpocket.html">LawPocket: gestión legal en la nube</a>' in medio and '<a href="series-de-taylor.html">Series de Taylor</a>' in medio
    assert 'class="next"' not in ultimo and '<a href="math-english-quest.html">' in ultimo


def test_proyecto_datos_estructurados(paginas):
    articulo, migas = datos_ld(paginas["proyectos/lawpocket.html"])
    assert articulo["@type"] == "BlogPosting" and articulo["wordCount"] == 39 and articulo["keywords"] == "LawPocket, Proyecto Integrador"
    assert articulo["mainEntityOfPage"]["@id"] == "https://segope.vercel.app/proyectos/lawpocket.html"
    assert [m["name"] for m in migas["itemListElement"]] == ["Inicio", "Artículos", "LawPocket: gestión legal en la nube"]


def test_sin_demo_se_copia_el_enlace_del_articulo_y_con_repositorio_aparece_ver_codigo(contenido, ajustes):
    contenido["proyectos"][0]["demo_url"] = None
    contenido["proyectos"][0]["repo_url"] = "https://github.com/usuario/lawpocket"
    paginas, _ = sitio.renderizar(contenido, ajustes, PLANTILLAS)
    html = paginas["proyectos/lawpocket.html"]
    assert 'data-copy-url="https://segope.vercel.app/proyectos/lawpocket.html">Copiar enlace del artículo</button>' in html
    assert 'class="project-link" href="https://github.com/usuario/lawpocket"' in html and "Ver proyecto" not in html
    assert 'class="post-row__link"' not in paginas["index.html"].split("math-english-quest")[0]       # la tarjeta de LawPocket ya no tiene botón


def test_tiempo_de_lectura_crece_con_la_descripcion(contenido, ajustes):
    contenido["proyectos"][0]["description"] = "palabra " * 450
    paginas, _ = sitio.renderizar(contenido, ajustes, PLANTILLAS)
    assert "2 min de lectura" in paginas["proyectos/lawpocket.html"] and "2 min de lectura" in paginas["index.html"]


# ================================================================== casos límite
class _Etiquetas(HTMLParser):
    """Lo que vería un navegador: qué etiquetas se abren de verdad en la página."""

    def __init__(self):
        super().__init__()
        self.abiertas = []

    def handle_starttag(self, tag, attrs):
        self.abiertas.append(tag)


def test_el_texto_del_contenido_se_escapa_y_no_puede_romper_la_pagina(contenido, ajustes):
    contenido["proyectos"][0]["title"] = 'Hola <b>mundo</b> & "comillas" </script><script>alert(1)</script>'
    paginas, _ = sitio.renderizar(contenido, ajustes, PLANTILLAS)
    for ruta, scripts_esperados in (("index.html", 2), ("proyectos/lawpocket.html", 3)):       # datos estructurados + el JS de la página
        html = paginas[ruta]
        analizador = _Etiquetas()
        analizador.feed(html)
        assert "b" not in analizador.abiertas                                              # el <b> del título es texto, no una etiqueta
        assert analizador.abiertas.count("script") == scripts_esperados                    # nadie logró abrir un <script> extra
        assert "&lt;b&gt;mundo&lt;/b&gt;" in html
        assert all(isinstance(d, dict) for d in datos_ld(html))                            # el JSON-LD sigue siendo JSON válido
        assert "</script><script>alert(1)" not in html                                     # y </script> no pudo cerrar el bloque a destiempo


def test_un_solo_proyecto_usa_singular_y_sin_vecinos(contenido, ajustes):
    contenido["proyectos"] = contenido["proyectos"][:1]
    paginas, _ = sitio.renderizar(contenido, ajustes, PLANTILLAS)
    assert "1 artículo publicado" in paginas["index.html"] and "Aquí resumo LawPocket y otros proyectos de clase." in paginas["index.html"]
    assert 'class="next"' not in paginas["proyectos/lawpocket.html"] and set(paginas) == {"index.html", "about.html", "proyectos/lawpocket.html"}


def test_sin_proyectos_el_blog_se_genera_igual(contenido, ajustes):
    contenido["proyectos"] = []
    paginas, _ = sitio.renderizar(contenido, ajustes, PLANTILLAS)
    assert set(paginas) == {"index.html", "about.html"}
    assert "Todavía no hay proyectos publicados." in paginas["index.html"] and "0 artículos publicados" in paginas["index.html"]
    assert "Aquí resumo mis proyectos y otros proyectos de clase." in paginas["index.html"]


def test_perfil_sin_foto_telefono_ni_github(contenido, ajustes):
    contenido["perfil"].update(photo_url=None, phone=None, github_url=None)
    paginas, _ = sitio.renderizar(contenido, ajustes, PLANTILLAS)
    assert "<img" not in paginas["about.html"].split("skills-grid")[0] and "Teléfono" not in paginas["about.html"] and "GitHub" not in "".join(paginas.values())
    assert 'class="avatar"' not in paginas["index.html"] and 'class="avatar"' not in paginas["proyectos/lawpocket.html"]


def test_telefono_con_codigo_de_pais_no_se_duplica(contenido, ajustes):
    contenido["perfil"]["phone"] = "+1 555 123 4567"
    paginas, _ = sitio.renderizar(contenido, ajustes, PLANTILLAS)
    assert 'href="tel:+15551234567"' in paginas["about.html"]


def test_un_elemento_del_catalogo_sin_logo_no_rompe_la_cuadricula(contenido, ajustes):
    contenido["tech_stack"][0]["logo_url"] = None
    paginas, _ = sitio.renderizar(contenido, ajustes, PLANTILLAS)
    assert '<div class="skill-card"><p>Java</p></div>' in paginas["about.html"]


# ================================================================== enlaces a archivos
def test_localizador_distingue_blog_api_y_servicios_externos(tmp_path, ajustes):
    cache = tmp_path / "archivos"
    (cache / "certificados").mkdir(parents=True)
    (cache / "certificados" / "a.pdf").write_bytes(b"%PDF-")
    loc = sitio.Localizador(ajustes, "http://localhost:8000", cache)
    assert loc("https://segope.vercel.app/PDF/x.pdf") == "PDF/x.pdf"                                   # tu blog
    assert loc("https://santosgonzalez.dev/Imagenes/y.png") == "Imagenes/y.png"                        # dominio de ejemplo anterior
    assert loc("http://localhost:8000/media/certificados/a.pdf") == "archivos/certificados/a.pdf"      # copiado de la API
    assert loc("https://res.cloudinary.com/demo/image/upload/z.jpg") == "https://res.cloudinary.com/demo/image/upload/z.jpg"
    assert loc(None) is None and loc("") is None and loc.avisos == []
    assert loc("http://localhost:8000/media/certificados/falta.pdf") == "http://localhost:8000/media/certificados/falta.pdf"
    assert "falta.pdf" in loc.avisos[0]


def test_avisa_si_el_cms_pide_un_archivo_que_no_existe_en_el_blog(contenido, ajustes, tmp_path):
    (tmp_path / "PDF").mkdir()
    (tmp_path / "PDF" / "OperatingSystemsSupport.pdf").write_bytes(b"%PDF-")
    _, avisos = sitio.renderizar(contenido, ajustes, PLANTILLAS, raiz=tmp_path)
    assert any("PDF/InternetOfThings.pdf" in a for a in avisos) and not any("OperatingSystemsSupport.pdf" in a for a in avisos)


def test_certificado_subido_al_cms_se_enlaza_a_la_copia_local(contenido, ajustes, tmp_path):
    contenido["certificados"][0]["pdf_url"] = "http://localhost:8000/media/certificados/nuevo.pdf"
    contenido["certificados"][0]["image_url"] = "http://localhost:8000/media/certificados/nuevo.png"
    (tmp_path / "certificados").mkdir()
    (tmp_path / "certificados" / "nuevo.pdf").write_bytes(b"%PDF-")
    (tmp_path / "certificados" / "nuevo.png").write_bytes(b"\x89PNG")
    paginas, avisos = sitio.renderizar(contenido, ajustes, PLANTILLAS, cache=tmp_path)
    assert 'href="archivos/certificados/nuevo.pdf"' in paginas["about.html"] and 'data-cert-img="archivos/certificados/nuevo.png"' in paginas["index.html"]
    assert avisos == []


# ================================================================== helpers de texto
def test_fechas_en_espanol():
    assert sitio.fecha_larga("2026-07-15") == "15 de julio de 2026" and sitio.fecha_numerica("2025-12-01") == "01/12/2025"
    assert sitio.nombre_corto("LawPocket: gestión legal en la nube") == "LawPocket" and sitio.nombre_corto("Math & English Quest") == "Math & English Quest"
    assert sitio.articulos_publicados(1) == "1 artículo publicado" and sitio.articulos_publicados(3) == "3 artículos publicados"


# ================================================================== escribir en disco
def _blog_falso(raiz: Path):
    for carpeta, archivo in (("CSS", "index.css"), ("JS", "index.js"), ("Imagenes", "a.png"), ("PDF", "a.pdf")):
        (raiz / carpeta).mkdir(parents=True)
        (raiz / carpeta / archivo).write_text("x", encoding="utf-8")
    (raiz / "plantillas").mkdir()


def test_escribir_en_otra_carpeta_la_arma_completa_y_borra_lo_viejo(tmp_path):
    raiz, salida = tmp_path / "blog", tmp_path / "salida"
    _blog_falso(raiz)
    salida.mkdir()
    (salida / "viejo.html").write_text("vieja", encoding="utf-8")
    sitio.escribir({"index.html": "<p>hola</p>", "proyectos/a.html": "<p>a</p>"}, salida, raiz)
    assert (salida / "index.html").read_text(encoding="utf-8") == "<p>hola</p>" and (salida / "proyectos" / "a.html").exists()
    assert (salida / "CSS" / "index.css").exists() and (salida / "PDF" / "a.pdf").exists() and not (salida / "viejo.html").exists()


def test_escribir_en_la_raiz_solo_reemplaza_lo_generado(tmp_path):
    _blog_falso(tmp_path)
    (tmp_path / "proyectos").mkdir()
    (tmp_path / "proyectos" / "proyecto-archivado.html").write_text("vieja", encoding="utf-8")
    sitio.escribir({"index.html": "nueva", "proyectos/vigente.html": "ok"}, tmp_path, tmp_path)
    assert not (tmp_path / "proyectos" / "proyecto-archivado.html").exists()          # una página de un proyecto que ya no está publicado desaparece
    assert (tmp_path / "proyectos" / "vigente.html").exists() and (tmp_path / "CSS" / "index.css").exists() and (tmp_path / "plantillas").is_dir()


def test_escribir_copia_los_archivos_descargados_de_la_api(tmp_path):
    raiz, cache = tmp_path / "blog", tmp_path / "blog" / "datos" / "archivos"
    _blog_falso(raiz)
    (cache / "certificados").mkdir(parents=True)
    (cache / "certificados" / "x.pdf").write_bytes(b"%PDF-")
    sitio.escribir({"index.html": "x"}, raiz, raiz, cache)
    assert (raiz / "archivos" / "certificados" / "x.pdf").read_bytes() == b"%PDF-"


def test_no_borra_carpetas_peligrosas(tmp_path):
    raiz = tmp_path / "blog"
    _blog_falso(raiz)
    for peligrosa in (tmp_path, Path(tmp_path.anchor)):
        with pytest.raises(ValueError):
            sitio.escribir({"index.html": "x"}, peligrosa, raiz)
    assert (raiz / "CSS" / "index.css").exists()
