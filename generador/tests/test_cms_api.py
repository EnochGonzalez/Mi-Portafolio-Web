"""Lectura de la API: reintentos, paginación, copia local del contenido y de los archivos."""
import httpx
import pytest

import cms_api
from api_falsa import api_falsa, cliente_falso


@pytest.fixture(autouse=True)
def sin_esperas(monkeypatch):
    monkeypatch.setattr(cms_api, "ESPERA_INICIAL", 0)          # los reintentos no hacen esperar a la prueba


# ------------------------------------------------------------------ reintentos
def test_reintenta_cuando_la_api_esta_despertando(contenido):
    cliente = cliente_falso(contenido, fallos_iniciales=2)
    assert cms_api.pedir(cliente, "/api/v1/public/profile")["full_name"] == contenido["perfil"]["full_name"]
    assert len(cliente._transport.estado["peticiones"]) == 3                 # 2 intentos fallidos + 1 bueno


def test_las_esperas_entre_reintentos_se_duplican(contenido, monkeypatch):
    monkeypatch.setattr(cms_api, "ESPERA_INICIAL", 2.0)
    esperas = []
    cms_api.pedir(cliente_falso(contenido, fallos_iniciales=3), "/api/v1/public/profile", dormir=esperas.append)
    assert esperas == [2.0, 4.0, 8.0]


def test_se_rinde_despues_de_cinco_intentos(contenido):
    cliente = cliente_falso(contenido, caida_total=True)
    with pytest.raises(cms_api.ErrorApi, match="tras 5 intentos"):
        cms_api.pedir(cliente, "/api/v1/public/profile")
    assert len(cliente._transport.estado["peticiones"]) == 5


def test_un_error_que_no_se_arregla_reintentando_no_se_reintenta(contenido):
    cliente = cliente_falso(contenido)
    with pytest.raises(cms_api.ErrorApi, match="HTTP 404"):
        cms_api.pedir(cliente, "/api/v1/public/projects/no-existe")
    assert len(cliente._transport.estado["peticiones"]) == 1


# ------------------------------------------------------------------ paginación y contenido completo
def test_pedir_todas_sigue_los_cursores(contenido, monkeypatch):
    monkeypatch.setattr(cms_api, "LIMITE_PAGINA", 6)
    cliente = cliente_falso(contenido)
    items = cms_api.pedir_todas(cliente, "/api/v1/public/tech-stack")
    assert [i["name"] for i in items] == [i["name"] for i in contenido["tech_stack"]] and len(items) == 16
    assert cliente._transport.estado["peticiones"].count("/api/v1/public/tech-stack") == 3     # 6 + 6 + 4


def test_descargar_contenido_junta_la_tarjeta_con_el_detalle(contenido):
    cliente = cliente_falso(contenido)
    descargado = cms_api.descargar_contenido("http://api.prueba/", cliente)
    assert descargado["fuente"] == "http://api.prueba"
    assert [p["slug"] for p in descargado["proyectos"]] == ["lawpocket", "math-english-quest", "series-de-taylor"]
    assert all(p["description"] and "is_featured" in p for p in descargado["proyectos"])         # descripción (detalle) + is_featured (tarjeta)
    assert len(descargado["certificados"]) == 5 and len(descargado["tech_stack"]) == 16 and descargado["perfil"]["email"]
    assert not cliente.is_closed                                                                 # un cliente prestado no se cierra


def test_la_instantanea_se_guarda_y_se_lee_igual(contenido, tmp_path):
    ruta = tmp_path / "datos" / "contenido.json"
    cms_api.guardar_instantanea(contenido, ruta)
    assert cms_api.leer_instantanea(ruta) == contenido
    assert "González" in ruta.read_text(encoding="utf-8")                                         # acentos legibles, no \u00f3
    with pytest.raises(cms_api.ErrorApi, match="No hay instantánea"):
        cms_api.leer_instantanea(tmp_path / "no-existe.json")


# ------------------------------------------------------------------ archivos que viven en la API
def _contenido_con_media(contenido):
    contenido["fuente"] = "http://api.prueba"
    contenido["certificados"][0]["pdf_url"] = "http://api.prueba/media/certificados/nuevo.pdf"
    contenido["certificados"][0]["image_url"] = "http://api.prueba/media/certificados/nuevo.jpg"
    contenido["certificados"][1]["pdf_url"] = "https://res.cloudinary.com/demo/otro.pdf"
    return contenido


def _cliente_de_archivos(archivos, contados):
    def manejar(request):
        contados.append(str(request.url))
        if request.url.path in archivos:
            return httpx.Response(200, content=archivos[request.url.path])
        return httpx.Response(404)
    return httpx.Client(transport=httpx.MockTransport(manejar))


def test_solo_se_descargan_los_archivos_del_media_de_la_api(contenido, tmp_path):
    pedidos = []
    cliente = _cliente_de_archivos({"/media/certificados/nuevo.pdf": b"%PDF-1", "/media/certificados/nuevo.jpg": b"\xff\xd8\xff"}, pedidos)
    avisos = cms_api.descargar_archivos(_contenido_con_media(contenido), tmp_path, cliente)
    assert avisos == [] and sorted(pedidos) == ["http://api.prueba/media/certificados/nuevo.jpg", "http://api.prueba/media/certificados/nuevo.pdf"]
    assert (tmp_path / "certificados" / "nuevo.pdf").read_bytes() == b"%PDF-1"            # lo del blog y lo de Cloudinary no se tocó


def test_los_archivos_ya_copiados_no_se_vuelven_a_descargar(contenido, tmp_path):
    (tmp_path / "certificados").mkdir()
    (tmp_path / "certificados" / "nuevo.pdf").write_bytes(b"ya estaba")
    pedidos = []
    cms_api.descargar_archivos(_contenido_con_media(contenido), tmp_path, _cliente_de_archivos({"/media/certificados/nuevo.jpg": b"x"}, pedidos))
    assert pedidos == ["http://api.prueba/media/certificados/nuevo.jpg"] and (tmp_path / "certificados" / "nuevo.pdf").read_bytes() == b"ya estaba"


def test_si_un_archivo_falla_se_avisa_y_se_sigue(contenido, tmp_path):
    avisos = cms_api.descargar_archivos(_contenido_con_media(contenido), tmp_path, _cliente_de_archivos({"/media/certificados/nuevo.jpg": b"x"}, []))
    assert len(avisos) == 1 and "nuevo.pdf" in avisos[0] and (tmp_path / "certificados" / "nuevo.jpg").exists()


def test_rutas_con_puntos_dobles_no_escapan_de_la_carpeta(contenido, tmp_path):
    contenido["fuente"] = "http://api.prueba"
    contenido["perfil"]["photo_url"] = "http://api.prueba/media/../../secreto.png"
    pedidos = []
    avisos = cms_api.descargar_archivos(contenido, tmp_path / "datos", _cliente_de_archivos({}, pedidos))
    assert any("sospechosa" in a for a in avisos) and pedidos == [] and not (tmp_path / "secreto.png").exists()
