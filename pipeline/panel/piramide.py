"""
pipeline.panel.piramide — Distribución de sexo al ingreso (dona).

Reemplaza la pirámide etaria por una dona de tres segmentos:
  - Hombres
  - Mujeres
  - Otros (todo lo que no sea M/F, incluyendo no binario, sin dato, etc.)

Diseño consistente con la dona de transgresión:
  - Dona central con % del grupo mayoritario
  - Tres métricas debajo: n y % por grupo
  - Sin leyenda flotante

Función expuesta:
  render(df, pais, centro_id=None)
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from pipeline.panel.config import titulo_seccion
from pipeline.validacion_top import normalizar_sexo_valor, lineas_base


COLOR_HOMBRE  = '#004AAD'   # from config PALETA_PRINCIPAL
COLOR_MUJER   = '#7B68EE'   # from config PALETA_MUJER
COLOR_OTROS   = '#B4BAC2'   # from config PALETA_OTROS_SEXO
TEXTO_OSCURO  = '#004AAD'


def _normalizar_sexo(v):
    """Delegado a validacion_top.normalizar_sexo_valor (fuente única)."""
    return normalizar_sexo_valor(v)


def _calcular_sexo(df):
    """
    Filtra etapa=ingreso y cuenta por grupo de sexo.
    Retorna dict con n_hombres, n_mujeres, n_otros, total, pct_* .
    """
    vacio = {
        'n_hombres': 0, 'n_mujeres': 0, 'n_otros': 0, 'total': 0,
        'pct_hombres': 0, 'pct_mujeres': 0, 'pct_otros': 0,
    }
    if df is None or df.empty or 'etapa' not in df.columns:
        return vacio

    # Una fila por episodio: el TOP de ingreso que lo abre. Ver DECISIONES.md.
    df_ing = lineas_base(df).copy()
    if df_ing.empty:
        return vacio

    if 'sexo' not in df_ing.columns:
        return vacio

    grupos = df_ing['sexo'].apply(_normalizar_sexo).value_counts()
    n_h = int(grupos.get('H', 0))
    n_m = int(grupos.get('M', 0))
    n_o = int(grupos.get('O', 0))
    total = n_h + n_m + n_o
    if total == 0:
        return vacio

    return {
        'n_hombres':   n_h,
        'n_mujeres':   n_m,
        'n_otros':     n_o,
        'total':       total,
        'pct_hombres': round(n_h / total * 100, 1),
        'pct_mujeres': round(n_m / total * 100, 1),
        'pct_otros':   round(n_o / total * 100, 1),
    }


def _figura_dona(datos):
    """Dona de tres segmentos con % mayoritario al centro."""
    grupos = [
        ('Hombres', datos['n_hombres'], COLOR_HOMBRE),
        ('Mujeres', datos['n_mujeres'], COLOR_MUJER),
        ('Otros',   datos['n_otros'],   COLOR_OTROS),
    ]
    # Filtrar grupos con n > 0 para no mostrar segmentos vacíos
    grupos_vis = [(lbl, n, c) for lbl, n, c in grupos if n > 0]

    labels  = [g[0] for g in grupos_vis]
    values  = [g[1] for g in grupos_vis]
    colors  = [g[2] for g in grupos_vis]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.65,
        marker=dict(colors=colors, line=dict(color='white', width=2)),
        textinfo='none',
        hovertemplate='%{label}: %{value} pacientes (%{percent})<extra></extra>',
        sort=False,
    ))

    # Texto central: grupo mayoritario
    grupo_max = max(grupos_vis, key=lambda g: g[1])
    pct_max   = round(grupo_max[1] / datos['total'] * 100, 1)
    color_max = grupo_max[2]

    fig.add_annotation(
        text=f"<b>{pct_max}%</b>",
        x=0.5, y=0.56,
        font=dict(size=26, color=color_max, family='Inter, sans-serif'),
        showarrow=False,
    )
    fig.add_annotation(
        text=grupo_max[0].lower(),
        x=0.5, y=0.38,
        font=dict(size=10, color='#777', family='Inter, sans-serif'),
        showarrow=False,
    )

    fig.update_layout(
        height=200,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor='rgba(0,0,0,0)',
        showlegend=False,
        font=dict(family='Inter, sans-serif', color=TEXTO_OSCURO),
    )
    return fig


def render(df, pais, centro_id=None):
    """Renderiza la dona de distribución de sexo al ingreso."""
    with st.container(border=True):
        st.markdown(
            titulo_seccion(
                '👥', 'Distribución por sexo',
                'pacientes al ingreso · primera evaluación TOP'
            ),
            unsafe_allow_html=True,
        )

        if centro_id:
            df = df[df['centro'].astype(str).str.strip() == str(centro_id).strip()].copy()

        datos = _calcular_sexo(df)

        if datos['total'] == 0:
            st.caption('Sin datos de sexo disponibles.')
            return

        st.plotly_chart(_figura_dona(datos), use_container_width=True,
                        config={'displayModeBar': False})

        # Métricas debajo: n y % por grupo
        grupos = [
            ('Hombres', datos['n_hombres'], datos['pct_hombres'], COLOR_HOMBRE),
            ('Mujeres', datos['n_mujeres'], datos['pct_mujeres'], COLOR_MUJER),
            ('Otros',   datos['n_otros'],   datos['pct_otros'],   COLOR_OTROS),
        ]
        cols = st.columns(3)
        for i, (label, n, pct, color) in enumerate(grupos):
            with cols[i]:
                st.markdown(
                    f'<div style="text-align:center;padding:.2rem 0;">'
                    f'  <div style="font-size:1rem;font-weight:700;color:{color};">{n}</div>'
                    f'  <div style="font-size:.68rem;color:#777;line-height:1.3;">'
                    f'    {label}<br>({pct}%)'
                    f'  </div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
