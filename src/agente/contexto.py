"""De qué conversación es el mensaje que se está atendiendo ahora.

Existe por un problema concreto: cuando el agente anota un pedido en el MCP,
ese pedido tiene que quedar atado a la conversación de donde salió, para poder
abrir el chat después y leer lo que la persona escribió. Pero el modelo no sabe
el id de la conversación: lo sabe el canal, dos capas más arriba.

Las dos salidas obvias son peores que esta:

  · Escribirlo en el prompt del sistema ("estás atendiendo la conversación
    #42"). Rompe el caché del proveedor, porque el prompt deja de ser idéntico
    entre conversaciones y se paga entero en cada mensaje.
  · Pedirle al modelo que lo pase como argumento. Es un dato que no tiene, así
    que lo inventaría, que es exactamente lo que no queremos en un campo que
    sirve para rastrear.

Con un contextvar el dato viaja solo: lo pone `Agente.responder` antes de
llamar al grafo y lo lee el envoltorio de las tools del MCP al momento de
llamarlas. Es por hilo y por tarea, así que dos conversaciones atendidas a la
vez no se pisan.
"""

from __future__ import annotations

from contextvars import ContextVar

conversacion_actual: ContextVar[str] = ContextVar("conversacion_actual", default="")
canal_actual: ContextVar[str] = ContextVar("canal_actual", default="")
