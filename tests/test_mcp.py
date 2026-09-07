"""El puente con el MCP: que una tool async se pueda llamar desde el grafo
síncrono, y que la conversación viaje sola.

No levanta el MCP de verdad: fabrica una tool async igual a las que devuelve
`langchain-mcp-adapters` y la pasa por el mismo envoltorio que usa el agente.
Lo que se prueba es el pegamento, que es donde estaba el riesgo.
"""

import sys
from pathlib import Path

import pytest
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agente.contexto import canal_actual, conversacion_actual  # noqa: E402
from agente.mcp import _envolver  # noqa: E402


class Argumentos(BaseModel):
    kind: str = Field(description="feature | bug")
    title: str
    conversation: str = ""
    channel: str = ""


def _tool_async(recibido: list):
    """Una tool como las del MCP: solo async, con esquema de argumentos."""

    async def corrutina(**kwargs):
        recibido.append(kwargs)
        return "anotado"

    return StructuredTool(
        name="record_feature_request",
        description="anota un pedido",
        args_schema=Argumentos,
        coroutine=corrutina,
    )


def test_una_tool_async_se_puede_llamar_desde_codigo_sincrono():
    """Sin el envoltorio esto revienta con NotImplementedError."""
    recibido = []
    tool = _envolver(_tool_async(recibido))

    salida = tool.invoke({"kind": "feature", "title": "modo oscuro"})

    assert salida == "anotado"
    assert recibido[0]["title"] == "modo oscuro"


def test_la_conversacion_la_pone_el_canal_y_no_el_modelo():
    recibido = []
    tool = _envolver(_tool_async(recibido))

    marca_conv = conversacion_actual.set("42")
    marca_canal = canal_actual.set("whatsapp")
    try:
        tool.invoke({"kind": "bug", "title": "no llega el correo"})
    finally:
        conversacion_actual.reset(marca_conv)
        canal_actual.reset(marca_canal)

    assert recibido[0]["conversation"] == "42"
    assert recibido[0]["channel"] == "whatsapp"


def test_si_el_modelo_manda_conversacion_no_se_la_pisamos():
    """Caso raro pero posible: si vino en la llamada, se respeta."""
    recibido = []
    tool = _envolver(_tool_async(recibido))

    marca = conversacion_actual.set("42")
    try:
        tool.invoke({"kind": "bug", "title": "x", "conversation": "99"})
    finally:
        conversacion_actual.reset(marca)

    assert recibido[0]["conversation"] == "99"


def test_sin_contexto_no_inventa_conversacion():
    recibido = []
    tool = _envolver(_tool_async(recibido))

    tool.invoke({"kind": "feature", "title": "widget"})

    assert recibido[0].get("conversation", "") == ""


def test_sin_mcp_configurado_el_agente_arranca_igual():
    from agente.mcp import cargar_herramientas

    assert cargar_herramientas("") == []
    assert cargar_herramientas("   ") == []


@pytest.mark.parametrize("url", ["http://127.0.0.1:9/mcp"])
def test_un_mcp_caido_no_tumba_el_arranque(url):
    """Un servicio auxiliar caído no puede dejar sin atender WhatsApp."""
    from agente.mcp import cargar_herramientas

    assert cargar_herramientas(url, "token") == []
