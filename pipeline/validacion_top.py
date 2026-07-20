"""
pipeline.validacion_top — Criterios de validación compartidos para datos TOP.

Fuente de verdad única para los umbrales que definen un valor "imposible" en
el instrumento TOP. Usado tanto por el pipeline de reportes (wide_top.py,
caract_excel.py) como por el dashboard interactivo (pipeline/panel/*.py),
para que ambos apliquen exactamente el mismo criterio y no diverjan cuando
entre un dato sucio nuevo.

Decisión de arquitectura (2026-07-20): antes de este módulo, cada consumidor
reimplementaba su propio filtro (dias_consumo.py duplicaba el filtro 0-28;
edad.py y salud.py no filtraban nada). Este módulo centraliza esos criterios.

Criterios:
  - Días de consumo semanal:  0-7   (una semana tiene 7 días)
  - Días de consumo mensual:  0-28  (4 semanas)
  - Fecha de nacimiento:      la edad calculada (contra fecha_entrevista, o
                               contra hoy si no hay fecha_entrevista) debe
                               estar entre 10 y 100 años. Criterio dinámico
                               (no un año fijo), igual al que ya usaba
                               wide_top.py antes de este módulo.
  - Escalas de salud/calidad de vida (TOP): 0-20

No confundir con el rango de pandas (años 1677-2262), que es un límite
técnico de la librería, no un criterio clínico; se mantiene como resguardo
adicional dentro de edad_valida() pero no reemplaza el criterio clínico.
"""
import pandas as pd

# ── Umbrales centralizados ──────────────────────────────────────────────────
DIAS_SEMANA_MIN, DIAS_SEMANA_MAX = 0, 7
DIAS_MES_MIN, DIAS_MES_MAX = 0, 28

EDAD_MINIMA_ANIOS = 10
EDAD_MAXIMA_ANIOS = 100

ESCALA_SALUD_MIN, ESCALA_SALUD_MAX = 0, 20

_PANDAS_ANIO_MIN, _PANDAS_ANIO_MAX = 1677, 2262


def dias_validos_semana(serie):
    """
    Recibe una Serie numérica (días de consumo en una semana, columnas *_s1..*_s4)
    y devuelve una Serie del mismo largo donde los valores fuera de 0-7 quedan
    en NaN. No modifica el resto.
    """
    num = pd.to_numeric(serie, errors='coerce')
    return num.where((num >= DIAS_SEMANA_MIN) & (num <= DIAS_SEMANA_MAX))


def dias_validos_mes(serie):
    """
    Recibe una Serie numérica (columnas *_total, escala 0-28) y devuelve una
    Serie donde los valores fuera de 0-28 quedan en NaN.
    """
    num = pd.to_numeric(serie, errors='coerce')
    return num.where((num >= DIAS_MES_MIN) & (num <= DIAS_MES_MAX))


def fecha_nacimiento_valida(serie_fecha_nacimiento, serie_fecha_referencia=None):
    """
    Recibe una Serie de fecha_nacimiento (y opcionalmente una Serie de
    fecha_entrevista para calcular la edad contra esa fecha en vez de hoy) y
    devuelve una Serie de fechas donde los valores imposibles quedan en NaT.

    Imposible = la edad calculada es menor a EDAD_MINIMA_ANIOS o mayor a
    EDAD_MAXIMA_ANIOS, o la fecha cae fuera del rango técnico que pandas
    puede representar (1677-2262).
    """
    fn = pd.to_datetime(serie_fecha_nacimiento, errors='coerce')

    if serie_fecha_referencia is not None:
        ref = pd.to_datetime(serie_fecha_referencia, errors='coerce')
        ref = ref.fillna(pd.Timestamp.now())
    else:
        ref = pd.Timestamp.now()

    edad_anios = (ref - fn).dt.days / 365.25

    invalida = (
        fn.isna()
        | (edad_anios < EDAD_MINIMA_ANIOS)
        | (edad_anios > EDAD_MAXIMA_ANIOS)
        | (fn.dt.year < _PANDAS_ANIO_MIN)
        | (fn.dt.year > _PANDAS_ANIO_MAX)
    )
    return fn.where(~invalida)


def edad_valida(serie_fecha_nacimiento, serie_fecha_referencia=None):
    """
    Igual que fecha_nacimiento_valida(), pero devuelve directamente la edad en
    años (float), con NaN donde la fecha de nacimiento es inválida. Pensado
    para pipeline/panel/edad.py, que necesita la edad, no la fecha.
    """
    fn_valida = fecha_nacimiento_valida(serie_fecha_nacimiento, serie_fecha_referencia)

    if serie_fecha_referencia is not None:
        ref = pd.to_datetime(serie_fecha_referencia, errors='coerce')
        ref = ref.fillna(pd.Timestamp.now())
    else:
        ref = pd.Timestamp.now()

    return (ref - fn_valida).dt.days / 365.25


def escala_salud_valida(serie):
    """
    Recibe una Serie numérica (salud_psicologica, salud_fisica, calidad_vida,
    escala 0-20 en el instrumento TOP) y devuelve una Serie donde los valores
    fuera de 0-20 quedan en NaN.
    """
    num = pd.to_numeric(serie, errors='coerce')
    return num.where((num >= ESCALA_SALUD_MIN) & (num <= ESCALA_SALUD_MAX))
