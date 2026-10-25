"""El comando completo (build.py): con la API, sin la API y con la API caída."""
import json
import shutil

import pytest

import build
import cms_api
from api_falsa import cliente_falso
from conftest import PLANTILLAS, RAIZ


@pytest.fixture(autouse=True)
def sin_esperas(monkeypatch):
    monkeypatch.setattr(cms_api, "ESPERA_INICIAL", 0)


@pytest.fixture()
def blog(tmp_path):
    """Un blog de mentiras con las plantillas reales y los CSS/JS/Imagenes/PDF mínimos."""
    shutil.copytree(PLANTILLAS, tmp_path / "plantillas")
    for carpeta in ("CSS", "JS", "Imagenes", "PDF"):
        shutil.copytree(RAIZ / carpeta, tmp_path / carpeta)
    return tmp_path


def correr(blog, *argumentos, cliente=None):
    return build.main(["--sitio", "https://segope.vercel.app", *argumentos], raiz=blog, cliente=cliente)


def test_con_la_api_genera_el_blog_y_guarda_la_instantanea(blog, contenido, capsys):
    assert correr(blog, "--api", "http://api.prueba", cliente=cliente_falso(contenido)) == 0
    for pagina in ("index.html", "about.html", "proyectos/lawpocket.html", "proyectos/math-english-quest.html", "proyectos/series-de-taylor.html"):
        assert (blog / pagina).is_file(), pagina
    guardado = json.loads((blog / "datos" / "contenido.json").read_text(encoding="utf-8"))
    assert guardado["fuente"] == "http://api.prueba" and len(guardado["proyectos"]) == 3
    assert "Listo: 5 páginas (3 proyectos)" in capsys.readouterr().out


def test_sin_api_construye_desde_la_instantanea(blog, contenido, capsys):
    cms_api.guardar_instantanea(contenido, blog / "datos" / "contenido.json")
    assert correr(blog) == 0
    assert (blog / "index.html").is_file() and "datos/contenido.json (generado el" in capsys.readouterr().out


def test_si_la_api_esta_caida_se_usa_la_copia_guardada_y_el_blog_no_se_rompe(blog, contenido, capsys):
    cms_api.guardar_instantanea(contenido, blog / "datos" / "contenido.json")
    assert correr(blog, "--api", "http://api.prueba", cliente=cliente_falso(contenido, caida_total=True)) == 0
    salida = capsys.readouterr()
    assert "AVISO" in salida.err and "copia guardada" in salida.err and (blog / "proyectos" / "lawpocket.html").is_file()


def test_si_la_api_esta_caida_y_no_hay_copia_falla_con_un_mensaje_claro(blog, contenido, capsys):
    assert correr(blog, "--api", "http://api.prueba", cliente=cliente_falso(contenido, caida_total=True)) == 1
    assert "ERROR" in capsys.readouterr().err and not (blog / "index.html").exists()


def test_exigir_api_no_acepta_la_copia(blog, contenido, capsys):
    cms_api.guardar_instantanea(contenido, blog / "datos" / "contenido.json")
    assert correr(blog, "--api", "http://api.prueba", "--exigir-api", cliente=cliente_falso(contenido, caida_total=True)) == 1
    assert not (blog / "index.html").exists()


def test_sin_api_ni_copia_explica_que_hacer(blog, capsys):
    assert correr(blog) == 1
    assert "--api" in capsys.readouterr().err


def test_un_proyecto_archivado_desaparece_del_blog_en_la_siguiente_construccion(blog, contenido):
    assert correr(blog, "--api", "http://api.prueba", cliente=cliente_falso(contenido)) == 0
    assert (blog / "proyectos" / "math-english-quest.html").is_file()
    contenido["proyectos"] = [p for p in contenido["proyectos"] if p["slug"] != "math-english-quest"]         # la API ya no lo devuelve
    assert correr(blog, "--api", "http://api.prueba", cliente=cliente_falso(contenido)) == 0
    assert not (blog / "proyectos" / "math-english-quest.html").exists() and "2 artículos publicados" in (blog / "index.html").read_text(encoding="utf-8")


def test_se_puede_generar_en_otra_carpeta_sin_tocar_el_blog(blog, contenido, tmp_path_factory):
    salida = tmp_path_factory.mktemp("salida")
    cms_api.guardar_instantanea(contenido, blog / "datos" / "contenido.json")
    assert correr(blog, "--salida", str(salida)) == 0
    assert (salida / "index.html").is_file() and (salida / "CSS" / "proyecto.css").is_file() and not (blog / "index.html").exists()


def test_el_dominio_sale_del_argumento_sitio(blog, contenido):
    cms_api.guardar_instantanea(contenido, blog / "datos" / "contenido.json")
    build.main(["--sitio", "https://otro.ejemplo.com/"], raiz=blog)
    assert 'rel="canonical" href="https://otro.ejemplo.com/index.html"' in (blog / "index.html").read_text(encoding="utf-8")


# ------------------------------------------------------------------ protección contra publicar un blog vacío
def _sin_proyectos(contenido):
    return {**contenido, "proyectos": []}


def test_si_la_api_responde_vacia_pero_la_copia_tenia_proyectos_no_se_genera_nada(blog, contenido, capsys):
    cms_api.guardar_instantanea(contenido, blog / "datos" / "contenido.json")
    correr(blog)                                                      # el blog bueno, ya generado
    bueno = (blog / "index.html").read_text(encoding="utf-8")
    assert correr(blog, "--api", "http://api.prueba", cliente=cliente_falso(_sin_proyectos(contenido))) == 1
    error = capsys.readouterr().err
    assert "no devolvió ningún proyecto" in error and "--permitir-vacio" in error
    assert (blog / "index.html").read_text(encoding="utf-8") == bueno                       # el blog no se tocó
    assert len(json.loads((blog / "datos" / "contenido.json").read_text(encoding="utf-8"))["proyectos"]) == 3   # ni la copia


def test_con_permitir_vacio_se_acepta_un_blog_sin_proyectos(blog, contenido):
    cms_api.guardar_instantanea(contenido, blog / "datos" / "contenido.json")
    assert correr(blog, "--api", "http://api.prueba", "--permitir-vacio", cliente=cliente_falso(_sin_proyectos(contenido))) == 0
    assert "0 artículos publicados" in (blog / "index.html").read_text(encoding="utf-8")


def test_la_primera_vez_sin_copia_previa_un_blog_vacio_es_normal(blog, contenido):
    assert correr(blog, "--api", "http://api.prueba", cliente=cliente_falso(_sin_proyectos(contenido))) == 0
    assert (blog / "index.html").is_file()


def test_una_copia_previa_dañada_no_impide_generar(blog, contenido):
    (blog / "datos").mkdir()
    (blog / "datos" / "contenido.json").write_text("{esto no es json", encoding="utf-8")
    assert correr(blog, "--api", "http://api.prueba", cliente=cliente_falso(contenido)) == 0
