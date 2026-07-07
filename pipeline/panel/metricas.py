"""
pipeline.panel.metricas — Métricas superiores del Panel de gestión.

Cuatro tarjetas en fila horizontal:
  1. Total de registros (con desglose "X ingresos + Y seguimientos")
  2. Pacientes ingresados (personas únicas con al menos un registro etapa=ingreso)
  3. Con seguimiento (% de ingresados que tienen al menos un seguimiento)
  4. Centros activos (X / N total)

Función expuesta:
  render(df, pais, centro_id=None)

Notas de diseño:
  - Componente agnóstico al instrumento: no depende de sustancias específicas
  - Si centro_id viene con valor, filtra el df antes de calcular
  - Usa la clase CSS 'kpi' que ya existe en app.py
"""
import streamlit as st
import pandas as pd


# ═══════════════════════════════════════════════════════════════════════════════
# CÁLCULOS PUROS (testeables sin Streamlit)
# ═══════════════════════════════════════════════════════════════════════════════

def _calcular_metricas(df):
    """
    Calcula las 4 métricas superiores a partir del DataFrame.

    Args:
        df: DataFrame con columnas snake_case de top_registros.
            Espera al menos: etapa, codigo_paciente, centro

    Returns:
        dict con claves:
            total_registros, n_ingresos, n_seguimientos,
            pacientes_ingresados, pacientes_con_seguimiento,
            pct_con_seguimiento, centros_activos, centros_totales
    """
    if df.empty:
        return {
            'total_registros':          0,
            'n_ingresos':               0,
            'n_seguimientos':           0,
            'pacientes_ingresados':     0,
            'pacientes_con_seguimiento': 0,
            'pct_con_seguimiento':      0.0,
            'centros_activos':          0,
            'centros_totales':          0,
        }

    etapa = df.get('etapa', pd.Series(dtype=str)).fillna('').astype(str)

    n_ingresos     = int((etapa == 'ingreso').sum())
    n_seguimientos = int((etapa == 'seguimiento').sum())
    total_registros = len(df)

    # Pacientes ingresados: códigos únicos con etapa=ingreso
    if 'codigo_paciente' in df.columns:
        pac_ingresados = set(
            df.loc[etapa == 'ingreso', 'codigo_paciente']
              .dropna().astype(str).str.strip()
        ) - {''}
        pac_seguimiento = set(
            df.loc[etapa == 'seguimiento', 'codigo_paciente']
              .dropna().astype(str).str.strip()
        ) - {''}
    else:
        pac_ingresados  = set()
        pac_seguimiento = set()

    pacientes_ingresados     = len(pac_ingresados)
    pacientes_con_seguimiento = len(pac_ingresados & pac_seguimiento)
    pct_con_seguimiento = (
        (pacientes_con_seguimiento / pacientes_ingresados * 100)
        if pacientes_ingresados > 0 else 0.0
    )

    # Centros activos: distintos códigos de centro con al menos 1 registro
    if 'centro' in df.columns:
        centros = df['centro'].dropna().astype(str).str.strip()
        centros = centros[centros != '']
        centros_activos = int(centros.nunique())
    else:
        centros_activos = 0

    # [TODO Etapa 1 sesión 2] centros_totales debería venir del catálogo
    # del país (ej: El Salvador tiene 8 centros configurados). Por ahora
    # usamos el conteo de activos como aproximación.
    centros_totales = centros_activos

    return {
        'total_registros':          total_registros,
        'n_ingresos':               n_ingresos,
        'n_seguimientos':           n_seguimientos,
        'pacientes_ingresados':     pacientes_ingresados,
        'pacientes_con_seguimiento': pacientes_con_seguimiento,
        'pct_con_seguimiento':      pct_con_seguimiento,
        'centros_activos':          centros_activos,
        'centros_totales':          centros_totales,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# RENDER
# ═══════════════════════════════════════════════════════════════════════════════

def render(df, pais, centro_id=None):
    """
    Pinta las 4 tarjetas de métricas superiores.

    Args:
        df: DataFrame de un solo país (ya filtrado por data.cargar_datos_pais)
        pais: nombre del país (para labels contextuales, no filtra)
        centro_id: si viene con valor, filtra df al centro antes de calcular
    """
    # Filtrado opcional por centro
    if centro_id and 'centro' in df.columns:
        df_local = df[df['centro'].astype(str).str.strip() == str(centro_id).strip()].copy()
    else:
        df_local = df

    m = _calcular_metricas(df_local)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(
            f'''<div class="kpi">
                <div class="kpi-lbl">Total de registros</div>
                <div class="kpi-val">{m["total_registros"]:,}</div>
                <div class="kpi-sub">{m["n_ingresos"]:,} ingresos + {m["n_seguimientos"]:,} seguimientos</div>
            </div>'''.replace(',', '.'),
            unsafe_allow_html=True
        )

    with col2:
        st.markdown(
            f'''<div class="kpi">
                <div class="kpi-lbl">Pacientes ingresados</div>
                <div class="kpi-val">{m["pacientes_ingresados"]:,}</div>
                <div class="kpi-sub">primera evaluación aplicada</div>
            </div>'''.replace(',', '.'),
            unsafe_allow_html=True
        )

    with col3:
        color_class = 'green' if m['pct_con_seguimiento'] >= 10 else ('orange' if m['pct_con_seguimiento'] >= 3 else 'red')
        st.markdown(
            f'''<div class="kpi {color_class}">
                <div class="kpi-lbl">Con seguimiento</div>
                <div class="kpi-val">{m["pct_con_seguimiento"]:.1f}%</div>
                <div class="kpi-sub">{m["pacientes_con_seguimiento"]:,} de {m["pacientes_ingresados"]:,} pacientes</div>
            </div>'''.replace(',', '.'),
            unsafe_allow_html=True
        )

    with col4:
        st.markdown(
            f'''<div class="kpi">
                <div class="kpi-lbl">Centros activos</div>
                <div class="kpi-val">{m["centros_activos"]}</div>
                <div class="kpi-sub">con al menos un registro</div>
            </div>''',
            unsafe_allow_html=True
        )
