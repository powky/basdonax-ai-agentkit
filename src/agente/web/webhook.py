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
import re
import time
from collections import defaultdict
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ..agente import Agente
from ..ajustes_soporte import AjustesDelSoporte
from ..canales.buffer import BufferDeMensajes
from langchain_core.tools import StructuredTool

from ..canales.chatwoot import Chatwoot
from ..contexto import canal_actual, conversacion_actual, personales_actuales
from ..config import Config
from ..cuenta_soporte import NO_SE_PUDO, SIN_CUENTA, CuentaDelSoporte, redactar
from ..fallas import contexto_de_fallas
from ..lector import GastoDelLector, LectorDeAdjuntos, NoSePuedeLeer, archivos_del_evento
from ..mcp import catalogo_caido
from ..privacidad import DatosPersonales
from ..vuelta import contexto_de_la_vuelta, ultima_respuesta_de_ian
from .. import traspaso

registro = logging.getLogger("agente.webhook")

# La ruta del webhook con su token, tal como la escribe uvicorn. Se tapa el
# segmento entero, sea o no el token bueno: un intento con uno casi igual
# tampoco tiene por qué quedar escrito.
_RUTA_CON_TOKEN = re.compile(r"^(/chatwoot/)[^/?#]+")


class TaparToken(logging.Filter):
    """Tapa el token del webhook en el log de acceso de uvicorn.

    El token va en la URL porque Chatwoot no firma sus webhooks: es la única
    llave de la puerta. Y uvicorn escribe la ruta entera en cada línea de
    acceso (`"POST /chatwoot/<el token> HTTP/1.1" 200`), así que sin esto el
    secreto queda a la vista de cualquiera que lea los logs del panel.

    uvicorn arma esa línea con los `args` del registro (cliente, método, ruta,
    versión, estado), no con el mensaje ya armado: por eso la ruta se cambia
    adentro de `args`.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args
        if isinstance(args, tuple) and len(args) >= 3 and isinstance(args[2], str):
            ruta = _RUTA_CON_TOKEN.sub(r"\1<token>", args[2])
            if ruta != args[2]:
                record.args = (*args[:2], ruta, *args[3:])
        # Tapa, no descarta: la línea sigue sirviendo para ver que el mensaje
        # llegó y con qué estado.
        return True


def tapar_token_en_logs() -> None:
    """Le pone TaparToken al log de acceso de uvicorn, una sola vez.

    Va después de crear la `uvicorn.Config`, que es la que arma los loggers de
    uvicorn.
    """
    acceso = logging.getLogger("uvicorn.access")
    if not any(isinstance(f, TaparToken) for f in acceso.filters):
        acceso.addFilter(TaparToken())


# La nota que queda en la bandeja cuando una conversación vuelve al bot.
NOTA_DE_LA_VUELTA = (
    "Volvió a escribir más de 24 horas después de tu última respuesta: la "
    "retoma el bot. Si no la resuelve, te la vuelve a pasar."
)

# Cuánto dura "la retomó recién": los demás mensajes de la misma ráfaga ya no
# vuelven a pedir el historial ni a dejar otra nota.
RETOMADA_RECIEN = 600

# Cada cuánto, como mucho, se le vuelven a contar las fallas conocidas a la
# misma conversación: el agente ya las tiene en su memoria.
FALLAS_CADA = 30 * 60

# De cuántas conversaciones se recuerda quién escribe (ver privacidad.py). Es
# lo que se tapa antes de mandarle nada al modelo; pasado el tope se olvida la
# más vieja, y su próximo mensaje lo vuelve a traer en el contacto.
TOPE_DE_PERSONALES = 5000

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
    lector: LectorDeAdjuntos | None = None,
    ajustes: AjustesDelSoporte | None = None,
    cuenta: CuentaDelSoporte | None = None,
) -> FastAPI:
    """Arma el servidor.

    El agente, el canal, el lector de adjuntos y los ajustes se pueden pasar
    armados: es lo que hacen los tests para probar todo esto sin salir a
    internet ni gastar un token.
    """
    config = config or Config.desde_entorno()

    canal = canal or Chatwoot(
        url=config.chatwoot_url,
        token=config.chatwoot_token,
        cuenta_id=config.chatwoot_cuenta_id,
        etiqueta_humano=config.chatwoot_etiqueta_humano,
    )

    # Los interruptores del admin (leer adjuntos, volver al bot a las 24 h).
    ajustes = ajustes or AjustesDelSoporte(
        config.studiante_api_url, config.studiante_soporte_llave
    )

    # La cuenta de Studiante de quien escribe, si su WhatsApp quedó atado a
    # ella con el código de la app (ver cuenta_soporte.py).
    cuenta = cuenta or CuentaDelSoporte(config.studiante_api_url, config.studiante_soporte_llave)

    # El lector de adjuntos solo existe con Gemini, que lee fotos, PDF y
    # audio. Con otro proveedor los archivos siguen pasando a una persona.
    if lector is None and config.proveedor == "gemini" and hasattr(canal, "descargar"):
        from ..modelos import crear_modelo

        lector = LectorDeAdjuntos(
            crear_modelo("gemini", config.api_key, config.modelo_lector, 2048),
            canal.descargar,
            config.prompt_lector,
            # Cada lectura va con la clave del bot y no pasa por el API: se
            # le cuenta aparte, para que el panel de costos la vea.
            gasto=GastoDelLector(config.studiante_api_url, config.studiante_soporte_llave),
        )

    def guardar_nombre(nombre: str) -> str:
        """Guarda el nombre de la persona en el contacto de Chatwoot."""
        # Desde ya es un dato que se tapa: el contacto con el nombre nuevo
        # llega recién en el próximo evento de Chatwoot.
        personales = personales_actuales.get()
        if personales is not None:
            personales.sumar("NOMBRE", nombre)
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

    # La conversación tampoco la pasa el modelo: sale del contextvar, así que
    # nadie puede pedirle la cuenta de otra persona. `para` solo queda en el
    # log (Gemini rechaza una herramienta sin ningún argumento).
    def ver_su_cuenta(para: str = "") -> str:
        """Lee la cuenta de quien escribe; el texto lo arma cuenta_soporte.py."""
        conversacion = conversacion_actual.get()
        if not conversacion or not cuenta.configurada():
            return SIN_CUENTA
        try:
            datos = cuenta.de(conversacion)
        except Exception as e:
            # Tragado a propósito: el modelo recibe un texto que le dice qué
            # hacer (no inventar y pasarla), y el error queda en el log.
            registro.error("[%s] no pude leer su cuenta: %s", conversacion, e)
            return NO_SE_PUDO
        # Lo personal que traiga la cuenta se tapa desde la próxima llamada al
        # modelo, que es la que lee este resultado.
        personales = personales_actuales.get()
        if personales is not None:
            personales.sumar_cuenta(datos)
        registro.info(
            "[%s] miró su cuenta (%s)%s", conversacion,
            "verificada" if datos.get("verified") else ("sin verificar" if datos.get("linked") else "sin cuenta"),
            f": {para[:80]}" if para else "",
        )
        return redactar(datos)

    herramienta_cuenta = StructuredTool.from_function(
        func=ver_su_cuenta,
        name="ver_su_cuenta",
        description=(
            "Lee la cuenta de Studiante de la persona con la que estás hablando: "
            "sus carreras, el índice que reportó su universidad, cuándo se leyó "
            "su récord, qué materias reprobadas le impiden los honores y si la app "
            "de su teléfono quedó sin verificar. Úsala cuando pregunte por su "
            "índice, sus notas, sus honores o por qué algo de su cuenta no carga o "
            "no cuadra. Es siempre la cuenta de quien te escribe, y solo si su "
            "WhatsApp quedó atado a ella; si no, te dice cómo conseguirlo. En "
            "`para` pon en pocas palabras qué quieres averiguar."
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
        config, herramientas_extra=[herramienta_nombre, herramienta_persona, herramienta_cuenta]
    )

    # Un candado por conversación. Dos personas distintas se atienden a la
    # vez sin problema, pero dos mensajes de la MISMA persona no: si se
    # respondieran en paralelo, los dos leerían la memoria en el mismo punto
    # y el segundo pisaría lo que guardó el primero.
    candados: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    # Quién escribe en cada conversación: lo que el modelo no puede ver.
    personales: dict[str, DatosPersonales] = {}

    def _personales_de(conversacion: str) -> DatosPersonales:
        datos = personales.get(conversacion)
        if datos is None:
            if len(personales) >= TOPE_DE_PERSONALES:
                personales.pop(next(iter(personales)))
            datos = personales[conversacion] = DatosPersonales()
        return datos

    def _anotar_personales(entrante) -> None:
        """Lo que el evento dice de quién escribe: su contacto, su número y la
        ficha de la app. Se junta acá, antes de la ráfaga, porque después de
        ella el evento ya no está."""
        datos = _personales_de(entrante.conversacion)
        evento = entrante.datos or {}
        conversacion = evento.get("conversation") or {}
        datos.sumar_contacto((conversacion.get("meta") or {}).get("sender") or {})
        remitente = evento.get("sender") or {}
        # En un mensaje que entra, el remitente es el contacto. Si dijera otra
        # cosa (alguien del equipo), su nombre no es el de la persona.
        if (remitente.get("type") or "contact") == "contact":
            datos.sumar_contacto(remitente)
        datos.sumar_por_forma(str((conversacion.get("contact_inbox") or {}).get("source_id") or ""))
        datos.sumar_mensaje(entrante.texto or "")

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
            # Y quién escribe: el modelo lo tapa antes de mandar nada. Va
            # antes del to_thread, que es el que copia el contexto.
            personales_actuales.set(_personales_de(conversacion))

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

    # Las conversaciones que el bot retomó hace un rato, y cuándo.
    retomadas: dict[str, float] = {}

    # A qué conversaciones se les contaron las fallas conocidas, y cuándo.
    fallas_contadas: dict[str, float] = {}

    def _fallas_para(entrante) -> str:
        """Las fallas que otras personas ya reportaron, si este mensaje puede
        ser de eso (ver fallas.py). Una vez cada FALLAS_CADA por conversación."""
        fallas = ajustes.vigentes().fallas
        conversacion = entrante.conversacion
        if not fallas or time.monotonic() - fallas_contadas.get(conversacion, float("-inf")) < FALLAS_CADA:
            return ""
        contacto = ((entrante.datos.get("conversation") or {}).get("meta") or {}).get("sender") or {}
        universidad = str((contacto.get("custom_attributes") or {}).get("universidad") or "")
        bloque = contexto_de_fallas(fallas, conversacion, entrante.texto or "", universidad)
        if bloque:
            fallas_contadas[conversacion] = time.monotonic()
            registro.info("[%s] le cuento las fallas conocidas", conversacion)
        return bloque

    def _fuera_de_los_canales(entrante) -> bool:
        """En qué canales contesta. El webhook de Chatwoot es de cuenta, no de
        bandeja: llega TODO, así que el filtro va acá."""
        if not config.canales:
            return False
        canal_entrante = canal.canal_de(entrante.conversacion)
        if canal_entrante and canal_entrante not in config.canales:
            registro.info(
                "[%s] de %s: fuera de los canales que atiende el agente",
                entrante.conversacion,
                canal_entrante,
            )
            return True
        return False

    async def _leer_adjuntos(entrante) -> str:
        """Lo que escribió la persona, con lo que cuenta el lector de cada archivo.

        Lo que no se pudo leer sigue el camino de siempre: queda anunciado y la
        conversación pasa a una persona, con el motivo en la nota interna.
        """
        escrito = (entrante.datos.get("content") or "").strip()
        partes = [escrito] if escrito else []
        fallas = []
        for archivo in archivos_del_evento(entrante.datos):
            try:
                relato = await asyncio.to_thread(lector.leer, archivo)
            except NoSePuedeLeer as e:
                fallas.append(f"{archivo.tipo} {archivo.nombre}: {e}".strip())
                partes.append(f"[adjunto recibido: {archivo.como_se_llama()}, que no se pudo abrir]")
                continue
            except Exception as e:
                # El error del proveedor no se esconde: va entero a la nota
                # interna y al log. A la persona no, como en `responder`.
                aviso = f"{type(e).__name__}: {e}"
                registro.error("[%s] el lector falló: %s", entrante.conversacion, aviso)
                fallas.append(f"{archivo.tipo} {archivo.nombre}: {aviso}".strip())
                partes.append(f"[adjunto recibido: {archivo.como_se_llama()}, que no se pudo abrir]")
                continue
            registro.info("[%s] leí %s", entrante.conversacion, archivo.como_se_llama())
            partes.append(f"[la persona mandó {archivo.como_se_llama()}. Lo que muestra: {relato}]")
        if fallas:
            traspaso.pedir(
                entrante.conversacion,
                "Mandó archivos que el agente no pudo leer (" + "; ".join(fallas) + "). "
                "Hay que abrirlos a mano.",
            )
        return "\n".join(partes)

    async def _atender(entrante, contexto: str = "") -> None:
        """Suma el mensaje a la ráfaga, con sus archivos ya leídos si se puede."""
        conversacion = entrante.conversacion
        try:
            _anotar_personales(entrante)
        except Exception as e:
            # Lo que no se anotó se tapa igual por su forma (el correo, el
            # teléfono); dejar sin respuesta a la persona por esto no.
            registro.error("[%s] no pude anotar sus datos: %s", conversacion, e)
        contexto = "\n".join(x for x in (contexto, _fallas_para(entrante)) if x)
        # El contexto de la vuelta va pegado al mensaje y no como parte
        # aparte: sin espera en el buffer, saldría como una respuesta sola.
        def con_contexto(texto: str) -> str:
            return f"{contexto}\n{texto}" if contexto else texto

        if entrante.adjuntos and lector is not None and ajustes.vigentes().leer_adjuntos:
            # La lectura tarda unos segundos: entra a la ráfaga como algo que
            # se espera al soltarla, y el webhook contesta ya.
            async def leido() -> str:
                return con_contexto(await _leer_adjuntos(entrante))

            await buffer.agregar(conversacion, asyncio.create_task(leido()))
            return

        # Un archivo que el bot no lee lo pasa a una persona, siempre y sin
        # preguntarle al modelo: dejarlo a su criterio es dejarlo al azar, y el
        # caso que nos importa —alguien mandando el pensum que no encontró— es
        # justo el que no se puede perder. El traspaso se consume después de
        # enviar: el agente igual acusa recibo, y recién ahí la conversación
        # cambia de manos.
        if entrante.adjuntos:
            traspaso.pedir(
                conversacion,
                "Mandó archivos que el agente no puede leer ("
                + ", ".join(entrante.adjuntos)
                + "). Hay que abrirlos a mano.",
            )
        await buffer.agregar(conversacion, con_contexto(entrante.texto))

    async def _quizas_retomar(entrante) -> None:
        """Si la persona volvió a escribir pasadas 24 horas de la última
        respuesta de Ian, la conversación vuelve al bot (ver vuelta.py)."""
        conversacion = entrante.conversacion
        try:
            if time.monotonic() - retomadas.get(conversacion, float("-inf")) < RETOMADA_RECIEN:
                # Otro mensaje de la misma ráfaga: la vuelta ya está hecha.
                await _atender(entrante)
                return
            vigentes = ajustes.vigentes()
            if not vigentes.devolver_al_bot:
                return
            mensajes = await asyncio.to_thread(canal.historial, conversacion)
            ultima = ultima_respuesta_de_ian(mensajes, config.chatwoot_etiqueta_humano)
            if ultima is None:
                # Ian nunca le contestó: esa persona espera a alguien del
                # equipo, no al bot.
                return
            ahora = time.time()
            if ahora - ultima < vigentes.devolver_tras:
                return
            anteriores = [m for m in mensajes if str(m.get("id") or "") != entrante.identificador]
            contexto = contexto_de_la_vuelta(anteriores, config.chatwoot_etiqueta_humano)
            await asyncio.to_thread(canal.devolver_al_bot, conversacion, NOTA_DE_LA_VUELTA)
            retomadas[conversacion] = time.monotonic()
            registro.info(
                "[%s] escribió %s h después de la última respuesta de Ian: la retoma el bot",
                conversacion,
                int((ahora - ultima) // 3600),
            )
            await _atender(entrante, contexto)
        except Exception as e:
            # Si esto falla la conversación queda como estaba, con Ian: es lo
            # mismo que pasaba antes de que existiera la vuelta.
            registro.error("[%s] no pude ver si la retoma el bot: %s", conversacion, e)

    @asynccontextmanager
    async def ciclo_de_vida(app: FastAPI):
        # Que los datos del equipo se VEAN en la bandeja. Chatwoot solo pinta
        # los atributos que están definidos, y sin esto el panel queda vacío
        # aunque los datos se hayan guardado bien.
        if hasattr(canal, "asegurar_atributos"):
            await asyncio.to_thread(canal.asegurar_atributos)
        # Los interruptores del admin, antes del primer mensaje.
        vigentes = await asyncio.to_thread(ajustes.leer)
        registro.info(
            "Ajustes del soporte - leer adjuntos %s (%s) - volver al bot %s",
            "sí" if vigentes.leer_adjuntos else "no",
            "con Gemini" if lector is not None else "sin lector",
            "sí" if vigentes.devolver_al_bot else "no",
        )
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

        if entrante is None:
            return JSONResponse({"estado": "ignorado"})

        if not canal.deberia_responder(entrante):
            # La etiqueta del traspaso ya no es para siempre: si es lo único
            # que lo calla, puede que la conversación vuelva al bot. Se mira en
            # otro lado porque pide el historial, y el webhook contesta ya.
            calla = getattr(canal, "calla_por_la_etiqueta", None)
            if calla is not None and calla(entrante) and not _fuera_de_los_canales(entrante):
                canal.marcar_atendido(entrante)
                asyncio.create_task(_quizas_retomar(entrante))
                return JSONResponse({"estado": "revisando"})
            # No es un error: es la mayoría de lo que llega. Cada respuesta
            # que manda el propio agente vuelve como un evento más.
            return JSONResponse({"estado": "ignorado"})

        # La ficha se guarda igual unas líneas más arriba, porque a quien
        # atienda a mano esos datos le sirven venga de donde venga.
        if _fuera_de_los_canales(entrante):
            return JSONResponse({"estado": "ignorado"})

        # Se suma a la ráfaga y contestamos ya. Lo que sigue pasa solo.
        await _atender(entrante)

        return JSONResponse({"estado": "recibido"})

    return app
