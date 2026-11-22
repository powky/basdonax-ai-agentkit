"""El lector de adjuntos y los interruptores del admin. Sin red ni tokens.

    pytest
"""

from __future__ import annotations

import io
import json
import sys
import threading
import time
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agente.ajustes_soporte import DE_FABRICA, AjustesDelSoporte  # noqa: E402
from agente.config import RAIZ  # noqa: E402
from agente.lector import (  # noqa: E402
    ESPERA_DEL_GASTO,
    Archivo,
    GastoDelLector,
    LectorDeAdjuntos,
    NoSePuedeLeer,
    archivos_del_evento,
    codigo_del_error,
)


class ModeloQueAnota:
    """Un modelo de mentira que guarda lo que le pidieron."""

    def __init__(self, respuesta="un plan de estudios de UNAPEC"):
        self.respuesta = respuesta
        self.pedidos = []

    def invoke(self, mensajes):
        self.pedidos.append(mensajes)
        return AIMessage(content=[{"type": "text", "text": self.respuesta}])


def descarga(datos=b"%PDF-1.7 ...", tipo="application/pdf"):
    llamadas = []

    def bajar(url, tope):
        llamadas.append((url, tope))
        return datos, tipo

    bajar.llamadas = llamadas
    return bajar


INSTRUCCIONES = RAIZ / "prompts/lector-adjuntos.md"


def test_lee_los_adjuntos_del_evento():
    evento = {
        "attachments": [
            {"file_type": "file", "data_url": "https://ws.x/rails/blob/plan%20UNAPEC.pdf",
             "content_type": "application/pdf", "file_size": 2048},
            {"file_type": "audio", "data_url": "https://ws.x/rails/blob/nota.oga",
             "content_type": "audio/ogg; codecs=opus"},
            "basura",
        ]
    }
    pdf, audio = archivos_del_evento(evento)
    assert pdf == Archivo("file", "https://ws.x/rails/blob/plan%20UNAPEC.pdf", "application/pdf", 2048, "plan UNAPEC.pdf")
    assert pdf.como_se_llama() == "un PDF"
    assert audio.mime == "audio/ogg" and audio.como_se_llama() == "una nota de voz"
    assert archivos_del_evento({}) == []


def test_le_pasa_el_archivo_al_modelo_y_devuelve_su_relato():
    modelo = ModeloQueAnota()
    bajar = descarga()
    lector = LectorDeAdjuntos(modelo, bajar, INSTRUCCIONES)

    relato = lector.leer(Archivo("file", "https://ws.x/a.pdf", "application/pdf"))

    assert relato == "un plan de estudios de UNAPEC"
    (pedido,) = modelo.pedidos[0]
    texto, medio = pedido.content
    assert "No copies datos personales" in texto["text"], "las instrucciones salen del archivo"
    assert "un PDF (application/pdf)" in texto["text"]
    assert medio == {"type": "media", "mime_type": "application/pdf", "data": b"%PDF-1.7 ..."}
    assert bajar.llamadas == [("https://ws.x/a.pdf", lector.tope)]


def test_el_tipo_sale_de_la_red_si_el_evento_no_lo_trae():
    modelo = ModeloQueAnota()
    lector = LectorDeAdjuntos(modelo, descarga(b"\xff\xd8", "image/jpeg"), INSTRUCCIONES)
    lector.leer(Archivo("image", "https://ws.x/foto"))
    assert modelo.pedidos[0][0].content[1]["mime_type"] == "image/jpeg"


@pytest.mark.parametrize(
    "archivo, tipo_de_la_red",
    [
        (Archivo("video", "https://ws.x/v.mp4", "video/mp4"), "video/mp4"),
        (Archivo("file", "https://ws.x/hoja.xlsx", ""), "application/vnd.ms-excel"),
        (Archivo("file", "https://ws.x/grande.pdf", "application/pdf", 40 * 1024 * 1024), "application/pdf"),
        (Archivo("file", "", "application/pdf"), "application/pdf"),
    ],
)
def test_lo_que_no_lee_lo_dice(archivo, tipo_de_la_red):
    modelo = ModeloQueAnota()
    lector = LectorDeAdjuntos(modelo, descarga(b"x", tipo_de_la_red), INSTRUCCIONES)
    with pytest.raises(NoSePuedeLeer):
        lector.leer(archivo)
    assert modelo.pedidos == [], "no gasta un pedido en lo que no va a leer"


def test_un_relato_vacio_no_cuenta_como_leido():
    lector = LectorDeAdjuntos(ModeloQueAnota(respuesta="  "), descarga(), INSTRUCCIONES)
    with pytest.raises(NoSePuedeLeer):
        lector.leer(Archivo("file", "https://ws.x/a.pdf", "application/pdf"))


# -- Los interruptores ---------------------------------------------------------


class Respuesta(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def abridor(*respuestas):
    pedidos = []

    def abrir(pedido, timeout):
        pedidos.append(pedido)
        r = respuestas[min(len(pedidos), len(respuestas)) - 1]
        if isinstance(r, Exception):
            raise r
        return Respuesta(json.dumps(r).encode())

    abrir.pedidos = pedidos
    return abrir


def test_lee_los_interruptores_con_la_llave():
    abrir = abridor({"data": {"readAttachments": False, "returnToBot": True, "returnAfter": 3600}})
    ajustes = AjustesDelSoporte("https://api.x/api/v1/", "llave", abrir=abrir)

    a = ajustes.leer()

    assert (a.leer_adjuntos, a.devolver_al_bot, a.devolver_tras) == (False, True, 3600)
    (pedido,) = abrir.pedidos
    assert pedido.full_url == "https://api.x/api/v1/agent/support/config"
    assert pedido.get_header("X-api-key") == "llave"


def test_se_guardan_un_minuto():
    reloj = [0.0]
    abrir = abridor({"data": {"readAttachments": False}}, {"data": {"readAttachments": True}})
    ajustes = AjustesDelSoporte("https://api.x", "llave", abrir=abrir, reloj=lambda: reloj[0])

    assert ajustes.leer().leer_adjuntos is False
    reloj[0] = 30
    assert ajustes.leer().leer_adjuntos is False, "dentro del minuto no vuelve a pedir"
    reloj[0] = 61
    assert ajustes.leer().leer_adjuntos is True
    assert len(abrir.pedidos) == 2


def test_si_el_api_no_contesta_sigue_con_lo_ultimo():
    reloj = [0.0]
    abrir = abridor({"data": {"readAttachments": False}}, OSError("caído"))
    ajustes = AjustesDelSoporte("https://api.x", "llave", abrir=abrir, reloj=lambda: reloj[0])

    assert ajustes.leer().leer_adjuntos is False
    reloj[0] = 120
    assert ajustes.leer().leer_adjuntos is False, "con el API caído vale lo último que supo"


def test_sin_llave_valen_los_de_fabrica_y_no_sale_a_la_red():
    abrir = abridor(OSError("no debería llamar"))
    ajustes = AjustesDelSoporte("https://api.x", "", abrir=abrir)
    assert ajustes.leer() == DE_FABRICA
    assert ajustes.vigentes() == DE_FABRICA
    assert abrir.pedidos == []


# -- El gasto de cada lectura ---------------------------------------------------


class ModeloQueGasta:
    """Un Gemini de mentira que contesta con su consumo, o que falla."""

    model = "gemini-2.5-flash"

    def __init__(self, uso=None, falla: Exception | None = None, nombre="gemini-2.5-flash"):
        self.uso = uso
        self.falla = falla
        self.nombre = nombre

    def invoke(self, mensajes):
        if self.falla is not None:
            raise self.falla
        return AIMessage(
            content=[{"type": "text", "text": "una foto del horario de la UASD"}],
            usage_metadata=self.uso,
            response_metadata={"model_name": self.nombre},
        )


def anotador(*fallas):
    """Un `abrir` que guarda cada pedido y su espera; con fallas, las levanta."""
    pedidos = []

    def abrir(pedido, timeout):
        pedidos.append((pedido, timeout))
        if fallas:
            raise fallas[0]
        return Respuesta(b"")

    abrir.pedidos = pedidos
    return abrir


def en_el_mismo_hilo(tarea):
    tarea()


# Así lo devuelve LangChain para Gemini: la salida YA trae el razonamiento
# sumado, y la entrada trae adentro lo que salió del caché.
USO = {
    "input_tokens": 1800,
    "output_tokens": 420,
    "total_tokens": 2220,
    "input_token_details": {"cache_read": 600},
    "output_token_details": {"reasoning": 300},
}


def error_de_google(codigo: int, estado: str, mensaje: str) -> Exception:
    """El error como llega de verdad: el de Google envuelto en el de LangChain."""
    from google.genai.errors import ClientError, ServerError
    from langchain_google_genai.chat_models import ChatGoogleGenerativeAIError

    clase = ClientError if codigo < 500 else ServerError
    adentro = clase(codigo, {"error": {"code": codigo, "message": mensaje, "status": estado}})
    try:
        try:
            raise adentro
        except Exception as e:
            raise ChatGoogleGenerativeAIError(f"Error calling model 'gemini-2.5-flash' ({estado}): {e}") from e
    except ChatGoogleGenerativeAIError as envuelto:
        return envuelto


def test_cada_lectura_le_cuenta_al_api_lo_que_gasto():
    abrir = anotador()
    gasto = GastoDelLector("https://api.x/api/v1/", "llave", abrir=abrir, lanzar=en_el_mismo_hilo)
    lector = LectorDeAdjuntos(
        ModeloQueGasta(USO, nombre="models/gemini-2.5-flash"), descarga(), INSTRUCCIONES, gasto=gasto
    )

    assert lector.leer(Archivo("file", "https://ws.x/a.pdf", "application/pdf")) == "una foto del horario de la UASD"

    ((pedido, espera),) = abrir.pedidos
    assert pedido.full_url == "https://api.x/api/v1/agent/support/ai/usage"
    assert pedido.get_method() == "POST"
    assert pedido.get_header("X-api-key") == "llave"
    assert pedido.get_header("Content-type") == "application/json"
    assert espera == ESPERA_DEL_GASTO == 3
    assert json.loads(pedido.data) == {
        "purpose": "support_reader",
        "provider": "google",
        "model": "gemini-2.5-flash",
        "inputTokens": 1800,
        "cachedTokens": 600,
        # Sin el razonamiento, que va aparte: el API cobra los dos juntos.
        "outputTokens": 120,
        "thoughtsTokens": 300,
        "ok": True,
        "errorCode": "",
    }


def test_al_api_no_le_llega_nada_del_archivo_ni_de_la_conversacion():
    abrir = anotador()
    gasto = GastoDelLector("https://api.x", "llave", abrir=abrir, lanzar=en_el_mismo_hilo)
    lector = LectorDeAdjuntos(ModeloQueGasta(USO), descarga(b"%PDF datos de Juan"), INSTRUCCIONES, gasto=gasto)

    lector.leer(Archivo("file", "https://ws.x/Juan_Perez_Record.pdf", "application/pdf", 10, "Juan_Perez_Record.pdf"))

    ((pedido, _),) = abrir.pedidos
    crudo = pedido.data.decode("utf-8")
    for dato in ("Juan", "Perez", "ws.x", "UASD", "PDF", "No copies"):
        assert dato not in crudo, dato
    assert set(json.loads(crudo)) == {
        "purpose", "provider", "model", "inputTokens", "cachedTokens",
        "outputTokens", "thoughtsTokens", "ok", "errorCode",
    }


def test_una_lectura_que_google_rechaza_tambien_se_cuenta_y_el_error_sube_igual():
    abrir = anotador()
    gasto = GastoDelLector("https://api.x", "llave", abrir=abrir, lanzar=en_el_mismo_hilo)
    sin_saldo = error_de_google(402, "RESOURCE_EXHAUSTED", "Your prepayment credits are depleted.")
    lector = LectorDeAdjuntos(ModeloQueGasta(falla=sin_saldo), descarga(), INSTRUCCIONES, gasto=gasto)

    with pytest.raises(type(sin_saldo)) as levantado:
        lector.leer(Archivo("file", "https://ws.x/a.pdf", "application/pdf"))

    assert levantado.value is sin_saldo, "el error del proveedor no se esconde"
    ((pedido, _),) = abrir.pedidos
    cuerpo = json.loads(pedido.data)
    assert cuerpo["ok"] is False and cuerpo["errorCode"] == "402"
    assert cuerpo["model"] == "gemini-2.5-flash", "sin respuesta, el nombre sale del modelo"
    assert (cuerpo["inputTokens"], cuerpo["outputTokens"], cuerpo["thoughtsTokens"]) == (0, 0, 0)


@pytest.mark.parametrize(
    "error, codigo",
    [
        (lambda: error_de_google(402, "RESOURCE_EXHAUSTED", "Your prepayment credits are depleted."), "402"),
        (lambda: error_de_google(429, "RESOURCE_EXHAUSTED", "quota"), "429"),
        (lambda: error_de_google(503, "UNAVAILABLE", "high demand"), "503"),
        (lambda: TimeoutError("se cortó"), "timeout"),
        (lambda: type("ReadTimeout", (Exception,), {})("lento"), "timeout"),
        (lambda: ValueError("otra cosa"), "ValueError"),
    ],
)
def test_el_codigo_del_error_es_el_estado_del_proveedor(error, codigo):
    assert codigo_del_error(error()) == codigo


def test_un_api_caido_no_tumba_la_lectura():
    abrir = anotador(OSError("caído"))
    gasto = GastoDelLector("https://api.x", "llave", abrir=abrir, lanzar=en_el_mismo_hilo)
    lector = LectorDeAdjuntos(ModeloQueGasta(USO), descarga(), INSTRUCCIONES, gasto=gasto)

    assert lector.leer(Archivo("file", "https://ws.x/a.pdf", "application/pdf")) == "una foto del horario de la UASD"
    assert len(abrir.pedidos) == 1


def test_un_api_lento_no_demora_la_lectura():
    """El aviso sale en otro hilo: la lectura vuelve sin esperar al API."""
    llamado, suelto = threading.Event(), threading.Event()

    def abrir(pedido, timeout):
        llamado.set()
        suelto.wait(5)
        raise OSError("tardó")

    gasto = GastoDelLector("https://api.x", "llave", abrir=abrir)
    lector = LectorDeAdjuntos(ModeloQueGasta(USO), descarga(), INSTRUCCIONES, gasto=gasto)
    try:
        antes = time.monotonic()
        assert lector.leer(Archivo("file", "https://ws.x/a.pdf", "application/pdf"))
        assert time.monotonic() - antes < 1
        assert llamado.wait(2), "el aviso salió igual"
    finally:
        suelto.set()


def test_sin_llave_ni_api_no_se_cuenta_nada():
    for url, llave in (("https://api.x", ""), ("", "llave")):
        abrir = anotador()
        gasto = GastoDelLector(url, llave, abrir=abrir, lanzar=en_el_mismo_hilo)
        LectorDeAdjuntos(ModeloQueGasta(USO), descarga(), INSTRUCCIONES, gasto=gasto).leer(
            Archivo("file", "https://ws.x/a.pdf", "application/pdf")
        )
        assert abrir.pedidos == []


def test_un_consumo_raro_cuenta_como_cero_y_no_rompe():
    abrir = anotador()
    gasto = GastoDelLector("https://api.x", "llave", abrir=abrir, lanzar=en_el_mismo_hilo)
    gasto.anotar(None, {"input_tokens": "mil", "output_tokens": -3, "input_token_details": None})
    gasto.anotar("gemini-2.5-flash", {"input_tokens": 10, "input_token_details": {"cache_read": 50}})

    raro, de_mas = (json.loads(p.data) for p, _ in abrir.pedidos)
    assert (raro["model"], raro["inputTokens"], raro["outputTokens"]) == ("", 0, 0)
    assert de_mas["cachedTokens"] == 10, "el caché nunca pasa de la entrada"


def test_si_no_puede_lanzar_el_hilo_la_lectura_sigue():
    def no_hay_hilos(tarea):
        raise RuntimeError("can't start new thread")

    gasto = GastoDelLector("https://api.x", "llave", abrir=anotador(), lanzar=no_hay_hilos)
    lector = LectorDeAdjuntos(ModeloQueGasta(USO), descarga(), INSTRUCCIONES, gasto=gasto)
    assert lector.leer(Archivo("file", "https://ws.x/a.pdf", "application/pdf"))
