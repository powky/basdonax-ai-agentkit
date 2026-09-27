"""La ficha que manda la app, leída de los formatos reales.

Los textos de acá abajo NO son inventados: son los que arma la app en
`AccountScreen.tsx`, `MissingPensumSheet.tsx`, `DeleteAccountFlow.tsx` y
`FalloPortal.tsx`. Si alguno cambia allá, estos tests son los que avisan.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agente.canales.ficha import leer_ficha  # noqa: E402

REPORTE = (
    "Hola 👋 Quiero reportar un problema en Studiante.\n"
    "\n"
    "Equipo: App v1.5.0 · ios 26.0 · iPhone 17 Pro · ian@studiante.app\n"
    "\n"
    "Mi problema:\n"
    "no me carga el horario desde ayer"
)

PENSUM_FALTANTE = (
    "Hola 👋 No encuentro mi pensum en Studiante y lo necesito 🙏\n"
    "\n"
    "Universidad: UNAPEC\n"
    "Carrera que busco: Mercadotecnia\n"
    "Año o versión del plan (si lo sabes): 2019"
)

PENSUM_CON_ERROR = (
    "Hola 👋 Encontré un error en un pensum de Studiante.\n"
    "\n"
    "Universidad: UASD\n"
    "Carrera: Derecho\n"
    "Plan: DER-2018\n"
    "Qué está mal: falta Derecho Civil III\n"
    "\n"
    "App v1.4.2 · android 15 · SM-A536E · otra@persona.com"
)


def test_lee_el_reporte_de_problema():
    ficha = leer_ficha(REPORTE)
    assert ficha.motivo == "reporte"
    assert ficha.version_app == "1.5.0"
    assert ficha.sistema == "iOS 26.0"
    assert ficha.dispositivo == "iPhone 17 Pro"
    assert ficha.correo == "ian@studiante.app"
    assert ficha.etiquetas == ["reporte"]


def test_lee_el_pensum_faltante():
    ficha = leer_ficha(PENSUM_FALTANTE)
    assert ficha.motivo == "pensum-faltante"
    assert ficha.universidad == "UNAPEC"
    assert ficha.carrera == "Mercadotecnia"
    assert ficha.plan == "2019"


def test_lee_el_pensum_con_error():
    """Acá la línea del equipo va al final, suelta y sin 'Equipo:' delante."""
    ficha = leer_ficha(PENSUM_CON_ERROR)
    assert ficha.motivo == "pensum-con-error"
    assert ficha.universidad == "UASD"
    assert ficha.carrera == "Derecho"
    assert ficha.plan == "DER-2018"
    assert ficha.version_app == "1.4.2"
    assert ficha.sistema == "Android 15"
    assert ficha.dispositivo == "SM-A536E"


def test_equipo_sin_modelo_no_corre_los_datos():
    """La app filtra lo vacío: un equipo sin modelo manda tres partes, no cuatro.

    Por eso la línea se lee por contenido y no por posición — leyéndola por
    posición, el correo terminaría guardado como 'dispositivo'.
    """
    ficha = leer_ficha(
        "Hola 👋 Quiero reportar un problema en Studiante.\n"
        "\n"
        "Equipo: App v1.5.0 · android 14 · alguien@correo.com\n"
    )
    assert ficha.version_app == "1.5.0"
    assert ficha.sistema == "Android 14"
    assert ficha.dispositivo == ""
    assert ficha.correo == "alguien@correo.com"


def test_un_mensaje_normal_no_inventa_nada():
    ficha = leer_ficha("hola, tienen la UASD en la app?")
    assert ficha.vacia()
    assert ficha.atributos() == {}
    assert ficha.etiquetas == []


def test_atributos_solo_lleva_lo_que_hay():
    ficha = leer_ficha(PENSUM_FALTANTE)
    assert ficha.atributos() == {
        "universidad": "UNAPEC",
        "carrera": "Mercadotecnia",
        "plan": "2019",
    }


def test_lee_el_equipo_de_la_2_1_con_build_y_ota():
    """Desde la 2.1.0 la versión trae el build y la OTA va aparte.

    Antes "App v2.1.0 (11)" no casaba con la versión y quedaba guardado como
    el modelo del teléfono, y el modelo de verdad se perdía.
    """
    ficha = leer_ficha(
        "Hola 👋 Quiero reportar un problema en Studiante.\n"
        "\n"
        "Equipo: App v2.1.0 (11) · OTA aae41f9 · ios 18.7.10 · iPhone XR · alguien@correo.com\n"
        "\n"
        "Mi problema: Tengo el índice en 4.0 y ninguna estrella"
    )
    assert ficha.motivo == "reporte"
    assert ficha.version_app == "2.1.0 (11)"
    assert ficha.ota == "aae41f9"
    assert ficha.sistema == "iOS 18.7.10"
    assert ficha.dispositivo == "iPhone XR"
    assert ficha.correo == "alguien@correo.com"
    assert ficha.atributos()["ota"] == "aae41f9"


def test_lee_el_fallo_de_conexion_con_la_universidad():
    """El mensaje del botón "Reportar el fallo", tal como lo arma FalloPortal."""
    ficha = leer_ficha(
        "Hola 👋 No pude conectar el portal de UASD en Studiante.\n"
        "\n"
        "Error: Se quedó en \"Guardando tu horario…\".\n"
        "Equipo: App v2.1.0 (21) · OTA a22f6fb · android 36 · SM-A155M · alguien@correo.com\n"
        "Carrera: PIED5\n"
        "Hora: 2026-09-24 22:45 (UTC-4)"
    )
    assert ficha.motivo == "portal"
    assert ficha.etiquetas == ["portal"]
    assert ficha.version_app == "2.1.0 (21)"
    assert ficha.ota == "a22f6fb"
    assert ficha.dispositivo == "SM-A155M"
    assert ficha.carrera == "PIED5"

