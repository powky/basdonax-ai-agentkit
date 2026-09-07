"""La libreta de traspasos.

Chiquita, pero decide dos cosas que se notan en la bandeja: que el motivo que
queda es el que explica cómo empezó todo, y que el aviso no se repita en cada
mensaje siguiente.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agente import traspaso  # noqa: E402


def test_lo_anotado_se_recupera():
    traspaso.pedir("7", "el catálogo no contestó")

    assert traspaso.tomar("7") == "el catálogo no contestó"


def test_se_lee_una_sola_vez():
    """Si quedara pegado, cada mensaje siguiente dejaría la misma nota."""
    traspaso.pedir("8", "un motivo")

    assert traspaso.tomar("8") == "un motivo"
    assert traspaso.tomar("8") == ""


def test_gana_el_primer_motivo():
    """El segundo suele ser consecuencia del primero, y el primero explica más."""
    traspaso.pedir("9", "falló la consulta del catálogo")
    traspaso.pedir("9", "el modelo no pudo generar la respuesta")

    assert traspaso.tomar("9") == "falló la consulta del catálogo"


def test_sin_conversacion_o_sin_motivo_no_anota_nada():
    traspaso.pedir("", "un motivo")
    traspaso.pedir("10", "")

    assert traspaso.tomar("") == ""
    assert traspaso.tomar("10") == ""
