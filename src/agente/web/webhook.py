"""El servidor que atiende WhatsApp.

Esta es la app que corre en el servidor. **No es la plataforma de pruebas**
(`web/app.py`): son dos cosas distintas y a propósito. La de pruebas es para
tu máquina, tiene la pantalla con los ajustes y no sale de localhost. Esta no
tiene pantalla: es una puerta por donde entra Chatwoot y nada más.

Lo que hace, de punta a punta:

    Chatwoot pega en POST /chatwoot/<token>
      → contestamos 200 al toque              ← esto es obligatorio
      → juntamos la ráfaga de mensajes          (buffer.py)
      → responde el agente                      (agente.py)
      → la respuesta sale por la API de Chatwoot (canales/chatwoot.py)

**Por qué el 200 sale antes de responderle a la persona.** Chatwoot espera
que el webhook conteste rápido; si tardamos lo que tarda el modelo en
pensar, da el pedido por fallado y lo reintenta — y entonces el agente
contesta dos veces lo mismo. Así que primero decimos "recibido" y recién
después pensamos la respuesta, en segundo plano.

**La seguridad es el token en la URL.** Chatwoot no firma sus webhooks (no
hay HMAC como en Meta), así que lo único que separa un mensaje de verdad de
cualquiera que descubra el dominio es que la URL tenga el token. Por eso es
largo y por eso no va en el código.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import time
from collections import defaultdict
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ..agente import Agente
from ..canales.buffer import BufferDeMensajes
from langchain_core.tools import StructuredTool

from ..canales.chatwoot import Chatwoot
from ..contexto import canal_actual, conversacion_actual
from ..config import Config
from ..mcp import catalogo_caido
from .. import traspaso

registro = logging.getLogger("agente.webhook")


# Cuánto se acepta de desfase entre el reloj de Chatwoot y el nuestro. Sin este
# tope, un pedido firmado interceptado hoy sirve para siempre.
TOLERANCIA_FIRMA = 300


def firma_valida(secreto: str, cuerpo: bytes, firma: str, marca: str) -> bool:
    """Comprueba la firma que manda Chatwoot con cada webhook.

    Chatwoot arma `sha256=HMAC_SHA256(secreto, "<timestamp>.<cuerpo>")` y lo
    manda en `X-Chatwoot-Signature`, con el timestamp aparte. Verificarlo es
    mejor que confiar en el token de la URL: aquel prueba que quien llama
    conoce la dirección, este prueba que el CUERPO salió de tu Chatwoot y que
    nadie lo tocó por el camino.
    """
    if not firma or not marca:
        return False

    # El timestamp entra en el HMAC, así que un pedido viejo no se puede
    # reenviar: la firma solo vale para su momento.
    try:
        if abs(time.time() - int(marca)) > TOLERANCIA_FIRMA:
            return False
    except ValueError:
        return False

    esperada = hmac.new(
        secreto.encode(), f"{marca}.".encode() + cuerpo, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={esperada}", firma)


def crear_app(
    config: Config | None = None,
    agente: Agente | None = None,
    canal: Chatwoot | None = None,
) -> FastAPI:
    """Arma el servidor.

    El agente y el canal se pueden pasar armados: es lo que hacen los tests
    para probar todo esto sin salir a internet ni gastar un token.
    """
    config = config or Config.desde_entorno()

    canal = canal or Chatwoot(
        url=config.chatwoot_url,
        token=config.chatwoot_token,
        cuenta_id=config.chatwoot_cuenta_id,
        etiqueta_humano=config.chatwoot_etiqueta_humano,
    )

    def guardar_nombre(nombre: str) -> str:
        """Guarda el nombre de la persona en el contacto de Chatwoot."""
        return canal.guardar_nombre(conversacion_actual.get(), nombre)

    # La única tool que depende del canal: el resto vive en el MCP. La
    # conversación no la pasa el modelo —no la conoce— sino el contextvar que
    # deja puesto `responder` unas líneas más abajo.
    def pedir_una_persona(motivo: str) -> str:
        """La deja anotada; el traspaso lo hace el webhook al terminar."""
        traspaso.pedir(conversacion_actual.get(), motivo)
        return (
            "Listo: la conversación queda para el equipo. Decile a la persona "
            "que alguien la retoma, sin prometer cuándo, y no sigas intentando "
            "resolverlo vos."
        )

    herramienta_persona = StructuredTool.from_function(
        func=pedir_una_persona,
        name="pasar_a_una_persona",
        description=(
            "Deja la conversación para que la siga alguien del equipo. Úsala "
            "cuando el tema no lo podés resolver vos: piden hablar con una "
            "persona, están molestos, reclaman datos incorrectos, piden que "
            "conectemos una universidad o un portal nuevo, o es prensa, una "
            "universidad, algo comercial o legal. El `motivo` es una nota "
            "interna que solo ve el equipo: escribí en una línea qué necesita "
            "y con qué datos, no la conversación entera."
        ),
    )

    herramienta_nombre = StructuredTool.from_function(
        func=guardar_nombre,
        name="guardar_nombre",
        description=(
            "Guarda el nombre de la persona con la que estás hablando, para que "
            "el equipo la vea por su nombre y no por su número. Úsala apenas te "
            "lo diga, una sola vez por conversación."
        ),
    )

    # El agente se arma una sola vez y atiende a todo el mundo. Es lo que
    # queremos: adentro tiene la conexión a Postgres, y armarlo por mensaje
    # sería abrir una conexión nueva cada vez.
    agente = agente or Agente(
        config, herramientas_extra=[herramienta_nombre, herramienta_persona]
    )

    # Un candado por conversación. Dos personas distintas se atienden a la
    # vez sin problema, pero dos mensajes de la MISMA persona no: si se
    # respondieran en paralelo, los dos leerían la memoria en el mismo punto
    # y el segundo pisaría lo que guardó el primero.
    candados: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def responder(conversacion: str, texto: str) -> None:
        """Le pasa la ráfaga al agente y manda la respuesta por Chatwoot."""
        async with candados[conversacion]:
            # El interruptor se mira de nuevo ACÁ, no solo al recibir el
            # mensaje. Entre una cosa y la otra pasó el buffer —hoy
            # BUFFER_SEGUNDOS=60— y ese rato es justo cuando alguien del
            # equipo entra a la bandeja y toma la conversación. Mirarlo solo
            # a la entrada deja al bot soltando una última respuesta arriba
            # de la persona, con la etiqueta ya puesta.
            if await asyncio.to_thread(canal.la_atiende_una_persona, conversacion):
                registro.info("[%s] la tomó una persona: no contesto", conversacion)
                return

            registro.info("[%s] %s", conversacion, texto.replace("\n", " | ")[:200])

            # Por dónde entró: lo usan las tools del MCP para anotar de qué
            # canal salió cada pedido.
            canal_actual.set(canal.canal_de(conversacion))

            # El "escribiendo..." y el agente son código bloqueante (urllib y
            # el modelo). Van a un hilo aparte para no trabar el servidor:
            # mientras este mensaje se piensa, los demás siguen entrando.
            await asyncio.to_thread(canal.escribiendo, conversacion, True)

            try:
                mensajes = await asyncio.to_thread(
                    agente.responder_partido, texto, conversacion
                )
            except Exception as e:
                # El error del proveedor NO se le manda al cliente: un
                # "RateLimitError: quota exceeded" no le dice nada a un
                # estudiante y nos hace ver rotos. La persona recibe una
                # línea humana, y el error de verdad va a los logs y a una
                # nota privada, que es donde sirve.
                aviso = f"{type(e).__name__}: {e}"
                registro.error("[%s] %s", conversacion, aviso)
                mensajes = [
                    "Se me complicó procesarlo ahora mismo. Ya alguien del "
                    "equipo lo retoma 🙏🏻"
                ]
                traspaso.pedir(
                    conversacion,
                    f"El agente no pudo generar la respuesta: {aviso}",
                )

            # Segunda mirada, y no es de más: pensar la respuesta puede
            # llevarse veinte segundos cuando el modelo consulta el catálogo.
            # Lo que no se puede permitir no es pensarla, es mandarla encima
            # de quien ya está atendiendo.
            if await asyncio.to_thread(canal.la_atiende_una_persona, conversacion):
                registro.info(
                    "[%s] la tomaron mientras pensaba: no mando la respuesta",
                    conversacion,
                )
                await asyncio.to_thread(canal.escribiendo, conversacion, False)
                return

            try:
                await asyncio.to_thread(canal.enviar, conversacion, mensajes)
            except Exception as e:
                # Acá ya no hay a quién avisarle: el canal de salida es
                # justamente el que falló. Queda en los logs.
                registro.error("[%s] no se pudo enviar: %s", conversacion, e)
            finally:
                await asyncio.to_thread(canal.escribiendo, conversacion, False)

            registro.info("[%s] -> %s mensaje(s)", conversacion, len(mensajes))

            # Si contestó a ciegas, no se queda como si nada: queda una nota
            # interna y la conversación pasa a una persona. Va DESPUÉS de
            # enviar porque el traspaso pone la etiqueta que apaga al bot, y
            # ponerla antes dejaría a la persona esperando una respuesta que
            # ya estaba escrita.
            motivo = _por_que_pasarla(conversacion)
            if motivo:
                registro.info("[%s] la paso a una persona: %s", conversacion, motivo)
                await asyncio.to_thread(canal.pasar_a_una_persona, conversacion, motivo)

    def _por_que_pasarla(conversacion: str) -> str:
        """Si esta respuesta salió sin poder consultar el catálogo, con qué
        texto se avisa en la bandeja.

        Puede venir de tres lados: una tool que falló, el modelo que pidió
        el traspaso porque esto no lo resuelve él, o el MCP caído desde que
        arrancó. En los tres el riesgo es el mismo y es el peor que tenemos:
        contestar sobre el catálogo sin haberlo mirado, o dar por cerrado
        algo que necesita una persona.
        """
        pedido = traspaso.tomar(conversacion)
        if pedido:
            return pedido

        if catalogo_caido():
            return (
                "El agente está sin acceso al catálogo de universidades y "
                "pensums, así que no puede confirmar qué hay en la app. Lo dejo "
                "para que lo siga una persona."
            )

        return ""

    def _clasificar(entrante) -> None:
        """Guarda en Chatwoot lo que la app haya mandado en el mensaje."""
        try:
            ficha = canal.clasificar(entrante)
            if not ficha.vacia():
                registro.info(
                    "[%s] ficha: %s", entrante.conversacion,
                    ", ".join(f"{k}={v}" for k, v in ficha.atributos().items()) or ficha.motivo,
                )
        except Exception as e:
            # Clasificar es un extra: que falle no puede dejar sin respuesta a
            # la persona, que es lo que sigue en el flujo principal.
            registro.error("[%s] no se pudo clasificar: %s", entrante.conversacion, e)

    buffer = BufferDeMensajes(config.buffer_segundos, responder)

    @asynccontextmanager
    async def ciclo_de_vida(app: FastAPI):
        # Que los datos del equipo se VEAN en la bandeja. Chatwoot solo pinta
        # los atributos que están definidos, y sin esto el panel queda vacío
        # aunque los datos se hayan guardado bien.
        if hasattr(canal, "asegurar_atributos"):
            await asyncio.to_thread(canal.asegurar_atributos)
        registro.info(
            "Agente escuchando - %s / %s - memoria %s - buffer %ss - canales %s - firma %s",
            config.proveedor,
            config.modelo,
            "Postgres" if config.modo == "produccion" else "SQLite",
            config.buffer_segundos,
            ", ".join(config.canales) if config.canales else "todos",
            "sí" if config.chatwoot_webhook_secret else "NO (sin CHATWOOT_WEBHOOK_SECRET)",
        )
        yield
        # Al apagar, soltamos lo que estaba esperando. Sin esto, un deploy
        # justo en esos segundos se come la ráfaga de alguien.
        await buffer.vaciar()

    app = FastAPI(title="Agente - webhook de Chatwoot", lifespan=ciclo_de_vida)

    # -- Las rutas -------------------------------------------------------------

    @app.get("/salud")
    async def salud() -> dict:
        """Para que el servidor sepa que la app está viva.

        Coolify le pega a esto cada tanto. Si no contesta, reinicia el
        contenedor.
        """
        return {
            "estado": "ok",
            "proveedor": config.proveedor,
            "modelo": config.modelo,
            "memoria": "postgres" if config.modo == "produccion" else "sqlite",
        }

    @app.post("/chatwoot/{token}")
    async def entrante(token: str, pedido: Request) -> JSONResponse:
        """Por acá entra todo lo que manda Chatwoot."""
        if not config.chatwoot_webhook_token or token != config.chatwoot_webhook_token:
            # Sin detalles en la respuesta: al que probó la URL no le decimos
            # si el token existe, si es corto o si le erró por una letra.
            registro.warning("Llamada con token equivocado")
            return JSONResponse({"error": "no autorizado"}, status_code=401)

        # El cuerpo crudo, no el parseado: la firma se calcula sobre los bytes
        # exactos que mandó Chatwoot, y volver a serializar el JSON cambia
        # espacios y orden.
        crudo = await pedido.body()

        if config.chatwoot_webhook_secret:
            if not firma_valida(
                config.chatwoot_webhook_secret,
                crudo,
                pedido.headers.get("x-chatwoot-signature", ""),
                pedido.headers.get("x-chatwoot-timestamp", ""),
            ):
                registro.warning("Pedido con firma inválida")
                return JSONResponse({"error": "no autorizado"}, status_code=401)

        try:
            evento = json.loads(crudo)
        except Exception:
            return JSONResponse({"error": "esperaba JSON"}, status_code=400)

        entrante = canal.traducir(evento)

        # La ficha se guarda ANTES de decidir si el agente contesta, y a
        # propósito: si una persona tomó la conversación, los datos del equipo
        # le sirven igual —o más— para diagnosticar. Va a un hilo porque son
        # dos o tres llamadas a la API de Chatwoot y el webhook tiene que
        # contestar ya.
        if entrante is not None:
            asyncio.create_task(asyncio.to_thread(_clasificar, entrante))

        if entrante is None or not canal.deberia_responder(entrante):
            # No es un error: es la mayoría de lo que llega. Cada respuesta
            # que manda el propio agente vuelve como un evento más.
            return JSONResponse({"estado": "ignorado"})

        # En qué canales contesta. El webhook de Chatwoot es de cuenta, no de
        # bandeja: llega TODO, así que el filtro va acá. La ficha se guarda
        # igual unas líneas más arriba, porque a quien atienda a mano esos
        # datos le sirven venga de donde venga.
        if config.canales:
            canal_entrante = canal.canal_de(entrante.conversacion)
            if canal_entrante and canal_entrante not in config.canales:
                registro.info(
                    "[%s] de %s: fuera de los canales que atiende el agente",
                    entrante.conversacion,
                    canal_entrante,
                )
                return JSONResponse({"estado": "ignorado"})

        # Un archivo lo pasa a una persona, siempre y sin preguntarle al
        # modelo. El agente no sabe abrirlos: no puede leer el PDF de un plan
        # de estudios ni la captura de un error. Dejarlo a su criterio es
        # dejarlo al azar, y el caso que nos importa —alguien mandando el
        # pensum que no encontró— es justo el que no se puede perder.
        #
        # Va acá y no adentro de la respuesta porque el traspaso se consume
        # después de enviar: el agente igual acusa recibo, y recién ahí la
        # conversación cambia de manos.
        if entrante.adjuntos:
            traspaso.pedir(
                entrante.conversacion,
                "Mandó archivos que el agente no puede leer ("
                + ", ".join(entrante.adjuntos)
                + "). Hay que abrirlos a mano.",
            )

        # Se suma a la ráfaga y contestamos ya. Lo que sigue pasa solo.
        await buffer.agregar(entrante.conversacion, entrante.texto)

        return JSONResponse({"estado": "recibido"})

    return app
