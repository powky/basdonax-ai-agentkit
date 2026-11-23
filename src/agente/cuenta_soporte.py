"""La cuenta de Studiante de la persona con la que habla el bot.

La app escribe en cada mensaje de soporte un código ("Ref. K7Q2-9XMD") que
solo sale de la cuenta de esa persona. Cuando alguien lo manda desde su
WhatsApp, el API ata ese número a la cuenta como verificado, y desde ahí el
bot puede leer el diagnóstico de esa cuenta: sus carreras, el índice que
reportó su universidad, lo que le impide los honores y si la app de su
teléfono quedó sin verificar. Es lo que Ian miraba en el admin para contestar
"mi índice es otro" o "no me salen los honores".

Tres cosas que importan:

  · **El correo del mensaje no sirve como llave.** Cualquiera lo puede
    escribir, así que con un número atado solo por el correo el API no manda
    el diagnóstico, y acá se le explica al modelo cómo conseguir el código.
  · **La conversación no la elige el modelo.** La herramienta no recibe
    argumentos: el id sale del contextvar que pone el canal (contexto.py). Ni
    con la mejor inyección de prompt alguien puede pedir la cuenta de otro.
  · **Nada de quién es la persona.** El API no manda nombre, correo, matrícula
    ni nada de Empleos; acá tampoco se agrega.
"""

from __future__ import annotations

import json
import logging
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Callable

registro = logging.getLogger("agente.cuenta")

ESPERA_DE_RED = 15

# La hora de República Dominicana, que no cambia en verano.
RD = timezone(timedelta(hours=-4))

SISTEMAS = {"ios": "iOS", "android": "Android"}

COMO_VERIFICAR = (
    "Para que puedas verla, pídele que te escriba desde la app: Cuenta → "
    "«¿Necesitas ayuda?» → WhatsApp. El mensaje que arma la app trae un código "
    "que ata este WhatsApp a su cuenta (si su app es vieja y no lo trae, que la "
    "actualice primero). No le pidas el correo para buscarla: con el correo no "
    "se puede saber si la cuenta es suya."
)

SIN_CUENTA = "Este WhatsApp no está atado a ninguna cuenta de Studiante. " + COMO_VERIFICAR

SIN_VERIFICAR = (
    "Hay una cuenta con el correo que trae el mensaje, pero eso no prueba que "
    "sea de esta persona, así que no puedes verla. " + COMO_VERIFICAR
)

NO_SE_PUDO = (
    "No se pudo leer su cuenta en este momento. No inventes nada de su cuenta "
    "ni le digas cómo está: dile que lo revisas y usa "
    "`pasar_a_una_persona` con lo que pregunta."
)


class CuentaDelSoporte:
    """Pide al API la cuenta atada a una conversación de Chatwoot."""

    def __init__(self, url_api: str, llave: str, abrir: Callable = urllib.request.urlopen) -> None:
        self.base = url_api.rstrip("/") if url_api else ""
        self.llave = llave
        self._abrir = abrir

    def configurada(self) -> bool:
        return bool(self.base and self.llave)

    def de(self, conversacion: str) -> dict:
        """Lo que dice el API de la cuenta de esa conversación."""
        pedido = urllib.request.Request(
            f"{self.base}/agent/support/conversations/{int(conversacion)}/account",
            headers={
                "X-Api-Key": self.llave,
                "Accept": "application/json",
                "User-Agent": "Studiante-Agente/1.0 (+https://studiante.app)",
            },
        )
        with self._abrir(pedido, timeout=ESPERA_DE_RED) as respuesta:
            return json.loads(respuesta.read().decode("utf-8")).get("data") or {}


def _fecha(crudo) -> str:
    """"2026-11-14T13:02:00Z" → "14/11/2026", en hora dominicana."""
    if not crudo:
        return ""
    try:
        momento = datetime.fromisoformat(str(crudo).replace("Z", "+00:00"))
    except ValueError:
        return ""
    return momento.astimezone(RD).strftime("%d/%m/%Y")


def _numero(valor) -> str:
    """3.42 → "3.42"; 98.0 → "98"."""
    try:
        return f"{float(valor):g}"
    except (TypeError, ValueError):
        return str(valor)


def redactar(datos: dict) -> str:
    """El diagnóstico en el idioma del modelo: renglones cortos, cada uno con
    lo que significa para la persona."""
    if not datos.get("linked"):
        return SIN_CUENTA
    diagnostico = datos.get("diagnosis")
    if not datos.get("verified") or not isinstance(diagnostico, dict):
        return SIN_VERIFICAR

    como = "con el código de la app" if datos.get("source") == "app" else "la ató Ian"
    lineas = [f"Cuenta de Studiante de esta persona (verificada: {como})."]

    if diagnostico.get("blocked"):
        lineas.append(
            "- Ian le puso una restricción a la cuenta. No le expliques ni le "
            "menciones nada de eso: pásala con `pasar_a_una_persona`."
        )
    if diagnostico.get("chatBlocked"):
        lineas.append(
            "- Ian le quitó los mensajes entre amigos. No lo expliques: si "
            "pregunta por eso, pásala con `pasar_a_una_persona`."
        )

    carreras = diagnostico.get("enrollments") or []
    if not carreras:
        lineas.append("- No tiene ninguna carrera elegida en la app.")
    for c in carreras:
        nombre = c.get("programName") or c.get("programCode") or "su carrera"
        codigo = f" ({c['programCode']})" if c.get("programName") and c.get("programCode") else ""
        cual = "Carrera activa" if c.get("active") else "También tiene"
        linea = f"- {cual}: {c.get('university', '')} · {nombre}{codigo}."
        if isinstance(c.get("progress"), int):
            linea += f" Avance: {c['progress']}%."
        lineas.append(linea)
        indice = c.get("index")
        if isinstance(indice, dict) and indice.get("value"):
            texto = f"  Índice que reportó su universidad: {_numero(indice['value'])}"
            if indice.get("creditsPassed"):
                texto += f", con {_numero(indice['creditsPassed'])} créditos aprobados"
            reprobadas = indice.get("failedAttempts") or 0
            texto += f" y {reprobadas} {'intento reprobado' if reprobadas == 1 else 'intentos reprobados'} en su historial"
            cuando = _fecha(indice.get("updatedAt"))
            texto += f" (al {cuando})." if cuando else "."
            lineas.append(texto)
        elif c.get("active"):
            lineas.append("  Sin índice de su universidad: no ha leído su récord con esta carrera.")

    portal = diagnostico.get("portal")
    if isinstance(portal, dict):
        partes = []
        if portal.get("lastRecordAt"):
            partes.append(f"su récord el {_fecha(portal['lastRecordAt'])}")
        if portal.get("lastScheduleAt"):
            partes.append(f"su horario el {_fecha(portal['lastScheduleAt'])}")
        if partes:
            lineas.append("- Sincronización automática: leyó por última vez " + " y ".join(partes) + ".")
    else:
        lineas.append("- Nunca conectó su universidad con la sincronización automática.")

    honores = diagnostico.get("honors")
    if isinstance(honores, dict):
        fallas = honores.get("failed") or []
        donde = f"{honores.get('university', '')} · {honores.get('programCode', '')}".strip(" ·")
        if fallas:
            lineas.append(
                f"- Honores ({donde}): estas materias reprobadas cuentan en contra, aunque "
                "las haya aprobado después:"
            )
            for f in fallas:
                linea = f"  · {f.get('code', '')} {f.get('name', '')} — {f.get('grade', '')} en {f.get('term', '')}".rstrip()
                otra = f.get("retake")
                if isinstance(otra, dict):
                    if otra.get("inProgress"):
                        linea += f"; la está cursando de nuevo en {otra.get('term', '')}"
                    elif otra.get("grade"):
                        linea += f"; la aprobó en {otra.get('term', '')} con {otra.get('grade')}"
                lineas.append(linea + ".")
        elif isinstance(portal, dict) and portal.get("lastRecordAt"):
            lineas.append(f"- Honores ({donde}): no hay materias reprobadas en su récord que los impidan.")

    app = diagnostico.get("appCheck")
    if isinstance(app, dict):
        detalle = ", ".join(
            x
            for x in (
                SISTEMAS.get(app.get("platform") or "", app.get("platform")),
                f"versión {app['appVersion']}" if app.get("appVersion") else "",
                app.get("code"),
            )
            if x
        )
        lineas.append(
            "- La app de su teléfono no pudo demostrar que es la original"
            + (f" ({detalle})" if detalle else "")
            + f", la última vez el {_fecha(app.get('lastAt'))}: por eso le puede fallar"
            " cargar el pensum o el catálogo. Que la actualice desde la tienda, la cierre"
            " del todo y la vuelva a abrir."
        )

    visto = _fecha(diagnostico.get("lastSeenAt"))
    if visto or diagnostico.get("appVersion"):
        texto = "- Última vez en la app"
        if visto:
            texto += f": {visto}"
        if diagnostico.get("appVersion"):
            texto += f", versión {diagnostico['appVersion']}"
            if diagnostico.get("platform"):
                texto += f" en {SISTEMAS.get(diagnostico['platform'], diagnostico['platform'])}"
        lineas.append(texto + ".")

    lineas.append(
        "Esto es para que entiendas su caso. No se lo leas entero ni le hables de "
        "un diagnóstico: usa solo lo que responde a lo que pregunta, con tus palabras."
    )
    return "\n".join(lineas)
