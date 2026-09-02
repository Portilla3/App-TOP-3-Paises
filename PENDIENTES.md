# Pendientes

Hallazgos que aparecieron mientras se trabajaba en otra cosa. Se anotan acá para
no perderlos y para no desviar el trabajo en curso. No están priorizados entre
sí; el orden es de aparición.

---

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
