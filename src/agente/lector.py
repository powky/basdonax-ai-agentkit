"""Leer lo que mandan: fotos, PDF y notas de voz.

La primera decisión del diseño es que el agente recibe texto y devuelve texto
(AGENTS.md), y eso no se toca. El archivo no le llega al agente: lo lee antes
otro pedido a Gemini, que lo cuenta en palabras, y al agente le llega ese
relato como si la persona lo hubiera escrito:

    [la persona mandó un PDF. Lo que muestra: el plan de estudios de
     Mercadotecnia de UNAPEC, versión 2019, con materias por cuatrimestre,
     créditos y prerrequisitos…]

Así la memoria guarda texto y no megas de base64, y el agente decide con lo
que ya sabe hacer: buscar el pensum en el catálogo, mirar la guía, o pasarla
a una persona.

Lo que dice el lector sale de `prompts/lector-adjuntos.md`, leído en cada
archivo (como el prompt del sistema): se ajusta sin tocar código.

El vídeo no se lee: pesa mucho y casi nunca es lo que hace falta. Sigue
pasando a una persona, como cualquier archivo que no se pudo abrir.

Cada lectura, salga bien o mal, se le cuenta al API de Studiante
(`GastoDelLector`) para el panel de costos del admin: cuántos tokens gastó y
si Google contestó. Solo números y el código del error; nada del archivo, de
lo que dijo el lector ni de la conversación. El precio lo pone el API.
"""

from __future__ import annotations

import json
import logging
import mimetypes
import threading
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.parse import unquote

from langchain_core.messages import HumanMessage

registro = logging.getLogger("agente.lector")

# Lo que Gemini lee y nos sirve. Las notas de voz de WhatsApp llegan como
# audio/ogg (opus).
TIPOS_QUE_LEE = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
    "application/pdf",
    "audio/ogg",
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/aac",
    "audio/wav",
    "audio/x-wav",
    "audio/flac",
}

# El tope por archivo. Gemini acepta hasta 20 MB por pedido con los datos
# adentro; un pensum escaneado pesa 1-3 MB y una nota de voz, unos cientos de KB.
TOPE = 15 * 1024 * 1024

# Cómo se nombra cada tipo en el relato.
_NOMBRES = {"image": "una foto", "file": "un archivo", "audio": "una nota de voz", "video": "un vídeo"}

# Lo que se espera al API cuando se le cuenta el gasto de una lectura. Corto a
# propósito: va en otro hilo y no frena nada, pero tampoco tiene que quedar
# colgado si el API no contesta.
ESPERA_DEL_GASTO = 3


class NoSePuedeLeer(Exception):
    """El archivo no es de los que se leen, pesa de más, o no se pudo bajar."""


@dataclass(frozen=True)
class Archivo:
    """Un adjunto tal como lo manda Chatwoot en el webhook."""

    tipo: str  # image | file | audio | video | location…
    url: str
    mime: str = ""
    tamano: int = 0
    nombre: str = ""

    def como_se_llama(self) -> str:
        # Por la terminación también: Chatwoot no siempre manda el tipo, y
        # "un PDF" le dice al agente bastante más que "un archivo".
        if (self.mime or _mime_por_nombre(self.nombre)) == "application/pdf":
            return "un PDF"
        return _NOMBRES.get(self.tipo, "un archivo")


def archivos_del_evento(evento: dict) -> list[Archivo]:
    """Los adjuntos de un evento `message_created` de Chatwoot."""
    crudos = evento.get("attachments")
    if not isinstance(crudos, list):
        return []
    salida = []
    for a in crudos:
        if not isinstance(a, dict):
            continue
        url = str(a.get("data_url") or "")
        nombre = unquote(url.rsplit("/", 1)[-1].split("?")[0]) if url else ""
        tamano = a.get("file_size")
        salida.append(
            Archivo(
                tipo=str(a.get("file_type") or "file").strip().lower(),
                url=url,
                mime=_mime_limpio(str(a.get("content_type") or "")),
                tamano=tamano if isinstance(tamano, int) else 0,
                nombre=nombre,
            )
        )
    return salida


class LectorDeAdjuntos:
    """Cuenta en palabras lo que trae un archivo."""

    def __init__(
        self,
        modelo,
        descargar: Callable[[str, int], tuple[bytes, str]],
        instrucciones: Path,
        tope: int = TOPE,
        gasto: GastoDelLector | None = None,
    ) -> None:
        self.modelo = modelo
        self.descargar = descargar
        self.instrucciones = instrucciones
        self.tope = tope
        self.gasto = gasto

    def leer(self, archivo: Archivo) -> str:
        """El relato del archivo. Levanta NoSePuedeLeer si no es legible.

        El error del proveedor no se tapa: si Gemini falla, sube tal cual y
        quien llama lo anota en la nota interna del traspaso.
        """
        if archivo.tipo == "video":
            raise NoSePuedeLeer("los vídeos no se leen")
        if not archivo.url:
            raise NoSePuedeLeer("el adjunto no trae dirección")
        if archivo.tamano and archivo.tamano > self.tope:
            raise NoSePuedeLeer(f"pesa {archivo.tamano // (1024 * 1024)} MB")

        datos, mime_de_la_red = self.descargar(archivo.url, self.tope)
        mime = archivo.mime or _mime_limpio(mime_de_la_red) or _mime_por_nombre(archivo.nombre)
        if mime not in TIPOS_QUE_LEE:
            raise NoSePuedeLeer(f"no leo archivos {mime or 'sin tipo'}")

        pedido = HumanMessage(
            content=[
                {
                    "type": "text",
                    "text": self.instrucciones.read_text(encoding="utf-8")
                    + f"\n\nLo que llegó: {archivo.como_se_llama()} ({mime}).",
                },
                {"type": "media", "mime_type": mime, "data": datos},
            ]
        )
        try:
            respuesta = self.modelo.invoke([pedido])
        except Exception as e:
            # Un pedido que Google rechazó (un 402 sin saldo, un 429) también
            # se cuenta: es lo que deja ver en el panel desde cuándo no lee.
            self._anotar_gasto(error=e)
            raise
        self._anotar_gasto(respuesta=respuesta)
        texto = _texto(respuesta).strip()
        if not texto:
            raise NoSePuedeLeer("el lector no devolvió nada")
        return texto

    def _anotar_gasto(self, respuesta=None, error: BaseException | None = None) -> None:
        if self.gasto is None:
            return
        metadatos = getattr(respuesta, "response_metadata", None)
        modelo = (metadatos.get("model_name") if isinstance(metadatos, dict) else "") or getattr(
            self.modelo, "model", ""
        )
        self.gasto.anotar(str(modelo or ""), getattr(respuesta, "usage_metadata", None), error)


class GastoDelLector:
    """Le cuenta al API cuánto gastó cada lectura del lector de adjuntos.

    El lector llama a Gemini con la clave del bot, así que el API no se entera
    solo, como sí pasa con lo que va por su proxy. Esto le manda al API los
    tokens de cada llamada a `POST /agent/support/ai/usage` y el API les pone
    el precio: nunca se manda un monto desde acá.

    Va en otro hilo y no espera la respuesta: que el API tarde o esté caído no
    puede demorar ni tumbar la respuesta a la persona.
    """

    def __init__(
        self,
        url_api: str,
        llave: str,
        abrir: Callable = urllib.request.urlopen,
        lanzar: Callable[[Callable[[], None]], None] | None = None,
    ) -> None:
        self.url = f"{url_api.rstrip('/')}/agent/support/ai/usage" if url_api else ""
        self.llave = llave
        self._abrir = abrir
        # Los tests lo corren en el mismo hilo para mirar lo que salió.
        self._lanzar = lanzar or _en_otro_hilo

    def configurado(self) -> bool:
        return bool(self.url and self.llave)

    def anotar(self, modelo: str, uso: dict | None = None, error: BaseException | None = None) -> None:
        """Manda el gasto de una llamada, sin esperar. Nunca levanta."""
        if not self.configurado():
            return
        try:
            cuerpo = cuerpo_del_gasto(modelo, uso, error)
            self._lanzar(lambda: self._mandar(cuerpo))
        except Exception as e:
            # Tragado a propósito, como el de `_mandar`: contar el gasto es
            # para el panel, y la lectura (y la respuesta a la persona) sigue
            # aunque no se pueda.
            registro.warning("no pude anotar el gasto del lector: %s", e)

    def _mandar(self, cuerpo: dict) -> None:
        pedido = urllib.request.Request(
            self.url,
            data=json.dumps(cuerpo).encode("utf-8"),
            method="POST",
            headers={
                "X-Api-Key": self.llave,
                "Content-Type": "application/json",
                "User-Agent": "Studiante-Agente/1.0 (+https://studiante.app)",
            },
        )
        try:
            with self._abrir(pedido, timeout=ESPERA_DEL_GASTO) as respuesta:
                respuesta.read()
        except Exception as e:
            # Tragado a propósito: es la cuenta del panel de costos, no una
            # dependencia del bot. Queda en el log para que se vea si el API
            # deja de recibirla.
            registro.warning("el API no recibió el gasto del lector: %s", e)


def cuerpo_del_gasto(modelo: str, uso: dict | None, error: BaseException | None) -> dict:
    """Lo que se le manda al API por una llamada: números y un código, nada más.

    Los tokens van con el sentido de Google (el `usageMetadata`), que es como
    los cobra el API: la entrada con lo que salió del caché adentro, y la
    salida SIN el razonamiento, que va aparte. LangChain suma el razonamiento a
    `output_tokens`, así que acá se resta; si no, el API lo cobraría dos veces.
    """
    uso = uso if isinstance(uso, dict) else {}
    detalle_entrada = uso.get("input_token_details") or {}
    detalle_salida = uso.get("output_token_details") or {}
    entrada = _entero(uso.get("input_tokens"))
    razonamiento = _entero(detalle_salida.get("reasoning") if isinstance(detalle_salida, dict) else 0)
    cache = _entero(detalle_entrada.get("cache_read") if isinstance(detalle_entrada, dict) else 0)
    return {
        "purpose": "support_reader",
        "provider": "google",
        "model": (modelo or "").strip().removeprefix("models/"),
        "inputTokens": entrada,
        "cachedTokens": min(cache, entrada),
        "outputTokens": max(_entero(uso.get("output_tokens")) - razonamiento, 0),
        "thoughtsTokens": razonamiento,
        "ok": error is None,
        "errorCode": codigo_del_error(error) if error is not None else "",
    }


def codigo_del_error(error: BaseException) -> str:
    """El estado HTTP con el que contestó el proveedor ("402"), si se sabe.

    LangChain envuelve el error de Google en el suyo (`raise … from e`), y el
    estado queda en el de adentro: por eso se recorre la cadena. Sin estado,
    "timeout" o el nombre del error, que en el panel dice bastante más que
    nada.
    """
    visto: set[int] = set()
    actual: BaseException | None = error
    while actual is not None and id(actual) not in visto:
        visto.add(id(actual))
        for valor in (
            getattr(actual, "code", None),
            getattr(actual, "status_code", None),
            getattr(getattr(actual, "response", None), "status_code", None),
        ):
            if isinstance(valor, int) and not isinstance(valor, bool) and 100 <= valor <= 599:
                return str(valor)
        actual = actual.__cause__ or actual.__context__
    if isinstance(error, TimeoutError) or "timeout" in type(error).__name__.lower():
        return "timeout"
    return type(error).__name__[:40]


def _entero(valor) -> int:
    if isinstance(valor, bool):
        return 0
    if isinstance(valor, (int, float)) and valor > 0:
        return int(valor)
    return 0


def _en_otro_hilo(tarea: Callable[[], None]) -> None:
    threading.Thread(target=tarea, name="gasto-lector", daemon=True).start()


def _texto(mensaje) -> str:
    contenido = getattr(mensaje, "content", "")
    if isinstance(contenido, str):
        return contenido
    if isinstance(contenido, list):
        return "".join(
            b.get("text", "") for b in contenido if isinstance(b, dict) and b.get("type") == "text"
        )
    return ""


def _mime_limpio(crudo: str) -> str:
    """"image/jpeg; charset=…" → "image/jpeg"; "audio/ogg; codecs=opus" → "audio/ogg"."""
    return crudo.split(";", 1)[0].strip().lower()


def _mime_por_nombre(nombre: str) -> str:
    if nombre.lower().endswith(".opus") or nombre.lower().endswith(".oga"):
        return "audio/ogg"
    adivinado, _ = mimetypes.guess_type(nombre or "")
    return (adivinado or "").lower()
