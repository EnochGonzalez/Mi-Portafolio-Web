"""Genera el blog (index.html, about.html y proyectos/<slug>.html) a partir del contenido del CMS.

Uso (desde la carpeta del blog):
    python generador/build.py --api http://localhost:8000     # lee la API, actualiza datos/contenido.json y genera
    python generador/build.py                                  # sin API: genera desde datos/contenido.json

Variables de entorno equivalentes: CMS_API_URL (--api) y SITE_BASE_URL (--sitio).
Si la API no responde y existe datos/contenido.json, se construye con esa copia (a menos que uses --exigir-api).
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import cms_api
import sitio

RAIZ = Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None, raiz: Path = RAIZ, cliente=None) -> int:
    parser = argparse.ArgumentParser(description="Genera el blog a partir del contenido del CMS.")
    parser.add_argument("--api", default=os.getenv("CMS_API_URL"), help="URL de la API (por defecto, la variable CMS_API_URL)")
    parser.add_argument("--sitio", default=os.getenv("SITE_BASE_URL", "https://segope.vercel.app"), help="dirección pública del blog")
    parser.add_argument("--salida", default=None, help="carpeta de salida (por defecto, la raíz del blog)")
    parser.add_argument("--exigir-api", action="store_true", help="falla si la API no responde, en vez de usar la copia local")
    args = parser.parse_args(argv)

    instantanea = raiz / "datos" / "contenido.json"
    cache = raiz / "datos" / "archivos"
    avisos: list[str] = []
    contenido = None

    if args.api:
        try:
            contenido = cms_api.descargar_contenido(args.api, cliente=cliente)
            cms_api.guardar_instantanea(contenido, instantanea)
            avisos += cms_api.descargar_archivos(contenido, cache)
            print(f"Contenido leído de {args.api} y guardado en datos/contenido.json")
        except cms_api.ErrorApi as error:
            if args.exigir_api or not instantanea.is_file():
                print(f"ERROR: {error}", file=sys.stderr)
                return 1
            print(f"AVISO: {error}\n       Se usa la copia guardada en datos/contenido.json", file=sys.stderr)
    if contenido is None:
        try:
            contenido = cms_api.leer_instantanea(instantanea)
        except cms_api.ErrorApi as error:
            print(f"ERROR: {error}", file=sys.stderr)
            return 1
        print(f"Contenido leído de datos/contenido.json (generado el {contenido.get('generado_en', '?')})")

    ajustes = sitio.Ajustes(sitio_url=args.sitio)
    paginas, avisos_pagina = sitio.renderizar(contenido, ajustes, raiz / "plantillas", cache, raiz)
    salida = Path(args.salida).resolve() if args.salida else raiz
    sitio.escribir(paginas, salida, raiz, cache)

    for aviso in avisos + avisos_pagina:
        print(f"AVISO: {aviso}", file=sys.stderr)
    proyectos = len(contenido["proyectos"])
    print(f"Listo: {len(paginas)} páginas ({proyectos} proyectos) en {salida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
