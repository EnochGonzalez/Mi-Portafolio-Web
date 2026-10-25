"""Cliente de la API del CMS (solo lecturas públicas: no necesita token) y copia local del contenido.

El generador del blog usa esto para traer el contenido y guardarlo en datos/contenido.json (una "instantánea").
Si más adelante la API no está disponible, el blog se puede construir igual desde esa instantánea.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import httpx

REINTENTOS = 5                         # veces que se intenta cada petición (la API gratuita puede tardar en "despertar")
ESPERA_INICIAL = 2.0                   # segundos; se duplica en cada intento (2, 4, 8, 16)
CODIGOS_REINTENTABLES = {429, 502, 503, 504}
LIMITE_PAGINA = 50


class ErrorApi(Exception):
    """No se pudo leer el contenido de la API."""


def pedir(cliente: httpx.Client, ruta: str, params: dict | None = None, dormir=time.sleep):
    """GET con reintentos. Devuelve el campo `data` de la respuesta {status, message, data}."""
    ultimo = "sin respuesta"
    for intento in range(REINTENTOS):
        if intento:
            dormir(min(ESPERA_INICIAL * 2 ** (intento - 1), 20))
        try:
            respuesta = cliente.get(ruta, params=params)
        except httpx.TransportError as error:                 # sin conexión, tiempo agotado...
            ultimo = type(error).__name__
            continue
        if respuesta.status_code == 200:
            return respuesta.json()["data"]
        if respuesta.status_code in CODIGOS_REINTENTABLES:
            ultimo = f"HTTP {respuesta.status_code}"
            continue
        raise ErrorApi(f"{ruta} respondió HTTP {respuesta.status_code}: {respuesta.text[:200]}")
    raise ErrorApi(f"No se pudo leer {ruta} tras {REINTENTOS} intentos ({ultimo})")


def pedir_todas(cliente: httpx.Client, ruta: str, dormir=time.sleep) -> list[dict]:
    """Lee todas las páginas de una lista, siguiendo next_cursor."""
    elementos: list[dict] = []
    cursor = None
    while True:
        params = {"limit": LIMITE_PAGINA, **({"cursor": cursor} if cursor else {})}
        pagina = pedir(cliente, ruta, params, dormir)
        elementos.extend(pagina["items"])
        cursor = pagina["next_cursor"]
        if cursor is None:
            return elementos


def descargar_contenido(url_api: str, cliente: httpx.Client | None = None, dormir=time.sleep) -> dict:
    """Trae de la API el perfil, los proyectos publicados (con su detalle), los certificados y el catálogo."""
    propio = cliente is None
    if cliente is None:
        cliente = httpx.Client(base_url=url_api, timeout=httpx.Timeout(60.0, connect=15.0))
    try:
        perfil = pedir(cliente, "/api/v1/public/profile", None, dormir)
        tarjetas = pedir_todas(cliente, "/api/v1/public/projects", dormir)
        # La lista trae lo de la tarjeta; el detalle agrega la descripción larga.
        proyectos = [{**t, **pedir(cliente, f"/api/v1/public/projects/{t['slug']}", None, dormir)} for t in tarjetas]
        certificados = pedir_todas(cliente, "/api/v1/public/certificates", dormir)
        tech_stack = pedir_todas(cliente, "/api/v1/public/tech-stack", dormir)
    finally:
        if propio:
            cliente.close()
    return {
        "generado_en": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fuente": url_api.rstrip("/"),
        "perfil": perfil,
        "proyectos": proyectos,
        "certificados": certificados,
        "tech_stack": tech_stack,
    }


# ------------------------------------------------------------------ instantánea (datos/contenido.json)
def guardar_instantanea(contenido: dict, ruta: Path) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(contenido, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def leer_instantanea(ruta: Path) -> dict:
    if not ruta.is_file():
        raise ErrorApi(f"No hay instantánea en {ruta}. Corre el generador una vez con la API encendida (--api).")
    return json.loads(ruta.read_text(encoding="utf-8"))


# ------------------------------------------------------------------ archivos que viven en la API (/media)
def urls_de_archivos(contenido: dict) -> list[str]:
    """Todas las URLs de archivos (PDF, imágenes, logos, foto) que aparecen en el contenido."""
    urls = [contenido["perfil"].get("photo_url")]
    for certificado in contenido["certificados"]:
        urls += [certificado.get("pdf_url"), certificado.get("image_url")]
    urls += [item.get("logo_url") for item in contenido["tech_stack"]]
    return [u for u in urls if u]


def descargar_archivos(contenido: dict, destino: Path, cliente: httpx.Client | None = None) -> list[str]:
    """Copia a `destino` (datos/archivos) los archivos que están en el /media de la API.

    Así el blog se construye sin la API (y no depende de que el disco de la API conserve los archivos).
    Los archivos que ya vivían en tu blog (PDF/, Imagenes/) o en otro servicio no se tocan. Devuelve avisos."""
    fuente = contenido["fuente"]
    prefijo = fuente + "/media/"
    avisos: list[str] = []
    propio = cliente is None
    cliente = cliente or httpx.Client(timeout=60.0)
    try:
        for url in dict.fromkeys(urls_de_archivos(contenido)):            # sin repetidos, en orden
            if not url.startswith(prefijo):
                continue
            relativa = url[len(prefijo):]
            if ".." in relativa.split("/") or relativa.startswith("/"):
                avisos.append(f"Ruta sospechosa ignorada: {url}")
                continue
            archivo = destino / relativa
            if archivo.is_file():
                continue
            try:
                respuesta = cliente.get(url)
                respuesta.raise_for_status()
            except httpx.HTTPError as error:
                avisos.append(f"No pude descargar {url} ({type(error).__name__})")
                continue
            archivo.parent.mkdir(parents=True, exist_ok=True)
            archivo.write_bytes(respuesta.content)
    finally:
        if propio:
            cliente.close()
    return avisos
