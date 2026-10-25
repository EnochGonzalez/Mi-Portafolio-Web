# Generador del blog (Bloque 4)

El blog sigue siendo un sitio **estático**, pero ahora sus páginas ya no se escriben a mano: un script las arma
con el contenido que guardas en el CMS.

```
 CMS (API)  ──lee──►  generador/build.py  ──escribe──►  index.html, about.html y proyectos/<proyecto>.html
                          │   usa las plantillas de plantillas/
                          └──guarda una copia en datos/contenido.json
```

## Primera vez (en tu computadora)

Dentro de la carpeta del blog:

```
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r generador\requirements.txt
python -m pytest
```

`python -m pytest` debe terminar con `50 passed`.

## Cada vez que cambies contenido en el CMS

1. Enciende la API (en su carpeta): `python -m uvicorn app.main:app --reload`
2. En la carpeta del blog:

```
python generador\build.py --api http://localhost:8000
```

Eso trae el contenido, actualiza `datos/contenido.json` y reescribe las páginas. Abre `index.html` con Live Server
(o `python -m http.server 5500`) para revisar, y si todo está bien: `git add .`, `git commit`, `git push`.

Sin la API encendida también funciona (`python generador\build.py`): construye con la última copia guardada.

## Qué se genera y qué sigue siendo tuyo

| Carpeta o archivo | ¿Quién lo escribe? |
|---|---|
| `index.html`, `about.html`, `proyectos/*.html` | **El generador.** No los edites a mano: se reescriben en cada ejecución. |
| `archivos/` | El generador (copia de los PDF e imágenes que subes por el CMS). |
| `plantillas/` | **Tú.** Aquí cambias el diseño y los textos fijos de las páginas. |
| `CSS/`, `JS/`, `Imagenes/`, `PDF/` | **Tú.** `CSS/proyecto.css` y `JS/proyecto.js` los comparten todos los proyectos. |
| `datos/contenido.json` | El generador (copia del contenido del CMS; súbela a Git). |

## Qué viene del CMS y qué está en las plantillas

- **Del CMS:** proyectos (título, fecha, etiquetas, descripción, lenguajes, tecnologías, enlaces), certificados,
  lenguajes y herramientas (la cuadrícula de Acerca y "Stack actual"), y el perfil y contacto (nombre, foto, bio,
  correo, teléfono, GitHub).
- **De las plantillas:** el titular del Inicio ("Notas breves sobre…"), "Bitácora de desarrollo", los menús, el texto
  del botón ("Ver proyecto", en `Ajustes` de `generador/sitio.py`) y el nombre del sitio.
- **Derivado:** "3 artículos publicados", el tiempo de lectura, las fechas en español, los textos de SEO
  (títulos, descripciones, datos estructurados) y la navegación Anterior/Siguiente.

## Diferencias respecto al blog hecho a mano

Se comparó el blog anterior con el generado, con capturas en escritorio y celular: **Acerca, LawPocket y Series de
Taylor son idénticos píxel por píxel.** Lo único distinto:

- Las páginas de proyectos ahora viven en `proyectos/` (antes `HTML/`) y sus nombres van en minúsculas (`proyectos/lawpocket.html`); las viejas (`HTML/LawPocket.html`…) redirigen (ver `vercel.json`).
- Los tres proyectos comparten `proyecto.css` y `proyecto.js`.
- "Stack actual" ahora muestra los mismos lenguajes que Acerca (antes eran 5 escritos a mano, con "HTML / CSS" juntos).
- Los botones de proyecto dicen todos "Ver proyecto". El CMS no guarda un texto de botón por proyecto.
- Math & English Quest muestra "JavaScript, Kotlin" (el orden sale de `display_order`) y ya no lleva "(prototipo web)".
- Metadatos que estaban desactualizados (p. ej. "Series de Taylor con Canvas") ahora se toman del CMS.

## Si la API no responde

Cada petición se reintenta hasta 5 veces (esperando 2, 4, 8 y 16 segundos: una API gratuita puede tardar en despertar).
Si sigue sin responder y existe `datos/contenido.json`, se construye con esa copia y se avisa. Con `--exigir-api` falla
en vez de usar la copia.

## Publicar en Vercel

**Hoy (modo seguro):** el generador corre en tu computadora y subes el resultado con Git. Vercel solo sirve los archivos,
sin ejecutar nada, así que no puede fallar por la API.

**Más adelante (cuando la API esté publicada):** Vercel podrá ejecutar el generador en cada despliegue, con
`Build Command = pip install -r generador/requirements.txt && python generador/build.py` y las variables
`CMS_API_URL` y `SITE_BASE_URL`. Se conectará con el aviso de la API (deploy hook). Esto todavía no está activado.

Nota: Vercel publica también `generador/`, `plantillas/` y `datos/`. No tienen secretos (el contenido ya es público).

## Opciones del comando

| Opción | Para qué |
|---|---|
| `--api URL` | Leer la API (también: variable `CMS_API_URL`). |
| `--sitio URL` | Dirección pública del blog (también: `SITE_BASE_URL`; por defecto `https://segope.vercel.app`). |
| `--salida CARPETA` | Generar en otra carpeta, completa, sin tocar tus archivos. Útil para comparar. |
| `--exigir-api` | No usar la copia si la API falla. |
