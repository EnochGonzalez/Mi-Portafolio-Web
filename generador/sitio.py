"""Convierte el contenido del CMS (el JSON de la API) en las páginas HTML del blog.

Las páginas salen de las plantillas de plantillas/ (Jinja2). Aquí se prepara lo que las plantillas necesitan:
fechas en español, tiempo de lectura, enlaces a archivos, datos estructurados (JSON-LD) y la navegación entre proyectos.
"""
from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
MESES_CORTOS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
PALABRAS_POR_MINUTO = 200
CARPETAS_ESTATICAS = ("CSS", "JS", "Imagenes", "PDF")        # lo que se escribe a mano y no se genera
# Carpeta de las páginas de proyectos. Se llama distinto de la antigua HTML/ a propósito: Windows no distingue
# mayúsculas en los nombres y Git se confunde si solo cambia una mayúscula (LawPocket.html -> lawpocket.html).
CARPETA_PROYECTOS = "proyectos"


@dataclass
class Ajustes:
    """Datos del sitio que no vienen de la API."""
    sitio_url: str = "https://segope.vercel.app"
    nombre_sitio: str = "SEGOPE.dev"
    texto_boton_proyecto: str = "Ver proyecto"
    codigo_pais: str = "+52"                                       # para los enlaces tel: si el teléfono no trae +
    anio: int | None = None
    dominios_anteriores: tuple = ("https://santosgonzalez.dev",)   # dominio de ejemplo con el que se sembraron los datos

    def __post_init__(self):
        self.sitio_url = self.sitio_url.rstrip("/")
        if self.anio is None:
            self.anio = date.today().year

    @property
    def marca(self) -> str:
        return self.nombre_sitio.split(".")[0]

    @property
    def sufijo(self) -> str:
        return "." + self.nombre_sitio.split(".", 1)[1] if "." in self.nombre_sitio else ""

    @property
    def dominios_propios(self) -> list[str]:
        return [self.sitio_url, *[d.rstrip("/") for d in self.dominios_anteriores]]


# ------------------------------------------------------------------ enlaces a archivos
class Localizador:
    """Decide cómo enlazar cada archivo del CMS.

    - Si vive en tu propio blog (https://segope.vercel.app/PDF/x.pdf)  ->  ruta relativa (PDF/x.pdf).
    - Si está en el /media de la API y ya se copió a datos/archivos      ->  archivos/...
    - Cualquier otra URL (otro servicio, p. ej. Cloudinary)              ->  se deja tal cual.
    """

    def __init__(self, ajustes: Ajustes, fuente_api: str | None = None, cache: Path | None = None, raiz: Path | None = None):
        self.ajustes = ajustes
        self.fuente = fuente_api.rstrip("/") if fuente_api else None
        self.cache = cache
        self.raiz = raiz
        self.avisos: list[str] = []

    def __call__(self, url: str | None) -> str | None:
        if not url:
            return None
        for dominio in self.ajustes.dominios_propios:
            if url.startswith(dominio + "/"):
                relativa = url[len(dominio) + 1:]
                if self.raiz is not None and not (self.raiz / relativa).exists():
                    self.avisos.append(f"El archivo {relativa} no existe en el blog (lo pide el CMS).")
                return relativa
        if self.fuente and url.startswith(self.fuente + "/media/"):
            relativa = url[len(self.fuente) + len("/media/"):]
            if self.cache is not None and (self.cache / relativa).is_file():
                return "archivos/" + relativa
            self.avisos.append(f"No encontré {relativa} en datos/archivos; se deja la URL de la API: {url}")
        return url


def con_prefijo(valor: str | None, prefijo: str) -> str | None:
    """Rutas relativas llevan el prefijo de la página ('' en la raíz, '../' dentro de HTML/); las absolutas no."""
    if not valor or valor.startswith(("http://", "https://")):
        return valor
    return prefijo + valor


# ------------------------------------------------------------------ fechas y textos
def fecha_larga(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def fecha_numerica(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d.day:02d}/{d.month:02d}/{d.year}"


def inicial_minuscula(texto: str) -> str:
    return texto[:1].lower() + texto[1:]


def nombre_corto(titulo: str) -> str:
    """'LawPocket: gestión legal en la nube' -> 'LawPocket'."""
    return titulo.split(":")[0].strip()


def articulos_publicados(cantidad: int) -> str:
    return "1 artículo publicado" if cantidad == 1 else f"{cantidad} artículos publicados"


# ------------------------------------------------------------------ preparación de los datos de cada página
def _perfil(perfil: dict, localizar, prefijo: str, ajustes: Ajustes) -> dict:
    telefono = perfil.get("phone")
    tel_href = None
    if telefono:
        digitos = re.sub(r"\D", "", telefono)
        tel_href = "tel:" + ("+" + digitos if telefono.strip().startswith("+") else ajustes.codigo_pais + digitos)
    github = perfil.get("github_url")
    return {
        "nombre": perfil["full_name"], "puesto": perfil["job_title"], "puesto_min": inicial_minuscula(perfil["job_title"]),
        "lema": perfil["tagline"], "bio": perfil["bio"], "correo": perfil["email"],
        "telefono": telefono, "tel_href": tel_href,
        "github_url": github, "github_texto": re.sub(r"^https?://", "", github).rstrip("/") if github else None,
        "foto": con_prefijo(localizar(perfil.get("photo_url")), prefijo),
    }


def _certificados(certificados: list[dict], localizar, prefijo: str) -> list[dict]:
    return [{
        "titulo": c["title"], "institucion": c["issuer"], "fecha": fecha_numerica(c["issued_at"]),
        "pdf": con_prefijo(localizar(c["pdf_url"]), prefijo), "imagen": con_prefijo(localizar(c["image_url"]), prefijo),
    } for c in certificados]


def _habilidades(tech_stack: list[dict], localizar, prefijo: str) -> list[dict]:
    """Lo que aparece en 'Lenguajes y herramientas': los elementos con show_in_profile, en su orden."""
    return [{"nombre": i["name"], "logo": con_prefijo(localizar(i.get("logo_url")), prefijo)}
            for i in tech_stack if i["show_in_profile"]]


def _proyectos(proyectos: list[dict], ajustes: Ajustes) -> list[dict]:
    resultado = []
    for p in proyectos:
        lenguajes = [t["name"] for t in p["tech_stack"] if t["category"] == "LENGUAJE"]
        tecnologias = [t["name"] for t in p["tech_stack"] if t["category"] != "LENGUAJE"]
        texto = f"{p['description']} Lenguajes: {', '.join(lenguajes)}"
        if tecnologias:
            texto += f" Tecnologías: {', '.join(tecnologias)}"
        if p.get("demo_url"):
            texto += f" {ajustes.texto_boton_proyecto}"
        palabras = len(texto.split())
        fecha = date.fromisoformat(p["project_date"])
        url_pagina = f"{CARPETA_PROYECTOS}/{p['slug']}.html"
        resultado.append({
            "slug": p["slug"], "titulo": p["title"], "extracto": p["short_description"], "descripcion": p["description"],
            "fecha_iso": p["project_date"], "dia": f"{fecha.day:02d}", "mes_corto": MESES_CORTOS[fecha.month - 1], "anio": fecha.year,
            "fecha_larga": fecha_larga(p["project_date"]), "etiquetas": p["tags"], "lenguajes": lenguajes, "tecnologias": tecnologias,
            "demo_url": p.get("demo_url"), "repo_url": p.get("repo_url"),
            "palabras": palabras, "minutos": max(1, round(palabras / PALABRAS_POR_MINUTO)),
            "url_pagina": url_pagina, "url_absoluta": f"{ajustes.sitio_url}/{url_pagina}",
            "busqueda": " ".join([p["title"], p["short_description"], *p["tags"]]).lower(),
        })
    return resultado


# ------------------------------------------------------------------ datos estructurados (JSON-LD) para buscadores
def _ld_index(proyectos: list[dict], perfil: dict, ajustes: Ajustes) -> dict:
    return {
        "@context": "https://schema.org", "@type": "Blog", "name": ajustes.nombre_sitio, "url": f"{ajustes.sitio_url}/index.html",
        "description": f"Bitácora de desarrollo de {perfil['nombre']}.",
        "author": {"@type": "Person", "name": perfil["nombre"]},
        "blogPost": [{"@type": "BlogPosting", "headline": p["titulo"], "url": p["url_absoluta"], "datePublished": p["fecha_iso"]} for p in proyectos],
    }


def _ld_proyecto(p: dict, perfil: dict, ajustes: Ajustes) -> list[dict]:
    return [{
        "@context": "https://schema.org", "@type": "BlogPosting", "headline": p["titulo"], "description": p["extracto"],
        "datePublished": p["fecha_iso"], "dateModified": p["fecha_iso"],
        "author": {"@type": "Person", "name": perfil["nombre"], "url": f"{ajustes.sitio_url}/about.html"},
        "publisher": {"@type": "Person", "name": perfil["nombre"]},
        "mainEntityOfPage": {"@type": "WebPage", "@id": p["url_absoluta"]},
        "keywords": ", ".join(p["etiquetas"]), "wordCount": p["palabras"],
    }, {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Inicio", "item": f"{ajustes.sitio_url}/index.html"},
            {"@type": "ListItem", "position": 2, "name": "Artículos", "item": f"{ajustes.sitio_url}/index.html#articulos"},
            {"@type": "ListItem", "position": 3, "name": p["titulo"], "item": p["url_absoluta"]},
        ],
    }]


def _ld_acerca(perfil: dict, habilidades: list[dict], ajustes: Ajustes) -> dict:
    return {
        "@context": "https://schema.org", "@type": "Person", "name": perfil["nombre"], "url": f"{ajustes.sitio_url}/about.html",
        "jobTitle": perfil["puesto"], "knowsAbout": [h["nombre"] for h in habilidades],
    }


# ------------------------------------------------------------------ plantillas
def crear_entorno(carpeta_plantillas: Path) -> Environment:
    entorno = Environment(
        loader=FileSystemLoader(str(carpeta_plantillas)),
        autoescape=select_autoescape(["html"]),                  # &, <, > y comillas se escapan solos
        trim_blocks=True, lstrip_blocks=True, keep_trailing_newline=True,
    )
    # JSON-LD dentro de <script>: JSON normal, sin escapar acentos, y sin poder cerrar la etiqueta por accidente.
    entorno.filters["json_ld"] = lambda dato: Markup(json.dumps(dato, ensure_ascii=False).replace("</", "<\\/"))
    return entorno


def renderizar(contenido: dict, ajustes: Ajustes, carpeta_plantillas: Path, cache: Path | None = None,
               raiz: Path | None = None) -> tuple[dict[str, str], list[str]]:
    """Devuelve ({ruta de salida: html}, avisos). No escribe nada en disco."""
    entorno = crear_entorno(carpeta_plantillas)
    localizar = Localizador(ajustes, contenido.get("fuente"), cache, raiz)
    proyectos = _proyectos(contenido["proyectos"], ajustes)
    sitio = {"ajustes": ajustes, "anio": ajustes.anio}
    paginas: dict[str, str] = {}

    # ---- Inicio
    perfil = _perfil(contenido["perfil"], localizar, "", ajustes)
    habilidades = _habilidades(contenido["tech_stack"], localizar, "")
    certificados = _certificados(contenido["certificados"], localizar, "")
    nombres = ", ".join(nombre_corto(p["titulo"]) for p in proyectos[:2]) or "mis proyectos"
    descripcion = f"Bitácora de desarrollo de {perfil['nombre']}: {nombres} y otros proyectos."
    paginas["index.html"] = entorno.get_template("index.html").render(
        **sitio, prefijo="", pagina="inicio", css="index.css", js="index.js", perfil=perfil,
        titulo=f"{ajustes.nombre_sitio} — bitácora de {perfil['nombre']}", descripcion=descripcion,
        url_canonica=f"{ajustes.sitio_url}/index.html", og_tipo="website",
        ld=_ld_index(proyectos, perfil, ajustes), articulos=proyectos, conteo=articulos_publicados(len(proyectos)),
        nombres=nombres, habilidades=habilidades, certificados=certificados[:3],
    )

    # ---- Acerca
    paginas["about.html"] = entorno.get_template("about.html").render(
        **sitio, prefijo="", pagina="acerca", css="about.css", js="about.js", perfil=perfil,
        titulo=f"Acerca del autor | {ajustes.nombre_sitio}", descripcion=f"{perfil['nombre']}, {perfil['puesto_min']}.",
        url_canonica=f"{ajustes.sitio_url}/about.html", og_tipo="profile",
        ld=_ld_acerca(perfil, habilidades, ajustes), habilidades=habilidades, certificados=certificados,
    )

    # ---- una página por proyecto (están en proyectos/, así que las rutas relativas llevan '../')
    perfil_hijo = _perfil(contenido["perfil"], localizar, "../", ajustes)
    for i, p in enumerate(proyectos):
        copiar_url = p["demo_url"] or p["url_absoluta"]
        paginas[p["url_pagina"]] = entorno.get_template("proyecto.html").render(
            **sitio, prefijo="../", pagina="articulo", css="proyecto.css", js="proyecto.js", perfil=perfil_hijo,
            titulo=f"{p['titulo']} | {ajustes.nombre_sitio}", descripcion=p["extracto"],
            url_canonica=p["url_absoluta"], og_tipo="article", p=p, ld_proyecto=_ld_proyecto(p, perfil_hijo, ajustes),
            anterior=proyectos[i - 1] if i > 0 else None, siguiente=proyectos[i + 1] if i < len(proyectos) - 1 else None,
            url_copiar=copiar_url, texto_copiar="Copiar enlace del proyecto" if p["demo_url"] else "Copiar enlace del artículo",
        )
    return paginas, localizar.avisos


# ------------------------------------------------------------------ escritura en disco
def escribir(paginas: dict[str, str], salida: Path, raiz: Path, cache: Path | None = None) -> None:
    """Escribe las páginas. Si la salida es la raíz del blog, solo reemplaza lo generado (proyectos/ y archivos/);
    si es otra carpeta, la borra y la arma completa copiando CSS, JS, Imagenes y PDF."""
    salida, raiz = salida.resolve(), raiz.resolve()
    en_sitio = salida == raiz
    if not en_sitio:
        if salida == Path(salida.anchor) or salida in raiz.parents:
            raise ValueError(f"Por seguridad no borro {salida}")
        shutil.rmtree(salida, ignore_errors=True)
    else:
        for generada in (CARPETA_PROYECTOS, "archivos"):
            shutil.rmtree(salida / generada, ignore_errors=True)
    salida.mkdir(parents=True, exist_ok=True)

    if not en_sitio:
        for carpeta in CARPETAS_ESTATICAS:
            if (raiz / carpeta).is_dir():
                shutil.copytree(raiz / carpeta, salida / carpeta)
    if cache is not None and cache.is_dir() and any(cache.rglob("*")):
        shutil.copytree(cache, salida / "archivos", dirs_exist_ok=True)

    for ruta, html in paginas.items():
        destino = salida / ruta
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(html, encoding="utf-8")
