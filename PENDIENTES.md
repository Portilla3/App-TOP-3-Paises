# Pendientes

Hallazgos que aparecieron mientras se trabajaba en otra cosa. Se anotan acá para
no perderlos y para no desviar el trabajo en curso. No están priorizados entre
sí; el orden es de aparición.

---

## Del 2026-10-18 · credenciales y login

**Los cinco centros del Grupo 4 de Perú tienen datos provisionales.**
`correo_institucional` quedó con `pendiente-XXXX@qalat.pe`, inventado porque la
columna es NOT NULL y no se tenían los correos reales. Y `responsable_nombre`
tiene el nombre del centro, no el de una persona, que es lo que hay en el resto
de la tabla. Son EESS34AS, EESS35SG, EESS36IH, EESS37BA y EESS38BV. Hay que
pedirle los datos reales a Perú y corregirlos.

**Falta una consulta de control de centros bloqueados.** Hoy ninguno lo está:
los siete que acumularon fallos entraron después. Pero nadie estaba mirando esa
bitácora, y un centro realmente bloqueado no avisaría, dejaría de intentar. La
consulta es la de INCIDENTES.md: por centro, si su último intento fue exitoso.
Conviene correrla con alguna periodicidad o incorporarla al panel.

**Quince intentos fallaron por texto pegado desde WhatsApp.** Es la causa más
frecuente y la que sigue sin arreglo. La solución propuesta es extraer el primer
grupo alfanumérico de lo que escriban. Requiere su entrada en `DECISIONES.md`
antes de implementarse, porque implica recortar la entrada del usuario.

**Doce filas de prueba en `centro_bitacora`, ids 114 a 125.** Las generó Claude
probando el login el 18 de octubre: diez `login_exitoso` y dos `login_fallido`.
Inflan la métrica de uso por centro, sobre todo la de EESS34AS, que aparece con
cinco ingresos sin haber entrado nunca de verdad. Decidir si se borran o se
marcan. Si se borran, va con respaldo previo como cualquier otro borrado.

**Falta la restricción única sobre el código de centro normalizado.** Hoy no hay
colisiones, pero nada impide insertar `csp` existiendo `CSP`. Con la comparación
insensible a mayúsculas, el `LIMIT 1` de la función elegiría una de las dos en
silencio. Un índice único sobre `upper(trim(centro))` lo cierra.

**Verificar en vivo que los cinco centros nuevos entren.** Solo se probó la
función contra la base, no el flujo completo en el navegador. Y los cinco verán
un panel vacío porque no tienen registros todavía.

**El resto de las funciones de la base sigue sin versionar.** `sql/` tiene solo
`validar_login_centro.sql`. Falta inventariar cuáles hay y bajarlas.

**La regla "Claude no alcanza Supabase" quedó obsoleta.** Con el conector MCP
activo, Claude ejecuta SQL directamente, y así se hicieron los cambios del 18 de
octubre. Las instrucciones del proyecto y `QALAT_ARRANQUE_CHAT.md` todavía dicen
lo contrario. Hay que decidir qué reemplaza a esa regla: qué puede ejecutar
Claude por su cuenta y qué sigue pasando por Rodrigo. Los respaldos previos y el
`RETURNING` en los UPDATE no cambian; lo que cambia es quién aprieta el botón.

## Datos

**Registros duplicados.** 34 grupos, 71 registros, 37 sobrantes. Rodrigo
autorizó eliminar el menos completo de cada grupo. Falta correr el diagnóstico
que separa los duplicados reales de los que el `GROUP BY` juntó por tener
`fecha_entrevista` en nulo. Requiere respaldo, suspender `deny_delete_all` y
restituirla. *2026-09-02*

**Las columnas `_prom` no tienen validación de rango.** Hay valores de 1260,
800, 700, 620 y un −2 en cantidad promedio por día. Las columnas de días sí
están validadas, estas no. *2026-09-02*

**La etapa `seguimiento1` y `seguimiento2`.** 33 registros peruanos usan esos
valores en vez de `seguimiento`, y el panel filtra por igualdad exacta de texto,
así que quedan fuera. *2026-08-28*

**Los 1.115 valores de sustancias sin completar con cero.** Decisión tomada el
2026-09-02, pendiente de ejecución. Mientras no se ejecute, el denominador de
sustancias incluye registros cuyo cero es inferido. *2026-09-02*

**Sustancia principal fuera de la lista del país.** 94 registros: Tusi 28,
Tabaco 29, Metanfetamina en El Salvador 7, Crack en Perú 4, más variantes de
`Otra`. Los cargó Claude al normalizar las 130 correcciones manuales, usando
categorías del clasificador viejo que el instrumento de esos países no ofrece.
El clasificador actual los resuelve bien y el texto original está en
`otra_sust_nombre`, así que no urge tocar la base. *2026-09-02*

---

## Código

**Ocho módulos del panel siguen filtrando la etapa a mano.** `config.py`,
`kpis_centro.py`, `metricas.py`, `semaforo_seguimiento.py` y `tiempo_top.py`
comparan `etapa == 'ingreso'` por su cuenta. No se homologaron con el resto
porque su lógica no es de caracterización: cuentan aplicaciones, miden tiempos
entre TOP y arman el semáforo de seguimiento. Cada uno necesita decidirse por
separado si su unidad es el episodio o el registro. *2026-09-02*

**Resuelto el 2026-09-10, pendiente de ejecución.** `metricas.py` y
`kpis_centro.py` pasan a episodios, para que la tarjeta describa la misma
población que los gráficos de abajo. `semaforo_seguimiento.py`, `tiempo_top.py` y
`config.py::continuidad_por_centro` dejan de identificar el TOP2 por la etiqueta
`etapa` y pasan a llamar a `seguimiento_core`. Los dos indicadores de seguimiento
se conservan y se distinguen por su denominador, según la entrada de
`DECISIONES.md` del 2026-09-10.


**`auto_archivo_wide()` busca rutas de otro entorno.** `/mnt/user-data/uploads`
y `/home/claude`, y se ejecuta al importar el módulo, no al llamarlo. Importar
`caract_excel` falla si no hay base presente. *2026-09-02*

**El denominador de transgresión difiere entre módulos.** `caract_excel.py`
calcula sobre válidos; `word_caract.py` y el panel sobre el total. Además
`_es_s()` trata el vacío como `False`, o sea lo cuenta como no transgresor. Hoy
son dos o tres casos, pero el criterio está desalineado. *2026-09-02*

**El panel y los reportes cuentan pacientes distintos: 127 de diferencia.**
Medido el 2026-09-02 sobre los 1.475 registros. El panel cuenta 1.199 y los
reportes 1.326.

La causa: el panel filtra `etapa == 'ingreso'` comparando texto exacto, mientras
`procesar_wide()` toma el registro más antiguo de cada paciente como su TOP1,
sin mirar cómo el centro etiquetó la etapa. Hay **182 pacientes sin ningún
registro con `etapa=ingreso`**: 111 solo tienen `en_tratamiento`, 43
`seguimiento`, 21 `seguimiento1` o `seguimiento2`. El Wide los cuenta, el panel
no.

Los porcentajes se mueven poco donde hay volumen, menos de dos puntos en Perú,
Ecuador y El Salvador. En México, con 56 pacientes en el panel y 84 en el Wide,
la metanfetamina cambia 4,2 puntos y la cocaína 4,8.

**Decisión pendiente.** Alinear el panel al criterio del Wide, tomando la
primera medición de cada paciente como línea base, o alinear el Wide al del
panel y perder esos 182. El primer TOP de un paciente es su línea base aunque el
centro haya escrito mal la etapa, así que la primera opción conserva datos
válidos; a cambio, el rótulo del gráfico deja de poder decir "al ingreso" y pasa
a "primera medición".

Reproducible con `python tools/comparar_panel_wide.py <respaldo.xlsx>`.
*2026-09-02*


---

## Trabajo autorizado el 2026-09-10

**Homologar el TOP2 en los tres módulos que lo reimplementan.**
`semaforo_seguimiento.py`, `tiempo_top.py` y `config.py::continuidad_por_centro`
pasan a `seguimiento_core`. Lo que distingue a los dos indicadores es el
denominador, no la definición de TOP2.

**Renombrar el indicador operativo.** Pasa a llamarse "% de aplicación del TOP de
seguimiento", sobre todos los ingresos del centro. El nombre "% de seguimiento"
queda reservado para la cobertura sobre los elegibles a 90 días, y en rigor
tampoco se usa ahí: esa se rotula "% de cobertura de seguimiento". Hay que
recorrer panel, Excel de avance y tarjetas de centro; el rótulo viejo aparece en
más de un lugar.

**`metricas.py` y `kpis_centro.py` pasan a episodios.** Hoy la tarjeta "Pacientes
ingresados" cuenta personas únicas y los gráficos de la misma pantalla cuentan
episodios. También hay que corregir el subtítulo "X ingresos + Y seguimientos",
que ignora `en_tratamiento` y `egreso` y por eso no suma el total que muestra la
misma tarjeta.

**`sustancia.py:183` compara contra el literal `'Otras'`.** El clasificador
devuelve `'Otra sustancia'`, así que ese filtro siempre sale vacío y el hover del
gráfico nunca muestra el desglose. El archivo ya importa la constante
`OTRA_SUSTANCIA` y la usa tres líneas más abajo. Se arregla cuando se toque otra
cosa del panel, y de paso se buscan otros literales sueltos.

**Prueba de humo de los reportes.** Ninguna de las 102 pruebas genera un reporte:
verifican criterios de cálculo, no que el Word o el PPT se armen. Es la razón por
la que los cuatro defectos del 9 de septiembre los encontró Ecuador y no la suite.

**Monitoreo externo de las cuatro apps.** Sin él, la caída se entera cuando la
reporta un país. La del 8 de septiembre estuvo seis días arriba.

*2026-09-10*
