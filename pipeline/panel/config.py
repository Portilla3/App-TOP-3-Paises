"""
pipeline.panel.config — Constantes y helpers compartidos por componentes del Panel.

Centraliza:
  - Umbrales de color del semáforo de actividad
  - Paleta de colores del panel
  - Helper para extraer catálogo de centros desde el DataFrame de un país

Diseño:
  - HOY el catálogo de centros se deriva empíricamente del df (Decisión B de sesión 2).
  - En sesiones futuras, si algún país necesita mostrar centros configurados
    que aún no han reportado, se agregará un catálogo estático como fallback
    y se hará union con lo que exista en la base.
"""
import pandas as pd


# ═══════════════════════════════════════════════════════════════════════════════
# UMBRALES DEL SEMÁFORO DE ACTIVIDAD (días desde el último registro)
# ═══════════════════════════════════════════════════════════════════════════════

SEMAFORO_UMBRAL_VERDE     = 14   # 0-14 días  → verde   (activo)
SEMAFORO_UMBRAL_AMARILLO  = 44   # 15-44 días → amarillo (atrasado)
                                 # 45+ días   → rojo    (inactivo)

# Paleta consistente con app.py
COLOR_VERDE    = '#538135'
COLOR_AMARILLO = '#E8A100'
COLOR_ROJO     = '#C00000'
COLOR_GRIS     = '#9AA0A6'   # centros sin registros


def _es_vacio(dias):
    """True si el valor representa 'sin dato' (None, NaN, o negativo)."""
    if dias is None:
        return True
    try:
        # NaN != NaN es True; también atrapa strings raros
        if dias != dias:
            return True
        return float(dias) < 0
    except (TypeError, ValueError):
        return True


def color_semaforo(dias_desde_ultimo):
    """
    Devuelve el color hex correspondiente al número de días desde el último registro.

    Args:
        dias_desde_ultimo: int/float o None/NaN. Sin datos → gris.
    """
    if _es_vacio(dias_desde_ultimo):
        return COLOR_GRIS
    if dias_desde_ultimo <= SEMAFORO_UMBRAL_VERDE:
        return COLOR_VERDE
    if dias_desde_ultimo <= SEMAFORO_UMBRAL_AMARILLO:
        return COLOR_AMARILLO
    return COLOR_ROJO


def etiqueta_semaforo(dias_desde_ultimo):
    """Devuelve la etiqueta textual para tooltips."""
    if _es_vacio(dias_desde_ultimo):
        return 'sin registros'
    if dias_desde_ultimo <= SEMAFORO_UMBRAL_VERDE:
        return 'activo'
    if dias_desde_ultimo <= SEMAFORO_UMBRAL_AMARILLO:
        return 'atrasado'
    return 'inactivo'


# ═══════════════════════════════════════════════════════════════════════════════
# CATÁLOGO DE CENTROS POR PAÍS
# ═══════════════════════════════════════════════════════════════════════════════

def obtener_centros_pais(df):
    """
    Extrae la lista ordenada de códigos de centro presentes en el DataFrame.

    Args:
        df: DataFrame de un país (columna 'centro' esperada)

    Returns:
        list[str] ordenada alfabéticamente. Vacía si no hay datos.
    """
    if df is None or df.empty or 'centro' not in df.columns:
        return []
    centros = df['centro'].dropna().astype(str).str.strip()
    centros = centros[centros != '']
    return sorted(centros.unique().tolist())


def actividad_por_centro(df, hoy=None):
    """
    Para cada centro calcula: última fecha de entrevista y días transcurridos.

    Args:
        df: DataFrame con columnas 'centro' y 'fecha_entrevista'
        hoy: opcional pd.Timestamp para tests. Por defecto, fecha actual.

    Returns:
        pd.DataFrame con columnas: centro, ultima_fecha (Timestamp), dias (int),
        n_registros (int). Ordenado alfabéticamente por centro.
    """
    if df is None or df.empty or 'centro' not in df.columns:
        return pd.DataFrame(columns=['centro', 'ultima_fecha', 'dias', 'n_registros'])

    if hoy is None:
        hoy = pd.Timestamp.now().normalize()

    tmp = df.copy()
    tmp['centro'] = tmp['centro'].astype(str).str.strip()
    tmp = tmp[tmp['centro'] != '']

    if 'fecha_entrevista' not in tmp.columns:
        # Sin fechas, todos gris con conteo
        agg = tmp.groupby('centro').size().reset_index(name='n_registros')
        agg['ultima_fecha'] = pd.NaT
        agg['dias']         = None
        return agg.sort_values('centro').reset_index(drop=True)

    tmp['fecha_entrevista'] = pd.to_datetime(tmp['fecha_entrevista'], errors='coerce')

    agg = tmp.groupby('centro').agg(
        ultima_fecha=('fecha_entrevista', 'max'),
        n_registros =('fecha_entrevista', 'size'),
    ).reset_index()

    agg['dias'] = agg['ultima_fecha'].apply(
        lambda f: int((hoy - f.normalize()).days) if pd.notna(f) else None
    )

    return agg.sort_values('centro').reset_index(drop=True)


def ingresos_por_centro(df):
    """
    Cuenta registros con etapa='ingreso' por centro.

    Args:
        df: DataFrame con columnas 'centro' y 'etapa'

    Returns:
        pd.DataFrame con columnas: centro, n_ingresos.
        Ordenado descendente por n_ingresos.
    """
    if df is None or df.empty or 'centro' not in df.columns:
        return pd.DataFrame(columns=['centro', 'n_ingresos'])

    if 'etapa' not in df.columns:
        return pd.DataFrame(columns=['centro', 'n_ingresos'])

    tmp = df.copy()
    tmp['centro'] = tmp['centro'].astype(str).str.strip()
    tmp['etapa']  = tmp['etapa'].fillna('').astype(str)
    tmp = tmp[(tmp['centro'] != '') & (tmp['etapa'] == 'ingreso')]

    agg = tmp.groupby('centro').size().reset_index(name='n_ingresos')
    return agg.sort_values('n_ingresos', ascending=False).reset_index(drop=True)
