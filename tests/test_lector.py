"""El lector de adjuntos y los interruptores del admin. Sin red ni tokens.

    pytest
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agente.ajustes_soporte import DE_FABRICA, AjustesDelSoporte  # noqa: E402
from agente.config import RAIZ  # noqa: E402
from agente.lector import Archivo, LectorDeAdjuntos, NoSePuedeLeer, archivos_del_evento  # noqa: E402


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
