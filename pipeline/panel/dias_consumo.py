"""
pipeline.panel.dias_consumo — Días de consumo por sustancia principal al ingreso.

Para cada categoría de sustancia principal declarada calcula el promedio de días
consumidos en las últimas 4 semanas (columna _total de Supabase, escala 0-28),
usando SOLO los pacientes que declararon esa sustancia como principal.

Lógica:
  1. Filtrar etapa=ingreso
  2. Clasificar sustancia_principal con la misma taxonomía de panel/sustancia.py
  3. Para cada categoría canónica, tomar la columna _total correspondiente
     y calcular el promedio entre quienes tienen valor > 0
  4. Excluir categorías sin columna _total disponible (Tusi, Ketamina, etc.)

Mapeo categoría → columna Supabase:
  Alcohol          → alcohol_total
  Marihuana        → marihuana_total
  Cocaína          → cocaina_total
  Pasta base       → pastabase_total
  Sedantes         → sedantes_total
  (resto: sin columna _total → no se muestran)

Diseño:
  - Barras horizontales ordenadas desc por promedio
  - Escala fija 0-28, línea de referencia en 14 días
  - Valor del promedio anotado al final de cada barra
  - N pacientes en hover

Función expuesta:
  render(df, pais, centro_id=None)
"""
import re as _re
import unicodedata

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from pipeline.panel.config import titulo_seccion
from pipeline.panel.sustancia import _clasificar_sustancia   # reutiliza la misma taxonomía


# Mapeo categoría canónica → columna _total en Supabase
_CAT_A_COL = {
    'Alcohol':         'alcohol_total',
    'Cannabis/Marihuana': 'marihuana_total',
    'Cocaína':         'cocaina_total',
    'Pasta base':      'pastabase_total',
    'Sedantes':        'sedantes_total',
}

COLOR_BARRA   = '#004AAD'   # from config PALETA_PRINCIPAL
COLOR_REF     = '#B0B8C1'   # from config PALETA_REF_LINE
TEXTO_OSCURO  = '#004AAD'
ALTO_BARRA_PX = 32


def _calcular_dias(df):
    """
    Filtra etapa=ingreso, clasifica sustancia_principal y calcula el promedio
    de días de consumo para cada categoría canónica con columna _total disponible.

    Retorna lista de dicts ordenados desc por promedio.
    """
    cols_req = {'etapa', 'sustancia_principal'}
    if df is None or df.empty or not cols_req.issubset(df.columns):
        return []

    df_ing = df[df['etapa'].astype(str).str.strip() == 'ingreso'].copy()
    if df_ing.empty:
        return []

    # Clasificar sustancia principal (reutiliza taxonomía de sustancia.py)
    df_ing['_cat'] = df_ing['sustancia_principal'].apply(
        lambda v: _clasificar_sustancia(v)[0]
    )

    resultado = []
    for cat, col in _CAT_A_COL.items():
        if col not in df_ing.columns:
            continue
        # Solo pacientes que declararon esta categoría como principal
        mask = df_ing['_cat'] == cat
        if not mask.any():
            continue
        serie = pd.to_numeric(df_ing.loc[mask, col], errors='coerce')
        con_valor = serie[serie > 0]
        if con_valor.empty:
            continue
        resultado.append({
            'sustancia': cat,
            'promedio':  round(con_valor.mean(), 1),
            'n':         len(con_valor),
            'n_cat':     int(mask.sum()),   # total que declararon esta como principal
        })

    resultado.sort(key=lambda x: x['promedio'], reverse=True)
    return resultado


def _figura(datos):
    labels  = [d['sustancia'] for d in datos]
    valores = [d['promedio']  for d in datos]
    textos  = [f"<b>{d['promedio']}</b>" for d in datos]
    hovers  = [
        f"<b>{d['sustancia']}</b><br>"
        f"Promedio: {d['promedio']} días<br>"
        f"Pacientes con consumo: {d['n']} de {d['n_cat']} que la declararon principal"
        for d in datos
    ]

    ancho_barra = 80   # px por barra en modo vertical
    alto = 220

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=labels,
        y=valores,
        orientation='v',
        marker_color=COLOR_BARRA,
        text=textos,
        textposition='outside',
        hovertext=hovers,
        hoverinfo='text',
        cliponaxis=False,
    ))

    # Línea de referencia en 14 días
    fig.add_shape(
        type='line',
        x0=-0.5, x1=len(datos) - 0.5, y0=14, y1=14,
        line=dict(color=COLOR_REF, width=1.5, dash='dot'),
        layer='below',
    )
    fig.add_annotation(
        x=len(datos) - 0.5, y=14,
        text='14 días',
        showarrow=False,
        font=dict(size=9, color=COLOR_REF),
        yanchor='bottom',
        xanchor='right',
    )

    fig.update_layout(
        height=alto,
        margin=dict(l=10, r=10, t=24, b=8),
        yaxis=dict(
            range=[0, 31],
            tickvals=[0, 7, 14, 21, 28],
            ticktext=['0', '7', '14', '21', '28'],
            title=None,
            gridcolor='#F0F0F0',
            zeroline=False,
        ),
        xaxis=dict(
            title=None,
            tickfont=dict(size=10),
            fixedrange=True,
        ),
        bargap=0.35,
        plot_bgcolor='white',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Inter, sans-serif', color=TEXTO_OSCURO),
        showlegend=False,
    )
    return fig


def render(df, pais, centro_id=None):
    with st.container(border=True):
        st.markdown(
            titulo_seccion(
                '📅', 'Días de consumo · sustancia principal',
                'promedio de días en las últimas 4 semanas · solo pacientes al ingreso'
            ),
            unsafe_allow_html=True,
        )

        if centro_id:
            df = df[df['centro'].astype(str).str.strip() == str(centro_id).strip()].copy()

        datos = _calcular_dias(df)

        if not datos:
            st.caption('Sin datos de consumo disponibles para este país.')
            return

        st.plotly_chart(_figura(datos), use_container_width=True,
                        config={'displayModeBar': False})
