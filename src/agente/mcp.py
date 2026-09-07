"""Las tools que viven en el MCP de Studiante.

El agente no habla con el API de Studiante: habla con `studiante-agent-mcp`,
que a su vez habla con el API usando una llave de servicio acotada. Esa vuelta
de más es el punto: este proceso recibe mensajes de desconocidos, y lo que
tiene en la mano solo alcanza para LEER el catálogo publicado y anotar lo que
la gente pide. Ni con la mejor inyección de prompt puede borrar un pensum,
porque la credencial que hace eso no está acá.

**Por qué hay un hilo con su propio event loop.** Las tools que devuelve
`langchain-mcp-adapters` son asíncronas, y el grafo de este kit corre síncrono
(`grafo.invoke`) dentro de un `asyncio.to_thread`. Llamar a una tool async
desde ahí revienta con NotImplementedError. La salida limpia es un event loop
propio, en un hilo demonio, al que se le mandan las corrutinas y se espera el
resultado: la conexión MCP queda viva entre mensajes (no se reconecta en cada
pregunta) y el grafo sigue siendo el mismo código síncrono de siempre.

Si `MCP_URL` no está configurada, esto devuelve una lista vacía y el agente
funciona igual, solo que sin catálogo ni sugerencias. Es a propósito: la
plataforma de pruebas y los tests no tienen por qué levantar un MCP.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any

from . import traspaso
from .contexto import canal_actual, conversacion_actual

registro = logging.getLogger("agente.mcp")

# Cuánto se espera una tool antes de cortar. El modelo ya hizo esperar a la
# persona; si el MCP no contesta en este tiempo, es mejor un error que un
# silencio de un minuto.
ESPERA = 20

_loop: asyncio.AbstractEventLoop | None = None
_hilo: threading.Thread | None = None
_candado = threading.Lock()

# El catálogo estaba configurado y no se pudo conectar. Es distinto de "no hay
# MCP": si nadie lo configuró, el agente no tiene por qué avisar nada.
_caido = False


def catalogo_caido() -> bool:
    """Si el catálogo está configurado pero hoy no se puede consultar."""
    return _caido


def _loop_de_fondo() -> asyncio.AbstractEventLoop:
    """El event loop donde viven la conexión MCP y sus llamadas."""
    global _loop, _hilo
    with _candado:
        if _loop is not None:
            return _loop

        _loop = asyncio.new_event_loop()

        def correr() -> None:
            asyncio.set_event_loop(_loop)
            _loop.run_forever()

        # Demonio: si el proceso se va, este hilo no lo retiene.
        _hilo = threading.Thread(target=correr, name="mcp-loop", daemon=True)
        _hilo.start()
        return _loop


def _esperar(corrutina, espera: float = ESPERA) -> Any:
    """Corre una corrutina en el loop de fondo y espera el resultado acá."""
    futuro = asyncio.run_coroutine_threadsafe(corrutina, _loop_de_fondo())
    return futuro.result(timeout=espera)


def cargar_herramientas(url: str, token: str = "") -> list:
    """Se conecta al MCP y devuelve sus tools, ya usables desde código síncrono.

    Se llama UNA vez, al armar el agente. Si el MCP no está o no contesta, se
    devuelve una lista vacía y queda en los logs: un agente sin catálogo
    contesta peor, pero contesta — dejar de atender WhatsApp porque un servicio
    auxiliar está caído sería el peor de los dos mundos.
    """
    url = (url or "").strip()
    if not url:
        return []

    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient
    except ImportError:  # pragma: no cover - depende del requirements instalado
        registro.error("Falta langchain-mcp-adapters: el agente arranca sin tools del MCP.")
        _marcar_caido(True)
        return []

    conexion: dict[str, Any] = {"url": url, "transport": "streamable_http"}
    if token:
        conexion["headers"] = {"Authorization": f"Bearer {token}"}

    try:
        cliente = MultiServerMCPClient({"studiante": conexion})
        tools = _esperar(cliente.get_tools(), espera=30)
    except Exception as e:
        registro.error("No se pudo conectar al MCP (%s): %s", url, e)
        _marcar_caido(True)
        return []

    _marcar_caido(False)
    envueltas = [_envolver(t) for t in tools]
    registro.info("MCP conectado: %s tool(s) — %s", len(envueltas), ", ".join(t.name for t in envueltas))
    return envueltas


def _envolver(tool):
    """Le pone a una tool async un camino síncrono, sin tocar el resto.

    LangChain llama `tool.func` cuando el grafo corre síncrono y `tool.coroutine`
    cuando corre async. Las del MCP solo traen la segunda; acá se agrega la
    primera, que manda la misma corrutina al loop de fondo y espera. La tool
    sigue siendo la misma: mismo nombre, misma descripción, mismo esquema de
    argumentos, que es lo que el modelo lee.
    """
    if getattr(tool, "func", None) is not None:
        return tool

    corrutina = tool.coroutine
    campos = set(getattr(getattr(tool, "args_schema", None), "model_fields", {}) or {})

    def sincrono(*args, **kwargs):
        # La conversación no la pone el modelo: la pone el canal (contexto.py).
        # Así el pedido queda atado al chat de donde salió y nadie tiene que
        # confiar en que el modelo copie bien un id que no conoce.
        if "conversation" in campos and not kwargs.get("conversation"):
            conversacion = conversacion_actual.get()
            if conversacion:
                kwargs["conversation"] = conversacion
        if "channel" in campos and not kwargs.get("channel"):
            canal = canal_actual.get()
            if canal:
                kwargs["channel"] = canal
        try:
            return _esperar(corrutina(*args, **kwargs))
        except Exception as e:
            # Que una consulta falle no puede voltear la respuesta entera. El
            # modelo recibe un texto honesto —que además le dice qué hacer— y
            # sigue; y queda anotado para que el webhook le pase la
            # conversación a una persona en vez de dejar una respuesta a
            # medias como si nada hubiera pasado.
            registro.error("La tool %s falló: %s", tool.name, e)
            traspaso.pedir(
                conversacion_actual.get(),
                f"El agente no pudo consultar el catálogo ({tool.name}) al responder "
                "este mensaje, así que puede haber contestado de menos. Lo dejo para "
                "que lo revise una persona.",
            )
            return (
                "No se pudo consultar el catálogo de Studiante en este momento. "
                "No inventes la respuesta ni afirmes que algo no está: decile a "
                "la persona que lo vas a confirmar con el equipo."
            )

    tool.func = sincrono
    return tool


def _marcar_caido(caido: bool) -> None:
    global _caido
    _caido = caido
