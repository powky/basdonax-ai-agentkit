"""Los interruptores del bot que Ian prende y apaga desde el admin.

Viven en el API de Studiante (la sección Soporte del admin) y se leen acá
con una llave de servicio que solo sirve para eso (`support:config`):

  · `leer_adjuntos`: el bot abre las fotos, los PDF y los audios que le
    mandan, en vez de pasarle cada archivo a una persona.
  · `devolver_al_bot`: si la persona vuelve a escribir más de 24 horas después
    de la última respuesta de Ian, el bot retoma la conversación.

Se leen como mucho una vez por minuto. Si el API no contesta, valen los
últimos que se leyeron; si nunca se leyeron, los de fábrica (los dos
prendidos, que es como los dejó Ian). Que el API se caiga no puede dejar al
bot mudo: es un ajuste, no una dependencia.
"""

from __future__ import annotations

import json
import logging
import threading
import time
import urllib.request
from dataclasses import dataclass
from typing import Callable

registro = logging.getLogger("agente.ajustes")

# Cada cuánto se vuelven a pedir. Un cambio en el admin tarda como mucho esto
# en llegar al bot.
CADA = 60.0
ESPERA_DE_RED = 8


@dataclass(frozen=True)
class Ajustes:
    leer_adjuntos: bool = True
    devolver_al_bot: bool = True
    # Cuánto tiene que pasar desde la última respuesta de Ian, en segundos.
    devolver_tras: int = 24 * 60 * 60


DE_FABRICA = Ajustes()


class AjustesDelSoporte:
    """Lee los interruptores del API y se los guarda un rato."""

    def __init__(
        self,
        url_api: str,
        llave: str,
        cada: float = CADA,
        abrir: Callable = urllib.request.urlopen,
        reloj: Callable[[], float] = time.monotonic,
    ) -> None:
        self.url = f"{url_api.rstrip('/')}/agent/support/config" if url_api else ""
        self.llave = llave
        self.cada = cada
        self._abrir = abrir
        self._reloj = reloj
        self._ultimos = DE_FABRICA
        self._leidos_en: float | None = None
        self._candado = threading.Lock()
        self._pidiendo = False

    def vigentes(self) -> Ajustes:
        """Los que hay ahora, sin esperar la red.

        Es lo que mira el webhook, que tiene que contestarle a Chatwoot ya: si
        pasó el minuto, los pide de nuevo en otro hilo y este mensaje se
        decide con los que había.
        """
        if self.url and self.llave and self._vencidos() and not self._pidiendo:
            self._pidiendo = True
            threading.Thread(target=self._pedir_aparte, daemon=True).start()
        return self._ultimos

    def _vencidos(self) -> bool:
        return self._leidos_en is None or self._reloj() - self._leidos_en >= self.cada

    def _pedir_aparte(self) -> None:
        try:
            self.leer()
        finally:
            self._pidiendo = False

    def leer(self) -> Ajustes:
        """Los vigentes. Hace red como mucho una vez cada `cada` segundos."""
        if not self.url or not self.llave:
            return self._ultimos
        with self._candado:
            ahora = self._reloj()
            if self._leidos_en is not None and ahora - self._leidos_en < self.cada:
                return self._ultimos
            # Se marca antes de pedir: si el API está caído, el próximo intento
            # espera su minuto en vez de reintentar con cada mensaje.
            self._leidos_en = ahora
            try:
                self._ultimos = self._pedir()
            except Exception as e:
                # Uno de los tragados a propósito: sin el API el bot sigue con
                # lo último que supo. Queda en el log para que se vea.
                registro.warning("no pude leer los ajustes del soporte: %s", e)
            return self._ultimos

    def _pedir(self) -> Ajustes:
        pedido = urllib.request.Request(
            self.url,
            headers={
                "X-Api-Key": self.llave,
                "Accept": "application/json",
                "User-Agent": "Studiante-Agente/1.0 (+https://studiante.app)",
            },
        )
        with self._abrir(pedido, timeout=ESPERA_DE_RED) as respuesta:
            datos = json.loads(respuesta.read().decode("utf-8")).get("data") or {}
        tras = datos.get("returnAfter")
        return Ajustes(
            leer_adjuntos=bool(datos.get("readAttachments", True)),
            devolver_al_bot=bool(datos.get("returnToBot", True)),
            devolver_tras=int(tras) if isinstance(tras, int) and tras > 0 else DE_FABRICA.devolver_tras,
        )
