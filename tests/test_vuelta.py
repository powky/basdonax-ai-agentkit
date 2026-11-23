"""Cuándo una conversación de Ian vuelve al bot (vuelta.py).

La regla es la misma que usa el API para la cola del admin: si una se mueve y
la otra no, el admin dice que una conversación espera a Ian mientras el bot ya
la retomó, o al revés.

    pytest
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agente.vuelta import (  # noqa: E402
    autores,
    cambio_de_etiqueta,
    contexto_de_la_vuelta,
    ultima_respuesta_de_ian,
)


def entra(t, texto, id_=None):
    return {"id": id_ or t, "message_type": 0, "created_at": t, "content": texto, "private": False}


def sale(t, texto, marca=None, id_=None):
    m = {"id": id_ or t, "message_type": 1, "created_at": t, "content": texto, "private": False}
    if marca:
        m["content_attributes"] = {marca: True}
    return m


def nota(t, texto):
    return {"id": t, "message_type": 1, "created_at": t, "content": texto, "private": True}


def actividad(t, texto):
    return {"id": t, "message_type": 2, "created_at": t, "content": texto, "private": False}


def traspasada():
    """Lo que hace el bot con un archivo: contesta, deja la nota, pone la etiqueta."""
    return [
        entra(100, "acá está mi pensum"),
        sale(160, "Ya se lo paso a una persona del equipo."),
        nota(161, "Mandó archivos que el agente no puede leer (file). Hay que abrirlos a mano."),
        actividad(162, "Ian Fernández agregó humano"),
    ]


def test_las_lineas_de_las_etiquetas():
    assert cambio_de_etiqueta("Ian Fernández agregó humano") == (True, False)
    assert cambio_de_etiqueta("Ian Fernández agregó pensum-faltante, humano") == (True, False)
    assert cambio_de_etiqueta("Ian Fernández eliminó a humano") == (False, True)
    assert cambio_de_etiqueta("Ian Fernández eliminó a pensum-faltante, humano") == (False, True)
    assert cambio_de_etiqueta("Ian Fernández agregó pensum-faltante") == (False, False)
    assert cambio_de_etiqueta("Ian Fernández agregó humanos") == (False, False)
    assert cambio_de_etiqueta("Ian Fernández added humano, portal") == (True, False)


def test_lo_que_sale_con_la_etiqueta_puesta_es_de_ian():
    mensajes = traspasada() + [sale(500, "Listo, ya lo agregué.")]
    quienes = [q for q, _ in autores(mensajes)]
    assert quienes == ["persona", "bot", "ian"], "la nota y la actividad no cuentan"
    assert ultima_respuesta_de_ian(mensajes) == 500


def test_las_marcas_mandan_sobre_la_etiqueta():
    mensajes = traspasada() + [sale(500, "esto lo mandó el bot", "studiante_bot")]
    assert ultima_respuesta_de_ian(mensajes) is None
    mensajes = [entra(1, "hola"), sale(2, "desde el admin", "studiante_ian")]
    assert ultima_respuesta_de_ian(mensajes) == 2, "lo que manda el admin es de Ian aunque no haya etiqueta"


def test_si_ian_nunca_contesto_no_hay_ultima():
    assert ultima_respuesta_de_ian(traspasada()) is None


def test_despues_de_quitar_la_etiqueta_vuelve_a_ser_del_bot():
    mensajes = traspasada() + [
        sale(500, "Listo."),
        actividad(90000, "Ian Fernández eliminó a humano"),
        sale(90060, "Claro, dime."),
    ]
    assert ultima_respuesta_de_ian(mensajes) == 500
    assert autores(mensajes)[-1][0] == "bot"


def test_el_contexto_cuenta_lo_ultimo_que_se_hablo():
    mensajes = traspasada() + [sale(500, "Listo, ya lo agregué. Búscalo como Mercadotecnia 2019.")]
    contexto = contexto_de_la_vuelta(mensajes)
    assert contexto.startswith("[contexto:")
    assert "Ian: Listo, ya lo agregué." in contexto
    assert "la venía atendiendo Ian, y la persona volvió" in contexto
    assert "Ian, del equipo" not in contexto, "Studiante es una persona: Ian, no «el equipo»"
    assert "La persona: acá está mi pensum" in contexto
    assert "Hay que abrirlos a mano" not in contexto, "las notas internas no se le cuentan"
    assert contexto.rstrip().endswith("]")


def test_sin_mensajes_no_hay_contexto():
    assert contexto_de_la_vuelta([]) == ""


def test_lo_largo_se_corta_en_un_espacio_y_no_parte_un_correo():
    """El «pensum con error» trae la línea del equipo al final: cortado a los
    300 justo en el correo, quedaba «mariafgomez2001@cor…», que ya no tiene
    forma de correo para la máscara."""
    relleno = "Qué está mal: " + "la materia no aparece en el cuatrimestre " * 6 + "y tampoco sale en la app "
    correo = "mariafgomez2001@correo.com"
    texto = relleno + correo + " · Ref. K7Q2-9XMD"
    assert texto.index(correo) < 300 < texto.index(correo) + len(correo), "el corte cae en el correo"

    contexto = contexto_de_la_vuelta([entra(100, texto)])

    assert "mariafgomez" not in contexto and "@cor" not in contexto
    linea = next(l for l in contexto.splitlines() if l.startswith("La persona:"))
    assert linea.endswith("en la app…") and len(linea) <= len("La persona: ") + 301


def test_desde_que_el_bot_marca_lo_que_sale_sin_marca_es_de_ian():
    from agente.vuelta import MARCAS_DESDE

    despues = sale(MARCAS_DESDE + 60, "hola, soy Ian")
    despues["sender"] = {"id": 1, "type": "user"}
    assert ultima_respuesta_de_ian([entra(MARCAS_DESDE, "hola"), despues]) == MARCAS_DESDE + 60

    antes = sale(MARCAS_DESDE - 60, "esto lo decía la etiqueta")
    antes["sender"] = {"id": 1, "type": "user"}
    assert ultima_respuesta_de_ian([antes]) is None
