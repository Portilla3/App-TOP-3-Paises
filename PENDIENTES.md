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

**Comparación panel contra Wide.** Los reportes leen el Base Wide y el panel lee
Supabase directo, con nombres de columna y filtros distintos. Falta correr los
dos caminos sobre los mismos datos y comparar. Requiere el export completo de
`top_registros`. *2026-09-02*
