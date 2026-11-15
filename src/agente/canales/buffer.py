"""Juntar la ráfaga de mensajes.

La gente en WhatsApp no escribe un mensaje: escribe tres.

    "hola"
    "una consulta"
    "por el precio del plan"

Sin esto el agente contesta tres veces, y las tres mal: la primera no sabe
nada, la segunda tampoco, y recién la tercera tiene la pregunta entera. Peor
todavía, las tres respuestas se pisan entre sí en la pantalla del cliente.

Con esto, el agente espera, junta lo que llegue y contesta **una sola vez**
con todo junto.

    "hola
     una consulta
     por el precio del plan"

Cómo espera: cada mensaje nuevo reinicia el reloj (si sigue escribiendo,
seguimos esperando), pero hay un tope duro. Sin ese tope, alguien que manda
un mensaje cada tanto dejaría al agente esperando para siempre y nunca
recibiría respuesta.

Una parte de la ráfaga puede llegar todavía sin escribir: la lectura de una
foto o un PDF (lector.py) tarda unos segundos, así que se suma como algo que
se espera, y se espera recién al soltar la ráfaga, en el lugar donde llegó.
El reloj no se frena por eso: la persona sigue escribiendo mientras se lee.

Está en memoria a propósito. El AGENTS.md dice Redis, y va a hacer falta
cuando haya más de un proceso atendiendo: hoy hay uno solo, y una ráfaga que
se pierde si el contenedor se reinicia justo en esos segundos no justifica
sumar una base entera. Cuando se escale a varios procesos, se cambia esta
clase y nada más — el webhook no se entera.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable, Union

registro = logging.getLogger("agente.buffer")

# Un pedazo de la ráfaga: el texto, o lo que falta para tenerlo.
Parte = Union[str, Awaitable[str]]


class BufferDeMensajes:
    """Acumula los mensajes de cada conversación y avisa cuando paró la ráfaga."""

    def __init__(
        self,
        segundos: float,
        al_completar: Callable[[str, str], Awaitable[None]],
        tope: float | None = None,
    ) -> None:
        """
        `segundos`     cuánto se espera desde el último mensaje
        `al_completar` qué hacer con la ráfaga junta: (conversacion, texto)
        `tope`         cuánto se puede estirar la espera como máximo
        """
        self.segundos = max(0.0, float(segundos))
        self.al_completar = al_completar

        # El tope existe para el que escribe de a poco: sin él, un mensaje
        # cada 50 segundos con una espera de 60 no se contesta nunca.
        self.tope = float(tope) if tope is not None else self.segundos * 3

        self._pendientes: dict[str, list[Parte]] = {}
        self._relojes: dict[str, asyncio.Task] = {}
        self._arrancó_en: dict[str, float] = {}

    async def agregar(self, conversacion: str, texto: Parte) -> None:
        """Suma un mensaje a la ráfaga de esa conversación."""
        # Sin espera configurada no hay ráfaga que juntar: se contesta y listo.
        if self.segundos <= 0:
            await self.al_completar(conversacion, await _juntar([texto]))
            return

        self._pendientes.setdefault(conversacion, []).append(texto)

        ahora = asyncio.get_running_loop().time()
        self._arrancó_en.setdefault(conversacion, ahora)

        # El reloj anterior ya no sirve: llegó un mensaje nuevo y hay que
        # volver a contar desde cero (salvo que ya nos pasamos del tope).
        reloj = self._relojes.pop(conversacion, None)
        if reloj is not None:
            reloj.cancel()

        gastado = ahora - self._arrancó_en[conversacion]
        espera = min(self.segundos, max(0.0, self.tope - gastado))

        self._relojes[conversacion] = asyncio.create_task(
            self._esperar_y_soltar(conversacion, espera)
        )

    async def _esperar_y_soltar(self, conversacion: str, espera: float) -> None:
        try:
            await asyncio.sleep(espera)
        except asyncio.CancelledError:
            # Llegó otro mensaje: este reloj queda descartado y el nuevo se
            # encarga. No hay nada que limpiar, los mensajes ya están juntos.
            return

        self._relojes.pop(conversacion, None)
        self._arrancó_en.pop(conversacion, None)
        partes = self._pendientes.pop(conversacion, [])

        if not partes:
            return

        await self.al_completar(conversacion, await _juntar(partes))

    def pendientes(self, conversacion: str) -> int:
        """Cuántos mensajes hay esperando. Lo usan los tests y el /salud."""
        return len(self._pendientes.get(conversacion, []))

    async def vaciar(self) -> None:
        """Suelta todo lo que esté esperando. Se llama al apagar el servidor.

        Sin esto, un deploy en el momento justo se come la ráfaga de alguien
        y esa persona se queda sin respuesta, sin que nadie se entere.
        """
        for reloj in list(self._relojes.values()):
            reloj.cancel()
        self._relojes.clear()
        self._arrancó_en.clear()

        pendientes = self._pendientes
        self._pendientes = {}

        for conversacion, partes in pendientes.items():
            if partes:
                await self.al_completar(conversacion, await _juntar(partes))


async def _juntar(partes: list[Parte]) -> str:
    """La ráfaga en un solo texto, con cada lectura ya terminada."""
    textos = []
    for parte in partes:
        if isinstance(parte, str):
            textos.append(parte)
            continue
        try:
            textos.append(await parte)
        except Exception as e:
            # La lectura ya convierte sus fallas en texto y en traspaso (ver
            # webhook.py): si igual algo se escapa, se pierde esa parte y no la
            # ráfaga entera, que es lo que sí importa que llegue.
            registro.error("una parte de la ráfaga no se pudo leer: %s", e)
    return "\n".join(t for t in textos if t)
