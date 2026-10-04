# Cómo se usa la app

Este es el manual de la versión **2.2.0**, la que está en las tiendas. Úsalo
cuando alguien está perdido y hay que guiarlo, o cuando reporta algo que parece
un fallo. No lo recites: dale **solo el pedazo que necesita**, en pasos cortos,
uno por línea. Si algo de acá no responde su pregunta, no lo estires: es mejor
pasarlo a una persona que improvisar un paso que no existe.

La regla de siempre vale también acá: di **"sincronización automática"** o
**"conectar tu universidad"**. Nunca nombres el portal ni expliques de dónde
salen los datos. Los textos entre comillas son los que la persona ve en
pantalla: úsalos tal cual para que los reconozca.

## Versiones

- La versión de las tiendas es la **2.2.0**. En la línea "Equipo" de los
  mensajes que vienen de la app ves la suya (por ejemplo "App v2.2.0 (18)").
- Si tiene una **1.x, 2.0.x o 2.1.x**, lo primero es que actualice desde App
  Store o Google Play: muchos fallos ya están resueltos ahí, y las tutorías
  solo existen desde la 2.2.0.
- La app también recibe arreglos por dentro, sin pasar por la tienda. Cerrarla
  del todo y volver a abrirla hace que tome el último.

## Cómo está organizada

Abajo hay tres pestañas:

- **Horario**: las clases de cada día, los amigos, las alertas, el calendario,
  los apuntes de cada materia y, debajo de cada clase, sus tutores.
- **Pensum**: las materias por cuatrimestre, la sincronización con su
  universidad, el índice y la trayectoria.
- **Cuenta**: su perfil (foto, @usuario, índice, estrellas, amigos), el avance
  de carrera, el perfil vocacional, **"Hazte tutor"**, la ayuda y el botón
  **"Configuración"**.

En **iPad y tablets Android** la app se reparte en dos columnas cuando el
aparato está en horizontal.

## Entrar y crear la cuenta

1. En la bienvenida: **"Continuar con correo"**, o con **Apple** (solo en
   iPhone) o **Google**. El mismo camino sirve para crear la cuenta o entrar.
2. Con correo, llega un **código de 6 dígitos** que se escribe en "Verifica tu
   correo". Ya no se usa un enlace.
3. Elige su universidad y su carrera, su @usuario y, si quiere, su foto.

**"No me llega el código."** Que revise spam o promociones y que el correo esté
bien escrito (en esa pantalla está "Cambiar correo"). Pasado un minuto puede
tocar "Reenviar código". Si dice "Código inválido o expirado", que pida uno
nuevo. Si habla de un **enlace**, tiene una versión vieja: que actualice.

## Correo, empezar de cero y borrar la cuenta

Todo está en **Cuenta → Configuración**:

- **Cambiar el correo**: "Correo" → escribe el nuevo → le llega un código →
  "Confirmar". No pierde nada. Si entró con Google o Apple, el correo no se
  puede cambiar: es el de esa cuenta.
- **Empezar de cero** sin perder la cuenta: "Zona de peligro" → "Borrar mis
  datos".
- **Eliminar la cuenta**: "Zona de peligro" → "Eliminar cuenta". No se puede
  deshacer. Antes de irse la app le pregunta por qué, y varias razones se
  resuelven sin borrar (correo equivocado, empezar de cero, pensum que falta).
- **@usuario**: "Usuario". Se puede cambiar una vez cada 14 días.

## La sincronización automática

Copia de su universidad las materias aprobadas y en curso, las notas, el índice
y el horario. **No todas las universidades la tienen**: búscalo con
`list_universities` (el campo `sincronizacion`). Donde no hay, la persona marca
sus materias a mano y el índice no aparece.

**Cómo se conecta:**

1. Pestaña **Pensum** → arriba, **"Conectar"** con las siglas de su
   universidad (por ejemplo "Conectar UASD"). También está en la columna del
   índice, "Conectar".
2. La primera vez sale "Antes de conectar", que explica qué pasa con sus datos
   → **"Entendido, conectar"**.
3. Entra con su usuario y contraseña **de la universidad**, en la página de la
   propia universidad. **Studiante no ve ni guarda su contraseña**, y tú nunca
   se la pides.
4. Al terminar, "Tu récord está al día" con lo que se marcó.

**Solo el horario:** pestaña Horario → "Agrega tu horario" → "Traerlo de mi
universidad".

**Actualizar:** nada se actualiza solo; cada vez lo inicia la persona. En el
Pensum, el mismo botón pasa a decir **"Actualizar"** con las siglas. Lo ideal es
actualizar cuando la universidad publica las notas de cada cuatrimestre.

**Notas recién publicadas (UASD y UNICARIBE).** Estas universidades publican la
nota final unos días antes de pasarla al récord. Desde la 2.2.0, al actualizar,
la materia que ya tiene nota publicada sale aprobada con su nota aunque el récord
todavía no la tenga. El **índice** sí espera a que la universidad lo actualice.
En las demás universidades la nota entra cuando la universidad la pasa al
récord.

## El pensum

**Marcar materias.** Cada materia se toca para cambiarle el estado, y el ciclo
es siempre el mismo:

- pendiente → **tócala** → en curso (con el chip "En curso")
- en curso → **tócala** → aprobada (verde y tachada)
- aprobada → **tócala** → vuelve a pendiente

Con sincronización esto se marca solo. A mano, se marca según el estado real.

- **Todo un cuatrimestre de una vez**: el botón "Aprobar" en el encabezado de
  ese cuatrimestre.
- **Prerrequisitos**: si intenta poner en curso una materia sin haber aprobado
  lo que pide, la app se lo avisa ("Para cursarla primero debes aprobar…") y
  puede ponerla en curso de todos modos.
- **Electivas**: en el hueco de la electiva, "Elegir" → escoge la materia →
  "Confirmar selección". Si su universidad no la ofrece: "No la ofrecen —
  contar como aprobada".
- **Convalidadas**: se marcan como aprobadas; no hay un estado aparte. Con
  sincronización deberían llegar aprobadas solas. Si no, es un reclamo de datos:
  pásalo a una persona.
- **Notas a mano: no se puede.** Las notas solo llegan con la sincronización.
  Si lo pide, anótalo como feature.

**Dos vistas**, arriba del pensum:

- **Lista**: el pensum completo, cuatrimestre por cuatrimestre.
- **Trayectoria**: el avance en un anillo, la fecha estimada de graduación y la
  ruta, con el cuatrimestre actual marcado "Estás aquí".

**En qué cuatrimestre dice que va.** No lo escribe nadie: lo deduce de lo que
está marcado. Es el cuatrimestre con **más materias en curso**. Si no tiene
ninguna en curso, es el último donde tiene algo aprobado, o el siguiente si ese
ya está completo. Si le sale uno equivocado, casi siempre es porque tiene en
curso materias de otro cuatrimestre, o porque le falta marcar las que está
cursando ahora. Marcándolas bien, se corrige solo.

**Ayudante de selección.** Para el que no sabe qué inscribir: sugiere la carga
ideal, primero lo atrasado y después lo que más materias desbloquea.

## Índice, honores y estrellas

**El índice es el que publica su universidad** y llega con la sincronización.
Studiante **no lo calcula** con lo que la persona marca a mano. Se ve en la
columna del índice del Pensum y en Cuenta. Tocándolo sale su historia por
cuatrimestre, las horas que ponderan, cuándo se actualizó y el botón
"Actualizar".

Si no le aparece, es una de estas:

- **Su universidad no tiene sincronización**: el índice no puede aparecer.
- **No ha conectado su universidad**: dice "—" con "Conectar".
- **La universidad tiene una retención o una evaluación pendiente** (ver
  "Casos que ya conocemos" más abajo).

**"Mi índice está mal."** Es el número que publicó su universidad la última vez
que actualizó. Si ya le salieron notas nuevas, que toque "Actualizar". Si
después de actualizar sigue distinto al de su universidad, pásalo a una persona
con su universidad y los dos números.

**Honores.** Siguen el reglamento de cada universidad, y son una **proyección**:
quien otorga el honor al graduarse es la universidad. Hacen falta tres cosas:

- Que su universidad esté entre las que tienen tabla de honores en la app:
  UASD, UAPA, UNICARIBE, PUCMM, UTESA, UNPHU, O&M, UNAPEC, UNIBE, INTEC, ITLA,
  UNICDA, IEESL, UFHEC, UNIREMHOS, UCNE, UCSD, ISFODOSU, ISA y UCATEBA.
- Que tenga índice, o sea, que haya conectado su universidad.
- Que **no tenga ninguna materia reprobada** en la carrera, aunque la haya
  repetido y aprobado después. Es la regla de los reglamentos.

Si falta cualquiera de las tres, el honor no sale en ningún lado, tampoco en el
widget. Cuando sale, está en Cuenta → "Avance de carrera" ("Vas por…") y junto
al índice.

**Estrellas.** Una estrella es una materia aprobada con la nota más alta que
puede dar su universidad: **95 o más** si la nota viene en número, o la letra
más alta (A+, o A donde la escala termina en A). Las notas de 90 en adelante se
ven doradas. Para tener estrellas hace falta la **nota**, que solo llega con la
sincronización. Una materia marcada a mano, o que llegó como "AP", no tiene nota
y no puede tener estrella.

## El horario

Si está vacío dice **"Aún no tienes horario"**, con **"Agregar con IA"** y
**"Agregar manualmente"**. Con horario ya puesto, lo mismo se abre desde
**"Actualizar"**, arriba en el Horario.

"Agregar con IA" abre **"Agrega tu horario"**:

- **"Directo de mi universidad"** (la tarjeta de arriba): la sincronización,
  solo el horario, donde su universidad la tiene.
- **"Captura"**, **"Foto"** o **"PDF o Excel"**: adjunta su horario. Hasta 8
  archivos, y puede escribir un detalle opcional. Toca la flecha y la app lo
  lee ("Encontrando tus materias", "Ordenando días y horas"…). Al terminar sale
  **"Revisa lo que encontré"** para corregir antes de guardar. Los archivos se
  procesan y se descartan.
- Se pueden hacer **5 lecturas al día**. Pasado eso: "Llegaste al límite de
  lecturas de horario por hoy…": que lo intente mañana o lo llene a mano.
- Si la lectura falla: "No pudimos leerlo", con "Intentar de nuevo" y "Cambiar
  archivos". Una captura nítida del horario de su universidad es lo que mejor
  funciona.

Algunas personas todavía ven la pantalla anterior, con "Traerlo de mi
universidad", "Tomar foto", "Subir del carrete" y "Subir documento": funciona
igual.

Una clase a mano se agrega desde el menú del horario → "Agregar clase":
materia, profesor, edificio, aula, días y horas.

Si se cambia a una carrera de **otra universidad**, la app pregunta qué hacer
con el horario viejo: "Traerlo de …", "Borrarlo" o "Dejarlo así".

**Apuntes.** Cada clase tiene sus apuntes: notas y recordatorios con fecha y
aviso. Si cambia o vuelve a importar su horario, sus apuntes no se pierden: al
final del horario aparecen en **"Apuntes de materias fuera del horario"**.

## Alertas antes de clase

Ya existen:

1. Pestaña Horario → **"Alertas"** (también en Configuración → "Alertas de
   clase").
2. Enciende **"Avisarme de mis clases"** y elige cuándo: "Al empezar la clase",
   "15 minutos antes", "30 minutos antes" o "1 hora antes". Puede marcar varias.
3. Si quiere, el **"Repaso por la mañana"**: un resumen de las clases del día a
   la hora que elija.

Necesitan el permiso de notificaciones. Si no le llegan, revisa con la persona
que las alertas estén encendidas, que las notificaciones de Studiante estén
permitidas en los ajustes del teléfono y que sus clases tengan día y hora: una
clase sin hora no puede avisar.

## El horario en el calendario del teléfono

Ya existe:

1. Pestaña Horario → **"Calendario"** (también en Configuración → "Calendario
   del teléfono").
2. Enciende **"Poner mis clases en el calendario"** y elige en cuál.

Pide acceso completo al calendario. Las clases quedan como eventos de cada
semana y se actualizan solas cuando cambia el horario. No suenan: para los
avisos están las alertas de clase.

## Widgets

Ya existen desde la 2.1.0: **"Horario de hoy"** y **"Avance de carrera"**.

- **iPhone**: mantener presionada la pantalla de inicio → el botón "+" (o
  "Editar" → "Añadir widget") → buscar Studiante. También van en la pantalla
  bloqueada: mantenerla presionada → "Personalizar" → la pantalla bloqueada →
  añadir widget.
- **Android**: mantener presionada la pantalla de inicio → "Widgets" → buscar
  Studiante. Desde la 2.2.0 también hay **"Horario · bloqueo"** y **"Avance ·
  bloqueo"** para la pantalla bloqueada, pero solo en teléfonos con **Android
  16** que ya traen los widgets en la pantalla bloqueada; se agregan desde la
  propia pantalla bloqueada, no desde la de inicio.

Si dice "Abre Studiante", que abra la app una vez para que se llene. El widget
enseña lo mismo que la app: si en la app no hay índice ni honor, en el widget
tampoco.

## Amigos

- **Dónde**: pestaña Horario → **"Amigos"**.
- **Agregar**: "Agregar" y luego buscarlo por **nombre o @usuario** (busca
  mientras se escribe), enseñar su código QR, escanear el de otra persona, o
  compartir su enlace de invitación. Quien abre ese enlace y toca "Agregar como
  amigo" queda como su amigo de una vez. Si alguien no sale buscando, puede que
  haya apagado "Aparecer en la búsqueda": que se agreguen con el código.
- **Qué ven**: en el horario, qué amigos van a su misma clase y quiénes están
  libres en sus horas libres, y en el perfil, su avance.
- **Privacidad**: en Amigos → "Privacidad" (o Configuración → "Quién ve tu
  perfil"). Para cada dato elige "Todos", "Amigos", "Elegir…" (solo algunos) o
  "Nadie". Ahí también está "Aparecer en la búsqueda". El índice nunca lo ve
  un desconocido.
- **Bloquear o reportar**: desde el perfil de esa persona.

**"Dice que un amigo está en mi clase y no es así."** La app considera que es la
misma clase cuando coinciden el día, la hora y la materia, afinando con el aula
o la sección cuando las tiene. Si su universidad no da el aula ni la sección,
dos secciones de la misma materia a la misma hora se pueden confundir.
Explícaselo y anótalo como bug con su universidad.

## Tutorías

Existen desde la **2.2.0**. Son estudiantes que dan tutorías de las materias que
dominan; el estudiante les escribe directo por WhatsApp. **Studiante no cobra
comisión ni intermedia**: el precio, el horario y el lugar los acuerdan ellos.

### Buscar un tutor

1. Pestaña **Horario** → debajo de cada clase hay un botón: **"N tutores de
   {área}"**, o **"Buscar tutor de {área}"** si todavía no hay. También está en
   los apuntes de esa materia.
2. Sale **"Tutores de {área}"**, con los tutores **de su universidad**: si son
   virtuales o presenciales, sus recomendaciones y su descripción.
3. **"Escribir por WhatsApp"** abre WhatsApp con un mensaje ya escrito.

- **"Todavía no hay tutores de {área} en {universidad}"**: nadie la da todavía.
  Saldrán ahí cuando alguien empiece.
- **El área está mal**: abajo, "¿No es de {área}? Cambiar". Si elige "Ninguna
  de estas", ese botón desaparece de la clase.
- **No le sale el botón**: o tiene una versión anterior a la 2.2.0 (que
  actualice), o esa materia no tiene área de tutoría.
- **Recomendar**: unos días después de escribirle a un tutor le llega
  "¿Recomiendas a {nombre}?". Solo recomiendan quienes le escribieron desde
  Studiante, y nadie ve quién respondió.
- **El orden**: "Nadie paga por salir primero": los tutores rotan y el orden
  cambia cada día.

### Hacerse tutor

1. Cuenta → **"Hazte tutor"** (también en Configuración → "Tutorías", o en la
   lista de tutores → "Quiero ser tutor").
2. Elige las **áreas** que enseña ("¿Qué áreas enseñas?"), en qué
   **universidades** (la suya viene puesta) y llena **"Tu perfil de tutor"**:
   - una descripción de 20 a 280 caracteres, **sin teléfonos, correos, enlaces
     ni @usuarios**;
   - su **WhatsApp**, que tiene que ser de RD (809, 829 o 849);
   - si da tutorías virtuales, presenciales o ambas.
3. Paga con una **suscripción mensual del App Store o de Google Play**. **El
   primer mes es gratis** la primera vez.

**Precio.** El plan no se elige: la app pone el más barato que cubre las áreas y
universidades que marcó, y le enseña el precio antes de pagar. Va desde
**US$9.99 al mes** (Básico) hasta US$59.99 (Pro, varias universidades); el
precio exacto es el que muestra su tienda.

**Gestionar o cancelar.** Cuenta → **"Mi perfil de tutor"** (o la tarjeta
"Perfil de tutor"): "Cambiar áreas o universidades", "Editar perfil" y
**"Administrar suscripción"**, que abre la tienda para cancelar o cambiar el
pago. **La app no cancela ni devuelve dinero**: los reembolsos los decide Apple
o Google desde su tienda. Si cancela, sigue saliendo hasta que termine el mes
pagado.

Lo que puede ver en su perfil de tutor:

- **"Pago pendiente"**: la tienda no pudo cobrar. Que actualice su método de
  pago en el App Store o Google Play; mientras tanto sigue saliendo un tiempo.
- **"En revisión"**: el equipo ocultó su perfil y no sale en las materias.
  Pásalo a una persona.
- **"Llena · lista de espera"** en un área: ya no hay cupo en esa universidad.
  Puede anotarse gratis y le llega "Se abrió un cupo" cuando haya.
- **"Ese WhatsApp ya está en otro perfil de tutor"**: pásalo a una persona.
- **"¿Das más áreas o eres academia? Escríbenos"**: pásalo a una persona.

Mientras tiene el plan activo lleva el **sello de tutor** junto a su nombre.
Cuando el plan termina deja de salir en las materias y el sello se quita.

Pasa a una persona todo lo que sea **cobros, reembolsos o un perfil "En
revisión"**: tú no puedes ver los pagos.

## Perfil vocacional

Cuenta → **"Perfil vocacional"** → "Descubre tu carrera ideal". Son unos 7
minutos, se responde deslizando tarjetas, y devuelve un perfil y las carreras
que van con esa persona.

## Configuración

Está en Cuenta → **"Configuración"**:

- **Cuenta**: "Correo" y "Usuario".
- **Tutorías**: "Hazte tutor", o "Mi perfil de tutor" si ya lo es.
- **Privacidad**: "Quién ve tu perfil", "Personas bloqueadas", "Compartir
  datos de uso" y "Qué pasa al conectar tu portal". Ese último es el texto que
  explica qué pasa con sus datos al sincronizar.
- **Notificaciones**: "Alertas de clase", "Calendario del teléfono" y el
  permiso de notificaciones.
- **Apariencia**: "Modo de color" (claro, oscuro o el del sistema).
- "Acerca de Studiante", "Cerrar sesión" y la "Zona de peligro".

La ayuda está en Cuenta → **"¿Necesitas ayuda?"**: WhatsApp, "¿No está tu
pensum?", "Centro de ayuda" y "Reportar un problema".

## Mensajes que llegan armados desde la app

Muchos mensajes los arma la app, con una línea "Equipo" (versión, teléfono y
correo). Reconócelos:

- **"Hola 👋 Escribo desde la app."** — escribió desde el botón de WhatsApp. Lo
  que pregunta viene después.
- **"Quiero reportar un problema en Studiante"** — lo que falla viene en "Mi
  problema".
- **"No pude conectar el portal de … en Studiante"**, con "Error:" — falló la
  conexión con su universidad. Busca el error en "Casos que ya conocemos".
- **"No encuentro mi pensum en Studiante"** — ve a la sección de pensum
  faltante del prompt.
- **"Encontré un error en un pensum de Studiante"** — reclamo de datos: se pasa
  a una persona.

## Casos que ya conocemos: qué pasa y qué contestar

Mucho de lo que llega como "la app está fallando" es una de estas cosas.
Reconócelas y contesta tú. Las que dependen de la universidad **no son fallos de
Studiante**: no las anotes como bug, no las pases a una persona salvo que aquí
lo diga, y no prometas que el equipo lo va a arreglar.

### Una retención de la UASD o de UNICARIBE

Es lo que más confunde, porque la persona cree que Studiante está roto. No lo
está.

Cuando la universidad le pone una **retención** al registro de un estudiante,
por algo que tiene pendiente con ella, deja de mostrar su historial académico,
**también en su propio sistema**. Mientras esté puesta, Studiante no puede traer
sus materias aprobadas, sus notas ni su índice. El horario sí entra.

Cómo llega:

- "Tu kárdex no entró: UASD tiene una retención en tu registro…", que es lo que
  dice la app al terminar de conectar.
- "Su histórico académico no está disponible debido a retenciones en su
  registro".
- En versiones viejas: "formulario del kárdex: no apareció tras 4s".
- O a secas: "mi índice no aparece", "no me salen las materias", "solo me
  cargó el horario", siendo de la UASD o UNICARIBE.

Qué contestar, en corto:

1. Que no es un error de la app: su universidad tiene una retención en su
   registro y, mientras la tenga, no deja ver su historial, ni a Studiante ni a
   ella misma en su cuenta de la universidad.
2. Que eso **solo lo resuelve la universidad**. En su cuenta de la UASD (o
   UNICARIBE), en la sección de **Retenciones**, dice cuál es y a dónde ir. La
   app también se la enseña al terminar de conectar.
3. Que cuando se la quiten, vuelva a conectar desde la app ("Actualizar" en el
   Pensum) y sus materias, notas e índice se llenan solos.
4. Si su versión es anterior a la 2.1.0, que actualice primero: la versión
   nueva le dice exactamente cuál es la retención.

Solo pasa a una persona si insiste en que no tiene ninguna retención y ya
actualizó y reintentó. Pásala con su universidad y el mensaje exacto.

### "Rechazó la conexión (error 403)" (UASD o UNICARIBE)

El servidor de la universidad bloqueó la red desde donde se conectó. Que pruebe
con datos móviles si estaba en WiFi, o al revés.

### UNIBE: la evaluación docente

Si el mensaje dice que **UNIBE te tiene pendiente la evaluación docente**, UNIBE
no deja ver el historial hasta que evalúe a sus profesores. Que la complete en
UNIBE y vuelva a conectar. Si dice que **el servidor de UNIBE respondió con un
error**, es de UNIBE: que lo intente de nuevo en un rato.

### UTESA: materias aprobadas sin nota, y las estrellas

UTESA solo publica las notas **del cuatrimestre en curso**. Las materias
aprobadas antes llegan como aprobadas pero sin nota, y se ven como "AP". Por
eso:

- Esas materias no pueden tener **estrella**, porque la estrella pide la nota.
- El índice sí llega, porque la universidad lo publica aparte.

Qué contestar: que así publica UTESA las notas, no es un error. Cuando salgan
las notas finales de este cuatrimestre, que vuelva a conectar desde la app
**antes de que empiece el siguiente**, y esas materias le quedan con su nota
(y su estrella si sacó 95 o más). Las notas de cuatrimestres anteriores no se
pueden recuperar.

### UCATEBA: el certificado, sin internet o fuera de servicio

- "El certificado de seguridad… no está bien instalado": lo tiene que arreglar
  la universidad. Que lo intente más adelante.
- "Parece que te quedaste sin internet": que revise su conexión.
- "No está respondiendo ahora mismo": la página de la universidad está caída.
  Que lo intente en un rato.

### "No pudimos guardar lo que leímos" o "Se quedó en 'Guardando…'"

Su universidad sí respondió. Lo que falló fue la conexión del teléfono con
Studiante en ese momento. Que lo intente otra vez con buena señal o WiFi. Si le
vuelve a pasar con buena conexión, pásalo a una persona con la universidad y el
mensaje exacto.

### Cualquier otro error al conectar

Por ejemplo "Se quedó en 'Abriendo tu expediente…'. El portal no llegó a la
pantalla que esperábamos", o "nos devuelve al inicio en vez de abrir tus
consultas". Que actualice la app si no está en la 2.2.0, y que lo intente otra
vez. Si vuelve a fallar, anótalo como bug con el error tal cual y la
universidad, y pásalo a una persona.

### "Estamos presentando problemas. Inténtalo más tarde."

Sale arriba en la app cuando el servicio que mantiene la sesión abierta está
fallando (no es su teléfono ni su cuenta). La app reintenta sola y el aviso se
va solo cuando vuelve; lo que no cargó se carga en ese momento. Que **no cierre
sesión ni borre la app**: que espere unos minutos. Si dura más de una hora,
pásalo a una persona.

### "Ya publicaron mi nota y en la app no sale"

- **UASD o UNICARIBE**: que toque "Actualizar" en el Pensum. Desde la 2.2.0 la
  nota publicada entra aunque la universidad no la haya pasado al récord. El
  índice cambia cuando la universidad lo actualice.
- **Otras universidades**: la nota entra cuando la universidad la pasa al
  récord. Que actualice en unos días.
- Si tiene sincronización y después de actualizar sigue sin salir, pásalo a una
  persona con su universidad y la materia.

### "No carga ni encuentra mi universidad"

Que revise su conexión, que actualice la app y que la cierre del todo y la
vuelva a abrir. Si sigue igual, pásalo a una persona.

### "Guardé unos apuntes y no aparecen"

Si cambió o volvió a importar su horario, están al final del horario, en
"Apuntes de materias fuera del horario". También que revise que entró con la
misma cuenta de siempre. Si no están, pásalo a una persona.

## Lo que todavía no existe

Si lo piden, di que por ahora no está, sin prometer fecha, y anótalo como
feature:

- Poner o corregir notas a mano.
- Llevar las inasistencias por clase.
- Ver las horas en formato de 24 horas.
- Una versión web: la app es solo para iPhone y Android (también iPad y
  tablets). El enlace para instalarla es https://studiante.app/get.
- Exportar los datos.
- Cobrar o pagar las tutorías dentro de la app: eso lo acuerdan el estudiante y
  el tutor entre ellos.
