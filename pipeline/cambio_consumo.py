"""
pipeline.cambio_consumo — Clasificación del cambio en días de consumo.

Fuente única para comparar los días de consumo de una sustancia entre el TOP de
ingreso y el de seguimiento. Antes de este módulo, la misma lógica estaba escrita
cuatro veces (seg_excel.py, word_seg.py, pdf_seg.py, pptx_seg.py) y cualquier
corrección había que replicarla en las cuatro.

Qué cambia respecto de la versión anterior
------------------------------------------
1. Las categorías ahora son excluyentes. Antes se contaban con cuatro condiciones
   independientes, de modo que un paciente con cero días en ambos momentos podía
   caer a la vez en "abstinencia" (seguimiento en cero) y en "sin cambio" (los dos
   valores iguales). No se notaba porque el filtro previo dejaba fuera esos casos.

2. Se incorporan los pacientes que ingresan sin consumo. Antes quedaban excluidos
   del análisis, de manera que una recaída, es decir alguien que ingresa en
   abstinencia y consume en el seguimiento, no aparecía en ninguna categoría. Se
   separan en dos grupos propios: quien se mantiene sin consumo y quien inicia.

3. El dato faltante deja de contarse como cero. Antes se convertía a cero antes de
   clasificar, y como la abstinencia se define como un cero en el seguimiento, un
   campo vacío en el segundo TOP se contaba como abstinencia.

Sobre el alcance de la clasificación
------------------------------------
Esto mide cambio bruto en días, no cambio clínicamente significativo. El estándar
del instrumento usa el índice de cambio fiable de Jacobson y Truax, que exige que
la diferencia supere el error de medición antes de llamarla mejoría o deterioro.
Ese índice requiere la confiabilidad de cada ítem y la desviación estándar de la
población propia, y su implementación quedó pendiente para cuando la base regional
tenga volumen suficiente. Mientras tanto, los rótulos dicen "disminuyó" y "aumentó",
no "mejoró" y "empeoró", que es lo que el cálculo efectivamente respalda.
"""
import pandas as pd

# Orden de presentación. Las seis son excluyentes entre sí y suman el N válido.
CATEGORIAS = [
    ('sin_consumo', 'Se mantiene sin consumo'),
    ('inicio',      'Inició consumo'),
    ('abstinencia', 'Abstinencia'),
    ('disminuyo',   'Disminuyó'),
    ('sin_cambio',  'Sin cambio'),
    ('aumento',     'Aumentó'),
]


def clasificar_cambio(v1, v2):
    """
    Clasifica el cambio en días de consumo de una sustancia entre dos mediciones.

    Args:
        v1: Serie con los días de consumo en el TOP de ingreso.
        v2: Serie con los días de consumo en el TOP de seguimiento.

    Returns:
        dict con los conteos por categoría, sus porcentajes sobre el N válido,
        el N válido y el número de pacientes que consumían al ingreso.

    Solo entran los pacientes con dato numérico en ambos momentos. Quien tenga el
    campo vacío en cualquiera de los dos queda fuera del N válido, no en cero.
    """
    s1 = pd.to_numeric(pd.Series(v1), errors='coerce')
    s2 = pd.to_numeric(pd.Series(v2), errors='coerce')

    valido = s1.notna() & s2.notna()
    s1 = s1[valido]
    s2 = s2[valido]
    n = int(len(s1))

    consumia = s1 > 0
    out = {
        'n_valido': n,
        'n_consumia_ingreso': int(consumia.sum()),
        'sin_consumo': int(((~consumia) & (s2 == 0)).sum()),
        'inicio':      int(((~consumia) & (s2 > 0)).sum()),
        'abstinencia': int((consumia & (s2 == 0)).sum()),
        'disminuyo':   int((consumia & (s2 > 0) & (s2 < s1)).sum()),
        'sin_cambio':  int((consumia & (s2 == s1)).sum()),
        'aumento':     int((consumia & (s2 > s1)).sum()),
    }

    for clave, _ in CATEGORIAS:
        out['pct_' + clave] = round(out[clave] / n * 100, 1) if n else 0.0

    # Porcentajes sobre quienes consumían al ingreso, para las cuatro categorías
    # clásicas. Son los que se venían informando y permiten comparar con reportes
    # anteriores y con la literatura, que usa esa misma base.
    nc = out['n_consumia_ingreso']
    for clave in ('abstinencia', 'disminuyo', 'sin_cambio', 'aumento'):
        out['pct_cons_' + clave] = round(out[clave] / nc * 100, 1) if nc else 0.0

    return out


def verificar_particion(res):
    """
    Comprueba que las seis categorías sumen exactamente el N válido. Sirve como
    resguardo en caso de que alguien agregue una condición y rompa la exclusión
    mutua, que es justamente el error que este módulo vino a corregir.
    """
    suma = sum(res[clave] for clave, _ in CATEGORIAS)
    return suma == res['n_valido']
