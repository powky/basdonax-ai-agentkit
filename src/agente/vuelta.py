"""Cuándo una conversación de Ian vuelve al bot.

La etiqueta del traspaso apagaba al bot para siempre: si la persona volvía a
escribir una semana después, con otra pregunta, nadie le contestaba hasta que
Ian la viera. El 15/11 eran 79 de las conversaciones que esperaban: Ian ya
las había contestado y la persona había vuelto a escribir.

La regla ahora: si escribe **más de 24 horas después de la última respuesta
de Ian**, la retoma el bot, con lo último que se habló como contexto. Si Ian
nunca le contestó, sigue siendo suya: esa persona está esperando a alguien
del equipo, no al bot.

El bot escribe con el usuario de Ian en Chatwoot, así que el remitente no los
distingue. Lo que sí:

  · lo que el bot manda va marcado (`studiante_bot` en `content_attributes`),
    y lo que Ian manda desde el admin también (`studiante_ian`);
  · lo que salió sin marca mientras la etiqueta estaba puesta es de Ian,
    porque con la etiqueta el bot no habla.

Es la misma regla que usa el API para la cola del admin
(studiante-api/internal/service/support_summary.go): si cambia una, cambia
la otra.
"""

from __future__ import annotations

import json
import re

ENTRANTE, SALIENTE, ACTIVIDAD = 0, 1, 2

MARCA_BOT = "studiante_bot"
MARCA_IAN = "studiante_ian"

# Desde acá el bot marca todo lo que manda (3275b07, arriba a las 22:28 UTC del
# 15/11): lo que un usuario manda sin marca es de Ian —desde la bandeja, el
# teléfono o donde sea—, con la etiqueta puesta o no. Antes, solo la etiqueta
# lo dice. Es el mismo momento que MarksSince en el API.
MARCAS_DESDE = 1794781800  # 2026-11-15T22:30:00Z


def _atributo(mensaje: dict, clave: str):
    crudo = mensaje.get("content_attributes")
    if isinstance(crudo, str):
        try:
            crudo = json.loads(crudo)
        except ValueError:
            return None
    return crudo.get(clave) if isinstance(crudo, dict) else None


def _tipo(mensaje: dict) -> int:
    tipo = mensaje.get("message_type")
    if isinstance(tipo, int):
        return tipo
    return {"incoming": ENTRANTE, "outgoing": SALIENTE, "activity": ACTIVIDAD}.get(str(tipo), -1)


def cambio_de_etiqueta(texto: str, etiqueta: str = "humano") -> tuple[bool, bool]:
    """Lee la línea de Chatwoot cuando cambia una etiqueta: (la puso, la quitó).

    «Ian Fernández agregó humano», «… eliminó a pensum-faltante, humano».
    """
    bajo = (texto or "").lower()
    for verbo, puso in (("agregó ", True), ("agrego ", True), (" added ", True),
                        ("eliminó ", False), ("elimino ", False), ("quitó ", False), (" removed ", False)):
        i = bajo.find(verbo)
        if i < 0:
            continue
        resto = bajo[i + len(verbo):]
        tiene = etiqueta in [t.strip(".;:") for t in re.split(r"[,\s]+", resto) if t]
        return (tiene, False) if puso else (False, tiene)
    return False, False


def autores(mensajes: list[dict], etiqueta: str = "humano") -> list[tuple[str, dict]]:
    """Cada mensaje público con quién lo escribió: persona, bot o ian.

    Las notas privadas y las líneas de actividad quedan afuera.
    """
    puesta = False
    salida = []
    for m in sorted(mensajes, key=lambda x: (x.get("created_at") or 0, x.get("id") or 0)):
        tipo = _tipo(m)
        if tipo == ACTIVIDAD:
            puso, quito = cambio_de_etiqueta(m.get("content") or "", etiqueta)
            if puso:
                puesta = True
            if quito:
                puesta = False
            continue
        if m.get("private"):
            continue
        if tipo == ENTRANTE:
            salida.append(("persona", m))
        elif tipo == SALIENTE:
            de_un_usuario = (m.get("sender") or {}).get("type") == "user"
            if _atributo(m, MARCA_BOT):
                quien = "bot"
            elif _atributo(m, MARCA_IAN) or puesta:
                quien = "ian"
            elif (m.get("created_at") or 0) >= MARCAS_DESDE and de_un_usuario:
                quien = "ian"
            else:
                quien = "bot"
            salida.append((quien, m))
    return salida


def ultima_respuesta_de_ian(mensajes: list[dict], etiqueta: str = "humano") -> int | None:
    """Cuándo contestó Ian por última vez (segundos Unix), o None si nunca."""
    de_ian = [m.get("created_at") or 0 for quien, m in autores(mensajes, etiqueta) if quien == "ian"]
    return max(de_ian) if de_ian else None


def contexto_de_la_vuelta(mensajes: list[dict], etiqueta: str = "humano", cuantos: int = 8) -> str:
    """Lo último que se habló, para que el bot no arranque de cero.

    El bot no tiene en su memoria lo que contestó Ian (eso pasó fuera de él),
    así que se le cuenta. Va entre corchetes, como los avisos del sistema, para
    que no lo tome por algo que escribió la persona.
    """
    lineas = []
    for quien, m in autores(mensajes, etiqueta)[-cuantos:]:
        texto = " ".join((m.get("content") or "").split())
        if not texto and m.get("attachments"):
            texto = "(mandó un archivo)"
        if not texto:
            continue
        if len(texto) > 300:
            # Se corta en un espacio y la palabra a medias se va: un correo o
            # un «Ref.» partido («mariafgomez2001@cor…») ya no tiene la forma
            # que la máscara reconoce (privacidad.py), y su primera parte
            # saldría al modelo.
            corte = texto.rfind(" ", 0, 301)
            texto = (texto[:corte] if corte > 0 else "") + "…"
        nombre = {"persona": "La persona", "bot": "Tú (el bot)", "ian": "Ian"}[quien]
        lineas.append(f"{nombre}: {texto}")
    if not lineas:
        return ""
    return (
        "[contexto: esta conversación la venía atendiendo Ian, y la "
        "persona volvió a escribir más de un día después. Lo último que se habló:\n"
        + "\n".join(lineas)
        + "\n— fin del contexto. Lo que sigue es lo que escribió ahora.]"
    )
