import copy
import json
from pathlib import Path

import pytest

import sitio

RAIZ = Path(__file__).resolve().parents[2]
PLANTILLAS = RAIZ / "plantillas"


@pytest.fixture()
def contenido():
    """Copia del contenido real del blog tal como lo entrega la API (3 proyectos, 5 certificados, 16 del catálogo, perfil)."""
    datos = json.loads((Path(__file__).parent / "contenido_ejemplo.json").read_text(encoding="utf-8"))
    return copy.deepcopy(datos)


@pytest.fixture()
def ajustes():
    return sitio.Ajustes(sitio_url="https://segope.vercel.app", anio=2026)


@pytest.fixture()
def paginas(contenido, ajustes):
    resultado, _ = sitio.renderizar(contenido, ajustes, PLANTILLAS)
    return resultado
