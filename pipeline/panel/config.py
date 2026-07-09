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

# Paleta consistente con app.py y mockup aprobado
COLOR_VERDE    = '#8BC34A'
COLOR_AMARILLO = '#F0A836'
COLOR_ROJO     = '#E15D5D'
COLOR_GRIS     = '#B4BAC2'   # centros sin registros

# ═══════════════════════════════════════════════════════════════════════════════
# PALETA CENTRALIZADA DEL PANEL
# Paleta oficial QALAT aprobada por Rodrigo.
# ═══════════════════════════════════════════════════════════════════════════════

PALETA_PRINCIPAL   = '#004AAD'   # Azul Royal (RGB 0,74,173) — barras principales
PALETA_SECUNDARIO  = '#E5E5E5'   # Gris claro (RGB 229,229,229) — fondos / no-destacado
PALETA_VERDE       = '#1D9E75'   # Verde (RGB 29,158,117) — continuidad, positivo
PALETA_ROJO        = '#D95F5F'   # Rojo suave — transgresión, alertas, umbral salud
PALETA_NEUTRO      = '#A0B4C8'   # Gris azulado neutro — "Otras", sin dato
PALETA_FONDO_REF   = '#F2F4F7'   # Gris muy claro — fondo de barra referencia
PALETA_REF_LINE    = '#B0B8C1'   # Gris medio — línea punteada de referencia
PALETA_TEXTO       = '#1F3864'   # Azul oscuro — texto general
PALETA_MUJER       = '#7B68EE'   # Púrpura suave — dona sexo mujeres
PALETA_OTROS_SEXO  = '#B4BAC2'   # Gris — dona sexo otros


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


def prioridad_semaforo(dias_desde_ultimo):
    """
    Devuelve un entero para ordenar centros por color:
      0 = verde (activo), 1 = amarillo (atrasado), 2 = rojo (inactivo), 3 = gris (sin datos)
    """
    if _es_vacio(dias_desde_ultimo):
        return 3
    if dias_desde_ultimo <= SEMAFORO_UMBRAL_VERDE:
        return 0
    if dias_desde_ultimo <= SEMAFORO_UMBRAL_AMARILLO:
        return 1
    return 2


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


def continuidad_por_centro(df):
    """
    Para cada centro calcula el % de pacientes con ingreso que también
    tienen al menos un segundo registro TOP (cualquier etapa distinta de ingreso).

    Definición operativa (aprobada por Rodrigo, sesión 3):
      Numerador  = pacientes del centro con etapa='ingreso' que aparecen
                   además con etapa in {en_tratamiento, egreso, seguimiento}
      Denominador = pacientes del centro con etapa='ingreso'

    Args:
        df: DataFrame con columnas 'centro', 'etapa', 'codigo_paciente'

    Returns:
        pd.DataFrame con columnas: centro, n_ingresos, n_con_continuidad,
        pct_continuidad (float 0-100). Ordenado descendente por pct_continuidad.
    """
    cols_req = {'centro', 'etapa', 'codigo_paciente'}
    if df is None or df.empty or not cols_req.issubset(df.columns):
        return pd.DataFrame(columns=[
            'centro', 'n_ingresos', 'n_con_continuidad', 'pct_continuidad'
        ])

    tmp = df.copy()
    tmp['centro']          = tmp['centro'].astype(str).str.strip()
    tmp['etapa']           = tmp['etapa'].fillna('').astype(str)
    tmp['codigo_paciente'] = tmp['codigo_paciente'].astype(str).str.strip()
    tmp = tmp[(tmp['centro'] != '') & (tmp['codigo_paciente'] != '')]

    filas = []
    ETAPAS_SEGUNDA = {'en_tratamiento', 'egreso', 'seguimiento'}
    for centro, grupo in tmp.groupby('centro'):
        pacientes_ingreso = set(
            grupo.loc[grupo['etapa'] == 'ingreso', 'codigo_paciente']
        )
        pacientes_segunda = set(
            grupo.loc[grupo['etapa'].isin(ETAPAS_SEGUNDA), 'codigo_paciente']
        )
        n_ing  = len(pacientes_ingreso)
        n_cont = len(pacientes_ingreso & pacientes_segunda)
        pct    = (n_cont / n_ing * 100) if n_ing > 0 else 0.0
        filas.append({
            'centro':            centro,
            'n_ingresos':        n_ing,
            'n_con_continuidad': n_cont,
            'pct_continuidad':   pct,
        })

    if not filas:
        return pd.DataFrame(columns=[
            'centro', 'n_ingresos', 'n_con_continuidad', 'pct_continuidad'
        ])

    out = pd.DataFrame(filas)
    return out.sort_values('pct_continuidad', ascending=False).reset_index(drop=True)


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS DE UI COMPARTIDOS
# ═══════════════════════════════════════════════════════════════════════════════

def titulo_seccion(icono, texto, subtitulo=None):
    """
    Devuelve el HTML del título de una sección del Panel de gestión.
    Reemplaza la vieja franja azul '.sec' por un título limpio dentro
    de la card blanca (que se activa con st.container(border=True)).

    Args:
        icono: emoji o carácter unicode (ej: '🚦', '🏆')
        texto: título principal en negro
        subtitulo: opcional, texto gris pequeño debajo
    """
    sub_html = (
        f'<div style="font-size:.72rem;color:#777;margin-top:.05rem;line-height:1.15;">{subtitulo}</div>'
        if subtitulo else ''
    )
    return (
        f'<div style="padding:.02rem .1rem .18rem .1rem;">'
        f'  <div style="font-size:.92rem;font-weight:600;color:#1F1F1F;line-height:1.15;">'
        f'    {icono}&nbsp;&nbsp;{texto}'
        f'  </div>'
        f'  {sub_html}'
        f'</div>'
    )
