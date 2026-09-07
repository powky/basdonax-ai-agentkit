"""El canal de Chatwoot.

Es el que atiende WhatsApp de verdad, pero no le habla a Meta: le habla a
Chatwoot, que está en el medio. El recorrido completo de un mensaje es este:

    persona → WhatsApp → Meta → Chatwoot → (webhook) → agente
                                    ↑                     │
                                    └───── API REST ──────┘

Por qué con Chatwoot en el medio y no directo contra Meta:

  · Queda el historial y la bandeja de entrada, con buscador.
  · Una persona puede meterse en la conversación y seguirla a mano.
  · El mismo agente atiende Instagram, el widget de la web o Telegram sin
    tocar una línea: para nosotros todo entra por el mismo webhook.

A diferencia de Telegram, acá **nadie sale a buscar los mensajes**: Chatwoot
nos pega a una URL cuando pasa algo. Por eso esto necesita un servidor con
dominio y HTTPS, y por eso el webhook vive en su propia app (web/webhook.py).

El `conversacion` (el thread_id de LangGraph) es el **id de conversación de
Chatwoot**. Es la misma unidad que ves en la bandeja: un hilo en la pantalla
es un hilo de memoria del agente. También es lo que necesitamos para
contestar, así que sirve para las dos cosas.

Se usa `urllib`, de la biblioteca estándar, para no sumar una dependencia.
La API de Chatwoot son pedidos HTTP con JSON: no hace falta más.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections import deque

from .base import Canal, MensajeEntrante
from .ficha import Ficha, leer_ficha

# Cuánto esperamos a que Chatwoot conteste. Corre en el mismo servidor que
# el agente, así que si tarda más que esto es porque algo anda mal.
ESPERA_DE_RED = 20


class ErrorDeChatwoot(Exception):
    """Chatwoot contestó algo que no esperábamos."""


class Chatwoot(Canal):
    """La bandeja de Chatwoot: por acá entran y salen los mensajes."""

    nombre = "chatwoot"

    def __init__(
        self,
        url: str,
        token: str,
        cuenta_id: str | int,
        etiqueta_humano: str = "humano",
    ) -> None:
        if not url or not token:
            raise ValueError(
                "Faltan datos de Chatwoot. Abrí el .env y completá "
                "CHATWOOT_URL y CHATWOOT_TOKEN."
            )

        # La barra final sobra y duplicada rompe la URL ("...com//api/v1").
        self.url = url.rstrip("/")
        self.token = token
        self.cuenta_id = str(cuenta_id)
        self.etiqueta_humano = (etiqueta_humano or "").strip().lower()

        # Los mensajes que ya contestamos. Chatwoot reintenta el webhook si no
        # le respondemos rápido, y sin esto el agente contesta dos veces lo
        # mismo. Alcanza con acordarse de los últimos.
        self._ya_contestados: deque[str] = deque(maxlen=1000)

        # De qué canal es cada conversación (whatsapp, instagram, email…). Se
        # anota al traducir el evento porque después, cuando el agente
        # responde, el evento ya no está a mano — y el pedido que anote tiene
        # que saber por dónde entró.
        self._canales: dict[str, str] = {}

    # -- Entrada ---------------------------------------------------------------

    def traducir(self, evento: dict) -> MensajeEntrante | None:
        """Convierte un evento del webhook en algo que el agente entiende.

        Devuelve None si el evento no es un mensaje que tengamos que mirar:
        otro tipo de evento, o un mensaje sin texto (un audio, una foto, un
        adjunto suelto) que el agente todavía no sabe leer.
        """
        if evento.get("event") != "message_created":
            return None

        conversacion = evento.get("conversation") or {}
        id_conversacion = conversacion.get("id")
        texto = (evento.get("content") or "").strip()

        if not id_conversacion or not texto:
            return None

        self._canales[str(id_conversacion)] = _canal_de(evento)

        return MensajeEntrante(
            texto=texto,
            # El id de conversación es el thread_id: la memoria de cada
            # persona por separado.
            conversacion=str(id_conversacion),
            identificador=str(evento.get("id") or ""),
            datos=evento,
        )

    def deberia_responder(self, mensaje: MensajeEntrante) -> bool:
        """Si el agente tiene que contestar este mensaje o dejarlo pasar.

        Acá está casi toda la diferencia entre un bot de demo y uno que
        atiende clientes de verdad. Son cuatro filtros y los cuatro importan:
        """
        evento = mensaje.datos

        # 1. Solo los mensajes que ENTRAN. Los que salen son las respuestas
        #    del propio agente y las de las personas del equipo. Sin este
        #    filtro el agente se lee a sí mismo y se contesta para siempre:
        #    es el error más caro de todos, porque cada vuelta gasta tokens.
        if _tipo_de_mensaje(evento) != "incoming":
            return False

        # 2. Las notas privadas son para el equipo, no para el cliente. Si el
        #    agente contestara ahí, mandaría al chat algo que era interno.
        if evento.get("private"):
            return False

        # 3. El mismo mensaje dos veces. Chatwoot reintenta si el webhook no
        #    contestó a tiempo, y el reintento trae el mismo id.
        if mensaje.identificador and mensaje.identificador in self._ya_contestados:
            return False

        # 4. El traspaso a una persona. Si la conversación tiene la etiqueta,
        #    el bot se calla: la está atendiendo alguien del equipo. Es *el*
        #    diferencial de tener Chatwoot en el medio — se apaga con un clic
        #    desde la bandeja, sin tocar el servidor.
        if self._la_atiende_una_persona(evento):
            return False

        if mensaje.identificador:
            self._ya_contestados.append(mensaje.identificador)

        return True

    def la_atiende_una_persona(self, conversacion: str) -> bool:
        """Si esa conversación ya la tomó alguien del equipo.

        Pregunta por id, sin evento de por medio, porque se llama cuando el
        mensaje que la disparó ya pasó: después del buffer, justo antes de
        pensar la respuesta y otra vez antes de mandarla. Entre que la
        persona escribe y el bot contesta pasan los segundos de
        BUFFER_SEGUNDOS más lo que tarde el modelo, y ese rato es
        exactamente cuando alguien entra a la bandeja y pone la etiqueta.
        """
        if not self.etiqueta_humano:
            return False

        return self._tiene_la_etiqueta(self._etiquetas_de(conversacion))

    def _la_atiende_una_persona(self, evento: dict) -> bool:
        """Lo mismo, pero mirando primero lo que ya venía en el evento."""
        if not self.etiqueta_humano:
            return False

        conversacion = evento.get("conversation") or {}
        etiquetas = conversacion.get("labels")

        # Chatwoot manda las etiquetas en el evento casi siempre. Cuando no
        # las manda (cambia entre versiones y entre tipos de evento) hay que
        # preguntarle, porque dar por hecho que no hay ninguna sería dejar al
        # bot hablando arriba de una persona.
        if etiquetas is None:
            etiquetas = self._etiquetas_de(conversacion.get("id"))

        return self._tiene_la_etiqueta(etiquetas)

    def _tiene_la_etiqueta(self, etiquetas) -> bool:
        """La comparación, en un solo lugar: sin mayúsculas y sin espacios."""
        return self.etiqueta_humano in {
            str(e).strip().lower() for e in etiquetas or []
        }

    def _etiquetas_de(self, id_conversacion) -> list[str]:
        """Le pregunta a Chatwoot qué etiquetas tiene una conversación."""
        if not id_conversacion:
            return []

        # Por qué se traga el error: si Chatwoot no contesta esta consulta, la
        # alternativa es no responderle al cliente. Preferimos responder. El
        # riesgo del otro lado (el bot habla arriba de una persona) existe,
        # pero solo en el caso raro de que justo esta llamada falle.
        try:
            respuesta = self._api(
                "GET", f"conversations/{id_conversacion}/labels"
            )
        except Exception:
            return []

        return respuesta.get("payload") or []

    def guardar_nombre(self, conversacion: str, nombre: str) -> str:
        """Le pone nombre al contacto de esa conversación.

        Existe porque la app no manda el nombre: manda el correo y los datos
        del equipo. El nombre lo sabe la persona, así que el agente lo pregunta
        y lo guarda acá — y a partir de ahí la bandeja deja de ser una lista de
        números de teléfono.

        Devuelve un texto para el modelo, no lanza: si Chatwoot rechaza el
        cambio, el agente tiene que poder seguir la conversación igual.
        """
        nombre = " ".join((nombre or "").split())[:80]
        if not nombre:
            return "No me pasaste un nombre."

        try:
            datos = self._api("GET", f"conversations/{conversacion}")
            contacto = ((datos.get("meta") or {}).get("sender") or {})
            id_contacto = contacto.get("id")
            if not id_contacto:
                return "No encontré el contacto de esta conversación."

            self._api("PUT", f"contacts/{id_contacto}", {"name": nombre})
            return f"Listo, el contacto quedó como {nombre}."
        except Exception as e:
            print(f"[chatwoot] no se pudo guardar el nombre en {conversacion}: {e}")
            return "No pude guardarlo, pero seguí la conversación normalmente."

    def nombre_de(self, conversacion: str) -> str:
        """El nombre que ya tiene el contacto, si tiene uno de verdad.

        Los canales rellenan este campo con lo que sea: en WhatsApp puede venir
        el número, y "+18091234567" no es un nombre. Si lo que hay no tiene una
        letra, se devuelve vacío para que el agente lo pregunte.
        """
        try:
            datos = self._api("GET", f"conversations/{conversacion}")
            nombre = (((datos.get("meta") or {}).get("sender") or {}).get("name") or "").strip()
        except Exception:
            return ""
        return nombre if any(c.isalpha() for c in nombre) else ""

    def canal_de(self, conversacion: str) -> str:
        """Por dónde entró esa conversación: whatsapp, instagram, email, web."""
        return self._canales.get(str(conversacion), "")

    # -- Clasificación ---------------------------------------------------------

    def clasificar(self, mensaje: MensajeEntrante) -> Ficha:
        """Guarda en Chatwoot lo que la app haya mandado en el mensaje.

        Cuando alguien escribe desde la app, el mensaje trae versión, sistema,
        equipo, correo y a veces universidad y carrera (ver ficha.py). Eso se
        escribe en el contacto y la conversación queda etiquetada con el motivo
        —reporte, pensum-faltante, pensum-con-error— para que la bandeja se
        pueda filtrar sin que nadie clasifique a mano.

        Corre para TODOS los mensajes que entran, incluso los que el agente no
        va a contestar porque una persona tomó la conversación: la ficha es
        igual de útil para quien atiende a mano.

        Nada de esto puede tumbar la respuesta: si Chatwoot rechaza el correo
        por duplicado o la llamada falla, queda en los logs y se sigue.
        """
        ficha = leer_ficha(mensaje.texto)
        if ficha.vacia():
            return ficha

        evento = mensaje.datos or {}
        conversacion = evento.get("conversation") or {}
        id_conversacion = conversacion.get("id")

        contacto = (
            (conversacion.get("meta") or {}).get("sender")
            or evento.get("sender")
            or {}
        )
        id_contacto = contacto.get("id")

        if id_contacto:
            self._actualizar_contacto(id_contacto, ficha, contacto)
        if id_conversacion and ficha.etiquetas:
            self._etiquetar(id_conversacion, ficha.etiquetas)

        return ficha

    # Los atributos que la ficha escribe, con el nombre que se ve en la
    # bandeja. Ver ficha.atributos(): las claves tienen que coincidir.
    ATRIBUTOS = {
        "app_version": "Versión de la app",
        "sistema": "Sistema",
        "dispositivo": "Dispositivo",
        "universidad": "Universidad",
        "carrera": "Carrera",
        "plan": "Plan",
    }

    def asegurar_atributos(self) -> None:
        """Crea en Chatwoot las definiciones de los atributos que escribimos.

        Sin esto el panel del contacto sale VACÍO aunque los datos estén
        guardados: Chatwoot solo pinta los atributos que alguien definió antes
        en sus ajustes, y la API acepta los valores igual. O sea que el fallo
        no da error en ningún lado — simplemente no se ve nada, que es la peor
        forma de fallar.

        Es idempotente: los que ya existen devuelven conflicto y se ignoran.
        Y es best-effort: si Chatwoot no contesta, el agente atiende igual.
        """
        for clave, nombre in self.ATRIBUTOS.items():
            try:
                self._api(
                    "POST",
                    "custom_attribute_definitions",
                    {
                        "attribute_display_name": nombre,
                        "attribute_key": clave,
                        "attribute_display_type": "text",
                        "attribute_model": "contact_attribute",
                        "attribute_description": "Lo manda la app en el mensaje de soporte.",
                    },
                )
            except Exception:
                # Ya existía, o Chatwoot está de mal humor. Ninguna de las dos
                # cosas justifica no atender a nadie.
                pass

    def _actualizar_contacto(self, id_contacto, ficha: Ficha, actual: dict) -> None:
        """Escribe correo y atributos en el contacto, sin pisar lo que ya hay."""
        cambios: dict = {}

        # El correo solo se escribe si el contacto no tiene: sobreescribirlo
        # con el de otra sesión mezclaría dos personas en un mismo contacto.
        if ficha.correo and not (actual.get("email") or "").strip():
            cambios["email"] = ficha.correo

        atributos = ficha.atributos()
        if atributos:
            # Los de antes se conservan: un segundo mensaje sin universidad no
            # puede borrar la que se leyó en el primero.
            previos = actual.get("custom_attributes") or {}
            cambios["custom_attributes"] = {**previos, **atributos}

        if not cambios:
            return

        try:
            self._api("PUT", f"contacts/{id_contacto}", cambios)
        except Exception as e:
            # El caso típico: el correo ya existe en otro contacto y Chatwoot
            # contesta 422. Se reintenta sin el correo, que los atributos del
            # equipo son lo que más se usa para diagnosticar.
            if "email" in cambios:
                cambios.pop("email")
                if cambios:
                    try:
                        self._api("PUT", f"contacts/{id_contacto}", cambios)
                        return
                    except Exception as e2:
                        e = e2
            print(f"[chatwoot] no se pudo actualizar el contacto {id_contacto}: {e}")

    def _etiquetar(self, id_conversacion, etiquetas: list[str]) -> None:
        """Suma etiquetas a la conversación.

        La API de Chatwoot REEMPLAZA la lista completa, así que primero hay que
        leer las que ya tiene: mandar solo la nueva le borraría la etiqueta
        `humano` a una conversación que alguien tomó, y el bot volvería a
        hablar encima.
        """
        try:
            actuales = self._etiquetas_de(id_conversacion)
            faltantes = [e for e in etiquetas if e not in actuales]
            if not faltantes:
                return
            self._api(
                "POST",
                f"conversations/{id_conversacion}/labels",
                {"labels": list(actuales) + faltantes},
            )
        except Exception as e:
            print(f"[chatwoot] no se pudo etiquetar la conversación {id_conversacion}: {e}")

    # -- Salida ----------------------------------------------------------------

    def enviar(self, conversacion: str, mensajes: list[str]) -> None:
        """Manda las respuestas a esa conversación, en orden.

        Salen como `outgoing`, que es lo que Chatwoot entiende por "esto lo
        dice nuestro lado". Desde ahí Chatwoot lo empuja al canal que
        corresponda: WhatsApp, Instagram, el widget de la web.
        """
        for texto in mensajes:
            if not texto.strip():
                continue

            self._api(
                "POST",
                f"conversations/{conversacion}/messages",
                {"content": texto, "message_type": "outgoing"},
            )

    def pasar_a_una_persona(self, conversacion: str, motivo: str) -> None:
        """Deja una nota interna y pone la etiqueta de traspaso.

        La nota es `private`: sale en la bandeja y NO le llega al cliente.
        Sirve para que quien abra la conversación sepa de una por qué está
        ahí, en vez de tener que deducirlo leyendo el hilo.

        La etiqueta va después de la nota y no antes: es la misma que apaga
        al bot, así que ponerla primero haría que el propio mensaje que
        estamos por mandar se quede sin salir.
        """
        try:
            self._api(
                "POST",
                f"conversations/{conversacion}/messages",
                {"content": motivo, "message_type": "outgoing", "private": True},
            )
        except Exception as e:
            print(f"[chatwoot] no se pudo dejar la nota en {conversacion}: {e}")

        if self.etiqueta_humano:
            self._etiquetar(conversacion, [self.etiqueta_humano])

    def escribiendo(self, conversacion: str, encendido: bool = True) -> None:
        """El "escribiendo..." mientras el modelo piensa.

        No es decorativo: una respuesta puede tardar varios segundos y sin
        esto la persona no sabe si la escucharon o si se colgó.
        """
        # Que falle el aviso no puede voltear la respuesta: es cosmético.
        try:
            self._api(
                "POST",
                f"conversations/{conversacion}/toggle_typing_status",
                {"typing_status": "on" if encendido else "off"},
            )
        except Exception:
            pass

    # -- La API ----------------------------------------------------------------

    def yo_soy(self) -> dict:
        """Los datos de la cuenta. Sirve para avisar al arrancar con cuál se habla."""
        return self._api("GET", "conversations?status=open&page=1")

    def _api(self, metodo: str, camino: str, datos: dict | None = None) -> dict:
        """Una llamada a la API de Chatwoot."""
        url = f"{self.url}/api/v1/accounts/{self.cuenta_id}/{camino}"

        pedido = urllib.request.Request(
            url,
            data=json.dumps(datos).encode("utf-8") if datos is not None else None,
            method=metodo,
            headers={
                "Content-Type": "application/json",
                # Así se autentica Chatwoot: no es un Bearer, es este header.
                "api_access_token": self.token,
                # Sin esto salimos como "Python-urllib/3.x", y cualquier
                # Cloudflare delante de Chatwoot lo trata como bot y contesta
                # 403 con el código 1010. El síntoma es de los que cuestan:
                # el agente recibe el mensaje, lo piensa, gasta los tokens del
                # modelo, y la respuesta muere al salir.
                "User-Agent": "Studiante-Agente/1.0 (+https://studiante.app)",
                "Accept": "application/json",
            },
        )

        try:
            with urllib.request.urlopen(pedido, timeout=ESPERA_DE_RED) as respuesta:
                cuerpo = respuesta.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            # El cuerpo del error es lo único que dice qué pasó de verdad
            # (token vencido, conversación que no existe, cuenta equivocada).
            # Sin esto solo se ve "HTTP Error 404" y no se puede arreglar nada.
            detalle = e.read().decode("utf-8", "replace")[:300]
            raise ErrorDeChatwoot(
                f"Chatwoot devolvió {e.code} en {metodo} {camino}: {detalle}"
            ) from None

        return json.loads(cuerpo) if cuerpo else {}


# -- Ayudantes ----------------------------------------------------------------


def _canal_de(evento: dict) -> str:
    """De "Channel::Whatsapp" a "whatsapp". Vacío si Chatwoot no lo manda."""
    conversacion = evento.get("conversation") or {}
    crudo = (
        (conversacion.get("channel") or "")
        or ((evento.get("inbox") or {}).get("channel_type") or "")
    )
    if not crudo:
        return ""
    corto = str(crudo).rsplit("::", 1)[-1].lower()
    # Los nombres que usa Chatwoot para lo mismo, unificados.
    return {"twilipsms": "sms", "api": "api", "webwidget": "web"}.get(corto, corto)


def _tipo_de_mensaje(evento: dict) -> str:
    """Si el mensaje entra o sale.

    Chatwoot lo manda como texto ("incoming"), pero según la versión y el
    endpoint puede venir como número (0 = incoming, 1 = outgoing). Traducimos
    los dos para que un cambio de versión no vuelva loco al bot.
    """
    tipo = evento.get("message_type")

    if isinstance(tipo, int):
        return {0: "incoming", 1: "outgoing"}.get(tipo, "otro")

    return str(tipo or "").strip().lower()
