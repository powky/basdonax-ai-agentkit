"""Las conversaciones que hay que dejarle a una persona.

Es una libreta chiquita y a propósito: quien decide el traspaso (una tool que
falló, el modelo que se dio cuenta de que esto no lo resuelve él, el proveedor
que se cayó) no es quien lo ejecuta. El traspaso tiene que pasar **después**
de mandar la respuesta, porque pone la etiqueta que apaga al bot: hacerlo en
el momento dejaría a la persona esperando un mensaje que ya estaba escrito.

Vive en el proceso y no en un contextvar porque quien escribe corre en otro
hilo — `asyncio.to_thread` copia el contexto, así que lo que se cambia adentro
no vuelve.
"""

from __future__ import annotations

_pendientes: dict[str, str] = {}


def pedir(conversacion: str, motivo: str) -> None:
    """Anota que esta conversación la tiene que seguir una persona.

    Si ya había un motivo anotado se queda el primero: es el que explica cómo
    empezó todo, y el segundo suele ser una consecuencia del primero.
    """
    if conversacion and motivo:
        _pendientes.setdefault(conversacion, motivo)


def tomar(conversacion: str) -> str:
    """El motivo del traspaso, si lo hay. Se lee una sola vez.

    Se consume porque el aviso es por respuesta, no por conversación: si
    quedara pegado, cada mensaje siguiente volvería a dejar la misma nota.
    """
    return _pendientes.pop(conversacion, "")
