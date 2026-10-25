"""Una API del CMS de mentiras (sin red): responde con el formato real {status, message, data} y pagina por cursor."""
import httpx


def api_falsa(contenido: dict, fallos_iniciales: int = 0, caida_total: bool = False) -> httpx.MockTransport:
    estado = {"fallos": fallos_iniciales, "peticiones": []}

    def envolver(datos, codigo=200):
        return httpx.Response(codigo, json={"status": "success", "message": "ok", "data": datos})

    def paginar(items, params):
        limite = int(params.get("limit", 20))
        inicio = int(params.get("cursor", 0))
        resto = items[inicio:inicio + limite]
        siguiente = str(inicio + limite) if inicio + limite < len(items) else None
        return envolver({"items": resto, "next_cursor": siguiente})

    def manejar(request: httpx.Request) -> httpx.Response:
        estado["peticiones"].append(request.url.path)
        if caida_total:
            raise httpx.ConnectError("sin conexión", request=request)
        if estado["fallos"] > 0:
            estado["fallos"] -= 1
            return httpx.Response(503, json={"status": "error", "code": "ARRANCANDO", "message": "despertando", "details": []})
        ruta, params = request.url.path, dict(request.url.params)
        if ruta == "/api/v1/public/profile":
            return envolver(contenido["perfil"])
        if ruta == "/api/v1/public/projects":
            tarjetas = [{k: v for k, v in p.items() if k != "description"} for p in contenido["proyectos"]]
            return paginar(tarjetas, params)
        if ruta.startswith("/api/v1/public/projects/"):
            slug = ruta.rsplit("/", 1)[1]
            proyecto = next((p for p in contenido["proyectos"] if p["slug"] == slug), None)
            if proyecto is None:
                return httpx.Response(404, json={"status": "error", "code": "PROJECT_NOT_FOUND", "message": "no existe", "details": []})
            return envolver({k: v for k, v in proyecto.items() if k != "is_featured"})
        if ruta == "/api/v1/public/certificates":
            return paginar(contenido["certificados"], params)
        if ruta == "/api/v1/public/tech-stack":
            return paginar(contenido["tech_stack"], params)
        return httpx.Response(404, json={"status": "error", "code": "NOT_FOUND", "message": "no", "details": []})

    transporte = httpx.MockTransport(manejar)
    transporte.estado = estado
    return transporte


def cliente_falso(contenido, **opciones) -> httpx.Client:
    return httpx.Client(transport=api_falsa(contenido, **opciones), base_url="http://api.prueba")
