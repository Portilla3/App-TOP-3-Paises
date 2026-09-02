# Pruebas de decisiones

Cada prueba de `test_decisiones.py` corresponde a una entrada de
`../DECISIONES.md`. No verifican que el código funcione, verifican que sigue
obedeciendo una decisión ya tomada.

**Si una falla**, hay dos posibilidades y ninguna es "arreglar la prueba":

1. Alguien rompió la regla sin darse cuenta. Se corrige el código.
2. La decisión cambió. Entonces falta su entrada nueva en `DECISIONES.md`,
   con el fundamento, y recién ahí se actualiza la prueba.

Existen porque escribir una regla no alcanza. La convención H/M/O estaba escrita
desde el 28 de agosto y seis módulos seguían leyendo el sexo al revés. La regla
de que `validacion_top.py` es la única fuente de criterios estaba escrita el
mismo día, y el clasificador de sustancias seguía copiado en diez archivos cinco
días después. Lo que hace que una regla no se olvide no es escribirla más
grande, es que algo falle cuando se rompe.

## Cómo correrlas

```
pip install pytest
python -m pytest tests/ -v
```

## Deuda marcada

Una prueba está en `xfail(strict=True)`: la del clasificador duplicado. Eso
significa que hoy se espera que falle, y que el día que se pague la deuda la
prueba va a pasar y el `strict=True` va a exigir quitar el marcador. No es una
prueba apagada, es un recordatorio que se apaga solo.
