# SEGOPE.dev — Blog Dev de Santos González

Blog estático optimizado para SEO. Cada página es un módulo independiente:
su propio HTML, su propio CSS y su propio JS, sin un archivo gigante
compartido que haya que rastrear.

## Estructura de carpetas

```
BlogDev/
├── index.html              → Módulo "Inicio"
├── about.html                → Módulo "Acerca"
├── HTML/
│   ├── LawPocket.html         → Módulo del artículo
│   ├── MathEnglishQuest.html
│   └── SeriesTaylor.html
├── CSS/
│   ├── index.css              → Estilos solo de Inicio
│   ├── about.css              → Estilos solo de Acerca
│   ├── LawPocket.css          → Estilos solo de ese artículo
│   ├── MathEnglishQuest.css
│   └── SeriesTaylor.css
├── JS/
│   ├── index.js               → JS solo de Inicio (buscador)
│   ├── about.js               → JS solo de Acerca
│   ├── LawPocket.js           → JS solo de ese artículo
│   ├── MathEnglishQuest.js
│   └── SeriesTaylor.js
├── Imagenes/
├── sitemap.xml, robots.txt, feed.xml   → Se quedan en la raíz (SEO)
```

## Antes de publicar

Cambia `BASE_URL` en `build_site.py` (ahora `https://santosgonzalez.dev`,
un marcador de posición) por tu dominio real si vas a publicarlo — de eso
depende que el `canonical`, el `sitemap.xml` y el `feed.xml` apunten al
lugar correcto.
