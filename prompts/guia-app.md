# Cómo se usa la app

Este es el manual de la versión **2.3.0**, la que está en las tiendas, con lo
que le ha llegado por dentro hasta el **16 de octubre** (Campus, entre otras
cosas). Úsalo
cuando alguien está perdido y hay que guiarlo, o cuando reporta algo que parece
un fallo. No lo recites: dale **solo el pedazo que necesita**, en pasos cortos,
uno por línea. Si algo de acá no responde su pregunta, no lo estires: es mejor
pasarlo a una persona que improvisar un paso que no existe.

La regla de siempre vale también acá: di **"sincronización automática"** o
**"conectar tu universidad"**. Nunca nombres el portal ni expliques de dónde
salen los datos. Los textos entre comillas son los que la persona ve en
pantalla: úsalos tal cual para que los reconozca.

## Versiones

- La versión de las tiendas es la **2.3.0**. En la línea "Equipo" de los
  mensajes que vienen de la app ves la suya: "App v2.3.0 (22)" en iPhone y
  "App v2.3.0 (29)" en Android.
- Si tiene una **1.x, 2.0.x, 2.1.x o 2.2.x**, lo primero es que actualice desde
  App Store o Google Play: muchos fallos ya están resueltos ahí, las tutorías
  existen desde la 2.2.0, y los mensajes con amigos, los apuntes compartidos,
  el aviso para juntarse y la pantalla de honores, desde la 2.3.0.
- La app también recibe arreglos y funciones por dentro, sin pasar por la
  tienda. Cerrarla del todo y volver a abrirla hace que tome lo último. Si algo
  de esta guía no le sale teniendo la 2.3.0, lo primero es eso: cerrarla del
  todo y abrirla otra vez (a veces hacen falta dos veces).
- Lo que llegó así después del 10 de octubre:
  - **Campus** (ver su sección): para la UASD desde el 12 de octubre y para
    UNAPEC desde el 14.
  - **UTECO** con sincronización: récord e índice desde el 12 de octubre, y el
    horario desde el 13.
  - Honores de **O&M** solo por índice (12 de octubre).
  - El chat con una **cuenta eliminada** (13 de octubre).
  - El **calendario del teléfono** que para cuando termina el ciclo (15 de
    octubre).
  - Los **códigos de error** de Campus (16 de octubre).

## Cómo está organizada

Abajo hay tres pestañas, y una cuarta, **Campus**, para quien estudia en la
UASD o en UNAPEC:

- **Horario**: las clases de cada día, los amigos y sus mensajes, quién está
  libre a la misma hora, las alertas, el calendario, los apuntes de cada
  materia y, debajo de cada clase, sus tutores.
- **Pensum**: las materias por cuatrimestre, la sincronización con su
  universidad, el índice y la trayectoria.
- **Campus** (solo UASD y UNAPEC, entre Pensum y Cuenta): lo que su
  universidad tiene en línea, traído a la app. Ver la sección "Campus".
- **Cuenta**: su perfil (foto, @usuario, índice, estrellas, amigos), el avance
  de carrera, el perfil vocacional, **"Hazte tutor"**, la ayuda y el botón
  **"Configuración"**. Arriba a la derecha, **"Novedades"** vuelve a abrir lo
  nuevo de la 2.3 ("Lo nuevo de Studiante 2.3"), que sale solo una vez en el
  Horario.

En **iPad y tablets Android** la app se reparte en dos columnas cuando el
aparato está en horizontal.

## Entrar y crear la cuenta

1. En la bienvenida: **"Continuar con correo"**, o con **Apple** (solo en
   iPhone) o **Google**. El mismo camino sirve para crear la cuenta o entrar.
2. Con correo, llega un **código de 6 dígitos** que se escribe en "Verifica tu
   correo". Ya no se usa un enlace.
3. Con correo, pone su nombre (con Google o Apple ya viene). Después, en los
   tres casos: elige su **@usuario** ("Elige tu usuario"), su foto si quiere
   ("Ponle cara a tu perfil"), cómo prefiere ver la app ("¿Cómo prefieres
   verla?") y, al final, **su universidad y su carrera**.
4. En el camino le sale una vez "Necesito tu ayuda", que pide seguirnos en
   Instagram. No es obligatorio: **"Ya te sigo"** continúa.

Si entró con Google o Apple y terminó en un horario vacío sin haber elegido
carrera, le pasó lo que se arregló el 10 de octubre: que cierre la app del todo
y la vuelva a abrir, y elija su carrera en la pestaña Pensum → "Seleccionar
pensum".

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

**"Antes de conectar" le volvió a salir.** Con la 2.3.0 le sale otra vez a todo
el mundo, una sola vez, porque se le agregó un punto: Studiante guarda su
**nombre y matrícula** tal como aparecen en su universidad, por seguridad. Sirven
para que el chat sea solo de estudiantes de verdad y, si alguien lo usa para
hacer daño, para identificar la cuenta ante las autoridades. Nadie los ve en la
app y se borran con su cuenta. Es normal: "Entendido, conectar" y sigue.

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
- **Electivas**: en la casilla de la electiva, "Elegir" → escoge la materia →
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

### Elegir el plan correcto: menciones y planes que se llaman parecido

Al elegir carrera, las que tienen varios planes salen en **una sola fila** con
un chip: "5 menciones", "N variantes" o "N pensums". Tocándola sale "Esta
carrera tiene 5 menciones. Elige la tuya." (o "Hay N pensums de esta carrera.
Elige el tuyo."), y cada opción trae su **código** y sus **créditos**. Se elige
con "Elegir este pensum".

**Cómo se nota que eligió el plan equivocado:** al conectar su universidad le
sale "N materias de tu récord no están en este pensum." y el pensum queda a
medio marcar, con materias que dio sin marcar.

**Cómo se cambia** (no pierde nada):

1. Pestaña Pensum → arriba, **"Cambiar"** (o tocar el título) → sale "Mis
   pensums".
2. **"Agregar pensum"** → su universidad → busca la carrera → elige el plan
   correcto → "Elegir este pensum". Ese queda como el activo.
3. En "Mis pensums", "Editar" → el zafacón en el equivocado, para quitarlo.
4. Que vuelva a conectar su universidad (**"Actualizar"** en el Pensum): el
   plan correcto se marca solo.

Si los dos planes tienen el **mismo código**, la app pregunta "¿Cambiar de
plan?" y el progreso se conserva. Si tienen códigos distintos, se agrega aparte
y se marca con la sincronización.

#### UASD, Psicología: hay dos familias de planes

Son planes **distintos**, con materias distintas, y la gente los confunde porque
se llaman casi igual:

- **"Licenciatura en Psicología"** con **menciones**. Es **una sola fila**,
  "Licenciatura en Psicología" con el chip "5 menciones". Hay que **tocarla** y
  ahí salen las menciones:
  - "Mención Psicología Clínica" (PSIC)
  - "Mención Psicología Escolar" (PSIE)
  - "Mención Psicología Industrial" (PSII)
  - "Mención Psicología Social" (PSIS)
  - "Mención Psicología del Desarrollo Humano" (HUMA)

  Todas de **171 créditos**.
- Las licenciaturas **sin mención**, cada una en su propia fila:
  "Licenciatura en Psicología Clínica" (LPSC, 200 créditos), "Licenciatura en
  Psicología Educativa" (LPSE), "Licenciatura en Psicología Organizacional"
  (LPSO) y "Licenciatura en Psicología Social" (LPSS), de 194 a 200 créditos.

**"Licenciatura en Psicología Clínica" NO es lo mismo que "Licenciatura en
Psicología, Mención Psicología Clínica".** Quien estudia Clínica con mención
tiene que tocar "Licenciatura en Psicología" y elegir "Mención Psicología
Clínica" adentro, no la fila "Licenciatura en Psicología Clínica".

Para saber cuál es la suya, pregúntale **una** de estas, en este orden:

1. **Cómo se llama su carrera en su récord o en su selección de la UASD.** Si
   dice "Mención", es la fila "Licenciatura en Psicología" y adentro su
   mención. Si dice "Licenciatura en Psicología Clínica" a secas, es esa fila.
2. Si no lo sabe: **¿en el primer semestre dio "Psicología General" o
   "Psicología I"?**
   - **"Psicología General"** (con "Orientación Institucional"; en el segundo,
     "Bases Neurobiológicas de la Conducta" y "Conducta Animal") → la de
     **menciones**: "Licenciatura en Psicología" → su mención.
   - **"Psicología I"** (con "Orientación Institucional y Académica" y
     "Laboratorio de Biología Básica") → la **licenciatura sin mención**:
     "Licenciatura en Psicología Clínica", "Educativa", "Organizacional" o
     "Social".

#### UASD, Medicina: el pensum cambió y hay varios planes

Al buscar "Medicina" salen:

- **"Doctor en Medicina"** con el chip "3 pensums". Tocándola salen tres, y se
  distinguen por el código y los créditos:
  - **DMED**, 362 créditos. Es el que tiene casi todo el mundo.
  - **MEDD**, 393 créditos. El plan nuevo.
  - **"Plan 13"** (MED3), 280 créditos. El plan viejo, con códigos de tres
    cifras (BIO100, MED133…).
- **"Pre-Médica/Medicina"**, "Plan 14" (CS01), 362 créditos. Tiene las mismas
  materias que DMED: si su récord dice "Pre-Médica/Medicina", elige esa; si
  dice "Doctor en Medicina", DMED. Cualquiera de las dos le marca lo mismo.
- **"Pre-Médica"** sola (4 semestres): es solo la etapa de premédica. Si ya
  está en Medicina, no es esa.

Para saber cuál es la suya, pregúntale **qué dio en el segundo semestre**:

- **"Estructura y Sistemas Anatómicos"** o **"Inglés Técnico en Salud I"** →
  **MEDD** (393 créditos). En el primero también tuvo "Orientación
  Institucional y Académica", "Educación Física" y "Laboratorio de Física
  Básica".
- **"Biofísica"**, **"Fundamentos de Desarrollo Cognitivo"** o **"Vida en
  Comunidad"** → **DMED** (o "Pre-Médica/Medicina" si así le dice su récord).
- Códigos de **tres cifras** en su récord (BIO100, MED133, SAP103) →
  **"Plan 13"**.

Si después de elegir y conectar le siguen saliendo muchas materias "que no
están en este pensum", pásalo a una persona con su universidad, el plan que
eligió y el número que le sale.

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
  UNICDA, IEESL, UFHEC, UNIREMHOS, UCNE, UCSD, ISFODOSU, ISA, UCATEBA y UNAD.
- Que tenga índice, o sea, que haya conectado su universidad.
- Que **no tenga ninguna materia reprobada** en la carrera, aunque la haya
  repetido y aprobado después. Es la regla de los reglamentos. **En la UASD y en
  O&M no aplica**: ahí el honor sale solo del índice. En la UASD, Cum Laude
  desde 85, Magna con más de 90 y Summa con más de 95. En O&M, Cum Laude de 3.40
  a 3.49, Magna de 3.50 a 3.79 y Summa de 3.80 a 4.00.
- Lo que el reglamento no cuenta como reprobada tampoco quita el honor: los
  retiros, por ejemplo, o en UNAPEC Matemática Pre-Universitaria, Matemática
  Básica Universitaria y Deporte. Si cree que una materia no debería contar,
  es un reclamo de datos (ver "¿Algún dato está mal?" abajo).

Si falta cualquiera de las tres, el honor no sale en ningún lado, tampoco en el
widget. Cuando sale, está en Cuenta → "Avance de carrera" ("Vas por…") y junto
al índice.

**"¿Por qué no me salen honores?"** Desde la 2.3.0 la app lo dice sola. Que toque
su índice (la columna del índice en el Pensum, o el índice en Cuenta) → **"¿Por
qué no me salen honores?"** (o "Ver tus honores" si ya tiene uno). Sale **"Tus
honores"** con el motivo:

- **"Reprobaste una materia"**: con cuál, en qué período y con qué nota, y si
  después la aprobó o la está repitiendo.
- **"Tu índice no llega a Cum Laude"**: cuánto le falta. Cuenta el índice con
  el que se gradúe, así que todavía puede subirlo.
- **"Falta tu índice"**: tiene que conectar su universidad (ahí mismo está el
  botón).
- **"No tenemos la regla de tu universidad"**: su universidad no está en la
  lista de arriba. Anótalo como feature con su universidad.
- Si ya tiene honor: "Para … te faltan …", lo que le falta para el siguiente.

Si dice que un dato está mal (por ejemplo, que esa materia la convalidó y no la
reprobó), abajo está **"¿Algún dato está mal?"** → "Avisar por WhatsApp", que
manda el mensaje armado con todo (ver "Mensajes que llegan armados").

**Estrellas.** Una estrella es una materia aprobada con la nota más alta que
puede dar su universidad: **95 o más** si la nota viene en número, o la letra
más alta (A+, o A donde la escala termina en A). Las notas de 90 en adelante se
ven doradas. Para tener estrellas hace falta la **nota**, que solo llega con la
sincronización. Una materia marcada a mano, o que llegó como "AP", no tiene nota
y no puede tener estrella.

## El horario

Si está vacío dice **"Aún no tienes horario"**, con **"Agregar mi horario"** y
**"Agregar manualmente"** (en versiones anteriores el primero tenía otro nombre,
pero hace lo mismo). Con horario ya puesto, lo mismo se abre desde
**"Actualizar"**, arriba en el Horario.

"Agregar mi horario" abre **"Agrega tu horario"**:

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

**Hasta cuándo.** Desde el 15 de octubre, si su horario vino de su universidad
y la universidad publica las fechas del ciclo, cada clase **para el día que
termina el ciclo** y la pantalla dice "…cada semana hasta el …, cuando termina
tu ciclo." Las clases agregadas a mano, leídas de una foto o sin fechas de la
universidad siguen 20 semanas y se van extendiendo solas mientras usa la app.

**"Me salen clases en enero" (o después de que termina el ciclo).** Que vuelva
a traer su horario de su universidad ("Actualizar" en el Horario → "Directo de
mi universidad") con la app al día: con las fechas nuevas el calendario se
corta solo. Si su universidad no publica fechas o el horario lo puso a mano, por
ahora no se puede: que apague el calendario cuando termine el ciclo y lo vuelva
a encender con el horario nuevo.

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

- **Dónde**: pestaña Horario → **"Amigos"**. El botón redondo de los mensajes,
  al lado, también abre Amigos.
- **Agregar**: "Agregar" y luego buscarlo por **nombre o @usuario** (busca
  mientras se escribe), enseñar su código QR, escanear el de otra persona, o
  compartir su enlace de invitación. Quien abre ese enlace y toca "Agregar como
  amigo" queda como su amigo de una vez. Si alguien no sale buscando, puede que
  haya apagado "Aparecer en la búsqueda": que se agreguen con el código.
- **Qué ven**: en el horario, qué amigos van a su misma clase y quiénes están
  libres a la misma hora (ver "Quién está libre a la misma hora" más abajo), y
  en el perfil, su avance.
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

## Mensajes con sus amigos

Desde la **2.3.0** puede escribirle a un amigo sin salir de la app. Solo entre
**amigos**: a alguien que no es su amigo no se le puede escribir, y no hay
solicitudes de mensaje.

**Quién lo tiene.** Quien ya conectó su universidad, o quien es de una
universidad que tiene sincronización. A los demás no les sale nada del chat. Y
con cada amigo, solo si ese amigo también lo tiene: si al lado de un amigo no
sale la burbuja, es que ese amigo no lo tiene.

**Para escribir hay que haber conectado su universidad** al menos una vez. Sin
eso puede leer lo que le escriban, pero en vez del cuadro para escribir le sale
un aviso para sincronizar, con su botón. Es para que el chat sea solo de
estudiantes de verdad y sin spam.

**Dónde se escribe:**

- Pestaña Horario → "Amigos" → la burbuja al lado de cada amigo. Quien le
  escribió sale arriba, con en rojo cuántos mensajes tiene sin leer.
- En el Horario, el botón redondo con la burbuja, al lado de "Amigos", lleva el
  número de mensajes sin leer y abre Amigos.
- En el perfil de un amigo, **"Enviar mensaje"**.
- En las listas de amigos libres o de la misma clase, la misma burbuja.
- Los avisos traen el nombre de quien escribe y el mensaje; tocarlo abre la
  conversación.

No hay una bandeja aparte: las conversaciones se abren desde Amigos.

**Qué se puede hacer:**

- Solo **texto**: no se mandan fotos, audios ni archivos, no hay grupos, y un
  mensaje enviado no se puede borrar ni editar.
- **Me gusta**: dos toques en el mensaje del amigo, o mantenerlo presionado →
  "Me gusta".
- **Responder** un mensaje: deslizarlo a la derecha, o mantenerlo presionado →
  "Responder".
- Si el amigo escribe un número de teléfono, debajo sale "Abrir en WhatsApp".
- En el menú de arriba (⋯): "Ver perfil", "Eliminar chat", "Bloquear" y
  "Reportar".

**Eliminar chat** lo borra solo de su lado, en su cuenta (en todos sus
teléfonos): el amigo conserva el suyo. Si alguno vuelve a escribir, empieza de
nuevo.

**Bloquear** hace que dejen de ser amigos y que no puedan escribirse ni verse.
Se deshace en Configuración → "Personas bloqueadas", pero desbloquear **no
devuelve la amistad**: para volver a escribirse hay que mandar una solicitud
otra vez.

**Reportar un mensaje:** mantener presionado el mensaje → "Reportar mensaje" →
contar qué pasó → "Enviar reporte". Lo revisa una persona del equipo, nadie le
dice a la otra persona quién reportó, y ahí mismo puede "Bloquear también". El
equipo no lee las conversaciones: solo ve lo que se reporta.

**Cuando un mensaje no sale**, debajo dice por qué:

- "Tiene palabras que no se permiten en el chat." — insultos de odio o acoso
  sexual. Las malas palabras de siempre sí pasan.
- "En el chat no se venden tutorías ni trabajos…" — para ofrecer tutorías está
  "Hazte tutor".
- "En Studiante no se vende ni se consigue nada ilegal."
- "Ya enviaste este mismo mensaje a varias personas hoy." — un mismo mensaje
  largo llega como mucho a 4 personas por día.
- "Vas muy rápido. Espera un momento." — más de 30 mensajes en un minuto.
- "No puedes enviar mensajes." — el equipo le quitó el chat por un tiempo.
  Pásalo a una persona.
- "Solo puedes escribirle a tus amigos." o "Ya no son amigos…" — dejaron de
  ser amigos.
- "Sin conexión. Toca para reintentar." o "No se envió. Toca para reintentar."
  — que lo toque con buena conexión. El segundo también sale si llegó al tope
  de 1000 mensajes en el día.
- Cada mensaje puede tener hasta 2000 caracteres.

**"Le escribo y no me contesta."** No supongas ni digas que lo bloquearon: la
app no lo dice a propósito, y tú tampoco puedes saberlo. Dile que la otra
persona lo ve cuando abra la app, y que revise que siguen siendo amigos.

**Si cuenta que alguien lo acosa o lo amenaza por el chat:** que reporte el
mensaje y bloquee desde la app, y pásalo a una persona.

Los mensajes se guardan hasta que alguno de los dos borre su cuenta.

**"Cuenta eliminada".** Si un amigo borró su cuenta, la conversación sigue en
su lista como **"Cuenta eliminada"**, con una silueta gris. Puede leer todo lo
que se dijeron, pero no escribir: en vez del cuadro sale "Esta cuenta se
eliminó. Lo que se dijeron sigue aquí." No hay perfil que abrir. Si quiere
quitarla, en el menú (⋯) está "Eliminar chat".

## Apuntes compartidos

Desde la 2.3.0, un apunte o un recordatorio se comparte **mencionando** a sus
amigos:

- Al escribir **"@"** en el título o el texto sale una barra con sus amigos:
  tocar a uno lo menciona. Escribir "@Ana" a mano, sin tocarla en la barra,
  **no** la menciona.
- O en "Compartir" → **"Mencionar amigos"**, marcando a quién.
- Se comparte al **guardar**. Solo con amigos, y hasta 20 por apunte.
- Para quitar a alguien hay que desmarcarlo en "Mencionar amigos": borrar
  "@Ana" del texto no la quita.

Al amigo le llega un aviso ("… te mencionó en un apunte" o "en un
recordatorio") y le sale en sus apuntes de esa materia, con "De …". Si no tiene
esa clase, le sale al final del Horario, en "Apuntes de materias fuera del
horario". Los recordatorios le suenan a él también.

- **Solo quien lo escribió puede editarlo**, y los cambios le llegan solos al
  amigo.
- El amigo puede marcarlo hecho o fijarlo arriba (solo para él), o "Quitar de
  mis apuntes" (quien lo escribió no se entera).
- Si quien lo escribió lo borra, se va de todos. Si dejan de ser amigos o se
  bloquean, se va lo que se compartieron.

## Quién está libre a la misma hora, y avisar para juntarse

Entre dos clases, el Horario enseña su tiempo libre y qué amigos están libres
también:

- "4h 10m libre" y debajo, en verde, por ejemplo "4 libres · 3 se suman
  después", o "2 libres desde las 11:00 am".
- "Ningún amigo libre a esta hora", en gris, si no hay nadie.
- Al final del día, **"Sin más clases"**: los amigos que también ya salieron.

Tocándolo sale la lista "N amigos libres contigo" (o "N amigos ya salieron"),
con cada amigo y desde cuándo está libre ("Libre desde hace 30 minutos",
"Libre desde las 11:00 am"…).

**Por qué un amigo no sale libre.** Solo salen los amigos que comparten su
"Horario libre" y que probablemente están en la universidad: ese día tuvieron
una clase presencial que terminó hace menos de 3 horas, o les queda otra más
tarde. Un amigo que ese día no tiene clases, o que todavía no ha empezado, no
sale. Cada quien lo decide en Amigos → "Privacidad" → **"Horario libre"**
("Todos", "Amigos", "Elegir…" o "Nadie"; viene en "Amigos"). Ocultar el suyo no
le oculta el de los demás.

**Avisar para juntarse.** En esa lista está **"Avisarles para juntarse"**:

1. Escribe un mensaje corto (hasta 100 caracteres) o deja el que trae la app.
2. Toca "Avisar a los N" (o "Avisarle").
3. A los amigos de la lista les llega "¡{su nombre} quiere juntarse!" con el
   mensaje.

Es **un aviso al día** por persona, y solo para el mismo día. Si el botón está
gris o sale un error, es uno de estos: "Ya enviaste tu aviso de hoy", "Ese rato
libre ya pasó", "Solo puedes avisar el mismo día", "Ese mensaje tiene palabras
que no se permiten" o "Ninguno de ellos puede recibir el aviso ahora".

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

## Campus (UASD y UNAPEC)

Es la pestaña **"Campus"**, entre Pensum y Cuenta: "Lo que tu universidad tiene
en línea, traído a Studiante." Llegó por dentro, sin pasar por la tienda: para
la UASD el 12 de octubre y para UNAPEC el 14.

**Quién la ve.** Todo el que tiene como **pensum activo** uno de la **UASD** o
de **UNAPEC**. Nadie más: las otras universidades todavía no tienen Campus (si
lo pide, anótalo como feature con su universidad). Un estudiante de la UASD ve
solo lo de la UASD, y uno de UNAPEC solo lo de UNAPEC.

**"No me sale Campus."** En este orden:

1. Que su pensum **activo** sea de la UASD o de UNAPEC (en la pestaña Pensum,
   "Cambiar" → el que está marcado). Si tiene dos carreras, Campus sigue a la
   activa.
2. Que cierre la app del todo y la abra otra vez, hasta dos veces: Campus llega
   por dentro.
3. Que tenga la 2.3.0. Si no, que actualice.
4. Si con todo eso no le sale, pásalo a una persona.

Abajo de Campus dice "Campus está en prueba. Si algo no cuadra, cuéntanos desde
Cuenta › Reportar un problema."

### Campus de la UASD

Cuatro tarjetas:

- **"UASD Virtual"**: sus **tareas**, con su fecha de entrega.
- **"Historial de notas"**: sus notas período por período.
- **"Calendario académico"**: las fechas del período.
- **"Programación docente"**: las secciones del próximo período.

Además, en el Horario, cada clase con tareas lleva un chip "Tareas N", y en el
Pensum las materias dicen "N tareas".

**Tareas (UASD Virtual).**

- Se conecta con **"Conectar UASD Virtual"**: entra con su **ID Banner y su
  contraseña**, como siempre, en la página de la UASD. Studiante no ve ni
  guarda su contraseña. Lee sus asignaturas, sus tareas y fechas, lo que ya
  entregó, cuestionarios, foros y notas de las tareas.
- Las tareas se ordenan en "Vencidas", "Vence hoy", "Próximos 3 días", "Vence
  esta semana", "Vence la semana que viene", "Más adelante" y "Sin fecha
  definida". Las semanas van de lunes a domingo. Arriba hay filtros: "Próximas",
  "Hechas" y uno por materia.
- Cada tarea dice si está "Abierta", cuánto le queda ("Quedan 3 h"), y si ya
  la entregó ("entregada", "respondido", "participaste" o la nota). Tocándola
  salen las instrucciones, el comentario del profesor y **"Abrir en UASD
  Virtual"**, que lo lleva directo a la tarea (pide entrar otra vez).
- **No se actualiza solo del todo**: con **"Actualizar"** se vuelve a leer
  todo, y hay que entrar otra vez cada vez (por seguridad no queda la sesión
  abierta). Entre una lectura y otra, la app revisa sola cada pocas horas si
  hay tareas nuevas o fechas movidas, pero eso no marca nada como hecho.
- **"Alertas"** (arriba en Tareas): "Avisarme de mis entregas" con cuánto antes
  ("2 días antes", "1 día antes", "3 horas antes", "1 hora antes") y "Tareas
  nuevas" cuando un profesor publica algo. Necesitan el permiso de
  notificaciones.
- "Sin fecha definida" o "Sin definir": el profesor puso una fecha de relleno;
  cuando ponga la real, sale al actualizar.
- Si una tarea falta, que toque "Actualizar". Si el profesor no le puso fecha,
  la materia sale en "Sin tareas con fecha".

Errores de UASD Virtual que puede ver (todos tienen "Intentar de nuevo"):

- "UASD Virtual pide entrar otra vez para abrir tu siguiente aula (2 de 4
  listas)." — No es un error: que vuelva a entrar y sigue.
- "El aula de {facultad} no respondió." — Esa aula de la UASD no contestó en un
  minuto. Las demás sí se leyeron; "Intentar de nuevo" lee solo las que
  faltaron. Es de la UASD: que pruebe en un rato.
- "UASD Virtual tardó demasiado en responder." o "No pudimos abrir UASD
  Virtual. Revisa tu conexión." — conexión o la UASD lenta: que pruebe con
  buena señal en un rato.
- "No vimos asignaturas en tu UASD Virtual para este período." — la UASD no le
  tiene materias virtuales inscritas este período.
- "Ya guardamos 2 de tus 4 aulas; vuelve a intentarlo para las demás." — se
  guardó lo que se pudo leer.

**Historial de notas.** Sale del récord que importó al conectar su universidad:
cada período con sus materias, notas, el índice del período y el acumulado.
Sin récord dice "Importa tu récord" con **"Importar mi récord"**. Cuando salen
notas nuevas, que vuelva a importar ("impórtalo de nuevo").

**Calendario académico.** Las fechas del período que publica la UASD, con
"AHORA" y "PRÓXIMO". Con la campana de un evento le avisa: "Cuando empieza",
"Un día antes del último día" y "El último día", a la hora que elija (7:00 a.
m. si no elige). Si dice "Todavía no hay calendario", la UASD no lo ha
publicado.

**Programación docente.** Las secciones del **próximo período**: horario,
profesor, aula, modalidad y **cupos**.

- La primera vez pregunta "¿En qué campus estudias?" (se cambia con
  "Cambiar"). Si no hay secciones en su campus, "Ver en todos los campus".
- "Elegir materia a consultar" muestra lo que le falta del pensum y si sus
  requisitos le dejan tomarla ("Puedes tomarla", "Si apruebas…", "Te
  falta…"). También se busca por nombre o clave.
- **Armar su selección**: tocando una sección la agrega. Si choca con otra,
  avisa ("Esta sección choca"). "Ver tu selección" enseña la semana, los
  créditos, los choques y las secciones sin cupo, y se puede "Compartir".
- **Studiante no inscribe materias**: es un plan para organizarse. La
  inscripción la hace en la UASD, en sus fechas.
- Los cupos cambian todo el tiempo: deslizar hacia abajo los vuelve a leer.
- Con **"Compartir con tus amigos"** ve qué secciones eligieron sus amigos que
  también la comparten ("Ana la eligió"). Viene apagado; se maneja en Amigos →
  Privacidad → "Tu próxima selección".
- Si sale "Llegaste al límite de consultas a la programación docente por hoy",
  que siga mañana.
- "La UASD no responde ahora mismo" — es de la UASD: que pruebe en un rato.

### Campus de UNAPEC

Seis tarjetas:

- **"Notas en línea"**: las calificaciones de sus materias en curso, a medida
  que salen.
- **"Asistencia"**: cuántas veces ha faltado a cada materia y cuántas le
  quedan.
- **"Historial de notas"**: igual que en la UASD.
- **"Cita de selección y pago"**: el día y la hora de su selección y los días
  de pago.
- **"Clases del próximo cuatrimestre"**: las secciones del próximo período,
  con horario, profesor y cupos, y su selección (igual que la programación de
  la UASD, sin campus). La inscripción la hace en UNAPEC el día de su cita.
- **"Calendario académico"**: las fechas del período, con alertas.

**Notas y asistencia.** Se traen con **"Traer de UNAPEC"** (la primera vez) o
**"Actualizar"**: entra con su cuenta de UNAPEC (la de Microsoft), en la página
de UNAPEC. Studiante no ve ni guarda su contraseña. Lee "Leyendo tus
calificaciones…", "Leyendo tu asistencia…", "Revisando tu inscripción…" y
guarda. **No se actualiza sola**: cada vez que quiera ver notas nuevas, que
toque "Actualizar".

- Cada materia trae "Primer parcial", "Segundo parcial" y "Examen final", el
  acumulado de 100 y lo que falta por publicar, y le dice cuánto necesita en lo
  que falta para mantener la letra. Las retiradas salen con "Retirada".
- "Si sacas todo lo que falta" proyecta el índice del cuatrimestre y si quedaría
  en condición "Normal" o en "Prueba académica".
- **Ausencias**: se permiten 3 por cada día de clase a la semana (6 si la
  materia es dos días). Una más es FN (se reprueba por inasistencia). La app
  dice "Puedes faltar N veces más", "Llegaste al máximo" o "Pasaste el máximo".
  Si sale "UNAPEC no tiene asistencia registrada todavía", los profesores no
  han pasado lista en UNAPEC.

Lo que puede salirle al traer las notas:

- **"UNAPEC no deja ver tus calificaciones todavía"** — no es un error de la
  app: UNAPEC bloquea las notas mientras tenga algo pendiente: **la evaluación
  de sus profesores, actualizar su configuración de pagos o la configuración
  de su próximo período**. Que lo complete en UNAPEC y vuelva a actualizar.
- "UNAPEC no muestra materias en curso para ti ahora mismo." — UNAPEC no le
  tiene materias este período.
- "Se quedó en 'Leyendo tus calificaciones…'…" — UNAPEC no respondió: que lo
  intente en un rato.

**Cita de selección.** Detecta su carrera; si no, pregunta "¿Cuál es tu
carrera en UNAPEC?". Si sale "UNAPEC no tiene tu cita ahora mismo", todavía no
la publican.

### "No pudimos preparar la lectura" y los códigos CS-…

Antes de abrir la página de UASD Virtual o de UNAPEC, la app prepara la
lectura. Desde el 16 de octubre, el botón dice **"Preparando…"**, lo reintenta
solo unos segundos, y si no se puede **no abre nada**: sale "No pudimos
preparar la lectura" con el motivo y un **código** ("Código: CS-AUTH"), y los
botones "Intentar de nuevo", "Reportar" y "Cerrar". Si reporta, el código
llega en el mensaje: "(código CS-…)".

| Código | Qué pasó | Qué contestar |
|---|---|---|
| CS-NET | El teléfono no llegó a Studiante | Que revise su conexión y vuelva a intentar |
| CS-AUTH | Su sesión de Studiante no se pudo renovar en ese momento (pasa cuando muchísima gente abre la app a la vez) | Que espere un minuto y toque "Intentar de nuevo". No tiene que cerrar sesión ni borrar nada |
| CS-VERIFY | No se pudo verificar el teléfono con Apple o Google | Que cierre la app y la abra en un par de minutos. Si sigue igual, pásalo a una persona |
| CS-OFF | Su pensum activo no es de esa universidad | Que en el Pensum active el de la UASD o UNAPEC ("Cambiar") |
| CS-LIMIT | Llegó al límite de lecturas del día (o hubo demasiadas peticiones a la vez) | Si dice "por hoy", que siga mañana; si no, en un minuto |
| CS-SERVER | Studiante tuvo un error de su lado | Que pruebe en un rato. Si sigue más de una hora, pásalo a una persona |
| CS-OUTDATED | Su app necesita lo último que llegó por dentro | Que cierre la app del todo y la abra otra vez (hasta dos veces) |
| CS-INCOMPLETE | La lectura llegó a medias | Que vuelva a intentar en un momento |
| CS-UNKNOWN | Otra cosa | Que vuelva a intentar; si se repite, pásalo a una persona con el código |

**Si dice "No pudimos preparar la lectura de UNAPEC" (o de UASD Virtual) sin
código**, tiene la app de antes del 16 de octubre. Casi siempre fue la sesión
que no se pudo renovar en un momento de mucha gente (lo de CS-AUTH): que cierre
la app del todo, la abra otra vez (así toma la versión con los códigos) y lo
intente de nuevo. Si vuelve a fallar, ya le sale el código.

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
- **"Hola 👋 Creo que hay un dato mal en mis honores en Studiante."** — viene
  de la pantalla de honores. Trae "Lo que veo mal" (lo que escribió la persona)
  y "Lo que dice la app" (universidad, índice, el resultado y las reprobadas).
  Es un reclamo de datos: pásalo a una persona tal cual.

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

### "formulario del kárdex: no apareció tras 4s" (UASD)

La página de la UASD tardó más de la cuenta en abrir su récord. Casi siempre es
un momento lento de la UASD: que lo intente otra vez en un rato. Si le sale
**siempre**, puede ser una retención: que revise la sección de Retenciones en
su cuenta de la UASD (ver el caso de arriba). Si no tiene ninguna y le sigue
saliendo, pásalo a una persona.

### "Le di a horario, cargó y no se puso nada"

Pasaba al traer el horario de su universidad sin tener una carrera de esa
universidad elegida: se leía pero no se guardaba. Se arregló el 15 de octubre.
Que lo intente de nuevo (Horario → "Actualizar" → "Directo de mi
universidad"). Si tampoco, que elija primero su carrera en el Pensum y lo
vuelva a traer.

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

### "El certificado de seguridad… no está bien instalado"

Algunas universidades mandan su certificado de seguridad incompleto. Desde la
**2.3.0, en Android**, la app lo completa sola: UFHEC, UNEFA y UNIREMHOS, que
fallaban en Android, ya abren. Así que:

1. Si está en Android con una versión anterior a la 2.3.0, que actualice desde
   Google Play.
2. Si ya tiene la 2.3.0 y le sigue saliendo, lo tiene que arreglar la
   universidad: que lo intente más adelante.

### UCATEBA: sin internet o fuera de servicio

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
- Llevar las inasistencias por clase a mano. (En UNAPEC las trae sola:
  Campus → "Asistencia".)
- Campus para universidades que no son la UASD ni UNAPEC.
- Ver las horas en formato de 24 horas.
- Una versión web: la app es solo para iPhone y Android (también iPad y
  tablets). El enlace para instalarla es https://studiante.app/get.
- Exportar los datos.
- Cobrar o pagar las tutorías dentro de la app: eso lo acuerdan el estudiante y
  el tutor entre ellos.
- En el chat: mandar fotos, audios o archivos, los chats de grupo, o borrar o
  editar un mensaje ya enviado.
