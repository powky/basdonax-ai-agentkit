"""El webhook con los dos interruptores del admin: leer adjuntos y volver al bot.

Lo que se prueba es el recorrido entero: llega el evento, se lee el archivo
(o no), el agente recibe el texto que corresponde, y la conversación queda con
quien tiene que quedar.

    pytest
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agente.ajustes_soporte import Ajustes  # noqa: E402
from agente.canales.base import MensajeEntrante  # noqa: E402
from agente.canales.chatwoot import _adjuntos_de, aviso_de_adjuntos  # noqa: E402
from agente.config import RAIZ, Config  # noqa: E402
from agente.lector import NoSePuedeLeer  # noqa: E402
from agente.web.webhook import NOTA_DE_LA_VUELTA, crear_app  # noqa: E402

TOKEN = "token-de-la-url"


class AgenteQueAnota:
    def __init__(self):
        self.recibido = []

    def responder_partido(self, texto, conversacion):
        self.recibido.append(texto)
        return ["respuesta"]


class Canal:
    """Un Chatwoot de mentira con la etiqueta, el historial y la vuelta."""

    def __init__(self, tomada=False, historial=None):
        self.tomada = tomada  # la etiqueta del traspaso
        self._historial = historial or []
        self.enviados = []
        self.traspasos = []
        self.devueltas = []
        self.atendidos = set()

    def traducir(self, evento):
        if evento.get("event") != "message_created":
            return None
        texto = evento.get("content", "")
        adjuntos = _adjuntos_de(evento)
        if adjuntos:
            aviso = aviso_de_adjuntos(evento)
            texto = f"{texto}\n{aviso}" if texto else aviso
        return MensajeEntrante(
            texto=texto,
            conversacion=str(evento["conversation"]["id"]),
            identificador=str(evento.get("id", "")),
            adjuntos=adjuntos,
            datos=evento,
        )

    def deberia_responder(self, mensaje):
        return not self.tomada and mensaje.identificador not in self.atendidos

    def calla_por_la_etiqueta(self, mensaje):
        return self.tomada and mensaje.identificador not in self.atendidos

    def marcar_atendido(self, mensaje):
        self.atendidos.add(mensaje.identificador)

    def historial(self, conversacion):
        return self._historial

    def devolver_al_bot(self, conversacion, nota):
        self.devueltas.append((conversacion, nota))
        self.tomada = False
        return True

    def canal_de(self, conversacion):
        return "whatsapp"

    def clasificar(self, mensaje):
        from agente.canales.ficha import Ficha

        return Ficha()

    def enviar(self, conversacion, mensajes):
        self.enviados.append((conversacion, mensajes))

    def escribiendo(self, conversacion, encendido=True):
        pass

    def guardar_nombre(self, conversacion, nombre):
        return "ok"

    def la_atiende_una_persona(self, conversacion):
        return self.tomada

    def pasar_a_una_persona(self, conversacion, motivo):
        self.traspasos.append((conversacion, motivo))


class LectorFalso:
    def __init__(self, relato="el plan de Mercadotecnia de UNAPEC, 2019, con créditos y prerrequisitos", falla=None):
        self.relato = relato
        self.falla = falla
        self.leidos = []

    def leer(self, archivo):
        self.leidos.append(archivo)
        if self.falla:
            raise self.falla
        return self.relato


class AjustesFijos:
    def __init__(self, **cambios):
        self.ajustes = Ajustes(**cambios)

    def vigentes(self):
        return self.ajustes

    def leer(self):
        return self.ajustes


def armar(canal, lector=None, **ajustes):
    config = Config(
        proveedor="claude",
        modelo="modelo-de-prueba",
        api_key="no-hace-falta",
        max_tokens=1024,
        memoria_mensajes=20,
        prompt_sistema=RAIZ / "prompts/sistema.md",
        chatwoot_url="https://ws.ejemplo.com",
        chatwoot_token="token",
        chatwoot_webhook_token=TOKEN,
        buffer_segundos=0,
    )
    agente = AgenteQueAnota()
    app = crear_app(config, agente=agente, canal=canal, lector=lector, ajustes=AjustesFijos(**ajustes))
    return TestClient(app), agente


def evento(texto="", id_=7, adjuntos=None):
    return {
        "event": "message_created",
        "id": id_,
        "content": texto,
        "message_type": "incoming",
        "conversation": {"id": 42},
        "attachments": adjuntos or [],
    }


PDF = {"file_type": "file", "data_url": "https://ws.ejemplo.com/rails/blob/pensum.pdf", "content_type": "application/pdf"}


def esperar(condicion, segundos=3.0):
    """La vuelta corre en segundo plano: el webhook ya contestó."""
    hasta = time.monotonic() + segundos
    while time.monotonic() < hasta:
        if condicion():
            return True
        time.sleep(0.02)
    return False


def test_con_el_lector_el_agente_ve_lo_que_trae_el_archivo(monkeypatch):
    from agente.web import webhook as modulo

    monkeypatch.setattr(modulo, "catalogo_caido", lambda: False)
    canal, lector = Canal(), LectorFalso()
    cliente, agente = armar(canal, lector)

    with cliente:
        cliente.post(f"/chatwoot/{TOKEN}", json=evento("este es mi pensum", adjuntos=[PDF]))

    assert len(lector.leidos) == 1
    (texto,) = agente.recibido
    assert texto.startswith("este es mi pensum\n[la persona mandó un PDF. Lo que muestra: el plan de Mercadotecnia")
    assert "[adjunto recibido" not in texto
    assert canal.traspasos == [], "lo que el bot lee ya no pasa solo a una persona"


def test_con_el_interruptor_apagado_el_archivo_pasa_a_una_persona(monkeypatch):
    from agente.web import webhook as modulo

    monkeypatch.setattr(modulo, "catalogo_caido", lambda: False)
    canal, lector = Canal(), LectorFalso()
    cliente, agente = armar(canal, lector, leer_adjuntos=False)

    with cliente:
        cliente.post(f"/chatwoot/{TOKEN}", json=evento(adjuntos=[PDF]))

    assert lector.leidos == []
    assert "[adjunto recibido: un PDF]" in agente.recibido[0]
    assert len(canal.traspasos) == 1 and canal.traspasos[0][1].startswith("Mandó archivos")


def test_lo_que_no_se_pudo_leer_pasa_a_una_persona_con_el_motivo(monkeypatch):
    from agente.web import webhook as modulo

    monkeypatch.setattr(modulo, "catalogo_caido", lambda: False)
    canal = Canal()
    cliente, agente = armar(canal, LectorFalso(falla=NoSePuedeLeer("los vídeos no se leen")))

    with cliente:
        cliente.post(f"/chatwoot/{TOKEN}", json=evento(adjuntos=[{"file_type": "video", "data_url": "https://ws.ejemplo.com/v.mp4"}]))

    assert "[adjunto recibido: un vídeo, que no se pudo abrir]" in agente.recibido[0]
    (traspaso,) = canal.traspasos
    assert traspaso[1].startswith("Mandó archivos que el agente no pudo leer") and "vídeos" in traspaso[1]


def test_si_el_lector_falla_el_error_va_a_la_nota_y_no_a_la_persona(monkeypatch):
    from agente.web import webhook as modulo

    monkeypatch.setattr(modulo, "catalogo_caido", lambda: False)
    canal = Canal()
    cliente, agente = armar(canal, LectorFalso(falla=RuntimeError("quota exceeded")))

    with cliente:
        cliente.post(f"/chatwoot/{TOKEN}", json=evento(adjuntos=[PDF]))

    assert "quota" not in agente.recibido[0]
    assert "RuntimeError: quota exceeded" in canal.traspasos[0][1]


def historial_con_ian(hace_horas):
    ahora = time.time()
    respuesta = ahora - hace_horas * 3600
    return [
        {"id": 1, "message_type": 0, "created_at": respuesta - 100, "content": "no me sale mi índice", "private": False},
        {"id": 2, "message_type": 2, "created_at": respuesta - 50, "content": "Ian Fernández agregó humano", "private": False},
        {"id": 3, "message_type": 1, "created_at": respuesta, "content": "Ya lo corregí, actualiza la app.", "private": False},
    ]


def test_si_escribe_un_dia_despues_de_ian_lo_retoma_el_bot():
    canal = Canal(tomada=True, historial=historial_con_ian(30))
    cliente, agente = armar(canal)

    with cliente:
        r = cliente.post(f"/chatwoot/{TOKEN}", json=evento("ahora tengo otra pregunta", id_=9))
        assert r.json()["estado"] == "revisando"
        assert esperar(lambda: canal.enviados), "el bot contesta"

    assert canal.devueltas == [("42", NOTA_DE_LA_VUELTA)]
    (texto,) = agente.recibido
    assert texto.startswith("[contexto:") and "Ian: Ya lo corregí" in texto
    assert texto.endswith("ahora tengo otra pregunta")


def test_si_ian_contesto_hace_un_rato_sigue_siendo_suya():
    canal = Canal(tomada=True, historial=historial_con_ian(2))
    cliente, agente = armar(canal)

    with cliente:
        cliente.post(f"/chatwoot/{TOKEN}", json=evento("gracias, ya probé", id_=9))
        assert not esperar(lambda: canal.enviados or canal.devueltas, 0.4)

    assert agente.recibido == []


def test_si_ian_nunca_contesto_espera_por_el():
    canal = Canal(tomada=True, historial=historial_con_ian(30)[:2])
    cliente, agente = armar(canal)

    with cliente:
        cliente.post(f"/chatwoot/{TOKEN}", json=evento("hola? sigo esperando", id_=9))
        assert not esperar(lambda: canal.enviados or canal.devueltas, 0.4)


def test_con_el_interruptor_apagado_no_vuelve_al_bot():
    canal = Canal(tomada=True, historial=historial_con_ian(30))
    cliente, agente = armar(canal, devolver_al_bot=False)

    with cliente:
        cliente.post(f"/chatwoot/{TOKEN}", json=evento("otra pregunta", id_=9))
        assert not esperar(lambda: canal.enviados or canal.devueltas, 0.4)


def test_el_reintento_de_chatwoot_no_la_retoma_dos_veces():
    canal = Canal(tomada=True, historial=historial_con_ian(30))
    cliente, agente = armar(canal)

    with cliente:
        cliente.post(f"/chatwoot/{TOKEN}", json=evento("otra pregunta", id_=9))
        cliente.post(f"/chatwoot/{TOKEN}", json=evento("otra pregunta", id_=9))
        assert esperar(lambda: canal.enviados)
        time.sleep(0.2)

    assert len(canal.devueltas) == 1 and len(agente.recibido) == 1


def test_con_gemini_el_lector_le_cuenta_su_gasto_al_api(monkeypatch):
    """El lector que arma el webhook lleva el aviso de gasto con la llave del bot."""
    import agente.modelos as modelos
    import agente.web.webhook as modulo
    from agente.lector import GastoDelLector

    armados = []

    class LectorQueAnota:
        def __init__(self, modelo, descargar, instrucciones, gasto=None):
            armados.append(gasto)

    monkeypatch.setattr(modulo, "LectorDeAdjuntos", LectorQueAnota)
    monkeypatch.setattr(modelos, "crear_modelo", lambda *a, **k: object())
    config = Config(
        proveedor="gemini",
        modelo="gemini-2.5-pro",
        api_key="no-hace-falta",
        max_tokens=1024,
        memoria_mensajes=20,
        prompt_sistema=RAIZ / "prompts/sistema.md",
        chatwoot_url="https://ws.ejemplo.com",
        chatwoot_token="token",
        chatwoot_webhook_token=TOKEN,
        buffer_segundos=0,
        studiante_api_url="https://api.ejemplo.com/api/v1",
        studiante_soporte_llave="llave-del-bot",
    )

    class CanalQueDescarga(Canal):
        def descargar(self, url, tope):
            raise AssertionError("no debería bajar nada")

    modulo.crear_app(config, agente=AgenteQueAnota(), canal=CanalQueDescarga(), ajustes=AjustesFijos())

    (gasto,) = armados
    assert isinstance(gasto, GastoDelLector) and gasto.configurado()
    assert gasto.url == "https://api.ejemplo.com/api/v1/agent/support/ai/usage"
    assert gasto.llave == "llave-del-bot"


def test_con_deepseek_el_lector_usa_la_clave_de_google(monkeypatch):
    """El bot conversa con DeepSeek, pero los archivos los sigue leyendo Gemini."""
    import agente.modelos as modelos
    import agente.web.webhook as modulo

    armados = []
    claves = []

    class LectorQueAnota:
        def __init__(self, modelo, descargar, instrucciones, gasto=None):
            armados.append(modelo)

    def crear(proveedor, clave, modelo, tope):
        claves.append((proveedor, clave))
        return object()

    monkeypatch.setattr(modulo, "LectorDeAdjuntos", LectorQueAnota)
    monkeypatch.setattr(modelos, "crear_modelo", crear)
    monkeypatch.setenv("GOOGLE_API_KEY", "clave-de-google")
    config = Config(
        proveedor="deepseek",
        modelo="deepseek-flash",
        api_key="llave-del-bot",
        max_tokens=1024,
        memoria_mensajes=20,
        prompt_sistema=RAIZ / "prompts/sistema.md",
        chatwoot_url="https://ws.ejemplo.com",
        chatwoot_token="token",
        chatwoot_webhook_token=TOKEN,
        buffer_segundos=0,
        studiante_api_url="https://api.ejemplo.com/api/v1",
        studiante_soporte_llave="llave-del-bot",
    )

    class CanalQueDescarga(Canal):
        def descargar(self, url, tope):
            raise AssertionError("no debería bajar nada")

    modulo.crear_app(config, agente=AgenteQueAnota(), canal=CanalQueDescarga(), ajustes=AjustesFijos())

    assert len(armados) == 1
    assert claves == [("gemini", "clave-de-google")]


def test_con_deepseek_y_sin_clave_de_google_no_hay_lector(monkeypatch):
    """Sin la clave de Google, los archivos pasan a una persona, como antes."""
    import agente.web.webhook as modulo

    armados = []

    class LectorQueAnota:
        def __init__(self, *a, **k):
            armados.append(1)

    monkeypatch.setattr(modulo, "LectorDeAdjuntos", LectorQueAnota)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    config = Config(
        proveedor="deepseek",
        modelo="deepseek-flash",
        api_key="llave-del-bot",
        max_tokens=1024,
        memoria_mensajes=20,
        prompt_sistema=RAIZ / "prompts/sistema.md",
        chatwoot_url="https://ws.ejemplo.com",
        chatwoot_token="token",
        chatwoot_webhook_token=TOKEN,
        buffer_segundos=0,
        studiante_api_url="https://api.ejemplo.com/api/v1",
        studiante_soporte_llave="llave-del-bot",
    )

    class CanalQueDescarga(Canal):
        def descargar(self, url, tope):
            raise AssertionError("no debería bajar nada")

    modulo.crear_app(config, agente=AgenteQueAnota(), canal=CanalQueDescarga(), ajustes=AjustesFijos())

    assert armados == []
