# Decisiones del proyecto QALAT

Registro de las decisiones que cierran una discusión. Cada entrada tiene la
regla, el fundamento y la fecha. Si una decisión aparece acá, no se rediscute:
se cambia con una entrada nueva que diga por qué.

---

### El formulario de Perú se llama `index.html` y no se renombra
**Regla.** `index.html` es el formulario de ingreso de Perú. No se renombra a
`index_peru.html` ni se convierte en portal, aunque rompa la convención de los
otros seis países.

**Fundamento.** Perú fue el primer país y su formulario quedó como página raíz
del sitio. Los centros peruanos tienen esa URL guardada por fuera del sistema,
en correos y favoritos, y no hay forma de avisarles a todos. Renombrar el
archivo los deja sin acceso sin que nadie se entere hasta que dejan de llegar
registros. El costo de la inconsistencia es confusión de quien lee el repo; el
costo de arreglarla es perder centros en producción.

**Consecuencia asumida.** Quien busque `index_peru.html` no lo va a encontrar y
va a concluir que Perú no tiene formulario. Por eso el archivo lleva un aviso en
su cabecera y el README abre con la tabla de archivo a país.

*2026-09-02*

---

### El denominador excluye los sin dato solo si la pregunta no correspondía
**Regla.** Ningún porcentaje ni promedio cuenta en su denominador a un paciente
que no tenía el dato, **salvo en consumo de sustancias**. En trabajo, educación
y transgresión el vacío sale del denominador. En consumo de sustancias el vacío
se completa con cero y entra. Todo gráfico muestra el N sobre el que se calculó.

**Fundamento.** La ausencia significa cosas distintas según la pregunta. En
trabajo y educación existe la casilla "no aplica": un jubilado no tiene días que
reportar y contarlo como cero diría que estuvo disponible y no asistió. En
transgresión la pregunta es Sí/No, así que un vacío es una respuesta que no se
dio. En consumo, en cambio, el instrumento no admite "no aplica", y los vacíos
que hay vienen del bug del formulario que borró los ceros durante cinco meses.
Sacarlos del denominador excluiría a quienes sí respondieron, y respondieron
cero: la prevalencia de marihuana en Perú pasaría de 10,5 % a 23,2 % sin que
nadie hubiera empezado a consumir.

**Consecuencia asumida.** Mientras los 1.115 valores sigan sin completarse, el
denominador de sustancias incluye registros cuyo cero es inferido. Al ejecutar
ese completado la distinción desaparece, porque ya no habrá vacíos.

*2026-09-02*

### La sustancia declarada que no está en la lista del país va a Otra sustancia
**Regla.** Cada país tiene su lista cerrada de sustancia principal en el
formulario, y esa lista es la taxonomía. Lo que se declare fuera de ella cae en
`Otra sustancia`, que tiene columna de días propia. Heroína en Ecuador es
Heroína; heroína en México es Otra sustancia.

**Fundamento.** La lista del formulario coincide con las columnas de días que
ese país mide. Una categoría sin columna no puede tener barra: quedaría vacía o
con un cero falso. Y no es una decisión de análisis, es leer lo que el
instrumento ya hizo: un mexicano no puede elegir heroína, no está en su lista,
así que la escribió en el campo de otra sustancia.

**Dónde vive.** `clasificar_sustancia()` en `pipeline/validacion_top.py`, con
`CATEGORIAS_POR_PAIS` como taxonomía madre. Antes estaba copiada en diez módulos
con tres vocabularios distintos, y eso dejaba fuera al 12 % de los pacientes.

*2026-09-02*

### Los gráficos muestran todas las categorías del país, siempre
**Regla.** Tanto los de prevalencia como los de promedio de días dibujan las seis
categorías del país, siete en Ecuador, aunque alguna venga en cero. Los de
promedio llevan el n de cada barra debajo.

**Fundamento.** Elegir las más frecuentes hacía que los dos gráficos mostraran
sustancias distintas, y ya produjo el caso de Sedantes apareciendo en el de días
y no en el de prevalencia. Con la lista fija son comparables entre centros, entre
países y en el tiempo. El n debajo evita que una barra de siete pacientes se lea
con el mismo peso que una de trescientos.

*2026-09-02*

---

### La línea base es el TOP con etapa de ingreso, y solo ese
**Regla.** El TOP 1 de un paciente es el que tiene etapa `ingreso`. Los
pacientes sin ningún TOP de ingreso quedan fuera de la caracterización y del
análisis de cambio. No se los recupera tomando su TOP más antiguo.

**Qué significa `ingreso`.** El ingreso real al centro, no la primera vez que se
le aplica el instrumento. Una persona que lleva seis meses atendiéndose y recién
ahora recibe su primer TOP no está ingresando: esa etapa es `en tratamiento` y
está bien puesta. Un derivado desde otro centro o desde una desintoxicación sí
está ingresando, porque ingresa a ese centro.

**Fundamento.** La caracterización responde cómo llegan los pacientes al centro.
Un TOP aplicado a mitad del tratamiento no describe cómo llegó esa persona, así
que usarlo como línea base fabricaría un dato que nadie midió. Es preferible un
N más chico y honesto que uno completo y falso.

**Consecuencia asumida.** Al 2026-09-02 quedan fuera 182 pacientes, el 13,7 %.
El reparto es desigual: México pierde el 34,5 %, Perú el 15,5 %, El Salvador el
11,8 % y Ecuador el 9,8 %. Tres centros quedan sin ningún paciente en su informe
y EESS28CI queda con dos de dieciocho.

Para el análisis de cambio el costo es mucho menor: de esos 182, solo 11 tienen
una segunda medición, así que los otros 171 nunca iban a servir para comparar
TOP 1 contra TOP 2.

**Por qué el costo es aceptable.** Buena parte de esos casos no son un error de
captura. Cuando un centro adopta el TOP, su cohorte ya está en curso, y esos
pacientes son legítimamente `en tratamiento`. México empezó a registrar en mayo
de 2026 con gente que ya atendía. Nunca tuvieron línea base y no la van a tener.

**Lo que sí es accionable.** Pedir a los centros que confirmen cuáles de esos 182
sí ingresaron recién y quedaron mal etiquetados, y reforzar que todo paciente que
ingresa al centro por primera vez lleva etapa `ingreso`, incluso si viene
derivado.

*2026-09-02*

### La unidad de análisis es el episodio, no la persona
**Regla.** Se cuentan episodios de tratamiento: un paciente que ingresa dos veces
al mismo centro, o a dos centros distintos, cuenta dos veces. Cada TOP con etapa
`ingreso` abre un episodio.

**Fundamento.** Los informes son para que el centro vea su propia operación. Un
paciente que egresó y volvió es una atención nueva desde el punto de vista del
centro, y contarlo una sola vez esconde trabajo hecho. Es el criterio del NDTMS
británico, de donde viene el instrumento, y el que se usa en Chile.

**Cuánto cambia hoy.** Poco: 47 pacientes tienen más de un TOP de ingreso en el
mismo centro y solo 4 códigos aparecen en más de un centro. Personas únicas da
1.326 y episodios por centro 1.330. La diferencia crece con el tiempo, y por eso
se define ahora y no cuando haya que recalcular informes ya entregados.

**Lo que se conserva.** El código de paciente sigue en la base, así que contar
personas únicas cuando haga falta es una consulta, no un recálculo.

*2026-09-02*

---

## Instrumento

### El campo sexo usa H/M/O en los cuatro países
**Regla.** `H` es hombre, `M` es mujer, `O` es otro. Los quince formularios
escriben esa convención y la base está homologada.

**Fundamento.** Convivían dos convenciones opuestas: Perú escribía M para
masculino y F para femenino, y los otros tres H para hombre y M para mujer. Como
la letra `M` significaba cosas distintas según el país, ningún cálculo podía
resolverlo sin saber el origen del registro. Se eligió H/M/O porque ya era la
convención de tres de los cuatro países y de unos 900 de los 1.400 registros.

*2026-08-28*

### La sustancia principal se toma siempre del TOP 1
**Regla.** En cualquier análisis de evolución, la sustancia principal es la
declarada en el TOP de ingreso, aunque el paciente declare otra en el
seguimiento.

**Fundamento.** El ingreso es la línea base contra la que se mide el cambio. Si
la sustancia principal cambiara entre mediciones, el paciente saltaría de una
categoría a otra y el análisis dejaría de comparar a la misma persona consigo
misma. Que un paciente cambie de sustancia principal es un dato en sí mismo,
pero no para esta tabla.

*2026-09-01*

### No se distingue abstinencia de nunca consumió al ingreso
**Regla.** Un cero en la sección de consumo significa que la persona no consumió
esa sustancia en las últimas cuatro semanas. El sistema no intenta separar a
quien nunca la consumió de quien está en abstinencia.

**Fundamento.** El TOP mide consumo en las últimas cuatro semanas, no historia
de consumo, así que el instrumento no captura el dato que permitiría separarlos.
El sistema inglés lo resuelve con un registro de admisión aparte donde el
paciente declara hasta tres sustancias problema, y la versión regional no lo
tiene. Agregar esa pregunta sería modificar el instrumento.

*2026-09-01*

---

## Análisis

### No se implementa el índice de cambio fiable
**Regla.** La clasificación del cambio compara días brutos entre las dos
mediciones. No se aplica el índice de Jacobson y Truax que usa el estándar del
TOP. Los rótulos dicen "disminuyó" y "aumentó", no "mejoró" ni "empeoró".

**Fundamento.** El índice requiere la confiabilidad de cada ítem, que sale del
estudio de validación, y la desviación estándar de la población propia, que con
el volumen actual sería inestable. Public Health England reunió un año de datos
antes de fijar sus umbrales. Queda abierto para cuando haya volumen; el paper de
validación del TOP para población chilena tendría los coeficientes.

**Consecuencia asumida.** Una diferencia de un día también cuenta como
disminución o aumento, de modo que esas dos categorías quedan sobredimensionadas
respecto de lo que informaría el estándar. Por eso los rótulos no hablan de
mejoría.

*2026-09-01*

### En sustancia principal entran todos con sus ceros; en cualquier sustancia solo los consumidores
**Regla.** Los dos gráficos de sustancia principal, el promedio de días y la
clasificación del cambio, incluyen a todos los pacientes que declararon esa
sustancia como principal, con sus ceros. Los gráficos que recorren todas las
sustancias promedian solo entre quienes las consumieron, y el porcentaje de
consumidores va al lado, en la misma vista.

**Fundamento.** Son dos preguntas distintas. En la sustancia principal, un cero
significa que la persona ingresó en abstinencia de su propia droga problema, y
ese es su dato real. En el gráfico de todas las sustancias, incluir a quienes no
la consumen convierte el número en una función de la composición de la
población: un centro que atiende más alcohólicos mostraría menos consumo de
cocaína aunque sus consumidores de cocaína consuman igual. Quien deja de
consumir no desaparece del reporte, aparece como una caída de la prevalencia.

*2026-09-01*

### Hay dos indicadores de seguimiento y no miden lo mismo
**Regla.** El sistema muestra dos indicadores distintos y ambos se conservan,
con nombres que no se pueden confundir.

| | Cobertura de seguimiento | Aplicación del TOP de seguimiento |
|---|---|---|
| Qué mide | Si los pacientes a los que ya les corresponde la segunda medición la tienen | Si el centro está aplicando el instrumento de seguimiento |
| Numerador | Pacientes elegibles con un segundo TOP de fecha distinta | Pacientes con al menos un TOP de seguimiento |
| Denominador | Pacientes cuyo primer TOP tiene 90 o más días | Todos los pacientes ingresados del centro |
| De dónde sale | `pipeline/panel/seguimiento_core.py::calcular_seguimiento()` | `pipeline/panel/config.py::continuidad_por_centro()` |
| Cómo se rotula | **"Con seguimiento (TOP2)"** | Pendiente de decidir, nunca "% de seguimiento" a secas |
| Para qué se usa | Informes a los ministerios y comparación entre centros | Gestión: detectar centros que no aplican el instrumento |

**Sobre el rótulo de la cobertura.** "Con seguimiento" se conserva porque en
QALAT ya significa una cosa concreta y compartida: el paciente tiene al menos un
TOP con fecha distinta a la del ingreso. No es la etiqueta `etapa` del formulario
ni es el seguimiento clínico del caso, y los centros lo leen así. Se le agrega
`(TOP2)` entre paréntesis para que quien llega nuevo al sistema no tenga que
saberlo de antemano. Decidido por Rodrigo el 2026-09-10, sobre la propuesta de
llamarlo "% de cobertura de seguimiento", que se descartó por introducir un
término que nadie usa.

**El nombre "% de seguimiento" a secas queda prohibido para los dos.** Es el
nombre que tenían ambos, y por eso convivieron sin que nadie notara que daban
cifras distintas para lo que parecía la misma pregunta. Lo que los distingue es
el denominador, así que el rótulo de cada uno tiene que dejarlo ver: la tarjeta
de cobertura muestra "34 de 209 elegibles" con su nota al pie, y el operativo
tendrá que hacer lo equivalente sobre el total de ingresos.

**Fundamento.** La cobertura es la medida correcta para juzgar desempeño: un
centro que abrió hace dos meses no tiene a nadie a quien le corresponda todavía
la segunda medición, y medirlo sobre todos sus ingresos lo castiga por el
calendario. Pero el indicador bruto responde una pregunta que la cobertura no
puede responder, porque los pacientes recientes salen de su denominador: un
centro que nunca aplicó ningún TOP de seguimiento no entendió el instrumento o
no tiene el proceso montado, y eso es capacitación. Un centro que aplica algunos
y pierde pacientes en el camino tiene un problema de seguimiento de casos, y esa
es otra conversación con otra respuesta. Un solo indicador no distingue los dos
casos.

**Consecuencia asumida.** Los dos números conviven en el sistema y no coinciden,
y el bruto es siempre igual o menor. Por eso ninguna pantalla muestra uno sin su
rótulo completo, y toda visualización de cobertura lleva la nota fija de
`NOTA_SEGUIMIENTO`.

**Lo que esta decisión no autoriza.** Ninguna otra reimplementación del TOP2.
`semaforo_seguimiento.py`, `tiempo_top.py` y `config.py::continuidad_por_centro`
identifican hoy el TOP2 por la etiqueta `etapa`, que es exactamente lo que
`seguimiento_core` prohíbe. Los tres pasan a llamar al core: lo que distingue a
los dos indicadores es el denominador, no la definición de TOP2.

**Lo que esta decisión deja abierto.** El denominador de la cobertura son todos
los pacientes con 90 o más días desde su primer TOP, sigan o no en tratamiento,
de modo que quien abandonó a la tercera semana entra igual. La cifra mezcla
entonces cumplimiento del instrumento con retención. Excluir a quienes ya
egresaron o abandonaron es una decisión distinta, que sube el porcentaje y que
hay que tomar y fundamentar aparte. Mientras no se tome, el rótulo no debe
prometer más de lo que mide, y por eso dice "Con seguimiento" y no "Cobertura".

*2026-09-10*

---

## Datos

### En sustancias, un vacío es un cero
**Regla.** Los registros de sustancias sin dato se completan con cero. Son unos
1.115 valores, los que no tienen ni las semanas registradas.

**Fundamento.** El manual del TOP no contempla "no aplica" en la sección de
consumo: toda persona tiene un nivel de consumo, aunque sea cero, y es
clínicamente esperable que un paciente derivado de una unidad de desintoxicación
llegue en abstinencia.

**Aclaración.** El criterio clínico ya se aplicó a quienes sí escribieron sus
semanas: los 6.186 valores recuperados en la fase 2 son totales reconstruidos
sumando las semanas de pacientes que registraron ceros y cuyo total se había
perdido por el bug del formulario. Esta decisión extiende el mismo criterio a
los que no tienen semanas.

**Estado.** Pendiente de ejecución. En la base siguen en nulo.

*2026-09-02*

### El residuo de trabajo y educación se asume como ausente
**Regla.** Los registros sin dato en días de trabajo y días de educación quedan
en nulo. No se piden a los centros ni se rellenan.

**Fundamento.** En esos dos campos el instrumento sí contempla que la pregunta
no corresponda a la situación de la persona, y para eso existe la casilla "No
aplica". Un jubilado o alguien que ya concluyó sus estudios tiene que quedar en
nulo. Rellenar con cero diría que estuvo disponible y no asistió.

**Lo que sí es accionable.** Los vacíos se concentran en cuatro centros:
EESS28CI con 85,7 %, CET042967 con 53,3 %, SCE con 52,4 % y CJR con 36,8 %. Y
SVG, EESS28CI y CSP no marcan nunca la casilla. Eso no es dato perdido, es
capacitación.

*2026-09-02*

### Los días de trabajo y educación duplicados se anulan
**Regla.** En los 300 registros donde ambos campos tenían el mismo valor, se
anularon los dos. No se conservó ninguno.

**Fundamento.** El formulario de JotForm del pilotaje escribía en las dos tablas
a la vez: en el Excel original hay 303 registros con ambos valores y los 303
coinciden, sin una sola excepción. El perfil estadístico sugería que el valor
capturado era el de trabajo, pero un formulario mal configurado al punto de
escribir en dos tablas distintas no ofrece garantía sobre qué capturó
realmente. Un nulo declarado es preferible a un dato dudoso.

*2026-09-02*

---

## Seguridad

### Todo respaldo se crea con RLS activo y permisos revocados
**Regla.** Después de cada `CREATE TABLE ... AS SELECT`, se ejecuta
`ENABLE ROW LEVEL SECURITY` y `REVOKE ALL ... FROM anon, authenticated`, y se
verifica con `relrowsecurity`.

**Fundamento.** `CREATE TABLE AS` deja la tabla en el esquema `public`, que es el
que Supabase expone por PostgREST, y la tabla nueva no hereda las políticas de
la tabla de origen. Sin eso, una copia completa de los registros de pacientes
queda legible con la clave publicable que está en texto plano dentro de los
quince formularios.

*2026-09-02*

### Las protecciones se declaran, no se dejan por ausencia
**Regla.** Cada tabla lleva políticas explícitas para las operaciones que debe
denegar, aunque con RLS activo la ausencia de política ya bloquee.

**Fundamento.** Una tabla protegida solo porque nadie escribió una política se
abre el día que alguien agrega una de más sin darse cuenta. `top_registros` tiene
`deny_delete_all` explícito; `irt_registros` estaba protegida por ausencia y se
le agregó `deny_delete_irt`.

*2026-09-02*

### La app no borra registros de producción
**Regla.** Ninguna pantalla de la app ofrece borrar registros de pacientes. El
borrado masivo se hace desde el SQL Editor de Supabase, con respaldo previo,
conteo con la misma condición del `WHERE` y `RETURNING`. Se eliminó la pestaña
"Migración JotForm" completa, que era lo único que ofrecía borrado, junto con
`_migrar_excel_jotform`, `_insertar_lote_supabase` y `_eliminar_por_pais`, y de
paso las dos funciones muertas `_actualizar_registro` y `_eliminar_registro`.

**Fundamento.** La pestaña era andamiaje de la migración desde JotForm: su
propio aviso decía "úsalo para pruebas de migración y bórralo después", y su
título ya llevaba "(obsoleta)". Lo que quedaba vivo era un botón que borraba
todos los registros de un país entero, protegido solo por escribir la palabra
BORRAR en una caja de texto y disponible para cualquiera con la clave UNODC, en
la misma pantalla donde se trabaja todos los días. La protección correcta de una
operación irreversible sobre datos de pacientes no es una confirmación mejor: es
que la operación no esté ahí. Además, las tres funciones que se van devolvían el
código HTTP y nadie lo miraba, de modo que el "✓ Todos los registros eliminados"
aparecía igual aunque Supabase hubiera rechazado la llamada, el mismo patrón que
se corrigió el 1 de septiembre en el formulario de corrección.

**Verificado antes de sacarlo.** Búsqueda en todo el repositorio: las cinco
funciones se llamaban únicamente desde dentro de esa pestaña, y
`_actualizar_registro` y `_eliminar_registro` no se llamaban desde ningún lado
desde `e176885`. Las 102 pruebas siguen pasando.

**Consecuencia asumida.** Recargar datos históricos desde un Excel de JotForm ya
no se puede hacer desde la app. Si vuelve a hacer falta, se recupera del
historial de git; la migración de los cuatro países ya está hecha.

*2026-09-10*

---

## Arquitectura

### No se renombran las claves del runner
**Regla.** Las claves `pdf_caract` y `pdf_seg` se mantienen, aunque apunten a
`word_caract.py` y `word_seg.py`.

**Fundamento.** El nombre quedó de cuando esos reportes se generaban en PDF.
Renombrarlas obliga a cambiar `runner.py`, `app.py` y `reportes_centro.py` a la
vez, y eso ya produjo dos bugs: un KeyError al descargar el Word y el ícono del
archivo saliendo con el color equivocado. No vale la pena por un nombre.

*2026-09-01*

### `validacion_top.py` es la única fuente de criterios de validación
**Regla.** Ningún módulo implementa su propio criterio de rango, normalización o
clasificación. Todo vive en `pipeline/validacion_top.py` y los demás lo importan.

**Fundamento.** Antes cada consumidor reimplementaba su versión, y eso produjo
el peor error del sistema: seis módulos leían el sexo como H igual hombre y dos
lo leían como M igual masculino, de modo que ningún país quedaba bien contado en
ambos lados. El panel mostraba cero mujeres en tres países y los informes de
Perú reportaban 85 % de mujeres.

*2026-08-28*

---

## Reglas de mantenimiento

1. **Ningún commit de código se cierra sin su línea en `CHANGELOG.md`, en el
   mismo commit.** Si queda para después, no se hace.
2. **Toda decisión que cierre una discusión entra en `DECISIONES.md` el mismo
   día**, con su fundamento. Una decisión sin fundamento escrito se rediscute en
   tres semanas.
3. **El handoff se genera a partir de estos dos archivos, no al revés.** Si un
   handoff dice algo que no está acá, falta la entrada; no se corrige el handoff.
