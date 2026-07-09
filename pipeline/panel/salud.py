"""
pipeline.panel.salud — Salud y Calidad de Vida al ingreso.

Muestra el promedio de las tres escalas de autopercepción (0-20):
  - Salud Psicológica  (salud_psicologica)
  - Salud Física       (salud_fisica)
  - Calidad de Vida    (calidad_vida)

Solo registros con etapa='ingreso'. Escala 0-20 (0=pésimo, 20=excelente).
Puntajes bajo 10 indican percepción deficiente.

Diseño: barras horizontales estilo informe (azul oscuro el más alto,
azul claro los demás), eje fijo 0-20, valor anotado al final.

Función expuesta:
  render(df, pais, centro_id=None)
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from pipeline.panel.config import titulo_seccion

COLOR_DESTAC = '#1A6B9A'   # from config PALETA_PRINCIPAL
COLOR_BASE   = '#A8C4E0'   # from config PALETA_SECUNDARIO
COLOR_REF    = '#D95F5F'   # from config PALETA_ROJO (umbral deficiente)
TEXTO_OSCURO = '#1F3864'

ESCALAS = [
    ('salud_psicologica', 'Salud Psicológica'),
    ('salud_fisica',      'Salud Física'),
    ('calidad_vida',      'Calidad de Vida'),
]


def _calcular_salud(df):
    vacio = {'items': [], 'n': 0}

    if df is None or df.empty or 'etapa' not in df.columns:
        return vacio

    df_ing = df[df['etapa'].astype(str).str.strip() == 'ingreso'].copy()
    if df_ing.empty:
        return vacio

    items = []
    n_valido = None
    for col, label in ESCALAS:
        if col not in df_ing.columns:
            continue
        serie = pd.to_numeric(df_ing[col], errors='coerce').dropna()
        if serie.empty:
            continue
        promedio = round(serie.mean(), 1)
        items.append({'label': label, 'promedio': promedio, 'n': len(serie)})
        if n_valido is None:
            n_valido = len(serie)

    return {'items': items, 'n': n_valido or 0}


def _figura(datos):
    items   = datos['items']
    labels  = [d['label']    for d in items][::-1]
    valores = [d['promedio'] for d in items][::-1]

    max_val = max(valores) if valores else 0
    colores = [COLOR_DESTAC if v == max_val else COLOR_BASE for v in valores]
    textos  = [f"{v}/20" for v in valores]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=labels,
        x=valores,
        orientation='h',
        marker_color=colores,
        text=textos,
        textposition='outside',
        textfont=dict(size=10, color=TEXTO_OSCURO),
        hovertemplate='%{y}: %{x}/20<extra></extra>',
        cliponaxis=False,
    ))

    # Línea de referencia en 10 (umbral de percepción deficiente)
    fig.add_shape(
        type='line',
        x0=10, x1=10, y0=-0.5, y1=len(items) - 0.5,
        line=dict(color=COLOR_REF, width=1.2, dash='dot'),
        layer='below',
    )
    fig.add_annotation(
        x=10, y=len(items) - 0.5,
        text='10',
        showarrow=False,
        font=dict(size=8, color=COLOR_REF),
        yanchor='bottom',
        xanchor='center',
    )

    fig.update_layout(
        height=210,
        margin=dict(l=0, r=60, t=4, b=8),
        xaxis=dict(
            range=[0, 23],
            tickvals=[0, 5, 10, 15, 20],
            fixedrange=True,
            gridcolor='#F0F0F0',
        ),
        yaxis=dict(
            title=None,
            tickfont=dict(size=10, color=TEXTO_OSCURO),
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
            titulo_seccion('🏥', 'Salud y Calidad de Vida',
                           'puntaje promedio 0–20 · solo pacientes al ingreso'),
            unsafe_allow_html=True,
        )

        if centro_id:
            df = df[df['centro'].astype(str).str.strip() == str(centro_id).strip()].copy()

        datos = _calcular_salud(df)

        if not datos['items']:
            st.caption('Sin datos de salud disponibles para este país.')
            return

        st.plotly_chart(_figura(datos), use_container_width=True,
                        config={'displayModeBar': False})

        st.markdown(
            f'<div style="font-size:.68rem;color:#999;margin-top:.1rem;">'
            f'  Puntajes promedio en escala 0–20 (0=pésimo, 20=excelente) · '
            f'  puntajes bajo 10 indican percepción deficiente · '
            f'  N válido: {datos["n"]}'
            f'</div>',
            unsafe_allow_html=True,
        )
