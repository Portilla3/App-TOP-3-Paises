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

from pipeline.panel.seguimiento_core import calcular_seguimiento, NOTA_SEGUIMIENTO


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
            'seg_elegibles':            0,
            'pct_con_seguimiento':      0.0,
            'seg_nota':                 NOTA_SEGUIMIENTO,
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

    pacientes_ingresados = len(pac_ingresados)

    # ── Cobertura de seguimiento: DEFINICIÓN HOMOLOGADA (fuente única) ──────────
    # NO se cuenta por etiqueta de etapa. Un paciente "tiene seguimiento" si tiene
    # un 2º TOP (fecha distinta), y el denominador son los pacientes con 90+ días
    # desde su primer TOP. Ver pipeline/panel/seguimiento_core.py
    seg = calcular_seguimiento(df)
    pacientes_con_seguimiento = seg['n_con_top2']
    seg_elegibles             = seg['n_elegibles']
    pct_con_seguimiento       = seg['pct_cobertura']
    seg_nota                  = seg['nota']

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
        'seg_elegibles':            seg_elegibles,
        'pct_con_seguimiento':      pct_con_seguimiento,
        'seg_nota':                 seg_nota,
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

    # Tamaños tipográficos aumentados solo para el Panel de gestión.
    # Override de los estilos globales de app.py (.kpi-lbl, .kpi-val, .kpi-sub).
    S_LBL = 'font-size:.95rem;color:#555;margin-bottom:.25rem;font-weight:500;'
    S_VAL = 'font-size:2.3rem;font-weight:800;color:#1F3864;line-height:1.05;'
    S_SUB = 'font-size:.85rem;color:#777;margin-top:.25rem;'

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(
            f'''<div class="kpi">
                <div style="{S_LBL}">Total de registros</div>
                <div style="{S_VAL}">{m["total_registros"]:,}</div>
                <div style="{S_SUB}">{m["n_ingresos"]:,} ingresos + {m["n_seguimientos"]:,} seguimientos</div>
            </div>'''.replace(',', '.'),
            unsafe_allow_html=True
        )

    with col2:
        st.markdown(
            f'''<div class="kpi">
                <div style="{S_LBL}">Pacientes ingresados</div>
                <div style="{S_VAL}">{m["pacientes_ingresados"]:,}</div>
                <div style="{S_SUB}">primera evaluación aplicada</div>
            </div>'''.replace(',', '.'),
            unsafe_allow_html=True
        )

    with col3:
        color_class = 'green' if m['pct_con_seguimiento'] >= 10 else ('orange' if m['pct_con_seguimiento'] >= 3 else 'red')
        st.markdown(
            f'''<div class="kpi {color_class}">
                <div style="{S_LBL}">Con seguimiento</div>
                <div style="{S_VAL}">{m["pct_con_seguimiento"]:.1f}%</div>
                <div style="{S_SUB}">{m["pacientes_con_seguimiento"]:,} de {m["seg_elegibles"]:,} elegibles</div>
            </div>'''.replace(',', '.'),
            unsafe_allow_html=True
        )

    with col4:
        st.markdown(
            f'''<div class="kpi">
                <div style="{S_LBL}">Centros activos</div>
                <div style="{S_VAL}">{m["centros_activos"]}</div>
                <div style="{S_SUB}">con al menos un registro</div>
            </div>''',
            unsafe_allow_html=True
        )

    # Nota obligatoria: base del denominador de seguimiento (definición homologada)
    st.markdown(
        f'<div style="font-size:.78rem;color:#888;margin-top:.4rem;">ℹ {m["seg_nota"]}</div>',
        unsafe_allow_html=True
    )
