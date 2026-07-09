"""
pipeline.panel.edad — Distribución por rango de edad al ingreso.

Rangos alineados con los informes Word/PowerPoint:
  Menos de 18 / 18 a 30 / 31 a 40 / 41 a 50 / 51 a 60 / 61 o más

Solo registros con etapa='ingreso'. Edad calculada desde fecha_nacimiento
respecto a fecha_entrevista (o fecha actual si falta).

Diseño: barras horizontales, el rango más frecuente destacado en azul oscuro,
los demás en azul claro. Valor y % al lado de cada barra.

Función expuesta:
  render(df, pais, centro_id=None)
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from pipeline.panel.config import titulo_seccion

COLOR_DESTAC = '#004AAD'   # from config PALETA_PRINCIPAL
COLOR_BASE   = '#E5E5E5'   # from config PALETA_SECUNDARIO
TEXTO_OSCURO = '#004AAD'

RANGOS = ['Menos de 18', '18 a 30', '31 a 40', '41 a 50', '51 a 60', '61 o más']


def _clasificar_edad(edad):
    if pd.isna(edad):
        return None
    e = int(edad)
    if e < 18:  return 'Menos de 18'
    if e <= 30: return '18 a 30'
    if e <= 40: return '31 a 40'
    if e <= 50: return '41 a 50'
    if e <= 60: return '51 a 60'
    return '61 o más'


def _calcular_edad(df):
    vacio = {'rangos': RANGOS, 'conteos': [0]*len(RANGOS), 'total': 0,
             'promedio': None, 'rango_max': None}

    if df is None or df.empty or 'etapa' not in df.columns:
        return vacio

    df_ing = df[df['etapa'].astype(str).str.strip() == 'ingreso'].copy()
    if df_ing.empty:
        return vacio

    # Calcular edad
    if 'fecha_nacimiento' in df_ing.columns and 'fecha_entrevista' in df_ing.columns:
        fn  = pd.to_datetime(df_ing['fecha_nacimiento'],  errors='coerce')
        fe  = pd.to_datetime(df_ing['fecha_entrevista'],  errors='coerce')
        fe  = fe.fillna(pd.Timestamp.now())
        edad = ((fe - fn).dt.days / 365.25).where(fn.notna())
    elif 'fecha_nacimiento' in df_ing.columns:
        fn   = pd.to_datetime(df_ing['fecha_nacimiento'], errors='coerce')
        hoy  = pd.Timestamp.now()
        edad = ((hoy - fn).dt.days / 365.25).where(fn.notna())
    else:
        return vacio

    df_ing['_rango'] = edad.apply(_clasificar_edad)
    df_ing = df_ing.dropna(subset=['_rango'])
    if df_ing.empty:
        return vacio

    conteos_raw = df_ing['_rango'].value_counts()
    conteos     = [int(conteos_raw.get(r, 0)) for r in RANGOS]
    total       = sum(conteos)
    rango_max   = RANGOS[conteos.index(max(conteos))] if total > 0 else None
    promedio    = round(edad.dropna().mean(), 1) if edad.notna().any() else None

    return {
        'rangos':    RANGOS,
        'conteos':   conteos,
        'total':     total,
        'promedio':  promedio,
        'rango_max': rango_max,
    }


def _figura(datos):
    rangos  = datos['rangos'][::-1]   # invertir para que "Menos de 18" quede abajo
    conteos = datos['conteos'][::-1]
    total   = datos['total']
    rango_max = datos['rango_max']

    colores = [COLOR_DESTAC if r == rango_max else COLOR_BASE for r in rangos]
    textos  = [
        f"{n} ({round(n/total*100,1)}%)" if total > 0 else "0"
        for n in conteos
    ]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=rangos,
        x=conteos,
        orientation='h',
        marker_color=colores,
        text=textos,
        textposition='outside',
        textfont=dict(size=10, color=TEXTO_OSCURO),
        hovertemplate='%{y}: %{x} personas<extra></extra>',
        cliponaxis=False,
    ))

    fig.update_layout(
        height=210,
        margin=dict(l=0, r=90, t=4, b=8),
        xaxis=dict(
            range=[0, max(conteos) * 1.45] if conteos else [0, 10],
            visible=False,
            fixedrange=True,
        ),
        yaxis=dict(
            title=None,
            tickfont=dict(size=10, color=TEXTO_OSCURO),
            fixedrange=True,
        ),
        bargap=0.3,
        plot_bgcolor='white',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Inter, sans-serif', color=TEXTO_OSCURO),
        showlegend=False,
    )
    return fig


def render(df, pais, centro_id=None):
    with st.container(border=True):
        st.markdown(
            titulo_seccion('📊', 'Distribución por rango de edad',
                           'pacientes al ingreso · primera evaluación TOP'),
            unsafe_allow_html=True,
        )

        if centro_id:
            df = df[df['centro'].astype(str).str.strip() == str(centro_id).strip()].copy()

        datos = _calcular_edad(df)

        if datos['total'] == 0:
            st.caption('Sin datos de edad disponibles.')
            return

        st.plotly_chart(_figura(datos), use_container_width=True,
                        config={'displayModeBar': False})

        # Nota al pie con promedio
        if datos['promedio']:
            rango_max = datos['rango_max']
            n_max = datos['conteos'][datos['rangos'].index(rango_max)]
            pct_max = round(n_max / datos['total'] * 100, 1)
            st.markdown(
                f'<div style="font-size:.68rem;color:#999;margin-top:.1rem;">'
                f'  Promedio de edad: {datos["promedio"]} años · '
                f'  rango más frecuente: {rango_max} ({pct_max}%) · '
                f'  N válido: {datos["total"]}'
                f'</div>',
                unsafe_allow_html=True,
            )
