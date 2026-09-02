# CHANGELOG

Registro de cambios de código del sistema QALAT. Cada entrada va en el mismo
commit que el cambio que describe. Las decisiones y su fundamento viven en
`DECISIONES.md`; acá va solo qué cambió en el código.

---

## 2026-09-02

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
