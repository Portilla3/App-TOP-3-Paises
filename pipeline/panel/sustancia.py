"""
pipeline.panel.sustancia — Sustancia principal declarada al ingreso.

Muestra el ranking de sustancias declaradas como principales por los pacientes
al momento del ingreso (etapa='ingreso'). El campo Supabase es 'sustancia_principal'
(text libre normalizado por los formularios de cada país).

Diseño:
  - Barras verticales, top 5-6 sustancias, resto agrupado en "Otras"
  - Color verde consistente con el bloque perfil
  - Porcentaje encima de cada barra
  - Nombre de la sustancia debajo

Función expuesta:
  render(df, pais, centro_id=None)

Notas de instrumento:
  Este componente es agnóstico al catálogo de sustancias por país. Se limita
  a leer 'sustancia_principal' tal como viene en Supabase y a agrupar.
  Cuando lleguemos a "columnas_instrumento" para el gráfico de "Días de
  consumo por sustancia" (sesión 4), ese sí necesita el catálogo por país.
"""
import unicodedata
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from pipeline.panel.config import titulo_seccion


COLOR_BARRA  = '#2E9B6C'   # verde consistente con continuidad
TEXTO_OSCURO = '#1F3864'


TOP_N_SUSTANCIAS = 6


# Nombres canónicos para display. Se aplica sobre la versión normalizada
# (mayúsculas y sin tildes). Las que no estén en el mapa se muestran
# en Title Case como fallback.
NOMBRES_CANONICOS = {
    'ALCOHOL':     'Alcohol',
    'MARIHUANA':   'Marihuana',
    'MARIGUANA':   'Marihuana',
    'COCAINA':     'Cocaína',
    'PASTA BASE':  'Pasta base',
    'PASTA':       'Pasta base',
    'BASUCO':      'Pasta base',
    'CRACK':       'Crack',
    'PIEDRA':      'Crack',
    'HEROINA':     'Heroína',
    'SEDANTES':    'Sedantes',
    'BENZODIACEPINAS': 'Sedantes',
    'INHALABLES':  'Inhalables',
    'INHALANTES':  'Inhalables',
    'TUSI':        'Tusi',
    'TUSSI':       'Tusi',
    'DOS CG':      'Tusi',
    'ANFETAMINAS': 'Anfetaminas',
    'METANFETAMINAS': 'Metanfetaminas',
    'CRISTAL':     'Metanfetaminas',
    'ECSTASY':     'Éxtasis',
    'EXTASIS':     'Éxtasis',
    'LSD':         'LSD',
    'KETAMINA':    'Ketamina',
    'OTRA':        'Otra',
    'OTRO':        'Otra',
    'OTRAS':       'Otras',
    'OTROS':       'Otras',
    'NINGUNA':     'Ninguna',
    'NINGUNO':     'Ninguna',
}


def _normalizar(s):
    """Convierte a mayúsculas y quita tildes para comparación."""
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ''
    txt = str(s).strip().upper()
    # Quitar tildes
    txt = ''.join(
        c for c in unicodedata.normalize('NFD', txt)
        if unicodedata.category(c) != 'Mn'
    )
    return txt


def _display(clave_normalizada):
    """Devuelve el nombre canónico para mostrar. Fallback: Title Case."""
    if clave_normalizada in NOMBRES_CANONICOS:
        return NOMBRES_CANONICOS[clave_normalizada]
    return clave_normalizada.title()


def _calcular_sustancias(df):
    """
    Filtra a etapa=ingreso, normaliza el texto (mayúsculas + sin tildes)
    y agrupa por sustancia_principal. Las que quedan fuera del TOP_N
    se agregan como 'Otras'.

    Returns:
        pd.DataFrame con columnas: sustancia, n, pct.
    """
    cols_req = {'etapa', 'sustancia_principal'}
    if df is None or df.empty or not cols_req.issubset(df.columns):
        return pd.DataFrame(columns=['sustancia', 'n', 'pct'])

    tmp = df.copy()
    tmp['etapa'] = tmp['etapa'].fillna('').astype(str)
    tmp = tmp[tmp['etapa'] == 'ingreso']
    if tmp.empty:
        return pd.DataFrame(columns=['sustancia', 'n', 'pct'])

    # Normalizar antes de contar: 'Alcohol' == 'ALCOHOL' == 'alcohol'
    tmp['sust_norm'] = tmp['sustancia_principal'].apply(_normalizar)
    tmp = tmp[tmp['sust_norm'] != '']
    if tmp.empty:
        return pd.DataFrame(columns=['sustancia', 'n', 'pct'])

    conteo = tmp.groupby('sust_norm').size().reset_index(name='n')
    conteo = conteo.sort_values('n', ascending=False).reset_index(drop=True)

    total = int(conteo['n'].sum())

    if len(conteo) > TOP_N_SUSTANCIAS:
        top   = conteo.iloc[:TOP_N_SUSTANCIAS].copy()
        resto = conteo.iloc[TOP_N_SUSTANCIAS:]
        if len(resto) > 0:
            fila_otras = pd.DataFrame([{
                'sust_norm': 'OTRAS',
                'n': int(resto['n'].sum())
            }])
            top = pd.concat([top, fila_otras], ignore_index=True)
        conteo = top

    # Aplicar nombre canónico para display
    conteo['sustancia'] = conteo['sust_norm'].apply(_display)
    conteo['pct']       = conteo['n'] / total * 100
    return conteo[['sustancia', 'n', 'pct']]


def render(df, pais, centro_id=None):
    """
    Pinta las barras de sustancia principal declarada al ingreso.
    """
    with st.container(border=True):
        st.markdown(
            titulo_seccion('💊', 'Sustancia principal declarada',
                           '% de pacientes al ingreso'),
            unsafe_allow_html=True
        )

        # Filtrado opcional por centro
        if centro_id and 'centro' in df.columns:
            df_local = df[df['centro'].astype(str).str.strip() == str(centro_id).strip()].copy()
        else:
            df_local = df

        conteo = _calcular_sustancias(df_local)

        if conteo.empty:
            st.info('ℹ Aún no hay datos de sustancia principal para el ingreso.')
            return

        textos = [f'{p:.0f}%' for p in conteo['pct']]
        hovers = [
            f'<b>{s}</b><br>{n} pacientes<br>{p:.1f}%'.replace('.', ',')
            for s, n, p in zip(conteo['sustancia'], conteo['n'], conteo['pct'])
        ]

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=conteo['sustancia'],
            y=conteo['pct'],
            marker=dict(color=COLOR_BARRA, line=dict(width=0)),
            text=textos,
            textposition='outside',
            textfont=dict(color=TEXTO_OSCURO, size=13, family='Arial'),
            hovertext=hovers,
            hoverinfo='text',
            showlegend=False,
            cliponaxis=False,
        ))

        max_pct = float(conteo['pct'].max()) if not conteo.empty else 100.0

        fig.update_layout(
            height=220,
            margin=dict(l=10, r=10, t=15, b=15),
            xaxis=dict(
                tickfont=dict(size=12, color=TEXTO_OSCURO, family='Arial'),
                fixedrange=True,
            ),
            yaxis=dict(
                visible=False,
                range=[0, max_pct * 1.25],
                fixedrange=True,
            ),
            plot_bgcolor='white',
            paper_bgcolor='white',
        )

        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
