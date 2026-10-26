# QALAT · Incidentes en producción

Lo que se rompió estando en uso, con su causa, su arreglo y lo que se aprendió.
Se escribe el mismo día del incidente.

Un incidente entra acá cuando afectó a un usuario, aunque el arreglo haya sido
de una línea. Los defectos encontrados en revisión, que nadie alcanzó a sufrir,
van en `CHANGELOG.md`.

Formato de cada entrada: quién avisó, síntoma, causa, arreglo con su commit,
costo asumido y lección. La lección es la parte que sirve; lo demás es registro.

---

## 2026-07-01 (detectado 2026-10-26) · Los formularios dejaron de tener las mismas reglas

**Quién avisó:** nadie. Apareció al comparar los errores graves por país: México
en cero y los otros tres países entre 4 y 7 %.

**Síntoma:** en Perú, Ecuador y El Salvador se pueden guardar TOP cuyo código no
coincide con la fecha de nacimiento. En los cuatro formularios de México, no.

**Causa:** el 1 de julio de 2026 se agregó la validación cruzada entre código y
fecha de nacimiento. En México quedó como bloqueo al guardar
(`validarCruceCodigoFecha(false)` en la validación del envío, commits 34c78b4 y
c1f5220). En Perú, Ecuador y El Salvador quedó solo como aviso al salir del campo
(commits c564eaf, 8510ee4 y a90d8f5). Monte Fénix y Mahanaim se copiaron del
formulario de México el 14 y el 16 de julio y heredaron el bloqueo. De fondo: hay
siete copias del formulario en dos familias de código distintas, y cada regla se
escribe siete veces.

**Efecto:** 78 TOP con el código distinto de la fecha de nacimiento entre junio y
octubre, todos en los tres países que solo avisan, salvo 2 de IMSS-Bienestar
cargados antes del bloqueo.

**Arreglo:** pendiente de autorización. Paso inmediato: el mismo bloqueo en
`index.html`, `index_ecuador.html` e `index_elsalvador.html`. Paso de fondo: las
validaciones en un solo archivo que carguen los siete formularios.

**Lección:** una regla del formulario se cambia en los siete a la vez, o no se
cambia. Revisado el 26 de octubre: el formato del código, los campos
obligatorios, las fechas (no futura, no anterior a 2020, nacimiento antes de la
entrevista), la edad de 5 a 100 años y "al menos una semana por sustancia" son
iguales en los siete. No se revisó todo lo demás.

---

## 2026-10-25 · La migración de JotForm tomó mal cuatro campos · cerrado el 2026-10-26

**Quién avisó:** nadie. Apareció al revisar los duplicados de SJA: la copia del
piloto tenía salud psicológica 0 y la copia del formulario 15, 9, 20 y 10.

**Síntoma:** en los registros que entraron por la migración de JotForm (Perú el
19 de mayo, El Salvador el 5 de junio; 402 registros, 322 de ingreso), la salud
psicológica casi siempre es 0 y, cuando no lo es, ronda 2.

| Grupo | Registros | Salud psicológica en 0 | Promedio si no es 0 |
|---|---|---|---|
| El Salvador, migración | 319 | 85,9 % | 2,0 |
| El Salvador, formulario | 584 | 1,1 % | 14,2 |
| Perú, migración | 83 | 52,6 % | 2,6 |
| Perú, formulario | 480 | 1,0 % | 10,7 |

Salud física y calidad de vida de esos mismos registros están bien (menos de
1,5 % en 0). Ecuador, migrado el 1 y 2 de junio, no tiene el problema.

**Causa:** la función de migración, ya retirada (`_migrar_excel_jotform`,
commit 631d2f8, `app.py` línea 331), tomaba la primera columna del Excel cuyo
nombre contuviera "psicol". En los Excel de JotForm esa columna es "4) Violencia
Intrafamiliar (Maltrato físico o psicológico) >> Última Semana (0-7)", no "6)
Calificar el estado de salud psicológica". Confirmado el 26 de octubre con los
Excel originales: en los 402 registros el valor de la base era exactamente el de
la semana 4 de violencia intrafamiliar.

**Efecto:** la línea base de salud psicológica sale más baja de lo real. En
ingresos de El Salvador el promedio es 9,6 con los migrados y 13,4 sin ellos;
en Perú, 9,1 y 10,0. Lo más delicado es el seguimiento: un paciente migrado con
0 al ingreso y 14 en el seguimiento aparece con una mejoría que no existió.

**Arreglo:** 26 de octubre de 2026, con autorización de Rodrigo. Se recuperó el
valor correcto de los Excel originales (`TOP_Perú2026-04-22_19_43_54.xlsx`, 83
filas, y `TOP_ElSalvador_LIMPIA.xlsx`, 319 filas). Los ids de cada lote siguen
el orden de las filas del Excel (Perú 374 a 456, El Salvador 545 a 863), y se
comprobó con una huella md5 de id, código y valor anterior antes de tocar nada;
10 registros con la fecha corregida después de la migración quedaron
identificados igual. Respaldo en `backup_salud_psicologica_migracion_20261026`
(402 filas, RLS activo, sin permisos para anon ni authenticated). El UPDATE
devolvió 402 filas, la huella posterior coincide con la esperada y cambiaron 400
valores (2 ya coincidían). La consulta está en
`sql/correcciones/2026-10-26_salud_psicologica_migracion.sql`.

Resultado: los registros migrados pasan a tener 0,3 % de ceros en El Salvador y
0 % en Perú, con promedios de 14,1 y 11,7, en línea con los cargados por
formulario (14,0 y 10,6). El promedio al ingreso sube de 9,6 a 13,5 en El
Salvador y de 9,1 a 10,2 en Perú.

**Los otros campos, revisados el 26 de octubre.** Se volvió a ejecutar sobre los
Excel la función de migración tal como estaba ese día (commit 27db6a6 para Perú,
01c86c4 para El Salvador) y se comparó campo por campo con lo que dicen las
columnas correctas. Aparecieron tres errores más; el resto (sustancias, VIF,
salud física, calidad de vida, vivienda, hurto, venta, peleas, otra acción,
sustancia principal) coincide.

- Días de educación: la función buscaba "colegio" o "educación", palabras que
  también están en el enunciado de las columnas de trabajo, y copió los días de
  trabajo en educación en los 402. El 2 de septiembre se anularon ambos en 302
  registros creyendo que era un defecto de JotForm, lo que borró los días
  trabajados de todos los que trabajaban.
- Robo: la función tomó la primera columna que contenía "robo", que era la de
  hurto ("hurtos, robos…"). Robo era idéntico a hurto en los 402.
- El texto "nan" quedó escrito en 215 nombres de otra sustancia y 336
  descripciones de otra acción.

**Arreglo de los tres, 26 de octubre, con autorización de Rodrigo.** Respaldo en
`backup_migracion_trabajo_robo_20261026` (402 filas, RLS activo, sin permisos).
UPDATE de trabajo, educación y robo: 402 filas, huella posterior igual a la
esperada; cambiaron 310 registros en trabajo o educación y 13 en robo (12 de
Perú, 1 de El Salvador). Los bloques con valores imposibles quedaron en blanco:
29 de trabajo y 1 de educación, todos de El Salvador. Los "nan" pasaron a NULL
(215 y 336). El porcentaje que trabajaba al ingreso queda en 77,1 % en El
Salvador (era 69,0 %) y 72,8 % en Perú (era 68,2 %). SQL en
`sql/correcciones/2026-10-26_migracion_trabajo_educacion_robo.sql`. La regla del
2 de septiembre sobre días duplicados quedó reemplazada en `DECISIONES.md`.

**Lección:** una migración se verifica comparando la distribución de cada
variable contra los datos que entran por el formulario, no solo contando filas.
Y buscar columnas por palabras sueltas es frágil cuando los enunciados repiten
palabras: tres de los cuatro errores salieron de ahí. Antes de corregir un dato
"raro", hay que mirar la fuente original: la anulación de septiembre partió de
un supuesto que el Excel de JotForm desmentía.

---

## 2026-10-08 y anteriores · Centros que no logran entrar al sistema

**Quién avisó:** nadie. Apareció al revisar `centro_bitacora` desde el chat de
correos, buscando otra cosa.

**Síntoma:** 31 intentos de login fallidos entre el 27 de agosto y el 8 de
octubre, de seis centros de El Salvador y uno de Perú.

**Causa:** son tres causas distintas, y conviene no confundirlas porque cada una
se arregla de otra forma.

| Qué pasó | Intentos | Textos |
|---|---|---|
| Escribieron el código bien y falló la clave | 12 | CJR, CMM, CSP, EESS09H, SCE, SJA |
| Escribieron el código en minúscula | 4 | `csp`, `Csp`, `sja` |
| Pegaron texto desde WhatsApp o escribieron a ciegas | 15 | `SJA🇸🇻  El Sa`, `CSPCCCSPSPSPCCSP` |

El caso del 16 de septiembre es el más claro: SJA hizo catorce intentos pegando
`SJA🇸🇻  El Sa`, que es una línea de WhatsApp con la bandera arrastrada.

**Ningún centro quedó bloqueado.** Los siete que fallaron entraron después:

| Centro | Fallos | Éxitos | Último fallo | Último ingreso |
|---|---|---|---|---|
| CSP | 5 | 10 | 8 oct | 15 oct |
| CMM | 4 | 3 | 8 sep | 8 oct |
| SJA | 2 | 11 | 8 oct | 8 oct |
| SCE | 2 | 4 | 8 sep | 8 oct |
| CJR | 2 | 6 | 31 ago | 8 oct |
| EESS09H | 1 | 3 | 27 ago | 9 sep |

Eso reordena la gravedad. Los doce fallos por clave son tropiezos normales de
login: se equivocaron una o dos veces y acertaron. El único episodio con costo
real es el del 16 de septiembre, cuando SJA perdió catorce intentos seguidos
pegando texto de WhatsApp antes de dar con el formato correcto.

**Arreglo:** parcial. La comparación del código dejó de distinguir mayúsculas
(migración `login_centro_insensible_a_mayusculas`), lo que resuelve 4 de los 31.

**Lo que no está arreglado, y es lo más frecuente:**

Los 15 intentos con texto pegado siguen fallando. `trim()` quita espacios, no
emojis ni palabras de más. La forma de resolverlos sería extraer el primer grupo
alfanumérico de lo que escriban: `SJA🇸🇻  El Sa` se convertiría en `SJA`. Los
códigos de centro son todos alfanuméricos, así que no hay riesgo de recortar uno
legítimo. Eso resolvería 14 de esos 15.

Los 12 fallos por clave no necesitan arreglo: los seis centros acertaron en el
intento siguiente. Lo que sí conviene es mirar esta tabla cada cierto tiempo. Un
centro que acumule fallos sin un éxito posterior sí estaría bloqueado, y hoy no
hay ninguno, pero nadie se enteraría si lo hubiera.

**Sobre el diagnóstico de "campo de texto invisible":** el CSS del login pinta el
texto en blanco sobre el panel azul oscuro, y se arregló el 28 de agosto. Los
fallos del 16 de septiembre ocurrieron cuando la app no se autodesplegaba, así
que pudieron darse con la versión vieja. Pero `CSPCCCSPSPSPCCSP` es del 8 de
octubre, con el despliegue ya arreglado, y ese mismo día el mismo usuario
escribió `Csp` y `CSP` correctamente. El dato no alcanza para confirmar ni para
descartar que el campo siga siendo ilegible en algún dispositivo. Hay que mirarlo
en vivo, en el móvil de alguien de El Salvador.

**Lecciones.**

Contar fallos sin mirar si hubo un éxito después lleva a conclusiones falsas. La
primera lectura de estos datos, hecha el 2026-10-19, concluyó que seis centros
llevaban semanas sin poder entrar. La consulta siguiente mostró que los seis
habían entrado, algunos el mismo día. El número de fallos no dice nada por sí
solo: lo que importa es si el último intento de cada centro fue exitoso.

Aun así, nadie estaba mirando esa bitácora. Si un centro quedara realmente
bloqueado, no abriría un ticket: dejaría de intentar, y la única señal estaría
ahí.

Guardar lo que la persona escribió, y no solo que falló, es lo que permitió
separar las tres causas. Sin esa columna, el diagnóstico habría sido "fallan los
logins" y el arreglo habría apuntado al lugar equivocado.

---

## 2026-09-10 · La app sirvió código viejo: los pushes no se despliegan solos

**Nadie avisó.** Salió al verificar en vivo el cambio del mismo día.

**Síntoma.** Se hicieron seis commits a `main` entre el 9 y el 10 de septiembre y
ninguno llegó a la app. El código en producción seguía siendo el del 9 a las
22:45. Durante todo el 10 de septiembre, la pestaña de migración y su botón de
borrado por país siguieron vivos para cualquiera con la clave UNODC, varias horas
después de que se eliminaran del repositorio.

**Evidencia.** El log de Manage app registra una sola línea de
`Pulling code changes from Github`, la del arranque del contenedor el 2026-09-09
a las 22:45. Ninguna más, con el contenedor vivo y registrando actividad hasta
las 16:21 del día siguiente.

**Lo que no es la causa.** El webhook de GitHub existe, apunta a
`https://share.streamlit.io/hook`, escucha `push` y declara "Last delivery was
successful". GitHub entrega. El problema está del lado de Streamlit, que recibe
el aviso y no actúa.

**Causa, todavía sin confirmar.** La hipótesis en pie es el renombre del
repositorio: la app está registrada en Streamlit Cloud como
`portilla3/qalat-top-ecuador` y el payload del webhook viaja con
`Portilla3/App-TOP-3-Paises`. Falta ver el historial de entregas del webhook, que
exige reautenticación por correo en GitHub.

**Arreglo aplicado.** Reboot manual desde Streamlit Cloud. El log muestra clon
nuevo a las 17:05:34 del 10 de septiembre. Es un parche: despliega una vez y deja
la causa intacta.

**Por qué solo pasa en esta app.** De las cuatro, tres duermen por inactividad y
una app dormida clona de cero al despertar, así que siempre sirve código fresco.
Esta es la única en uso continuo y por eso la única donde el defecto se
manifiesta. No es que las otras estén sanas: es que el problema no puede
aparecer mientras nadie las use a diario.

**Verificación posterior al reboot.** Cuatro pestañas y ninguna de migración.
Panel de gestión con datos. Respaldos genera el Excel y crea el snapshot.
CET021098 arma sus tres reportes de ingreso. SAI001021 responde con la nota
informativa "No hay registros de ingreso (TOP1)" y no con un error rojo.

**Lecciones.**

- Commit no es despliegue. Entre `main` y lo que ve un país hay un paso que puede
  fallar en silencio, y falló durante un día completo sin que nada lo indicara.
- El incidente del 9 de septiembre anotó que "la app sigue sirviendo el commit
  viejo" como consecuencia de un despliegue roto. Era más general que eso: puede
  pasar con el despliegue sano.
- Después de tocar código en producción, mirar la hora del último
  `Pulling code changes` en el log. Es el único lugar donde se ve qué está
  corriendo de verdad.

---

## 2026-09-10 · Un registro de paciente completo se mostraba en pantalla

**Nadie avisó.** Salió al revisar la pestaña de migración antes de eliminarla.
Por eso esta entrada existe: sin ella no queda constancia de que se detectó.

**Qué pasaba.** En la pestaña "Migración JotForm", al subir un Excel y pulsar
"Preparar registros para migración", la app imprimía en pantalla, bajo el rótulo
"Primer registro construido (debug)", el diccionario completo del primer registro
del archivo. Es decir: país, centro, código del paciente, fecha de nacimiento,
fecha de entrevista, sexo, etapa, y todas sus respuestas de consumo de sustancias
y del resto del TOP. Un registro clínico entero de una persona, con su fecha de
nacimiento, que junto al centro y la fecha es un cuasi identificador.

**Desde cuándo y quién lo veía.** Desde el commit `0c15228`, del 6 de abril de
2026. Cinco meses. La pestaña estaba detrás de `es_unodc`, así que solo la veía
quien tuviera la clave UNODC.

**Lo que hay que decir para no exagerarlo.** Solo se imprimía después de que
alguien subiera ese mismo Excel, así que el dato mostrado era un dato que la
persona ya tenía en la mano. No hubo acceso de nadie a información que no
tuviera. El riesgo real no era el acceso sino la superficie: quedaba en pantalla,
en una sesión que se comparte en reuniones y de la que se sacan capturas, sin que
hiciera falta para nada. Una línea de depuración que nunca debió salir del
desarrollo.

**Arreglo.** Desapareció con la pestaña completa, commit `c647b41`, 10 de
septiembre de 2026. No se parchó: se eliminó el módulo entero por la decisión
"La app no borra registros de producción" de `DECISIONES.md`.

**Lecciones.**

- Un `st.json` de depuración es una decisión de diseño mientras se desarrolla y
  una exposición de datos en cuanto se despliega. La app no tiene ninguna
  pantalla que necesite mostrar un registro individual completo, y no debería
  tenerla.
- Cinco meses sin que nadie lo notara mide lo que se mira una pestaña marcada
  como obsoleta. Un módulo que se deja "por si acaso" no se revisa.
- Esto no lo encontró una prueba ni un usuario. Lo encontró leer el código que se
  iba a borrar. Ese es el argumento para borrar en vez de ocultar.

---

## 2026-09-09 · Reportes caídos en Ecuador

**Avisó** Belén Estrella, Ministerio de Salud de Ecuador, el 3 y de nuevo el 9
de septiembre.

**Síntoma.** La descarga de reportes fallaba en algunos centros, con tres
mensajes distintos: `TypeError: '>' not supported between instances of
'NoneType' and 'float'` en CET021097 y CET021098, `operation 'rsub' not
supported for dtype 'str' with dtype 'int64'` en SAI001021, y
`KeyError: '_episodio'` en SAI001021 con filtro de periodo.

**Causa.** Cuatro defectos, no uno.

1. `pipeline/word_caract.py`, sección 2.4: una sustancia sin ningún consumidor
   en el centro llega con `prom=None` y `max()` la comparaba contra un float. La
   sección 2.2 del mismo archivo ya filtraba esos casos. Se arregló una copia y
   no la gemela.
2. `pipeline/wide_top.py`, hoja "Por Centro": con un centro sin ningún TOP de
   ingreso la base wide sale vacía, la agregación devuelve `Con_TOP2` como
   columna de texto y la resta `Pacientes - Con_TOP2` aborta. Defecto dormido
   desde hacía meses: con pandas 2 devolvía vacío en silencio, con pandas 3 más
   pyarrow lanza excepción. Entró por el `requirements.txt` acotado solo por
   major el 8 de septiembre.
3. `KeyError: '_episodio'`: misma condición que el punto 2, pero en el commit
   `c134f29` que la app seguía sirviendo. Ya estaba corregido en `main` por
   `33308e7` del 2 de septiembre.
4. Encontrado durante la revisión, nadie lo había reportado:
   `pipeline/pptx_caract.py` usaba una variable `labs` inexistente, regresión de
   `cdb9e56`. El PowerPoint de ingreso fallaba para cualquier centro con datos
   de edad, en todos los países.

**Arreglo.** Diez commits. PR #1, merge `ec60a52`, siete archivos con las
correcciones y con guardas de N=0 en los seis módulos de reporte. Después
`0234eda`, `b983cb0` y `6c460f8`: la falta de datos de un centro se muestra como
nota informativa y no como error rojo, con el clasificador `es_falta_de_datos()`
en `pipeline/runner.py`, en un solo lugar.

**No era un defecto.** SAI001021 tiene 2 registros TOP, ambos con etapa
`en_tratamiento`, y ninguno de ingreso. Sin TOP de ingreso no hay caracterización
posible. Es el único centro de Ecuador en esa condición.

**Verificación.** 222 generaciones de reporte sobre datos reales de tres países
y 34 centros, sin ninguna excepción técnica. Las 102 pruebas de
`tests/test_decisiones.py` siguen pasando. Informe completo en
`claude/INFORME_INCIDENTE_2026-09-09.md`.

**Lecciones.**

- La lógica duplicada en los seis módulos de reporte es la causa de fondo. Dos
  de los cuatro defectos son una corrección aplicada a un archivo y no a su par.
- Ninguna de las 102 pruebas genera un reporte. Verifican criterios de cálculo,
  no que el Word o el PPT se armen. Por eso nadie lo detectó antes que Ecuador.
- Para reproducir el defecto 2 hace falta pyarrow instalado. Sin pyarrow, pandas
  cae a otro backend y el error no aparece.
- Los números de línea de un traceback sirven para identificar qué commit está
  desplegado. Así se descubrió que la app servía código del 2 de septiembre.

---

## 2026-09-08 · Las cuatro apps caídas

**Avisó** Gloria, El Salvador. La caída venía desde el fin de semana.

**Síntoma.** "Oh no. Error running app", y en el log "Error installing
requirements". El contenedor nunca levantaba.

**Causa.** Un `packages.txt` sin uso real en los cuatro repositorios, herencia
de cuando las presentaciones se generaban con JavaScript. Hoy se generan con
`python-pptx`. Su sola presencia obliga a Streamlit Cloud a correr `apt-get`, y
la imagen base arrastra una fuente de Debian 11 bullseye con la firma vencida.
El despliegue moría antes de instalar una sola línea de Python. El mensaje de
pantalla decía "requirements" y despistaba.

**Arreglo.** Eliminar `packages.txt` de los cuatro repositorios, commit
`0e456a6`. Después se acotaron los `requirements.txt` por major, commit
`167a730`, con los pisos leídos del log de ese día.

**Costo asumido explícitamente.** Acotar por major deja entrar un major nuevo
sin aprobación. Ese costo se cobró al día siguiente: pandas 3 entró solo y
activó el defecto 2 del incidente del 9 de septiembre.

**Lecciones.**

- Si un despliegue de Streamlit falla, leer el log completo en Manage app antes
  de tocar `requirements.txt`. El mensaje de pantalla no identifica la etapa que
  falló.
- Mientras el despliegue está roto, la app sigue sirviendo el commit viejo. Los
  países reportan errores sobre una versión que ya no es la de `main`. Estuvo
  así seis días.
- Verificar que una app arranca no es verificar que funciona.
