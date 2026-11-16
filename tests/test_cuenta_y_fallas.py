"""La cuenta de quien escribe (ver_su_cuenta) y las fallas que ya reportaron otros.

    pytest
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agente.ajustes_soporte import FALLAS_VALEN, Ajustes, AjustesDelSoporte, FallaConocida  # noqa: E402
from agente.canales.ficha import leer_ficha  # noqa: E402
from agente.contexto import conversacion_actual  # noqa: E402
from agente.cuenta_soporte import NO_SE_PUDO, SIN_CUENTA, SIN_VERIFICAR, CuentaDelSoporte, redactar  # noqa: E402
from agente.fallas import contexto_de_fallas  # noqa: E402

from test_webhook_adjuntos_y_vuelta import TOKEN, AjustesFijos, Canal, armar, esperar, evento  # noqa: E402


class Respuesta(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def abrir_con(datos, pedidos=None):
    def abrir(pedido, timeout=None):
        if pedidos is not None:
            pedidos.append(pedido)
        return Respuesta(json.dumps({"data": datos}).encode())

    return abrir


DIAGNOSTICO = {
    "lastSeenAt": "2026-11-16T14:00:00Z",
    "appVersion": "2.3.1",
    "platform": "ios",
    "enrollments": [
        {
            "university": "UASD",
            "programCode": "DER",
            "programName": "Licenciatura en Derecho",
            "active": True,
            "progress": 45,
            "index": {"value": 3.42, "creditsPassed": 98, "failedAttempts": 2, "updatedAt": "2026-11-14T13:02:00Z"},
        }
    ],
    "portal": {"lastRecordAt": "2026-11-14T13:02:00Z", "lastScheduleAt": "2026-11-15T02:30:00Z"},
    "honors": {
        "university": "UASD",
        "programCode": "DER",
        "failed": [
            {"code": "MAT101", "name": "Matemática", "term": "2023-2", "grade": "55", "retake": {"term": "2024-1", "grade": "80"}}
        ],
    },
}


# -- el texto que lee el modelo -----------------------------------------------


def test_sin_cuenta_le_dice_como_conseguirla():
    texto = redactar({"linked": False})
    assert texto == SIN_CUENTA
    assert "¿Necesitas ayuda?" in texto and "No le pidas el correo" in texto


def test_con_solo_el_correo_no_ve_nada():
    texto = redactar({"linked": True, "verified": False, "source": "correo"})
    assert texto == SIN_VERIFICAR


def test_la_cuenta_verificada_en_renglones():
    texto = redactar({"linked": True, "verified": True, "source": "app", "diagnosis": DIAGNOSTICO})
    assert "verificada: con el código de la app" in texto
    assert "Carrera activa: UASD · Licenciatura en Derecho (DER). Avance: 45%." in texto
    assert "Índice que reportó su universidad: 3.42, con 98 créditos aprobados y 2 intentos reprobados" in texto
    # Las fechas en hora dominicana: el 15/11 a las 02:30 UTC es el 14/11 allá.
    assert "leyó por última vez su récord el 14/11/2026 y su horario el 14/11/2026." in texto
    assert "MAT101 Matemática — 55 en 2023-2; la aprobó en 2024-1 con 80." in texto
    assert "versión 2.3.1 en iOS" in texto
    assert "None" not in texto and "restricción" not in texto


def test_lo_que_no_se_explica():
    diag = dict(DIAGNOSTICO, blocked=True, appCheck={"platform": "android", "code": "UNRECOGNIZED_VERSION", "lastAt": "2026-11-15T10:00:00Z"})
    texto = redactar({"linked": True, "verified": True, "source": "ian", "diagnosis": diag})
    assert "la ató Ian" in texto
    assert "No le expliques ni le menciones nada de eso" in texto
    assert "no pudo demostrar que es la original (Android, UNRECOGNIZED_VERSION)" in texto


def test_sin_sincronizar_nunca():
    diag = {"enrollments": [], "appVersion": "2.3.1"}
    texto = redactar({"linked": True, "verified": True, "source": "app", "diagnosis": diag})
    assert "No tiene ninguna carrera elegida" in texto
    assert "Nunca conectó su universidad" in texto


def test_pide_la_conversacion_con_su_llave():
    pedidos = []
    cuenta = CuentaDelSoporte("https://api.studiante.app/api/v1/", "llave-de-prueba", abrir=abrir_con({"linked": False}, pedidos))
    assert cuenta.de("42") == {"linked": False}
    (pedido,) = pedidos
    assert pedido.full_url == "https://api.studiante.app/api/v1/agent/support/conversations/42/account"
    assert pedido.get_header("X-api-key") == "llave-de-prueba"


# -- las fallas en los ajustes ------------------------------------------------

CONFIG = {
    "readAttachments": True,
    "returnToBot": True,
    "returnAfter": 86400,
    "warnKnownFailures": True,
    "knownFailures": [
        {
            "university": "UASD",
            "people": 3,
            "lastAt": 1794800000,
            "errors": [{"text": "formulario del kárdex: no apareció tras 4s", "count": 2}],
            "conversations": [51, 52, 53],
        }
    ],
}


def test_los_ajustes_traen_las_fallas():
    ajustes = AjustesDelSoporte("https://api", "llave", abrir=abrir_con(CONFIG)).leer()
    assert ajustes.avisar_fallas
    (falla,) = ajustes.fallas
    assert falla.universidad == "UASD" and falla.personas == 3
    assert falla.conversaciones == ("51", "52", "53")
    assert falla.errores == (("formulario del kárdex: no apareció tras 4s", 2),)


def test_con_el_interruptor_apagado_no_hay_fallas():
    apagado = dict(CONFIG, warnKnownFailures=False)
    ajustes = AjustesDelSoporte("https://api", "llave", abrir=abrir_con(apagado)).leer()
    assert not ajustes.avisar_fallas and ajustes.fallas == ()


def test_sin_noticias_del_api_las_fallas_se_olvidan():
    ahora = [1000.0]
    llamadas = []

    def abrir(pedido, timeout=None):
        llamadas.append(1)
        if len(llamadas) > 1:
            raise OSError("el API no contesta")
        return Respuesta(json.dumps({"data": CONFIG}).encode())

    ajustes = AjustesDelSoporte("https://api", "llave", cada=60, abrir=abrir, reloj=lambda: ahora[0])
    assert ajustes.leer().fallas
    ahora[0] += FALLAS_VALEN + 61
    # El API dejó de contestar: el resto de los ajustes sigue, las fallas no.
    vigentes = ajustes.leer()
    assert vigentes.fallas == () and vigentes.leer_adjuntos


# -- el renglón para el modelo ------------------------------------------------

UASD = FallaConocida("UASD", 3, (("formulario del kárdex: no apareció tras 4s", 2),), ("51", "52", "53"))


def test_a_quien_reporta_lo_mismo_le_llega_la_falla():
    bloque = contexto_de_fallas((UASD,), "53", "Hola 👋 No pude conectar el portal de UASD en Studiante.")
    assert bloque.startswith("[fallas conocidas:")
    # Quien escribe no cuenta: quedan las otras dos.
    assert "- UASD: 2 personas más" in bloque


def test_hacen_falta_dos_personas_mas():
    dos = FallaConocida("UNIBE", 2, (), ("61", "62"))
    assert contexto_de_fallas((dos,), "62", "no me conecta UNIBE") == ""
    assert contexto_de_fallas((dos,), "70", "no me conecta UNIBE") != ""


def test_a_quien_pregunta_otra_cosa_no():
    assert contexto_de_fallas((UASD,), "99", "no encuentro mi pensum de derecho") == ""
    # Pero si su universidad es la que falla, sí: puede ser eso sin decirlo.
    assert contexto_de_fallas((UASD,), "99", "no me sale nada", universidad_del_contacto="UASD · DER") != ""


# -- el webhook ---------------------------------------------------------------


def test_el_webhook_cuenta_las_fallas_una_vez_por_conversacion(monkeypatch):
    from agente.web import webhook as modulo

    monkeypatch.setattr(modulo, "catalogo_caido", lambda: False)
    canal = Canal()
    cliente, agente = armar(canal, fallas=(UASD,))
    with cliente:
        cliente.post(f"/chatwoot/{TOKEN}", json=evento("no me conecta la UASD", id_=1))
        assert esperar(lambda: len(agente.recibido) == 1)
        cliente.post(f"/chatwoot/{TOKEN}", json=evento("sigue sin conectar", id_=2))
        assert esperar(lambda: len(agente.recibido) == 2)
    primero, segundo = agente.recibido
    assert primero.startswith("[fallas conocidas:") and primero.endswith("no me conecta la UASD")
    assert segundo == "sigue sin conectar"


class CuentaFalsa:
    def __init__(self, datos=None, falla=None):
        self.datos = datos
        self.falla = falla
        self.pedidas = []

    def configurada(self):
        return True

    def de(self, conversacion):
        self.pedidas.append(conversacion)
        if self.falla:
            raise self.falla
        return self.datos


def herramienta_de_cuenta(monkeypatch, cuenta):
    """Arma el webhook sin agente de mentira, para quedarse con la herramienta."""
    from agente.web import webhook as modulo

    herramientas = {}

    class AgenteQueGuarda:
        def __init__(self, config, herramientas_extra=None):
            for h in herramientas_extra or []:
                herramientas[h.name] = h

    monkeypatch.setattr(modulo, "Agente", AgenteQueGuarda)
    from test_webhook_adjuntos_y_vuelta import Config, RAIZ

    config = Config(
        proveedor="claude", modelo="m", api_key="k", max_tokens=1024, memoria_mensajes=20,
        prompt_sistema=RAIZ / "prompts/sistema.md", chatwoot_url="https://ws.ejemplo.com",
        chatwoot_token="t", chatwoot_webhook_token=TOKEN, buffer_segundos=0,
    )
    modulo.crear_app(config, canal=Canal(), ajustes=AjustesFijos(), cuenta=cuenta)
    return herramientas["ver_su_cuenta"]


def test_la_herramienta_lee_la_cuenta_de_quien_escribe(monkeypatch):
    cuenta = CuentaFalsa({"linked": True, "verified": True, "source": "app", "diagnosis": DIAGNOSTICO})
    herramienta = herramienta_de_cuenta(monkeypatch, cuenta)
    # El modelo no elige la conversación: no está entre sus argumentos.
    assert set(herramienta.args) == {"para"}
    marca = conversacion_actual.set("42")
    try:
        texto = herramienta.invoke({"para": "su índice"})
    finally:
        conversacion_actual.reset(marca)
    assert cuenta.pedidas == ["42"]
    assert "Índice que reportó su universidad: 3.42" in texto


def test_si_no_se_puede_leer_no_inventa(monkeypatch):
    herramienta = herramienta_de_cuenta(monkeypatch, CuentaFalsa(falla=OSError("timeout")))
    marca = conversacion_actual.set("42")
    try:
        assert herramienta.invoke({"para": "honores"}) == NO_SE_PUDO
    finally:
        conversacion_actual.reset(marca)


# -- la ficha -----------------------------------------------------------------


def test_el_codigo_no_es_el_modelo_del_telefono():
    ficha = leer_ficha("Hola 👋 Escribo desde la app.\n\nEquipo: App v2.3.1 (30) · android 16 · ana@b.com · Ref. K7Q2-9XMD\n\n")
    assert ficha.dispositivo == ""
    assert "K7Q2" not in json.dumps(ficha.atributos())


def test_la_universidad_del_reporte_de_fallo():
    ficha = leer_ficha(
        "Hola 👋 No pude conectar el portal de Nube UTESA en Studiante.\n\nError: x\n\n"
        "Equipo: App v2.3.1 (30) · ios 27.0 · iPhone 17 Pro · ana@b.com · Ref. K7Q2-9XMD\nCarrera: DER"
    )
    assert ficha.motivo == "portal" and ficha.universidad == "Nube UTESA"
    assert ficha.dispositivo == "iPhone 17 Pro" and ficha.carrera == "DER"


def test_ajustes_de_fabrica_sin_fallas():
    assert Ajustes().fallas == () and Ajustes().avisar_fallas
