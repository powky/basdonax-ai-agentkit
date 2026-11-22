"""Los datos personales no llegan al modelo (privacidad.py) y DeepSeek por el API.

Ninguno sale a la red: el pedido que arma ChatOpenAI lo recibe un transporte de
mentira (httpx.MockTransport), que contesta como contestaría el proxy del API.
Así se mira el JSON EXACTO que saldría hacia DeepSeek.

    pytest
"""

from __future__ import annotations

import asyncio
import json
import re
import socket
import sys
import unicodedata
from pathlib import Path

import httpx
import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import StructuredTool

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agente.agente import Agente  # noqa: E402
from agente.config import RAIZ, Config, ErrorDeConfiguracion  # noqa: E402
from agente.contexto import personales_actuales  # noqa: E402
from agente.memoria import ram  # noqa: E402
from agente.modelos import crear_modelo, listar_modelos, modelo_deepseek, olvidar_modelos  # noqa: E402
from agente.privacidad import (  # noqa: E402
    NOTA_PARA_EL_MODELO,
    DatosPersonales,
    Mascara,
    nombre_de_la_respuesta,
    nombres_presentados,
)

URL_API = "https://api.ejemplo.test/api/v1"
LLAVE = "llave-del-soporte-de-prueba"

# Lo que escribe la persona: la ficha de la app arriba y sus datos a mano.
MENSAJE = (
    "Hola 👋 Quiero reportar un problema en Studiante.\n\n"
    "Equipo: App v2.3.1 (26) · OTA a0078ce · ios 26.6 · iPhone 12 Pro Max · someone@icloud.com · Ref. X4RT-77QM\n\n"
    "Mi problema: soy JUAN perez, mi matrícula es 20181234, mi cédula 001-1234567-8, "
    "en la app soy @juanp y mi cel es 809-555-1234. No me carga el récord desde el 2026-11-14."
)

# Lo que devuelve la herramienta: también trae datos.
RESULTADO_DE_LA_HERRAMIENTA = (
    "Cuenta de juan.perez@gmail.com (@juanp), matrícula 20181234, a nombre de Juan Pérez, "
    "teléfono +1 (809) 555-1234."
)

# Nada de esto puede aparecer en lo que sale hacia el modelo. Los nombres se
# comparan sin tildes ni mayúsculas.
PROHIBIDOS = [
    "someone@icloud.com", "juan.perez@gmail.com", "juan", "perez", "20181234",
    "001-1234567-8", "1234567", "juanp", "809-555-1234", "8095551234", "(809) 555-1234",
    "x4rt-77qm", "x4rt77qm",
]


def plano(texto: str) -> str:
    sin = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in sin if not unicodedata.combining(c)).lower()


def sin_datos(cuerpo: dict) -> None:
    texto = plano(json.dumps(cuerpo, ensure_ascii=False))
    for prohibido in PROHIBIDOS:
        assert prohibido not in texto, f"salió {prohibido!r} hacia el modelo"


def respuesta_de_chat(mensaje: dict, id_="chatcmpl-1", terminar="stop") -> dict:
    return {
        "id": id_,
        "object": "chat.completion",
        "created": 0,
        "model": "deepseek-v4-flash",
        "choices": [{"index": 0, "message": {"role": "assistant", **mensaje}, "finish_reason": terminar}],
        "usage": {"prompt_tokens": 120, "completion_tokens": 30, "total_tokens": 150},
    }


class ProxyFalso:
    """El proxy del API, de mentira: anota cada pedido y contesta en orden.

    Cada respuesta es una función del cuerpo que llegó, porque los marcadores
    los elige la máscara: el "modelo" usa los que ve, como haría el de verdad.
    """

    def __init__(self, *respuestas):
        self.respuestas = list(respuestas)
        self.pedidos: list[httpx.Request] = []
        self.cuerpos: list[dict] = []

    def __call__(self, pedido: httpx.Request) -> httpx.Response:
        cuerpo = json.loads(pedido.content)
        self.pedidos.append(pedido)
        self.cuerpos.append(cuerpo)
        return httpx.Response(200, json=self.respuestas.pop(0)(cuerpo))

    def modelo(self, max_tokens=1024):
        transporte = httpx.MockTransport(self)
        return modelo_deepseek(
            LLAVE,
            "deepseek-flash",
            max_tokens,
            URL_API,
            http_client=httpx.Client(transport=transporte),
            http_async_client=httpx.AsyncClient(transport=transporte),
        )


def marcador(cuerpo: dict, categoria: str, rol: str = "user") -> str:
    """El primer marcador de esa categoría en los mensajes de ese rol."""
    for m in cuerpo["messages"]:
        if m["role"] == rol:
            encontrado = re.search(rf"\[{categoria}_\d+\]", m.get("content") or "")
            if encontrado:
                return encontrado.group(0)
    raise AssertionError(f"no hay ningún {categoria} en los mensajes de {rol}")


@pytest.fixture
def personas():
    """Lo que el webhook sabe de quién escribe: su contacto de Chatwoot."""
    datos = DatosPersonales()
    datos.sumar_contacto({"name": "Juan Pérez", "phone_number": "+18095551234", "email": ""})
    marca = personales_actuales.set(datos)
    yield datos
    personales_actuales.reset(marca)


def agente_deepseek(modelo, herramientas) -> Agente:
    """Un agente igual al de producción: el prompt de verdad y el grafo de verdad."""
    a = Agente.__new__(Agente)
    a.config = Config(
        proveedor="deepseek",
        modelo="deepseek-flash",
        api_key=LLAVE,
        max_tokens=1024,
        memoria_mensajes=20,
        prompt_sistema=RAIZ / "prompts/sistema.md",
        prompt_guia=RAIZ / "prompts/guia-app.md",
        studiante_api_url=URL_API,
    )
    a.modelo = modelo
    a.checkpointer = ram()
    a.herramientas = herramientas
    a.grafo = a._construir_grafo()
    return a


# -- la máscara, sin modelo ----------------------------------------------------


def test_ida_y_vuelta_deja_el_texto_igual():
    mascara = Mascara([("NOMBRE", "Juan Pérez")])
    texto = (
        "Juan Pérez, correo juan.perez@gmail.com, cel +1 809-555-1234, cédula 001-1234567-8, "
        "matrícula 20181234, usuario @juanp, Ref. X4RT-77QM."
    )
    tapado = mascara.tapar(texto)

    assert tapado == (
        "[NOMBRE_1] [NOMBRE_2], correo [CORREO_1], cel [TELEFONO_1], cédula [CEDULA_1], "
        "matrícula [NUMERO_1], usuario @[USUARIO_1], Ref. [REF_1]."
    )
    assert mascara.destapar(tapado) == texto


def test_el_mismo_dato_lleva_el_mismo_marcador():
    mascara = Mascara([("NOMBRE", "José Pérez"), ("TELEFONO", "+18095551234")])
    tapado = mascara.tapar("JOSE escribe desde 809-555-1234; josé pérez, a@b.com y otra vez A@B.com y 8095551234")

    assert tapado == "[NOMBRE_1] escribe desde [TELEFONO_1]; [NOMBRE_1] [NOMBRE_2], [CORREO_1] y otra vez [CORREO_1] y [TELEFONO_1]"
    # El nombre vuelve como está en su contacto, no como lo gritó hoy.
    assert mascara.destapar("Hola, [NOMBRE_1]") == "Hola, José"


def test_los_nombres_van_por_palabra_entera():
    mascara = Mascara([("NOMBRE", "Ana Luz")])
    assert mascara.tapar("Ana, mañana voy a Banana Anabel con luz") == "[NOMBRE_1], mañana voy a Banana Anabel con [NOMBRE_2]"


def test_lo_que_no_es_de_nadie_queda():
    texto = (
        "App v2.3.1 (26) · OTA a0078ce · ios 26.6 · iPhone 12 Pro Max. Desde el 2026-11-14, "
        "el 14/11/2026 y el 14-11-2026, periodo 2023-2024, índice 3.42 con 98 créditos, MAT101."
    )
    assert Mascara().tapar(texto) == texto


def test_el_usuario_no_se_confunde_con_el_correo():
    assert Mascara().tapar("ana@uasd.edu.do y @ana_23") == "[CORREO_1] y @[USUARIO_1]"


def test_telefonos_de_todas_las_formas():
    mascara = Mascara()
    for numero in ("809-555-1234", "(829) 555 1234", "+1 849.555.1234", "18095551234", "+34 612 345 678", "8095551234"):
        assert mascara.tapar(f"mi cel {numero}.") .startswith("mi cel [TELEFONO_"), numero
    assert mascara.tapar("40212345678") == "[CEDULA_1]"
    assert mascara.tapar("ID 1234567") == "ID [NUMERO_1]"


def test_los_datos_conocidos_cortan_en_el_guion_bajo_y_los_digitos():
    """`\\b` cuenta el guion bajo y los dígitos como parte de la palabra: así
    «juan_perez» o «juan2001» se llevaban el nombre del contacto entero."""
    mascara = Mascara([("NOMBRE", "Juan Pérez")])

    assert mascara.tapar("mi usuario es juan_perez") == "mi usuario es [NOMBRE_1]_[NOMBRE_2]"
    assert mascara.tapar("juan2001 y 2001juan") == "[NOMBRE_1]2001 y 2001[NOMBRE_1]"
    # Entre letras sigue siendo palabra entera.
    assert mascara.tapar("Juana y Perezoso") == "Juana y Perezoso"


def test_telefonos_con_cualquier_separador():
    """iOS copia de Contactos con un espacio y un guion que no se rompen; la
    gente escribe barras, guiones con espacios o guiones bajos."""
    formas = [
        "+1 (809) 555\u20111234",
        "809\u00a0555\u00a01234",
        "809\u2013555\u20131234",
        "809\u2011555\u20111234",
        "809 - 555 - 1234",
        "809/555/1234",
        "809_555_1234",
        "809  555  1234",
        "(809)\u00a0555\u20111234",
    ]
    for forma in formas:
        # Por su forma, aunque no se sepa de quién es.
        assert Mascara().tapar(f"mi cel {forma} ok") == "mi cel [TELEFONO_1] ok", forma
    conocido = Mascara([("TELEFONO", "+18095551234")])
    for forma in [*formas, "8 0 9 5 5 5 1 2 3 4", "809 . 555 . 1234"]:
        # El de su contacto, por sus dígitos: siempre el mismo marcador.
        assert conocido.tapar(f"es el {forma}") == "es el [TELEFONO_1]", forma
    assert Mascara().tapar("cédula 001\u20111234567\u20118") == "cédula [CEDULA_1]"
    assert Mascara([("CEDULA", "00112345678")]).tapar("la 001 1234567 - 8") == "la [CEDULA_1]"
    # Lo que separan las barras y los guiones largos y no es de nadie, queda.
    for texto in ("el 14 / 11 / 2026", "periodo 2023 \u2013 2024", "2023/2024", "créditos 3, 4, 3"):
        assert Mascara().tapar(texto) == texto


def test_correos_escritos_a_las_apuradas():
    """Con un espacio junto a la arroba, después del punto o sin el final: la
    primera parte, que suele ser el nombre, también se tapa."""
    for texto in (
        "correo jperez2001 @gmail.com",
        "correo juanperez@gmail. com",
        "correo juanperez@gmail",
        "correo juan @ hotmail.com",
        "correo juan@uasd. edu.do",
    ):
        tapado = Mascara().tapar(texto)
        assert tapado == "correo [CORREO_1]", texto
    # Un @usuario sigue siendo un usuario, y lo que sigue al correo no se lo lleva.
    assert Mascara().tapar("mi usuario es @juan.perez.") == "mi usuario es @[USUARIO_1]."
    assert Mascara().tapar("es @juan y escribe a ana@gmail.com. Gracias") == "es @[USUARIO_1] y escribe a [CORREO_1]. Gracias"


ENLACES_DE_PLAN = [
    # Tapados por forma eran un teléfono, una Ref. y una matrícula: el modelo
    # tenía que copiar el marcador adentro del enlace para que volviera entero.
    "https://studiante.app/l/p/uasd/IEMM/000012-2026",
    "https://studiante.app/l/p/cef/MDAECEF/MDAE-2026",
    "https://studiante.app/l/p/uce/6320023/6320-023",
    "https://studiante.app/l/p/ucsd/ARQ/8212211-2025",
    "https://studiante.app/l/p/pucmm/LENFE",
]


def test_el_enlace_de_un_plan_llega_entero_al_modelo():
    """El MCP del catálogo trae el enlace de cada plan y el bot se lo manda a la
    persona: adentro van solo códigos del catálogo, y no se tapan."""
    for enlace in ENLACES_DE_PLAN:
        for texto in (
            enlace,
            f"Este es tu plan: {enlace}\nTócalo desde tu teléfono.",
            f"({enlace})",
            f"{enlace}.",
            '{"total":1,"rows":[{"plan":"x","link":"' + enlace + '"}]}',
        ):
            assert Mascara().tapar(texto) == texto, texto
        # También en el resultado de la herramienta y en lo que ya contestó.
        mensajes = [ToolMessage(f'{{"link":"{enlace}"}}', tool_call_id="c1"), AIMessage(f"Este es tu plan: {enlace}")]
        assert [m.content for m in Mascara().tapar_mensajes(mensajes, nota=False)] == [m.content for m in mensajes]
    # Afuera del enlace, el mismo código sí se tapa: la excepción es el enlace.
    assert Mascara().tapar("el plan 000012-2026") == "el plan [TELEFONO_1]"
    assert Mascara().tapar("MDAE-2026") == "[REF_1]"


def test_lo_que_va_en_un_enlace_de_plan_sin_serlo_se_tapa_igual():
    """La excepción no sirve para pasar un dato personal colgado del enlace."""
    base = "https://studiante.app/l/p/uasd/LPSC"
    casos = {
        # Pegado detrás, después de un espacio o en la búsqueda.
        "https://studiante.app/l/p/uce/6320023/6320-023 8095551234": "https://studiante.app/l/p/uce/6320023/6320-023 [TELEFONO_1]",
        f"{base}/202510 juan@gmail.com": f"{base}/202510 [CORREO_1]",
        f"{base}/202510?ref=8095551234": f"{base}/202510?ref=[TELEFONO_1]",
        # Con una arroba o un cuarto pedazo ya no es un enlace de plan.
        "https://studiante.app/l/p/uasd/juan@gmail.com": "https://studiante.app/l/p/uasd/[CORREO_1]",
        f"{base}/202510/8095551234": f"{base}/[NUMERO_1]",
        # Un teléfono de aquí o una cédula escrita como tal no son un código.
        "https://studiante.app/l/p/uasd/8095551234": "https://studiante.app/l/p/uasd/[TELEFONO_1]",
        f"{base}/001-1234567-8": f"{base}/[CEDULA_1]",
        f"{base}/18295551234": f"{base}/[TELEFONO_1]",
    }
    for texto, tapado in casos.items():
        assert Mascara().tapar(texto) == tapado, texto
    # Lo que se sabe de la persona se tapa aunque esté adentro.
    conocido = Mascara([("TELEFONO", "+18095551234"), ("NOMBRE", "Lpsc Pérez")])
    assert conocido.tapar("https://studiante.app/l/p/uasd/X/809-555-1234") == "https://studiante.app/l/p/uasd/X/[TELEFONO_1]"
    assert conocido.tapar(f"{base}/202510") == "https://studiante.app/l/p/uasd/[NOMBRE_1]/202510"


def test_destapa_lo_que_el_modelo_escribio_distinto():
    mascara = Mascara([("NOMBRE", "Juan")])
    mascara.tapar("Juan, a@b.com")

    assert mascara.destapar("[NOMBRE_1] NOMBRE_1 [nombre_1] [Nombre 1] [CORREO_1] [EMAIL_1] [Correo_1") == (
        "Juan Juan Juan Juan a@b.com a@b.com a@b.com"
    )


def test_un_marcador_inventado_no_le_llega_a_la_persona():
    mascara = Mascara([("NOMBRE", "Juan")])
    mascara.tapar("Juan")

    assert mascara.destapar("¡Hola [NOMBRE_7]! Listo. [NOMBRE_3], ¿algo más? Tu cel (TELEFONO_2) quedó.") == (
        "¡Hola! Listo. ¿algo más? Tu cel quedó."
    )
    assert mascara.destapar("Hola [NOMBRE_1], ¿cómo estás?") == "Hola Juan, ¿cómo estás?"


def test_el_prompt_del_sistema_no_se_tapa_por_forma_ni_por_nombres():
    """Lo escribe Ian: sus ejemplos tienen que quedar como están."""
    mascara = Mascara([("NOMBRE", "Domingo Ana"), ("CORREO", "domingo@gmail.com")])
    sistema = "Santo Domingo. Escribir «@Ana» no la menciona. Ref. K7Q2-9XMD. 8095551234. domingo@gmail.com"

    assert mascara.tapar(sistema, en_el_sistema=True) == (
        "Santo Domingo. Escribir «@Ana» no la menciona. Ref. K7Q2-9XMD. 8095551234. [CORREO_1]"
    )


def test_quien_se_presenta_queda_tapado_en_toda_la_conversacion():
    assert nombres_presentados("hola, me llamo maría josé y estudio en la UASD") == ["maría josé"]
    assert nombres_presentados("Soy de Santiago. soy estudiante. Soy Ana Pérez, gracias") == ["Ana Pérez"]
    assert nombres_presentados("Mi nombre es Pedro") == ["Pedro"]

    mascara = Mascara()
    tapados = mascara.tapar_mensajes(
        [
            SystemMessage("Eres el soporte."),
            AIMessage("¿Cómo te llamas?"),
            HumanMessage("me llamo maría josé"),
            HumanMessage("María, como dije"),
        ]
    )

    assert [m.content for m in tapados[1:]] == ["¿Cómo te llamas?", "me llamo [NOMBRE_1] [NOMBRE_2]", "[NOMBRE_1], como dije"]


def test_la_respuesta_a_como_te_llamas_es_un_nombre():
    """El bot pregunta el nombre y la gente contesta "Juan", sin «me llamo»."""
    for respuesta, nombre in [
        ("juan carlos", "juan carlos"),
        ("Hola! Yaneris 😊", "Yaneris"),
        ("Me llamo Ana, gracias", "Ana"),
        ("Pedro Martínez, gracias", "Pedro Martínez"),
        ("prefiero no decirlo", ""),
        ("después te digo", ""),
        ("no me carga el récord, ¿qué hago?", ""),
        ("mi matrícula es 20181234", ""),
        # Con una cola: se queda lo de antes de la coma o del conector.
        ("María Fernanda, de la UNAPEC", "María Fernanda"),
        ("Juan y tú?", "Juan"),
        ("Juan, y tú?", "Juan"),
        ("Pedro Martínez, estudiante de la PUCMM", "Pedro Martínez"),
        ("juan perez de la uasd", "juan perez"),
        ("Hola, buenas! Ana 😊", "Ana"),
        ("me dicen Mafe", "Mafe"),
        # El apellido compuesto sigue; la sigla de la universidad no.
        ("María de los Ángeles", "María de los Ángeles"),
        ("Juan de la Cruz", "Juan de la Cruz"),
        ("Juan de la PUCMM", "Juan"),
        # Lo que no es un nombre sigue sin serlo.
        ("¿Quién eres?", ""),
        ("Ayer intenté entrar y no pude", ""),
        ("Quería saber si funciona", ""),
        ("3 veces intenté", ""),
        ("Hola, buenas", ""),
        ("jaja ok", ""),
    ]:
        assert nombre_de_la_respuesta(respuesta) == nombre, respuesta

    mascara = Mascara()
    tapados = mascara.tapar_mensajes(
        [
            HumanMessage("no me sale el pensum"),
            AIMessage("Ya lo reviso. Por cierto, ¿cómo te llamas?"),
            HumanMessage("Yaneris"),
            HumanMessage("Yaneris otra vez"),
        ],
        nota=False,
    )

    assert [m.content for m in tapados] == [
        "no me sale el pensum",
        "Ya lo reviso. Por cierto, ¿cómo te llamas?",
        "[NOMBRE_1]",
        "[NOMBRE_1] otra vez",
    ]
    assert mascara.descubiertos == ["Yaneris"]


def test_sin_la_pregunta_una_palabra_suelta_no_es_un_nombre():
    tapados = Mascara().tapar_mensajes([AIMessage("¿Algo más?"), HumanMessage("Gracias")], nota=False)
    assert tapados[1].content == "Gracias"


def test_el_nombre_que_se_guardo_tambien_se_tapa():
    mascara = Mascara()
    pedido = AIMessage("", tool_calls=[{"name": "guardar_nombre", "args": {"nombre": "Yaneris"}, "id": "c1"}])
    tapados = mascara.tapar_mensajes(
        [HumanMessage("Yaneris"), pedido, ToolMessage("Listo, el contacto quedó como Yaneris.", tool_call_id="c1")]
    )

    assert tapados[1].content == "[NOMBRE_1]"
    assert tapados[2].tool_calls[0]["args"] == {"nombre": "[NOMBRE_1]"}
    assert tapados[2].tool_calls[0]["id"] == "c1"
    assert tapados[3].content == "Listo, el contacto quedó como [NOMBRE_1]."
    assert tapados[3].tool_call_id == "c1"
    assert pedido.tool_calls[0]["args"] == {"nombre": "Yaneris"}, "la memoria se queda con el dato real"


def test_destapar_conserva_el_id_el_consumo_y_los_metadatos():
    from langchain_core.outputs import ChatGeneration, ChatResult

    mascara = Mascara([("NOMBRE", "Juan")])
    mascara.tapar("Juan")
    original = AIMessage(
        "Hola [NOMBRE_1]",
        id="run-1",
        tool_calls=[{"name": "guardar_nombre", "args": {"nombre": "[NOMBRE_1]"}, "id": "call_1"}],
        usage_metadata={"input_tokens": 10, "output_tokens": 2, "total_tokens": 12},
        response_metadata={"id": "chatcmpl-1", "model_name": "deepseek-v4-flash"},
    )
    resultado = mascara.destapar_resultado(
        ChatResult(generations=[ChatGeneration(message=original, generation_info={"finish_reason": "stop"})], llm_output={"id": "chatcmpl-1"})
    )

    (generacion,) = resultado.generations
    mensaje = generacion.message
    assert mensaje.content == "Hola Juan" and generacion.text == "Hola Juan"
    assert mensaje.tool_calls == [{"name": "guardar_nombre", "args": {"nombre": "Juan"}, "id": "call_1", "type": "tool_call"}]
    assert mensaje.id == "run-1" and mensaje.usage_metadata["total_tokens"] == 12
    assert mensaje.response_metadata == {"id": "chatcmpl-1", "model_name": "deepseek-v4-flash"}
    assert generacion.generation_info == {"finish_reason": "stop"} and resultado.llm_output == {"id": "chatcmpl-1"}


def test_la_nota_va_al_final_del_prompt_y_una_sola_vez():
    tapados = Mascara().tapar_mensajes([SystemMessage("Eres el soporte."), HumanMessage("hola")])

    assert tapados[0].content == f"Eres el soporte.\n\n{NOTA_PARA_EL_MODELO}"
    assert sum(NOTA_PARA_EL_MODELO in str(m.content) for m in tapados) == 1


def test_las_respuestas_viejas_de_gemini_llegan_como_texto():
    """Gemini dejó listas de bloques con su firma: viaja el texto, tapado."""
    viejo = AIMessage(content=[{"type": "text", "text": "Hola Juan", "extras": {"signature": "abc=="}}])
    (tapado,) = Mascara([("NOMBRE", "Juan")]).tapar_mensajes([viejo], nota=False)

    assert tapado.content == "Hola [NOMBRE_1]"


def test_de_donde_salen_los_datos_conocidos():
    datos = DatosPersonales()
    datos.sumar_contacto(
        {
            "name": "Mari Sánchez 🌸",
            "email": "mari@gmail.com",
            "phone_number": "+18295550000",
            "additional_attributes": {"social_profiles": {"instagram": "mari.sz"}},
        }
    )
    datos.sumar_contacto({"name": "+18095551234"})  # en WhatsApp el nombre puede ser el número
    datos.sumar_mensaje("Equipo: App v2.3.1 (26) · ios 26.6 · otra@icloud.com · Ref. X4RT-77QM\nMe llamo Mari")
    datos.sumar_cuenta(
        {
            "linked": True,
            "username": "marisz",
            "diagnosis": {"email": "cuenta@gmail.com", "honors": {"failed": [{"name": "Matemática"}]}},
        }
    )

    assert sorted(datos.valores()) == sorted(
        [
            ("NOMBRE", "Mari Sánchez 🌸"),
            ("NOMBRE", "Mari"),
            ("CORREO", "mari@gmail.com"),
            ("TELEFONO", "+18295550000"),
            ("USUARIO", "mari.sz"),
            ("CORREO", "otra@icloud.com"),
            ("REF", "X4RT-77QM"),
            ("USUARIO", "marisz"),
            ("CORREO", "cuenta@gmail.com"),
        ]
    ), "«Matemática» es una materia, no una persona; el número del nombre no es un nombre"


# -- DeepSeek por el API: lo que sale de verdad --------------------------------


def test_lo_que_sale_hacia_el_proxy_no_trae_datos_y_vuelve_con_los_reales(personas):
    recibido = []

    def buscar_cuenta(correo: str, nombre: str) -> str:
        """Busca la cuenta de la persona."""
        recibido.append({"correo": correo, "nombre": nombre})
        return RESULTADO_DE_LA_HERRAMIENTA

    def primera(cuerpo):
        # El modelo pide la herramienta con los marcadores que ve, uno sin
        # corchetes: el de verdad a veces los pierde.
        nombre, correo = marcador(cuerpo, "NOMBRE"), marcador(cuerpo, "CORREO")
        argumentos = {"correo": correo, "nombre": f"{nombre.strip('[]')} {nombre}"}
        llamada = {"id": "call_1", "type": "function", "function": {"name": "buscar_cuenta", "arguments": json.dumps(argumentos)}}
        return respuesta_de_chat({"content": None, "tool_calls": [llamada]}, terminar="tool_calls")

    def segunda(cuerpo):
        nombre, telefono = marcador(cuerpo, "NOMBRE"), marcador(cuerpo, "TELEFONO")
        correo_de_la_cuenta = marcador(cuerpo, "CORREO", rol="tool")
        texto = f"Listo, {nombre}: tu cuenta es {correo_de_la_cuenta} y te escribo al {telefono}. [NOMBRE_99]"
        return respuesta_de_chat({"content": texto}, id_="chatcmpl-2")

    proxy = ProxyFalso(primera, segunda)
    herramienta = StructuredTool.from_function(buscar_cuenta)
    agente = agente_deepseek(proxy.modelo(), [herramienta])

    respuesta = agente.responder(MENSAJE, conversacion="42")

    # 1. Lo que salió: dos llamadas, ninguna con un dato.
    assert len(proxy.cuerpos) == 2
    for cuerpo in proxy.cuerpos:
        sin_datos(cuerpo)
    usuario = next(m for m in proxy.cuerpos[0]["messages"] if m["role"] == "user")["content"]
    assert "App v2.3.1 (26) · OTA a0078ce · ios 26.6 · iPhone 12 Pro Max · [CORREO_1] · Ref. [REF_1]" in usuario
    assert "@[USUARIO_1]" in usuario and "desde el 2026-11-14" in usuario
    # La vuelta de la herramienta también se tapó: el pedido y su resultado.
    segunda_vuelta = proxy.cuerpos[1]["messages"]
    pedido = next(m for m in segunda_vuelta if m.get("tool_calls"))
    assert json.loads(pedido["tool_calls"][0]["function"]["arguments"])["correo"].startswith("[CORREO_")
    resultado = next(m for m in segunda_vuelta if m["role"] == "tool")
    assert resultado["tool_call_id"] == "call_1" and "[CORREO_" in resultado["content"]
    # El prompt del sistema viaja con la nota, y los ejemplos del manual quedan.
    sistema = proxy.cuerpos[0]["messages"][0]
    assert sistema["role"] == "system" and sistema["content"].endswith(NOTA_PARA_EL_MODELO)
    assert "Ref. K7Q2-9XMD" in sistema["content"] and '"@Ana"' in sistema["content"]

    # 2. Cómo salió: al proxy del API, con la llave acotada y el tope.
    peticion = proxy.pedidos[0]
    assert str(peticion.url) == f"{URL_API}/agent/support/ai/chat/completions"
    assert peticion.headers["x-api-key"] == LLAVE
    assert proxy.cuerpos[0]["model"] == "deepseek-flash"
    assert proxy.cuerpos[0].get("max_completion_tokens") == 1024 or proxy.cuerpos[0].get("max_tokens") == 1024
    assert not proxy.cuerpos[0].get("stream")
    assert [t["function"]["name"] for t in proxy.cuerpos[0]["tools"]] == ["buscar_cuenta"]

    # 3. Lo que volvió: la herramienta recibió los datos reales, y la persona también.
    assert recibido == [{"correo": "someone@icloud.com", "nombre": "Juan Juan"}]
    assert respuesta.texto == "Listo, Juan: tu cuenta es juan.perez@gmail.com y te escribo al 809-555-1234."
    assert (respuesta.tokens_entrada, respuesta.tokens_salida) == (120, 30)

    # 4. La memoria guarda lo real, con sus ids.
    historial = agente.historial("42")
    assert historial[0].content == MENSAJE
    assert historial[1].tool_calls[0]["id"] == "call_1"
    assert historial[1].tool_calls[0]["args"] == {"correo": "someone@icloud.com", "nombre": "Juan Juan"}
    assert historial[2].tool_call_id == "call_1" and historial[2].content == RESULTADO_DE_LA_HERRAMIENTA
    assert historial[3].response_metadata["id"] == "chatcmpl-2" and historial[3].content == respuesta.texto
    assert historial[3].response_metadata["model_name"] == "deepseek-v4-flash"
    assert historial[3].usage_metadata["input_tokens"] == 120


def test_el_turno_siguiente_vuelve_a_tapar_lo_que_la_memoria_tiene_real(personas):
    proxy = ProxyFalso(
        lambda c: respuesta_de_chat({"content": f"Hola {marcador(c, 'NOMBRE')}"}),
        lambda c: respuesta_de_chat({"content": "Dale"}, id_="chatcmpl-2"),
    )
    agente = agente_deepseek(proxy.modelo(), [])

    assert agente.responder(MENSAJE, conversacion="7").texto == "Hola Juan"
    agente.responder("gracias", conversacion="7")

    sin_datos(proxy.cuerpos[1])
    asistente = [m["content"] for m in proxy.cuerpos[1]["messages"] if m["role"] == "assistant"]
    assert asistente == ["Hola [NOMBRE_1]"], "lo que contestó el modelo vuelve tapado"


def test_el_nombre_que_contesto_no_sale_ni_en_la_llamada_que_lo_guarda():
    """La conversación sin contacto conocido: el nombre llega suelto, y es
    justo el mensaje que va al modelo para que llame a guardar_nombre."""
    datos = DatosPersonales()
    marca = personales_actuales.set(datos)
    guardados = []

    def guardar_nombre(nombre: str) -> str:
        """Guarda el nombre de la persona."""
        guardados.append(nombre)
        return f"Listo, el contacto quedó como {nombre}."

    def guarda(cuerpo):
        ultimo = [m for m in cuerpo["messages"] if m["role"] == "user"][-1]["content"]
        nombre = " ".join(re.findall(r"\[NOMBRE_\d+\]", ultimo))
        llamada = {"id": "call_9", "type": "function", "function": {"name": "guardar_nombre", "arguments": json.dumps({"nombre": nombre})}}
        return respuesta_de_chat({"content": None, "tool_calls": [llamada]}, terminar="tool_calls")

    proxy = ProxyFalso(
        lambda c: respuesta_de_chat({"content": "Te ayudo. Por cierto, ¿cómo te llamas?"}),
        guarda,
        lambda c: respuesta_de_chat({"content": f"Un gusto, {marcador(c, 'NOMBRE')}."}, id_="chatcmpl-3"),
    )
    try:
        agente = agente_deepseek(proxy.modelo(), [StructuredTool.from_function(guardar_nombre)])
        agente.responder("no me carga el pensum", conversacion="5")
        respuesta = agente.responder("juan carlos", conversacion="5")
    finally:
        personales_actuales.reset(marca)

    for cuerpo in proxy.cuerpos:
        sin_datos(cuerpo)
        assert "carlos" not in plano(json.dumps(cuerpo, ensure_ascii=False))
    assert guardados == ["juan carlos"]
    assert respuesta.texto == "Un gusto, juan."
    assert ("NOMBRE", "juan carlos") in datos.valores(), "queda para cuando el mensaje se caiga de la memoria"


def test_el_archivo_con_el_nombre_no_sale_hacia_el_modelo(personas):
    """Sin lector (con DeepSeek no hay), el bot igual acusa recibo del archivo.
    Su nombre, «Juan_Perez_Record.pdf», no tiene forma ni borde de palabra que
    la máscara reconozca: por eso al modelo le llega solo el tipo."""
    from test_chatwoot import ChatwootFalso, evento

    adjunto = {"file_type": "file", "data_url": "https://ws.ejemplo.com/x/Juan_Perez_Record.pdf?v=1"}
    entrante = ChatwootFalso().traducir(evento(texto="", adjuntos=[adjunto]))
    proxy = ProxyFalso(lambda c: respuesta_de_chat({"content": "Recibido, ya lo ve alguien del equipo."}))
    agente = agente_deepseek(proxy.modelo(), [])

    agente.responder(entrante.texto, conversacion="11")

    usuario = [m["content"] for m in proxy.cuerpos[0]["messages"] if m["role"] == "user"]
    assert usuario == ["[adjunto recibido: un PDF]"]
    sin_datos(proxy.cuerpos[0])


def test_el_nombre_con_una_cola_tampoco_sale():
    """«María Fernanda, de la UNAPEC» contesta a «¿cómo te llamas?» con algo
    más: antes se descartaba entera y el nombre salía tal cual."""
    datos = DatosPersonales()
    datos.sumar_contacto({"name": "Mafe 🌸"})
    marca = personales_actuales.set(datos)
    proxy = ProxyFalso(
        lambda c: respuesta_de_chat({"content": "Claro. Por cierto, ¿cómo te llamas?"}),
        lambda c: respuesta_de_chat({"content": f"Un gusto, {marcador(c, 'NOMBRE')}."}, id_="chatcmpl-2"),
    )
    try:
        agente = agente_deepseek(proxy.modelo(), [])
        agente.responder("no me sale el pensum", conversacion="12")
        respuesta = agente.responder("María Fernanda, de la UNAPEC", conversacion="12")
    finally:
        personales_actuales.reset(marca)

    ultimo = [m["content"] for m in proxy.cuerpos[1]["messages"] if m["role"] == "user"][-1]
    assert ultimo == "[NOMBRE_1] [NOMBRE_2], de la UNAPEC"
    assert "maria" not in plano(json.dumps(proxy.cuerpos[1], ensure_ascii=False))
    assert respuesta.texto == "Un gusto, María."


def test_en_vivo_tambien_sale_tapado(personas):
    """responder_en_vivo transmite el grafo: el modelo igual pide la respuesta
    entera, tapada, y la persona la ve destapada."""
    proxy = ProxyFalso(lambda c: respuesta_de_chat({"content": f"Hola {marcador(c, 'NOMBRE')}, ¿qué pasó con [CORREO_1]?"}))
    agente = agente_deepseek(proxy.modelo(), [])

    transmision = agente.responder_en_vivo(MENSAJE, conversacion="9")

    assert transmision.texto() == "Hola Juan, ¿qué pasó con someone@icloud.com?"
    sin_datos(proxy.cuerpos[0])
    assert not proxy.cuerpos[0].get("stream")


def test_el_camino_async_y_el_de_pedazos_tambien_tapan(personas):
    proxy = ProxyFalso(
        lambda c: respuesta_de_chat({"content": f"Hola {marcador(c, 'NOMBRE')}"}),
        lambda c: respuesta_de_chat({"content": f"Chao {marcador(c, 'NOMBRE')}"}, id_="chatcmpl-2"),
    )
    modelo = proxy.modelo()

    asincrona = asyncio.run(modelo.ainvoke([HumanMessage(MENSAJE)]))
    pedazos = list(modelo._stream([HumanMessage(MENSAJE)]))

    assert asincrona.content == "Hola Juan" and asincrona.usage_metadata["input_tokens"] == 120
    assert [p.message.content for p in pedazos] == ["Chao Juan"]
    for cuerpo in proxy.cuerpos:
        sin_datos(cuerpo)


# -- el proveedor y la configuración ---------------------------------------------


def test_crear_el_modelo_y_listarlo_no_toca_la_red(monkeypatch):
    def sin_red(*_, **__):
        raise AssertionError("intentó salir a la red")

    monkeypatch.setattr(socket, "create_connection", sin_red)
    monkeypatch.setattr(socket.socket, "connect", sin_red)
    olvidar_modelos("deepseek")

    assert listar_modelos("deepseek", LLAVE) == [
        {"id": "deepseek-flash", "nombre": "DeepSeek (vía el API de Studiante)", "max_salida": 8192}
    ]
    modelo = crear_modelo("deepseek", LLAVE, "deepseek-flash", 65536, url_api=URL_API + "/")

    from langchain_openai import ChatOpenAI

    assert isinstance(modelo, ChatOpenAI) and type(modelo).__name__ == "ChatOpenAIConMascara"
    assert modelo.openai_api_base == f"{URL_API}/agent/support/ai"
    assert modelo.default_headers == {"X-Api-Key": LLAVE}
    assert modelo.use_responses_api is False and modelo.disable_streaming is True
    assert modelo.max_tokens == 8192, "el MAX_TOKENS alto que quedó de Gemini se recorta"
    # El API corta a DeepSeek a los 90 s y Cloudflare al API a los 100: si el
    # cliente cortara antes, el 504 que dice «no reintentes» no llegaría nunca.
    assert modelo.request_timeout > 100 and modelo.max_retries == 1
    # bind_tools no le saca la máscara: el grafo llama a esto.
    atado = modelo.bind_tools([StructuredTool.from_function(lambda x: x, name="eco", description="eco")])
    assert atado.bound is modelo


def test_deepseek_sin_la_direccion_del_api_no_arranca():
    with pytest.raises(ValueError, match="STUDIANTE_API_URL"):
        crear_modelo("deepseek", LLAVE, "deepseek-flash", 1024)


def test_proveedor_deepseek_usa_la_llave_del_soporte(monkeypatch):
    monkeypatch.setenv("PROVEEDOR", "deepseek")
    monkeypatch.setenv("STUDIANTE_SOPORTE_LLAVE", LLAVE)
    monkeypatch.delenv("MODELO_DEEPSEEK", raising=False)
    monkeypatch.delenv("STUDIANTE_API_URL", raising=False)

    config = Config.desde_entorno()

    assert (config.proveedor, config.api_key, config.modelo) == ("deepseek", LLAVE, "deepseek-flash")
    assert config.studiante_api_url == "https://api.studiante.app/api/v1"

    monkeypatch.setenv("STUDIANTE_SOPORTE_LLAVE", "")
    with pytest.raises(ErrorDeConfiguracion, match="STUDIANTE_SOPORTE_LLAVE"):
        Config.desde_entorno()


# -- el webhook le pasa al modelo quién escribe -----------------------------------


def test_el_webhook_deja_a_mano_quien_escribe(monkeypatch):
    from fastapi.testclient import TestClient

    from agente.web import webhook as modulo
    from test_webhook_adjuntos_y_vuelta import TOKEN, AjustesFijos, Canal

    monkeypatch.setattr(modulo, "catalogo_caido", lambda: False)

    class AgenteQueMira:
        def __init__(self):
            self.vio = []

        def responder_partido(self, texto, conversacion):
            datos = personales_actuales.get()
            self.vio.append(sorted(datos.valores()) if datos is not None else None)
            return ["respuesta"]

    config = Config(
        proveedor="deepseek",
        modelo="deepseek-flash",
        api_key=LLAVE,
        max_tokens=1024,
        memoria_mensajes=20,
        prompt_sistema=RAIZ / "prompts/sistema.md",
        chatwoot_url="https://ws.ejemplo.com",
        chatwoot_token="token",
        chatwoot_webhook_token=TOKEN,
        buffer_segundos=0,
    )
    agente = AgenteQueMira()
    app = modulo.crear_app(config, agente=agente, canal=Canal(), lector=None, ajustes=AjustesFijos())
    evento = {
        "event": "message_created",
        "id": 7,
        "content": "Equipo: App v2.3.1 (26) · ios 26.6 · someone@icloud.com · Ref. X4RT-77QM",
        "message_type": "incoming",
        "sender": {"type": "contact", "name": "Juan Pérez", "phone_number": "+18095551234"},
        "conversation": {"id": 42, "contact_inbox": {"source_id": "18095551234"}, "meta": {"sender": {"name": "Juan Pérez"}}},
    }

    with TestClient(app) as cliente:
        cliente.post(f"/chatwoot/{TOKEN}", json=evento)

    assert agente.vio == [
        sorted(
            [
                ("NOMBRE", "Juan Pérez"),
                ("TELEFONO", "+18095551234"),
                ("CORREO", "someone@icloud.com"),
                ("REF", "X4RT-77QM"),
            ]
        )
    ], "el número del inbox es el mismo teléfono: no se repite"
