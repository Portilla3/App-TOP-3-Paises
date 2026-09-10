# QALAT · Incidentes en producción

Lo que se rompió estando en uso, con su causa, su arreglo y lo que se aprendió.
Se escribe el mismo día del incidente.

Un incidente entra acá cuando afectó a un usuario, aunque el arreglo haya sido
de una línea. Los defectos encontrados en revisión, que nadie alcanzó a sufrir,
van en `CHANGELOG.md`.

Formato de cada entrada: quién avisó, síntoma, causa, arreglo con su commit,
costo asumido y lección. La lección es la parte que sirve; lo demás es registro.

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
