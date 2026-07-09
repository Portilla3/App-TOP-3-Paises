"""
pipeline.panel.dias_consumo — Días de consumo por sustancia al ingreso.

Muestra el promedio de días consumidos en las últimas 4 semanas (escala 0-28)
para cada sustancia registrada, solo en registros con etapa='ingreso'.

Columnas Supabase usadas: alcohol_total, marihuana_total, pastabase_total,
cocaina_total, sedantes_total. Se excluyen sustancias sin ningún registro > 0.

Diseño:
  - Barras horizontales ordenadas descendente por promedio
  - Escala fija 0-28 (eje X)
  - Línea de referencia vertical en 14 días (mitad del período)
  - Valor del promedio anotado al final de cada barra
  - N pacientes con > 0 días en hover

Función expuesta:
  render(df, pais, centro_id=None)
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from pipeline.panel.config import titulo_seccion


# Columnas Supabase → etiqueta visible
SUSTANCIAS_COLS = [
    ('alcohol_total',    'Alcohol'),
    ('marihuana_total',  'Marihuana'),
    ('cocaina_total',    'Cocaína'),
    ('pastabase_total',  'Pasta base'),
    ('sedantes_total',   'Sedantes'),
]

COLOR_BARRA    = '#4A90D9'
COLOR_REF      = '#B0B8C1'
TEXTO_OSCURO   = '#1F3864'
ALTO_BARRA_PX  = 32   # altura por barra en px


def _calcular_dias(df):
    """
    Filtra etapa=ingreso y calcula, para cada sustancia:
      - promedio de días (solo entre quienes registraron > 0)
      - n pacientes con > 0 días

    Excluye sustancias sin ningún paciente con > 0 días.
    Retorna lista de dicts ordenados desc por promedio.
    """
    cols_req = {'etapa'}
    if df is None or df.empty or not cols_req.issubset(df.columns):
        return []

    df_ing = df[df['etapa'].astype(str).str.strip() == 'ingreso'].copy()
    if df_ing.empty:
        return []

    resultado = []
    for col, label in SUSTANCIAS_COLS:
        if col not in df_ing.columns:
            continue
        serie = pd.to_numeric(df_ing[col], errors='coerce')
        con_valor = serie[serie > 0]
        if con_valor.empty:
            continue
        resultado.append({
            'sustancia': label,
            'promedio':  round(con_valor.mean(), 1),
            'n':         len(con_valor),
            'n_total':   len(df_ing),
        })

    resultado.sort(key=lambda x: x['promedio'], reverse=True)
    return resultado


def _figura(datos):
    """Construye el gráfico Plotly de barras horizontales."""
    labels   = [d['sustancia'] for d in datos]
    valores  = [d['promedio']  for d in datos]
    textos   = [f"<b>{d['promedio']}</b> días" for d in datos]
    hovers   = [
        f"<b>{d['sustancia']}</b><br>"
        f"Promedio: {d['promedio']} días<br>"
        f"Pacientes con consumo: {d['n']} de {d['n_total']}"
        for d in datos
    ]

    alto = max(180, len(datos) * ALTO_BARRA_PX + 60)

    fig = go.Figure()

    # Barras
    fig.add_trace(go.Bar(
        y=labels,
        x=valores,
        orientation='h',
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
        x0=14, x1=14, y0=-0.5, y1=len(datos) - 0.5,
        line=dict(color=COLOR_REF, width=1.5, dash='dot'),
        layer='below',
    )
    fig.add_annotation(
        x=14, y=len(datos) - 0.5,
        text='14 días',
        showarrow=False,
        font=dict(size=9, color=COLOR_REF),
        yanchor='bottom',
        xanchor='center',
    )

    fig.update_layout(
        height=alto,
        margin=dict(l=0, r=50, t=4, b=20),
        xaxis=dict(
            range=[0, 31],
            tickvals=[0, 7, 14, 21, 28],
            ticktext=['0', '7', '14', '21', '28'],
            title=None,
            gridcolor='#F0F0F0',
            zeroline=False,
        ),
        yaxis=dict(
            autorange='reversed',
            title=None,
            tickfont=dict(size=11),
        ),
        bargap=0.35,
        plot_bgcolor='white',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Inter, sans-serif', color=TEXTO_OSCURO),
        showlegend=False,
    )
    return fig


def render(df, pais, centro_id=None):
    """Renderiza el componente de días de consumo por sustancia."""
    with st.container(border=True):
        st.markdown(
            titulo_seccion(
                '📅', 'Días de consumo por sustancia',
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

        st.plotly_chart(_figura(datos), use_container_width=True, config={'displayModeBar': False})
