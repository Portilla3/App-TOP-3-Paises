# Pendientes

Hallazgos que aparecieron mientras se trabajaba en otra cosa. Se anotan acá para
no perderlos y para no desviar el trabajo en curso. No están priorizados entre
sí; el orden es de aparición.

---

## Del 2026-10-18 · credenciales y login

**Resuelto el 2026-10-19 · las cinco claves de plataforma del Grupo 4 de Perú.**
Desactivadas con autorización de Rodrigo (`activo = false`), no borradas. Esos
centros solo necesitan el formulario TOP, donde ya están. El estado previo quedó
en `backup_credenciales_grupo4_20261019`, que guarda solo código y estado, sin
las claves cifradas. Para reactivar una:
`UPDATE centro_credenciales SET activo = TRUE WHERE centro = 'EESS34AS';`

**22 centros de Perú cargan TOP y no tienen acceso a la plataforma.** Solo
EESS02SB y EESS09H lo tienen. Se le pidió a Miguel el correo institucional y el
responsable de cada uno para crear sus claves. En Ecuador pasa lo mismo con 39
centros y en México con 37.

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

**Resuelto el 2026-10-19 · filas de prueba en `centro_bitacora`.** Las doce (ids 114 a 125) se borraron con autorización de Rodrigo. Respaldo en `backup_bitacora_pruebas_20261019`, con RLS activo y permisos revocados.

**Falta la restricción única sobre el código de centro normalizado.** Hoy no hay
colisiones, pero nada impide insertar `csp` existiendo `CSP`. Con la comparación
insensible a mayúsculas, el `LIMIT 1` de la función elegiría una de las dos en
silencio. Un índice único sobre `upper(trim(centro))` lo cierra.

**Verificar en vivo que los cinco centros nuevos entren.** Solo se probó la
función contra la base, no el flujo completo en el navegador. Y los cinco verán
un panel vacío porque no tienen registros todavía.

**El resto de las funciones de la base sigue sin versionar.** `sql/` tiene solo
`validar_login_centro.sql`. Falta inventariar cuáles hay y bajarlas.

**Resuelto el 2026-10-19 · la regla "Claude no alcanza Supabase".** Reemplazada en `DECISIONES.md`: Claude lee por su cuenta y pide permiso para cualquier modificación.

**Próximo desarrollo: abrir la Plataforma a todos los centros.** Plan de
Rodrigo, en este orden: (1) al menos dos centros por país con acceso completo;
(2) encuesta de Rodrigo a esos centros sobre el uso; (3) módulo de gestión para
que cada gobierno asigne y administre las claves de sus centros, con
capacitación; (4) acceso para todos los centros. El objetivo es que cada centro
vea la lista de sus pacientes con TOP aplicado. Rodrigo lo considera urgente:
sin acceso, los centros vuelven a cargar TOP que ya estaban y se mantienen
errores. *2026-10-26*

## Datos

**Resuelto el 2026-10-27 · bloqueo del código distinto de la fecha de nacimiento
en Perú, Ecuador y El Salvador.** Ver `DECISIONES.md`. Falta avisar a esos tres
países que el formulario ya no deja guardar si no coinciden.

**La fecha dentro del código no se validaba como fecha.** Desde el 27 de octubre
lo impide el bloqueo del cruce con la fecha de nacimiento en los siete
formularios. Quedan los registros antiguos. Al 27 de octubre hay 12 registros
reales con un código cuya fecha no existe (mes 13, 19 o 90; día 00; año 1013 o
2200), por ejemplo EDOC12191996 o MACR08131982. Agregar esa validación junto con
el bloqueo del cruce código-fecha de nacimiento. *2026-10-27*

**IMSS-Bienestar, primer TOP "en tratamiento".** El 26 de octubre Cinthia pidió
confirmar la etapa a 6 centros (39 pacientes: Neuman SLP 16, Sinaloa 7, Orizaba
6, Veracruzano 6, Sonora 2, Ixtlahuacan 2). Las respuestas no han llegado. Faltan
los centros ambulatorios, que se enviarán después. Neuman sigue registrando
primeros TOP "en tratamiento" en octubre. *2026-10-27*

**Solicitud de confirmación a los países.** El 27 de octubre quedaron listos un
Word por país (Perú 98 casos en 19 centros, Ecuador 64 en 24, El Salvador 120 en
7, México 74 en 15) y un Excel por centro con sus casos, la pregunta y la regla
si no responde en 15 días desde que lo recibe. Falta enviarlos y, con las
respuestas, aplicar las correcciones con respaldo previo. *2026-10-27*

**Prueba del criterio de error grave.** Vive en `tools/errores_graves.sql`. Si
algún día pasa al panel, se mueve a `validacion_top.py` con su prueba.
*2026-10-26*

**Los 78 TOP con código distinto de la fecha de nacimiento y los 16 seguimientos
con otro código.** Hay que corregirlos hacia atrás, preguntando al centro cuál
dato es el correcto. Nada se corrige sin permiso. *2026-10-26*

**Registros duplicados.** El 27 de octubre se borraron las 39 copias viejas ya
reemplazadas por la última carga (respaldo en `backup_limpieza_20261027`). Quedan
9 grupos dudosos, 19 registros, a confirmar con los centros; mientras tanto vale
la última carga. Son: SAI000850 BRSU09082000, NWH JOCO20011985, EESS03CA
MAGO06022008, CET045943 NESA25051997, CMM SAGO12051974, EESS29EL GISA06012013,
SAI001735 CROR11061997, CET045943 NICH30091972 y SJA GUCH29081991 (en este, la
última carga trae nacimiento 1999 y los demás registros dicen 1991). Aparte:
SAI001735 ANBR20062002 tiene un segundo ingreso con fecha 20/04 que no es
duplicado por fecha. *2026-10-27*

**De dónde vienen los duplicados, y la vía para corregir.** Clasificadas el
26 de octubre, las 49 copias de más son: 28 TOP del piloto vueltos a cargar en
la Plataforma (CMM 12, todas el 10 de julio), 10 TOP de la Plataforma vueltos a
cargar con cambios, 8 vueltos a cargar iguales y 3 que ya venían duplicados de
JotForm. 21 cambian algún dato: lo más probable es que el centro estuviera
corrigiendo, porque los formularios de corrección están en pausa. Siguen
apareciendo (12 en septiembre y octubre). Falta decidir qué vía tiene el centro
para corregir: avisar a Rodrigo, que corrige en Supabase, o reactivar los
formularios de corrección. *2026-10-26*

**Correcciones que no aparecen como duplicado.** Resuelto el 27 de octubre: se
borró la copia vieja de CJR ROGA05111971 y de EESS02SB GIPO13121982. Además hay 10 pacientes con dos ingresos en el mismo centro a menos de 60 días;
algunos pueden ser la misma carga con la fecha cambiada. Confirmar con los
centros. *2026-10-26*

**Resuelto el 2026-10-26 · campos mal migrados desde JotForm.** Salud
psicológica, días de trabajo y educación, robo y textos "nan". Ver
`INCIDENTES.md`. En la misma migración hay 9 registros (7 de El Salvador, 2 de Perú) con fecha de entrevista
posterior al día en que se cargaron, imposible; lo más probable es día y mes
invertidos. *2026-10-25*

**Las columnas `_prom` no tienen validación de rango.** Hay valores de 1260,
800, 700, 620 y un −2 en cantidad promedio por día. Las columnas de días sí
están validadas, estas no. *2026-09-02*

**La etapa `seguimiento1` y `seguimiento2`.** 33 registros peruanos usan esos
valores en vez de `seguimiento`, y el panel filtra por igualdad exacta de texto,
así que quedan fuera. *2026-08-28*

Revisado el 2026-10-26: no todos son seguimientos. Hasta el 27 de agosto el
formulario de Perú ofrecía Admisión, Seguimiento 1, Seguimiento 2 y Egreso, sin
"en tratamiento", así que quien aplicaba el TOP a un paciente que ya estaba en
tratamiento marcaba Seguimiento 1. Los 7 que tienen un ingreso antes pasaron a
`seguimiento` el 27 de octubre, y uno más se resolvió al borrar su copia vieja.
Ojo con los 7 que pasaron a `seguimiento`: según Rodrigo, lo más probable es
que sean TOP aplicados durante el tratamiento (`en_tratamiento`), porque el
formulario antiguo de Perú no tenía esa opción y "Seguimiento 1" se usaba para
eso. Entre el ingreso y ese TOP pasaron de 1,5 a 4,5 meses. Se incluyen en la
consulta a los centros: ¿seguía en tratamiento o ya había egresado? Si no
responden, pasan a `en_tratamiento`. *2026-10-27*

Los otros 25 (23 son el primer TOP del paciente, EESS28CI
concentra 16) se le preguntan al centro; si no responde en el plazo, pasan a
`en_tratamiento`. Propuesta presentada a la mesa el 26 de octubre.

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

**Semanas en blanco en VIF y en días de trabajo y educación.** Los formularios
las suman como cero, igual que en sustancias, pero la regla no está decidida.
En trabajo y educación, además, convive con la casilla "No aplica". *2026-10-25*

**Opcional: rellenar con 0 las semanas en blanco al enviar.** En sustancias el
cálculo ya las toma como cero; rellenarlas dejaría el dato explícito en la base
sin bloquear a nadie. No se decidió hacerlo. *2026-10-25*


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
