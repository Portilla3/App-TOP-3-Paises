# CHANGELOG

Registro de cambios de código del sistema QALAT. Cada entrada va en el mismo
commit que el cambio que describe. Las decisiones y su fundamento viven en
`DECISIONES.md`; acá va solo qué cambió en el código.

---

## 2026-10-27

- Despliegue: la app TOP se volvió a crear en Streamlit Cloud desde
  `Portilla3/App-TOP-3-Paises` (antes estaba registrada como `qalat-top-ecuador`,
  el nombre viejo del repositorio, y por eso los pushes no se desplegaban solos).
  Secretos copiados por Rodrigo desde la app anterior. Este commit sirve también
  de prueba de que el despliegue automático funciona.

- Datos, con autorización de Rodrigo: los 7 TOP de SLIMB000615 (Hospital
  Psiquiátrico de Sinaloa, IMSS-Bienestar) pasan de "en_tratamiento" a "ingreso",
  según la respuesta del centro a la consulta de Cinthia ("¿Era ingreso?": Sí en
  los 7). Ids 1361, 1362, 1646, 1647, 1648, 2258 y 2259; cada paciente tenía un
  solo TOP. Respaldo en `backup_sinaloa_etapa_20261027` (RLS, sin permisos),
  conteo 7 = actualizadas 7.

- Login de centro: tolera el texto pegado. Si lo escrito no es un código, busca
  entre sus palabras el de un centro con clave activa ("SJA🇸🇻 El Sa" → SJA), y si
  la clave falla tal cual la prueba sin los espacios del borde. Migración
  `login_centro_texto_pegado`; ver DECISIONES.md, "El login tolera el texto
  pegado". Ninguna clave ni código de centro cambió.
- Claves nuevas del módulo: solo mayúsculas y números, sin 0/O ni 1/I (migración
  `claves_generadas_mayusculas`). Las claves ya entregadas no cambian.
- Verificado en producción: los dos cuerpos de función son idénticos al
  repositorio y los permisos se mantienen. Simulación con la fila de ensayo
  CENTRO_PRUEBA (país 'Test'): respaldo en `backup_centro_prueba_20261027` (RLS,
  sin permisos), clave temporal, cinco casos (texto pegado, minúscula con espacio,
  salto de línea: entran; clave en minúscula o incompleta: fallan) y restauración
  exacta, con la misma huella md5 que el respaldo. Las filas 134 a 138 de
  `centro_bitacora` son de esa prueba.

- Formularios (los siete): el promedio de consumo por día no acepta negativos
  (`min="0"` y bloqueo al enviar, con el campo marcado en rojo). Sin máximo. Probado
  en un navegador simulado (jsdom) con Perú, México y Ecuador. Prueba nueva en
  `tests/test_formularios.py`.

- Claves de centros: el selector para crear o restablecer muestra solo los códigos
  de la lista de centros del formulario TOP del país; se quitó "(otro código)" y el
  campo de texto libre. Revisado contra la base: todos los centros con TOP y todas
  las claves existentes están en su formulario.

- Claves de centros: Monte Fénix y Mahanaim no ven la pestaña ni aparecen en el
  selector de UNODC (`SIN_GESTION_DE_CLAVES` en `app.py`). Cada una es un solo
  centro y su perfil de institución ya es el del centro. Verificado con la app
  completa para Perú, México, Monte Fénix, Mahanaim y UNODC.

- Claves de centros: nueva pestaña "🔑 Claves de centros" en el perfil de país
  (`pipeline/panel/gestion_claves.py`). Con la clave de administrador del país,
  el gobierno ve sus centros, si tienen clave y cuándo entraron por última vez,
  y crea, restablece o desactiva claves. UNODC elige el país. Al cerrar sesión se
  borra la clave de administrador. En Supabase, `sql/admin_claves_centros.sql`:
  tabla `pais_admin` (RLS, sin permisos, política restrictiva), tres funciones
  públicas y dos internas, e índice único sobre el código de centro normalizado.
  Probado en un Postgres local con crypt simulado: flujo completo, bloqueo a los
  5 intentos, desbloqueo a los 15 minutos y permisos de anon. 18 pruebas nuevas
  en `tests/test_gestion_claves.py`.
  Aplicado en Supabase con autorización de Rodrigo (migración
  `admin_claves_centros`). Verificado en producción: los cinco cuerpos de función
  son idénticos al archivo, anon no lee `pais_admin` ni llama las internas, y el
  camino completo con bcrypt real responde. La clave de administrador temporal
  del país 'Test' usada para esa prueba se borró. `pais_admin` queda vacía.

- Prueba de humo de los reportes: `tests/test_reportes.py`, con la base
  sintética de `tests/datos_sinteticos.py`. Arma la wide y los seis reportes en
  Perú, Ecuador, El Salvador y México, el camino del centro, el filtro de periodo
  y los tres casos del incidente del 2026-09-09 (sustancia sin consumidores,
  centro sin ingreso, base sin seguimiento). 43 pruebas, un minuto y medio. Se
  comprobó que fallan si se reintroduce un error en el PowerPoint de ingreso o el
  `max()` sobre `None` del defecto 1.

- Panel: las tarjetas cuentan con el mismo criterio que los gráficos, y el segundo
  TOP se identifica en un solo lugar. Es el trabajo autorizado el 2026-09-10.
  - `seguimiento_core.top2_por_paciente()`: una fila por paciente con su TOP1 y su
    TOP2. `calcular_seguimiento()` la usa por dentro; da los mismos números que
    antes en los siete países con umbral 90, 60 y 0 (comparado con datos reales).
  - Semáforo de seguimiento, tiempo entre TOP1 y TOP2 y
    `config.continuidad_por_centro()` dejan de buscar el TOP2 por la etiqueta
    `etapa` y llaman al core. El semáforo incluye ahora a los pacientes cuyo primer
    TOP no es de ingreso y lo dice en su nota; sus urgentes son exactamente los
    elegibles sin TOP2 de la tarjeta "Con seguimiento (TOP2)".
  - `continuidad_por_centro()` devuelve `n_pacientes`, `n_con_top2` y
    `pct_aplicacion`: es el % de aplicación del TOP de seguimiento, sobre todos los
    pacientes del centro.
  - Tarjeta "Pacientes ingresados" del panel de país y del centro, e ingresos del
    mes: salen de `lineas_base()` (episodios), como el perfil al ingreso. La tabla
    "Tu centro frente al promedio nacional" usa la misma población.
  - Tarjeta "Total de registros": el desglose muestra las cuatro etapas y "otra
    etiqueta", y suma el total. Antes decía "X ingresos + Y seguimientos".
  - Rótulos: "Con seguimiento (TOP2)" en la tarjeta, el gráfico por centro, el Excel
    y el PPT de seguimiento; "Aplicación del TOP de seguimiento" en la tarjeta del
    centro y en el Excel de avance (antes "% Continuidad").
  - Gráfico de sustancia principal: el desglose de "Otra sustancia" al pasar el
    mouse comparaba contra el literal 'Otras' y salía siempre vacío. Quien escribió
    solo "otra" va aparte del detalle de drogas.
  - 10 pruebas nuevas en `tests/test_decisiones.py`.

- Datos, con autorización de Rodrigo y respaldo en `backup_limpieza_20261027` (48
  filas, RLS activo, sin permisos): borradas las 39 copias viejas de TOP duplicados
  ya reemplazadas por la última carga (el borrado exige que exista una copia más
  nueva del mismo TOP); borradas las copias viejas de 2 TOP vueltos a cargar con
  la etapa corregida (CJR ROGA05111971, EESS02SB GIPO13121982); 7 TOP de Perú con
  etapa "seguimiento1" o "seguimiento2" y un ingreso anterior pasan a
  "seguimiento". Quedan 9 grupos duplicados dudosos (19 registros) y 25 TOP de
  Perú con "seguimiento1/2" sin ingreso previo, a confirmar con los centros.

- Formularios de Perú (`index.html`), Ecuador y El Salvador: no dejan guardar si
  el código no coincide con la fecha de nacimiento, igual que los cuatro de México.
  Como la fecha de nacimiento viene de un selector de fecha, también impide códigos
  con fechas que no existen (como DDDD12345678). Nueva prueba
  `tests/test_formularios.py`: los siete formularios deben bloquear igual y tener el
  mismo formato de código y las mismas reglas de fecha.

- Datos: borrado el registro de prueba DDDD12345678 (id 955, SRIMB000931, entrevistador
  "PACO LACO", cargado el 22 de junio), con autorización de Rodrigo. Respaldo en
  `backup_registro_prueba_dddd_20261027` (RLS activo, sin permisos para anon ni
  authenticated). Pasó porque el formulario solo exige 4 letras y 8 números, y el
  cruce con la fecha de nacimiento de México todavía no bloqueaba en junio.

## 2026-10-26

- Datos: corregidos días de trabajo, días de educación y robo de los 402 TOP
  migrados desde JotForm, y los textos "nan" pasados a NULL. Bloques con valores
  imposibles quedan en blanco. Detalle en INCIDENTES.md; SQL en
  `sql/correcciones/2026-10-26_migracion_trabajo_educacion_robo.sql`.

- Datos: corregida la salud psicológica de los 402 TOP migrados desde JotForm,
  que tenían los días de violencia intrafamiliar de la última semana. Respaldo,
  conteo y huella antes y después; detalle en INCIDENTES.md. SQL en
  `sql/correcciones/2026-10-26_salud_psicologica_migracion.sql`.

- `tools/errores_graves.sql`: consulta de errores graves de registro por grupo y
  por mes de carga, con el criterio de DECISIONES.md. Solo lee. Excluye las dos
  migraciones de JotForm y cuenta la última carga de cada TOP.

## 2026-10-25

### Con los TOP cargados dos veces se usa la última versión, no la primera
`quedarse_con_ultima_version()` en `pipeline/validacion_top.py`, usada por
`procesar_wide()` al deduplicar y por `lineas_base()` al elegir el TOP de
ingreso de cada episodio. Conserva la copia de `created_at` mayor, con `id` como
desempate. Sin ninguna de las dos columnas, conserva la primera, como antes.

Había 45 grupos de registros con el mismo centro, paciente, etapa y fecha. En 41
las copias eran distintas: centros que volvieron a cargar un TOP para corregirlo
y TOP que habían entrado por la migración del piloto y se cargaron de nuevo. Se
conservaba la primera copia, así que la corrección no llegaba a los informes.
Cambian 41 TOP, 37 de ingreso.

Siete pruebas nuevas, 113 en total.

### Queda escrita la regla de las semanas en blanco en sustancias
El atajo del cero ya funcionaba en los formularios pero no estaba en ningún
documento. Entra en `DECISIONES.md` y en `QALAT_REGLAS_DE_CALCULO.md`, junto con
el descarte de exigir las cuatro semanas cuando hay consumo. Sin cambios de
código.

## 2026-10-19

### Cinco centros nuevos de Perú en el formulario TOP
`index.html`, que es el formulario de Perú, suma EESS34AS, EESS35SG, EESS36IH,
EESS37BA y EESS38BV a la lista de centros, que pasa de 33 a 38. Son centros que
Rodrigo capacitó en octubre para cargar TOP.

El 18 de octubre, desde el chat de correos, a esos cinco se les crearon claves
de acceso a la plataforma en lugar de agregarlos al formulario. Eso los dejaba
sin poder cargar ningún TOP y con un acceso que todavía no necesitan, porque
no tienen datos que ver.

## 2026-10-18

### `validar_login_centro()` deja de distinguir mayúsculas en el código de centro
Migración `login_centro_insensible_a_mayusculas`, aplicada en producción desde el
chat de correos. La entrada y la columna se comparan con `upper(trim(...))`. La
clave no se toca: bcrypt sigue comparando exacto.

Verificado contra la base el 2026-10-19: la definición vigente coincide con lo
declarado, y no hay dos credenciales que colisionen al normalizar.

**Impacto real, medido sobre los 31 intentos fallidos que hubo antes del
cambio:** resuelve 4. Los otros 27 se reparten en 12 que escribieron el código
bien y fallaron por la clave, y 15 que pegaron texto desde WhatsApp. El arreglo
es correcto y no hace daño, pero no es la causa principal de que los centros no
entren.

### Las funciones de la base pasan a estar versionadas
`sql/validar_login_centro.sql`. Hasta ahora la única copia de las funciones era
la de producción: un cambio hecho desde cualquier sesión se perdía sin rastro y
sin forma de compararlo. Esta es la primera; faltan las demás.

### Cuatro pruebas del login de centro
`tests/test_login_centro.py`. No ejecutan la función, que vive en Supabase:
verifican que el archivo versionado conserve las decisiones, que la clave no se
normalice, que no se pierdan `SECURITY DEFINER` ni el `search_path` fijo, y que
la bitácora siga guardando lo que la persona escribió. Esa última columna es la
que permitió medir por qué fallan los logins.

Ciento seis pruebas en total.

## 2026-09-10

### Se eliminó la pestaña de migración JotForm y el botón de borrado por país
`app.py` pierde la pestaña completa "📥 Migración JotForm (obsoleta)" y las cinco
funciones que solo ella usaba: `_migrar_excel_jotform`, `_insertar_lote_supabase`,
`_eliminar_por_pais`, y las dos que ya no llamaba nadie desde `e176885`,
`_actualizar_registro` y `_eliminar_registro`. Con eso desaparece el botón que
borraba todos los registros de un país entero con solo escribir BORRAR en una
caja de texto, y también el `st.json(registros_migra[0])` que volcaba en pantalla
un registro de paciente completo, más los cinco `except:` desnudos que quedaban
en el archivo.

La app pasa de cinco pestañas a cuatro para UNODC. Las de países no cambian.

Verificado antes de tocar: búsqueda en todo el repositorio confirmando que las
cinco funciones no se llamaban desde ningún otro lugar. `py_compile` limpio,
`pyflakes` sin avisos nuevos, 102 pruebas pasando. El fundamento está en
`DECISIONES.md`, "La app no borra registros de producción".

---

## 2026-09-02

### Un centro sin ningún TOP de ingreso reventaba el pipeline
`procesar_wide(filtro_centro=...)` fallaba con `KeyError: '_episodio'` cuando el
centro filtrado no tenía ningún TOP de ingreso: `pd.DataFrame([])` sale sin
columnas. Son tres centros al 2026-09-02, dos de México y uno de Ecuador. Ahora
devuelve un Wide vacío con la estructura correcta y lo deja anotado en el log.

Salió al extender la verificación al nivel centro, que es un camino distinto:
el Wide filtra con `filtro_centro` antes de armar los episodios y el panel filtra
el DataFrame después.

### La verificación de coincidencia cubre los 91 centros
`tools/verificar_coincidencia.py` compara ahora por país y por centro. Los 91
centros dan idéntico en pacientes contados y distribución de sustancia
principal. Ciento dos pruebas.

### Cuatro módulos dejaban fuera del informe a quien declaró otro sexo
`caract_excel.py`, `word_caract.py`, `word_seg.py` y `pptx_caract.py` calculaban
el N válido de sexo con `isin(['H','M'])`, así que las personas con `O` no
entraban ni al denominador ni al gráfico. El panel sí las contaba, de modo que
Perú y Ecuador daban un N distinto en cada salida. Son dos personas, una en cada
país. El N válido pasa a ser `notna()` y los cuatro módulos dibujan las tres
categorías del instrumento, aunque alguna venga en cero.

El pie del informe pasa a decir los dos números: cuántas personas ingresaron y
sobre cuántas se calcularon los porcentajes.

Doce pruebas nuevas, ciento dos en total.

### Los rangos de edad se calculaban con dos criterios distintos
El panel clasificaba con `int(edad) < 18` y los cuatro módulos de reporte con
`pd.cut(bins=[0,17,30,...])`. Como la edad es un número con decimales, alguien
de 17 años y medio caía en "Menos de 18" en el panel y en "18 a 30" en los
informes. En México eso daba 21 contra 22 personas en el mismo rango.

`rango_etario()` y `rangos_etarios()` en `validacion_top.py` cuentan los años
cumplidos, que es el criterio del panel. Los cinco módulos los usan.

### El panel mostraba dos nombres para la misma sustancia
El gráfico de prevalencia dibujaba la categoría interna y el de días la etiqueta
del país, así que en México uno decía "Cocaína" y el otro "Cocaína/crack" para
los mismos pacientes. Ambos usan la etiqueta.

### Pie de texto desactualizado en el Word de caracterización
Decía "solo se listan las sustancias con al menos un consumidor registrado",
que dejó de ser cierto cuando los gráficos pasaron a mostrar todas.

### El panel y los reportes dan los mismos números
`tools/verificar_coincidencia.py` corre los dos caminos sobre el mismo archivo y
compara indicador por indicador: pacientes, N válido, distribución de sustancia
principal, porcentaje de mujeres y promedio de días de cada sustancia. Sobre los
1.475 registros, los cuatro países coinciden en todo.

Para llegar ahí faltaban tres cosas.

**Los gráficos de `pptx_caract.py` y `word_caract.py` se saltaban las categorías
sin casos.** Ahora recorren `categorias_pais()` y dibujan todas, con "sin dato"
sobre las vacías. Alcanza a los tres gráficos de sustancias de cada módulo.

**El promedio de días de la sustancia principal excluía los ceros.** Filtraba
`v > 0`, así que dejaba fuera a quienes ingresaron en abstinencia de su propia
droga problema, justo lo que `DECISIONES.md` manda incluir desde el 1 de
septiembre. El de días por sustancia sí debe filtrarlos y se mantiene.

**La deduplicación del Wide se llevaba por delante un TOP de ingreso.**
`drop_duplicates` usaba código y fecha; un paciente con sus tres registros sin
fecha perdía el de ingreso y su episodio desaparecía de los reportes, pero no
del panel. La clave ahora incluye centro y etapa.

`columna_de_sustancia()` en `validacion_top.py` resuelve el nombre de la columna
de días en los dos formatos, el corto de Supabase y el largo del Base Wide, para
que ambos caminos busquen igual.

Cuatro pruebas nuevas, noventa en total.

### Aviso de etapa en los siete formularios de captura
Cuando la etapa elegida es `en tratamiento` o `seguimiento`, antes de enviar
aparece una confirmación que recuerda que un paciente recién ingresado lleva
etapa `ingreso` aunque venga derivado. Uno de los dos botones corrige la etapa y
envía; el otro envía tal cual.

Es JavaScript local: no consulta la base, no agrega espera ni un punto de falla.
De los 182 pacientes sin TOP de ingreso al 2026-09-02, 111 marcaron
`en tratamiento` y 43 `seguimiento`.

### La unidad de análisis pasa a ser el episodio de tratamiento
`construir_episodios()` y `lineas_base()` en `pipeline/validacion_top.py`. Un TOP
con etapa de ingreso abre un episodio, identificado por
`código|centro|fecha del ingreso`; los TOP siguientes del mismo paciente en el
mismo centro le pertenecen hasta que aparezca otro ingreso. Lo anterior a
cualquier ingreso queda fuera.

Antes había dos criterios conviviendo. `procesar_wide()` tomaba el registro más
antiguo de cada código como TOP 1, sin mirar la etapa ni el centro, y contaba
1.326 pacientes. El panel comparaba `etapa == 'ingreso'` como texto y contaba
1.199 registros. Con episodios ambos cuentan 1.162.

`procesar_wide()` arma los TOP 1 y TOP 2 por episodio, y `edad.py`,
`piramide.py`, `salud.py`, `transgresion.py`, `dias_consumo.py` y
`sustancia.py` reemplazan su filtro por `lineas_base()`.

Los porcentajes se mueven poco, menos de un punto en la distribución de sexo de
los cuatro países. Lo que cambia es el N, y que los dos caminos por fin cuentan
lo mismo.

Quince pruebas nuevas, ochenta y seis en total.

### `tools/comparar_panel_wide.py` mide la brecha entre los dos caminos
Los reportes leen el Base Wide y el panel lee los registros crudos. El script
corre los dos criterios sobre el mismo archivo y compara pacientes contados,
sustancia principal y sexo.

Primera corrida sobre los 1.475 registros: el panel cuenta 1.199 pacientes y los
reportes 1.326. La diferencia son 182 pacientes que no tienen ningún registro
con `etapa=ingreso` y que el panel descarta al comparar ese texto exacto.

### Los seis módulos de reporte usan la taxonomía madre
`caract_excel.py`, `seg_excel.py`, `word_caract.py`, `word_seg.py`,
`pptx_caract.py` y `pptx_seg.py` tenían cada uno su copia de `norm_sust()`, con
vocabularios que no coincidían entre sí ni con `wide_top.py`. Ahora la función
conserva el nombre pero delega en `clasificar_sustancia()`, y recibe el país
detectado de los datos.

Las tres listas de categorías escritas a mano en `caract_excel.py`,
`seg_excel.py` y `word_seg.py` se reemplazan por `categorias_pais()`, y las
tablas dejan de saltarse las categorías en cero: se muestran todas las del país,
que es lo que hace comparables los informes entre centros y en el tiempo.

Con esto se salda la deuda que dejaba
`test_el_clasificador_de_sustancias_no_esta_duplicado` en `xfail(strict=True)`.
El marcador se quita, tal como estaba previsto. Setenta y una pruebas.

### El panel aplica la taxonomía por país y muestra todas las categorías
`pipeline/panel/dias_consumo.py` y `pipeline/panel/sustancia.py` usan
`clasificar_sustancia()` con el país detectado de los datos, en lugar del mapeo
`_CAT_A_COL`, cuyas claves nunca coincidían con lo que el clasificador devolvía.

Tres cambios de comportamiento, los tres decididos hoy:

**Se muestran todas las categorías del país**, seis o siete según el formulario,
aunque alguna venga en cero. El gráfico de prevalencia tenía un corte de las
cinco más frecuentes, y por eso mostraba Tusi en Perú mientras el de días
mostraba Sedantes: dos gráficos de la misma pantalla con sustancias distintas.
Ahora los dos recorren la misma lista.

**El n va bajo cada barra** en el gráfico de días. Al mostrar todas las
categorías, una barra de siete pacientes se dibuja igual de alta que una de
trescientos, y sin el n se leen con el mismo peso.

**El denominador de prevalencia son los que declararon una sustancia.** Antes
era el total de pacientes al ingreso, así que quien dejó la pregunta en blanco
diluía los porcentajes de los demás y la suma no daba cien.

Las etiquetas siguen la convención de cada país: Ecuador ve "Pasta Base/basuco"
y México verá "Cocaína/crack", sin que cambie la categoría con que se calcula.

### El clasificador reconoce las respuestas vacías de una letra
`clasificar_sustancia()` mandaba a `Otra sustancia` valores como `N`, `-`, `nan`
o `s/d`, que no nombran ninguna sustancia y deben quedar fuera del denominador.
Se comparan exactos y no como subcadena, porque `n` y `no` aparecen dentro de
casi cualquier nombre de sustancia. Se suma `minguna`, la errata habitual de
`ninguna` en los registros del pilotaje.

Probado contra los 94 registros que hoy tienen en la base una sustancia
principal fuera de la lista de su país: Tusi 28, Tabaco 29, Metanfetamina en El
Salvador 7, Crack en Perú 4, y las variantes `Otra` y `Otras`. Todos caen donde
corresponde. Setenta pruebas en total.

### `detectar_pais()` lee el país de los datos, no del nombre del archivo
`word_caract.py` y los otros tres módulos que conocían el país lo sacaban de
`_extraer_pais(os.path.basename(wide_file))`, y el runner tenía que neutralizar
esa llamada al cargar el módulo. `caract_excel.py` y `seg_excel.py` no lo
intentaban siquiera.

La columna existe en los dos formatos: `pais` en la tabla de Supabase y
`pais_TOP1` en el Base Wide. `detectar_pais()` la busca ahí primero, y solo si
no aparece deduce el país por las columnas de días que traen datos. Esa segunda
vía tiene que mirar el contenido y no la presencia de la columna, porque el Wide
genera columnas para todas las sustancias del sistema estén llenas o no: el Base
Wide de El Salvador trae las doce columnas de heroína y las doce de pasta base,
todas vacías.

### `clasificar_sustancia()` reemplaza diez clasificadores copiados
`pipeline/validacion_top.py` incorpora la taxonomía madre: `CATEGORIAS_POR_PAIS`
con la lista cerrada de cada formulario, `SUSTANCIA_A_COLUMNA` con su columna de
días, y `clasificar_sustancia(texto, pais)` que aplica la regla de que lo
declarado fuera de la lista del país cae en `Otra sustancia`.

Antes el clasificador estaba copiado en diez módulos, con tres vocabularios
distintos: `wide_top.py` devolvía `Marihuana`, `caract_excel.py` esperaba
`Cannabis/Marihuana` y el panel usaba `Inhalables` donde otro usaba
`Inhalantes`. El mapeo `_CAT_A_COL` del panel fue escrito contra un vocabulario
y recibía datos clasificados con otro, así que cuatro de sus siete claves nunca
coincidían con nada.

Medido sobre las 548 declaraciones de Perú: llegaban al gráfico 482, el 88 %.
Ahora llegan las 548. Los 53 pacientes de marihuana entran en su categoría; los
9 de crack y 4 de tabaco entran en `Otra sustancia`, porque el formulario
peruano no mide sus días.

`_norm_str()` también se muda a `validacion_top.py`, por ser criterio de
normalización de texto.

### Borrados `pdf_caract.py` y `pdf_seg.py`
1.794 líneas que ningún flujo alcanzaba. El runner mapea la clave `pdf_caract` a
`word_caract.py` y `pdf_seg` a `word_seg.py`. Contenían dos de las diez copias
del clasificador, y una de ellas ya había recibido un arreglo sin efecto.

### Documentado que `index.html` es el formulario de Perú
El archivo no sigue la convención `index_<pais>.html` de los otros seis y eso ya
indujo a error más de una vez, incluida una conclusión equivocada de que Perú no
tenía formulario de ingreso. No se renombra, por las URLs que los centros
peruanos tienen guardadas por fuera. Queda documentado en tres lugares: un aviso
en la cabecera del propio archivo, la tabla de archivo a país que ahora abre el
README, y la entrada correspondiente en `DECISIONES.md`.

Sin cambios de código.

### Retirados dos rellenos con cero que no rellenaban nada
`pptx_caract.py` aplicaba `.fillna(0)` antes de contar consumidores y
`word_seg.py` construía una serie de ceros cuando faltaba la columna del TOP 2.
Ninguno de los dos alteraba un resultado: `NaN > 0` ya es `False`, y la serie de
ceros quedaba anulada por el `if c2 else 0` de la línea siguiente. Se retiran
porque hacen pensar que existe un error donde no lo hay, y porque el próximo que
lea ese código va a intentar arreglarlo.

Verificado sobre los 571 pacientes: los seis conteos de consumidores son
idénticos antes y después.

`pptx_caract.py` pasa además el N válido de cada sustancia junto al porcentaje,
para poder mostrarlo en el gráfico cuando se decida el denominador.

### `es_flag_activo()` centraliza la lectura de las casillas "no aplica"
`pipeline/validacion_top.py` incorpora `es_flag_activo()`, y `caract_excel.py` y
`seg_excel.py` lo importan en lugar de aplicar cada uno su propio
`isin(['true','1','t'])`.

El criterio anterior reconocía el flag solo en el formato del TOP de ingreso.
Las casillas `trabajo_na` y `educacion_na` llegan al Base Wide como `True`/`False`
en el TOP 1 y como `1.0`/`0.0` en el TOP 2, de modo que en el reporte de
seguimiento el filtro no capturaba nada: cuatro registros marcados como "no
aplica" quedaban fuera de la exclusión.

Ningún promedio cambia con este commit. Los cuatro registros tienen el total en
nulo, así que ya quedaban fuera del cálculo por su cuenta. Lo que cambia es que
la nota al pie de la tabla de días de trabajo y estudio pasa a ser cierta en los
dos reportes, y que la exclusión sigue funcionando si esos nulos alguna vez se
completan.

Verificado contra la base de 1.402 registros: 14 y 74 marcas en el TOP 1, 1 y 3
en el TOP 2, promedios idénticos antes y después.

### Eliminado el formulario de corrección embebido en `app.py`
`_CORRECCION_HTML_TEMPLATE` eran 1.158 líneas que ningún flujo alcanzaba. Los
arreglos aplicados sobre ese template durante la jornada del 1 de septiembre no
tenían efecto en producción; los formularios reales viven en archivos aparte.

### Homologación del campo sexo a H/M/O
`normalizar_sexo()` y `normalizar_sexo_valor()` en `pipeline/validacion_top.py`,
usadas por los ocho módulos que antes implementaban su propio criterio. Seis
leían `H` como hombre y dos leían `M` como masculino.

### Paginación de las lecturas de Supabase
`_cargar_supabase()` y `_leer_todos_registros_full()` truncaban en mil registros
por el límite por defecto de PostgREST. El respaldo pasó de 1.000 a 1.402.

### Preservación del cero en los quince formularios
`parseInt(el.textContent) || null` devolvía `null` cuando el valor era `0`,
porque `0` es *falsy* en JavaScript. Reemplazado por una comprobación explícita
con `isNaN`. El error estuvo activo cinco meses.
