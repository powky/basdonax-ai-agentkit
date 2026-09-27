"""Leer la ficha que manda la app.

Cuando alguien escribe desde la app —"Reportar un problema", "no encuentro mi
pensum", "este pensum tiene un error"— el mensaje llega con un encabezado que
la app arma sola. Esto lo lee y lo convierte en datos, para que la conversación
en Chatwoot quede clasificada sin que nadie escriba nada a mano.

Los tres formatos, tal como salen de la app:

    Hola 👋 Quiero reportar un problema en Studiante.

    Equipo: App v1.5.0 · ios 26.0 · iPhone 17 Pro · alguien@correo.com

    Mi problema:
    ...

    Hola 👋 No encuentro mi pensum en Studiante y lo necesito 🙏

    Universidad: UNAPEC
    Carrera que busco: Mercadotecnia
    Año o versión del plan (si lo sabes): 2019

    Hola 👋 Encontré un error en un pensum de Studiante.

    Universidad: UNAPEC
    Carrera: Mercadotecnia
    Plan: ADM10
    Qué está mal:
    ...
    App v1.5.0 · ios 26.0 · iPhone 17 Pro · alguien@correo.com

La línea `Equipo:` se lee por CONTENIDO y no por posición: la app arma esa
lista filtrando lo que esté vacío, así que un teléfono sin modelo detectado
manda tres partes en vez de cuatro y por posición se leería todo corrido.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# El separador que usa la app entre los datos del equipo.
_SEPARADOR = "·"

_CORREO = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
# Desde la 2.1.0 la versión lleva el build al lado ("App v2.1.0 (11)") y la
# OTA va en su propia parte ("OTA aae41f9"). Sin esto, "App v2.1.0 (11)" no
# casaba con nada y terminaba guardado como el MODELO del teléfono.
_VERSION_APP = re.compile(r"^App\s+v?(?P<v>[\w.+-]+)(?:\s*\((?P<build>[\w.-]+)\))?$", re.IGNORECASE)
_OTA = re.compile(r"^OTA\s+(?P<ota>[\w-]+)$", re.IGNORECASE)
_SISTEMA = re.compile(r"^(?P<so>ios|android|ipados)\b\s*(?P<version>.*)$", re.IGNORECASE)


@dataclass
class Ficha:
    """Lo que se pudo leer del mensaje. Todo opcional: la gente también escribe
    sin pasar por la app."""

    motivo: str = ""  # reporte | pensum-faltante | pensum-con-error | portal
    version_app: str = ""
    ota: str = ""
    sistema: str = ""
    dispositivo: str = ""
    correo: str = ""
    universidad: str = ""
    carrera: str = ""
    plan: str = ""
    etiquetas: list[str] = field(default_factory=list)

    def vacia(self) -> bool:
        return not any(
            (
                self.motivo,
                self.version_app,
                self.ota,
                self.sistema,
                self.dispositivo,
                self.correo,
                self.universidad,
                self.carrera,
                self.plan,
            )
        )

    def atributos(self) -> dict:
        """Los datos con los nombres que van a los atributos del contacto."""
        pares = {
            "app_version": self.version_app,
            "ota": self.ota,
            "sistema": self.sistema,
            "dispositivo": self.dispositivo,
            "universidad": self.universidad,
            "carrera": self.carrera,
            "plan": self.plan,
        }
        return {k: v for k, v in pares.items() if v}


def leer_ficha(texto: str) -> Ficha:
    """Saca de un mensaje todo lo que la app haya puesto en él."""
    ficha = Ficha()
    if not texto:
        return ficha

    ficha.motivo = _motivo(texto)

    for linea in texto.splitlines():
        linea = linea.strip()
        if not linea:
            continue

        etiqueta, _, valor = linea.partition(":")
        valor = valor.strip()
        clave = etiqueta.strip().lower()

        if clave == "equipo":
            _leer_equipo(valor, ficha)
        elif clave == "universidad":
            ficha.universidad = valor
        elif clave in ("carrera", "carrera que busco"):
            ficha.carrera = valor
        elif clave == "plan" or clave.startswith("año o versión del plan"):
            ficha.plan = valor
        elif _SEPARADOR in linea and not valor:
            # El reporte de error del pensum pega la línea del equipo al final,
            # suelta y sin "Equipo:" delante.
            _leer_equipo(linea, ficha)

    if not ficha.correo:
        encontrado = _CORREO.search(texto)
        if encontrado:
            ficha.correo = encontrado.group(0)

    ficha.etiquetas = [ficha.motivo] if ficha.motivo else []
    return ficha


def _motivo(texto: str) -> str:
    """Qué venía a hacer la persona, según con qué botón abrió el chat."""
    cabeza = texto[:200].lower()
    if "reportar un problema" in cabeza:
        return "reporte"
    if "no encuentro mi pensum" in cabeza:
        return "pensum-faltante"
    if "error en un pensum" in cabeza:
        return "pensum-con-error"
    # El botón "Reportar el fallo" de la pantalla que no pudo conectar la
    # universidad (FalloPortal en la app).
    if "no pude conectar el portal" in cabeza:
        return "portal"
    return ""


def _leer_equipo(valor: str, ficha: Ficha) -> None:
    """Reparte las partes de la línea del equipo según lo que sea cada una."""
    for parte in valor.split(_SEPARADOR):
        parte = parte.strip()
        if not parte:
            continue

        version = _VERSION_APP.match(parte)
        if version:
            build = version.group("build")
            ficha.version_app = f"{version.group('v')} ({build})" if build else version.group("v")
            continue
        ota = _OTA.match(parte)
        if ota:
            ficha.ota = ota.group("ota")
            continue

        sistema = _SISTEMA.match(parte)
        if sistema:
            so = sistema.group("so").lower()
            so = {"ios": "iOS", "ipados": "iPadOS", "android": "Android"}.get(so, so)
            ficha.sistema = f"{so} {sistema.group('version')}".strip()
            continue

        if _CORREO.fullmatch(parte):
            ficha.correo = parte
            continue

        # Lo que queda es el modelo del equipo ("iPhone 17 Pro", "SM-A536E").
        if not ficha.dispositivo:
            ficha.dispositivo = parte
