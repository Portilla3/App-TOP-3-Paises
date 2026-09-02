# CHANGELOG

Registro de cambios de código del sistema QALAT. Cada entrada va en el mismo
commit que el cambio que describe. Las decisiones y su fundamento viven en
`DECISIONES.md`; acá va solo qué cambió en el código.

---

## 2026-09-02

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
