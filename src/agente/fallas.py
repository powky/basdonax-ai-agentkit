"""Las fallas que ya reportaron otras personas, para el mensaje que se atiende.

Cuando el portal de una universidad deja de conectar, no escribe una persona:
escriben diez, cada una con el mismo error (el 18/9 fueron doce con el kárdex
de la UASD). El API las cuenta con los mensajes de Chatwoot y las manda en los
ajustes (ver ajustes_soporte.py); acá se arma el renglón que el modelo lee
pegado al mensaje, para que a la tercera persona le diga que ya se sabe en vez
de pasársela a Ian como si fuera la primera.

Solo va cuando el mensaje puede ser de eso: habla de conectar o de un error,
nombra la universidad, o la universidad del contacto es la que falla. A quien
pregunta por su pensum no hay por qué contarle que otra cosa falla.
"""

from __future__ import annotations

import re
import unicodedata

from .ajustes_soporte import FallaConocida

# Cuántas OTRAS personas hacen falta, sin contar a quien escribe.
OTRAS_PERSONAS = 2

_DE_CONEXION = re.compile(
    r"conect|conexi|sincroniz|portal|kardex|record|no me deja (entrar|iniciar)|no carga|error|falla|"
    r"se queda|se quedo|no lee|no abre",
    re.IGNORECASE,
)


def _plano(texto: str) -> str:
    """Sin tildes y en minúsculas, para comparar."""
    sin = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in sin if not unicodedata.combining(c)).lower()


def contexto_de_fallas(
    fallas: tuple[FallaConocida, ...],
    conversacion: str,
    texto: str,
    universidad_del_contacto: str = "",
) -> str:
    """El renglón para el modelo, o "" si no hay nada que contarle."""
    if not fallas:
        return ""
    plano = _plano(texto)
    del_contacto = _plano(universidad_del_contacto).split("·")[0].strip()
    de_conexion = bool(_DE_CONEXION.search(plano))
    lineas = []
    for f in fallas:
        otras = [c for c in f.conversaciones if c != str(conversacion)]
        if len(otras) < OTRAS_PERSONAS:
            continue
        uni = _plano(f.universidad)
        if not (de_conexion or uni in plano or (del_contacto and del_contacto == uni)):
            continue
        linea = f"- {f.universidad}: {len(otras)} personas más en los últimos tres días."
        if f.errores:
            vistos = "; ".join(f"«{t}» ({n})" for t, n in f.errores[:3])
            linea += f" Lo que vieron: {vistos}."
        lineas.append(linea)
    if not lineas:
        return ""
    return (
        "[fallas conocidas: otras personas reportaron hace poco que el portal de "
        "estas universidades no conecta. Es para ti, no se lo leas a la persona]\n"
        + "\n".join(lineas)
    )
