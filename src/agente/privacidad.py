"""Los datos personales no salen hacia el modelo.

La regla es de Ian y no tiene excepciones: «a DeepSeek no le enviemos PII
nunca». Ni nombres, ni correos, ni teléfonos, ni cédulas, ni matrículas, ni
@usuarios, ni el código «Ref.» de la app. Empleos ya la cumple (el CV va sin
encabezado y con los nombres tapados); esto hace que la cumpla el bot.

Cómo: antes de CADA llamada al modelo, los datos se cambian por marcadores
—[NOMBRE_1], [CORREO_1], [TELEFONO_1]— y en la respuesta se vuelven a poner
los de verdad. La persona lee su nombre; el modelo nunca lo vio.

    memoria (datos reales) → tapar → modelo → destapar → memoria y persona

Lo que importa entender antes de tocar esto:

  · **Se tapa por llamada, no en la memoria.** La memoria de LangGraph guarda
    los datos reales: los necesita la persona, que lee su nombre, y las
    herramientas, que reciben el correo de verdad. Cada llamada arma su propia
    `Mascara` y la tira al terminar. Dentro de una llamada, el mismo dato
    lleva siempre el mismo marcador.
  · **De dónde salen los datos.** De dos lados. Lo que se sabe de quién
    escribe: el contacto de Chatwoot, la ficha de la app, la cuenta de
    Studiante y el nombre que se guardó (`DatosPersonales`, que el webhook
    deja en contexto.py). Y lo que tiene FORMA de dato personal aunque no se
    sepa de quién es: un correo, un teléfono, una cédula, siete dígitos
    seguidos, un @usuario, un «Ref.». Un nombre no tiene forma: el de un
    tercero escrito a mano no se detecta. El de quien escribe sí, cuando se
    presenta («me llamo…», «soy…») o cuando contesta a «¿cómo te llamas?».
  · **El prompt del sistema no se tapa por forma, ni por nombres.** Lo escribe
    Ian y no trae datos de nadie, pero sus ejemplos («@Ana», «Ref. K7Q2-9XMD»)
    vueltos marcadores confundirían al modelo sin proteger a nadie, y un
    estudiante que se llama Domingo dejaría todo el manual hablando de «Santo
    [NOMBRE_1]». Ahí solo se tapan los valores conocidos que no son nombres.
  · **Al modelo le llega texto y nada más.** Las respuestas viejas de Gemini
    quedaron en la memoria como listas de bloques (con la firma de su
    razonamiento adentro); se aplanan al texto que se tapó, así no viaja nada
    que no haya pasado por acá.

El API de Studiante vuelve a tapar los patrones obvios del otro lado: es el
respaldo, no el primer paso.
"""

from __future__ import annotations

import json
import re
import threading
import unicodedata
from dataclasses import dataclass
from functools import cache, lru_cache
from typing import Iterable, Iterator, Literal

from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from .canales.ficha import leer_ficha
from .contexto import personales_actuales

CATEGORIAS = ("NOMBRE", "CORREO", "TELEFONO", "CEDULA", "NUMERO", "USUARIO", "REF")

# Cuál gana cuando dos detecciones se pisan en el mismo lugar y del mismo
# largo. El correo primero: "juan.perez@gmail.com" también trae un nombre y un
# usuario adentro, y taparlos por separado dejaría el dominio a la vista.
_PRIORIDAD = {c: i for i, c in enumerate(("CORREO", "REF", "CEDULA", "TELEFONO", "NUMERO", "USUARIO", "NOMBRE"))}

# Lo que se le agrega al prompt del sistema cuando la máscara está prendida.
# Es fija a propósito: el prompt es el prefijo que el proveedor cachea, y un
# texto que cambiara por conversación lo haría pagar entero cada vez.
NOTA_PARA_EL_MODELO = (
    "## Datos personales\n\n"
    "Los datos personales de esta conversación (nombres, correos, teléfonos, "
    "cédulas, matrículas, usuarios y el código «Ref.» de la app) te llegan "
    "cambiados por marcadores como [NOMBRE_1], [CORREO_1], [TELEFONO_1] o "
    "[USUARIO_1]. El mismo dato lleva siempre el mismo marcador. Cuando "
    "necesites uno —para saludar por su nombre, repetir su correo o pasárselo "
    "a una herramienta— copia el marcador tal cual, con los corchetes: se "
    "cambia por el dato real antes de que la persona lo lea. No inventes "
    "marcadores que no estén en la conversación, no le cuentes a la persona "
    "que existen y nunca le pidas que repita un dato porque lo ves así: ya lo "
    "tenemos."
)

# Las herramientas cuyo argumento ES el nombre de la persona. Lo que el modelo
# guardó con `guardar_nombre` se tapa en el resto de la conversación aunque el
# contacto de Chatwoot todavía no lo traiga (llega recién en el próximo evento).
HERRAMIENTAS_CON_NOMBRE = {"guardar_nombre": "nombre"}


# ---------------------------------------------------------------------------
# Lo que se sabe de quién escribe
# ---------------------------------------------------------------------------


class DatosPersonales:
    """Lo que se sabe de la persona que escribe: lo que no puede llegar al modelo.

    Lo arma el webhook con cada mensaje (el contacto de Chatwoot, la ficha) y
    lo completan las herramientas (la cuenta, el nombre que se guardó). Es un
    objeto que se modifica, y no un valor que se reemplaza, porque las
    herramientas corren con una copia del contexto: un `.set()` hecho ahí no
    vuelve, pero el objeto es el mismo de los dos lados.
    """

    def __init__(self) -> None:
        self._valores: dict[tuple[str, str], str] = {}
        # Las herramientas pueden correr en paralelo, cada una en su hilo.
        self._candado = threading.Lock()

    def sumar(self, categoria: str, valor) -> None:
        if categoria not in CATEGORIAS or not isinstance(valor, str):
            return
        valor = " ".join(valor.split())
        if not valor:
            return
        with self._candado:
            self._valores.setdefault((categoria, _clave(categoria, valor)), valor)

    def valores(self) -> list[tuple[str, str]]:
        with self._candado:
            return [(categoria, valor) for (categoria, _), valor in self._valores.items()]

    def sumar_contacto(self, contacto: dict) -> None:
        """El contacto de Chatwoot: nombre, correo, teléfono y lo que traiga de redes."""
        if not isinstance(contacto, dict):
            return
        # En WhatsApp el nombre puede venir con el número adentro ("+1809…"):
        # sin una letra no es un nombre, y el número ya se tapa por su forma.
        nombre = contacto.get("name")
        if isinstance(nombre, str) and any(c.isalpha() for c in nombre):
            self.sumar("NOMBRE", nombre)
        self.sumar("CORREO", contacto.get("email"))
        self._sumar_telefono(contacto.get("phone_number"))
        identificador = contacto.get("identifier")
        if isinstance(identificador, str):
            self.sumar_por_forma(identificador)
        # Instagram y compañía dejan el usuario en los atributos adicionales,
        # con nombres de clave que cambian entre versiones de Chatwoot.
        self._sumar_por_claves(contacto.get("additional_attributes"), profundidad=2)

    def sumar_cuenta(self, datos: dict) -> None:
        """Lo personal que traiga la cuenta de Studiante (cuenta_soporte.py).

        Hoy el API no manda nombre, correo ni matrícula en el diagnóstico, y
        por eso esto casi nunca suma nada. Está para el día que los mande: sin
        esto, ese día saldrían derecho al modelo. Se mira el primer nivel de la
        respuesta y del diagnóstico, no adentro de las listas: las materias
        también tienen "name", y "Matemática" no es una persona.
        """
        if not isinstance(datos, dict):
            return
        self._sumar_por_claves(datos, profundidad=1)
        self._sumar_por_claves(datos.get("diagnosis"), profundidad=1)

    def sumar_mensaje(self, texto: str) -> None:
        """Lo personal que trae un mensaje: la ficha de la app y quien se presenta.

        Las formas (el correo, el Ref.) se tapan igual en cada llamada. Se
        guardan además porque la memoria del modelo es corta: el mensaje que
        las trajo se cae de la ventana a los veinte mensajes, y el nombre de
        quien dijo «me llamo…» al principio no tiene forma para volver a
        encontrarlo después.
        """
        if not texto:
            return
        self.sumar("CORREO", leer_ficha(texto).correo)
        for m in _REF_CON_ETIQUETA.finditer(texto):
            self.sumar("REF", m.group(1))
        for nombre in nombres_presentados(texto):
            self.sumar("NOMBRE", nombre)

    def sumar_por_forma(self, valor: str) -> None:
        """Un dato suelto sin etiqueta: se decide qué es por cómo se ve."""
        valor = (valor or "").strip()
        if _CORREO.fullmatch(valor):
            self.sumar("CORREO", valor)
        elif len(re.sub(r"\D", "", valor)) >= 7 and not re.search(r"[^\d\s+().-]", valor):
            self._sumar_telefono(valor)
        elif len(valor) >= 5:
            self.sumar("NUMERO", valor)

    def _sumar_telefono(self, valor) -> None:
        if isinstance(valor, str) and len(re.sub(r"\D", "", valor)) >= 7:
            self.sumar("TELEFONO", valor)

    def _sumar_por_claves(self, datos, profundidad: int) -> None:
        if not isinstance(datos, dict) or profundidad <= 0:
            return
        for clave, valor in datos.items():
            if isinstance(valor, dict):
                self._sumar_por_claves(valor, profundidad - 1)
                continue
            categoria = _CATEGORIA_POR_CLAVE.get(re.sub(r"[^a-z]", "", _plegar(str(clave))))
            if categoria and isinstance(valor, str):
                self.sumar(categoria, valor)


# Las claves que dicen qué es un dato, sin mayúsculas, tildes ni guiones.
_CATEGORIA_POR_CLAVE = {
    **dict.fromkeys(
        ("name", "fullname", "firstname", "lastname", "displayname", "givenname",
         "familyname", "nombre", "nombres", "apellido", "apellidos"),
        "NOMBRE",
    ),
    **dict.fromkeys(("email", "correo", "mail"), "CORREO"),
    **dict.fromkeys(("phone", "phonenumber", "telefono", "celular", "mobile", "whatsapp"), "TELEFONO"),
    **dict.fromkeys(
        ("username", "usuario", "handle", "screenname", "instagram", "instagramusername",
         "socialinstagramusername", "socialtelegramusername", "telegram", "tiktok"),
        "USUARIO",
    ),
    **dict.fromkeys(("cedula", "nationalid", "documentid", "documento"), "CEDULA"),
    **dict.fromkeys(("studentid", "matricula", "userid", "idestudiante"), "NUMERO"),
    **dict.fromkeys(("ref", "supportref", "codigoref"), "REF"),
}


def datos_de_la_conversacion() -> list[tuple[str, str]]:
    """Los datos conocidos de la conversación que se atiende, o nada."""
    datos = personales_actuales.get()
    return datos.valores() if datos is not None else []


# ---------------------------------------------------------------------------
# Los nombres
# ---------------------------------------------------------------------------

# Palabras que aparecen en los nombres de contacto y no son de nadie. Se
# tapan igual si están en la conversación como otra cosa; lo que se evita es
# que "Studiante Soporte" o "Ing. Pedro" conviertan la charla en marcadores.
_NO_SON_NOMBRES = frozenset(
    """
    del las los san santo santa the and que con por para una uno app
    hola buenas studiante soporte estudiante universidad whatsapp iphone android
    samsung xiaomi huawei motorola redmi galaxy user usuario cliente contacto
    ing lic dra sra srta prof
    """.split()
)

# Donde termina un nombre que alguien escribió al presentarse.
_CORTAN_EL_NOMBRE = _NO_SON_NOMBRES | frozenset(
    """
    de la el y e o a en es soy me mi yo tu su un estudio estudiante tengo quiero
    necesito desde aqui aca alumno alumna egresado egresada profesor profesora
    nuevo nueva hola gracias porque pero ya
    """.split()
)

_PRESENTACION = re.compile(
    r"\b(?P<cue>me\s+llamo|mi\s+nombre\s+es|nombre\s*:|soy)\s+", re.IGNORECASE
)
_PALABRA = re.compile(r"[^\W\d_]+")


def nombres_presentados(texto: str) -> list[str]:
    """Los nombres de quien se presenta: «me llamo Juan Pérez», «soy Ana».

    «Me llamo» y «mi nombre es» se aceptan en minúscula, porque así escribe
    mucha gente. «Soy» es más traicionero («soy de la UASD», «soy estudiante»):
    ahí el nombre tiene que empezar con mayúscula y no ser una palabra común.
    """
    nombres = []
    for m in _PRESENTACION.finditer(texto or ""):
        exige_mayuscula = m.group("cue").lower() == "soy"
        palabras = []
        posicion = m.end()
        while len(palabras) < 4:
            p = _PALABRA.match(texto, posicion)
            if not p:
                break
            palabra = p.group(0)
            if _plegar(palabra) in _CORTAN_EL_NOMBRE or len(palabra) < 2:
                break
            if exige_mayuscula and not palabras and not palabra[0].isupper():
                break
            palabras.append(palabra)
            # El nombre sigue solo si lo que viene es un espacio y otra palabra:
            # una coma o un salto de línea lo terminan.
            espacio = re.match(r"[ \t]+", texto[p.end():])
            if not espacio:
                break
            posicion = p.end() + espacio.end()
        if palabras:
            nombres.append(" ".join(palabras))
    return nombres


# El bot pregunta el nombre (prompts/sistema.md, «El nombre») y la respuesta
# casi nunca es «me llamo…»: es "Juan" o "juan pérez", suelto. Sin esto, ese
# mensaje —justo el que trae el nombre— saldría derecho al modelo.
_PREGUNTA_EL_NOMBRE = re.compile(
    r"como te llamas|como es tu nombre|cual es tu nombre|tu nombre\b|como te llamo|con quien tengo el gusto"
)

# Lo que rodea un nombre en una respuesta corta y se puede sacar: "Hola, Juan
# 😊 gracias", "me dicen Mafe".
_RELLENO = frozenset(
    """
    hola holaa buenas buenos dias tardes noches claro si ok okay okey dale bueno
    pues gracias saludos bendiciones jaja jajaja perfecto listo es mi nombre me
    llamo soy yo con gusto mucho un placer dicen puedes decirme llamarme
    """.split()
)

# Lo que, si aparece, dice que la respuesta no es un nombre: "prefiero no",
# "después te digo", "no me sale el récord", "¿quién eres?".
_NO_ES_UN_NOMBRE = _CORTAN_EL_NOMBRE | frozenset(
    """
    no prefiero nada ninguno ninguna despues luego ahora todavia aun que para por
    cuando donde como pero tambien puedo ayuda problema error pensum carrera
    materia materias record indice horario sale carga funciona necesito digo
    importa decirlo decir quien quienes eres sos cual cuales disculpa perdon
    mande queria quisiera saber pregunta preguntar consulta estoy esta hay mira
    oye favor porfa porfavor bien mal igual tienes tiene hice intente entrar
    matricula cedula correo numero telefono cel celular cuenta clave contrasena
    ayer hoy manana siempre nunca antes entonces osea mas menos todo todos toda
    algo alguien nadie eso esto esa ese este ahi alli asi tal solo muy poco otra
    otro sigue sigo intento puse pude hago hace hacer ver vi veo
    """.split()
)

# Donde termina una cláusula: lo que viene después de la coma ya no es el
# nombre ("María Fernanda, de la UNAPEC"; "Juan, y tú?").
_FIN_DE_CLAUSULA = re.compile(r"[,.;:!?¿¡()\n]+")

# Las partículas de un apellido compuesto ("de la Cruz", "de los Ángeles").
_PARTICULAS = frozenset("de del la las los".split())


def nombre_de_la_respuesta(texto: str) -> str:
    """El nombre en la respuesta a «¿cómo te llamas?», o "" si no parece uno.

    Se mira solo la primera cláusula que dice algo (la que no es puro saludo)
    y, adentro de ella, lo que hay antes del primer conector: «María Fernanda,
    de la UNAPEC», «Juan y tú?» o «Pedro Martínez, estudiante de la PUCMM»
    son nombres con una cola, y rechazar la respuesta entera por esa cola era
    mandarle el nombre al modelo. Se equivoca para el lado seguro: tapar de
    más se destapa en la respuesta; tapar de menos es un nombre que ya salió.
    Lo que sí la descarta: que empiece con una palabra común («prefiero no»,
    «no me carga»), con un número, o que sea una pregunta sin conector
    («¿quién eres?»).
    """
    presentados = nombres_presentados(texto)
    if presentados:
        return presentados[0]
    texto = texto or ""
    inicio = 0
    for corte in [*_FIN_DE_CLAUSULA.finditer(texto), None]:
        fin = corte.start() if corte else len(texto)
        clausula, antes, despues = texto[inicio:fin], texto[:inicio], corte.group(0) if corte else ""
        inicio = corte.end() if corte else fin
        palabras = re.findall(r"[^\W_]+", clausula)
        while palabras and _plegar(palabras[0]) in _RELLENO:
            palabras.pop(0)
        if palabras:
            # Esta es la cláusula que dice algo: se decide con ella.
            es_pregunta = "?" in despues or "¿" in antes[-2:]
            return _nombre_al_principio(palabras, es_pregunta)
    return ""


def _nombre_al_principio(palabras: list[str], es_pregunta: bool) -> str:
    """Las palabras del principio que forman un nombre, hasta el primer conector."""
    nombre: list[str] = []
    cortado = False
    i = 0
    while i < len(palabras):
        palabra, plegada = palabras[i], _plegar(palabras[i])
        if plegada in _PARTICULAS and nombre:
            # "de la Cruz" sigue el nombre; "de la UNAPEC" y "de la uasd" no:
            # la partícula vale si después viene una palabra con mayúscula que
            # no es una sigla.
            j = i
            while j < len(palabras) and _plegar(palabras[j]) in _PARTICULAS:
                j += 1
            siguiente = palabras[j] if j < len(palabras) else ""
            if siguiente[:1].isupper() and not siguiente.isupper() and _plegar(siguiente) not in _NO_ES_UN_NOMBRE:
                nombre.extend(palabras[i:j])
                i = j
                continue
            cortado = True
            break
        if any(c.isdigit() for c in palabra) or len(palabra) < 2 or plegada in _NO_ES_UN_NOMBRE or plegada in _RELLENO:
            cortado = True
            break
        nombre.append(palabra)
        i += 1
    propias = [p for p in nombre if _plegar(p) not in _PARTICULAS]
    if not 1 <= len(propias) <= 4:
        return ""
    # «Juan y tú?» corta en la "y"; «¿Quién eres?» no corta en nada: entera,
    # una pregunta de más de una palabra no es un nombre.
    if es_pregunta and not cortado and len(propias) > 1:
        return ""
    return " ".join(nombre)


def _partes_del_nombre(nombre: str) -> list[str]:
    """Lo que se busca de un nombre: cada palabra de tres letras o más.

    Por palabra y no el nombre entero, porque la gente escribe "Juan", "juan
    pérez" o "JUAN" según el día; y así el modelo ve [NOMBRE_1] [NOMBRE_2] y
    sabe que para saludar alcanza con el primero. El nombre entero se suma solo
    cuando trae palabras cortas que no se taparían solas ("Li Wu").
    """
    palabras = [p for p in _PALABRA.findall(nombre or "") if _plegar(p) not in _NO_SON_NOMBRES]
    partes = [p for p in palabras if len(p) >= 3]
    if any(len(p) < 3 for p in palabras) and sum(len(p) for p in palabras) >= 4:
        partes.append(" ".join(palabras))
    return partes


# ---------------------------------------------------------------------------
# Las formas
# ---------------------------------------------------------------------------

_CORREO = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")

# El correo escrito a las apuradas en el teléfono: con un espacio junto a la
# arroba («jperez2001 @gmail.com»), después del punto («juan@gmail. com») o sin
# el final («juan@gmail»). Sin esto se tapaba lo de después de la arroba como
# si fuera un @usuario y quedaba a la vista la primera parte, que suele ser el
# nombre. Para no confundirlo con un @usuario, el espacio junto a la arroba se
# acepta solo con los proveedores de siempre, y el del punto, solo antes de un
# final conocido.
_PROVEEDORES_DE_CORREO = r"gmail|googlemail|hotmail|outlook|yahoo|ymail|icloud|live|msn|aol|protonmail|proton|gmx|yandex"
_FINALES_DE_CORREO = r"com|net|org|edu|gob|gov|info|biz|app|dev|io|co|do|es|us|me"
_CORREO_FLOJO = re.compile(
    r"(?<![\w.+-])[\w.+-]*\w"
    rf"(?:[ \t]?@[ \t]?(?:{_PROVEEDORES_DE_CORREO})(?:[ \t]?\.[ \t]?(?:{_FINALES_DE_CORREO}))?"
    rf"|@[\w-]+(?:\.[\w-]+)*[ \t]?\.[ \t]?(?:{_FINALES_DE_CORREO}))"
    r"(?:\.[a-z]{2})?(?![\w-])",
    re.IGNORECASE,
)

# El mismo patrón con que el API lee el código (model/support_link.go).
_REF_CON_ETIQUETA = re.compile(r"(?i)\bref\b\.?\s*:?\s*([0-9a-z]{4}[-\s]?[0-9a-z]{4})\b")
# El código suelto, copiado sin el "Ref.": en mayúsculas, con el guion y con
# letras y números mezclados, que es como lo muestra la app.
_REF_SUELTO = re.compile(r"(?<![\w-])(?=[0-9A-Z-]*\d)(?=[0-9A-Z-]*[A-Z])[0-9A-Z]{4}-[0-9A-Z]{4}(?![\w-])")

# Lo que puede ir entre los dígitos de un teléfono: hasta tres de estos. No
# solo el espacio, el punto y el guion del teclado: iOS copia los números de
# Contactos con un espacio que no se rompe (U+00A0) y un guion que tampoco
# (U+2011), y hay quien escribe «809 - 555 - 1234», «809/555/1234» o
# «809_555_1234». El salto de línea no: juntaría números de renglones
# distintos.
_SEPARADOR = r"(?:[^\S\r\n]|[./_\-‐-―−])"

# Una tira de siete dígitos o más, con separadores sueltos en el medio: un
# teléfono, una cédula, una matrícula. Lo que decide qué es cada una está en
# `_que_numero_es`. Nada de letras pegadas: "OTA a0078ce" no es un número. El
# guion bajo sí puede ir pegado («record_100123456»).
_TIRA = re.compile(
    rf"(?<![^\W_])(?<!@)\+?(?:\(\d{{1,4}}\)|\d)(?:{_SEPARADOR}{{0,3}}(?:\(\d{{1,4}}\)|\d)){{6,}}(?![^\W_])(?!@)"
)

# Un @usuario que no es parte de un correo. Se tapa lo de después de la
# arroba: el modelo ve "@[USUARIO_1]" y entiende que es un usuario.
_ARROBA = re.compile(r"(?<![\w@.])@([A-Za-z0-9_][A-Za-z0-9_.]{0,28}[A-Za-z0-9_])")

# El enlace de un plan que arma el MCP del catálogo (studiante-agent-mcp,
# catalogo.mjs) y que el bot le manda a la persona para que lo toque:
# https://studiante.app/l/p/<universidad>/<carrera>[/<plan>]. Lleva solo
# códigos del catálogo, pero muchos tienen forma de dato personal —
# "000012-2026" pasa por teléfono, "MDAE-2026" por una Ref., "6320023/6320-023"
# por una matrícula—, y tapados así el modelo tenía que copiar el marcador
# adentro del enlace para que volviera entero: 130 de los 1,176 enlaces.
#
# Por eso adentro de uno de estos no se busca por forma, salvo lo que no
# puede ser un código: un teléfono de aquí (809, 829, 849) o una cédula escrita
# como cédula (001-1234567-8), que ningún plan del catálogo tiene. Lo que se
# sabe de la persona —su teléfono, su cédula, su nombre— se tapa igual aunque
# esté adentro. El patrón es el del MCP y nada más: una arroba, un espacio o
# un cuarto pedazo lo dejan de ser, así que un correo o un número pegados
# detrás no viajan colgados del enlace.
_ENLACE_DE_PLAN = re.compile(
    r"https?://(?:www\.)?studiante\.app/l/p/[A-Za-z0-9-]{2,24}"
    r"(?:/[A-Za-z0-9_-][A-Za-z0-9._-]{0,47}){1,2}"
    r"(?![\w./@+-])"
)

_CODIGOS_RD = ("809", "829", "849")
# Con la barra y los guiones largos, que ahora también juntan una tira: una
# fecha no es de nadie y al modelo le sirve.
_ENTRE_FECHA = r"\s?[-./‐-―−]\s?"
_FECHA = re.compile(rf"\d{{4}}{_ENTRE_FECHA}\d{{1,2}}{_ENTRE_FECHA}\d{{1,2}}|\d{{1,2}}{_ENTRE_FECHA}\d{{1,2}}{_ENTRE_FECHA}\d{{4}}")
_AÑOS = re.compile(rf"(?:19|20)\d{{2}}{_ENTRE_FECHA}(?:19|20)\d{{2}}")
_CEDULA = re.compile(rf"\d{{3}}{_SEPARADOR}{{1,3}}\d{{7}}{_SEPARADOR}{{1,3}}\d")


def _que_numero_es(tira: str) -> str | None:
    """Qué es una tira de dígitos, o None si es una fecha o un período.

    Las fechas quedan: "2026-11-14" le sirve al modelo y no es de nadie. Lo
    demás se tapa siempre; el tipo solo cambia el marcador que ve el modelo.
    """
    digitos = re.sub(r"\D", "", tira)
    if len(digitos) < 7 or _FECHA.fullmatch(tira) or _AÑOS.fullmatch(tira):
        return None
    if tira.startswith("+"):
        return "TELEFONO"
    if _CEDULA.fullmatch(tira):
        return "CEDULA"
    if (len(digitos) == 10 and digitos[:3] in _CODIGOS_RD) or (
        len(digitos) == 11 and digitos[0] == "1" and digitos[1:4] in _CODIGOS_RD
    ):
        return "TELEFONO"
    if len(digitos) == 11:
        return "CEDULA"
    if len(digitos) == 10 or "(" in tira:
        return "TELEFONO"
    return "NUMERO"


def _no_es_un_codigo(tira: str) -> bool:
    """Si una tira de dígitos de adentro de un enlace de plan es un teléfono
    de aquí o una cédula escrita como tal: eso no lo tiene ningún código del
    catálogo, y se tapa aunque venga en el enlace."""
    digitos = re.sub(r"\D", "", tira)
    return bool(
        _CEDULA.fullmatch(tira)
        or (len(digitos) == 10 and digitos[:3] in _CODIGOS_RD)
        or (len(digitos) == 11 and digitos[0] == "1" and digitos[1:4] in _CODIGOS_RD)
    )


# ---------------------------------------------------------------------------
# Comparar sin tildes ni mayúsculas
# ---------------------------------------------------------------------------


@lru_cache(maxsize=4096)
def _plegar_letra(c: str) -> str:
    """Una letra sin tilde y en minúscula, y SIEMPRE una sola letra.

    Que sea una sola es lo que permite buscar en el texto plegado y cortar en
    el original con las mismas posiciones.
    """
    base = "".join(x for x in unicodedata.normalize("NFD", c) if not unicodedata.combining(x))
    plegada = base.lower() if len(base) == 1 else c.lower()
    return plegada if len(plegada) == 1 else c


@lru_cache(maxsize=256)
def _plegar(texto: str) -> str:
    # Con caché: el prompt del sistema es el mismo en cada llamada y mide
    # decenas de miles de letras.
    return "".join(map(_plegar_letra, texto))


def _clave(categoria: str, valor: str) -> str:
    """Cuándo dos datos son el mismo, aunque estén escritos distinto."""
    if categoria == "TELEFONO":
        digitos = re.sub(r"\D", "", valor)
        # +1 809… y 809… son el mismo número.
        return digitos[1:] if len(digitos) == 11 and digitos[0] == "1" else digitos
    if categoria in ("CEDULA", "NUMERO") and re.fullmatch(r"[\d\s.()-]+", valor):
        return re.sub(r"\D", "", valor)
    if categoria == "REF":
        return re.sub(r"[-\s]", "", valor).upper()
    if categoria == "USUARIO":
        return _plegar(valor).lstrip("@")
    return " ".join(_plegar(valor).split())


# ---------------------------------------------------------------------------
# La máscara de una llamada
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Tramo:
    inicio: int
    fin: int
    categoria: str
    # Con qué se destapa, si no es lo que dice el texto (ver `tapar`).
    real: str = ""


def _mejor_escrito(nombre: str) -> tuple[bool, bool]:
    """Entre dos formas de escribir el mismo nombre, la que se ve mejor en un
    saludo: con mayúscula y minúsculas antes que todo junto, y con tildes."""
    letras = [c for c in nombre if c.isalpha()]
    mezclado = any(c.isupper() for c in letras) and any(c.islower() for c in letras)
    return mezclado, any(ord(c) > 127 for c in letras)


# Lo que el modelo puede devolver por un marcador: con o sin corchetes, en
# minúscula, con espacio en vez de guion bajo, con la tilde de "teléfono", o
# en inglés. Sin corchetes se exige el guion bajo: "número 2" en una frase no
# es un marcador.
_NOMBRES_DE_MARCADOR = r"NOMBRE|CORREO|TEL[EÉ]FONO|C[EÉ]DULA|N[UÚ]MERO|USUARIO|REF|NAME|EMAIL|PHONE|USER|NUMBER"
_MARCADOR = re.compile(
    rf"\[\s*(?P<a>{_NOMBRES_DE_MARCADOR})[\s_-]*(?P<n>\d{{1,4}})\s*\]"
    rf"|(?<![A-Za-z0-9])\[?(?P<b>{_NOMBRES_DE_MARCADOR})_(?P<m>\d{{1,4}})\]?(?![A-Za-z0-9])",
    re.IGNORECASE,
)
_ALIAS = {"NAME": "NOMBRE", "EMAIL": "CORREO", "PHONE": "TELEFONO", "USER": "USUARIO", "NUMBER": "NUMERO"}


def _con_bordes(valor: str) -> str:
    """Un dato conocido como patrón, con el borde que le toca a cada punta.

    Una punta que es letra corta solo contra otra letra: el guion bajo y los
    dígitos separan, porque «juan_perez», «Juan2001» o «mi user es juan_p»
    traen a Juan adentro, y con `\\b` (que los cuenta como parte de la
    palabra) se escapaban. Una punta que es dígito corta contra otro dígito:
    lo que siga de un número más largo lo tapa la forma. Entre las palabras de
    un nombre, cualquier espacio: un doble espacio o un salto de línea no lo
    esconden.
    """
    cuerpo = r"\s+".join(map(re.escape, valor.split(" ")))
    antes = r"(?<![^\W\d_])" if valor[0].isalpha() else r"(?<!\d)" if valor[0].isdigit() else ""
    despues = r"(?![^\W\d_])" if valor[-1].isalpha() else r"(?!\d)" if valor[-1].isdigit() else ""
    return f"{antes}{cuerpo}{despues}"


class Mascara:
    """Los marcadores de UNA llamada al modelo y el dato real detrás de cada uno."""

    def __init__(self, conocidos: Iterable[tuple[str, str]] = ()) -> None:
        # Lo que se busca tal cual (plegado): valor → (categoría, ¿es nombre?,
        # cómo se escribe).
        self._literales: dict[str, tuple[str, bool, str]] = {}
        # Los teléfonos y cédulas conocidos, por sus dígitos: dígitos → categoría.
        self._por_digitos: dict[str, str] = {}
        # Con nombres (True), sin nombres (False) y el de los dígitos (None).
        self._buscadores: dict[bool | None, re.Pattern | None] = {}
        self._marcadores: dict[tuple[str, str], str] = {}
        self._reales: dict[str, str] = {}
        self._cuantos: dict[str, int] = {}
        # Los nombres que salieron de la conversación y no de lo conocido:
        # quien se llama a sí mismo en un mensaje (ver tapar_mensajes).
        self.descubiertos: list[str] = []
        for categoria, valor in conocidos:
            self.conocer(categoria, valor)

    # -- Qué se tapa ----------------------------------------------------------

    def conocer(self, categoria: str, valor) -> None:
        """Suma un dato que hay que tapar donde sea que aparezca, tal cual."""
        if categoria not in CATEGORIAS or not isinstance(valor, str) or not valor.strip():
            return
        if categoria == "NOMBRE":
            for parte in _partes_del_nombre(valor):
                self._sumar_literal(parte, "NOMBRE")
            return
        valor = valor.strip()
        if categoria == "USUARIO":
            valor = valor.lstrip("@")
            if len(valor) >= 3:
                self._sumar_literal(valor, "USUARIO")
            return
        if categoria == "REF":
            pegado = re.sub(r"[-\s]", "", valor)
            if len(pegado) == 8:
                self._sumar_literal(pegado, "REF")
                self._sumar_literal(f"{pegado[:4]}-{pegado[4:]}", "REF")
            return
        if len(valor) >= 5:
            self._sumar_literal(valor, categoria)
        if categoria in ("TELEFONO", "CEDULA"):
            digitos = re.sub(r"\D", "", valor)
            if categoria == "TELEFONO" and len(digitos) == 11 and digitos[0] == "1":
                # El 1 del país va como prefijo opcional (_buscador_de_digitos).
                digitos = digitos[1:]
            if len(digitos) >= 7 and digitos not in self._por_digitos:
                self._por_digitos[digitos] = categoria
                self._buscadores.pop(None, None)

    def _sumar_literal(self, valor: str, categoria: str) -> None:
        plegado = " ".join(_plegar(valor).split())
        if not plegado:
            return
        anterior = self._literales.get(plegado)
        if anterior is None:
            self._literales[plegado] = (categoria, categoria == "NOMBRE", valor)
            self._buscadores.clear()
        elif _mejor_escrito(valor) > _mejor_escrito(anterior[2]):
            self._literales[plegado] = (anterior[0], anterior[1], valor)

    def _buscador(self, con_nombres: bool) -> re.Pattern | None:
        if con_nombres not in self._buscadores:
            valores = sorted(
                (v for v, (_, es_nombre, _) in self._literales.items() if con_nombres or not es_nombre),
                key=len,
                reverse=True,
            )
            self._buscadores[con_nombres] = (
                re.compile("|".join(map(_con_bordes, valores))) if valores else None
            )
        return self._buscadores[con_nombres]

    def _buscador_de_digitos(self) -> re.Pattern | None:
        """Los teléfonos y cédulas conocidos, por sus dígitos y no por cómo se
        escribieron: el contacto dice +18095551234 y la persona copia
        «+1 (809) 555‑1234» de Contactos, con un guion que no es el del teclado.
        Entre dígito y dígito se acepta cualquier cosa corta que no sea otro
        dígito; al teléfono, además, el +1 o el 1 de adelante."""
        if None not in self._buscadores:
            patrones = []
            for i, (digitos, categoria) in enumerate(sorted(self._por_digitos.items(), key=lambda x: -len(x[0]))):
                cuerpo = r"\D{0,3}".join(digitos)
                prefijo = r"(?:\+?\s?1\D{0,3})?" if categoria == "TELEFONO" else ""
                # El grupo dice la categoría: «TELEFONO_0», «CEDULA_1».
                patrones.append(rf"(?P<{categoria}_{i}>(?<![\d+]){prefijo}{cuerpo}(?!\d))")
            self._buscadores[None] = re.compile("|".join(patrones)) if patrones else None
        return self._buscadores[None]

    # -- Tapar ----------------------------------------------------------------

    def tapar(self, texto: str, en_el_sistema: bool = False) -> str:
        """El texto con cada dato personal cambiado por su marcador."""
        if not isinstance(texto, str) or not texto:
            return texto
        tramos = [] if en_el_sistema else list(_tramos_por_forma(texto))
        buscador = self._buscador(con_nombres=not en_el_sistema)
        if buscador is not None:
            for m in buscador.finditer(_plegar(texto)):
                categoria, es_nombre, escrito = self._literales[" ".join(m.group(0).split())]
                # Un nombre vuelve como lo escribió la persona en su contacto o
                # al presentarse, no como salió en este mensaje: el saludo es
                # "Hola, Juan", aunque hoy haya escrito "JUAN".
                tramos.append(_Tramo(m.start(), m.end(), categoria, escrito if es_nombre else ""))
        digitos = self._buscador_de_digitos()
        if digitos is not None:
            for m in digitos.finditer(texto):
                tramos.append(_Tramo(m.start(), m.end(), m.lastgroup.rsplit("_", 1)[0]))
        if not tramos:
            return texto

        # Cuando dos se pisan gana el que empieza antes, después el más largo:
        # "juan.perez@gmail.com" es un correo, no un nombre con un dominio.
        tramos.sort(key=lambda t: (t.inicio, t.inicio - t.fin, _PRIORIDAD[t.categoria]))
        partes, hasta = [], 0
        for t in tramos:
            if t.inicio < hasta:
                continue
            partes.append(texto[hasta:t.inicio])
            partes.append(self._marcador(t.categoria, texto[t.inicio:t.fin], t.real))
            hasta = t.fin
        partes.append(texto[hasta:])
        return "".join(partes)

    def _marcador(self, categoria: str, valor: str, real: str = "") -> str:
        clave = (categoria, _clave(categoria, valor))
        marcador = self._marcadores.get(clave)
        if marcador is None:
            self._cuantos[categoria] = self._cuantos.get(categoria, 0) + 1
            marcador = f"{categoria}_{self._cuantos[categoria]}"
            self._marcadores[clave] = marcador
            # Lo demás vuelve como se vio la primera vez.
            self._reales[marcador] = real or valor
        return f"[{marcador}]"

    def tapar_valor(self, valor):
        """Lo mismo, adentro de los argumentos de una herramienta."""
        if isinstance(valor, str):
            return self.tapar(valor)
        if isinstance(valor, dict):
            return {k: self.tapar_valor(v) for k, v in valor.items()}
        if isinstance(valor, list):
            return [self.tapar_valor(v) for v in valor]
        return valor

    def tapar_mensajes(self, mensajes: list[BaseMessage], nota: bool = True) -> list[BaseMessage]:
        """Los mensajes como los tiene que ver el modelo. No toca los originales:
        son los de la memoria de LangGraph."""
        # Primero se junta lo que no tiene forma —quien se presentó, quien
        # contestó cómo se llama, el nombre que se guardó— para taparlo en
        # TODOS los mensajes, también en los que vienen antes del que lo trajo.
        pregunto_el_nombre = False
        for mensaje in mensajes:
            if mensaje.type == "human":
                texto = _texto_plano(mensaje.content)
                nombres = [nombre_de_la_respuesta(texto)] if pregunto_el_nombre else nombres_presentados(texto)
                for nombre in filter(None, nombres):
                    self.conocer("NOMBRE", nombre)
                    self.descubiertos.append(nombre)
                # La respuesta es el mensaje que sigue a la pregunta, no todos.
                pregunto_el_nombre = False
            elif mensaje.type == "ai":
                pregunto_el_nombre = bool(_PREGUNTA_EL_NOMBRE.search(_plegar(_texto_plano(mensaje.content))))
            for llamada in getattr(mensaje, "tool_calls", None) or []:
                argumento = HERRAMIENTAS_CON_NOMBRE.get(llamada.get("name"))
                if argumento:
                    self.conocer("NOMBRE", (llamada.get("args") or {}).get(argumento))

        tapados = [self._tapar_mensaje(m) for m in mensajes]
        return _con_la_nota(tapados) if nota else tapados

    def _tapar_mensaje(self, mensaje: BaseMessage) -> BaseMessage:
        cambios: dict = {
            "content": self.tapar(_texto_plano(mensaje.content), en_el_sistema=isinstance(mensaje, SystemMessage))
        }
        if isinstance(mensaje, AIMessage):
            cambios["tool_calls"] = [
                {**llamada, "args": self.tapar_valor(llamada.get("args") or {})}
                for llamada in mensaje.tool_calls
            ]
            cambios["invalid_tool_calls"] = [
                {**llamada, "args": self.tapar(llamada.get("args"))} for llamada in mensaje.invalid_tool_calls
            ]
            cambios["additional_kwargs"] = _cambiar_llamadas_crudas(mensaje.additional_kwargs, self.tapar)
        return mensaje.model_copy(update=cambios)

    # -- Destapar -------------------------------------------------------------

    def destapar(self, texto: str) -> str:
        """El texto con los datos reales en lugar de los marcadores.

        Un marcador que el modelo inventó —uno que no existe en esta llamada—
        se saca: no hay nada real que poner, y "[NOMBRE_7]" no le puede llegar
        a la persona.
        """
        if not isinstance(texto, str) or not texto:
            return texto
        inventado = False

        def cambiar(m: re.Match) -> str:
            nonlocal inventado
            nombre = _plegar((m.group("a") or m.group("b"))).upper()
            categoria = _ALIAS.get(nombre, nombre)
            real = self._reales.get(f"{categoria}_{int(m.group('n') or m.group('m'))}")
            if real is None:
                inventado = True
                return ""
            return real

        salida = _MARCADOR.sub(cambiar, texto)
        return _prolijar(salida) if inventado else salida

    def destapar_valor(self, valor):
        if isinstance(valor, str):
            return self.destapar(valor)
        if isinstance(valor, dict):
            return {k: self.destapar_valor(v) for k, v in valor.items()}
        if isinstance(valor, list):
            return [self.destapar_valor(v) for v in valor]
        return valor

    def destapar_mensaje(self, mensaje: BaseMessage) -> BaseMessage:
        """La respuesta del modelo con los datos reales: el texto y los
        argumentos de cada herramienta, que necesitan el correo de verdad."""
        cambios: dict = {"content": self._destapar_contenido(mensaje.content)}
        if isinstance(mensaje, AIMessage):
            cambios["tool_calls"] = [
                {**llamada, "args": self.destapar_valor(llamada.get("args") or {})}
                for llamada in mensaje.tool_calls
            ]
            cambios["invalid_tool_calls"] = [
                {**llamada, "args": self.destapar(llamada.get("args"))} for llamada in mensaje.invalid_tool_calls
            ]
            cambios["additional_kwargs"] = _cambiar_llamadas_crudas(mensaje.additional_kwargs, self.destapar)
            if isinstance(mensaje.additional_kwargs.get("reasoning_content"), str):
                cambios["additional_kwargs"]["reasoning_content"] = self.destapar(
                    mensaje.additional_kwargs["reasoning_content"]
                )
        # model_copy y no un mensaje nuevo: se conservan el id, el consumo de
        # tokens y los metadatos del proveedor.
        return mensaje.model_copy(update=cambios)

    def _destapar_contenido(self, contenido):
        if isinstance(contenido, str):
            return self.destapar(contenido)
        if isinstance(contenido, list):
            return [
                {**b, "text": self.destapar(b["text"])}
                if isinstance(b, dict) and isinstance(b.get("text"), str)
                else self.destapar(b) if isinstance(b, str) else b
                for b in contenido
            ]
        return contenido

    def destapar_resultado(self, resultado: ChatResult) -> ChatResult:
        return ChatResult(
            generations=[
                ChatGeneration(message=self.destapar_mensaje(g.message), generation_info=g.generation_info)
                for g in resultado.generations
            ],
            llm_output=resultado.llm_output,
        )


def _tramos_por_forma(texto: str) -> Iterator[_Tramo]:
    if "studiante.app/l/p/" in texto:
        for enlace in _ENLACE_DE_PLAN.finditer(texto):
            for m in _TIRA.finditer(enlace.group(0)):
                if _no_es_un_codigo(m.group(0)):
                    yield _Tramo(enlace.start() + m.start(), enlace.start() + m.end(), _que_numero_es(m.group(0)))
        # Y el resto del enlace se cambia por un carácter que ninguna forma
        # usa, del mismo largo para no mover las posiciones: adentro no se
        # tapa nada más, y lo que venga afuera («…/6320-023 8095551234») se
        # busca solo, sin juntarse con los dígitos del enlace.
        texto = _ENLACE_DE_PLAN.sub(lambda m: "\0" * len(m.group(0)), texto)
    for m in _CORREO.finditer(texto):
        yield _Tramo(m.start(), m.end(), "CORREO")
    for m in _CORREO_FLOJO.finditer(texto):
        yield _Tramo(m.start(), m.end(), "CORREO")
    for m in _REF_CON_ETIQUETA.finditer(texto):
        yield _Tramo(m.start(1), m.end(1), "REF")
    for m in _REF_SUELTO.finditer(texto):
        yield _Tramo(m.start(), m.end(), "REF")
    for m in _TIRA.finditer(texto):
        categoria = _que_numero_es(m.group(0))
        if categoria:
            yield _Tramo(m.start(), m.end(), categoria)
    for m in _ARROBA.finditer(texto):
        yield _Tramo(m.start(1), m.end(1), "USUARIO")


def _texto_plano(contenido) -> str:
    """El texto de un mensaje, sea un string o una lista de bloques.

    Solo los bloques de texto: lo que no es texto (la firma del razonamiento
    de Gemini, una imagen) no tiene por qué viajar, y si viajara lo haría sin
    pasar por la máscara.
    """
    if isinstance(contenido, str):
        return contenido
    if isinstance(contenido, list):
        return "".join(
            b if isinstance(b, str) else b.get("text", "")
            for b in contenido
            if isinstance(b, str) or (isinstance(b, dict) and b.get("type") == "text")
        )
    return ""


def _cambiar_llamadas_crudas(extra: dict, cambiar) -> dict:
    """Los pedidos de herramienta en el formato crudo del proveedor.

    ChatOpenAI manda los de `tool_calls` (los de LangChain) cuando hay, y si no
    los que estén en `additional_kwargs`: los dos pasan por la máscara.
    """
    salida = dict(extra or {})
    if isinstance(salida.get("tool_calls"), list):
        salida["tool_calls"] = [_cambiar_funcion(c, cambiar) for c in salida["tool_calls"]]
    if isinstance(salida.get("function_call"), dict):
        salida["function_call"] = _cambiar_funcion({"function": salida["function_call"]}, cambiar)["function"]
    return salida


def _cambiar_funcion(llamada, cambiar):
    if not isinstance(llamada, dict) or not isinstance(llamada.get("function"), dict):
        return llamada
    funcion = dict(llamada["function"])
    argumentos = funcion.get("arguments")
    if isinstance(argumentos, str):
        # Vienen como JSON en un string: se cambia adentro y se vuelve a armar,
        # que poner un correo a mano en el medio puede romper las comillas.
        try:
            funcion["arguments"] = json.dumps(_recorrer(json.loads(argumentos), cambiar), ensure_ascii=False)
        except ValueError:
            funcion["arguments"] = cambiar(argumentos)
    return {**llamada, "function": funcion}


def _recorrer(valor, cambiar):
    if isinstance(valor, str):
        return cambiar(valor)
    if isinstance(valor, dict):
        return {k: _recorrer(v, cambiar) for k, v in valor.items()}
    if isinstance(valor, list):
        return [_recorrer(v, cambiar) for v in valor]
    return valor


def _con_la_nota(mensajes: list[BaseMessage]) -> list[BaseMessage]:
    """Le avisa al modelo de los marcadores, al final del prompt del sistema."""
    for i, mensaje in enumerate(mensajes):
        if isinstance(mensaje, SystemMessage):
            texto = f"{mensaje.content}\n\n{NOTA_PARA_EL_MODELO}" if mensaje.content else NOTA_PARA_EL_MODELO
            return [*mensajes[:i], mensaje.model_copy(update={"content": texto}), *mensajes[i + 1:]]
    return [SystemMessage(NOTA_PARA_EL_MODELO), *mensajes]


def _prolijar(texto: str) -> str:
    """Lo que queda después de sacar un marcador inventado: "Hola , ¿cómo
    estás?" vuelve a ser "Hola, ¿cómo estás?"."""
    texto = re.sub(r"\(\s*\)", "", texto)
    texto = re.sub(r"(?<=\S)[ \t]{2,}", " ", texto)
    texto = re.sub(r"[ \t]+(?=[,.;:!?)\]])", "", texto)
    # La coma del vocativo que quedó huérfana: "Listo. , ¿algo más?".
    texto = re.sub(r"([.!?¿¡:;])[ \t]*,", r"\1", texto)
    texto = re.sub(r"(?m)^[ \t]*,[ \t]*", "", texto)
    return re.sub(r"(?m)[ \t]+$", "", texto)


# ---------------------------------------------------------------------------
# El modelo con la máscara puesta
# ---------------------------------------------------------------------------


@cache
def con_mascara(clase: type) -> type:
    """Una subclase del modelo de LangChain que tapa los datos en CADA llamada.

    Subclase y no un envoltorio por fuera, porque el grafo no llama al modelo:
    llama a lo que devuelve `bind_tools()`, y eso es una copia atada al modelo
    original. Pisando `_generate` (y sus parientes) la máscara viaja adentro
    del modelo y sigue puesta después de `bind_tools()` y dentro de LangGraph.

    Sirve para cualquier proveedor de LangChain; hoy se usa solo con DeepSeek.
    """

    class ConMascara(clase):  # type: ignore[misc, valid-type]
        # Sin pedazos: destapar en vivo no se puede, porque un marcador puede
        # llegar partido entre dos pedazos ("[NOMB" + "RE_1]"), y lo que ya
        # salió no se corrige. Con esto LangChain pide la respuesta entera
        # también cuando el grafo transmite en vivo (responder_en_vivo).
        disable_streaming: bool | Literal["tool_calling"] = True

        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            mascara, tapados = _preparar(messages)
            resultado = super()._generate(tapados, stop=stop, run_manager=run_manager, **kwargs)
            return mascara.destapar_resultado(resultado)

        async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
            mascara, tapados = _preparar(messages)
            resultado = await super()._agenerate(tapados, stop=stop, run_manager=run_manager, **kwargs)
            return mascara.destapar_resultado(resultado)

        # Con disable_streaming nadie debería llegar a estos dos. Están para que
        # una versión nueva de LangChain, o alguien que los llame a mano, no
        # encuentre un camino sin máscara: salen por la misma llamada tapada,
        # en un solo pedazo.
        def _stream(self, messages, stop=None, run_manager=None, **kwargs):
            kwargs.pop("stream", None)
            yield _un_pedazo(self._generate(messages, stop=stop, run_manager=run_manager, **kwargs))

        async def _astream(self, messages, stop=None, run_manager=None, **kwargs):
            kwargs.pop("stream", None)
            yield _un_pedazo(await self._agenerate(messages, stop=stop, run_manager=run_manager, **kwargs))

    ConMascara.__name__ = ConMascara.__qualname__ = f"{clase.__name__}ConMascara"
    return ConMascara


def _preparar(mensajes: list[BaseMessage]) -> tuple[Mascara, list[BaseMessage]]:
    """La máscara de esta llamada y los mensajes ya tapados.

    Los nombres que aparecieron en la charla se suman a lo conocido de la
    conversación: la ventana de memoria es corta, y dentro de veinte mensajes
    el «me llamo Juan» ya no va a estar para reconocer al próximo "Juan".
    """
    mascara = Mascara(datos_de_la_conversacion())
    tapados = mascara.tapar_mensajes(mensajes)
    datos = personales_actuales.get()
    if datos is not None:
        for nombre in mascara.descubiertos:
            datos.sumar("NOMBRE", nombre)
    return mascara, tapados


def _un_pedazo(resultado: ChatResult):
    """La respuesta entera como el único pedazo de una transmisión."""
    from langchain_core.messages import AIMessageChunk
    from langchain_core.messages.tool import tool_call_chunk
    from langchain_core.outputs import ChatGenerationChunk

    generacion = resultado.generations[0]
    mensaje = generacion.message
    pedazo = AIMessageChunk(
        content=mensaje.content,
        id=mensaje.id,
        additional_kwargs={k: v for k, v in mensaje.additional_kwargs.items() if k != "tool_calls"},
        response_metadata=dict(mensaje.response_metadata),
        usage_metadata=getattr(mensaje, "usage_metadata", None),
        tool_call_chunks=[
            tool_call_chunk(
                name=llamada["name"],
                args=json.dumps(llamada["args"], ensure_ascii=False),
                id=llamada.get("id"),
                index=i,
            )
            for i, llamada in enumerate(getattr(mensaje, "tool_calls", None) or [])
        ],
    )
    return ChatGenerationChunk(message=pedazo, generation_info=generacion.generation_info)
