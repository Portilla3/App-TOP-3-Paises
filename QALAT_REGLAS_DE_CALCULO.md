# QALAT · Reglas de cálculo

Cómo se cuenta cada cosa en este sistema, y por qué. Última revisión: 2 de
septiembre de 2026.

Este documento no describe el estado del proyecto ni lo que falta hacer: eso
vive en el documento de estado. Acá están solo los criterios, que cambian mucho
menos y que hay que respetar al programar cualquier reporte, gráfico o consulta.

**Si una regla de acá se rompe, el sistema avisa.** Cada una tiene su prueba en
`tests/test_decisiones.py`, ciento dos en total, que se corren con
`python -m pytest tests/ -v`. Escribir la regla no alcanzó nunca: la convención
del sexo estaba escrita desde el 28 de agosto y seis módulos la incumplían, y la
regla de que `validacion_top.py` es la única fuente de criterios estaba escrita
el mismo día mientras el clasificador de sustancias seguía copiado en diez
archivos. Lo que hace que una regla no se olvide es que algo falle cuando se
rompe.

**Dónde vive cada criterio.** Todos en `pipeline/validacion_top.py`. Ningún
módulo implementa el suyo. Si hace falta un criterio nuevo, se agrega ahí y los
demás lo importan.

---

## 1. A quién se cuenta

### La unidad es el episodio de tratamiento, no la persona

Quien ingresa dos veces al mismo centro, o a dos centros distintos, cuenta dos
veces. Cada TOP con etapa de ingreso abre un episodio, identificado por
`código | centro | fecha del TOP de ingreso`. Los TOP siguientes del mismo
paciente en el mismo centro pertenecen a ese episodio hasta que aparezca otro
ingreso.

**Por qué.** Los informes son para que el centro vea su propia operación. Un
paciente que egresó y volvió es una atención nueva desde el punto de vista del
centro, y contarlo una sola vez esconde trabajo hecho. Es el criterio del NDTMS
británico, de donde viene el instrumento, y el que se usa en Chile.

**Cuánto cambia.** Al 2026-09-02, 47 pacientes tienen más de un TOP de ingreso
en el mismo centro y 4 códigos aparecen en más de un centro. Personas únicas da
1.326 y episodios 1.330. La diferencia crece con el tiempo.

**Lo que se conserva.** El código de paciente sigue en la base, así que contar
personas únicas cuando haga falta es una consulta, no un recálculo.

`construir_episodios()` · `lineas_base()`

### La línea base es el TOP con etapa de ingreso, y solo ese

Los pacientes sin ningún TOP de ingreso quedan fuera de la caracterización y del
análisis de cambio. No se los recupera tomando su TOP más antiguo.

**Qué significa ingreso.** El ingreso real al centro, no la primera vez que se
le aplica el instrumento. Una persona que lleva seis meses atendiéndose y recién
ahora recibe su primer TOP no está ingresando: esa etapa es `en tratamiento` y
está bien puesta. Un derivado desde otro centro o desde una desintoxicación sí
está ingresando, porque ingresa a ese centro.

**Por qué.** La caracterización responde cómo llegan los pacientes al centro. Un
TOP aplicado a mitad del tratamiento no describe cómo llegó esa persona, así que
usarlo como línea base fabricaría un dato que nadie midió. Es preferible un N
más chico y honesto que uno completo y falso.

**Costo asumido.** Al 2026-09-02 quedan fuera 182 pacientes, el 13,7 %. El
reparto es desigual: México pierde el 34,5 %, Perú el 15,5 %, El Salvador el
11,8 % y Ecuador el 9,8 %. Tres centros quedan sin ningún paciente en su informe
y EESS28CI queda con dos de dieciocho.

Para el análisis de cambio el costo es mucho menor: de esos 182, solo 11 tienen
una segunda medición, así que los otros 171 nunca iban a servir para comparar
TOP 1 contra TOP 2.

**Por qué es aceptable.** Buena parte de esos casos no son un error de captura.
Cuando un centro adopta el TOP, su cohorte ya está en curso, y esos pacientes son
legítimamente `en tratamiento`. México empezó a registrar en mayo de 2026 con
gente que ya atendía. Nunca tuvieron línea base y no la van a tener.

### La sustancia principal se toma siempre del TOP 1

En cualquier análisis de evolución, la sustancia principal es la declarada al
ingreso, aunque el paciente declare otra en el seguimiento.

**Por qué.** El ingreso es la línea base contra la que se mide el cambio. Si la
sustancia principal cambiara entre mediciones, el paciente saltaría de una
categoría a otra y el análisis dejaría de comparar a la misma persona consigo
misma. Que un paciente cambie de sustancia principal es un dato en sí mismo,
pero no para esta tabla.

---

## 2. El denominador

### Todo porcentaje se calcula sobre los casos con dato válido

Ningún porcentaje ni promedio cuenta en su denominador a un paciente que no
tenía el dato. **Qué cuenta como dato válido depende de la pregunta**, porque la
ausencia significa cosas distintas según lo que se preguntó:

| Sección | Un vacío significa | ¿Entra al denominador? |
|---|---|---|
| Consumo de sustancias | cero | **sí** |
| Días de trabajo y educación | no aplica | no |
| Transgresión (Sí/No) | no se respondió | no |
| Sexo | no se respondió | no |
| Sustancia principal | no se declaró | no |

**Por qué la excepción de sustancias.** El manual del TOP no contempla "no
aplica" en la sección de consumo: toda persona tiene un nivel de consumo aunque
sea cero, y es clínicamente esperable que un paciente derivado de una unidad de
desintoxicación llegue en abstinencia. Además, los vacíos que hay vienen del bug
del formulario que borró los ceros durante cinco meses. Sacarlos del denominador
excluiría a quienes sí respondieron, y respondieron cero: la prevalencia de
marihuana en Perú pasaría de 10,5 % a 23,2 % sin que nadie hubiera empezado a
consumir.

**Por qué trabajo y educación sí se excluyen.** Ahí el instrumento contempla que
la pregunta no corresponda, y para eso existe la casilla "No aplica". Un jubilado
o alguien que ya concluyó sus estudios tiene que quedar en nulo. Rellenar con
cero diría que estuvo disponible y no asistió.

**Todo gráfico muestra el N sobre el que se calculó.** Si el N válido difiere del
total de personas, el pie lo dice: cuántas ingresaron y sobre cuántas se calculó.

---

## 3. Sustancias

### La lista cerrada del formulario de cada país es la taxonomía

Lo que se declare fuera de esa lista cae en `Otra sustancia`, que tiene columna
de días propia (`otra_sust_total`) y su propio campo de texto
(`otra_sust_nombre`). Heroína en Ecuador es Heroína; heroína en México es Otra
sustancia.

**Por qué.** La lista del formulario coincide con las columnas de días que ese
país mide. Una categoría sin columna no puede tener barra: quedaría vacía o con
un cero falso. Y no es una decisión de análisis, es leer lo que el instrumento ya
hizo: un mexicano no puede elegir heroína, no está en su lista, así que la
escribió en el campo de otra sustancia.

| | Perú | Ecuador | El Salvador | México |
|---|---|---|---|---|
| | Alcohol | Alcohol | Alcohol | Alcohol |
| | Marihuana | Marihuana | Marihuana | Marihuana |
| | Pasta Base | Pasta Base/basuco | **Crack** | **Metanfetamina (cristal)** |
| | Cocaína | Cocaína | Cocaína | **Cocaína/crack (piedra)** |
| | Sedantes | Sedantes | Sedantes | Sedantes |
| | | **Heroína** | | |
| | Otra sustancia | Otra sustancia | Otra sustancia | Otra sustancia |

Seis categorías por país, siete en Ecuador. Siempre la última es Otra sustancia.

`CATEGORIAS_POR_PAIS` · `clasificar_sustancia(texto, pais)`

### La etiqueta es la del formulario de ese país

México ve "Cocaína/crack" y Ecuador "Pasta Base/basuco". La etiqueta cambia; la
categoría con que se calcula, no. En México "crack" y "cocaína" apuntan a la
misma columna, `cocaina_total`, porque su formulario las pregunta juntas.

No hay problema de comparabilidad regional porque no se generan reportes
regionales automáticos: esos se arman a mano.

`ETIQUETAS_POR_PAIS` · `etiqueta_sustancia(categoria, pais)`

### La categoría se llama Heroína, no Opiáceos

Ecuador pregunta "Heroína" en su formulario, así que esa es la etiqueta. La
categoría captura solo heroína; morfina, fentanilo, tramadol y metadona caen en
Otra sustancia, porque ningún formulario los pregunta. Verificado que no existe
ninguno de esos cuatro en la base.

### Lo que no nombra una sustancia no es "Otra sustancia", es ausencia de dato

`ninguna`, `niega`, `ludopatía`, `N`, `-`, `nan`, `s/d` y la errata `minguna`
devuelven nulo y quedan fuera del denominador. Las respuestas de una o dos letras
se comparan exactas: como subcadena, `n` o `no` aparecerían dentro de casi
cualquier nombre de sustancia.

### En sustancia principal entran todos con sus ceros; en cualquier sustancia solo los consumidores

Los gráficos de sustancia principal, el promedio de días y la clasificación del
cambio, incluyen a todos los pacientes que la declararon como principal, con sus
ceros. Los gráficos que recorren todas las sustancias promedian solo entre
quienes las consumieron, y el porcentaje de consumidores va al lado.

**Por qué.** Son dos preguntas distintas. En la sustancia principal, un cero
significa que la persona ingresó en abstinencia de su propia droga problema, y
ese es su dato real. En el gráfico de todas las sustancias, incluir a quienes no
la consumen convierte el número en una función de la composición de la
población: un centro que atiende más alcohólicos mostraría menos consumo de
cocaína aunque sus consumidores de cocaína consuman igual. Quien deja de
consumir no desaparece del reporte, aparece como una caída de la prevalencia.

### No se distingue abstinencia de nunca consumió al ingreso

El TOP mide consumo en las últimas cuatro semanas, no historia de consumo, así
que el instrumento no captura el dato que permitiría separarlos. El sistema
inglés lo resuelve con un registro de admisión aparte que la versión regional no
tiene. Agregar esa pregunta sería modificar el instrumento.

---

## 4. Los gráficos

### Se muestran todas las categorías del país, siempre

Tanto los de prevalencia como los de promedio de días dibujan las seis
categorías del país, siete en Ecuador, aunque alguna venga en cero.

**Por qué.** Elegir las más frecuentes hacía que los dos gráficos mostraran
sustancias distintas, y ya produjo el caso de Sedantes apareciendo en el de días
y no en el de prevalencia, y de Tusi apareciendo como categoría propia en Perú.
Con la lista fija son comparables entre centros, entre países y en el tiempo.

### Los gráficos de promedio llevan el n bajo cada barra

Al mostrar todas las categorías, una barra de siete pacientes se dibuja igual de
alta que una de trescientos. Sin el n se leen con el mismo peso.

### El sexo tiene tres categorías

Hombre, Mujer y Otro, aunque alguna venga en cero. "Otro" es una respuesta, no un
dato faltante, así que entra al N válido. Al 2026-09-02 hay dos personas que la
eligieron, una en Perú y una en Ecuador.

### Los rótulos del cambio no hablan de mejoría

Se dice "disminuyó" y "aumentó", no "mejoró" ni "empeoró". Ver la regla del
índice de cambio fiable.

---

## 5. Convenciones de los campos

### El campo sexo usa H/M/O en los cuatro países

`H` es hombre, `M` es mujer, `O` es otro. Los quince formularios escriben esa
convención y la base está homologada.

**Por qué.** Convivían dos convenciones opuestas: Perú escribía M para masculino
y F para femenino, y los otros tres H para hombre y M para mujer. Como la letra
`M` significaba cosas distintas según el país, ningún cálculo podía resolverlo
sin saber el origen del registro. Se eligió H/M/O porque ya era la convención de
tres de los cuatro países y de unos 900 de los 1.400 registros.

Fue el peor error del sistema: el panel mostraba cero mujeres en tres países y
los informes de Perú reportaban 85 % de mujeres.

`normalizar_sexo()` · `normalizar_sexo_valor()`

### Los rangos de edad cuentan años cumplidos

Menos de 18 · 18 a 30 · 31 a 40 · 41 a 50 · 51 a 60 · 61 o más.

Quien tiene 17 años y medio está en "Menos de 18", no en "18 a 30". El panel
clasificaba con `int(edad) < 18` y los reportes con `pd.cut(bins=[0,17,...])`, y
en México eso daba 21 contra 22 personas en el mismo rango.

`rango_etario()` · `rangos_etarios()`

### Los flags "no aplica" llegan en dos formatos

`trabajo_na` y `educacion_na` llegan como `True`/`False` en el TOP 1 y como
`1.0`/`0.0` en el TOP 2. Un criterio que reconozca solo uno de los dos deja pasar
registros que debía excluir, sin avisar.

`es_flag_activo()`

### El país se lee de los datos, no del nombre del archivo

La columna existe en los dos formatos: `pais` en la tabla de Supabase y
`pais_TOP1` en el Base Wide. Solo si falta se deduce por las columnas de días que
traen datos, y esa deducción mira el contenido y no la presencia de la columna:
el Base Wide genera columnas para todas las sustancias del sistema, llenas o no.

`detectar_pais()`

---

## 6. Datos

### En sustancias, un vacío es un cero

Los registros de sustancias sin dato se completan con cero. Son unos 1.115
valores, los que no tienen ni las semanas registradas.

**Estado.** Pendiente de ejecución. En la base siguen en nulo. Mientras tanto, el
denominador de sustancias incluye registros cuyo cero es inferido.

**Cada UPDATE lleva su filtro de país.** Sin eso se inventan datos: un nulo de
crack en Perú no es un faltante, es una sustancia que su formulario no pregunta.

| Sustancia | Filtro |
|---|---|
| alcohol, marihuana, cocaina, sedantes, otra_sust | sin filtro, las preguntan los siete |
| pastabase | `AND pais IN ('Perú','Ecuador')` |
| crack | `AND pais = 'El Salvador'` |
| metanfetamina | `AND pais LIKE 'México%'` |
| heroina | `AND pais = 'Ecuador'` |

El `LIKE` es necesario porque conviven México, México CIJ, México Mahanaim y
México Monte Fénix.

### El residuo de trabajo y educación se asume como ausente

Quedan en nulo. No se piden a los centros ni se rellenan. Lo accionable no es el
dato sino la capacitación: los vacíos se concentran en EESS28CI con 85,7 %,
CET042967 con 53,3 %, SCE con 52,4 % y CJR con 36,8 %.

### Los días de trabajo y educación duplicados se anulan

En los 300 registros donde ambos campos tenían el mismo valor, se anularon los
dos. El formulario de JotForm del pilotaje escribía en las dos tablas a la vez, y
un formulario mal configurado a ese punto no ofrece garantía sobre qué capturó.
Un nulo declarado es preferible a un dato dudoso.

---

## 7. Análisis

### No se implementa el índice de cambio fiable

La clasificación del cambio compara días brutos entre las dos mediciones. No se
aplica el índice de Jacobson y Truax que usa el estándar del TOP.

**Por qué.** El índice requiere la confiabilidad de cada ítem, que sale del
estudio de validación, y la desviación estándar de la población propia, que con
el volumen actual sería inestable. Public Health England reunió un año de datos
antes de fijar sus umbrales.

**Consecuencia asumida.** Una diferencia de un día también cuenta como
disminución o aumento, de modo que esas dos categorías quedan sobredimensionadas
respecto de lo que informaría el estándar. Por eso los rótulos no hablan de
mejoría.

---

## 8. Arquitectura

### `validacion_top.py` es la única fuente de criterios

Ningún módulo implementa su propio criterio de rango, normalización o
clasificación. Todo vive ahí y los demás lo importan.

**Por qué.** Antes cada consumidor reimplementaba su versión, y eso produjo el
peor error del sistema, el del sexo. Y volvió a pasar: el clasificador de
sustancias llegó a estar copiado en diez módulos con tres vocabularios distintos,
lo que dejaba al 12 % de los pacientes fuera del gráfico.

### El panel y los reportes deben dar los mismos números

Los reportes leen el Base Wide que arma `procesar_wide()`; el panel lee los
registros crudos de Supabase. Son dos caminos, y hay que verificar que coincidan
después de cualquier cambio:

```
python tools/verificar_coincidencia.py respaldo_top_registros_AAAA-MM-DD.xlsx
```

Compara país por país y centro por centro: pacientes contados, N válido,
distribución de sustancia principal, porcentaje de mujeres y promedio de días.
Al 2026-09-02, los cinco países y los 91 centros coinciden en todo.

El respaldo se baja desde la app, pestaña Respaldos, botón "Generar archivo
Excel". El export del SQL Editor de Supabase trunca en 100 filas.

### No se renombran las claves `pdf_caract` y `pdf_seg` del runner

Apuntan a `word_caract.py` y `word_seg.py`. El nombre quedó de cuando esos
reportes se generaban en PDF. Renombrarlas obliga a cambiar tres archivos a la
vez y eso ya produjo dos bugs.

### El formulario de Perú se llama `index.html`

No se renombra. Los centros peruanos tienen esa URL guardada en correos y
favoritos, y renombrarla los deja sin acceso sin que nadie se entere. La
inconsistencia ya indujo a error más de una vez, incluida la conclusión
equivocada de que Perú no tenía formulario de ingreso.

---

## 9. Seguridad

### Todo respaldo se crea con RLS activo y permisos revocados

Después de cada `CREATE TABLE ... AS SELECT` se ejecuta
`ENABLE ROW LEVEL SECURITY` y `REVOKE ALL ... FROM anon, authenticated`, y se
verifica con `relrowsecurity`.

**Por qué.** `CREATE TABLE AS` deja la tabla en el esquema `public`, que es el
que Supabase expone por PostgREST, y no hereda las políticas de la tabla de
origen. Sin eso, una copia completa de los registros de pacientes queda legible
con la clave publicable que está en texto plano dentro de los formularios.

### Las protecciones se declaran, no se dejan por ausencia

Cada tabla lleva políticas explícitas para las operaciones que debe denegar,
aunque con RLS activo la ausencia de política ya bloquee. Una tabla protegida
solo porque nadie escribió una política se abre el día que alguien agrega una de
más sin darse cuenta.

### Todo UPDATE va precedido de respaldo y de un conteo con la misma condición del WHERE

Y envuelto en una CTE con `RETURNING`, para que devuelva el número de filas
movidas. El SQL Editor responde "Success. No rows returned" a un UPDATE normal, y
esa ambigüedad ya provocó una doble ejecución que revirtió una corrección de
sexo sobre 46 mujeres.

---

## 10. Cómo se mantiene este documento

1. Toda decisión que cierre una discusión entra acá el mismo día, con su
   fundamento. Una decisión sin fundamento escrito se rediscute en tres semanas.
2. Cada regla nueva viene con su prueba en `tests/test_decisiones.py`. Una regla
   sin prueba se incumple sin que nadie se entere, y hay dos precedentes.
3. Si una prueba falla, hay dos posibilidades y ninguna es arreglar la prueba: o
   alguien rompió la regla sin darse cuenta y se corrige el código, o la decisión
   cambió y falta su entrada nueva acá.
4. Este documento es la fuente. La versión viva está en `DECISIONES.md` dentro
   del repositorio, versionada junto al código que la implementa.
