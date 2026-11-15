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
"""

from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.parse import unquote

from langchain_core.messages import HumanMessage

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
        if self.mime == "application/pdf":
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
    ) -> None:
        self.modelo = modelo
        self.descargar = descargar
        self.instrucciones = instrucciones
        self.tope = tope

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
        respuesta = self.modelo.invoke([pedido])
        texto = _texto(respuesta).strip()
        if not texto:
            raise NoSePuedeLeer("el lector no devolvió nada")
        return texto


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
