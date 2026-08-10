"""
seguimiento_core.py — FUENTE ÚNICA de la definición de seguimiento (TOP2).

Toda pantalla o reporte que muestre cobertura de seguimiento DEBE llamar a
`calcular_seguimiento()`. No recalcular en otro lado: si la definición se
duplica, se vuelve a desincronizar (que es el bug que estamos corrigiendo).

DEFINICIÓN HOMOLOGADA (acordada con Rodrigo, agosto 2026)
─────────────────────────────────────────────────────────
1. Deduplicación: si un paciente tiene dos registros con la MISMA fecha de
   entrevista, se cuenta uno solo (elimina duplicados de carga).
2. TOP1 / TOP2 por conteo, NO por etiqueta de etapa:
   - Se ordenan los TOP del paciente por fecha.
   - El primero es el TOP1.
   - Si existe un segundo TOP con fecha DISTINTA, ese es el TOP2.
   - La columna 'etapa' no interviene en este cálculo.
3. Elegibilidad: un paciente "corresponde seguimiento" si su TOP1 tiene
   `dias_umbral` o más días de antigüedad respecto a hoy. Default = 60 días,
   porque hay centros que aplican la segunda medición a los 60 días.
4. Cobertura = (pacientes elegibles con TOP2) / (pacientes elegibles) * 100.
5. Nota fija obligatoria en toda visualización: ver NOTA_SEGUIMIENTO.

El paciente se asigna al centro de su TOP1.
"""

import pandas as pd

DIAS_UMBRAL_DEFAULT = 90
NOTA_SEGUIMIENTO = "Calculado sobre pacientes con 90 o más días desde su primer TOP."


def calcular_seguimiento(df, hoy=None, dias_umbral=DIAS_UMBRAL_DEFAULT,
                         col_cod='codigo_paciente', col_fecha='fecha_entrevista',
                         col_centro='centro'):
    """
    Retorna un dict con los números canónicos de seguimiento.

    Claves:
      dias_umbral       int   umbral usado
      total_pacientes   int   pacientes únicos (tras dedup)
      n_elegibles       int   pacientes con TOP1 de dias_umbral+ días
      n_con_top2        int   elegibles que ya tienen un 2º TOP
      n_sin_top2        int   elegibles pendientes (= n_elegibles - n_con_top2)
      pct_cobertura     float % = n_con_top2 / n_elegibles * 100
      nota              str   texto fijo para mostrar
      por_centro        DataFrame [centro, elegibles, con_top2, sin_top2, pct]
    """
    vacio = {
        'dias_umbral': dias_umbral, 'total_pacientes': 0, 'n_elegibles': 0,
        'n_con_top2': 0, 'n_sin_top2': 0, 'pct_cobertura': 0.0,
        'nota': _nota(dias_umbral),
        'por_centro': pd.DataFrame(columns=['centro', 'elegibles', 'con_top2', 'sin_top2', 'pct']),
    }
    if df is None or len(df) == 0 or col_cod not in df.columns or col_fecha not in df.columns:
        return vacio

    hoy = pd.Timestamp(hoy).normalize() if hoy is not None else pd.Timestamp.now().normalize()

    d = df.copy()
    d[col_cod] = d[col_cod].astype(str).str.strip()
    d = d[d[col_cod] != '']
    d[col_fecha] = pd.to_datetime(d[col_fecha], errors='coerce')
    d = d.dropna(subset=[col_fecha])
    # Ignorar fechas futuras (errores de captura)
    d = d[d[col_fecha] <= hoy]
    if d.empty:
        return vacio

    # 1) dedup exacto: mismo paciente + misma fecha = un solo TOP
    d = d.drop_duplicates(subset=[col_cod, col_fecha])

    # 2) por paciente: primer TOP, nº de TOP distintos, centro del TOP1
    d = d.sort_values([col_cod, col_fecha])
    tiene_centro = col_centro in d.columns
    agg_kwargs = {'n_top': (col_fecha, 'nunique'), 'primer': (col_fecha, 'min')}
    per = d.groupby(col_cod).agg(**agg_kwargs).reset_index()
    if tiene_centro:
        centro_top1 = d.groupby(col_cod).first()[col_centro].reset_index()
        per = per.merge(centro_top1, on=col_cod, how='left')
    else:
        per[col_centro] = 'N/D'

    per['tiene_top2'] = per['n_top'] >= 2
    per['dias_top1'] = (hoy - per['primer']).dt.days
    per['elegible'] = per['dias_top1'] >= dias_umbral

    elig = per[per['elegible']]
    n_elig = int(len(elig))
    n_top2 = int(elig['tiene_top2'].sum())
    pct = round(100 * n_top2 / n_elig, 1) if n_elig else 0.0

    if n_elig:
        pc = elig.groupby(col_centro).agg(
            elegibles=('tiene_top2', 'size'),
            con_top2=('tiene_top2', 'sum'),
        ).reset_index().rename(columns={col_centro: 'centro'})
        pc['con_top2'] = pc['con_top2'].astype(int)
        pc['sin_top2'] = pc['elegibles'] - pc['con_top2']
        pc['pct'] = (100 * pc['con_top2'] / pc['elegibles']).round(1)
        pc = pc.sort_values('centro').reset_index(drop=True)
    else:
        pc = vacio['por_centro']

    return {
        'dias_umbral': dias_umbral,
        'total_pacientes': int(len(per)),
        'n_elegibles': n_elig,
        'n_con_top2': n_top2,
        'n_sin_top2': n_elig - n_top2,
        'pct_cobertura': pct,
        'nota': _nota(dias_umbral),
        'por_centro': pc,
    }


def cobertura_desde_wide(wide, hoy=None, dias_umbral=DIAS_UMBRAL_DEFAULT):
    """
    Igual definición que calcular_seguimiento, pero partiendo de la base WIDE
    (una fila por paciente, con 'Tiene_TOP2' y la columna de fecha del TOP1).
    La usan los reportes descargables (Excel/Word/PPT) para mostrar el MISMO
    porcentaje que las pantallas, sin volver a duplicar la lógica.

    Retorna: {n_elegibles, n_con_top2, pct_cobertura, nota}
    """
    base = {'n_elegibles': 0, 'n_con_top2': 0, 'pct_cobertura': 0.0, 'nota': _nota(dias_umbral)}
    if wide is None or len(wide) == 0 or 'Tiene_TOP2' not in wide.columns:
        return base

    hoy = pd.Timestamp(hoy).normalize() if hoy is not None else pd.Timestamp.now().normalize()
    col_f1 = next((c for c in wide.columns
                   if 'fecha entrevista' in c.lower() and c.endswith('_TOP1')), None)
    if col_f1 is None:
        return base

    dias = (hoy - pd.to_datetime(wide[col_f1], errors='coerce')).dt.days
    elegible = dias >= dias_umbral
    tiene = wide['Tiene_TOP2'].astype(str).str.strip().isin(['Sí', 'Si'])
    n_elig = int(elegible.sum())
    n_con = int((elegible & tiene).sum())
    return {
        'n_elegibles': n_elig,
        'n_con_top2': n_con,
        'pct_cobertura': round(100 * n_con / n_elig, 1) if n_elig else 0.0,
        'nota': _nota(dias_umbral),
    }


def _nota(dias_umbral):
    return f"Calculado sobre pacientes con {dias_umbral} o más días desde su primer TOP."
